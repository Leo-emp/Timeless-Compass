# TEST STILL: the Salamis strait at dusk, establishing shot from the harbour wall.
# Run: blender -b --python blender/scenes/salamis_set_test.py -- <out.png> [samples]
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'salamis_set.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 64

common.reset_scene()
sets.salamis_dusk()
common.camera('cam', Vector((-3.0, -10.5, 2.3)), Vector((2.0, 20.0, 0.2)), lens=28)
common.render_settings(res=(1280, 544), samples=SAMPLES, path=OUT)      # 2.35:1 cinema frame
bpy.context.scene.view_settings.exposure = 0.0
common.render()
