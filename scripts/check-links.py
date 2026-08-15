#!/usr/bin/env python3
"""Check the site's music links and cover images for breakage.

Scans static/js/music.js, data/playlist.yml, data/flyers-viejos.yml and the
recital content pages, then:
  - HEAD-checks external URLs (catbox.moe, audiogusano.neocities.org, ...)
  - verifies local paths exist (static/, content page bundles, public/)

Usage: python3 scripts/check-links.py [--local-dir static] [--no-external]
"""
import argparse
import concurrent.futures as cf
import os
import re
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXTERNAL_HOSTS = ("files.catbox.moe", "audiogusano.neocities.org", "open.spotify.com",
                  "music.youtube.com", "youtu.be", "www.youtube.com", "youtube.com",
                  "bandcamp.com", ".bandcamp.com", "agustinlayus.bandcamp.com",
                  "www.instagram.com", "dropbox.com", "www.dropbox.com")


def parse_music_js(local_dir):
    """Return (sources, images) referenced by the rocola player."""
    path = os.path.join(local_dir, "static", "js", "music.js")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "static", "js", "music.js")
    text = open(path, encoding="utf-8", errors="replace").read()
    srcs = re.findall(r'src\s*:\s*"([^"]+)"', text)
    imgs = re.findall(r'img\s*:\s*"([^"]+)"', text)
    return srcs, imgs


def parse_playlist_yml(local_dir):
    path = os.path.join(local_dir, "data", "playlist.yml")
    if not os.path.exists(path):
        path = os.path.join(ROOT, "data", "playlist.yml")
    text = open(path, encoding="utf-8").read()
    return re.findall(r'^\s*url\s*:\s*["\']?([^"\'\s]+)', text, re.M)


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
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 check-links"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return "ok"
    except urllib.error.HTTPError as e:
        return "http404" if e.code == 404 else f"http:{e.code}"
    except Exception:
        return "unreachable"


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
    ap.add_argument("--no-external", action="store_true", help="skip network HEAD checks")
    ap.add_argument("--max-workers", type=int, default=12)
    args = ap.parse_args()
    local = args.local_dir

    srcs, imgs = parse_music_js(local)
    playlist = parse_playlist_yml(local)
    flyers_new = parse_flyers_yml(local, "flyers.yml")
    flyers_old = parse_flyers_yml(local, "flyers-viejos.yml")
    content_audio = parse_content_audio(local)

    external = {}
    for u in list(srcs) + playlist + content_audio:
        if is_external(u) and any(h in u for h in EXTERNAL_HOSTS):
            external.setdefault(u, 0)
    external = list(external)

    dead_audio = []
    unreachable = []
    if external and not args.no_external:
        with cf.ThreadPoolExecutor(max_workers=args.max_workers) as ex:
            results = list(ex.map(lambda u: (u, head_status(u)), external))
        dead_audio = [u for u, st in results if st == "http404"]
        unreachable = [u for u, st in results if st == "unreachable"]

    missing_local_audio = sorted({u for u in srcs + content_audio if u.startswith("/") and not local_exists(local, u)})
    missing_covers = sorted({p for p in imgs if not local_exists(local, p)})
    missing_flyers = sorted({p for p in flyers_new + flyers_old if not local_exists(local, p)})

    print("=== DEAD EXTERNAL AUDIO (HTTP 404) ===")
    for u in dead_audio:
        print(f"  {u}")
    print(f"({len(dead_audio)}/{len(external)} external URLs confirmed 404)")

    if unreachable:
        print("\n=== EXTERNAL AUDIO UNREACHABLE (network blocked / timeout — re-run elsewhere) ===")
        for u in unreachable[:20]:
            print(f"  {u}")
        print(f"({len(unreachable)} unreachable, not confirmed dead)")

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
