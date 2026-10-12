#!/usr/bin/env python3
"""Fill in the `duration` of every track in data/shows.yml that is missing one.

archive.org already reports lengths, so this only has real work to do for the
handful of shows that are not on archive.org yet (their files still live on
catbox) and for tracks whose length the archive did not carry.

Usage:  python3 scripts/get-durations.py [--force] [--concurrency=2]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SHOWS = ROOT / "data" / "shows.yml"


def track_url(show: dict, track: dict) -> str | None:
    """The playable URL: the archive.org file if any, else the legacy URL."""
    if track.get("mp3"):
        return f"https://archive.org/download/{show['archive']}/{track['mp3']}"
    return track.get("src")


def probe(url: str) -> float | None:
    target = url if url.startswith("http") else str(ROOT / "static" / url.lstrip("/"))
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", target],
            capture_output=True, text=True, timeout=60, check=True,
        ).stdout.strip()
        secs = round(float(out))
        return secs if secs > 0 else None
    except Exception as exc:  # noqa: BLE001
        print(f"  failed {url}: {exc}")
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-probe known durations")
    ap.add_argument("--concurrency", type=int, default=2)
    args = ap.parse_args()

    header, _, _ = SHOWS.read_text(encoding="utf-8").partition("- id:")
    shows = yaml.safe_load(SHOWS.read_text(encoding="utf-8")) or []

    jobs = []
    for show in shows:
        if not show.get("archive"):
            continue
        for track in show["tracks"]:
            if track.get("duration") and not args.force:
                continue
            url = track_url(show, track)
            if url:
                jobs.append((show, track, url))

    print(f"probing {len(jobs)} track(s) with concurrency {args.concurrency}")
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        results = list(pool.map(lambda j: probe(j[2]), jobs))

    for (show, track, url), secs in zip(jobs, results):
        if secs:
            track["duration"] = secs
            done += 1
            print(f"  {secs:>6}s  {show['id']}#{track['id']}")

    if done:
        SHOWS.write_text(
            header + yaml.safe_dump(shows, sort_keys=False, allow_unicode=True,
                                    default_flow_style=False, width=10000),
            encoding="utf-8",
        )
    print(f"\nset {done} duration(s) in {SHOWS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()