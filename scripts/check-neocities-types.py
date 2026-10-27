#!/usr/bin/env python3
"""Fail the deploy if the built site contains files Neocities free tier refuses.

Why this exists: bcomnes/deploy-to-neocities filters unsupported extensions out
of the upload set locally, before it ever contacts Neocities. A .mp4 in static/
is therefore a *successful* deploy in which the file simply never reaches the
site -- it survives only because an earlier supporter-tier upload left a copy
there, and it stays frozen at that version forever since cleanup is off. Nothing
in the workflow output says so.

So catch it here, where it is still a build failure and a line of log.

ALLOWED below is the deploy action's own `supportedFiletypes` set (extracted
from dist/index.cjs), so this script predicts what will actually be uploaded
rather than what the docs claim.

--supporter turns the failure into a report. A Supporter account has no upload
whitelist on the Neocities side, and deploy.yml passes neocities_supporter:true
so the action stops filtering too, meaning these files DO reach the site. They
are still worth reporting, but failing the build over them would just be wrong.
The check stays around for the day the account downgrades.

Usage: python3 scripts/check-neocities-types.py [dir] [--supporter]
Exit 0 if clean (or, with --supporter, even with supporter-tier files present),
1 if a file would be silently dropped on the free tier.
"""
import os
import sys

# Verbatim from deploy-to-neocities dist/index.cjs -> supportedFiletypes.
ALLOWED = {
    ".apng", ".asc", ".atom", ".avif", ".bin", ".cjs", ".css", ".csv",
    ".dae", ".eot", ".epub", ".geojson", ".gif", ".glb", ".glsl", ".gltf",
    ".gpg", ".htm", ".html", ".ico", ".jpeg", ".jpg", ".js", ".json", ".jxl",
    ".key", ".kml", ".knowl", ".less", ".manifest", ".map", ".markdown", ".md",
    ".mf", ".mid", ".midi", ".mjs", ".mtl", ".obj", ".opml", ".osdx", ".otf",
    ".pdf", ".pgp", ".pls", ".png", ".py", ".rdf", ".resolveHandle", ".rss",
    ".sass", ".scss", ".sf2", ".svg", ".text", ".toml", ".ts", ".tsv", ".ttf",
    ".txt", ".webapp", ".webmanifest", ".webp", ".woff", ".woff2", ".xcf",
    ".xml", ".xsl", ".xslt", ".yaml", ".yml",
}

# Already on Neocities from when the account was Supporter tier, and load-bearing
# (layouts/partials/webamp.html points the Winamp player at all three skins).
# They keep serving, but any edit to them will never deploy -- the deploy action
# drops them before uploading. Warn, do not fail: failing would block every
# deploy over files that are working fine today.
FROZEN_OK = {".wsz"}

# Media that is both common and never allowed. Called out separately because
# these are what silently vanish: the gallery keeps pointing at them.
SUPPORTER_ONLY = {
    ".mp4", ".m4v", ".mov", ".webm", ".avi", ".mkv", ".flv",
    ".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac",
}

IGNORED_DIRS = {".git", ".github", "node_modules", "__pycache__"}

# Sanity check para cuentas premium: archivos > 5 MB y extensiones peligrosas.
DANGEROUS_EXTENSIONS = {".exe", ".sh", ".php", ".cgi", ".pl", ".py", ".bat", ".cmd"}
SIZE_THRESHOLD = 5 * 1024 * 1024


def human(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def scan(root):
    """Return (offenders, frozen) as lists of (relpath, ext, size)."""
    offenders, frozen = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in ALLOWED:
                continue
            full = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            entry = (os.path.relpath(full, root), ext or "(no extension)", size)
            (frozen if ext in FROZEN_OK else offenders).append(entry)
    return offenders, frozen


def main():
    args = sys.argv[1:]
    supporter = "--supporter" in args
    dirs = [a for a in args if not a.startswith("-")]
    root = dirs[0] if dirs else "public"

    if not os.path.isdir(root):
        print(f"Not a directory: {root}, skipping")
        return 0

    offenders, frozen = scan(root)

    # On Supporter the deploy action uploads .wsz like anything else, so the
    # "frozen forever" warning is no longer true. Silence it rather than
    # printing a claim that is wrong.
    if frozen and not supporter:
        print(f"ℹ️  {len(frozen)} frozen file(s) in {root}/ are live on Neocities but")
        print("   can no longer be updated (deploy-to-neocities drops them):")
        for path, ext, size in sorted(frozen, key=lambda o: -o[2]):
            print(f"     {path}  ({ext}, {human(size)})")
        print()

    if not offenders:
        print(f"✅ Every new file in {root}/ is deployable to Neocities free tier.")
        return 0

    supporters = [o for o in offenders if o[1] in SUPPORTER_ONLY]
    others = [o for o in offenders if o[1] not in SUPPORTER_ONLY]

    if supporter:
        # Premium: relajar. Solo sanity check: archivos peligrosos o muy grandes.
        dangerous = [o for o in offenders if o[1] in DANGEROUS_EXTENSIONS]
        huge = [o for o in offenders if o[2] > SIZE_THRESHOLD]
        if dangerous or huge:
            print(f"\nℹ️  Sanity check (premium): {len(dangerous) + len(huge)} archivo(s) a revisar.\n")
            if dangerous:
                print("   Extensiones peligrosas:")
                for path, ext, size in sorted(dangerous, key=lambda o: -o[2]):
                    print(f"     {path}  ({ext}, {human(size)})")
                print()
            if huge:
                print("   Archivos > 5 MB:")
                for path, ext, size in sorted(huge, key=lambda o: -o[2]):
                    print(f"     {path}  ({ext}, {human(size)})")
                print()
        else:
            print(f"\n✅ Premium: sin archivos peligrosos ni > 5 MB. ({len(offenders)} archivos supporter-only ignorados.)\n")
    else:
        print(f"\n❌ {len(offenders)} file(s) in {root}/ will NOT be uploaded to Neocities.")
        print("   deploy-to-neocities filters these out before uploading, so the deploy")
        print("   would succeed and the files would silently never appear on the site.\n")

    if (not supporter) and supporters:
        print("   Supporter-tier-only media (these are the ones that bite):")
        for path, ext, size in sorted(supporters, key=lambda o: -o[2]):
            print(f"     {path}  ({ext}, {human(size)})")
        print()

    if (not supporter) and others:
        print("   Other unsupported extensions:")
        for path, ext, size in sorted(others, key=lambda o: -o[2])[:40]:
            print(f"     {path}  ({ext}, {human(size)})")
        if len(others) > 40:
            print(f"     ...and {len(others) - 40} more")
        print()

    if supporter:
        print("   See https://neocities.org/site_files/allowed_types\n")
        return 0

    print("   Fix by converting to an allowed type (see")
    print("   scripts/convert-flyer-videos.sh for the video case), removing the file,")
    print("   or hosting the site somewhere without an extension whitelist.")
    print("   See https://neocities.org/site_files/allowed_types\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())