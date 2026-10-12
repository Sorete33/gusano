#!/usr/bin/env python3
"""Check the site's music links and cover images for breakage.

Scans data/shows.yml (the single catalogue both players read), the flyer data
and the recital content pages, then:
  - classifies files.catbox.moe links WITHOUT touching the network when
    possible, by cross-referencing the `duration` recorded on each track
    (sync-archive.py only records one when archive.org reports a length for
     that file, so a catbox track missing a duration is unconfirmed);
  - throttled ranged-GETs the catbox URLs the durations can't cover
    (serialized >= --catbox-interval apart, with a circuit breaker that backs
    off when catbox refuses connections, to avoid rate-limit bans);
  - HEAD-checks archive.org URLs only when --check-archive is passed, since
    there are ~170 of them and they are stable;
  - HEAD-checks other external hosts (spotify, youtube, ...);
  - verifies local paths exist (static/, content page bundles, public/)

Usage: python3 scripts/check-links.py [--offline] [--check-archive]
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
import urllib.request
import urllib.error

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UA = "Mozilla/5.0 check-links"

EXTERNAL_HOSTS = ("files.catbox.moe", "audiogusano.neocities.org", "open.spotify.com",
                  "music.youtube.com", "youtu.be", "www.youtube.com", "youtube.com",
                  "bandcamp.com", ".bandcamp.com", "agustinlayus.bandcamp.com",
                  "www.instagram.com", "dropbox.com", "www.dropbox.com")


def parse_shows_yml(local_dir):
    """data/shows.yml -> (sources, images, durations).

    This is the one catalogue both players read, so it is also the one place a
    dead audio link can show up. A track's playable URL is its archive.org file
    when it has one, otherwise the legacy full URL in `src`.
    """
    path = os.path.join(local_dir, "data", "shows.yml")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "data", "shows.yml")
    shows = yaml.safe_load(open(path, encoding="utf-8")) or []
    srcs, imgs, durations = [], [], {}
    for show in shows:
        if not isinstance(show, dict):
            continue
        if show.get("cover"):
            imgs.append(show["cover"])
        for track in show.get("tracks") or []:
            if track.get("mp3") and show.get("archive"):
                srcs.append(
                    "https://archive.org/download/%s/%s" % (show["archive"], track["mp3"])
                )
            elif track.get("src"):
                srcs.append(track["src"])
                # A duration only exists when archive.org reported a
                # length, so its absence means "dead or never confirmed".
                if track.get("duration"):
                    durations[track["src"]] = track["duration"]
    return srcs, imgs, durations


def parse_flyers_yml(local_dir, name):
    path = os.path.join(local_dir, "data", name)
    if not os.path.exists(path):
        path = os.path.join(ROOT, "data", name)
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    return re.findall(r'^\s*link\s*:\s*["\']?([^"\'\s]+)', text, re.M)


def parse_content_audio(local_dir):
    """All audio-ish URLs mentioned in recital pages."""
    urls = []
    base = os.path.join(local_dir, "content", "recitales")
    if not os.path.isdir(base):
        base = os.path.join(ROOT, "content", "recitales")
    pat = re.compile(r'https?://[^\s"\'\)\]]+\.(?:mp3|ogg|m4a|flac)')
    for dirpath, _dirs, files in os.walk(base):
        for fn in files:
            if fn.endswith((".md", ".markdown")):
                text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
                urls.extend(pat.findall(text))
    return urls


def is_external(url):
    low = url.lower()
    if low.startswith(("http://", "https://")):
        return True
    return False


def head_status(url, timeout=20):
    """Return "ok", "http404", "http:<code>" or "unreachable"."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return "ok"
    except urllib.error.HTTPError as e:
        return "http404" if e.code == 404 else f"http:{e.code}"
    except Exception:
        return "unreachable"


# --- catbox: throttled, ghost-404 aware, circuit-broken ----------------------
#
# files.catbox.moe returns a 200 HTML "not found" page (and 404 on ranged GET)
# for deleted files instead of a plain 404, so HEAD alone can't tell dead from
# live; we use a ranged GET and sniff the body. Catbox rate-limits aggressively
# (an earlier parallel scan got our IP banned), so requests are serialized
# (>= --catbox-interval apart, across all workers) and a global circuit breaker
# backs off when the host refuses connections, doubling 30s -> backoff_max.

_catbox_state_lock = threading.Lock()
_catbox_last_request = 0.0
_catbox_blocked_until = 0.0
_catbox_block_delay = 30.0


def is_html_body(head):
    """True if the first bytes of a body look like an HTML error page."""
    head = (head or b"").lstrip()[:1024].lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _catbox_request_interval(interval):
    """Serialize catbox requests and pause while the circuit breaker is open."""
    global _catbox_last_request
    while True:
        with _catbox_state_lock:
            now = time.monotonic()
            ready_at = max(_catbox_last_request + interval, _catbox_blocked_until)
            if now >= ready_at:
                _catbox_last_request = now
                return
            wait = min(ready_at - now, 5.0)
        time.sleep(wait)


def _catbox_reset_block():
    with _catbox_state_lock:
        _catbox_blocked_until = 0.0
        _catbox_block_delay = 30.0


def _catbox_trip(backoff_max):
    """Open the circuit breaker, doubling the wait up to backoff_max."""
    with _catbox_state_lock:
        delay = min(_catbox_block_delay, backoff_max)
        _catbox_block_delay = min(delay * 2, backoff_max)
        _catbox_blocked_until = time.monotonic() + delay
    return delay


def catbox_status(url, timeout=30, interval=1.0, backoff_max=300.0, max_attempts=2):
    """Classify a files.catbox.moe URL. Returns "ok", "dead", "empty" or
    "unreachable" ("empty" = zero-byte file, unplayable)."""
    for attempt in range(max_attempts):
        _catbox_request_interval(interval)
        req = urllib.request.Request(url, method="GET", headers={
            "User-Agent": UA,
            "Range": "bytes=0-1023",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read(1024)
                content_type = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            _catbox_reset_block()
            if e.code in (404, 410):
                return "dead"
            if e.code == 416:
                return "ok"
            if e.code >= 500 and attempt < max_attempts - 1:
                _catbox_trip(backoff_max)
                continue
            return f"http:{e.code}"
        except Exception:
            if attempt < max_attempts - 1:
                _catbox_trip(backoff_max)
                continue
            return "unreachable"
        _catbox_reset_block()
        if resp.status in (404, 410):
            return "dead"
        if resp.status == 416:
            return "ok"
        if is_html_body(data) or content_type.startswith("text/html"):
            return "dead"
        if not data:
            return "empty"
        return "ok"
    return "unreachable"


def external_status(url, catbox_interval=1.0, catbox_backoff_max=300.0):
    """HEAD-check normal hosts; throttled ranged-GET catbox (ghost-404 aware)."""
    if "files.catbox.moe" in url.lower():
        return catbox_status(url, interval=catbox_interval, backoff_max=catbox_backoff_max)
    return head_status(url)


def local_exists(local_dir, path):
    """Check a root-relative path like /covers/x.jpg against static/ and public/."""
    rel = path.lstrip("/")
    for base in ("static", "public", "content"):
        p = os.path.join(local_dir, base, rel)
        if os.path.exists(p):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local-dir", default=ROOT, help="repo root (default: this repo)")
    ap.add_argument("--no-external", action="store_true", help="skip network checks entirely")
    ap.add_argument("--offline", action="store_true",
                    help="no network: classify catbox links from the durations in shows.yml only")
    ap.add_argument("--check-archive", action="store_true",
                    help="also HEAD-check the ~170 archive.org URLs (slow)")
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--catbox-interval", type=float, default=1.0,
                    help="minimum seconds between catbox requests (rate-limit avoidance)")
    ap.add_argument("--catbox-backoff-max", type=float, default=300.0,
                    help="max circuit-breaker backoff for catbox, seconds")
    args = ap.parse_args()
    local = args.local_dir

    srcs, imgs, durations = parse_shows_yml(local)
    flyers_new = parse_flyers_yml(local, "flyers.yml")
    flyers_old = parse_flyers_yml(local, "flyers-viejos.yml")
    content_audio = parse_content_audio(local)
    playlist_set = set(srcs)

    external = {}
    for u in list(srcs) + content_audio:
        if not is_external(u):
            continue
        if not any(h in u for h in EXTERNAL_HOSTS):
            continue
        # ~170 archive.org URLs: stable, and slow to check, so opt in.
        if "archive.org" in u and not args.check_archive:
            continue
        external.setdefault(u, 0)
    external = list(external)

    offline_dead = []    # catbox, in playlist, no duration -> dead (offline signal)
    offline_live = []    # catbox with a recorded duration -> skipped network
    net_catbox = []      # catbox the durations file can't cover -> throttled GET
    net_other = []       # non-catbox external hosts -> HEAD
    for u in external:
        if "files.catbox.moe" in u.lower():
            if u in durations:
                offline_live.append(u)
            elif u in playlist_set:
                offline_dead.append(u)
            else:
                net_catbox.append(u)
        else:
            net_other.append(u)

    dead_audio = list(offline_dead)
    unreachable = []
    run_network = bool(external) and not (args.no_external or args.offline)
    if run_network:
        jobs = net_catbox + net_other
        if jobs:
            with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
                results = list(ex.map(lambda u: (
                    u,
                    external_status(u, args.catbox_interval, args.catbox_backoff_max),
                ), jobs))
            for u, st in results:
                if st in ("http404", "dead", "empty"):
                    dead_audio.append(u)
                elif st == "unreachable":
                    unreachable.append(u)

    missing_local_audio = sorted({u for u in srcs + content_audio if u.startswith("/") and not local_exists(local, u)})
    missing_covers = sorted({p for p in imgs if not local_exists(local, p)})
    missing_flyers = sorted({p for p in flyers_new + flyers_old if not local_exists(local, p)})

    print("=== DEAD EXTERNAL AUDIO ===")
    for u in dead_audio:
        print(f"  {u}")
    net_dead = len(dead_audio) - len(offline_dead)
    print(f"({len(dead_audio)}/{len(external)} external URLs dead"
          f"  [{len(offline_dead)} offline via shows.yml durations,"
          f" {net_dead} network-confirmed])")
    if offline_live:
        print(f"\n({len(offline_live)} catbox URLs have a duration in shows.yml — skipped network)")

    if unreachable:
        print("\n=== EXTERNAL AUDIO UNREACHABLE (network blocked / timeout) ===")
        for u in unreachable[:20]:
            print(f"  {u}")
        print(f"({len(unreachable)} unreachable, not confirmed dead)")

    skipped = net_catbox + net_other
    if skipped and not run_network:
        print("\n=== EXTERNAL URLS SKIPPED (network disabled) ===")
        for u in skipped[:30]:
            print(f"  {u}")
        print(f"({len(skipped)} skipped; playlist catbox links already classified offline)")

    print("\n=== LOCAL AUDIO NOT FOUND IN REPO ===")
    for u in missing_local_audio:
        print(f"  {u}")
    print(f"({len(missing_local_audio)})")

    print("\n=== COVER IMAGES MISSING ===")
    for p in missing_covers:
        print(f"  {p}")
    print(f"({len(missing_covers)}/{len(set(imgs))} unique covers missing)")

    print("\n=== FLYER LINKS MISSING ===")
    for p in missing_flyers:
        print(f"  {p}")
    print(f"({len(missing_flyers)})")

    total = len(dead_audio) + len(missing_local_audio) + len(missing_covers) + len(missing_flyers)
    print(f"\nTOTAL issues: {total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
