# One-off: replace the H1-H4 mounting-hole footprints in place (same centre)
# with MountingHole_3.2mm_M3. Run inside the kicad/kicad docker image.
import pcbnew
PCB = "/work/sticks3-bot-hat.kicad_pcb"
LIB = "/usr/share/kicad/footprints/MountingHole.pretty"
board = pcbnew.LoadBoard(PCB)
for fp in list(board.GetFootprints()):
    ref = fp.GetReference()
    if not ref.startswith("H"):
        continue
    pos, val = fp.GetPosition(), fp.GetValue()
    new = pcbnew.FootprintLoad(LIB, "MountingHole_3.2mm_M3")
    new.SetPosition(pos); new.SetReference(ref); new.SetValue(val)
    new.Reference().SetVisible(False)
    new.SetFPIDAsString("MountingHole:MountingHole_3.2mm_M3")
    board.Remove(fp); board.Add(new)
    print(ref, pos.x / 1e6, pos.y / 1e6, "->", new.GetFPID().GetLibItemName(),
          [p.GetDrillSize().x / 1e6 for p in new.Pads()])
board.Save(PCB)
