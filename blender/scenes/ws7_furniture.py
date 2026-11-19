# WS7 TEST: an andron (men's dining room) corner at night, c. 480 BC - kline + trapeza + klismos + footstool,
# chest, kalathos wool basket, oil lamps on a lamp stand and on the table, a bronze brazier with fire glow,
# a clay brazier, a rope coil and a stone anchor by the door (a ship-owner's house).
# Run: blender -b --python blender/scenes/ws7_furniture.py -- <out.png> [samples] [variant]
#   variant ''     = wide room       'close' = lamp + table + klismos detail      'day' = lit by daylight (no fire)
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, scans_glb

OUT, SAMPLES, VARIANT = W.args('furniture_v1.png')
common.reset_scene()
W.room(w=8.0, d=6.0, floor='damaged_plaster', wall='clay_plaster', wall_tint=(0.6, 0.57, 0.52), floor_tint=(0.42, 0.41, 0.4))
W.dark_world(0.015)
lit = VARIANT != 'day'

if VARIANT == 'andron':                   # RICH room from one call: painted shell + symposion + wall clutter
    for o in list(bpy.data.objects):          # the plain test room is not needed: the kit brings its own walls
        bpy.data.objects.remove(o, do_unlink=True)
    W.dark_world(0.01)
    props.dress_andron((0, 0, 0), couches=3, lit=True, seed=2)
    # NIGHT: the lamps and the brazier carry the room; a faint cool spill from the doorway; warm low bounce
    for o in bpy.data.objects:                 # lamp-lit night: every flame light 5x (pools of warm light, dark corners)
        if o.type == 'LIGHT' and o.data.type == 'POINT':
            o.data.energy *= 5.0
            ad = o.data.animation_data             # the flicker keys must scale too, or they override the new energy
            if ad and ad.action:
                for fc in props._fcurves(o.data):
                    for kp in fc.keyframe_points:
                        kp.co.y *= 5.0; kp.handle_left.y *= 5.0; kp.handle_right.y *= 5.0
    common.area_light('door', 60.0, (0.5, 0.62, 1.0), (2.6, 2.2, 2.0), (0.0, 0.0, 1.0), size=0.8)   # cool moon spill
    common.camera('cam', Vector((0.4, -3.2, 1.55)), Vector((-0.1, 1.5, 1.05)), lens=22)
    W.finish(OUT, SAMPLES, exposure=-0.2)
    raise SystemExit
if VARIANT == 'kit':                      # the whole room from one call (dressing kit)
    props.dress_symposion((0, 0.4, 0), couches=3, lit=True, seed=1)
    common.area_light('moon', 200.0, (0.55, 0.65, 1.0), (3.8, -1.5, 2.6), (0.0, 2.0, 0.5), size=1.5)
    common.camera('cam', Vector((0.3, -2.6, 1.7)), Vector((0.0, 1.2, 0.6)), lens=24)
    W.finish(OUT, SAMPLES, exposure=0.0)
    raise SystemExit
props.kline((0.2, 2.35, 0), heading_deg=0)
props.trapeza((0.1, 1.55, 0), heading_deg=0)
props.footstool((-0.9, 1.75, 0), heading_deg=0)
props.klismos((-1.9, 1.6, 0), heading_deg=-30)
props.chest((-3.2, 2.5, 0), heading_deg=90, size=(0.9, 0.5, 0.48), lid='gable')
props.basket((-2.6, 1.05, 0), kind='kalathos', fill=(0.85, 0.82, 0.74), name='wool_basket')   # with raw wool
props.basket((2.1, 1.0, 0), kind='carry', name='market_basket')
props.oil_lamp((0.25, 1.5, 0.5), heading_deg=-60, lit=lit, seed=2, name='table_lamp')
props.lamp_stand((-1.25, 2.6, 0), lit=lit, seed=3)
props.brazier((1.7, 1.9, 0), kind='bronze', lit=lit, power=100.0, seed=4)
props.brazier((2.9, 1.3, 0), kind='clay', lit=lit, power=90.0, flames=False, seed=5, name='clay_brazier')
props.rope_coil((3.0, 0.2, 0), radius=0.3, turns=5, layers=2)
props.stone_anchor((2.4, 0.15, 0), heading_deg=30)
scans_glb.load_glb('kylix_cleveland', loc=(-0.05, 1.6, 0.5), rot_z_deg=20)       # Douris' cup on the table
scans_glb.load_glb('amphora_neck_cleveland', loc=(-2.8, 2.65, 0.0), rot_z_deg=160)

if lit:
    common.area_light('moon', 200.0, (0.55, 0.65, 1.0), (3.8, -1.5, 2.6), (0.0, 2.0, 0.5), size=1.5)   # cool door light
else:
    W.window_light((0.0, 2.0, 0.5), energy=900.0, loc=(3.6, -1.8, 2.6), size=1.8)

if VARIANT == 'close':
    common.camera('cam', Vector((-0.45, 0.55, 0.85)), Vector((0.15, 1.55, 0.52)), lens=45, fstop=2.8, focus=(0.15, 1.52, 0.53))
else:
    common.camera('cam', Vector((0.0, -2.7, 1.55)), Vector((-0.2, 1.9, 0.55)), lens=28)
W.finish(OUT, SAMPLES, exposure=0.0 if lit else -0.3)
