# INSERT + FRAMING TEST (Session D): documentary detail inserts and depth-layer foreground framers.
# Run: blender -b --python blender/scenes/inserts_test.py -- <out.png> [view] [samples]
#   view: tablet | ostrakon | coins | scroll | games | framers_battle | framers_country
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, inserts, market, props, framing, countryside as cs, sets, camera_moves as cm

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'insert.png'
VIEW = argv[1] if len(argv) > 1 else 'tablet'
SAMPLES = int(argv[2]) if len(argv) > 2 else 32

common.reset_scene()
if VIEW == 'tablet':                                   # Demaratus' hidden warning (Herodotus 7.239)
    inserts.wax_tablet((0, 0, 0), rot_z=0.15)
    props.oil_lamp((0.2, 0.12, 0.0), lit=True)
    inserts.insert_set((-0.02, 0, 0.01), surface='wood', mood='fire', azimuth_deg=-30)
elif VIEW == 'ostrakon':                               # the vote to exile Themistocles
    for i in range(4):
        inserts.ostrakon((0.12 * (i - 1.5), 0.05 * math.sin(i * 2), 0), rot_z=0.4 * i - 0.6, seed=i)
    inserts.insert_set((0, 0, 0.005), surface='stone', mood='warm', azimuth_deg=-15, height_deg=48)
elif VIEW == 'coins':                                  # the Laurion silver that paid for the fleet
    market.owl_coins(Vector((0, 0, 0)), n=24, seed=3)
    market.balance(Vector((0.18, 0.12, 0)))
    inserts.insert_set((0.02, 0.02, 0.01), surface='wood', mood='warm', azimuth_deg=-40, height_deg=40)
elif VIEW == 'scroll':
    inserts.scroll((0, 0, 0), rot_z=0.3)
    inserts.insert_set((0, 0, 0.02), surface='cloth', mood='cold', azimuth_deg=-20)
elif VIEW == 'games':
    inserts.astragaloi((0, 0, 0), n=6, seed=2); inserts.aryballos((0.12, 0.06, 0))
    inserts.insert_set((0.03, 0.02, 0.01), surface='stone', mood='warm', azimuth_deg=-35)
else:                                                  # framers in front of a simple set
    bpy.ops.mesh.primitive_plane_add(size=400); g = bpy.context.object
    g.data.materials.append(cs.soil_material('fr_ground', scan='coast_sand_rocks_02', tint=(1.0, 0.95, 0.85), tiles=2.0))
    for i, x in enumerate((-2, 0.4, 2.6)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=1.7, location=(x, 6 + i, 0.85))
        bpy.context.object.data.materials.append(common.principled(f'fig{i}', (0.3, 0.06, 0.04), rough=0.7))
    sets.land('fr_hills', (0, 500, -2), (900, 250), 200, rough=20, noise=36, seed=2)
    common.hdri_sky('qwantani_sunset_puresky', background=0.8, lighting=0.3, rotate_deg=140)
    common.sun_light('sun', 3.5, (1.0, 0.65, 0.38), 9, 220)
    sets.haze(size=(3000, 3000, 400), density=0.00035, color=(1.0, 0.72, 0.5))
    cam = common.camera('cam', Vector((0.6, -1.0, 1.5)), Vector((0.4, 7, 1.3)), lens=50, fstop=2.0)
    cm.apply_lens(cam, 'medium', focus=Vector((0.4, 7, 1.3)), motion_blur=False)
    framing.auto_frame(cam, 'battle' if VIEW == 'framers_battle' else 'countryside', seed=4, count=2)
    common.render_settings(res=(1280, 544), samples=SAMPLES)
    bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.render.filepath = OUT
common.render()
