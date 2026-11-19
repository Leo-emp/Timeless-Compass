# WS17 debug (Session F): every MakeHuman modern outfit on one posed body (Workbench), to choose bases for roles.
# Run: blender -b --python blender/scenes/modern_debug_clothes.py -- <out.png> [female]
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import cast, common, pose, modern_dress
from tc import crowd
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = os.path.abspath(argv[0]); FEMALE = len(argv) > 1 and argv[1] == 'female'
SUITS = (['female_casualsuit01', 'female_casualsuit02', 'female_elegantsuit01', 'female_sportsuit01'] if FEMALE else
         ['male_casualsuit01', 'male_casualsuit02', 'male_casualsuit03', 'male_casualsuit04', 'male_casualsuit05',
          'male_casualsuit06', 'male_elegantsuit01', 'male_worksuit01'])
common.reset_scene()
for k, suit in enumerate(SUITS):
    p = crowd.person(1, 'secretary' if FEMALE else 'agent', 'usa_1960'); p['mpfb_clothes'] = [[suit, None], ['shoes02', None]]
    before = set(bpy.data.objects)
    human, rig = cast.build_human(p); modern_dress.rebind_mpfb_clothes(human, rig); pose.apply_pose(rig, 'stand_relaxed')
    r = bpy.data.objects.new('r' + suit, None); common.link(r)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not r:
            o.parent = r
    r.location = (k * 0.9 - (len(SUITS) - 1) * 0.45, 0, 0)
    t = bpy.data.curves.new('t' + suit, 'FONT'); t.body = suit.replace('_', ' '); t.size = 0.07; t.align_x = 'CENTER'
    to = bpy.data.objects.new('t' + suit, t); common.link(to); to.location = (r.location.x, -0.4, 0.05); to.rotation_euler.x = 1.2
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'; sc.render.resolution_x, sc.render.resolution_y = (1800, 800)
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
common.camera('c', Vector((0, -8.0, 1.0)), Vector((0, 0, 0.85)), lens=40)
common.render(OUT)
