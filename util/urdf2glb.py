"""Convert an Onshape URDF export (glTF meshes with embedded buffers) into the
files parts.html loads: compact GLBs (one per mesh file, primitives merged by
material), assembly.json with each link's world placement, and binary STLs
(mm) for the 3D printed parts: the ones coloured red in Onshape, plus the wheel.

Usage: python3 util/urdf2glb.py <unzipped export dir containing urdf/ meshes/> parts
Needs numpy."""
import base64, json, math, os, struct, sys
import xml.etree.ElementTree as ET
import numpy as np

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

def read_accessor(d, bufs, idx):
    a = d['accessors'][idx]; bv = d['bufferViews'][a['bufferView']]
    buf = bufs[bv['buffer']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    ncomp = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    dt = {5126: '<f4', 5123: '<u2', 5125: '<u4', 5121: '<u1'}[a['componentType']]
    n = a['count'] * ncomp
    arr = np.frombuffer(buf, dtype=dt, count=n, offset=off)
    return arr.reshape(a['count'], ncomp) if ncomp > 1 else arr

def convert(path):
    d = json.load(open(path))
    bufs = []
    for b in d['buffers']:
        uri = b['uri']; assert uri.startswith('data:')
        bufs.append(base64.b64decode(uri.split(',', 1)[1]))
    groups = {}  # material index -> [positions, normals, indices]
    for m in d['meshes']:
        for p in m['primitives']:
            g = groups.setdefault(p.get('material', 0), ([], [], [], 0))
            pos = read_accessor(d, bufs, p['attributes']['POSITION']).astype('<f4')
            nor = read_accessor(d, bufs, p['attributes']['NORMAL']).astype('<f4')
            ind = read_accessor(d, bufs, p['indices']).astype('<u4') + g[3]
            g[0].append(pos); g[1].append(nor); g[2].append(ind)
            groups[p.get('material', 0)] = (g[0], g[1], g[2], g[3] + len(pos))
    bin_parts = []; views = []; accs = []; prims = []; mats = []
    def add_view(arr):
        data = arr.tobytes()
        off = sum(len(b) for b in bin_parts)
        pad = (-len(data)) % 4
        bin_parts.append(data + b'\0' * pad)
        views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(data)})
        return len(views) - 1
    for mi, (P, N, I, _) in groups.items():
        P = np.concatenate(P); N = np.concatenate(N); I = np.concatenate(I)
        accs.append({'bufferView': add_view(P), 'componentType': 5126, 'count': len(P), 'type': 'VEC3',
                     'min': P.min(0).tolist(), 'max': P.max(0).tolist()})
        accs.append({'bufferView': add_view(N), 'componentType': 5126, 'count': len(N), 'type': 'VEC3'})
        accs.append({'bufferView': add_view(I), 'componentType': 5125, 'count': len(I), 'type': 'SCALAR'})
        src_mat = d['materials'][mi]
        mats.append({'name': src_mat.get('name', ''), 'doubleSided': True,
                     'pbrMetallicRoughness': {'baseColorFactor': src_mat['pbrMetallicRoughness']['baseColorFactor'],
                                              'metallicFactor': 0.0, 'roughnessFactor': 0.7}})
        prims.append({'attributes': {'POSITION': len(accs) - 3, 'NORMAL': len(accs) - 2},
                      'indices': len(accs) - 1, 'material': len(mats) - 1})
    binary = b''.join(bin_parts)
    gltf = {'asset': {'version': '2.0', 'generator': 'pystem urdf2glb'}, 'scene': 0,
            'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}], 'meshes': [{'primitives': prims}],
            'materials': mats, 'accessors': accs, 'bufferViews': views, 'buffers': [{'byteLength': len(binary)}]}
    js = json.dumps(gltf, separators=(',', ':')).encode()
    js += b' ' * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    glb = struct.pack('<III', 0x46546C67, 2, total) + struct.pack('<II', len(js), 0x4E4F534A) + js \
        + struct.pack('<II', len(binary), 0x004E4942) + binary
    tris = sum(len(g[2]) for g in groups.values())
    return glb, sum(len(np.concatenate(g[2])) for g in groups.values()) // 3

def rpy_to_mat(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def origin_to_T(el):
    T = np.eye(4)
    if el is not None:
        xyz = [float(v) for v in el.get('xyz', '0 0 0').split()]
        rpy = [float(v) for v in el.get('rpy', '0 0 0').split()]
        T[:3, :3] = rpy_to_mat(*rpy); T[:3, 3] = xyz
    return T

def mat_to_quat(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1) * 2; return [(R[2,1]-R[1,2])/s, (R[0,2]-R[2,0])/s, (R[1,0]-R[0,1])/s, 0.25*s]
    i = int(np.argmax(np.diag(R)))
    if i == 0:
        s = math.sqrt(1 + R[0,0] - R[1,1] - R[2,2]) * 2
        return [0.25*s, (R[0,1]+R[1,0])/s, (R[0,2]+R[2,0])/s, (R[2,1]-R[1,2])/s]
    if i == 1:
        s = math.sqrt(1 + R[1,1] - R[0,0] - R[2,2]) * 2
        return [(R[0,1]+R[1,0])/s, 0.25*s, (R[1,2]+R[2,1])/s, (R[0,2]-R[2,0])/s]
    s = math.sqrt(1 + R[2,2] - R[0,0] - R[1,1]) * 2
    return [(R[0,2]+R[2,0])/s, (R[1,2]+R[2,1])/s, 0.25*s, (R[1,0]-R[0,1])/s]

root = ET.parse(os.path.join(src, 'urdf', 'assembly.urdf')).getroot()
links = {l.get('name'): l for l in root.findall('link')}
parent_of = {}
for j in root.findall('joint'):
    parent_of[j.find('child').get('link')] = (j.find('parent').get('link'), origin_to_T(j.find('origin')))
world = {}
def world_T(name):
    if name in world: return world[name]
    if name not in parent_of: world[name] = np.eye(4); return world[name]
    p, T = parent_of[name]; world[name] = world_T(p) @ T; return world[name]

converted = {}; placements = []
for name, l in links.items():
    vis = l.find('visual')
    if vis is None: continue
    mesh_file = vis.find('geometry/mesh').get('filename').split('/')[-1]
    key = os.path.splitext(mesh_file)[0].lower()
    if key not in converted:
        glb, tris = convert(os.path.join(src, 'meshes', mesh_file))
        open(os.path.join(out, key + '.glb'), 'wb').write(glb)
        converted[key] = {'file': key + '.glb', 'tris': tris, 'bytes': len(glb)}
    T = world_T(name) @ origin_to_T(vis.find('origin'))
    color = vis.find('material/color')
    placements.append({'link': name, 'mesh': key, 'position': [round(v, 6) for v in T[:3, 3]],
                       'quaternion': [round(v, 6) for v in mat_to_quat(T[:3, :3])],
                       'color': [float(v) for v in color.get('rgba').split()[:3]] if color is not None else None})
json.dump({'units': 'm', 'up': 'z', 'meshes': converted, 'links': placements},
          open(os.path.join(out, 'assembly.json'), 'w'), indent=1)
for k, v in converted.items(): print(f"{k:16s} {v['tris']:6d} tris {v['bytes']/1024:7.0f} KB")

# --- binary STL (mm) for the 3D printed parts: the ones Onshape coloured red,
# plus the wheel (hub with the encoder disk built in), which is grey in the CAD ---
PRINTED = [p['mesh'] for p in placements if p['color'] == [1.0, 0.0, 0.0]] + ['wheel']
os.makedirs(os.path.join(out, 'stl'), exist_ok=True)
for key in sorted(set(PRINTED)):
    d = json.load(open(os.path.join(src, 'meshes', next(f for f in os.listdir(os.path.join(src, 'meshes')) if f.lower() == key + '.gltf'))))
    bufs = [base64.b64decode(b['uri'].split(',', 1)[1]) for b in d['buffers']]
    tris = []
    for m in d['meshes']:
        for p in m['primitives']:
            P = read_accessor(d, bufs, p['attributes']['POSITION']).astype('<f8') * 1000.0
            I = read_accessor(d, bufs, p['indices']).astype(int).reshape(-1, 3)
            tris.append(P[I])
    T = np.concatenate(tris)              # (n, 3, 3) mm
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(T), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    rec['n'] = n; rec['v'] = T
    with open(os.path.join(out, 'stl', key + '.stl'), 'wb') as f:
        f.write(b'PySTEM Mini Bot ' + key.encode().ljust(64)[:64]); f.write(struct.pack('<I', len(T))); f.write(rec.tobytes())
    print('stl', key, len(T), 'tris', 'bbox mm', (T.reshape(-1, 3).max(0) - T.reshape(-1, 3).min(0)).round(1))
