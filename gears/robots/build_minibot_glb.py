#!/usr/bin/env python3
"""Rebuild gears/robots/minibot.glb from the Onshape glTF export.

Usage: build_minibot_glb.py <assembly.gltf> [minibot.glb]

Onshape exports the assembly in metres with +X forward, +Y right, +Z down
and an arbitrary origin. GEARS draws the model as a child of the physics
body, whose frame is x right, y up, z forward (cm) with the origin at the
body centre; and Babylon's glTF loader turns a right-handed file into its
left-handed scene with a 180-degree Y rotation plus a Z flip (net: X
flip). So the file is written in (-right, up, forward) and comes out as
(right, up, forward). The conversion is a single root node with a matrix;
vertices are untouched.

Materials are replaced by flat colours matching the real robot, keyed on
part (node) name.
"""
import base64, json, struct, sys
import numpy as np

SRC = sys.argv[1]
DST = sys.argv[2] if len(sys.argv) > 2 else 'minibot.glb'

# Body centre in the Onshape frame, cm (from the measured geometry: chassis
# centre x/y, and 3.65 cm above the wheel contact plane at z = 10.82).
CX, CY, CZ = 6.01, 4.64, 7.17
S = 100.0
M = np.array([
    [0, -S,  0,  CY],   # x_file = -(S*y_on - CY) = -right
    [0,  0, -S,  CZ],   # y_file = -(S*z_on) + CZ  = up
    [S,  0,  0, -CX],   # z_file =  S*x_on - CX    = forward
    [0,  0,  0,  1 ],
], dtype=float)
assert abs(np.linalg.det(M[:3, :3]) - S**3) < 1e-6, "must be a proper rotation times uniform scale"

# Real-robot materials by part name: (key, rgb, roughness, metallic, exact).
# Substring keys match any part containing the key; exact keys match only a
# part named exactly that (so 'ball' does not catch 'ball mount'). The
# default applies to everything else.
COLOURS = [
    ('wheel',       (0.05, 0.05, 0.05), 0.9,  0.0, False),  # black rubber
    ('battery box', (0.05, 0.05, 0.05), 0.9,  0.0, False),  # black plastic
    ('pcb',         (0.05, 0.45, 0.15), 0.9,  0.0, False),  # green solder mask
    ('stick s3',    (0.22, 0.22, 0.24), 0.9,  0.0, False),  # dark grey M5 case
    ('ball',        (0.02, 0.02, 0.02), 0.15, 0.2, True),   # glossy black caster ball
]
DEFAULT = ((1.00, 0.00, 0.00), 0.9, 0.0)             # red printed parts (pure red; PBR lighting softens it on screen)

g = json.load(open(SRC))

# --- re-root into the body frame ---
root = {'name': 'minibot_root', 'matrix': [float(v) for v in M.T.flatten()],
        'children': g['scenes'][0]['nodes']}
g['nodes'].append(root)
g['scenes'][0]['nodes'] = [len(g['nodes']) - 1]

# --- flat colours ---
def material(name, rgb, rough, metal):
    return {'name': name, 'pbrMetallicRoughness': {'baseColorFactor': [rgb[0], rgb[1], rgb[2], 1.0],
                                                    'metallicFactor': metal, 'roughnessFactor': rough}}
g['materials'] = [material('default', *DEFAULT)] + [material(n, c, r, m) for n, c, r, m, _ in COLOURS]

def colour_index(part_name):
    n = part_name.lower().strip()
    for i, (key, _, _, _, exact) in enumerate(COLOURS):
        if (key == n) if exact else (key in n):
            return i + 1
    return 0

mesh_material = {}
for node in g['nodes']:
    if 'mesh' in node:
        mesh_material[node['mesh']] = colour_index(node.get('name', ''))
for mi, mesh in enumerate(g['meshes']):
    idx = mesh_material.get(mi, 0)
    for prim in mesh['primitives']:
        prim['material'] = idx
    mesh['name'] = mesh.get('name', '')

# --- pack as GLB ---
buf = g['buffers'][0]
bin_data = base64.b64decode(buf['uri'].split(',', 1)[1])
del buf['uri']
buf['byteLength'] = len(bin_data)
g['asset']['generator'] = 'ONSHAPE export, re-rooted and recoloured by build_minibot_glb.py'
js = json.dumps(g, separators=(',', ':')).encode()
js += b' ' * ((4 - len(js) % 4) % 4)
bin_data += b'\0' * ((4 - len(bin_data) % 4) % 4)
with open(DST, 'wb') as f:
    f.write(struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_data)))
    f.write(struct.pack('<II', len(js), 0x4E4F534A)); f.write(js)
    f.write(struct.pack('<II', len(bin_data), 0x004E4942)); f.write(bin_data)

names = [g['materials'][i]['name'] for i in range(len(g['materials']))]
for node in g['nodes']:
    if 'mesh' in node:
        print('  %-16s -> %s' % (node.get('name', '?'), names[mesh_material[node['mesh']]]))
print('wrote', DST)
