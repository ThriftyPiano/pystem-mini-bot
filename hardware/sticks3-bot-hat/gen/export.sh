#!/bin/bash
# Export fabrication outputs (gerbers, drill, placement, BOM) for JLCPCB.
# Produces ../fab/ with a ready-to-upload gerber zip.
set -e
cd "$(dirname "$0")"
CLI=~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
PCB=../sticks3-bot-hat.kicad_pcb
FAB=../fab
rm -rf "$FAB"
mkdir -p "$FAB/gerbers"

"$CLI" pcb export gerbers \
    --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --subtract-soldermask \
    -o "$FAB/gerbers/" "$PCB"
"$CLI" pcb export drill --format excellon --drill-origin absolute \
    --excellon-units mm --generate-map --map-format gerberx2 \
    -o "$FAB/gerbers/" "$PCB"
(cd "$FAB" && zip -qr sticks3-bot-hat-gerbers.zip gerbers)

# Pick & place (JLC wants: Designator, Mid X, Mid Y, Layer, Rotation)
"$CLI" pcb export pos --format csv --units mm --side both \
    -o "$FAB/positions.csv" "$PCB"

# BOM from design.py
python3 - <<'PYEOF'
import csv, sys, os
sys.path.insert(0, os.getcwd())
import design
with open("../fab/bom.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Part", "Manufacturer", "Package", "LCSC", "Note"])
    for row in design.BOM:
        w.writerow(row)
PYEOF

echo "fab outputs in $(cd "$FAB" && pwd):"
ls -la "$FAB"
