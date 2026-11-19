# WS7 TEST: trireme v3 (detailed hull, instanced kit) in the Salamis strait at dusk.
#   close - three-quarter view along the side: planked pitch hull, wales, open outrigger + thole pins, leather oar
#           sleeves, catheads, painted eye, rigging rope, rowing oars, crew stand-ins
#   sail  - a v3 trireme under its SET sail (folds, brails, wind ripple), broadside
#   fleet - 40 ships (a third Phoenician) deployed in line, near ones rowing, far ones kit-only
# Run: blender -b --python blender/scenes/ws7_ships_v3.py -- <out.png> [samples] [variant] [frame]
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, sets

OUT, SAMPLES, VARIANT = W.args('ships3_close_v1.png')
VARIANT = VARIANT or 'close'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FRAME = int(argv[3]) if len(argv) > 3 else 6

common.reset_scene()
sets.salamis_dusk()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 240
sun = bpy.data.objects['sun']; sun.data.energy = 8.0
sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(118))
sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25

t = time.time()
if VARIANT == 'close':
    props.trireme_v3((0, 30, 0), heading_deg=0, oars='row', crew='proxies', name='hero')
    common.camera('cam', Vector((40.5, 22.0, 3.6)), Vector((22.0, 30.5, 2.6)), lens=35, fstop=5.6, focus=(30.0, 28.0, 2.4))
elif VARIANT == 'sail':
    props.trireme_v3((0, 40, 0), heading_deg=10, oars=None, sail='set', crew='proxies', name='cruiser')
    common.camera('cam', Vector((-24.0, 16.0, 4.5)), Vector((16.0, 43.0, 7.0)), lens=32)   # stern quarter: sail seen full
elif VARIANT == 'quay':                    # dressed harbour quay: amphorae, ropes, anchors, baskets, moored boats
    sets.stone_wall(-14.0, 14.0, 22.0, 1.0, depth=6.0)        # quay: wall face at y = 19, top at z = 1
    props.dress_quay((0, 20.0, 1.0), length=24.0, boats=2, seed=2)   # props on top, boats moored off the face
    props.trireme_v3((-8, 48, 0), heading_deg=170, oars='rest', crew='proxies', name='moored')
    common.camera('cam', Vector((9.0, 14.5, 2.9)), Vector((-1.0, 22.5, 1.0)), lens=28)
else:
    props.fleet((0, 330, 0), count=40, spread=(420.0, 200.0), heading_deg=200, phoenician_share=0.35, oars='row',
                camera=(30.0, -20.0, 9.0), far=180.0, seed=3)        # the whole fleet in front of the camera
    common.camera('cam', Vector((30.0, -20.0, 9.0)), Vector((-5.0, 260.0, 2.0)), lens=35)
print('BUILD_SECONDS', round(time.time() - t, 1), 'objects', len(bpy.data.objects))

sc.frame_set(FRAME)
common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
sc.view_settings.look = 'AgX - High Contrast'
sc.view_settings.exposure = 0.4
common.render()
