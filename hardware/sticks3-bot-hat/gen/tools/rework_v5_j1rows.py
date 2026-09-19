# v4 -> v5 rework, in place, without pcbnew: swap the nets between the two
# rows of J1 (HAT2 header) and re-terminate the affected tracks.
#
# Why: on the first v3/v4 boards the StickS3 (screen up) puts its power row
# (GND EXT_5V BOOT G1 G8 BAT 3V3 5V_IN) on the header's *lower* row of pins,
# the one nearest the board edge (J1 even pads), and its GPIO row (G5 G4 G6
# G7 G43 G44 G2 G3) on the upper row (J1 odd pads). design.py had it the
# other way round. Column order was right. Measured on hardware 2026-09-19.
#
# Text-level edit of the .kicad_pcb: removes the listed segments/vias, adds
# the new ones, rewrites J1's pad nets and drops the stale zone fills (open
# the board in pcbnew and refill zones (B) before exporting).
import re, sys, uuid

PCB = sys.argv[1] if len(sys.argv) > 1 else "sticks3-bot-hat.kicad_pcb"
s = open(PCB).read()

NEW_PAD_NETS = {"1": "SERVO_A", "2": "GND", "3": "SERVO_B", "4": None,
                "5": "PAN", "6": None, "7": "TILT", "8": "COLOR",
                "9": "ENC_A", "10": "ECHO", "11": "ENC_B", "12": None,
                "13": "TRIG", "14": "+3V3", "15": None, "16": "+5V"}

DEL_SEGS = [  # (net, start, end)
    ("GND", (57.5, 55.5), (57.810582, 56.65911)),
    ("GND", (57.5, 56.9017), (55.4625, 58.9392)),
    ("GND", (57.5, 55.5), (57.5, 56.9017)),
    ("SERVO_A", (58.77, 57.1074), (58.77, 54.23)),
    ("SERVO_A", (58.77, 54.23), (57.5, 52.96)),
    ("SERVO_B", (61.31, 57.427), (61.31, 54.23)),
    ("SERVO_B", (61.31, 54.23), (60.04, 52.96)),
    ("PAN", (63.85, 54.23), (63.85, 59.0267)),
    ("PAN", (62.58, 52.96), (63.85, 54.23)),
    ("TILT", (65.12, 52.96), (66.3401, 51.7399)),
    ("TILT", (66.3401, 51.7399), (75.79, 51.7399)),
    ("ENC_A", (66.39, 54.23), (64.6891, 54.23)),
    ("ENC_A", (67.66, 52.96), (66.39, 54.23)),
    ("ENC_A", (64.6891, 54.23), (63.7567, 55.1624)),
    ("ENC_A", (63.7567, 55.1624), (63.7567, 55.995)),
    ("ENC_A", (63.7567, 55.995), (60.6777, 59.074)),
    ("ENC_B", (68.93, 56.9495), (68.93, 54.23)),
    ("ENC_B", (68.93, 54.23), (70.2, 52.96)),
    ("ENC_B", (66.1384, 59.7411), (68.93, 56.9495)),
    ("COLOR", (65.12, 55.5), (68.7622, 59.1422)),
    ("COLOR", (68.7622, 59.1422), (69.7393, 59.1422)),
    ("ECHO", (68.8506, 54.3094), (83.7, 54.3094)),
    ("ECHO", (67.66, 55.5), (68.8506, 54.3094)),
    ("ECHO", (83.7, 54.31), (84.59, 55.2)),
    ("+3V3", (72.74, 55.5), (74.75, 57.51)),
    ("+5V", (75.28, 55.5), (69.0199, 61.7601)),
    ("TRIG", (88.78, 52.5), (88.78, 56.0)),
    ("TRIG", (72.74, 52.96), (74.3, 51.4)),
    ("TRIG", (74.3, 51.4), (87.68, 51.4)),
    ("TRIG", (87.68, 51.4), (88.78, 52.5)),
]
DEL_VIAS = [("GND", (57.810582, 56.65911)), ("COLOR", (69.7393, 59.1422)), ("ECHO", (83.7, 54.3094))]

F, B = "F.Cu", "B.Cu"
ADD_SEGS = [  # (net, layer, width, start, end)
    ("SERVO_A", B, 0.25, (58.77, 57.1074), (58.77, 56.77)),
    ("SERVO_A", B, 0.25, (58.77, 56.77), (57.5, 55.5)),
    ("SERVO_B", B, 0.25, (61.31, 57.427), (61.31, 56.77)),
    ("SERVO_B", B, 0.25, (61.31, 56.77), (60.04, 55.5)),
    ("PAN", B, 0.25, (63.85, 59.0267), (63.85, 56.77)),
    ("PAN", B, 0.25, (63.85, 56.77), (62.58, 55.5)),
    ("TILT", B, 0.25, (65.12, 55.5), (63.85, 54.23)),
    ("TILT", B, 0.25, (63.85, 54.23), (63.85, 51.7399)),
    ("TILT", B, 0.25, (63.85, 51.7399), (75.79, 51.7399)),
    ("ENC_A", F, 0.25, (67.66, 55.5), (66.39, 56.77)),
    ("ENC_A", F, 0.25, (66.39, 56.77), (62.9817, 56.77)),
    ("ENC_A", F, 0.25, (62.9817, 56.77), (60.6777, 59.074)),
    ("ENC_B", F, 0.25, (66.14, 59.74), (68.93, 56.95)),
    ("ENC_B", F, 0.25, (68.93, 56.95), (68.93, 56.77)),
    ("ENC_B", F, 0.25, (68.93, 56.77), (70.2, 55.5)),
    ("COLOR", B, 0.25, (65.12, 52.96), (66.39, 54.23)),
    ("COLOR", B, 0.25, (66.39, 54.23), (66.39, 57.79)),
    ("COLOR", B, 0.25, (66.39, 57.79), (67.74, 59.14)),
    ("COLOR", B, 0.25, (67.74, 59.14), (69.74, 59.14)),
    ("ECHO", F, 0.25, (67.66, 52.96), (69.07, 51.55)),
    ("ECHO", F, 0.25, (69.07, 51.55), (83.7, 51.55)),
    ("ECHO", F, 0.25, (83.7, 51.55), (83.7, 53.5)),
    ("ECHO", B, 0.25, (83.7, 53.5), (83.7, 54.31)),
    ("ECHO", B, 0.25, (83.7, 54.31), (84.59, 55.2)),
    ("+3V3", B, 0.7, (74.75, 57.51), (74.01, 56.77)),
    ("+3V3", B, 0.25, (74.01, 56.77), (74.01, 54.23)),
    ("+3V3", B, 0.25, (74.01, 54.23), (72.74, 52.96)),
    ("+5V", F, 0.7, (69.0199, 61.7601), (73.28, 57.5)),
    ("+5V", F, 0.7, (73.28, 57.5), (76.9, 57.5)),
    ("+5V", B, 0.7, (76.9, 57.5), (76.9, 54.58)),
    ("+5V", B, 0.7, (76.9, 54.58), (75.28, 52.96)),
    ("TRIG", F, 0.25, (72.74, 55.5), (74.01, 54.23)),
    ("TRIG", F, 0.25, (74.01, 54.23), (87.68, 54.23)),
    ("TRIG", F, 0.25, (87.68, 54.23), (88.78, 55.33)),
    ("TRIG", F, 0.25, (88.78, 55.33), (88.78, 56.0)),
]
ADD_VIAS = [  # (net, at, size, drill)
    ("ENC_B", (66.14, 59.74), 0.6, 0.3),
    ("ECHO", (83.7, 53.5), 0.6, 0.3),
    ("+5V", (76.9, 57.5), 0.8, 0.4),
]

def close(a, b): return abs(a - b) < 0.0015
def fmt(v): return repr(float(v)).rstrip("0").rstrip(".") if isinstance(v, float) else str(v)

# --- 1. delete segments / vias --------------------------------------------
seg_re = re.compile(r'\n\t\(segment\n\t\t\(start ([\d.\-]+) ([\d.\-]+)\)\n\t\t\(end ([\d.\-]+) ([\d.\-]+)\)\n\t\t\(width [\d.]+\)\n\t\t\(layer "[^"]+"\)\n\t\t\(net "([^"]+)"\)\n\t\t\(uuid "[^"]+"\)\n\t\)')
via_re = re.compile(r'\n\t\(via\n\t\t\(at ([\d.\-]+) ([\d.\-]+)\)\n\t\t\(size [\d.]+\)\n\t\t\(drill [\d.]+\)\n\t\t\(layers "[^"]+" "[^"]+"\)\n\t\t\(net "([^"]+)"\)\n\t\t\(uuid "[^"]+"\)\n\t\)')
found = set()
def seg_sub(m):
    x1, y1, x2, y2 = map(float, m.group(1, 2, 3, 4)); net = m.group(5)
    for i, (n, a, b) in enumerate(DEL_SEGS):
        if n == net and ((close(x1, a[0]) and close(y1, a[1]) and close(x2, b[0]) and close(y2, b[1])) or
                         (close(x1, b[0]) and close(y1, b[1]) and close(x2, a[0]) and close(y2, a[1]))):
            found.add(("seg", i)); return ""
    return m.group(0)
def via_sub(m):
    x, y = map(float, m.group(1, 2)); net = m.group(3)
    for i, (n, a) in enumerate(DEL_VIAS):
        if n == net and close(x, a[0]) and close(y, a[1]):
            found.add(("via", i)); return ""
    return m.group(0)
s = seg_re.sub(seg_sub, s)
s = via_re.sub(via_sub, s)
missing = [DEL_SEGS[i] for i in range(len(DEL_SEGS)) if ("seg", i) not in found] + \
          [DEL_VIAS[i] for i in range(len(DEL_VIAS)) if ("via", i) not in found]
if missing:
    sys.exit("not found for deletion: %r" % missing)

# --- 2. add segments / vias (before the first zone) -----------------------
def seg_txt(net, layer, w, a, b):
    return (f'\n\t(segment\n\t\t(start {fmt(a[0])} {fmt(a[1])})\n\t\t(end {fmt(b[0])} {fmt(b[1])})'
            f'\n\t\t(width {fmt(w)})\n\t\t(layer "{layer}")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
def via_txt(net, at, size, drill):
    return (f'\n\t(via\n\t\t(at {fmt(at[0])} {fmt(at[1])})\n\t\t(size {fmt(size)})\n\t\t(drill {fmt(drill)})'
            f'\n\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)')
new = "".join(seg_txt(*t) for t in ADD_SEGS) + "".join(via_txt(*v) for v in ADD_VIAS)
zi = s.find("\n\t(zone")
s = s[:zi] + new + s[zi:]

# --- 3. J1 pad nets --------------------------------------------------------
i = s.find('(property "Reference" "J1"'); start = s.rfind("\n\t(footprint", 0, i); end = s.find("\n\t(footprint", start + 10)
blk = s[start:end]
def pad_sub(m):
    num = m.group(1); body = m.group(2)
    body = re.sub(r'\n\t\t\t\(net "[^"]*"\)', "", body)
    net = NEW_PAD_NETS[num]
    if net:
        body = body.replace("\n\t\t\t(remove_unused_layers no)", f'\n\t\t\t(remove_unused_layers no)\n\t\t\t(net "{net}")')
    return f'(pad "{num}"{body}\n\t\t)'
blk2 = re.sub(r'\(pad "(\d+)"(.*?)\n\t\t\)', pad_sub, blk, flags=re.S)
assert blk2 != blk
s = s[:start] + blk2 + s[end:]

# --- 4. drop stale zone fills ----------------------------------------------
n_fill = 0
while True:
    fi = s.find("\n\t\t(filled_polygon")
    if fi < 0: break
    depth = 0; j = fi + 1
    while True:
        c = s[j]
        if c == "(": depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0: break
        j += 1
    s = s[:fi] + s[j + 1:]; n_fill += 1

open(PCB, "w").write(s)
print(f"deleted {len(DEL_SEGS)} segments + {len(DEL_VIAS)} vias, added {len(ADD_SEGS)} segments + {len(ADD_VIAS)} vias, "
      f"renetted J1, dropped {n_fill} zone fills -> refill zones in pcbnew before export")
