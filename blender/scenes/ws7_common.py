# WS7 test-scene helpers (Session E): a small dark room to judge props in, and the standard test-still settings.
# Props are judged in MOODY light (rule r10: real deep shadows), not on a bright studio sweep - that is how they
# will appear in the films (lamp-lit interiors, dusk harbours).
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector

from lib import common, scatter

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
STILLS = os.path.join(REPO, 'spike', 'lib_stills', 'ws7')


def args(default_name):
    """Command line after '--': <out.png> [samples] [variant]."""
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = os.path.abspath(argv[0]) if argv else os.path.join(STILLS, default_name)   # Blender reads relative paths from C:\ - always absolute
    samples = int(argv[1]) if len(argv) > 1 else 20
    variant = argv[2] if len(argv) > 2 else ''
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    return out, samples, variant


def room(w=8.0, d=6.0, h=3.4, floor='old_sandstone_02', wall='plastered_wall_02', wall_tint=(0.95, 0.88, 0.78),
         floor_tint=(0.85, 0.8, 0.74)):
    """Floor + back wall + one side wall from scanned textures (Poly Haven CC0), so props sit in a real place."""
    fm = scatter.scan_material('ws7_floor', floor, tint=floor_tint, tiles=2.0)
    wm = scatter.scan_material('ws7_wall', wall, tint=wall_tint, tiles=2.5)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); f = bpy.context.object; f.name = 'floor'
    f.scale = (w, d, 1); f.data.materials.append(fm)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, d / 2, h / 2), rotation=(math.radians(90), 0, 0))
    b = bpy.context.object; b.name = 'back_wall'; b.scale = (w, h, 1); b.data.materials.append(wm)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-w / 2, 0, h / 2), rotation=(math.radians(90), 0, math.radians(90)))
    s = bpy.context.object; s.name = 'side_wall'; s.scale = (d, h, 1); s.data.materials.append(wm)
    return f


def dark_world(strength=0.02, color=(0.25, 0.3, 0.4)):
    w = bpy.data.worlds.new('dark'); bpy.context.scene.world = w
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (*color, 1); bg.inputs['Strength'].default_value = strength
    return w


def window_light(target, energy=900.0, loc=(3.5, -2.5, 3.0), size=1.6, color=(1.0, 0.86, 0.68)):
    """Warm side light like late sun through a doorway: one strong soft key, the far side falls into shadow."""
    return common.area_light('key', energy, color, loc, target, size=size)


def finish(out, samples, res=(960, 540), exposure=-0.2):
    common.render_settings(res=res, samples=samples, path=out)
    s = bpy.context.scene
    s.view_settings.look = 'AgX - High Contrast'
    s.view_settings.exposure = exposure
    s.cycles.max_bounces = 6
    common.render()
