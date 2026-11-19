import os, sys
sys.path.insert(0, 'C:/Users/User/timeless-compass/blender')
import bpy, numpy as np
from lib import common, cast
common.reset_scene()
h, rig = cast.build_human({"macro": {"gender": 1.0, "age": 0.68, "muscle": 0.7, "weight": 0.55, "proportions": 0.7, "height": 0.6, "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.05, "caucasian": 0.82, "african": 0.13}}})
pos, nor, tris = cast.rest_surface(h)
hb = np.array(rig.matrix_world @ rig.data.bones['head'].head_local)
print('HEADBONE', hb.round(3))
for g in sorted(vg.name for vg in h.vertex_groups):
    if g.startswith(('jaw','oris','levator','risorius','special','head','neck','lips','scalp','temporalis','orbicularis','oculi','ears')):
        w = cast.group_weights(h, g); m = w > 0.3
        if m.sum():
            p = pos[m] - hb
            print(f"{g:16s} n={m.sum():5d} x[{p[:,0].min():+.3f},{p[:,0].max():+.3f}] y[{p[:,1].min():+.3f},{p[:,1].max():+.3f}] z[{p[:,2].min():+.3f},{p[:,2].max():+.3f}]")
# skin material structure
for s in h.material_slots:
    m = s.material
    print('MAT', m.name, [ (n.type, n.name, getattr(getattr(n,'image',None),'name',None)) for n in m.node_tree.nodes][:12])
