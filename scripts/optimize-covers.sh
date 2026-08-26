#!/bin/bash
# Optimizes cover images in static/covers/ in-place
# Compresses PNGs/JPGs without changing filenames
# Requires: ImageMagick (convert/magick) or cwebp
# Usage: bash scripts/optimize-covers.sh

COVERS_DIR="static/covers"
QUALITY=80
MAX_WIDTH=800

if ! command -v magick &>/dev/null && ! command -v convert &>/dev/null; then
  echo "Error: install ImageMagick"
  exit 1
fi

converted=0
skipped=0

for img in "$COVERS_DIR"/*.{jpg,jpeg,png,JPG,JPEG,PNG}; do
  [ -f "$img" ] || continue

  basename=$(basename "$img")
  ext="${basename##*.}"
  name="${basename%.*}"
  tmp="${img}.tmp"

  size_before=$(stat -c%s "$img" 2>/dev/null || stat -f%z "$img" 2>/dev/null)
  size_before_kb=$((size_before / 1024))

  if [ "$size_before_kb" -lt 80 ]; then
    echo "SKIP (small ${size_before_kb}KB): $basename"
    skipped=$((skipped + 1))
    continue
  fi

  cmd="magick"
  if ! command -v magick &>/dev/null; then
    cmd="convert"
  fi

  if [[ "${ext,,}" == "png" ]]; then
    $cmd "$img" -resize "${MAX_WIDTH}>" -strip -quality "$QUALITY" "$tmp" 2>/dev/null
  else
    $cmd "$img" -resize "${MAX_WIDTH}>" -strip -quality "$QUALITY" "$tmp" 2>/dev/null
  fi

  if [ -f "$tmp" ]; then
    size_after=$(stat -c%s "$tmp" 2>/dev/null || stat -f%z "$tmp" 2>/dev/null)
    size_after_kb=$((size_after / 1024))
    mv "$tmp" "$img"
    echo "OPTIMIZED: $basename (${size_before_kb}KB -> ${size_after_kb}KB)"
    converted=$((converted + 1))
  fi
done

echo ""
echo "Done: $converted optimized, $skipped skipped"
