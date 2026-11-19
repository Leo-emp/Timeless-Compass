# WS7 DIAGNOSTIC: does the cloth solver run in background mode? Prints how far the sail cloth moved.
# Run: blender -b --python blender/scenes/ws7_debug_cloth.py -- <out.png>
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector

from lib import common

common.reset_scene()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 60

# a 4 x 3 m cloth, pinned along the top, wind from -X
bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=18, size=1, location=(0, 0, 0), rotation=(math.radians(90), 0, math.radians(90)))
ob = bpy.context.object; ob.scale = (4, 3, 1)
bpy.ops.object.transform_apply(scale=True, rotation=True)
pin = ob.vertex_groups.new(name='pin')
top = max(v.co.z for v in ob.data.vertices)
pin.add([v.index for v in ob.data.vertices if v.co.z > top - 1e-4], 1.0, 'REPLACE')
cl = ob.modifiers.new('cloth', 'CLOTH'); cl.settings.vertex_group_mass = 'pin'
cl.point_cache.frame_start = 1; cl.point_cache.frame_end = 60
bpy.ops.object.effector_add(type='WIND', location=(-4, 0, 0), rotation=(0, math.radians(90), 0))
bpy.context.object.field.strength = 9.0


def stats(tag):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg); me = e.to_mesh()
    xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    print('CLOTHDBG', tag, 'frame', sc.frame_current, 'x range', round(min(xs), 3), round(max(xs), 3), 'z min', round(min(zs), 3))
    e.to_mesh_clear()


stats('start')
for f in range(1, 61):                                   # method A: step frames
    sc.frame_set(f)
    if f in (2, 10, 30, 60):
        stats('A')
# method B: explicit bake with a context override
try:
    with bpy.context.temp_override(scene=sc, active_object=ob, point_cache=cl.point_cache):
        bpy.ops.ptcache.free_bake_all()
        bpy.ops.ptcache.bake_all(bake=True)
    sc.frame_set(60); stats('B baked')
except Exception as ex:
    print('CLOTHDBG B failed', ex)
common.camera('cam', Vector((8, -6, 1)), Vector((0, 0, -1)), lens=35)
common.sun_light('sun', 3.0, (1, 1, 1), 40, 30)
common.render_settings(res=(480, 270), samples=8, path=os.path.abspath(sys.argv[sys.argv.index('--') + 1]))
common.render()
