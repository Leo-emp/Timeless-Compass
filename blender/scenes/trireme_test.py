# TEST STILL: Athenian triremes rowing in the Salamis strait at dusk (low camera near the water).
# Run: blender -b --python blender/scenes/trireme_test.py -- <out.png> [samples]
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, sets, props

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'trireme.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 48

common.reset_scene()
sets.salamis_dusk()
props.trireme((-10, 40, 0), heading_deg=25, name='tri_a')
props.trireme((-55, 95, 0), heading_deg=20, name='tri_b')
props.trireme((25, 120, 0), heading_deg=30, name='tri_c')
sun = bpy.data.objects['sun']; sun.data.energy = 8.0
sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(118))
bpy.context.scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25
common.camera('cam', Vector((12.0, 8.0, 2.2)), Vector((-2.0, 52.0, 3.0)), lens=35)
common.render_settings(res=(1280, 544), samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = 0.4
common.render()
