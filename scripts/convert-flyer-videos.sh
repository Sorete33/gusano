#!/bin/bash
# Converts flyer videos to animated WebP and removes the originals.
#
# Why: Neocities' free tier only accepts a whitelist of extensions, and .mp4 is
# not on it. deploy-to-neocities silently drops unsupported types before
# uploading, so the .mp4 kept serving from an old supporter-tier upload while any
# edit to it silently failed to deploy. .webp IS allowed, and animated WebP
# autoplays and loops in an <img> exactly like the muted inline <video> the
# gallery used, so the gallery shortcodes need no change.
#
# The gallery cards are 300px wide, so 480px is plenty for the card; the
# lightbox is a little softer than the mp4 was, which is the trade.
#
# Requires: ffmpeg built with libwebp_anim (checked below).
# Usage: bash scripts/convert-flyer-videos.sh [--keep-source]

set -uo pipefail

MAX_WIDTH=480
FPS=12
QUALITY=50

KEEP_SOURCE=false
[ "${1:-}" = "--keep-source" ] && KEEP_SOURCE=true

# Directories Hugo copies through verbatim into the deploy.
SEARCH_DIRS=(static/covers static/images/gallery)

if ! command -v ffmpeg &>/dev/null; then
    echo "Error: ffmpeg not found"
    exit 1
fi

# ffmpeg prints its encoder table on stderr, not stdout, so 2>&1 is load-bearing.
# Capture to a file rather than piping: `grep -q` exits the moment it matches,
# ffmpeg dies on SIGPIPE (141), and with `set -o pipefail` that 141 becomes the
# pipeline's status -- so a piped check reports "no encoder" on a perfectly good
# ffmpeg.
encoders_dump=$(ffmpeg -hide_banner -encoders 2>&1)
if ! grep -q libwebp_anim <<<"$encoders_dump"; then
    echo "Error: this ffmpeg has no libwebp_anim encoder (need a full build)"
    exit 1
fi

# Collector: .mp4 plus the other video containers Neocities also rejects, so a
# .mov or .webm someone drops in gets caught by the same script.
shopt -s nullglob
sources=()
for dir in "${SEARCH_DIRS[@]}"; do
    [ -d "$dir" ] || continue
    for ext in mp4 m4v mov webm; do
        for f in "$dir"/*."$ext" "$dir"/*."${ext^^}"; do
            [ -f "$f" ] && sources+=("$f")
        done
    done
done
shopt -u nullglob

if [ ${#sources[@]} -eq 0 ]; then
    echo "Nothing to convert -- no video files in: ${SEARCH_DIRS[*]}"
    exit 0
fi

converted=0
failed=0

for src in "${sources[@]}"; do
    base="${src%.*}"
    dst="${base}.webp"

    if [ -f "$dst" ]; then
        echo "SKIP (webp already exists): $src"
        continue
    fi

    size_before=$(stat -c%s "$src" 2>/dev/null || stat -f%z "$src" 2>/dev/null)

    # -vf ... scale keeps the aspect ratio (the -2 makes ffmpeg round the height
    # to even, which webp needs). -an drops the audio track: the gallery played
    # these muted and looping anyway, so it was never used.
    if ffmpeg -y -v error -i "$src" \
        -vf "fps=${FPS},scale=${MAX_WIDTH}:-2:flags=lanczos" \
        -loop 0 -c:v libwebp_anim \
        -lossless 0 -q:v "$QUALITY" -compression_level 6 -preset picture \
        -an "$dst" 2>/tmp/ffmpeg-webp-$$.log
    then
        size_after=$(stat -c%s "$dst" 2>/dev/null || stat -f%z "$dst" 2>/dev/null)
        pct=$(( 100 - (size_after * 100 / size_before) ))
        printf "CONVERTED: %s (%dKB -> %dKB, -%d%%)\n" \
            "$src" $((size_before / 1024)) $((size_after / 1024)) "$pct"

        if [ "$KEEP_SOURCE" = false ]; then
            rm "$src"
        fi
        converted=$((converted + 1))
    else
        echo "FAILED: $src"
        cat /tmp/ffmpeg-webp-$$.log
        failed=$((failed + 1))
    fi
    rm -f /tmp/ffmpeg-webp-$$.log
done

echo ""
if [ "$failed" -gt 0 ]; then
    echo "Done: $converted converted, $failed FAILED (sources left in place)"
    exit 1
fi

echo "Done: $converted converted"

if [ "$KEEP_SOURCE" = true ]; then
    echo "Sources kept (--keep-source). Delete them once you have checked the webp."
fi

cat <<'EOF'

Next: update any data/*.yml that pointed at the .mp4, e.g.
    data/flyers-viejos.yml:
      - name: "kuelgue"
        link: "/covers/kuelgue.mp4"     ->  "/covers/kuelgue.webp"

then rebuild and confirm with:
    hugo --minify --gc --cleanDestinationDir
    python3 scripts/check-neocities-types.py public
EOF