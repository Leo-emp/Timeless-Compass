# CAMERA GRAMMAR TEST (WS8, Session D): one short clip per move on a simple dusk set with two standing figures
# (code-built stand-ins, no cloth: this tests the CAMERA, not the people).
# Run: blender -b --python blender/scenes/camera_grammar_test.py -- <out_prefix> [move] [samples]
#   move: dolly_zoom | rack_focus | handheld | impact | whip | lens_sheet
#   lens_sheet = one still per LENS_KIT shot type (close .. establishing) of the same figure
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, camera_moves as cm, countryside as cs, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'camtest'
MOVE = argv[1] if len(argv) > 1 else 'dolly_zoom'
SAMPLES = int(argv[2]) if len(argv) > 2 else 12

common.reset_scene()
bpy.ops.mesh.primitive_plane_add(size=400); g = bpy.context.object
g.data.materials.append(cs.soil_material('cam_ground', scan='coast_sand_rocks_02', tint=(1.0, 0.95, 0.85), tiles=2.0))
cs.dry_stone_wall([(-12, 14), (12, 16)], height=1.2, seed=1, name='backwall')        # depth cues behind
for i, x in enumerate((-30, -10, 14, 36)):
    bpy.ops.mesh.primitive_cone_add(radius1=3, depth=12, location=(x, 60 + 25 * i, 6)); bpy.context.object.data.materials.append(
        common.principled('cypress_standin', (0.05, 0.09, 0.04), rough=0.8))
sets.land('cam_hills', (0, 500, -2), (900, 250), 200, rough=20, noise=36, seed=2)
def figure(name, loc, color):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.5, location=(loc[0], loc[1], 0.75))
    body = bpy.context.object; body.name = name; body.data.materials.append(common.principled(name + '_m', color, rough=0.7))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(loc[0], loc[1], 1.65))
    head = bpy.context.object; head.data.materials.append(common.principled('skin_standin', (0.5, 0.33, 0.24), rough=0.5))
    head.parent = body; head.matrix_parent_inverse = body.matrix_world.inverted()
    return head
near = figure('near', (0.6, 0, 0), (0.3, 0.05, 0.04))           # foreground figure (madder)
far = figure('far', (-1.2, 6, 0), (0.07, 0.1, 0.26))            # background figure (woad)
common.hdri_sky('qwantani_sunset_puresky', background=0.8, lighting=0.3, rotate_deg=140)
common.sun_light('sun', 3.5, (1.0, 0.65, 0.38), 9, 220)
sets.haze(size=(3000, 3000, 400), density=0.00025, color=(1.0, 0.72, 0.5))

sc = bpy.context.scene
bpy.ops.object.camera_add(location=(1.4, -4.0, 1.6)); cam = bpy.context.object; sc.camera = cam
cam.data.clip_end = 5000
common.look_at(cam, near.matrix_world.translation)
common.render_settings(res=(640, 360), samples=SAMPLES, path=OUT)
sc.view_settings.look = 'AgX - High Contrast'
sc.render.fps = 24

if MOVE == 'lens_sheet':
    head = near.matrix_world.translation
    for st in ('close', 'medium', 'full', 'wide', 'establishing'):
        dist = cm.apply_lens(cam, st, focus=near)
        cam.location = head + Vector((0.35 * dist, -dist, 0.05 * dist)); common.look_at(cam, head)
        sc.render.filepath = f'{OUT}_{st}.png'
        bpy.ops.render.render(write_still=True)
    raise SystemExit
cm.apply_lens(cam, 'medium', focus=near)
sc.frame_start, sc.frame_end = 1, 48
if MOVE == 'dolly_zoom':
    cam.data.lens = 28
    cam.location = near.matrix_world.translation + Vector((0.4, -2.2, 0.0)); common.look_at(cam, near.matrix_world.translation)
    cm.dolly_zoom(cam, near, 1, 48, pull=1.5)
elif MOVE == 'rack_focus':
    cm.apply_lens(cam, 'close', focus=near)
    cam.location = Vector((1.6, -2.2, 1.65)); common.look_at(cam, (near.matrix_world.translation + far.matrix_world.translation) / 2)
    cm.rack_focus(cam, near, far, frame=16, pull_frames=18, hold_from=1)
elif MOVE == 'handheld':
    cam.keyframe_insert('location', frame=1); cam.keyframe_insert('rotation_euler', frame=1)
    cm.handheld_v2(cam, strength=2.0, seed=3)
elif MOVE == 'impact':
    cam.keyframe_insert('location', frame=1); cam.keyframe_insert('rotation_euler', frame=1)
    cm.impact_shake(cam, 14, strength=1.5)
elif MOVE == 'whip':
    cm.whip_pan(cam, 20, frames=6, degrees=80)
sc.render.filepath = f'{OUT}_{MOVE}_'
bpy.ops.render.render(animation=True)
