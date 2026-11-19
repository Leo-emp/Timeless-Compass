# WS7 TEST: story props for the 5 Salamis Shorts.
#   ram       - the Athlit ram on its museum plinth (corroded) + a freshly cast copy beside it (how rams looked new)
#   oracle    - Delphi: tripod-cauldron (Pythia's seat), omphalos with its woollen net, suppliant olive branches
#   wall      - the burning timber barricade on the Acropolis at night
#   scribes   - the king's secretaries' kit (leather scroll, ink, reed pens), a Greek wax tablet, the royal parasol
#   debris    - wreckage after a ramming on the dusk strait, with a v3 trireme backing off
# Run: blender -b --python blender/scenes/ws7_story.py -- <out.png> [samples] [variant] [frame]
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, sets

OUT, SAMPLES, VARIANT = W.args('story_ram_v1.png')
VARIANT = VARIANT or 'ram'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FRAME = int(argv[3]) if len(argv) > 3 else 12
common.reset_scene()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 240

if VARIANT == 'ram':
    W.room(w=8.0, d=6.0, floor='marble_01', wall='plastered_wall_02', wall_tint=(0.25, 0.25, 0.27), floor_tint=(0.3, 0.3, 0.3))
    W.dark_world(0.01)
    props.ram_athlit((0.0, 1.0, 0), heading_deg=-20, plinth=True, corroded=True, name='athlit')
    props.ram_athlit((2.4, 1.8, 0), heading_deg=-35, plinth=True, corroded=False, name='athlit_new')
    common.area_light('key', 260.0, (1.0, 0.92, 0.82), (2.2, -1.2, 2.6), (0.2, 1.0, 0.8), size=0.8)       # museum spot
    common.area_light('rim', 120.0, (0.75, 0.82, 1.0), (-2.0, 2.8, 2.0), (0.0, 1.0, 0.8), size=1.0)
    common.camera('cam', Vector((1.6, -2.2, 1.35)), Vector((0.6, 1.2, 0.75)), lens=35, fstop=4.0, focus=(0.0, 1.0, 0.8))
    W.finish(OUT, SAMPLES, exposure=-0.3)
elif VARIANT == 'oracle':
    W.room(w=8.0, d=7.0, floor='old_sandstone_02', wall='damaged_plaster', wall_tint=(0.5, 0.47, 0.42), floor_tint=(0.5, 0.48, 0.45))
    W.dark_world(0.01)
    props.tripod_cauldron((0.0, 1.6, 0), seat=True, name='pythia_tripod')
    props.omphalos((-1.3, 2.0, 0), height=0.9)
    for k in range(3):
        b = props.suppliant_branch((0.9 + 0.15 * k, 0.9 - 0.1 * k, 0.0), heading_deg=40 * k, seed=k, name=f'branch{k}')
        b.rotation_euler.x = math.radians(70); b.location.z = 0.05                    # laid on the floor as offerings
    props.brazier((1.6, 2.2, 0), kind='bronze', lit=True, power=90.0, seed=3)
    common.area_light('shaft', 900.0, (1.0, 0.9, 0.75), (-2.5, -0.5, 3.3), (0.0, 1.6, 0.6), size=0.5)   # light from the door
    common.camera('cam', Vector((0.9, -2.2, 1.4)), Vector((-0.2, 1.6, 0.8)), lens=30)
    W.finish(OUT, SAMPLES, exposure=-0.2)
elif VARIANT == 'wall':
    gm = props.scan_surface('ws7_rock', 'old_sandstone_02', (0.32, 0.28, 0.24), tile=2.0)
    bpy.ops.mesh.primitive_plane_add(size=60); bpy.context.object.data.materials.append(gm)
    W.dark_world(0.02, color=(0.12, 0.15, 0.25))
    props.timber_barricade((0, 4, 0), length=12.0, burning=True, seed=2)
    common.area_light('moon', 120.0, (0.5, 0.6, 1.0), (-8.0, -6.0, 8.0), (0, 4, 1), size=4.0)
    sc.frame_set(FRAME)
    common.camera('cam', Vector((3.5, -4.5, 1.6)), Vector((-0.5, 4.0, 1.2)), lens=28)
    W.finish(OUT, SAMPLES, exposure=-0.6)
elif VARIANT == 'court':                   # Xerxes' throne on Aigaleos: the king's setting without the king
    W.room(w=10.0, d=8.0, floor='old_sandstone_02', wall='plastered_wall_02', floor_tint=(0.42, 0.38, 0.33), wall_tint=(0.22, 0.2, 0.19))
    W.dark_world(0.02)
    props.carpet((0.0, 1.7, 0.0), size=(3.6, 2.6))
    props.pavilion((0.0, 2.0, 0.0), w=4.4, d=3.4, h=3.0)                      # the royal field canopy
    props.throne((0.0, 2.3, 0.012), heading_deg=0)          # footstool side (-Y) faces the camera
    props.royal_parasol((0.6, 2.75, 0.0), heading_deg=0, tilt_deg=-8)
    for x in (-1.15, 1.15):
        props.incense_burner((x, 1.0, 0.012), name=f'incense_{"l" if x < 0 else "r"}')
    props.trapeza((-1.75, 2.1, 0.012), heading_deg=90, name='side_table')
    props.phiale((-1.8, 1.95, 0.512), name='phiale_gold')
    props.rhyton((-1.7, 2.3, 0.512), heading_deg=30)
    props.scribe_kit((1.5, 1.0, 0.012), heading_deg=-60, persian=True, name='secretary_kit')   # scribes sat on the ground
    # low warm sun from the open side of the pavilion + a cool sky fill + a gold rim
    W.window_light((0.0, 2.2, 1.0), energy=650.0, loc=(4.0, -1.0, 1.6), size=1.5, color=(1.0, 0.78, 0.52))
    common.area_light('sky', 60.0, (0.55, 0.65, 1.0), (-3.5, -2.5, 3.5), (0, 2.0, 0.8), size=3.0)
    common.area_light('rim', 140.0, (1.0, 0.8, 0.55), (-1.5, 4.5, 2.2), (0, 2.2, 1.0), size=1.0)
    sc.frame_set(FRAME)
    common.camera('cam', Vector((0.9, -1.9, 1.25)), Vector((-0.1, 2.0, 1.0)), lens=28, fstop=4.0, focus=(0.0, 2.2, 1.0))
    W.finish(OUT, SAMPLES, exposure=-0.5)
elif VARIANT == 'aigaleos':               # the REAL setting (Herodotus 8.90, Plutarch): outdoors above the strait
    sets.xerxes_throne_aigaleos(density=0.8)
    z0 = 0.18 * 34 + 0.5 + 0.4                   # top of the throne platform (see sets.xerxes_throne_aigaleos)
    for x in (-2.2, 2.2):                        # incense smoking either side of the king (Persepolis Treasury relief)
        props.incense_burner((x, -38.6, z0), name=f'incense_{"l" if x < 0 else "r"}')
    props.royal_parasol((0.7, -41.2, z0), heading_deg=180, tilt_deg=-8)
    props.trapeza((-3.2, -40.0, z0), heading_deg=90, name='side_table')
    props.phiale((-3.25, -40.15, z0 + 0.5), name='phiale_gold')
    props.rhyton((-3.15, -39.8, z0 + 0.5), heading_deg=200)
    for i, (x, y) in enumerate(((2.8, -38.0), (3.6, -39.2))):   # the secretaries sit on the platform edge writing
        props.scribe_kit((x, y, z0), heading_deg=150 + i * 20, persian=True, name=f'secretary_kit{i}')
    for i, (x, y, role) in enumerate(((2.9, -37.6, 'scribe'), (3.7, -38.8, 'scribe'), (-1.6, -41.5, 'guard'),
                                      (1.6, -41.5, 'guard'), (-4.5, -37.2, 'courtier'))):
        m = bpy.data.objects.new(f'court_{role}{i}', None); bpy.context.scene.collection.objects.link(m)
        m.location = (x, y, z0); m['role'] = role
    sc.frame_set(FRAME)
    common.camera('cam', Vector((4.5, -27.0, z0 + 1.0)), Vector((-0.5, -40.0, z0 + 1.6)), lens=32)
    common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
    sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = -1.6   # the set's sun is strong
    common.render()
elif VARIANT == 'scribes':
    W.room(w=8.0, d=6.0, floor='old_sandstone_02', wall='plastered_wall_02', floor_tint=(0.5, 0.48, 0.45), wall_tint=(0.55, 0.52, 0.48))
    W.dark_world(0.02)
    props.trapeza((0.0, 1.2, 0), name='writing_table')
    props.scribe_kit((-0.12, 1.2, 0.5), heading_deg=0, persian=True, name='persian_kit')
    props.scribe_kit((0.25, 1.05, 0.5), heading_deg=15, persian=False, name='wax_tablet')
    props.royal_parasol((-1.4, 2.0, 0.0), heading_deg=0)
    W.window_light((0.0, 1.2, 0.5), energy=260.0, loc=(2.2, -1.2, 2.0), size=1.2, color=(1.0, 0.9, 0.78))
    common.camera('cam', Vector((0.35, 0.35, 1.05)), Vector((0.0, 1.2, 0.5)), lens=40, fstop=2.8, focus=(0.0, 1.15, 0.52))
    W.finish(OUT, SAMPLES, exposure=-0.4)
else:
    sets.salamis_dusk()
    sun = bpy.data.objects['sun']; sun.data.energy = 8.0
    sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(118))
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.25
    props.wreck_debris((2, 18, 0), radius=9.0, count=60, seed=4)
    props.trireme_v3((-20, 40, 0), heading_deg=-20, oars='rest', crew='proxies', name='victor')
    props.trireme_v3((-12, 24, 0), heading_deg=150, oars=None, crew='proxies', phoenician=True, bob=False, name='sinking')
    bpy.data.objects['sinking'].rotation_euler = (math.radians(9), math.radians(-4), math.radians(140))   # listing
    bpy.data.objects['sinking'].location.z = -0.9
    sc.frame_set(FRAME)
    common.camera('cam', Vector((9.0, 4.0, 3.2)), Vector((-2.0, 24.0, 0.4)), lens=30)
    common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
    sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = 0.4
    common.render()
