#!/bin/bash
# Re-render render-top.png / render-bottom.png / render-3d.png from the board
# (kicad-cli 10 with the KiCad 3D model library; falls back to the kicad/kicad:10.0-full
# docker image, which - unlike the plain one export.sh uses - ships the 3D models).
set -e
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
KICAD_IMAGE=${KICAD_IMAGE:-kicad/kicad:10.0-full}
MODELS=${KICAD_3DMODELS:-/usr/share/kicad/3dmodels}
if [ -n "$KICAD_CLI" ]; then :
elif command -v kicad-cli >/dev/null; then KICAD_CLI=kicad-cli
elif [ -x ~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli ]; then KICAD_CLI=~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
else KICAD_CLI="docker run --rm -u $(id -u):$(id -g) -v $ROOT:/work -w /work/gen $KICAD_IMAGE kicad-cli"; fi
PCB=../sticks3-bot-hat.kicad_pcb
DEF="-D KICAD10_3DMODEL_DIR=$MODELS"
$KICAD_CLI pcb render $DEF --quality high --background opaque --side top    -w 1600 -h 1100 --zoom 1.0 -o ../render-top.png "$PCB"
$KICAD_CLI pcb render $DEF --quality high --background opaque --side bottom -w 1600 -h 1100 --zoom 1.0 -o ../render-bottom.png "$PCB"
$KICAD_CLI pcb render $DEF --quality high --background opaque --perspective --rotate '-40,0,30' --floor -w 1600 -h 1100 --zoom 0.9 -o ../render-3d.png "$PCB"
