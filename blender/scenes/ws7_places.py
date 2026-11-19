# WS7 TEST: the three ship PLACES of the Salamis shot lists, framed from their own marks.
#   hold     - place_trireme_rowing_hold: down the gangway, real rowers rowing in unison, light shafts (s03 rams Short)
#   deck     - place_trireme_deck: low on the deck looking aft at the commander's mark, marines around (s04)
#   flagship - place_persian_flagship: night, officers at the stern under lanterns, fleet lights around (s08)
# Run: blender -b --python blender/scenes/ws7_places.py -- <out.png> [samples] [variant] [frame]
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))      # tc package
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, sets
from lib import crowd as C
from tc import crowd as tcc

OUT, SAMPLES, VARIANT = W.args('place_hold_v1.png')
VARIANT = VARIANT or 'hold'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FRAME = int(argv[3]) if len(argv) > 3 else 10
common.reset_scene()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 240


def person(role, era, mark, face_target, seed):
    """One real extra on a mark, turned to face a point (0 deg = facing -Y)."""
    p = tcc.cast(1, role, era, seed=seed)[0]
    dx, dy = face_target[0] - mark[0], face_target[1] - mark[1]
    return C.build_person(p, tuple(mark), math.degrees(math.atan2(dx, -dy)), frames=48)


if VARIANT == 'hold':
    sets.salamis_dusk()
    sun = bpy.data.objects['sun']; sun.data.energy = 6.0
    m = props.place_trireme_rowing_hold((0, 30, 0), 0, rowers=24, built=8, seed=2)
    common.camera('cam', m['cam_gangway'], m['cam_target'], lens=38, fstop=2.8, focus=m['seats'][0])
    exposure = 1.0
elif VARIANT == 'deck':
    sets.salamis_dusk()
    sun = bpy.data.objects['sun']; sun.data.energy = 7.0
    m = props.place_trireme_deck((0, 30, 0), 0, seed=3)
    props.populate(m['root'], 'greece_480bc', camera=m['cam_low_deck'], built=6, seed=3)
    person('commander', 'greece_480bc', m['commander'], (m['commander'].x + 6, m['commander'].y, 0), seed=31)
    common.camera('cam', m['cam_low_deck'], m['cam_low_target'], lens=49, fstop=2.8, focus=m['commander'] + Vector((0, 0, 1.6)))
    exposure = 0.3
else:
    W.dark_world(0.006, color=(0.1, 0.13, 0.25))
    common.area_light('moon', 5000.0, (0.82, 0.86, 0.95), (-60.0, -40.0, 80.0), (0, 30, 0), size=40.0)   # soft, nearly neutral moonlight
    sets.ocean(size=600.0) if hasattr(sets, 'ocean') else None
    m = props.place_persian_flagship((0, 30, 0), 0, seed=4)
    for i, mk in enumerate(m['officers']):
        person('commander' if i == 0 else 'courtier', 'persia_480bc', mk, m['cam_orbit_centre'], seed=40 + i)
    c = m['cam_orbit_centre']; r = m['cam_orbit_radius']
    # a little above eye level looking slightly DOWN: the officers + the dark sea dotted with the fleet's lanterns behind
    common.camera('cam', c + Vector((r * 0.85, -r * 0.6, 0.35)), c + Vector((-6.0, 4.0, -1.4)), lens=34, fstop=2.8, focus=c)
    exposure = 1.8

sc.frame_set(FRAME)
common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
sc.view_settings.look = 'AgX - High Contrast'
sc.view_settings.exposure = exposure
common.render()
