#!/bin/bash
# Export fabrication outputs (gerbers, drill, placement, BOM) for JLCPCB.
# Produces ../fab/ with a ready-to-upload gerber zip.
#
# Needs kicad-cli 10. Resolution order: KICAD_CLI env var, kicad-cli on PATH,
# the macOS app bundle, else the official docker image (kicad/kicad:10.0).
set -e
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
KICAD_IMAGE=${KICAD_IMAGE:-kicad/kicad:10.0}

if [ -n "$KICAD_CLI" ]; then
    :
elif command -v kicad-cli >/dev/null; then
    KICAD_CLI=kicad-cli
elif [ -x ~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli ]; then
    KICAD_CLI=~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
elif command -v docker >/dev/null; then
    docker image inspect "$KICAD_IMAGE" >/dev/null 2>&1 || docker pull "$KICAD_IMAGE"
    KICAD_CLI="docker run --rm -u $(id -u):$(id -g) -v $ROOT:/work -w /work/gen $KICAD_IMAGE kicad-cli"
else
    echo "kicad-cli not found and docker unavailable" >&2
    exit 1
fi
CLI() { $KICAD_CLI "$@"; }

PCB=../sticks3-bot-hat.kicad_pcb
SCH=../sticks3-bot-hat.kicad_sch
FAB=../fab

# Zone fills: kicad-cli exports the fill stored in the file, so refill first
# (the scripted reworks strip stale fills). Uses the macOS bundle's python
# or the docker image; otherwise open the board in pcbnew, press B, save.
KICAD_PY=~/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
if [ -x "$KICAD_PY" ]; then
    "$KICAD_PY" tools/refill_zones.py "$PCB"
elif command -v docker >/dev/null; then
    docker run --rm -u "$(id -u):$(id -g)" -v "$ROOT:/work" "$KICAD_IMAGE" python3 /work/gen/tools/refill_zones.py
else
    echo "*** WARNING: could not refill zones - refill in pcbnew (B) and save before trusting these gerbers ***"
fi
# fab/cpl-jlcpcb-corrected.csv is hand-maintained (JLC-specific part rotations
# that the assembled boards were built from) - keep it, regenerate the rest.
rm -rf "$FAB/gerbers" "$FAB"/*.zip "$FAB/positions.csv" "$FAB/bom.csv"
mkdir -p "$FAB/gerbers"

# Design rule / electrical rule checks (reports next to this script).
# Violations don't abort the export - read the reports before ordering.
# Known/accepted: the M3 hole footprints' 6.4 mm courtyard circle grazes the
# J1/J2 header courtyards by <0.25 mm (use screws with <=5.5 mm heads).
CLI pcb drc --severity-error --exit-code-violations \
    -o sticks3-bot-hat-drc.rpt "$PCB" \
    || echo "*** WARNING: DRC violations - see gen/sticks3-bot-hat-drc.rpt ***"
CLI sch erc --severity-error --exit-code-violations \
    -o sticks3-bot-hat-erc.rpt "$SCH" \
    || echo "*** WARNING: ERC violations - see gen/sticks3-bot-hat-erc.rpt ***"

CLI pcb export gerbers \
    --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
    --subtract-soldermask \
    -o "$FAB/gerbers/" "$PCB"
CLI pcb export drill --format excellon --drill-origin absolute \
    --excellon-units mm --generate-map --map-format gerberx2 \
    -o "$FAB/gerbers/" "$PCB"
(cd "$FAB" && rm -f sticks3-bot-hat-gerbers.zip && zip -qr sticks3-bot-hat-gerbers.zip gerbers)

# Pick & place (JLC wants: Designator, Mid X, Mid Y, Layer, Rotation)
CLI pcb export pos --format csv --units mm --side both \
    -o "$FAB/positions.csv" "$PCB"

# Schematic PDF for reference
CLI sch export pdf -o ../sticks3-bot-hat-schematic.pdf "$SCH"

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
