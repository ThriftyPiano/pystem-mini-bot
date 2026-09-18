# v3 -> v4 rework of the hand-routed board, in place (keeps all routing that
# isn't affected): sensor headers reordered to V G D0 / V G - A0, COLOR B ->
# DIST (HC-SR04, 4 pin, 5V, ECHO divider R4/R5), power LED moved right.
# Run inside the kicad/kicad docker image (see export.sh for the mount).
import sys
import pcbnew
sys.path.insert(0, "/work/gen")
import design

PCB = "/work/sticks3-bot-hat.kicad_pcb"
FP_DIR = "/usr/share/kicad/footprints"
PHASE = int(sys.argv[1])   # 0 delete, 1 renet+footprint removal, 2 place+route+silk
board = pcbnew.LoadBoard(PCB)
MM = pcbnew.FromMM
V = pcbnew.VECTOR2I_MM
F, B = pcbnew.F_Cu, pcbnew.B_Cu
mm = lambda v: round(v / 1e6, 2)

def net(name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
    return n

# ---- 1. delete tracks/vias that the rework replaces ---------------------
DEL_TRACKS = {
 "GND": [((58.52,69.57),(62.38,69.57)),((62.38,71),(62.38,69.57)),((62.38,69.57),(69.75,69.57)),
         ((69.75,69.57),(71.18,71)),((70.09,69.22),(69.75,69.57)),((70.09,66.02),(70.09,69.22)),
         ((68.6,64.53),(70.09,66.02)),((54.55,65.6),(58.52,69.57)),((62.38,71),(63.54,71.31)),
         ((72.65,72.47),(71.18,71)),((78.51,72.47),(72.65,72.47)),((79.98,71),(78.51,72.47)),
         ((79.98,71),(82.61,68.37)),((82.61,68.37),(83.28,68.37)),((83.28,68.37),(86.15,68.37)),
         ((86.15,68.37),(88.78,71)),((83.28,68.37),(83.28,67.7)),((88.78,76.2),(91.69,76.2)),
         ((91.69,76.2),(92.7,75.19)),
         ((88.78,60.78),(88.78,71)),((86,58),(88.78,60.78)),((88.78,76.2),(88.78,71)),
         ((76.2,67.22),(79.98,71)),((76.2,63.2),(76.2,67.22)),((62.38,76.2),(62.38,71)),
         ((71.18,76.2),(71.18,71)),((79.98,76.2),(79.98,71))],
 "COLOR_A": [((74.9,71),(74.9,69.82)),((69.74,59.14),(69.74,64.66)),((69.74,64.66),(74.9,69.82))],
 "COLOR_B": [((83.7,71),(83.7,54.31))],
 "ENC_A": [((57.3,71),(57.3,59.07))],
 "ENC_B": [((66.1,71),(66.1,69.82)),((66.14,69.78),(66.14,59.74)),((66.1,69.82),(66.14,69.78))],
 "TILT": [((78.56,54.51),(78.56,67.2)),((82.52,73.85),(83.7,75.02)),((83.7,76.2),(83.7,75.02)),
          ((82.52,71.17),(82.52,73.85)),((78.56,67.2),(82.52,71.17))],
 "+5V": [((87.94,67.36),(92.7,72.12))],
 "VSERVO": [((86,64),(90.24,64)),((90.24,76.79),(90.24,64)),((89.38,77.65),(90.24,76.79)),
            ((87.69,77.65),(89.38,77.65)),((86.24,76.2),(87.69,77.65))],
}
DEL_ALL_NETS = {"+3V3", "LED_K"}
DEL_VIAS = [(63.54,71.31),(90.24,64)]
n_del = 0
kept = []
for t in (list(board.GetTracks()) if PHASE == 0 else []):
    nm = t.GetNetname()
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        if (mm(p.x), mm(p.y)) in DEL_VIAS or nm in DEL_ALL_NETS:
            board.Remove(t); n_del += 1
        else:
            kept.append(t)
        continue
    s, e = t.GetStart(), t.GetEnd()
    key = {(mm(s.x), mm(s.y)), (mm(e.x), mm(e.y))}
    if nm in DEL_ALL_NETS or any({a, b} == key for a, b in DEL_TRACKS.get(nm, [])):
        board.Remove(t); n_del += 1
    else:
        kept.append(t)
if PHASE == 0:
    print("deleted", n_del, "track items")
    board.Save(PCB)
    sys.exit(0)
# ---- phase boundary: pcbnew's bindings crash if we keep going after Remove(),
# so each phase is a separate process (run.sh: 0, 1, 2 in order on the v3 board)
# renamed nets on kept items
if PHASE == 2:
    n_re = 0
    for t in list(board.GetTracks()):
        nm = str(t.GetNetname())
        if nm == "COLOR_A": t.SetNet(net("COLOR")); n_re += 1
        if nm == "COLOR_B": t.SetNet(net("ECHO")); n_re += 1
    print("renet", n_re)

# ---- 2. footprints: replace J8/J10 with 1x4, add R4/R5, move R3/D1 ------
fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
removed = []
def place(ref):
    slib, ssym, value, kind, fplib, fpname, (x, y, rot), pads, label = design.COMPONENTS[ref]
    old = fps.get(ref)
    if old is not None and str(old.GetFPID().GetLibItemName()) != fpname:
        board.Remove(old); old = None; removed.append(ref)
    if old is None:
        fp = pcbnew.FootprintLoad(f"{FP_DIR}/{fplib}.pretty", fpname)
        fp.SetFPIDAsString(f"{fplib}:{fpname}")
        fp.SetReference(ref); fp.SetValue(value)
        fp.Reference().SetVisible(label is None)
        board.Add(fp); fps[ref] = fp
    else:
        fp = old
    fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
    for pad in fp.Pads():
        nm = pads.get(pad.GetNumber())
        if nm: pad.SetNet(net(nm))
        else: pad.SetNetCode(0)  # unconnected
    return fp
if PHASE == 1:
    for ref in ("J8", "J10"):
        old = fps.get(ref)
        if old is not None and str(old.GetFPID().GetLibItemName()) != design.COMPONENTS[ref][5]:
            board.Remove(old)
    board.Save(PCB)
    sys.exit(0)
for ref in ("J1", "J6", "J7", "J8", "J10", "R3", "R4", "R5", "D1"):
    fp = place(ref)
    if ref in ("R3", "R4", "R5", "D1"):
        fp.Reference().SetVisible(False)  # no room beside DIST; BOM/positions carry the refs
    print(ref, [(p.GetNumber(), p.GetNetname(), mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in fp.Pads()])

# ---- 3. new routing ----------------------------------------------------
def trk(nm, layer, pts, w):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2)); t.SetWidth(MM(w))
        t.SetLayer(layer); t.SetNet(net(nm)); board.Add(t)
def via(nm, x, y, dia=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(F, B); v.SetDrill(MM(drill))
    try: v.SetWidth(MM(dia))
    except TypeError: v.SetWidth(F, MM(dia)); v.SetWidth(B, MM(dia))
    v.SetNet(net(nm)); board.Add(v)
S, P = 0.25, 0.7
trk("ENC_A", B, [(57.3,59.07),(57.3,69.0)], S); via("ENC_A", 57.3, 69.0)
trk("ENC_A", F, [(57.3,69.0),(61.3,69.0),(62.38,70.08),(62.38,71.0)], S)
trk("ENC_B", B, [(66.14,59.74),(66.14,65.96),(71.18,71.0)], S)
trk("COLOR", B, [(69.74,59.14),(69.74,64.0),(72.0,66.26),(72.0,69.2)], S); via("COLOR", 72.0, 69.2)
trk("COLOR", F, [(72.0,69.2),(81.7,69.2),(82.52,70.02),(82.52,71.0)], S)
trk("+3V3", B, [(72.74,55.5),(74.75,57.51),(74.75,70.85),(74.9,71.0)], P)
trk("+3V3", F, [(74.9,71.0),(73.3,72.6),(67.7,72.6),(66.1,71.0),(64.5,72.6),(58.9,72.6),(57.3,71.0)], P)
trk("+5V", F, [(86.24,71.0),(86.24,67.36)], P)
trk("+5V", F, [(87.94,67.36),(95.7,67.36),(96.6,68.26),(96.6,70.48)], P)
trk("LED_K", F, [(96.6,72.12),(96.6,73.61)], S)
trk("GND", F, [(96.6,75.19),(96.6,76.3)], P); via("GND", 96.6, 76.3, 0.8, 0.4)
trk("GND", F, [(93.86,75.225),(93.86,76.5)], P); via("GND", 93.86, 76.5, 0.8, 0.4)
trk("TRIG", F, [(72.74,52.96),(74.3,51.4),(87.68,51.4),(88.78,52.5),(88.78,56.0)], S); via("TRIG", 88.78, 56.0)
trk("TRIG", B, [(88.78,56.0),(88.78,71.0)], S)
trk("ECHO", B, [(83.7,54.31),(84.59,55.2),(91.7,55.2),(92.59,56.09),(92.59,74.4)], S); via("ECHO", 92.59, 74.4)
trk("ECHO", F, [(93.86,73.575),(92.59,74.4),(91.5,75.225)], S)
trk("ECHO_5V", F, [(91.32,71.0),(91.5,71.18),(91.5,73.575)], S)
trk("TILT", B, [(78.56,54.51),(78.56,65.5),(81.25,68.19),(81.25,73.0),(83.7,75.45),(83.7,76.2)], S)
trk("VSERVO", B, [(86.0,64.0),(84.38,65.62),(84.38,74.34),(86.24,76.2)], P)

# ---- 4. silkscreen -----------------------------------------------------
for d in list(board.GetDrawings()):
    if d.GetClass() == "PCB_TEXT":
        txt = d.GetText()
        if txt in ("S 3V G", "ENC A", "ENC B", "COLOR A", "COLOR B"):
            board.Remove(d)
        elif "HAT v3" in txt:
            d.SetText(txt.replace(" HAT v3", " HAT"))
def silk(x, y, text, size=1.0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text); t.SetPosition(V(x, y)); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(size * 0.15))
    board.Add(t)
silk(59.84, 73.7, "ENC A", 0.7); silk(68.64, 73.7, "ENC B", 0.7)
silk(78.71, 73.7, "COLOR", 0.7); silk(88.3, 73.7, "DIST", 0.7)
for x, c in [(57.3,"V"),(59.84,"G"),(62.38,"D"),(66.1,"V"),(68.64,"G"),(71.18,"D"),
             (74.9,"V"),(77.44,"G"),(79.98,"-"),(82.52,"A"),
             (86.24,"5"),(88.78,"T"),(91.32,"E"),(93.86,"G")]:
    silk(x, 72.5, c, 0.6)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
print("saved")
