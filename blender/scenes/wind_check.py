# QUICK CHECK (no render, ~20 s): build a small wind field + a vine row, evaluate the geometry nodes, and print
# how many instances exist and how much they move between two frames (the wind must make them move).
# Run: blender -b --python blender/scenes/wind_check.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
import numpy as np
from lib import common, countryside as cs

common.reset_scene()
f = cs.grain_field('chk', size=(6.0, 4.0), state='ripe', density=10, seed=1)
bpy.ops.mesh.primitive_plane_add(size=20); g = bpy.context.object
v = cs.vineyard(g, (-3, 3, 6, 9), seed=2)


def snapshot(obj, frame):
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    mats = [np.array(i.matrix_world) for i in dg.object_instances if i.is_instance and i.parent and i.parent.original == obj]
    return mats


for name, obj in (('wheat field', f), ('vineyard', v.id_data if hasattr(v, 'id_data') else None)):
    if obj is None:
        continue
    a, b = snapshot(obj, 1), snapshot(obj, 30)
    move = max((np.abs(x[:3, :3] - y[:3, :3]).max() for x, y in zip(a, b)), default=0.0)
    print(f'WINDCHECK {name}: {len(a)} instances, max rotation change frame 1->30 = {move:.4f}')
print('WINDCHECK done')
