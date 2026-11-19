# WS7 TEST: rich exteriors from one call each.
#   harbour - props.dress_harbour on a stone quay over the dusk sea (ships stern-to, cargo, sheds, stoa)
#   camp    - props.dress_persian_camp on dry ground (pavilion, tents, fires, spears, baggage, camels, horses)
#   beach   - props.dress_beach_camp: the Greek fleet hauled up on Salamis, sails + masts left ashore, campfires
# Run: blender -b --python blender/scenes/ws7_exteriors.py -- <out.png> [samples] [variant] [frame]
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, sets

OUT, SAMPLES, VARIANT = W.args('ext_harbour_v1.png')
VARIANT = VARIANT or 'harbour'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FRAME = int(argv[3]) if len(argv) > 3 else 12
common.reset_scene()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 240


def ground(name, scan, tint, size=200.0, z=0.0, tilt_deg=0.0, loc=(0, 0)):
    m = props.scan_surface(name, scan, tint, tile=3.0, rough=(0.7, 0.98), normal=1.0)
    bpy.ops.mesh.primitive_plane_add(size=size, location=(loc[0], loc[1], z), rotation=(math.radians(tilt_deg), 0, 0))
    g = bpy.context.object; g.name = name; g.data.materials.append(m)
    return g


def dusk_sea():
    sets.salamis_dusk()
    sun = bpy.data.objects['sun']; sun.data.energy = 7.0
    sun.rotation_euler = (math.radians(90 - 14), 0, math.radians(118))
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3


if VARIANT == 'harbour':
    dusk_sea()
    sets.stone_wall(-22.0, 22.0, 3.0, 1.0, depth=6.0)                 # quay wall: face at y = 0, top at z = 1
    ground('ws7_quay_paving', 'old_sandstone_02', (0.6, 0.55, 0.48), size=60.0, z=1.0, loc=(0, 32))
    kit = props.dress_harbour((0, 0.0, 1.0), length=40.0, ships=2, seed=3)
    CAM = (21.0, -21.0, 7.0)
    common.camera('cam', Vector(CAM), Vector((-3.0, 7.0, 1.2)), lens=30)          # over the water, quay + town
    props.populate(kit, 'greece_480bc', camera=CAM, built=8, seed=3)              # people at work: never an empty quay
elif VARIANT == 'camp':
    common.sky_world(sun_elev_deg=10.0, sun_rot_deg=220.0, strength=0.3)
    common.sun_light('sun', 4.0, (1.0, 0.78, 0.55), 12, 220)
    ground('ws7_camp_earth', 'brown_mud_dry', (0.34, 0.29, 0.23), size=300.0)                 # trodden earth, not white
    kit = props.dress_persian_camp((0, 0, 0), seed=4)
    CAM = (3.5, -15.0, 2.2)                                                   # down the camp street, people mid-distance
    common.camera('cam', Vector(CAM), Vector((-0.5, 6.0, 1.5)), lens=30)
    props.populate(kit, 'persia_480bc', camera=CAM, built=8, seed=4)
else:
    dusk_sea()
    # beach rising out of the sea: z = 0 at y = 4, +0.05 m per metre inland (the ships at y = 16 sit on the sand)
    ground('ws7_beach_sand', 'coast_sand_rocks_02', (0.62, 0.56, 0.46), size=120.0, z=(40 - 4) * 0.05, tilt_deg=math.degrees(math.atan(0.05)), loc=(0, 40))
    kit = props.dress_beach_camp((0, 0, 0), ships=4, seed=5)
    for o in kit.children:                       # the kit stands on z = 0: lift each piece onto the sloping sand
        o.location.z += max(0.0, (o.location.y - 4) * 0.05)
    CAM = (34.0, -10.0, 9.0)
    common.camera('cam', Vector(CAM), Vector((0.0, 22.0, 1.0)), lens=30)          # the whole beach from the sea
    props.populate(kit, 'greece_480bc', camera=CAM, built=8, seed=5)

sc.frame_set(FRAME)
common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
sc.view_settings.look = 'AgX - High Contrast'
sc.view_settings.exposure = -0.2 if VARIANT == 'camp' else 0.1
common.render()
