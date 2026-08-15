#!/usr/bin/env bash
# Optimize static/pepe emojis in place, keeping every filename and extension so
# existing comments and the picker manifest keep working.
set -euo pipefail

DIR="${1:-static/pepe}"

GIFS=$(find "$DIR" -iname '*.gif' -type f)
PNGS=$(find "$DIR" -iname '*.png' -type f)

GIF_COUNT=0; GIF_BEFORE=0; GIF_AFTER=0
PNG_COUNT=0; PNG_BEFORE=0; PNG_AFTER=0

if [ -n "$GIFS" ]; then
  for f in $GIFS; do
    s=$(stat -c%s "$f")
    GIF_BEFORE=$((GIF_BEFORE + s))
    gifsicle -O3 --lossy=80 "$f" -o "$f.tmp" && mv "$f.tmp" "$f"
    GIF_AFTER=$((GIF_AFTER + $(stat -c%s "$f")))
    GIF_COUNT=$((GIF_COUNT + 1))
  done
fi

if [ -n "$PNGS" ]; then
  for f in $PNGS; do
    s=$(stat -c%s "$f")
    PNG_BEFORE=$((PNG_BEFORE + s))
    pngquant --quality=60-80 --force --ext .png "$f"
    PNG_AFTER=$((PNG_AFTER + $(stat -c%s "$f")))
    PNG_COUNT=$((PNG_COUNT + 1))
  done
fi

echo "GIF: $GIF_COUNT files ${GIF_BEFORE} -> ${GIF_AFTER} bytes"
echo "PNG: $PNG_COUNT files ${PNG_BEFORE} -> ${PNG_AFTER} bytes"
