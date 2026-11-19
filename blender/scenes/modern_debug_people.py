# WS17 debug (Session F): which step breaks modern MakeHuman suits? Same agent built 4 ways, Workbench render.
# Run: blender -b --python blender/scenes/modern_debug_people.py -- <out.png> [role] [era] [seed]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import cast, common, life, pose, modern_dress
from tc import crowd
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0]); role = argv[1] if len(argv) > 1 else 'agent'; era = argv[2] if len(argv) > 2 else 'usa_1960'
seed = int(argv[3]) if len(argv) > 3 else 5
common.reset_scene()
p = crowd.person(seed, role, era)
for k, step in enumerate(('raw', 'groom', 'pose', 'life')):
    before = set(bpy.data.objects)
    human, rig = cast.build_human(p)
    if step != 'raw':
        modern_dress.rebind_mpfb_clothes(human, rig)
    if step in ('groom', 'pose', 'life'):
        cast.groom(human, rig, p, seed=p['seed'])
    if step in ('pose', 'life'):
        pose.apply_pose(rig, 'stand_relaxed')
    if step == 'life':
        life.bring_to_life(rig, 1, 24, seed=1, standing=True)
    r = bpy.data.objects.new('r' + step, None); common.link(r)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not r:
            o.parent = r
    r.location = (k * 1.3 - 2.0, 0, 0)
    print('STEP', step, 'rig', rig.name, 'children', len(r.children), flush=True)
bpy.context.scene.frame_set(1)
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x, sc.render.resolution_y = (1400, 700)
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
common.camera('c', Vector((0, -7.5, 1.0)), Vector((0, 0, 0.9)), lens=35)
common.render(OUT)
