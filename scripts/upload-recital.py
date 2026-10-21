#!/usr/bin/env python3
"""Sube un recital a archive.org y abre la entrada en el sitio.

Pensado para living en la carpeta de los masters: copiá este archivo ahí, poné
un `recital.txt` al lado con los datos del show, y corré el script desde esa
carpeta. El `recital.txt` es lo que evita que dos recitales se confundan: cada
carpeta dice de qué recital es, con qué fecha, qué bandas y qué archivo es de
quién.

    python3 upload-recital.py --dry-run    # planifica todo, no toca nada
    python3 upload-recital.py              # sube, sincroniza y crea la página
    python3 upload-recital.py --init       # escribe un recital.txt de ejemplo

Qué hace, en orden:

  0. Lee el `recital.txt` (o el que se pase con --info) y valida los datos.
  1. Resuelve qué archivo es de qué banda y arma el nombre canónico de cada
     pista: "NN - <Banda> - <Evento> (<fecha>).wav".
     Los masters NO se tocan: se copian a un temporal con ese nombre.
  2. Sube el item a archive.org con la CLI `ia`, con la metadata que usa el
     catálogo (title, date, venue, coverage, description, collection).
  3. Espera a que archive.org derive el .mp3 (y el .flac) de cada original.
  4. Inserta el esqueleto del show en <repo>/data/shows.yml.
  5. Corre <repo>/scripts/sync-archive.py, que es el que llena los tracks
     (mp3/flac/wav + duraciones) leyendo la metadata del item.
  6. Crea <repo>/content/recitales/<venue>/<show>/index.md con un
     {{< track >}} por pista, y copia el flyer como featured.<ext>.

Requisitos:
  - la CLI `ia` de archive.org, autenticada (va a estar: `ia configure --whoami`)
  - PyYAML
  - el repo del sitio: se busca hacia arriba desde este archivo, cae a
    ~/web/gusano-master, o se pasa con --repo / $GUSANO_REPO.

Flags útiles:
  --dry-run        planifica y muestra el plan, no sube ni escribe nada
  --init           escribe un recital.txt de ejemplo
  --skip-upload    el item ya está subido: arranca desde la entrada del catálogo
  --update         el show ya existe en data/shows.yml: lo actualiza
  --build          al final corre `hugo --minify --gc` para verificar

La guía completa, con el formato del recital.txt y qué hacer cuando algo
falla, está en docs/subir-un-recital.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML requerido: pip install pyyaml")

HERE = Path(__file__).resolve().parent
AUDIO_EXTS = (".wav", ".flac", ".mp3", ".m4a", ".ogg", ".aif", ".aiff")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
AUDIO_EXT = AUDIO_EXTS  # el sync llama así a los formatos que reconoce
INFO_NAMES = ("recital.txt", "recital.yaml", "recital.yml", "recital.info")
DEFAULT_COVERAGE = "Chivilcoy, Buenos Aires, Argentina"
DEFAULT_COLLECTION = "opensource_audio"
DEFAULT_MEDIATYPE = "audio"
DEFAULT_CREATOR = "gusanoide"
UA = "audiogusano-upload/1.0"

INFO_TEMPLATE = """\
# Datos del recital. Editá este archivo y corré upload-recital.py en la misma
# carpeta. Lo que está comentado es opcional.

# Nombre del evento. Va en el título del item y en el nombre de los archivos.
title: Festimaga 6

# Espacio (la sala). Va en el item y en el catálogo.
venue: La Maga

# Fecha real del show. IMPORTANTE: tiene que ser la misma que la del item en
# archive.org, porque es lo que usa el matcher para cruzarlos.
date: 2026-11-14

# Slug de la página: content/recitales/<venue-slug>/<slug>/
slug: festimaga6

# Bandas que tocaron (van a data/shows.yml y al filtro de /flyers/).
bands:
  - Mate Jazz
  - Black Mamba

# Una pista por archivo. "file" es el nombre del master, "band" la banda.
# Si no lo ponés, el script intenta adivinar por el nombre del archivo.
tracks:
  - file: 01 - mate jazz.wav
    band: Mate Jazz
  - file: 02 - black mamba.wav
    band: Black Mamba

# Flyer opcional: se copia a la página como featured.<ext> y la página entra
# sola al archivo de /flyers/.
featured: flyer.jpg

# Metadata extra del item de archive.org (opcional).
metadata:
  # creator: gusanoide
  # coverage: Chivilcoy, Buenos Aires, Argentina
"""


# ---------------------------------------------------------------- utilidades


def norm(s: str) -> str:
    """Minúsculas, sin acentos y sin signos. La misma normalización que usa
    sync-archive.py, para que las comparaciones den igual."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug(s: str) -> str:
    """'La Maga' -> 'la-maga'. Igual criterio que en el resto del repo."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "").replace("’", "")
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def die(msg: str) -> None:
    print(f"\nERROR: {msg}\n", file=sys.stderr)
    raise SystemExit(1)


def say(msg: str) -> None:
    print(msg, flush=True)


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


# ------------------------------------------------------------- info y repo


def find_info(explicit: str | None, folder: Path) -> Path:
    """El recital.txt: el que se pasó, o el primero que aparece en la carpeta
    de los masters, o en la carpeta del script, o en la de trabajo."""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_file():
            die(f"no existe el archivo de info {p}")
        return p.resolve()
    for base in (folder, HERE, Path.cwd()):
        for name in INFO_NAMES:
            p = base / name
            if p.is_file():
                return p.resolve()
    die(
        "no encontré el archivo de info. Poné un 'recital.txt' en la carpeta de "
        "los masters (o usá --init para que te lo escriba) y volvé a correr."
    )


def find_repo(explicit: str | None) -> Path:
    """El repo del sitio: --repo, $GUSANO_REPO, el primero hacia arriba que
    tenga data/shows.yml y scripts/sync-archive.py, o el lugar de siempre.

    El fallback importa: el script se copia a la carpeta de los masters, que
    vive fuera del repo, así que la búsqueda hacia arriba no encuentra nada."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("GUSANO_REPO"):
        candidates.append(Path(os.environ["GUSANO_REPO"]).expanduser())
    for start in (HERE, Path.cwd()):
        candidates.extend([start, *start.parents])
    candidates.append(Path.home() / "web" / "gusano-master")
    for c in candidates:
        if (c / "data" / "shows.yml").is_file() and (c / "scripts" / "sync-archive.py").is_file():
            return c.resolve()
    die(
        "no encontré el repo del sitio. Pasalo con --repo /ruta/al/repo, "
        "definí $GUSANO_REPO, o corré el script desde dentro del repo."
    )


def load_info(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        die(f"{path.name} no es un YAML válido: {exc}")
    if not isinstance(data, dict):
        die(f"{path.name}: tiene que ser una lista de 'clave: valor'.")
    return data


def get_str(info: dict, *names: str) -> str:
    for n in names:
        v = info.get(n)
        # YAML parsea "date: 2026-11-14" como datetime.date, no como texto.
        if isinstance(v, dt.datetime):
            v = v.date().isoformat()
        elif isinstance(v, dt.date):
            v = v.isoformat()
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def get_list(info: dict, *names: str) -> list[str]:
    for n in names:
        v = info.get(n)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [x.strip() for x in v.split(",") if x.strip()]
    return []


# ------------------------------------------------------------- plan de pistas


def resolve_file(folder: Path, name: str) -> Path | None:
    """Busca el master dentro de la carpeta. Exacto, y si no, por mayúsculas,
    por prefijo y por nombre normalizado (sin acentos)."""
    name = name.strip()
    direct = folder / name
    if direct.is_file():
        return direct
    cands = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
    for p in cands:
        if p.name.lower() == name.lower():
            return p
    stem = Path(name).stem.lower()
    for p in cands:
        if p.stem.lower().startswith(stem) or stem.startswith(p.stem.lower()):
            return p
    target = norm(name)
    for p in cands:
        if norm(p.name) == target:
            return p
    return None


def guess_band(filename: str, bands: list[str]) -> str:
    """Adivina la banda a partir del nombre del archivo."""
    n = norm(filename)
    hits = [b for b in bands if norm(b) and norm(b) in n]
    if not hits:
        return ""
    return max(hits, key=lambda b: len(norm(b)))


def build_plan(info: dict, folder: Path, required: bool = True) -> list[dict]:
    """Resuelve la lista de pistas: archivo de origen + banda + nombre canónico
    que va a tener en archive.org.

    Con required=False (--skip-upload) la carpeta puede no tener audios: el
    item ya está subido y las pistas las lee el sync de la metadata de
    archive.org."""
    bands = get_list(info, "bands", "bandas")
    raw_tracks = info.get("tracks") or info.get("pistas") or []
    if isinstance(raw_tracks, str):
        raw_tracks = [raw_tracks]

    plan: list[dict] = []
    unresolved: list[str] = []

    if raw_tracks:
        for entry in raw_tracks:
            if isinstance(entry, str):
                # "archivo = banda" o "archivo | banda"
                sep = "=" if "=" in entry else ("|" if "|" in entry else None)
                if sep:
                    fname, band = [x.strip() for x in entry.split(sep, 1)]
                else:
                    fname, band = entry.strip(), ""
            elif isinstance(entry, dict):
                fname = str(entry.get("file") or entry.get("archivo") or "").strip()
                band = str(entry.get("band") or entry.get("banda") or "").strip()
            else:
                continue
            if not fname:
                continue
            src = resolve_file(folder, fname)
            if src is None:
                unresolved.append(fname)
                continue
            if not band:
                band = guess_band(src.name, bands)
            plan.append({"src": src, "band": band})
    else:
        # Sin lista de pistas: se toman todos los audios de la carpeta.
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                plan.append({"src": p, "band": guess_band(p.name, bands)})

    if unresolved:
        die(
            "en el recital.txt hay archivos que no están en la carpeta:\n  - "
            + "\n  - ".join(unresolved)
            + "\nLa carpeta tiene: "
            + ", ".join(sorted(p.name for p in folder.iterdir() if p.is_file()))
        )
    if not plan and required:
        die(f"no hay audios para subir en {folder}")

    for i, t in enumerate(plan, start=1):
        band = t["band"]
        if not band:
            die(
                f"no pude saber de qué banda es '{t['src'].name}'.\n"
                "Agregalo al recital.txt:\n"
                "  tracks:\n"
                f"    - file: {t['src'].name}\n"
                "      band: <banda>"
            )
        t["band"] = band
        t["index"] = i
    return plan


def stage_files(plan: list[dict], title: str, date: str) -> list[Path]:
    """Copia cada master a un temporal con el nombre canónico. Los originales
    no se tocan nunca."""
    tmp = Path(tempfile.mkdtemp(prefix="audiogusano-"))
    staged = []
    for t in plan:
        ext = t["src"].suffix.lower()
        name = f"{t['index']:02d} - {t['band']} - {title} ({date}){ext}"
        dest = tmp / name
        shutil.copy2(t["src"], dest)
        t["remote"] = name
        staged.append(dest)
    return staged


# ------------------------------------------------------------------ archive.org


def ia_metadata(identifier: str) -> dict | None:
    """Metadata del item en archive.org, o None si no existe."""
    url = f"https://archive.org/metadata/{identifier}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    if not data:
        return None
    return data


def item_exists(identifier: str) -> bool:
    return ia_metadata(identifier) is not None


def existing_track_count(identifier: str) -> int:
    """Cuántas pistas tiene ya el item: para seguir numerando desde ahí y no
    repetir los números de los archivos."""
    data = ia_metadata(identifier) or {}
    groups = set()
    for f in data.get("files") or []:
        name = f.get("name") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if f".{ext}" not in AUDIO_EXT:
            continue
        groups.add(f.get("original") or name)
    return len(groups)


def upload_item(identifier: str, files: list[Path], meta: dict) -> None:
    ia = shutil.which("ia")
    if not ia:
        die("no está la CLI 'ia' de archive.org. Instalala con: pip install internetarchive")
    cmd = [ia, "upload", identifier, *[str(f) for f in files]]
    for k, v in meta.items():
        cmd += ["-m", f"{k}:{v}"]
    say(f"\n$ {' '.join(cmd[:3])} ... ({len(files)} archivos)")
    say("  metadata: " + ", ".join(f"{k}={v}" for k, v in meta.items()))
    res = subprocess.run(cmd)
    if res.returncode != 0:
        die(f"la CLI 'ia' falló con código {res.returncode}")


def wait_for_derivatives(identifier: str, originals: list[str], timeout: int = 1800) -> bool:
    """Espera a que archive.org derive los mp3. Los originales van derivados
    en background, y sin ellos el catálogo no encuentra archivo que reproducir."""
    deadline = time.time() + timeout
    pending = list(originals)
    say(f"\nEsperando los derivados de archive.org (hasta {timeout // 60} min)...")
    while pending and time.time() < deadline:
        data = ia_metadata(identifier) or {}
        names = {(f.get("name") or "") for f in (data.get("files") or [])}
        still = []
        for name in pending:
            base = name.rsplit(".", 1)[0]
            if name.lower().endswith(".mp3"):
                continue  # el mp3 ya es el original
            if f"{base}.mp3" in names or f"{base}.flac" in names:
                continue
            still.append(name)
        pending = still
        if pending:
            say(f"  faltan {len(pending)} derivados: {', '.join(pending)}")
            time.sleep(30)
    if pending:
        say(
            "\nAVISO: no llegaron todos los derivados a tiempo.\n"
            "  Podés seguir: el catálogo puede usar el .wav directamente.\n"
            "  Cuando archive.org termine, se completa con:\n"
            "    python3 <repo>/scripts/sync-archive.py --show <id> --refresh --write"
        )
        return False
    say("  derivados listos.")
    return True


# ------------------------------------------------------------------- catálogo


def load_shows(repo: Path) -> tuple[list[dict], str]:
    path = repo / "data" / "shows.yml"
    raw = path.read_text(encoding="utf-8")
    shows = yaml.safe_load(raw) or []
    header = raw.split("- id:")[0]
    return shows, header


def save_shows(repo: Path, shows: list[dict], header: str) -> None:
    """Escribe el catálogo. El orden de las claves se fija acá: el archivo
    tiene que quedar igual que lo que produce sync-archive.py, para que el
    diff sea sólo lo del show nuevo."""
    order = [
        "id",
        "date",
        "title",
        "tracks",
        "space",
        "bands",
        "cover",
        "page",
        "archive",
        "archive_url",
    ]
    shows.sort(key=lambda s: (s.get("date") or "", s.get("id") or ""), reverse=True)
    ordered = []
    for s in shows:
        row = {k: s[k] for k in order if k in s}
        row.update({k: v for k, v in s.items() if k not in row})
        ordered.append(row)
    body = yaml.safe_dump(
        ordered, sort_keys=False, allow_unicode=True, default_flow_style=False, width=10000
    )
    (repo / "data" / "shows.yml").write_text(header + body, encoding="utf-8")


def upsert_show(repo: Path, show: dict, update: bool) -> None:
    """Inserta (o actualiza) el esqueleto del show.

    Al actualizar se conservan las pistas que ya estaban: el sync usa el texto
    viejo (title, artist) para no perder la forma en que estaba escrita la
    entrada, y sólo actualiza los nombres de archivo."""
    shows, header = load_shows(repo)
    old = next((s for s in shows if s.get("id") == show["id"]), None)
    if old is not None and not update:
        die(
            f"el show '{show['id']}' ya está en data/shows.yml.\n"
            "Si querés actualizarlo, corré con --update."
        )
    if old is not None:
        show["tracks"] = old.get("tracks") or []
        # El título del catálogo está cuidado a mano: se respeta.
        if old.get("title"):
            show["title"] = old["title"]
        # Las bandas sí las manda el recital.txt: es la fuente de verdad de
        # este show. Si difieren, se avisa, para ver el cambio.
        old_bands = old.get("bands") or []
        new_bands = show.get("bands") or []
        if new_bands and new_bands != old_bands:
            say(f"  bandas: {old_bands} -> {new_bands}")
        show["bands"] = new_bands or old_bands
        show.setdefault("cover", old.get("cover"))
        if not show.get("cover"):
            show.pop("cover", None)
    shows = [s for s in shows if s.get("id") != show["id"]]
    shows.append(show)
    save_shows(repo, shows, header)


def run_sync(repo: Path, show_id: str) -> bool:
    """El que de verdad llena los tracks."""
    cmd = [
        sys.executable,
        str(repo / "scripts" / "sync-archive.py"),
        "--show",
        show_id,
        "--refresh",
        "--write",
    ]
    say(f"\n$ python3 scripts/sync-archive.py --show {show_id} --refresh --write")
    res = subprocess.run(cmd, cwd=repo)
    if res.returncode != 0:
        say(f"  sync-archive.py terminó con código {res.returncode}")
        return False
    return True


def get_show(repo: Path, show_id: str) -> dict | None:
    shows, _ = load_shows(repo)
    for s in shows:
        if s.get("id") == show_id:
            return s
    return None


# ---------------------------------------------------------------------- página


def next_weight(repo: Path) -> int:
    """Los pesos van correlativos: la página más nueva tiene el más negativo."""
    weights = []
    for p in (repo / "content" / "recitales").rglob("index.md"):
        m = re.search(r"^weight\s*:\s*(-?\d+)", p.read_text(encoding="utf-8"), re.M)
        if m:
            weights.append(int(m.group(1)))
    return (min(weights) - 1) if weights else -1


TRACK_RE = re.compile(
    r'\{\{<\s*track\s+show="([^"]*)"\s+track="([^"]*)"\s*>\}\}'
)


def write_page(repo: Path, show: dict, featured: Path | None, venue: str) -> Path:
    """Crea la página del show.

    Si la página ya existe NO se toca: las páginas tienen texto escrito a
    mano (links a Instagram, artículos, notas del show) y pisar eso sería
    perder trabajo. Lo que sí hace es avisar qué players quedaron afuera, con
    el markdown listo para pegar.

    Si no existe, se arma sola: front matter + un {{< track >}} por pista."""
    show_id = show["id"]
    venue_slug, show_slug = show_id.split("/", 1)
    page_dir = repo / "content" / "recitales" / venue_slug / show_slug
    page = page_dir / "index.md"

    if page.is_file():
        existing = page.read_text(encoding="utf-8")
        have = {tid for sid, tid in TRACK_RE.findall(existing) if sid == show_id}
        missing = [t for t in (show.get("tracks") or []) if t.get("id") not in have]
        if missing:
            say(f"\nla página ya existe: {page.relative_to(repo)}")
            say("no la toco (tiene texto escrito a mano). Faltan estos players:")
            for t in missing:
                artist = t.get("artist") or t.get("id") or ""
                say(f"  # {artist}")
                say(f'  {{{{< track show="{show_id}" track="{t.get("id")}" >}}}}')
                say("")
        else:
            say(f"página  : {page.relative_to(repo)} (ya existía, sin cambios)")
        # El flyer: si la página ya tiene uno, no se toca. Si no, se copia el
        # nuevo para que entre al archivo de /flyers/.
        if featured and featured.is_file() and not list(page_dir.glob("featured.*")):
            ext = featured.suffix.lower()
            shutil.copy2(featured, page_dir / f"featured{ext}")
            show["cover"] = f"/recitales/{venue_slug}/{show_slug}/featured{ext}"
        return page

    page_dir.mkdir(parents=True, exist_ok=True)
    bands = show.get("bands") or []
    title = show.get("title") or ""
    page_title = title if norm(venue) in norm(title) else f"{title} en {venue}"
    space = show.get("space") or venue
    if isinstance(space, str):
        spaces = [space]
    else:
        spaces = list(space)

    fm = [
        "---",
        f"date : {show.get('date')}",
        f'title : "{page_title}"',
        f"weight: {next_weight(repo)}",
        "bandas: [" + ", ".join(bands) + "]",
        "espacios: [" + ", ".join(spaces) + "]",
        'author: "Gusanoide"',
        "draft: false",
        "showHero: true",
        "heroStyle: background",
        "---",
        "",
    ]

    body: list[str] = []
    tracks = show.get("tracks") or []
    for t in tracks:
        artist = t.get("artist") or t.get("id") or ""
        body += [
            f"# {artist}",
            "",
            # {{ y }} hay que escaparlos en un f-string: sale {{< track >}}
            f'{{{{< track show="{show_id}" track="{t.get("id")}" >}}}}',
            "",
            "---",
            "",
        ]
    if show.get("archive_url"):
        body += [f"[Artículo en Internet Archive]({show['archive_url']})", ""]

    page.write_text("\n".join(fm + body), encoding="utf-8")
    say(f"página  : {page.relative_to(repo)}")

    if featured and featured.is_file():
        ext = featured.suffix.lower()
        shutil.copy2(featured, page_dir / f"featured{ext}")
        show["cover"] = f"/recitales/{venue_slug}/{show_slug}/featured{ext}"
    return page


# ------------------------------------------------------------------ principal


def looks_like_image(path: Path) -> bool:
    """Chequeo barato por los bytes mágicos: Hugo hace .Resize() del flyer en
    las páginas de banda, y si el archivo no es una imagen de verdad el build
    se cae recién al final, con un error medio críptico."""
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return False
    if head.startswith(b"\xff\xd8\xff"):
        return True  # jpeg
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return True  # png
    if head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        return True
    if head.startswith((b"GIF87a", b"GIF89a")):
        return True
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return True  # avif / heic
    return False


def resolve_image(folder: Path, name: str) -> Path | None:
    direct = folder / name
    if direct.is_file():
        return direct
    for p in folder.iterdir():
        if p.is_file() and p.name.lower() == name.lower():
            return p
    return None


def find_featured(info: dict, folder: Path) -> Path | None:
    name = get_str(info, "featured", "flyer", "afiche", "poster")
    if name:
        p = resolve_image(folder, name)
        if p is None:
            die(f"el flyer '{name}' no está en {folder}")
        if not looks_like_image(p):
            die(
                f"'{p.name}' no parece una imagen (no tiene cabecera de JPEG, PNG, "
                "WEBP, GIF ni AVIF). Si está corrupto o renombrado, el build de "
                "Hugo se cae al hacer el resize."
            )
        return p
    # Si no se indica, se busca un único candidato razonable.
    cands = [
        p
        for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTS
        and re.search(r"(flyer|afiche|poster|cover|imagen)", p.name, re.I)
    ]
    cands = [p for p in cands if looks_like_image(p)]
    return cands[0] if len(cands) == 1 else None


def default_folder() -> Path:
    """La carpeta de los masters: la del script si tiene el recital.txt, si no
    la de trabajo. Correr el script desde la carpeta de los masters es lo
    normal, pero también se puede correr desde el repo con --dir."""
    for base in (HERE, Path.cwd()):
        for name in INFO_NAMES:
            if (base / name).is_file():
                return base
    return HERE


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sube un recital a archive.org y abre la entrada en el sitio.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dir", help="carpeta con los masters (default: la de este archivo)")
    ap.add_argument("--info", help="archivo de info (default: recital.txt en la carpeta)")
    ap.add_argument("--repo", help="repo del sitio (default: se busca hacia arriba)")
    ap.add_argument("--dry-run", action="store_true", help="planifica y no toca nada")
    ap.add_argument("--init", action="store_true", help="escribe un recital.txt de ejemplo")
    ap.add_argument("--skip-upload", action="store_true", help="el item ya está subido")
    ap.add_argument(
        "--add-files",
        action="store_true",
        help="agregar pistas a un item que ya existe en archive.org",
    )
    ap.add_argument("--update", action="store_true", help="el show ya está en el catálogo")
    ap.add_argument("--build", action="store_true", help="corre hugo al final")
    ap.add_argument("--wait", type=int, default=30, help="minutos de espera por los derivados")
    args = ap.parse_args()

    folder = Path(args.dir).expanduser().resolve() if args.dir else default_folder()
    if not folder.is_dir():
        die(f"no existe la carpeta {folder}")

    if args.init:
        dest = folder / "recital.txt"
        if dest.exists():
            die(f"{dest} ya existe, no lo piso.")
        dest.write_text(INFO_TEMPLATE, encoding="utf-8")
        say(f"escribí {dest}. Completalo y corré el script otra vez.")
        return

    info_path = find_info(args.info, folder)
    info = load_info(info_path)
    repo = find_repo(args.repo)

    title = get_str(info, "title", "evento", "event")
    venue = get_str(info, "venue", "space", "espacio", "sala")
    date = get_str(info, "date", "fecha")
    if not title or not venue or not date:
        die(f"{info_path.name}: falta 'title', 'venue' o 'date'.")
    try:
        dt.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        die(f"{info_path.name}: 'date' tiene que ser AAAA-MM-DD (va '{date}').")

    slug_show = get_str(info, "slug") or slug(title)
    show_id = f"{slug(venue)}/{slug_show}"
    # El identificador del item sigue la convención de los que ya están:
    # live-<fecha>-<nombre del evento>. El slug de la página es otra cosa
    # (festimaga5 sin guion), así que no se usa para esto.
    identifier = get_str(info, "identifier") or f"live-{date}-{slug(title)}"
    page_title = title if norm(venue) in norm(title) else f"{title} en {venue}"

    say(f"info    : {info_path}")
    say(f"carpeta : {folder}")
    say(f"repo    : {repo}")
    say(f"evento  : {title} | {venue} | {date}")
    say(f"show id : {show_id}")
    say(f"item    : {identifier}")

    plan = build_plan(info, folder, required=not args.skip_upload)
    bands = get_list(info, "bands", "bandas")
    if not bands:
        seen: list[str] = []
        for t in plan:
            if t["band"] not in seen:
                seen.append(t["band"])
        bands = seen
    if not bands:
        say("AVISO: no hay bandas en el recital.txt. El catálogo queda sin bandas.")

    if plan:
        total = sum(t["src"].stat().st_size for t in plan)
        say(f"\n{len(plan)} pistas, {human_size(total)} en total:")
        for t in plan:
            say(f"  {t['index']:02d}  {t['src'].name}  ->  {t['band']}")
    else:
        say("\npistas: las toma del item de archive.org (--skip-upload).")

    meta = {
        "title": f"{page_title} ({date})",
        "creator": get_str(info, "creator") or DEFAULT_CREATOR,
        "date": date,
        "venue": venue,
        "coverage": get_str(info, "coverage") or DEFAULT_COVERAGE,
        "description": get_str(info, "description")
        or f"Grabación en vivo de {title} en {venue} el día {date}.",
        "mediatype": get_str(info, "mediatype") or DEFAULT_MEDIATYPE,
        "collection": get_str(info, "collection") or DEFAULT_COLLECTION,
    }
    extra = info.get("metadata")
    if isinstance(extra, dict):
        for k, v in extra.items():
            meta.setdefault(str(k), str(v))

    featured = find_featured(info, folder)
    if featured:
        say(f"flyer   : {featured.name}")
    else:
        say("flyer   : (ninguno) la página va a quedar fuera del archivo de /flyers/")

    # Al agregar pistas a un item que ya existe, la numeración sigue desde el
    # final: los nombres de archivo que ya están no se tocan.
    if args.add_files:
        if not item_exists(identifier):
            die(
                f"el item '{identifier}' no existe en archive.org.\n"
                "Para un recital nuevo no usés --add-files: corré sin él."
            )
        start = existing_track_count(identifier)
        say(f"\n--add-files: el item ya tiene {start} pistas; las nuevas siguen desde {start + 1}.")
        for t in plan:
            t["index"] = start + t["index"]

    if args.dry_run:
        say("\n--dry-run: no se sube nada ni se escribe nada.")
        say("\nQuedaría así:")
        say(f"  item   : {identifier}")
        for k, v in meta.items():
            say(f"    {k}: {v}")
        for t in plan:
            say(
                f"    archivo: {t['index']:02d} - {t['band']} - {title} "
                f"({date}){t['src'].suffix.lower()}"
            )
        if not plan:
            say("    (los archivos salen del item de archive.org)")
        say(f"  show   : {show_id}")
        say(f"  página : content/recitales/{slug(venue)}/{slug_show}/index.md")
        return

    # --- subida -------------------------------------------------------------
    if args.skip_upload:
        say("\n--skip-upload: el item se toma como ya subido.")
        if not item_exists(identifier):
            say(f"  ojo: no encontré el item '{identifier}' en archive.org.")
    elif args.add_files:
        # El item ya está en archive.org y lo que hay que hacer es agregarle
        # pistas. La numeración ya viene corrida desde el final.
        staged = stage_files(plan, title, date)
        try:
            # Sin metadata: el item ya la tiene y no hay que pisarla.
            upload_item(identifier, staged, {})
            wait_for_derivatives(identifier, [p.name for p in staged], args.wait * 60)
        finally:
            if staged:
                shutil.rmtree(staged[0].parent, ignore_errors=True)
    else:
        if item_exists(identifier):
            die(
                f"el item '{identifier}' ya existe en archive.org.\n"
                "Si querés agregarle pistas, usá --add-files.\n"
                "Si el item ya está bien armado y sólo falta la entrada del "
                "catálogo, usá --skip-upload (eso NO sube archivos)."
            )
        staged = stage_files(plan, title, date)
        try:
            upload_item(identifier, staged, meta)
            wait_for_derivatives(identifier, [p.name for p in staged], args.wait * 60)
        finally:
            if staged:
                shutil.rmtree(staged[0].parent, ignore_errors=True)

    # --- catálogo -----------------------------------------------------------
    venue_slug, show_slug = show_id.split("/", 1)
    show = {
        "id": show_id,
        "date": date,
        "title": page_title,
        "tracks": [],
        # 'space' es un texto, no una lista: el matcher de sync-archive.py lo
        # normaliza con norm(), que sólo acepta strings.
        "space": venue,
        "bands": bands,
        "page": f"/recitales/{venue_slug}/{show_slug}/",
    }
    upsert_show(repo, show, args.update or args.add_files)
    say(f"\ncatálogo: agregué {show_id} a data/shows.yml")

    run_sync(repo, show_id)
    show = get_show(repo, show_id) or show
    tracks = show.get("tracks") or []
    if not tracks:
        say(
            "\nEl sync no encontró el item para este show.\n"
            "Suele ser la fecha: el item tiene que tener la misma que el catálogo.\n"
            f"  item    : {identifier}\n"
            f"  catálogo: {date}\n"
            "Si el item tiene otra fecha, se arregla con una entrada en OVERRIDES\n"
            "dentro de scripts/sync-archive.py."
        )
    else:
        say(f"\ncatálogo: {len(tracks)} tracks cargados")

    # --- página -------------------------------------------------------------
    page = write_page(repo, show, featured, venue)
    if show.get("cover"):
        # el cover se define recién con la página: hay que persistirlo
        shows, header = load_shows(repo)
        for s in shows:
            if s.get("id") == show_id:
                s["cover"] = show["cover"]
        save_shows(repo, shows, header)
        say(f"flyer   : {show['cover']}")

    if args.build:
        if not shutil.which("hugo"):
            say("\n--build: no está el binario de hugo, me salto la verificación.")
        else:
            say("\n$ hugo --minify --gc")
            res = subprocess.run(
                ["hugo", "--minify", "--gc"], cwd=repo, capture_output=True, text=True
            )
            out = (res.stdout or "") + (res.stderr or "")
            for line in out.splitlines():
                if "WARN" in line or "ERROR" in line:
                    say("  " + line.strip())
            say(f"  hugo terminó con código {res.returncode}")

    say("\nListo. Revisá el diff:")
    say(f"  cd {repo} && git diff --stat")


if __name__ == "__main__":
    main()
