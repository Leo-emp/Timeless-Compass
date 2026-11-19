import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from lib import common, sets
common.reset_scene()
sets.salamis_dusk()
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != 'MESH' or o.name.startswith(('Cube', 'Sphere')):
        continue
    ev = o.evaluated_get(dg); me = ev.to_mesh()
    cs = [ev.matrix_world @ v.co for v in me.vertices]
    if cs:
        print("OBJ", o.name, len(cs), [round(min(c[i] for c in cs), 1) for i in range(3)], [round(max(c[i] for c in cs), 1) for i in range(3)])
    ev.to_mesh_clear()
