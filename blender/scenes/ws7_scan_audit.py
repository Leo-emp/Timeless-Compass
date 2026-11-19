# WS7 AUDIT: import every Sketchfab scan in library/scans and check it the way the owner's camel failed:
#   - HELPER MESHES: ground/shadow planes, backdrops, stands (flat + wide, or helper-like names)
#   - LOD STACKS: two or more meshes occupying the same space (same bounds) = duplicates rendered on top of each other
#   - LOST TEXTURES: image nodes with no image / 0-pixel image / unsupported format; materials with no texture at all
#   - SCALE: real size after import (with Sketchfab's own matrices) vs. a plausible real-world range
# Writes spike/lib_stills/ws7/scan_audit.json and prints one line per scan. No render (runs in ~1 min).
# Run: blender -b --python blender/scenes/ws7_scan_audit.py
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector

from lib import common

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SCANS = os.path.join(REPO, 'library', 'scans')
OUT = os.path.join(REPO, 'spike', 'lib_stills', 'ws7', 'scan_audit.json')
HELPER = re.compile(r'(plane|ground|floor|shadow|backdrop|background|pedestal|platform|turntable|camera|light|collider|proxy|helper)', re.I)
# plausible overall size (largest dimension, metres) for each kind of thing - outside it = "scale?"
RANGES = [(r'^tree_', (3.0, 30.0)), (r'elephant', (3.0, 7.5)), (r'camel', (1.8, 3.6)), (r'horse', (1.6, 3.2)),
          (r'(cow|zebu|bull)', (1.6, 3.2)), (r'donkey', (1.2, 2.4)), (r'(boar|goat|sheep|dog|hound)', (0.5, 1.8)),
          (r'(cat|chicken|pigeon|raven|seagull)', (0.15, 1.6)), (r'(amphora|krater|kylix|helmet)', (0.15, 0.7))]


def bbox(objs):
    pts = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in objs:
        if o.type == 'MESH':
            e = o.evaluated_get(dg)
            pts += [e.matrix_world @ Vector(c) for c in e.bound_box]
    if not pts:
        return Vector(), Vector()
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


report = {}
for asset in sorted(os.listdir(SCANS)):
    aj = os.path.join(SCANS, asset, 'asset.json'); glb = os.path.join(SCANS, asset, 'model.glb')
    if not os.path.exists(aj) or json.load(open(aj, encoding='utf-8')).get('kind') != 'sketchfab' or not os.path.exists(glb):
        continue
    common.reset_scene()
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=glb, import_shading='NORMALS', bone_heuristic='TEMPERANCE')
    except Exception as ex:
        report[asset] = {'issues': [f'IMPORT FAILED: {ex}']}; print('AUDIT', asset, 'IMPORT FAILED', ex); continue
    new = [o for o in bpy.data.objects if o not in before]
    rig = next((o for o in new if o.type == 'ARMATURE'), None)
    if rig:
        rig.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    meshes = [o for o in new if o.type == 'MESH']
    issues = []
    # helpers: flat + big, or helper names
    lo, hi = bbox(meshes); size = hi - lo; biggest = max(size) if meshes else 0
    for o in meshes:
        l, h = bbox([o]); d = h - l
        flat = min(d) < 0.01 * max(max(d), 1e-6) and max(d) > 0.6 * biggest
        if flat or HELPER.search(o.name) or HELPER.search(o.data.name):
            issues.append(f'helper? {o.name} ({"flat " if flat else ""}{[round(x, 2) for x in d]})')
    # LOD stacks: meshes with (almost) the same bounds
    boxes = [(o, *bbox([o])) for o in meshes]
    for i in range(len(boxes)):
        for k in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[k]
            split = len(a[0].data.vertices) >= 65000 or len(b[0].data.vertices) >= 65000   # Sketchfab 65k-vertex chunks
            same_mat = a[0].data.materials[:1] == b[0].data.materials[:1]
            if (not (split and same_mat) and (a[1] - b[1]).length < 0.02 * biggest and (a[2] - b[2]).length < 0.02 * biggest
                    and max(a[2] - a[1]) > 0.3 * biggest):
                issues.append(f'LOD/duplicate? {a[0].name} == {b[0].name}')
    # textures
    mats = {s.material for o in meshes for s in o.material_slots if s.material}
    for m in mats:
        texs = [n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'] if m.use_nodes else []
        if not texs:
            issues.append(f'no texture: material {m.name}')
        for n in texs:
            if n.image is None:
                issues.append(f'LOST texture node in {m.name}')
            elif n.image.size[0] == 0:
                issues.append(f'LOST image {n.image.name} in {m.name} (0 px)')
    # scale
    rng = next((r for pat, r in RANGES if re.search(pat, asset)), None)
    if rng and not (rng[0] <= biggest <= rng[1]):
        issues.append(f'scale? imports {biggest:.2f} m, expected {rng[0]}-{rng[1]} m (needs a size in its loader)')
    report[asset] = {'meshes': len(meshes), 'rigged': bool(rig), 'size_m': [round(x, 3) for x in size],
                     'materials': len(mats), 'issues': issues}
    print('AUDIT', asset, f'{len(meshes)} meshes', [round(x, 2) for x in size], '|', '; '.join(issues) or 'OK')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(report, open(OUT, 'w', encoding='utf-8'), indent=2)
print('AUDIT written', OUT)
