# WS7 TEST: ships of 480 BC in the Salamis strait at dusk.
#   fleet  - a Phoenician admiral's trireme (red-brown, shields, high deck), an Athenian trireme v2 ROWING with
#            crew stand-ins, a trireme v2 under SAIL farther off, two fishing boats near the camera
#   oars   - side view of trireme v2 rowing, to check the stroke (render two frames: catch and finish)
#   boats  - close look at the fishing boat (nets, catch basket, rope, anchor, eyes)
# Run: blender -b --python blender/scenes/ws7_ships.py -- <out.png> [samples] [variant] [frame]
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, sets

OUT, SAMPLES, VARIANT = W.args('ships_v1.png')
VARIANT = VARIANT or 'fleet'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FRAME = int(argv[3]) if len(argv) > 3 else 1

common.reset_scene()
sets.salamis_dusk()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 240
sun = bpy.data.objects['sun']; sun.data.energy = 8.0
sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(118))
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25

if VARIANT == 'fleet':
    props.trireme_v2((-12, 42, 0), heading_deg=25, oars='row', crew='proxies', speed_mps=4.0, name='athenian')
    props.trireme_phoenician((-60, 95, 0), heading_deg=-160, admiral=True, name='sidon')
    props.trireme_v2((8, 150, 0), heading_deg=165, oars=None, sail='set', crew='proxies', name='cruiser')   # broadside, sail visible
    props.fishing_boat((6, 14, 0), heading_deg=-50, oars='rest', seed=1, name='fisher_a')
    props.fishing_boat((-6, 22, 0), heading_deg=120, oars='in', seed=2, name='fisher_b')
    common.camera('cam', Vector((12.0, 3.0, 2.0)), Vector((-4.0, 45.0, 3.0)), lens=32)
elif VARIANT == 'oars':
    props.trireme_v2((0, 30, 0), heading_deg=0, oars='row', crew='proxies', name='rower')
    common.camera('cam', Vector((17.0, 8.0, 3.2)), Vector((17.0, 30.0, 1.8)), lens=35)
else:
    props.fishing_boat((0, 6, 0), heading_deg=-35, oars='rest', seed=3, name='fisher')
    common.camera('cam', Vector((7.5, -3.0, 2.6)), Vector((2.6, 7.0, 0.5)), lens=35)

sc.frame_set(FRAME)
common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
sc.view_settings.look = 'AgX - High Contrast'
sc.view_settings.exposure = 0.4
common.render()
