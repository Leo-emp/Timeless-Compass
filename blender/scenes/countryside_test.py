# COUNTRYSIDE TEST (WS16): an Attic farm landscape, early summer 480 BC, late golden afternoon.
#   foreground: ripe emmer wheat field (with a stone wall along it); middle: olive grove in rows over stubble,
#   threshing floor with sheaves, beehives; back: terraced hillside, mountains (sets.land), real photographed sky.
# Run: blender -b --python blender/scenes/countryside_test.py -- <out.png> [samples] [view: wide|field|floor|terraces|olive] [frames]
#   frames > 1 = a WIND TEST CLIP: renders frames 1..N (24 fps, 640x360) as <out>_####.png to check the gusts
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, countryside as cs, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'countryside.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
VIEW = argv[2] if len(argv) > 2 else 'wide'
FRAMES = int(argv[3]) if len(argv) > 3 else 1

common.reset_scene()

# --- the land: a broad gentle valley floor; terraces and mountains behind
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.05)); floor = bpy.context.object; floor.name = 'valley'
floor.data.materials.append(cs.soil_material('valley_soil', scan='coast_sand_rocks_02', tint=(0.95, 0.9, 0.8), tiles=2.0))
wheat = cs.grain_field('wheat', size=(46.0, 26.0), loc=(0, 6, 0), crop='wheat', state='ripe', density=24, seed=1)
stubble = cs.grain_field('stubble', size=(60.0, 34.0), loc=(6, 46, 0.02), crop='barley', state='stubble', density=14, seed=2)
ploughed = cs.grain_field('ploughed', size=(40.0, 24.0), loc=(-52, 20, 0.01), heading_deg=90, state='ploughed', seed=3)
fallow = cs.grain_field('fallow', size=(30.0, 30.0), loc=(48, 12, 0.01), state='fallow', seed=4)
cs.olive_grove(stubble, (-24, 36, 30, 62), spacing=9.5, seed=5)
cs.vineyard(floor, (-52, -27, -12, 6), seed=11)                       # low vines in rows, left of the wheat
from lib import tools
tools.ox_team((-52, 24, 0.02), heading_deg=90, seed=12)                # ploughing the autumn field (Hesiod)
tools.cart((-33, 42, 0.0), heading_deg=35, load='hay', seed=13)       # by the threshing floor
cs.flock(fallow, (48, 12), n=22, kind='sheep', seed=14)               # sheep grazing the fallow field
cs.flock(floor, (70, 60), n=14, kind='goat', radius=12, seed=15, dog=False)
cs.dry_stone_wall([(-23, -7.4), (0, -7.6), (23, -7.2)], height=1.0, seed=6, ruined=0.15, name='wall_front')
cs.dry_stone_wall([(-23.5, 19.5), (-23.5, 28.5), (30, 28.5)], height=1.1, seed=7, ruined=0.05, name='wall_back')
cs.threshing_floor((-40, 48, 0.0), radius=6.0, seed=8)
cs.beehives((-30, 30, 0.0), heading_deg=10, seed=9)
cs.terraced_hill('terraces', loc=(10, 70, 0), size=(90.0, 50.0), rise=20.0, steps=9, seed=10)
# ridged limestone mountains with rock faces + scrub (countryside.mountain; the soft sets.land hills read as sand)
cs.mountain('hymettos', (60, 470, -2), (1100.0, 420.0), 300.0, seed=1, peaks=2)
cs.mountain('far_hills', (-480, 700, -2), (900.0, 400.0), 220.0, seed=2, scrub=False,
            rock_tint=(0.85, 0.88, 0.95), scrub_tint=(0.8, 0.82, 0.86))       # further = bluer (air between)

# --- light: low warm sun from the left-front, a real sky with clouds, gentle haze for depth
common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=0.9, lighting=0.45, rotate_deg=200)
# sun_light's azimuth is where the light TRAVELS: az 35 = sun behind the camera's left shoulder for cameras looking +y
# (az 215 had put the sun in FRONT of every camera here: backlit, murky shots)
common.sun_light('sun', 4.8, (1.0, 0.76, 0.5), 22, 35, angle_deg=1.0)
sets.haze(size=(3000, 3000, 400), density=0.00022, color=(1.0, 0.8, 0.6))

views = {   # camera, target, lens
    'wide': (Vector((-6, -24, 2.4)), Vector((4, 40, 6)), 30),
    'field': (Vector((3, -10.5, 1.15)), Vector((0, 12, 1.0)), 50),
    'floor': (Vector((-30, 34, 3.5)), Vector((-40, 48, 0.4)), 40),
    'terraces': (Vector((0, 20, 4.0)), Vector((10, 80, 10)), 40),
    'olive': (Vector((2.5, 26.0, 1.7)), Vector((4.0, 38.0, 3.2)), 32),    # under the code-built olive trees
}
cam, tgt, lens = views[VIEW]
common.camera('cam', cam, tgt, lens=lens, fstop=8)
bpy.context.scene.camera.data.clip_end = 6000
common.render_settings(res=(960, 540) if FRAMES == 1 else (640, 360), samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = 0.0
if FRAMES == 1:
    common.render()
else:                                                   # wind clip: the plants move with the scene clock
    sc = bpy.context.scene
    sc.render.fps = 24; sc.frame_start, sc.frame_end = 1, FRAMES
    sc.render.filepath = OUT.rsplit('.', 1)[0] + '_'
    bpy.ops.render.render(animation=True)
