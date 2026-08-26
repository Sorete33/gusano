#!/bin/bash
# Optimizes pepe emojis in-place
# Resizes to max 128px (displayed at ~48px) and compresses
# Requires: ImageMagick (convert/magick)
# Usage: bash scripts/optimize-pepe.sh

PEPE_DIR="static/pepe"
MAX_SIZE=128
QUALITY=60

if ! command -v magick &>/dev/null && ! command -v convert &>/dev/null; then
  echo "Error: install ImageMagick"
  exit 1
fi

converted=0
total=0
skipped=0

find "$PEPE_DIR" -type f \( -iname "*.png" -o -iname "*.gif" \) | while read -r img; do
  total=$((total + 1))

  basename=$(basename "$img")

  size_before=$(stat -c%s "$img" 2>/dev/null || stat -f%z "$img" 2>/dev/null)
  size_before_kb=$((size_before / 1024))

  if [ "$size_before_kb" -lt 10 ]; then
    skipped=$((skipped + 1))
    continue
  fi

  tmp="${img}.tmp"

  cmd="magick"
  if ! command -v magick &>/dev/null; then
    cmd="convert"
  fi

  if [[ "${basename,,}" == *.gif ]]; then
    $cmd "${img}[0]" -resize "${MAX_SIZE}x${MAX_SIZE}" -quality "$QUALITY" "$tmp" 2>/dev/null
  else
    $cmd "$img" -resize "${MAX_SIZE}x${MAX_SIZE}" -strip -quality "$QUALITY" "$tmp" 2>/dev/null
  fi

  if [ -f "$tmp" ]; then
    size_after=$(stat -c%s "$tmp" 2>/dev/null || stat -f%z "$tmp" 2>/dev/null)
    size_after_kb=$((size_after / 1024))
    if [ "$size_after_kb" -lt "$size_before_kb" ]; then
      mv "$tmp" "$img"
      echo "OPTIMIZED: $basename (${size_before_kb}KB -> ${size_after_kb}KB)"
      converted=$((converted + 1))
    else
      rm -f "$tmp"
    fi
  fi
done

echo ""
echo "Done: $converted optimized out of checked files"
