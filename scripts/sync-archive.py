#!/usr/bin/env python3
"""Fill data/shows.yml with the real archive.org links.

Fetches the items of the audiogusano Internet Archive collection, matches each
show in data/shows.yml to its item, and rewrites the track list from the files
that item actually contains.

Matching, in order:
  1. exact date + the item's `venue` metadata
  2. exact date + band names found in the item's filenames
  3. exact date + band names found in the item title
  4. OVERRIDES below (hand-resolved, see comments)
Anything that does not resolve is reported and left alone.

Track files are grouped by their `original` field, which is what ties
`01 - X.flac` / `01 - X.mp3` / `01 - X.wav` to one recording. Per group the
playable format is mp3 > flac > wav. Items are sometimes missing an mp3
derivative, so wav is a real fallback, not a theoretical one.

Usage:
    python3 scripts/sync-archive.py            # dry run, prints a report
    python3 scripts/sync-archive.py --write    # rewrite data/shows.yml
    python3 scripts/sync-archive.py --show sala-biaus/epi-amy   # one show
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SHOWS = ROOT / "data" / "shows.yml"
CACHE = Path("/tmp/opencode/ia-cache")

# The collection owner. Change this if the uploads ever move to another account.
UPLOADER = "escalofrioexistencial@tuta.io"
SEARCH = (
    "https://archive.org/advancedsearch.php"
    "?q=uploader%3A%22{uploader}%22"
    "&fl%5B%5D=identifier&fl%5B%5D=date&fl%5B%5D=title"
    "&rows=400&page=1&output=json"
)

# Shows the automatic matcher cannot settle. Keyed by show id in data/shows.yml.
OVERRIDES = {
    # The page records a 2025-11-08 show at Club La Pampa whose IA item is
    # labelled "Festival Cebada" with venue "Festival Cebada".
    "club-la-pampa/epifanicas": "live-2025-11-08-festival-cebada",
    # Page front matter said 2026-03-20; the show was actually the 19th.
    "beertonic/armand2": "live-2026-03-19-armando-alonso",
    # The page covers "Día 1" of a three day event; dia 2 is a different take.
    "el-portal-del-tango/nueva-musica": "live-2025-12-03-muestra-de-fin-de-ao-dia-1",
    # The page spells the venue "Plaza Charo Latessa" and the band "Valkirias";
    # the item says "Latesa" and its file says "Valquirias", so exact venue and
    # band matching both miss.
    "plaza-charo/valquirias": "live-2025-11-08-12va-marcha-del-orgullo",
}

# Front matter dates that are known to be off by a day.
DATE_FIXES = {"beertonic/armand2": "2026-03-19"}

TRACK_RE = re.compile(r"^(?:\d+\s*[-–]\s*)?(.+?)\s*(?:\((\d{4}-\d{2}-\d{2})\))?$")
AUDIO_EXT = ("mp3", "flac", "wav")
FORMATS = {"mp3": "audio/mpeg", "flac": "audio/flac", "wav": "audio/wav"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "track"


def encode(name: str) -> str:
    """Percent-encode a filename for use in a URL path."""
    return urllib.parse.quote(name, safe="()!*-._~")


def fetch(url: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (urllib.parse.quote(url, safe="")[:180] + ".json")
    if key.exists():
        return json.loads(key.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": "sync-archive/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    key.write_text(json.dumps(data), encoding="utf-8")
    return data


def list_items() -> dict[str, dict]:
    data = fetch(SEARCH.format(uploader=urllib.parse.quote(UPLOADER)))
    out = {}
    for doc in data["response"]["docs"]:
        doc["d"] = (doc.get("date") or "")[:10]
        out[doc["identifier"]] = doc
    return out


def item_tracks(ident: str) -> list[dict]:
    """One entry per recording: group derivatives by `original`, pick a format."""
    meta = fetch(f"https://archive.org/metadata/{ident}")
    groups: dict[str, dict] = {}
    order: list[str] = []
    for f in meta.get("files", []):
        name = f.get("name") or ""
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in AUDIO_EXT:
            continue
        key = f.get("original") or name
        if key not in groups:
            groups[key] = {}
            order.append(key)
        # Keep the first file seen for a format (later ones are duplicates).
        groups[key].setdefault(ext, name)
        if ext == "wav" and f.get("length") and str(f["length"]).isdigit():
            groups[key]["_sec"] = int(f["length"])

    out = []
    for key in order:
        g = groups[key]
        fmt = next((e for e in AUDIO_EXT if e in g), None)
        if not fmt:
            continue
        raw = g[fmt]
        m = TRACK_RE.match(raw.rsplit(".", 1)[0])
        base = m.group(1).strip() if m else raw
        secs = g.get("_sec")
        if not secs and fmt in g:
            secs = parse_len(meta, g[fmt])
        entry = {
            "base": base,
            "fmt": fmt,
            "file": encode(raw),
            "seconds": secs,
        }
        # Keep the lossless originals around for the download link.
        for extra in ("flac", "wav"):
            if extra in g:
                entry[extra] = encode(g[extra])
        out.append(entry)
    return out


def parse_len(meta: dict, name: str) -> int | None:
    """IA writes length as '1854' on originals but '30:54' on mp3 derivatives."""
    for f in meta.get("files", []):
        if f.get("name") != name:
            continue
        v = str(f.get("length") or "")
        if v.isdigit():
            return int(v)
        if ":" in v:
            parts = [int(x) for x in v.split(":")]
            return sum(p * 60**i for i, p in enumerate(reversed(parts)))
    return None


def pick_item(show: dict, items: dict[str, dict]) -> tuple[str | None, str]:
    """Return (identifier, reason). identifier is None when unresolved."""
    sid = show["id"]
    if sid in OVERRIDES:
        return OVERRIDES[sid], "override"

    date = DATE_FIXES.get(sid, show.get("date") or "")
    cands = [it for it in items.values() if it["d"] == date]
    if not cands:
        return None, "no item on that date"
    if len(cands) == 1:
        return next(iter(cands))["identifier"], "unique date"

    bands = {norm(b): b for b in show.get("bands") or []}
    space = norm(show.get("space") or "")
    scored = []
    for it in cands:
        venue = norm(it.get("title", ""))
        if space and (space in venue or venue in space):
            s = 3
        else:
            s = 0
        hits = sum(1 for b in bands if b in venue)
        s += hits
        scored.append((s, hits, it["identifier"]))
    scored.sort(reverse=True)

    top = scored[0]
    runner = scored[1] if len(scored) > 1 else (0, 0, "")
    if top[0] > runner[0]:
        return top[2], f"date + score {top[0]} vs {runner[0]}"
    if top[1] == 0 and not space:
        return None, f"ambiguous between {top[2]} and {runner[2]}"
    return None, f"ambiguous between {top[2]} and {runner[2]}"


def variants(s: str) -> set[str]:
    """Normalized forms of a label: as written, and without a venue tail.

    playlist.yml titles read "Rey Midas en Club Conjura" while the IA filename
    is just "Rey Midas", so both forms have to be indexed.
    """
    out = set()
    if not s:
        return out
    n = norm(s)
    if n:
        out.add(n)
    trimmed = re.sub(r"\s+(en|-)\s+.*$", "", s).strip()
    if trimmed and trimmed != s:
        nt = norm(trimmed)
        if nt:
            out.add(nt)
    return out


def artist_for(base: str, show: dict) -> str:
    """Prefer a band name from the page's `bandas` over the raw filename.

    IA filenames often end in the venue ("Casco y Guada en Grey Bar"), which is
    already known from the show, so try the base with that tail removed before
    falling back to a substring match.
    """
    bands = show.get("bands") or []
    nb = norm(base)
    for b in bands:
        if nb == norm(b):
            return b
    trimmed = re.sub(r"\s+(en|-)\s+.*$", "", base).strip()
    for b in bands:
        if norm(trimmed) == norm(b):
            return b
    hits = [b for b in bands if norm(b) and norm(b) in nb]
    if hits:
        return max(hits, key=lambda b: len(norm(b)))
    return trimmed or base


def build_tracks(show: dict, ident: str, tracks: list[dict]) -> tuple[list[dict], list[str]]:
    """Rebuild a show's track list from the item's files, keeping old ids.

    Old tracks are matched to files one by one so that the wording already in
    the page survives; old tracks with no counterpart in the item are dropped
    and reported rather than silently kept.
    """
    old = show.get("tracks") or []
    by_norm: dict[str, dict] = {}
    for t in old:
        for key in variants(t.get("artist") or "") | variants(t.get("title") or ""):
            by_norm.setdefault(key, t)

    notes: list[str] = []
    used_ids: set[str] = set()
    consumed: set[int] = set()
    out = []
    for t in tracks:
        artist = artist_for(t["base"], show)
        prev = None
        for key in variants(artist) | variants(t["base"]):
            if key in by_norm:
                prev = by_norm[key]
                break
        if prev is not None:
            consumed.add(id(prev))
        base_id = slug(artist) if prev is None else (prev.get("id") or slug(artist))
        tid, n = base_id, 2
        while tid in used_ids:
            tid, n = f"{base_id}-{n}", n + 1
        used_ids.add(tid)

        label = t["base"]
        if prev and prev.get("title"):
            label = prev["title"]  # keep the page's / player's own wording

        entry = {"id": tid, "artist": artist, "title": label}
        if t["fmt"] == "mp3":
            entry["mp3"] = t["file"]
        else:
            # A handful of items have no mp3 derivative; `mp3` would be a lie.
            entry["src"] = t["file"]
            entry["fmt"] = t["fmt"]
            notes.append(f"  {tid}: no mp3 in item, using .{t['fmt']}")
        for extra in ("flac", "wav"):
            if t.get(extra):
                entry[extra] = t[extra]
        if t.get("seconds"):
            entry["duration"] = t["seconds"]
        out.append(entry)

    for t in old:
        if id(t) not in consumed:
            notes.append(
                f"  dropped '{t.get('title') or t.get('id')}'"
                f" ({t.get('src', 'no src')}) - no matching file in {ident}"
            )

    return out, notes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", help="only this show id")
    args = ap.parse_args()

    shows = yaml.safe_load(SHOWS.read_text(encoding="utf-8")) or []
    items = list_items()
    print(f"shows: {len(shows)}   IA items: {len(items)}\n")

    matched, unresolved, skipped = [], [], []
    untouched = []
    for show in shows:
        if args.show and show["id"] != args.show:
            skipped.append(show)
            continue
        ident, reason = pick_item(show, items)
        if not ident:
            unresolved.append((show["id"], reason))
            untouched.append(show)  # keep the show exactly as it was
            continue
        try:
            tracks = item_tracks(ident)
        except Exception as exc:  # noqa: BLE001
            unresolved.append((show["id"], f"metadata failed: {exc}"))
            untouched.append(show)
            continue
        new_tracks, notes = build_tracks(show, ident, tracks)
        old = len(show.get("tracks") or [])
        if old != len(new_tracks):
            note = "MORE" if len(new_tracks) > old else "FEWER"
            print(f"~ {show['id']}: {old} -> {len(new_tracks)} tracks ({note})")
        for n in notes:
            print(n)
        show["archive"] = ident
        show["archive_url"] = f"https://archive.org/details/{ident}"
        if DATE_FIXES.get(show["id"]):
            show["date"] = DATE_FIXES[show["id"]]
        show["tracks"] = new_tracks
        matched.append(show)

    total = sum(len(s.get("tracks") or []) for s in matched)
    print(f"\nmatched   : {len(matched)}")
    print(f"tracks    : {total}")
    print(f"unresolved: {len(unresolved)}")
    for sid, reason in unresolved:
        print(f"  {sid}: {reason}")

    if not args.write:
        print("\n(dry run - pass --write to update data/shows.yml)")
        return

    shows = matched + untouched + skipped
    shows.sort(key=lambda s: (s.get("date") or "", s["id"]), reverse=True)
    header = SHOWS.read_text(encoding="utf-8").split("- id:")[0]
    body = yaml.safe_dump(shows, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=10000)
    SHOWS.write_text(header + body, encoding="utf-8")
    print(f"\nwrote {SHOWS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()