#!/bin/bash
# Re-applies the v3 -> v4 rework to the committed v3 board (a339085) from scratch.
set -e
cd "$(dirname "$0")/../.."
git checkout a339085 -- sticks3-bot-hat.kicad_pcb
for ph in 0 1 2; do
  docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/work" kicad/kicad:10.0 \
    sh -c "python3 /work/gen/tools/rework_v4.py $ph 2>&1 | grep -v 'swig/python\|pcb_track.cpp\|Debug:'; exit \${PIPESTATUS:-0}"
done
