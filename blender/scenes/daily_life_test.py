# DAILY LIFE TEST (WS16 + WS3): trading in the agora, a country village, a fishermen's beach, c. 480 BC.
# Run: blender -b --python blender/scenes/daily_life_test.py -- <out.png> [samples] [view: market|village|beach|caravan|workshops|garden] [people] [dress]
#   people (market view): how many dressed extras to put at the stalls (each is cloth-simulated: ~2-4 min each)
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import common, market, countryside as cs, sets, wardrobe
import ws3_common as W

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'daily_life.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
VIEW = argv[2] if len(argv) > 2 else 'market'
PEOPLE = int(argv[3]) if len(argv) > 3 else 3
DRESS = len(argv) > 4 and argv[4] == 'dress'          # 'dress' = fill what the camera sees (lib/dressing.py)

common.reset_scene()


def place_person(person, loc, heading_deg):
    """Build + dress one tc/crowd.py extra at the origin (cloth simulates there), then move the whole figure."""
    if person.get('hair', {}).get('length', 0) > 0.08:                # long women's hair = WS1; keep it short here
        person['hair']['length'] = 0.06
    before = set(bpy.data.objects)
    human, rig, pos = W.make_person(person)
    wardrobe.dress(human, rig, pos, person)
    root = common.link(bpy.data.objects.new(f"person_{person['role']}_{person['seed']}", None))
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            w = o.matrix_world.copy(); o.parent = root; o.matrix_world = w
    root.location = loc; root.rotation_euler = (0, 0, math.radians(heading_deg))
    human.modifiers.new('smooth', 'SUBSURF').levels = 1
    return root


if VIEW == 'market':
    bpy.ops.mesh.primitive_plane_add(size=200); g = bpy.context.object
    g.data.materials.append(cs.soil_material('agora_ground', scan='brown_mud_dry', tint=(1.05, 1.0, 0.92), tiles=1.5))
    market.market((0, 0, 0), rows=2, per_row=3, seed=4)
    market.stoa((0, -9.0, 0), heading_deg=180, columns=12)             # colonnade facing the market
    from lib import architecture
    for i, x in enumerate((-24, -12, 12, 24)):                     # houses + shops along the far side
        architecture.house((x, 16, 0), w=8, d=8, heading_deg=180, seed=40 + i, name=f'agora_house{i}')
    from tc import crowd
    cast = [('trader', 11, (1.0, 2.4), 200), ('villager', 21, (-1.6, 2.6), 160), ('fisherman', 31, (3.8, 2.2), 230),
            ('citizen', 41, (-4.0, 2.0), 140)][:PEOPLE]
    for role, seed, (x, y), hd in cast:
        place_person(crowd.person(seed, role, 'greece_480bc'), (x, y, 0), hd)
    cam, tgt, lens = Vector((2.5, 9.5, 2.0)), Vector((0, 0.5, 1.0)), 32
    common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=0.8, lighting=0.3, rotate_deg=120)
    common.sun_light('sun', 4.0, (1.0, 0.8, 0.6), 30, 200)
elif VIEW == 'village':
    bpy.ops.mesh.primitive_plane_add(size=800); g = bpy.context.object
    g.data.materials.append(cs.soil_material('village_ground', scan='coast_sand_rocks_02', tint=(0.95, 0.9, 0.8), tiles=2.0))
    market.village((0, 0, 0), n=9, seed=3)
    cs.grain_field('village_field', size=(50.0, 30.0), loc=(0, -62, 0), state='ripe', density=18, seed=5)
    cs.olive_grove(g, (-90, -40, -40, 40), spacing=10, seed=6)
    sets.land('village_hills', (0, 520, -2), (900, 260), 220, rough=24, noise=40, seed=4)
    cam, tgt, lens = Vector((-30, -95, 16)), Vector((0, 0, 2)), 35
    common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=0.85, lighting=0.3, rotate_deg=200)
    common.sun_light('sun', 4.2, (1.0, 0.72, 0.45), 14, 240)
    sets.haze(size=(3000, 3000, 400), density=0.0002, color=(1.0, 0.8, 0.6))
elif VIEW == 'caravan':
    # a trade caravan on a Persian royal road across dry plain, a Persian trader (Median dress) leading it
    bpy.ops.mesh.primitive_plane_add(size=800); g = bpy.context.object
    g.data.materials.append(cs.soil_material('road_ground', scan='brown_mud_dry', tint=(1.1, 1.0, 0.85), tiles=2.0))
    market.caravan((0, 0, 0), heading_deg=0, n=5, seed=7)
    sets.land('road_hills', (0, 600, -2), (1200, 300), 240, rough=24, noise=40, seed=9)
    if PEOPLE:
        from tc import crowd
        place_person(crowd.person(51, 'trader', 'persia_480bc'), (0.8, 3.2, 0), 180)
    cam, tgt, lens = Vector((9, 10, 2.0)), Vector((0, -5, 1.4)), 32
    common.hdri_sky('qwantani_sunset_puresky', background=0.85, lighting=0.3, rotate_deg=140)
    common.sun_light('sun', 4.0, (1.0, 0.66, 0.4), 9, 220)
    sets.haze(size=(3000, 3000, 400), density=0.00025, color=(1.0, 0.7, 0.5))
elif VIEW == 'workshops':
    # the Kerameikos: a potter's yard and a smithy side by side, a potter and a smith at work
    bpy.ops.mesh.primitive_plane_add(size=200); g = bpy.context.object
    g.data.materials.append(cs.soil_material('yard_ground', scan='brown_mud_dry', tint=(1.0, 0.92, 0.85), tiles=1.5))
    market.potter_workshop((0, 0, 0), seed=3)
    market.smithy((7, -1, 0), heading_deg=-20, seed=4)
    if PEOPLE:
        from tc import crowd
        place_person(crowd.person(61, 'potter', 'greece_480bc'), (0.0, -0.9, 0), 0)
        if PEOPLE > 1:
            place_person(crowd.person(62, 'smith', 'greece_480bc'), (8.3, -1.6, 0), 60)
    cam, tgt, lens = Vector((3.2, -13.0, 3.0)), Vector((3.0, 0.5, 1.0)), 26
    common.hdri_sky('qwantani_dusk_2_puresky', background=0.6, lighting=0.25, rotate_deg=90)
    common.sun_light('sun', 2.5, (1.0, 0.62, 0.38), 8, 250)
elif VIEW == 'garden':
    # a Persian royal garden (paradeisos, after Pasargadae): stone channels, basins, cypress walks, palms
    cs.persian_garden((0, 0, 0), seed=2)
    sets.land('garden_hills', (0, 700, -2), (1400, 300), 300, rough=26, noise=42, seed=11)
    cam, tgt, lens = Vector((1.2, -36, 2.2)), Vector((0, 8, 1.6)), 28
    common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=0.9, lighting=0.45, rotate_deg=170)
    common.sun_light('sun', 4.5, (1.0, 0.8, 0.58), 32, 200)              # light down the garden's long axis
    sets.haze(size=(3000, 3000, 400), density=0.00018, color=(1.0, 0.8, 0.62))
else:                                                               # beach
    # the sea runs out to the horizon (-Y); the sand starts at the waterline (y = -1) and goes inland (+Y)
    sea = sets.ocean(size=400.0)
    sea.location = (0, -200, -0.15)
    sets.far_sea()
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 99, 0.0)); g = bpy.context.object
    g.scale = (300, 200, 1); bpy.ops.object.transform_apply(scale=True)
    g.data.materials.append(cs.soil_material('beach_sand', scan='coast_sand_rocks_02', tint=(1.35, 1.28, 1.12), tiles=1.5))
    market.fishing_beach((0, 3.5, 0.05), heading_deg=180, seed=2)        # bows up the beach, sterns to the sea
    sets.land('far_island', (-300, -1400, -2), (900, 300), 160, rough=20, noise=34, seed=3)   # Salamis across the strait
    cam, tgt, lens = Vector((7.5, 15.0, 2.0)), Vector((0, 0, 0.6)), 30
    common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=0.85, lighting=0.3, rotate_deg=60)
    common.sun_light('sun', 4.0, (1.0, 0.78, 0.55), 18, 300)
    sets.haze(size=(4000, 4000, 400), density=0.00012, color=(0.85, 0.9, 1.0))
common.camera('cam', cam, tgt, lens=lens, fstop=8)
bpy.context.scene.camera.data.clip_end = 6000
if DRESS:
    from lib import dressing
    setting = {'market': 'market', 'village': 'village', 'beach': 'harbour', 'caravan': 'persian_camp',
               'workshops': 'village', 'garden': 'garden'}.get(VIEW, 'village')
    keep = {'market': [(0, 0, 7.5), (0, -9, 5)], 'village': [(0, 0, 6)], 'beach': [(0, 3.5, 7)],
            'caravan': [(0, -7, 4), (0, 0, 3)], 'workshops': [(0, 0, 3.5), (7, -1, 3)], 'garden': [(0, 0, 1.6)]}.get(VIEW, [])
    ground = globals().get('g') or bpy.data.objects.get('paradeisos_ground')      # the view's own ground
    dressing.dress_view(bpy.context.scene.camera, ground, setting, amount=160, keep_clear=keep, seed=7)
common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = -0.4
common.render()
