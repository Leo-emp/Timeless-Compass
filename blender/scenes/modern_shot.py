# WS17 (Session F): shared runner for the modern-era set tests (blender/scenes/modern_*_test.py).
# Each test script calls run(build, cams, ...): build the set, optionally place modern extras, light, render one
# still per camera into <out_dir>. Command line (same for every test):
#   blender -b --python blender/scenes/modern_<set>_test.py -- <out_dir> [samples] [people 0|1] [res_scale]
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HERE, '..'), os.path.join(HERE, '..', '..')):
    if p not in sys.path:
        sys.path.insert(0, p)

import bpy
from mathutils import Vector

from lib import common


def args():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = os.path.abspath(argv[0]) if argv else os.path.abspath('modern_out')
    samples = int(argv[1]) if len(argv) > 1 else 32
    people = len(argv) > 2 and argv[2] == '1'
    scale = float(argv[3]) if len(argv) > 3 else 1.0
    return out, samples, people, scale


def dark_world(strength=0.02, color=(0.6, 0.7, 0.8)):
    w = bpy.data.worlds.new('dark'); bpy.context.scene.world = w
    bg = w.node_tree.nodes['Background']; bg.inputs['Strength'].default_value = strength; bg.inputs['Color'].default_value = (*color, 1)
    return w


def place_people(specs, marks, face_toward=None, turns=None):
    """specs = [(role, era, seed)], marks = [(x, y, z)]. Built with modern_dress (MakeHuman + overlays)."""
    from lib import modern_dress
    from tc import crowd
    people = [crowd.person(s, r, e) for r, e, s in specs]
    roots = modern_dress.modern_crowd(people, marks, frames=24, face_toward=face_toward, clip=False)
    if turns:
        import math
        for r, t in zip(roots, turns):
            if t is not None:
                r.rotation_euler.z = math.radians(t)
    return roots


def run(build, cams, out, samples, scale=1.0, frame=1, look='AgX - High Contrast', exposure=0.0, res=(1600, 900),
        people=None, engine='CYCLES'):
    """build() makes the set (+ lights). cams = [(name, loc, target, lens[, fstop])]. people() is called after the
    set if given. Renders <out>/<name>.png for each camera at `frame`."""
    common.reset_scene()
    build()
    if people:
        people()
    common.render_settings(res=(int(res[0] * scale), int(res[1] * scale)), samples=samples, engine=engine)
    sc = bpy.context.scene; sc.view_settings.look = look; sc.view_settings.exposure = exposure
    if engine == 'CYCLES':
        sc.cycles.volume_bounces = 2; sc.cycles.volume_step_rate = 2.0
    sc.frame_set(frame)
    os.makedirs(out, exist_ok=True)
    for c in cams:
        name, loc, tgt, lens = c[:4]
        fstop = c[4] if len(c) > 4 else None
        common.camera('cam_' + name, Vector(loc), Vector(tgt), lens=lens, fstop=fstop)
        common.render(os.path.join(out, name + '.png'))
    print('MODERN SHOT DONE', out, flush=True)
