# Refill all copper zones and save (needed after editing footprints outside the GUI).
import sys
import pcbnew
PCB = sys.argv[1] if len(sys.argv) > 1 else "/work/sticks3-bot-hat.kicad_pcb"
board = pcbnew.LoadBoard(PCB)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("zones refilled:", len(board.Zones()))
# Report courtyard geometry near the mounting holes
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
for h, j in (("H1", "J1"), ("H3", "J2")):
    hc = fps[h].GetPosition()
    cy = fps[j].GetCourtyard(pcbnew.F_CrtYd).BBox()
    dx = max(cy.GetLeft() - hc.x, hc.x - cy.GetRight(), 0)
    dy = max(cy.GetTop() - hc.y, hc.y - cy.GetBottom(), 0)
    d = (dx**2 + dy**2) ** 0.5 / 1e6
    print(f"{h} centre to {j} courtyard edge: {d:.2f} mm  (M3 courtyard radius 3.20, M2.5 was 2.70)")
