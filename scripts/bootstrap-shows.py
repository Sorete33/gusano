#!/usr/bin/env python3
"""One-shot migration: build data/shows.yml from the sources that duplicated each
other (content/recitales/**, static/js/music.js, data/playlist.yml).

data/shows.yml becomes the single catalogue that both players read.

Track ids are stable (slug of the artist/label) so data/show-durations.json keeps
its keys when a URL changes from catbox to archive.org.

Usage:  python3 scripts/bootstrap-shows.py [--write]
        (default is a dry run that only prints the drift report)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "recitales"
MUSIC_JS = ROOT / "static" / "js" / "music.js"
PLAYLIST = ROOT / "data" / "playlist.yml"
DURATIONS = ROOT / "data" / "playlist-durations.json"
OUT = ROOT / "data" / "shows.yml"

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
AUDIO_RE = re.compile(r'\{\{<+\s*audio\s+src="([^"]+)"')
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def norm(s: str) -> str:
    """Lowercase, strip accents and every non-alphanumeric char.

    Lets 'Guada y Abril dúo' match IA's 'Guada y Abril Duo' and
    "Paprika's Band" match 'Paprikas Band'.
    """
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "").replace("’", "")  # Paprika's -> paprikas
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "track"


def plain(s: str) -> str:
    """Markdown links -> their text; used for headings we reuse as titles."""
    s = LINK_RE.sub(r"\1", s or "")
    s = re.sub(r"[*_`]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def artist_from_heading(heading: str, spaces: list[str], bands: list[str],
                        title: str) -> str:
    """Work out which act a page heading is about.

    Headings routinely link both the band and the venue ("Mate Jazz en
    [Beertonic](...)"), so the first link is often the wrong one. Prefer a link
    that is not the venue, then the text leading the first link, then a band
    name that appears in the heading.
    """
    ns = {norm(s) for s in spaces if s and norm(s)}
    links = [plain(t) for t in LINK_RE.findall(heading)]
    for link in links:
        if norm(link) not in ns:
            return link

    if links:
        # Only venue links: keep whatever came before them.
        before = re.sub(r"\s+(en|de|del|para)\s*$", " ", heading.split("[", 1)[0])
        before = plain(before).strip(" .")
        if before:
            return before
    else:
        cleaned = re.sub(r"\s*\([^)]*\)\s*", " ", heading)
        cleaned = plain(cleaned).strip(" .")
        # Prose headings ("Bueno la maquinita se renego con bad seed, gracias")
        # are not labels; fall back to a band name the heading mentions.
        nh = norm(cleaned)
        hits = [b for b in bands if norm(b) and norm(b) in nh]
        if hits:
            return max(hits, key=lambda b: len(norm(b)))
        cleaned = re.sub(r"\s+(en|de|del)\s+.*$", "", cleaned).strip(" .")
        if cleaned and len(cleaned) <= 40:
            return cleaned
    return title or "desconocido"


def parse_front_matter(text: str) -> dict:
    m = FM_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        km = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not km:
            continue
        key, val = km.group(1), km.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [
                v.strip().strip("\"'")
                for v in val[1:-1].split(",")
                if v.strip()
            ]
        else:
            fm[key] = val.strip("\"'")
    return fm


def read_shows_from_content() -> list[dict]:
    """One show per content/recitales/<venue>/<show>/index.md.

    Tracks come from the <audio> shortcodes in document order; the artist/label
    is the nearest preceding heading (link text if the heading is a link).
    """
    shows = []
    for idx in sorted(CONTENT.rglob("index.md")):
        rel = idx.relative_to(CONTENT)
        # Two layouts exist: <venue>/<show>/index.md and, for a handful of
        # shows filed straight under a venue, <venue>/index.md.
        if rel.parts[-1] != "index.md" or len(rel.parts) not in (2, 3):
            continue
        if len(rel.parts) == 3:
            venue, show = rel.parts[0], rel.parts[1]
        else:
            venue, show = "", rel.parts[0]
        sid = f"{venue}/{show}" if venue else show
        text = idx.read_text(encoding="utf-8")
        fm = parse_front_matter(text)
        body = text[FM_RE.match(text).end():] if FM_RE.match(text) else text

        date = fm.get("date") or ""
        date = str(date)[:10]

        cover = ""
        coverdir = f"/recitales/{venue}/{show}" if venue else f"/recitales/{show}"
        for f in sorted(idx.parent.glob("featured.*")):
            cover = f"{coverdir}/{f.name}"
            break

        # Walk the body keeping the current heading, emit a track per audio tag.
        tracks = []
        heading = ""
        for line in body.splitlines():
            hm = HEADING_RE.match(line.strip())
            if hm:
                heading = hm.group(1).strip()
                continue
            am = AUDIO_RE.search(line)
            if am:
                label = plain(heading)
                artist = artist_from_heading(
                    heading,
                    fm.get("espacios") or [],
                    fm.get("bandas") or [],
                    plain(fm.get("title") or ""),
                )
                tracks.append({"artist": artist, "label": label, "src": am.group(1)})

        shows.append(
            {
                "id": sid,
                "date": date,
                "title": fm.get("title") or show,
                "space": (fm.get("espacios") or [""])[0] if isinstance(fm.get("espacios"), list) else fm.get("espacios", ""),
                "bands": fm.get("bandas") or [],
                "cover": cover,
                "page": f"{coverdir}/",
                "tracks": tracks,
            }
        )
    return shows


def read_songs_from_music_js(path: Path | None = None) -> list[dict]:
    """The hardcoded `songs` array in static/js/music.js.

    That array was removed once data/shows.yml existed, so a re-run needs the
    original:  git show HEAD:static/js/music.js > /tmp/legacy-music.js
    and pass --music-js /tmp/legacy-music.js
    """
    path = Path(path) if path else MUSIC_JS
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if "const songs = [" not in text:
        return []
    body = text.split("const songs = [", 1)[-1].split("\n];", 1)[0]
    songs = []
    for block in re.findall(r"\{(.*?)\}", body, re.S):
        entry = {}
        for key in ("title", "artist", "src", "img", "date"):
            m = re.search(rf'{key}:\s*"([^"]*)"', block)
            if m:
                entry[key] = m.group(1)
        if entry.get("src"):
            songs.append(entry)
    return songs


def read_playlist(path: Path | None = None) -> list[dict]:
    path = Path(path) if path else PLAYLIST
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [d for d in data if isinstance(d, dict) and d.get("url")]


def read_durations(path: Path | None = None) -> dict:
    path = Path(path) if path else DURATIONS
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def attach(shows: list[dict], songs: list[dict], playlist: list[dict],
           durations: dict) -> tuple[list[dict], dict]:
    """Fold the loose player entries into the shows they belong to.

    Match order per loose entry: exact src URL in a page -> cover path under
    /recitales/ -> date + artist/band. Whatever is left over becomes a
    synthetic show so nothing silently disappears.
    """
    by_url, by_img = {}, {}
    for sh in shows:
        for t in sh["tracks"]:
            by_url.setdefault(t["src"], sh)
        if sh["cover"]:
            by_img[sh["cover"]] = sh
    shows_by_id = {s["id"]: s for s in shows}
    orphans, used = [], set()

    def find(song: dict):
        if song.get("src") in by_url:
            return by_url[song["src"]]
        img = song.get("img") or ""
        if "/recitales/" in img:
            path = img.rsplit("/", 1)[0]
            key = path[len("/recitales/"):] if path.startswith("/recitales/") else path
            if key in shows_by_id:
                return shows_by_id[key]
        d = (song.get("date") or "")[:10]
        if d:
            artist = norm(song.get("artist") or "")
            # The band implied by the title, e.g. "Jane Doe en Rincón" -> Jane Doe.
            title = song.get("title") or ""
            tband = norm(title.split(" en ", 1)[0]) if " en " in title else ""
            cands = [s for s in shows if s["date"] == d]
            for s in cands:
                if artist and any(artist == norm(b) for b in s["bands"]):
                    return s
            # Only trust a unique date when the entry actually looks like it
            # belongs there: music.js carries a few wrong dates, and trusting
            # them silently files a track under the wrong show.
            if len(cands) == 1:
                s = cands[0]
                bands = {norm(b) for b in s["bands"]}
                if not artist and not tband:
                    return s
                if any(b in bands for b in (artist, tband) if b):
                    return s
                if any(b and b in (artist or tband) for b in bands):
                    return s
        # No usable date (playlist.yml carries none): parse "<Banda> en <Sala>"
        # out of the title and look for a show with that band at that venue.
        title = song.get("title") or ""
        band = norm(title.split(" en ", 1)[0])
        venue = norm(title.split(" en ", 1)[1]) if " en " in title else ""
        if band:
            hits = []
            for s in shows:
                if not any(norm(b) == band for b in s["bands"]):
                    continue
                if venue and not (
                    venue in norm(s["space"]) or norm(s["space"]) in venue
                ):
                    continue
                hits.append(s)
            if len(hits) == 1:
                return hits[0]
        return None

    for entry in songs + [{"src": p["url"], "title": p.get("title", "")} for p in playlist]:
        # music.js and playlist.yml overlap; first one wins.
        if entry.get("src") in used:
            continue
        # The page already owns this URL (152 of them) -> enrich that track
        # instead of adding a duplicate.
        if entry.get("src") in by_url:
            owner = by_url[entry["src"]]
            for t in owner["tracks"]:
                if t["src"] == entry["src"]:
                    # music.js / playlist.yml titles are already display ready,
                    # so they win over a raw page heading.
                    if entry.get("title"):
                        t["label"] = entry["title"]
                    if entry.get("artist") and not t.get("artist"):
                        t["artist"] = entry["artist"].strip()
                    if entry.get("img") and not owner["cover"]:
                        owner["cover"] = entry["img"]
                    break
            used.add(entry["src"])
            continue

        sh = find(entry)
        if sh is None:
            orphans.append(entry)
            continue
        used.add(entry.get("src"))
        sh["tracks"].append(
            {
                "artist": (entry.get("artist") or "").strip(),
                "label": entry.get("title") or "",
                "src": entry["src"],
                "cover": entry.get("img") or "",
            }
        )
        if entry.get("img") and not sh["cover"]:
            sh["cover"] = entry["img"]

    # Group leftovers under a single synthetic show. Empty date so it sorts last.
    for entry in orphans:
        d = ""
        sid = "sin-pagina/sin-asignar"
        sh = shows_by_id.get(sid)
        if sh is None:
            sh = {
                "id": sid, "date": d,
                "title": "Pistas sin show asignada (restos de playlist.yml)",
                "space": "", "bands": [], "cover": "", "page": "",
                "tracks": [], "synthetic": True,
            }
            shows.append(sh)
            shows_by_id[sid] = sh
        sh["tracks"].append(
            {
                "artist": (entry.get("artist") or "").strip(),
                "label": entry.get("title") or "",
                "src": entry["src"],
                "cover": entry.get("img") or "",
            }
        )

    # Adopt the richer title from music.js / playlist.yml when a page heading was
# only the band name. Matched by artist because the page's own src may point at
# a different recording (several pages do, which is why this data drifted).
    artist_titles, dated_titles = {}, {}
    for entry in songs + playlist:
        a = norm((entry.get("artist") or "").strip())
        t = entry.get("title") or ""
        if not (a and t) or t.strip() == a:
            continue
        artist_titles.setdefault(a, t)
        d = (entry.get("date") or "")[:10]
        if d:
            dated_titles.setdefault((d, a), t)
    adopted = 0
    for sh in shows:
        for t in sh["tracks"]:
            label = (t.get("label") or "").strip(" .")
            artist = (t.get("artist") or "").strip()
            if label and label != artist:
                continue
            # Prefer a title recorded for this exact date: band names repeat
            # across shows ("Corpo Porco en Sala Biaus" is a different night).
            rich = dated_titles.get(((sh.get("date") or "")[:10], norm(artist)))
            if not rich:
                rich = artist_titles.get(norm(artist))
            if rich:
                t["label"] = rich
                adopted += 1
    print(f"adopted titles from music.js/playlist: {adopted}")

    return shows, {"orphans": orphans, "used": used}


def finalise(shows: list[dict], durations: dict) -> dict:
    """Assign stable ids, carry durations over, drop empty tracks."""
    report = {
        "shows": len(shows), "tracks": 0, "no_duration": [],
        "synthetic_shows": [], "no_page": [], "per_track_cover": [],
    }
    out = []
    for sh in shows:
        if sh.get("synthetic"):
            report["synthetic_shows"].append(sh["id"])
        if not sh["page"]:
            report["no_page"].append(sh["id"])

        seen_ids, tracks = set(), []
        covers = set()
        for t in sh["tracks"]:
            src = t.get("src")
            if not src:
                continue
            base = slug(t.get("artist") or t.get("label") or "track")
            tid, n = base, 2
            while tid in seen_ids:
                tid, n = f"{base}-{n}", n + 1
            seen_ids.add(tid)

            artist = t.get("artist") or ""
            label = t.get("label") or ""
            if not label:
                label = f"{artist} en {sh['title']}" if artist else sh["title"]

            tr = {"id": tid, "artist": artist, "title": label, "src": src}
            dur = durations.get(src)
            if dur:
                tr["duration"] = int(dur)
            else:
                report["no_duration"].append(f"{sh['id']}#{tid}")
            if t.get("cover"):
                covers.add(t["cover"])
            tracks.append(tr)
            report["tracks"] += 1

        entry = {
            "id": sh["id"],
            "date": sh["date"],
            "title": sh["title"],
            "tracks": tracks,
        }
        for k in ("space", "bands", "cover", "page"):
            if sh.get(k):
                entry[k] = sh[k]
        if len(covers) > 1:
            report["per_track_cover"].append(sh["id"])
            for tr in tracks:
                pass  # per-track covers are rare; sh["cover"] below is enough
        out.append(entry)

    out.sort(key=lambda s: (s["date"], s["id"]), reverse=True)
    return {"shows": out, "report": report}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write data/shows.yml")
    ap.add_argument("--music-js", help="path to the legacy music.js (see read_songs_from_music_js)")
    ap.add_argument("--playlist", help="path to the legacy data/playlist.yml")
    ap.add_argument("--durations", help="path to the legacy data/playlist-durations.json")
    args = ap.parse_args()

    shows = read_shows_from_content()
    songs = read_songs_from_music_js(args.music_js)
    playlist = read_playlist(args.playlist)
    durations = read_durations(args.durations)

    print(f"content pages : {len(shows)}")
    print(f"music.js songs: {len(songs)}")
    print(f"playlist.yml  : {len(playlist)}")
    print(f"durations     : {len(durations)}")

    shows, extra = attach(shows, songs, playlist, durations)
    result = finalise(shows, durations)
    r = result["report"]

    print(f"\nshows         : {r['shows']}")
    print(f"tracks        : {r['tracks']}")
    print(f"no duration   : {len(r['no_duration'])}")
    print(f"synthetic     : {len(r['synthetic_shows'])} {r['synthetic_shows']}")
    print(f"no page       : {len(r['no_page'])} {r['no_page']}")
    print(f"multi-cover   : {len(r['per_track_cover'])} {r['per_track_cover']}")
    if r["no_duration"]:
        print("\ntracks still missing a duration:")
        for x in r["no_duration"]:
            print(f"  {x}")

    if not args.write:
        print("\n(dry run - pass --write to create data/shows.yml)")
        return

    header = (
        "# Catálogo único de recitales.\n"
        "# Generado por scripts/bootstrap-shows.py + scripts/sync-archive.py.\n"
        "#\n"
        "# Consumido por:\n"
        "#   layouts/partials/webamp.html   (winamp de la home)\n"
        "#   layouts/music.html             (rocola, inyecta window.shows)\n"
        "#   layouts/shortcodes/track.html  (players en las páginas de recital)\n"
        "#\n"
        "# Por pista:\n"
        "#   id       slug estable; es la clave en data/show-durations.json\n"
        "#   src      URL completa (catbox / pixeldrain legacy)\n"
        "#   mp3      nombre de archivo dentro del item de archive.org;\n"
        "#           se resuelve con `archive` -> https://archive.org/download/<archive>/<mp3>\n"
        "#   flac/wav descarga en alta calidad, mismo criterio\n"
        "#   duration segundos (lo rellena sync-archive.py desde la metadata de archive.org)\n"
        "# Si la pista tiene `mp3`, gana sobre `src`.\n"
    )
    body = yaml.safe_dump(
        result["shows"], sort_keys=False, allow_unicode=True,
        default_flow_style=False, width=10000,
    )
    OUT.write_text(header + body, encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(body.splitlines())} lines)")


if __name__ == "__main__":
    main()