#!/usr/bin/env python3
"""Rewrite the recital pages so they stop carrying audio URLs.

Every {{< audio src="..." >}}, its "[Link directo]" line and its
"[Streaming en formato WAV]" link are replaced by a single
{{< track "<show>" "<track>" >}} call, which renders from data/shows.yml.
The Internet Archive item link is refreshed from the same file.

After this runs, editing data/shows.yml updates both players and every page,
which is the whole point: the URL lives in one place.

Matching a page's audio tag to a track uses the section heading, then a
normalised comparison against track ids, then position. Anything it cannot
place confidently is left untouched and reported.

Usage:
    python3 scripts/migrate-pages.py              # dry run, prints a diff
    python3 scripts/migrate-pages.py --write      # rewrite the pages
    python3 scripts/migrate-pages.py --show mad-monky   # one page
"""

from __future__ import annotations

import argparse
import difflib
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
SHOWS = ROOT / "data" / "shows.yml"

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
AUDIO_RE = re.compile(r'^\s*\{\{<+\s*audio\b.*$')
TRACK_RE = re.compile(r'^\s*\{\{<+\s*track\s+show="([^"]*)"\s+track="([^"]*)"')
LINK_DIRECT_RE = re.compile(r"^\s*\[\s*(Link directo|Enlace directo|Descargar)[^\]]*\]\([^)]*\)\s*$", re.I)
STREAM_RE = re.compile(r"^\s*\[\s*[^\]]*(WAV|FLAC|Streaming|Descarga)[^\]]*\]\([^)]*\)\s*$", re.I)
IA_LINK_RE = re.compile(r"^\s*\[\s*[^\]]*Internet Archive[^\]]*\]\([^)]*\)\s*$", re.I)
IA_LABEL_RE = re.compile(r"^\s*\[\s*([^\]]*)\]")
HEADING_RE = re.compile(r"^(\s*)(#{1,6})\s+(.*?)\s*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
ANY_URL_RE = re.compile(r"https?://[^\s)\"']+")
# Hosts that only ever serve audio downloads, so a link to one of them next to
# a player is always redundant once the shortcode renders it.
#
# dropbox.com stays here even though Dropbox is gone from the site: this
# classifies links in historical recital content, and old pages still carry
# dropbox audio links that the player now supersedes. Removing it would make the
# script leave those links in place.
AUDIO_HOSTS = ("pixeldrain.com", "files.catbox.moe", "archive.org",
               "dropbox.com", "/audio/")


def is_audio_link(line: str) -> bool:
    """A standalone markdown link to a downloadable audio file."""
    if not (LINK_DIRECT_RE.match(line) or STREAM_RE.match(line)):
        return False
    url = ANY_URL_RE.search(line)
    return bool(url) and any(h in url.group(0) for h in AUDIO_HOSTS)


def swallow_links(lines: list[str], i: int) -> int:
    """Index of the first line after the block of audio download links.

    Blank lines *between* links go, but the blank run that ends the block is
    kept: dropping it would leave `---` glued to the previous line, which
    markdown reads as a setext heading instead of a rule.
    """
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    while i < len(lines) and is_audio_link(lines[i]):
        i += 1
        j = i
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j < len(lines) and is_audio_link(lines[j]):
            i = j
            continue
        break
    return i


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "").replace("’", "")
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def heading_label(heading: str) -> str:
    """The band/label a heading refers to.

    A heading is usually `[Catango Trio](instagram)`, so prefer the link text;
    otherwise drop a trailing "(extracto)" style qualifier.
    """
    links = LINK_RE.findall(heading)
    if links:
        return re.sub(r"\s+", " ", links[0]).strip()
    return re.sub(r"\s*\([^)]*\)\s*", " ", heading).strip(" .")


def words(s: str) -> set[str]:
    """Significant words of a label, accents folded, for fuzzy comparison."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return {w for w in re.split(r"[^a-z0-9]+", s) if len(w) >= 4}


def pick_track(label: str, tracks: list[dict], used: set[str]) -> dict | None:
    """Resolve a heading to one of the show's tracks."""
    nl = norm(label)
    if not nl:
        return None
    free = [t for t in tracks if t["id"] not in used]
    for t in free:  # exact id, or the label slugged the same way
        if slug(label) == t["id"] or nl == norm(t["id"]):
            return t
    for t in free:
        if norm(t.get("artist")) == nl or norm(t.get("title")) == nl:
            return t
    for t in free:  # containment either way
        for field in ("artist", "title"):
            nf = norm(t.get(field) or "")
            if nf and (nf in nl or nl in nf):
                return t
    # Finally, shared words: pages say "Facu Dovidio" where the file says
    # "Facundo Dovidio", and "Interludio de Ele" where the file says
    # "02 Ele Corr Interludio".
    lw = words(label)
    if lw:
        scored = []
        for t in free:
            tw = words(f"{t['id']} {t.get('artist') or ''} {t.get('title') or ''}")
            scored.append((len(lw & tw), t))
        scored.sort(key=lambda x: -x[0])
        if scored and scored[0][0] > 0:
            if len(scored) == 1 or scored[0][0] > scored[1][0]:
                return scored[0][1]
    # Last resort: close spellings, e.g. a page heading "Sabotaje" for a file
    # named "Sabotage".
    scored = sorted(
        ((difflib.SequenceMatcher(None, nl, norm(t["id"])).ratio(), t) for t in free),
        key=lambda x: -x[0],
    )
    if scored and scored[0][0] >= 0.82:
        if len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.05:
            return scored[0][1]
    return None


def migrate(path: Path, shows_by_id: dict, report: list) -> str | None:
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return None
    rel = path.relative_to(CONTENT)
    show_id = "/".join(rel.parts[:-1])
    show = shows_by_id.get(show_id)
    if show is None:
        report.append((show_id, "no show in data/shows.yml, page left alone"))
        return None

    fm, body = m.group(1), text[m.end():]
    tracks = show.get("tracks") or []
    if not tracks:
        report.append((show_id, "no tracks in the catalogue, page left alone"))
        return None

    out, used, heading = [], set(), ""
    i, changed = 0, False
    lines = body.splitlines()

    # Tracks already rendered by a previous run count as used. Without this a
    # page that is half-migrated looks untouched, and the "render every file"
    # fallback below would re-emit players the page already has.
    for line in lines:
        tm = TRACK_RE.match(line)
        if tm and tm.group(1) == show_id:
            used.add(tm.group(2))
    while i < len(lines):
        line = lines[i]
        hm = HEADING_RE.match(line)
        if hm:
            text_of = hm.group(3)
            # Only a top level heading names the act. Pages often put a note
            # under the band ("### (the recorder was on the roof)") and that
            # must not become the track label.
            if len(hm.group(2)) <= 2:
                heading = text_of
            out.append(line)
            i += 1
            continue

        if AUDIO_RE.match(line):
            label = heading_label(heading)
            track = pick_track(label, tracks, used)
            if track is None and len(tracks) == 1 and not used:
                track = tracks[0]
            if track is None and used and len(used) >= len(tracks):
                # Every file already has a player on this page, so this audio
                # tag is something the catalogue does not describe (a catbox /
                # pixeldrain recording, usually). Re-emitting the tracks here
                # would duplicate the ones above; leave the tag as it is.
                report.append(
                    (show_id, f"heading {label!r} matches no track and all "
                              f"{len(tracks)} file(s) already have a player; "
                              f"audio tag left alone")
                )
                out.append(line)
                i += 1
                continue
            if track is None and not used:
                # The page's sections don't line up with the archive at all
                # (a whole night recorded as one blob upstream, split per song
                # in the item). Emit every file, one player each.
                report.append((show_id, f"heading {label!r} matches no track; "
                                        f"rendering all {len(tracks)} files"))
                changed = True
                for t in tracks:
                    out.append(f'{{{{< track show="{show_id}" track="{t["id"]}" >}}}}')
                    out.append("")
                    used.add(t["id"])
                i += 1
                i = swallow_links(lines, i)
                continue
            if track is None:
                report.append(
                    (show_id, f"could not match heading {label!r} to a track; "
                              f"available: {[t['id'] for t in tracks]}")
                )
                out.append(line)
                i += 1
                continue
            used.add(track["id"])
            changed = True
            call = f'{{{{< track show="{show_id}" track="{track["id"]}"'
            suffix = "(extracto)" if "(extracto" in heading.lower() else ""
            if suffix:
                call += f' label="{suffix}"'
            call += " >}}"
            out.append(call)
            i += 1
            i = swallow_links(lines, i)
            continue

        if IA_LINK_RE.match(line):
            # Only repair a bare link. A suffixed label ("... - Día 2") is
            # hand-written and points at a different item: a page can carry
            # more than one show, and this script only knows the one whose id
            # matches its path, so rewriting those would lose them.
            lm = IA_LABEL_RE.match(line)
            label = lm.group(1).strip() if lm else ""
            if show.get("archive_url") and label == "Artículo en Internet Archive":
                out.append(
                    f'## [Artículo en Internet Archive]({show["archive_url"]})'
                )
                changed = True
                i += 1
                continue

        out.append(line)
        i += 1

    # Every show on archive.org should link to its item; almost no page had one.
    if show.get("archive_url") and not any(IA_LINK_RE.match(l) for l in out):
        while out and out[-1].strip() == "":
            out.pop()
        out.extend(["", f'## [Artículo en Internet Archive]({show["archive_url"]})', ""])
        changed = True

    # Files in the item that the page never had a section for (the music school
    # page is one continuous recording; archive.org has it split per song).
    # The user asked for one player per file, so give them one each.
    leftovers = [t for t in tracks if t["id"] not in used]
    if leftovers and any(used):
        out.extend(["", "---", ""])
        for t in leftovers:
            out.append(f'{{{{< track show="{show_id}" track="{t["id"]}" >}}}}')
            out.append("")

    new_body = "\n".join(out)
    # body already carries the newline(s) that followed the closing '---', so
    # do not add another one here.
    new_text = f"---\n{fm}\n---" + new_body
    if text.endswith("\n") and not new_text.endswith("\n"):
        new_text += "\n"
    return new_text if new_text != text else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--show", help="only this show id")
    ap.add_argument("--diff", action="store_true", help="print a unified diff per page")
    args = ap.parse_args()

    shows = yaml.safe_load(SHOWS.read_text(encoding="utf-8")) or []
    shows_by_id = {s["id"]: s for s in shows if isinstance(s, dict) and s.get("id")}

    report: list[tuple[str, str]] = []
    updates: list[tuple[Path, str, str]] = []

    for path in sorted(CONTENT.rglob("index.md")):
        rel = path.relative_to(CONTENT)
        show_id = "/".join(rel.parts[:-1])
        if args.show and show_id != args.show:
            continue
        new = migrate(path, shows_by_id, report)
        if new:
            updates.append((path, path.read_text(encoding="utf-8"), new))

    print(f"{len(updates)} page(s) would change")
    if report:
        print("\nnotes:")
        for sid, note in report:
            print(f"  {sid}: {note}")

    residual = []
    for path, _old, new in updates:
        stale = [
            u for u in ANY_URL_RE.findall(new)
            if any(h in u for h in ("catbox", "pixeldrain"))
            and path.suffix.lower() not in (".jpg", ".png")
            and not re.search(r"\.(jpe?g|png|gif|webp|svg)$", u, re.I)
        ]
        if stale:
            residual.append((path, stale))
    if residual:
        print(f"\n{len(residual)} page(s) still point at catbox/pixeldrain audio:")
        for path, urls in residual:
            print(f"  {path.relative_to(ROOT)}  ({len(urls)})")

    if args.diff:
        for path, old, new in updates:
            print("\n".join(difflib.unified_diff(
                old.splitlines(), new.splitlines(),
                f"a/{path.relative_to(ROOT)}", f"b/{path.relative_to(ROOT)}",
                lineterm="", n=1,
            )))

    if not args.write:
        print("\n(dry run - pass --write to rewrite the pages)")
        return

    for path, _old, new in updates:
        path.write_text(new, encoding="utf-8")
    print(f"\nrewrote {len(updates)} page(s)")


if __name__ == "__main__":
    main()