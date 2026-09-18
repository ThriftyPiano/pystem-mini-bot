import pcbnew
b = pcbnew.LoadBoard("/work/sticks3-bot-hat.kicad_pcb")
mm = lambda v: round(v/1e6, 2)
print("== footprints")
for fp in sorted(b.GetFootprints(), key=lambda f: f.GetReference()):
    p = fp.GetPosition()
    print(fp.GetReference(), fp.GetValue(), fp.GetFPID().GetLibItemName(), mm(p.x), mm(p.y), fp.GetOrientationDegrees(), fp.GetLayerName())
    for pad in fp.Pads():
        pp = pad.GetPosition()
        print("   pad", pad.GetNumber(), pad.GetNetname(), mm(pp.x), mm(pp.y), "drill", mm(pad.GetDrillSize().x), "size", mm(pad.GetSize().x), mm(pad.GetSize().y))
print("== tracks")
for t in b.GetTracks():
    s, e = t.GetStart(), t.GetEnd()
    kind = "via" if t.GetClass() == "PCB_VIA" else "trk"
    print(kind, t.GetNetname(), t.GetLayerName(), mm(s.x), mm(s.y), "->", mm(e.x), mm(e.y), "w", mm(t.GetWidth()))
print("== zones")
for z in b.Zones():
    print(z.GetNetname(), z.GetLayerName(), "clr", mm(z.GetLocalClearance()), "minw", mm(z.GetMinThickness()))
print("== texts")
for d in b.GetDrawings():
    if d.GetClass() == "PCB_TEXT":
        p = d.GetPosition(); print(repr(d.GetText()), d.GetLayerName(), mm(p.x), mm(p.y), d.GetTextAngleDegrees())
ds = b.GetDesignSettings()
print("== rules clearance", mm(ds.m_MinClearance), "trackw", mm(ds.m_TrackMinWidth), "netclass default trk", mm(ds.GetCurrentTrackWidth()))
