# Generates sticks3-bot-hat.kicad_sch from design.py.
#
# Strategy: embed the needed KiCad library symbols verbatim, place one
# instance per component on a coarse grid, and attach a global net label
# directly at every connected pin. No drawn wires — the global labels carry
# the connectivity, and the net names come from the same table the PCB is
# generated from, so the two cannot diverge.
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "sticks3-bot-hat.kicad_sch")
SYM_DIR = os.path.expanduser(
    "~/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols")

PROJECT = "sticks3-bot-hat"


def U():
    return str(uuid.uuid4())


def extract_symbol(lib, name):
    """Return the s-expr block for `name` from lib, flattening `extends`."""
    txt = open(os.path.join(SYM_DIR, lib + ".kicad_sym")).read()

    def block(sym):
        i = txt.index(f'(symbol "{sym}"')
        depth = 0
        for j in range(i, len(txt)):
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    return txt[i:j + 1]
        raise ValueError(sym)

    b = block(name)
    m = re.search(r'\(extends "([^"]+)"\)', b)
    if m:
        parent = m.group(1)
        pb = block(parent)
        # graft: parent geometry/pins with the child's name and properties
        child_props = dict(re.findall(r'\(property "(Reference|Value|Footprint|Datasheet)" "([^"]*)"', b))
        pb = pb.replace(f'(symbol "{parent}"', f'(symbol "{name}"', 1)
        pb = pb.replace(f'"{parent}_', f'"{name}_')
        for k, v in child_props.items():
            pb = re.sub(r'(\(property "%s" ")[^"]*(")' % k,
                        lambda mm: mm.group(1) + v + mm.group(2), pb, count=1)
        b = pb
    return b


def rename_symbol(block, name, libid):
    block = block.replace(f'(symbol "{name}"', f'(symbol "{libid}"', 1)
    return block


def pin_positions(block):
    """{number: (x, y, angle)} for every pin in a symbol block."""
    pins = {}
    for m in re.finditer(
            r'\(pin\s+\S+\s+\S+\s*\(at\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\)'
            r'[\s\S]*?\(number\s+"([^"]+)"', block):
        x, y, a, num = float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4)
        pins[num] = (x, y, a)
    return pins


# --- collect symbols --------------------------------------------------------
needed = {}   # libid -> block
pinmaps = {}  # libid -> {num: (x,y,angle)}
for ref, comp in design.COMPONENTS.items():
    lib, sym = comp[0], comp[1]
    libid = f"{lib}:{sym}"
    if libid not in needed:
        blk = extract_symbol(lib, sym)
        pinmaps[libid] = pin_positions(blk)
        needed[libid] = rename_symbol(blk, sym, libid)

# power flags for nets that have power_in pins / power rails
pwr_block = extract_symbol("power", "PWR_FLAG")
pinmaps["power:PWR_FLAG"] = pin_positions(pwr_block)
needed["power:PWR_FLAG"] = rename_symbol(pwr_block, "PWR_FLAG", "power:PWR_FLAG")

# --- place instances --------------------------------------------------------
ORDER = sorted(design.COMPONENTS)
COLS = 6
DX, DY = 50.0, 45.0
X0, Y0 = 40.0, 40.0

body = []


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def add_instance(ref, libid, value, footprint, x, y):
    pins = pinmaps[libid]
    plist = "\n".join(f'    (pin "{n}" (uuid "{U()}"))' for n in pins)
    body.append(f'''  (symbol
    (lib_id "{esc(libid)}")
    (at {x} {y} 0)
    (unit 1)
    (exclude_from_sim no)
    (in_bom yes)
    (on_board yes)
    (dnp no)
    (uuid "{U()}")
    (property "Reference" "{ref}" (at {x} {y - 3.5} 0)
      (effects (font (size 1.27 1.27))))
    (property "Value" "{esc(value)}" (at {x} {y + 3.5} 0)
      (effects (font (size 1.27 1.27))))
    (property "Footprint" "{esc(footprint)}" (at {x} {y} 0)
      (effects (font (size 1.27 1.27)) (hide yes)))
{plist}
    (instances
      (project "{PROJECT}"
        (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))))
  )''')


def add_label(net, x, y, rot):
    body.append(f'''  (global_label "{esc(net)}"
    (shape input)
    (at {x} {y} {rot})
    (effects (font (size 1.0 1.0)) (justify left))
    (uuid "{U()}")
  )''')


ROOT_UUID = U()

for i, ref in enumerate(ORDER):
    comp = design.COMPONENTS[ref]
    lib, sym, value, kind, fplib, fpname = comp[0], comp[1], comp[2], comp[3], comp[4], comp[5]
    pads = comp[7]
    libid = f"{lib}:{sym}"
    x = X0 + (i % COLS) * DX
    y = Y0 + (i // COLS) * DY
    fpid = (f"{fplib}:{fpname}" if kind == design.STD_FP
            else f"sticks3-bot-hat:{fpname}")
    add_instance(ref, libid, value, fpid, x, y)
    # net labels at connected pins
    for num, (px, py, ang) in pinmaps[libid].items():
        net = pads.get(num)
        gx, gy = round(x + px, 3), round(y - py, 3)
        if not net:
            if num in pads:  # explicitly not connected
                body.append(f'  (no_connect (at {gx} {gy}) (uuid "{U()}"))')
            continue
        out = (ang + 180) % 360
        rot = {0: 0, 90: 270, 180: 180, 270: 90}[out]
        add_label(net, gx, gy, rot)

# PWR_FLAG on the driven rails (ERC: something must drive power_in pins)
flag_pin = pinmaps["power:PWR_FLAG"]["1"]
for i, net in enumerate(["GND", "VSERVO", "+5V", "+3V3"]):
    x = X0 + i * 25.0
    y = Y0 + 5 * DY
    add_instance(f"#FLG0{i+1}", "power:PWR_FLAG", net, "", x, y)
    gx, gy = round(x + flag_pin[0], 3), round(y - flag_pin[1], 3)
    out = (flag_pin[2] + 180) % 360
    add_label(net, gx, gy, {0: 0, 90: 270, 180: 180, 270: 90}[out])

libsyms = "\n".join(needed.values())
sch = f'''(kicad_sch
  (version 20250114)
  (generator "eeschema")
  (generator_version "9.0")
  (uuid "{ROOT_UUID}")
  (paper "A2")
  (title_block
    (title "PySTEM Mini Bot - StickS3 HAT")
    (rev "2.0")
    (comment 1 "M5StickS3 flat-mount HAT2 carrier: 4x servo, 2x encoder, color sensor, 6V->5V buck")
  )
  (lib_symbols
{libsyms}
  )
{chr(10).join(body)}
  (sheet_instances
    (path "/" (page "1"))
  )
)
'''
open(OUT, "w").write(sch)
print("saved", os.path.abspath(OUT))
