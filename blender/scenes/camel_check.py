# QUICK CHECK (no render): load the camel scan, clean it, print what is left and where (debug the caravan).
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, scatter, market
common.reset_scene()
vs = scatter.load_scan('animal_camels')
for c in vs:
    print('CAMEL collection', c.name, [(o.name, o.type, tuple(round(x, 3) for x in o.scale)) for o in c.objects][:12])
    market._clean_camel_collection(c)
    bpy.context.view_layer.update()
    for o in c.objects:
        if o.type == 'MESH':
            pts = [o.matrix_world @ Vector(b) for b in o.bound_box]
            print('CAMEL mesh', o.name, 'verts', len(o.data.vertices), 'zmin', round(min(p.z for p in pts), 3), 'zmax', round(max(p.z for p in pts), 3),
                  'mods', [m.type for m in o.modifiers], 'parent', o.parent.name if o.parent else None)
    print('CAMEL offset', tuple(round(x, 3) for x in c.instance_offset))
print('CAMEL done')
