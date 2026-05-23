#!/usr/bin/env bash
# Export every .drawio file in this folder to png/<name>.png at 2x scale.
#
# Requires the drawio CLI:
#   macOS: brew install --cask drawio
#   Other: https://github.com/jgraph/drawio-desktop/releases
#
# Run from the diagrams/ directory:
#   bash _export_pngs.sh

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

if ! command -v drawio >/dev/null 2>&1; then
    echo "ERROR: drawio CLI not found. Install with: brew install --cask drawio"
    exit 1
fi

mkdir -p png

for f in *.drawio; do
    name="${f%.drawio}"
    drawio -x -f png -o "png/${name}.png" --scale 2 "$f" 2>&1 | tail -1
done

echo
echo "Exported $(ls png/*.png | wc -l | tr -d ' ') PNGs to png/"
