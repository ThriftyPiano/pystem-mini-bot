# Generates sticks3-bot-hat.kicad_pcb from design.py using KiCad's pcbnew API.
# Run with KiCad's bundled python:
#   ~/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 gen_pcb.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew  # noqa: E402
import design  # noqa: E402
from design import BOARD_L, BOARD_T, BOARD_W, BOARD_H  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "sticks3-bot-hat.kicad_pcb")
STD_FP_DIR = os.path.expanduser(
    "~/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
LOCAL_FP_DIR = os.path.join(HERE, "..", "sticks3-bot-hat.pretty")

MM = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I_MM(x, y)


board = pcbnew.CreateEmptyBoard()

# --- nets ------------------------------------------------------------------
nets = {}
for name in design.NETS:
    n = pcbnew.NETINFO_ITEM(board, name)
    board.Add(n)
    nets[name] = n

# --- footprints ------------------------------------------------------------
fps = {}
for ref, (slib, ssym, value, kind, fplib, fpname, (x, y, rot), pads,
          label) in design.COMPONENTS.items():
    libdir = (os.path.join(STD_FP_DIR, fplib + ".pretty")
              if kind == design.STD_FP else LOCAL_FP_DIR)
    fp = pcbnew.FootprintLoad(libdir, fpname)
    assert fp, f"footprint {fplib}/{fpname} not found"
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetPosition(V(x, y))
    fp.SetOrientationDegrees(rot)
    for pad in fp.Pads():
        net = pads.get(pad.GetNumber())
        if net:
            pad.SetNet(nets[net])
    # keep silkscreen tidy: hide default ref text for connectors (we add
    # human labels instead), keep it for passives
    if label is not None or ref.startswith(("H",)):
        fp.Reference().SetVisible(False)
    # nudge refs that land under neighbouring part bodies
    ref_moves = {"C3": (-2.6, 0), "C4": (0, -2.8), "C5": (3.7, 0)}
    if ref in ref_moves:
        dx, dy = ref_moves[ref]
        fp.Reference().SetPosition(V(x + dx, y + dy))
        fp.Reference().SetTextAngleDegrees(0)
    board.Add(fp)
    fps[ref] = fp

# --- board outline (rounded rectangle) -------------------------------------
R = 2.0
L, T, W, H = BOARD_L, BOARD_T, BOARD_W, BOARD_H


def edge_seg(x1, y1, x2, y2):
    s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(x1, y1))
    s.SetEnd(V(x2, y2))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(0.1))
    board.Add(s)


def edge_arc(cx, cy, sx, sy, angle_deg):
    a = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
    a.SetCenter(V(cx, cy))
    a.SetStart(V(sx, sy))
    a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T), False)
    a.SetLayer(pcbnew.Edge_Cuts)
    a.SetWidth(MM(0.1))
    board.Add(a)


edge_seg(L + R, T, L + W - R, T)
edge_seg(L + W, T + R, L + W, T + H - R)
edge_seg(L + W - R, T + H, L + R, T + H)
edge_seg(L, T + H - R, L, T + R)
edge_arc(L + R, T + R, L, T + R, 90)
edge_arc(L + W - R, T + R, L + W - R, T, 90)
edge_arc(L + W - R, T + H - R, L + W, T + H - R, 90)
edge_arc(L + R, T + H - R, L + R, T + H, 90)

# --- silkscreen text -------------------------------------------------------


def silk(x, y, text, size=1.0, layer=pcbnew.F_SilkS, rot=0, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(V(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * (0.2 if bold else 0.15)))
    t.SetTextAngleDegrees(rot)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


for ref, comp in design.COMPONENTS.items():
    pass  # per-connector labels are placed explicitly below

silk(73.0, 79.6, "PySTEM Mini Bot - StickS3 HAT v3", 1.0,
     layer=pcbnew.B_SilkS, bold=True)
silk(73.0, 81.5, "robot.pystem.com - battery 6V, center +", 0.9,
     layer=pcbnew.B_SilkS)
# connector labels: sensor row (between the rows), servo row (below)
silk(59, 73.7, "ENC A", 0.7)
silk(68, 73.7, "ENC B", 0.7)
silk(77, 73.7, "COLOR A", 0.7)
silk(86, 73.7, "COLOR B", 0.7)
silk(59.84, 79.2, "WHEEL A", 0.8)
silk(68.64, 79.2, "WHEEL B", 0.8)
silk(77.44, 79.2, "PAN", 0.8)
silk(86.24, 79.2, "TILT", 0.8)
silk(87.0, 66.6, "6V ctr+", 0.7)
silk(52.7, 71.0, "S 3V G", 0.6)
silk(52.7, 76.2, "S V G", 0.6)
silk(65.5, 58.6, "StickS3 flat, screen up", 0.7)

# --- routing ---------------------------------------------------------------
# ROUTES: (net, layer, width_mm, [(x1,y1),(x2,y2),...])
F, B = pcbnew.F_Cu, pcbnew.B_Cu
ROUTES = []

# GND stitch via on the freerouted J1.1 top track, ties B pour patch to F
VIAS = []


def add_routes():
    for net, layer, w, pts in ROUTES:
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(V(*a))
            t.SetEnd(V(*b))
            t.SetWidth(MM(w))
            t.SetLayer(layer)
            t.SetNet(nets[net])
            board.Add(t)
    for x, y, net in VIAS:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(V(x, y))
        v.SetDrill(MM(0.4))
        v.SetWidth(MM(0.8))
        v.SetLayerPair(F, B)
        v.SetNet(nets[net])
        board.Add(v)


# --- zones -----------------------------------------------------------------


def add_zone(net, layer, rect, priority=0):
    (x1, y1, x2, y2) = rect
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(nets[net])
    z.SetAssignedPriority(priority)
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetThermalReliefGap(MM(0.4))
    z.SetThermalReliefSpokeWidth(MM(0.6))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    for (px, py) in [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]:
        o.Append(MM(px), MM(py))
    board.Add(z)
    return z



def stitch_via_near(ref, padnum, net="GND"):
    """Drop a GND stitch via next to a THT pad, in a spot clear of the
    autorouted tracks, so the B.Cu pour patch at the pad isn't an isolated
    island (starved-thermal DRC). Searches outward from the pad."""
    import math
    pad = None
    for p in fps[ref].Pads():
        if p.GetNumber() == padnum:
            pad = p
    px, py = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)

    def seg_dist(ax, ay, bx, by, cx, cy, dx, dy):
        # min distance between segments AB and CD
        def pt_seg(px_, py_, x1, y1, x2, y2):
            ddx, ddy = x2 - x1, y2 - y1
            if ddx == ddy == 0:
                return math.hypot(px_ - x1, py_ - y1)
            t = max(0, min(1, ((px_ - x1) * ddx + (py_ - y1) * ddy) / (ddx * ddx + ddy * ddy)))
            return math.hypot(px_ - x1 - t * ddx, py_ - y1 - t * ddy)
        return min(pt_seg(ax, ay, cx, cy, dx, dy), pt_seg(bx, by, cx, cy, dx, dy),
                   pt_seg(cx, cy, ax, ay, bx, by), pt_seg(dx, dy, ax, ay, bx, by))

    obstacles = []  # (x1,y1,x2,y2,halfwidth,is_front)
    for t in board.GetTracks():
        if t.GetNetname() == net:
            continue
        s, e = t.GetStart(), t.GetEnd()
        if t.GetClass() == "PCB_VIA":
            obstacles.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                              pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                              pcbnew.ToMM(t.GetWidth()) / 2, True))
        elif t.GetClass() == "PCB_TRACK":
            obstacles.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                              pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                              pcbnew.ToMM(t.GetWidth()) / 2, t.GetLayerName() == "F.Cu"))
    pads = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net:
                continue
            pads.append((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)))

    best = None
    for r in [x / 10 for x in range(12, 40, 2)]:
        for ang in range(0, 360, 15):
            cx = px + r * math.cos(math.radians(ang))
            cy = py + r * math.sin(math.radians(ang))
            ok = True
            for (x1, y1, x2, y2, hw, front) in obstacles:
                # via clearance (both layers)
                if seg_dist(cx, cy, cx, cy, x1, y1, x2, y2) < 0.4 + hw + 0.25:
                    ok = False
                    break
                # stub runs on F.Cu from pad to via
                if front and seg_dist(px, py, cx, cy, x1, y1, x2, y2) < 0.35 + hw + 0.25:
                    ok = False
                    break
            if ok:
                for (qx, qy) in pads:
                    if math.hypot(cx - qx, cy - qy) < 1.5:
                        ok = False
                        break
            if ok:
                best = (cx, cy)
                break
        if best:
            break
    if not best:
        print("WARNING: no stitch via spot found near", ref, padnum)
        return
    cx, cy = best
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(V(px, py))
    t.SetEnd(V(cx, cy))
    t.SetWidth(MM(0.7))
    t.SetLayer(F)
    t.SetNet(nets[net])
    board.Add(t)
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(cx, cy))
    v.SetDrill(MM(0.4))
    v.SetWidth(MM(0.8))
    v.SetLayerPair(F, B)
    v.SetNet(nets[net])
    board.Add(v)
    print(f"stitch via at ({cx:.2f},{cy:.2f})")


def make_zones():
    full = (L - 1, T - 1, L + W + 1, T + H + 1)
    add_zone("GND", B, full)
    add_zone("GND", F, full)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "final"
    out = os.path.abspath(OUT)
    if mode == "route-prep":
        # no zones: export a clean DSN for freerouting
        pcbnew.SaveBoard(out, board)
        dsn = os.path.join(HERE, "route.dsn")
        ok = pcbnew.ExportSpecctraDSN(board, dsn)
        print("dsn export:", ok, dsn)
    elif mode == "final":
        ses = sys.argv[2]
        pcbnew.SaveBoard(out, board)  # establish file context
        ok = pcbnew.ImportSpecctraSES(board, ses)
        print("ses import:", ok)
        add_routes()
        stitch_via_near("J1", "1")
        stitch_via_near("J6", "3")
        stitch_via_near("C7", "2")
        make_zones()
        pcbnew.SaveBoard(out, board)
        print("saved", out)
    elif mode == "dump":
        for ref in sorted(fps):
            for pad in sorted(fps[ref].Pads(), key=lambda p: p.GetNumber()):
                p = pad.GetPosition()
                print(f"{ref}.{pad.GetNumber()} {pad.GetNetname() or '-':10s} "
                      f"({pcbnew.ToMM(p.x):.2f},{pcbnew.ToMM(p.y):.2f})")
