#!/usr/bin/env python3
"""Fill data/shows.yml with the real archive.org links.

Fetches the items of the audiogusano Internet Archive collection, matches each
show in data/shows.yml to its item, and rewrites the track list from the files
that item actually contains.

This script only reads archive.org. To upload a new show and open its entry
in the catalogue in one go, use scripts/upload-recital.py, which calls this
one once the item is on archive.org.

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
    python3 scripts/sync-archive.py --refresh  # ignore the /tmp cache

--write refuses to run if any existing track would be dropped, because the
matcher keys on artist name and two tracks sharing an artist collide. Pass
--allow-drop once you have read the list and agree with it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
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
# How long a cached archive.org response stays usable. archive.org derives
# mp3/flac derivatives in the background, so a listing cached before that
# finishes reports an item as having no mp3 and the matcher rewrites the show
# to .wav. Six hours is short enough to avoid that in normal use.
CACHE_TTL = 6 * 3600
FETCH_ATTEMPTS = 3

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
    # Three shows whose IA item carries a date the catalogue does not, so the
    # date match finds nothing. Each file's length matches the catalogue's.
    # The catalogue dates are the correct ones - do not "fix" these towards the
    # item. Only festimaga3 was wrong, and it is in DATE_FIXES below.
    "la-maga/festimaga3": "live-2025-11-02-festimaga-3",
    "club-racing/eruca": "live-2026-03-08-eruca-sativa",  # catalogue: 2026-05-08
    "casa-fratello/armand": "live-2025-03-27-armando-alonso",  # catalogue: 2025-04-26
    # Page front matter said 2026-03-20; the show was actually the 19th.
    "beertonic/armand2": "live-2026-03-19-armando-alonso",
    # The page covers "Día 1" of a three day event; dia 2 is a different take.
    # Both items carry the same date, so neither resolves by date alone.
    "el-portal-del-tango/nueva-musica": "live-2025-12-03-muestra-de-fin-de-ao-dia-1",
    "el-portal-del-tango/nueva-musica-dia-2": "live-2025-12-03-muestra-de-fin-de-ao-dia-2",
    # The page spells the venue "Plaza Charo Latessa" and the band "Valkirias";
    # the item says "Latesa" and its file says "Valquirias", so exact venue and
    # band matching both miss.
    "plaza-charo/valquirias": "live-2025-11-08-12va-marcha-del-orgullo",
}

# Front matter dates that are known to be off by a day.
DATE_FIXES = {
    "beertonic/armand2": "2026-03-19",
    # Page front matter and heading said 2025-11-28; the archive filenames all
    # say 2025-11-25. The item's own `date` field says 2025-11-02, which is
    # wrong too - the show was the 25th.
    "la-maga/festimaga3": "2025-11-25",
}

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


def fetch(url: str, max_age: int = CACHE_TTL) -> dict:
    """GET a JSON endpoint, caching it briefly.

    archive.org derives mp3/flac in the background, so a cached listing taken
    before the derivatives existed reports an item as having no mp3. The TTL
    is short for that reason; --refresh sets max_age to 0.

    archive.org also intermittently answers with an empty payload. Retrying is
    what makes a run reproducible: a single empty response used to look
    exactly like "this item has no files", which silently zeroed a show.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (urllib.parse.quote(url, safe="")[:180] + ".json")
    if key.exists() and time.time() - key.stat().st_mtime < max_age:
        return json.loads(key.read_text(encoding="utf-8"))
    req = urllib.request.Request(url, headers={"User-Agent": "sync-archive/1.0"})
    last: Exception | None = None
    for attempt in range(FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            key.write_text(json.dumps(data), encoding="utf-8")
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{url}: gave up after {FETCH_ATTEMPTS} attempts ({last})")


def list_items(max_age: int = CACHE_TTL) -> dict[str, dict]:
    data = fetch(SEARCH.format(uploader=urllib.parse.quote(UPLOADER)), max_age)
    out = {}
    for doc in data["response"]["docs"]:
        doc["d"] = (doc.get("date") or "")[:10]
        out[doc["identifier"]] = doc
    return out


def item_tracks(ident: str, max_age: int = CACHE_TTL) -> list[dict]:
    """One entry per recording: group derivatives by `original`, pick a format."""
    meta = fetch(f"https://archive.org/metadata/{ident}", max_age)
    files = meta.get("files") or []
    if not files:
        # archive.org has been seen to answer with an empty payload for an item
        # that plainly has files. Treat that as an error so the show is reported
        # unresolved and left alone, never rewritten to zero tracks.
        raise RuntimeError(
            f"{ident}: archive.org returned no file list "
            f"(item may be private, or the response was empty)"
        )
    groups: dict[str, dict] = {}
    order: list[str] = []
    for f in files:
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
    """IA writes length as '1854' or '1854.61' on originals but '30:54' on mp3
    derivatives. All three forms have to be accepted: a wav-only item has no
    mp3 to fall back on, so a missed decimal here silently drops the duration.
    """
    for f in meta.get("files", []):
        if f.get("name") != name:
            continue
        v = str(f.get("length") or "")
        if v.isdigit():
            return int(v)
        if ":" in v:
            parts = [int(x) for x in v.split(":")]
            return sum(p * 60**i for i, p in enumerate(reversed(parts)))
        try:
            return round(float(v))
        except ValueError:
            return None
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


def ranked_variants(*values: str) -> list[str]:
    """Normalized forms of each value, most specific first, de-duplicated.

    Same forms as variants(), but as an ordered list and across several values
    at once. Callers look these up in sequence and take the first hit, so the
    order has to be stable: iterating a set here let Python's per-process hash
    seed decide which track matched, and a re-run could drop a different one.
    """
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        candidates = [norm(value)]
        trimmed = re.sub(r"\s+(en|-)\s+.*$", "", value).strip()
        if trimmed and trimmed != value:
            candidates.append(norm(trimmed))
        for key in candidates:
            if key and key not in seen:
                seen.add(key)
                out.append(key)
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


def build_tracks(show: dict, ident: str, tracks: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """Rebuild a show's track list from the item's files, keeping old ids.

    Old tracks are matched to files one by one so that the wording already in
    the page survives; old tracks with no counterpart in the item are dropped
    and reported rather than silently kept.

    Returns (tracks, notes, drops). `drops` is what lets the caller refuse a
    destructive --write.

    Matching has to be deterministic: two tracks by the same artist both want
    the artist key, and resolving that by set iteration order made a re-run
    drop a different track each time. So a key claimed by more than one track is
    marked ambiguous and never used - the precise title keys are unambiguous and
    still find the right track - and candidates are tried in a fixed order.
    """
    old = show.get("tracks") or []
    by_norm: dict[str, dict] = {}
    shared: set[str] = set()
    for t in old:
        for key in variants(t.get("artist") or "") | variants(t.get("title") or ""):
            if by_norm.setdefault(key, t) is not t:
                shared.add(key)

    notes: list[str] = []
    used_ids: set[str] = set()
    consumed: set[int] = set()
    out = []
    for t in tracks:
        artist = artist_for(t["base"], show)
        prev = None
        # Most specific first: the whole filename, then the filename without
        # its venue tail, then the artist. Skipping contested keys and tracks
        # already taken keeps one old track from being claimed twice.
        for key in ranked_variants(t["base"], artist):
            if key in shared or key not in by_norm:
                continue
            cand = by_norm[key]
            if id(cand) in consumed:
                continue
            prev = cand
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
        # Same for the artist. Re-deriving it from the filename both loses the
        # distinction between two tracks by one band - "Traumas de la Infancia"
        # and "Traumas de la Infancia Reunión" both reduce to the former - and
        # makes the next run unable to tell them apart again.
        entry_artist = (prev.get("artist") or artist) if prev is not None else artist

        entry = {"id": tid, "artist": entry_artist, "title": label}
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

    drops: list[str] = []
    for t in old:
        if id(t) not in consumed:
            have = ", ".join(k for k in ("mp3", "flac", "wav", "src") if t.get(k))
            name = t.get("title") or t.get("id")
            drops.append(name)
            notes.append(
                f"  dropped '{name}'"
                f" (has: {have or 'no audio file'}) - no matching file in {ident}"
            )

    return out, notes, drops


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", help="only this show id")
    ap.add_argument(
        "--allow-drop", action="store_true",
        help="write even though some existing tracks would be dropped",
    )
    ap.add_argument(
        "--refresh", action="store_true",
        help="ignore the cached archive.org responses and refetch everything",
    )
    args = ap.parse_args()

    max_age = 0 if args.refresh else CACHE_TTL
    shows = yaml.safe_load(SHOWS.read_text(encoding="utf-8")) or []
    items = list_items(max_age)
    print(f"shows: {len(shows)}   IA items: {len(items)}\n")

    matched, unresolved, skipped = [], [], []
    untouched = []
    would_drop: list[str] = []
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
            tracks = item_tracks(ident, max_age)
        except Exception as exc:  # noqa: BLE001
            unresolved.append((show["id"], f"metadata failed: {exc}"))
            untouched.append(show)
            continue
        new_tracks, notes, drops = build_tracks(show, ident, tracks)
        for d in drops:
            would_drop.append(f"{show['id']}: {d}")
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

    # Only matched shows get rebuilt. Reporting just those made a clean run
    # look like 15 tracks had gone missing.
    rebuilt = sum(len(s.get("tracks") or []) for s in matched)
    kept = sum(len(s.get("tracks") or []) for s in untouched)
    print(f"\nmatched   : {len(matched)}")
    print(f"tracks    : {rebuilt} rebuilt + {kept} left as-is = {rebuilt + kept}")
    print(f"unresolved: {len(unresolved)}")
    for sid, reason in unresolved:
        print(f"  {sid}: {reason}")

    if not args.write:
        print("\n(dry run - pass --write to update data/shows.yml)")
        return

    if would_drop and not args.allow_drop:
        print(
            f"\nrefusing to write: {len(would_drop)} track(s) would be dropped.",
            file=sys.stderr,
        )
        for d in would_drop:
            print(f"  {d}", file=sys.stderr)
        print(
            "\nThis is usually the matcher, not archive.org: tracks that share an "
            "artist name collide.\nRe-run with --allow-drop if the drops are "
            "really ones you want gone.",
            file=sys.stderr,
        )
        sys.exit(1)

    shows = matched + untouched + skipped
    shows.sort(key=lambda s: (s.get("date") or "", s["id"]), reverse=True)
    header = SHOWS.read_text(encoding="utf-8").split("- id:")[0]
    body = yaml.safe_dump(shows, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=10000)
    SHOWS.write_text(header + body, encoding="utf-8")
    print(f"\nwrote {SHOWS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()