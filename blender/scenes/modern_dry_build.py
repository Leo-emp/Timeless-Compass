# WS17 (Session F): build every modern-era set / prop / fx once WITHOUT rendering - catches code errors in seconds
# before cloud renders are spent. Run: blender -b --python blender/scenes/modern_dry_build.py
import os, sys, traceback
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from lib import common, fx, modern, modern_props as P
JOBS = [('office', modern.government_office), ('bunker', modern.bunker_command), ('hangar', modern.hangar),
        ('desert', modern.desert_test_site), ('interrogation', modern.interrogation_room), ('ward', modern.psych_ward),
        ('mission', modern.mission_control), ('huts', modern.los_alamos_huts), ('lab', modern.lab_1950s),
        ('props', lambda: [P.typewriter(), P.rotary_phone(), P.reel_to_reel(), P.folder_stack(), P.geiger_counter(), P.film_projector(),
                           P.desk(), P.office_chair(), P.filing_cabinet(open_drawer=1), P.desk_lamp((0, 0, 0)), P.wall_clock((0, 0, 2)),
                           P.venetian_blinds((0, 0, 1))]),
        ('vehicles', lambda: [P.jeep(), P.army_truck(), P.sedan(), P.sedan(style='1950s'), P.bomber(), P.jet(),
                              P.rocket('v2'), P.rocket('redstone'), P.rocket('r7'), P.launch_tower()]),
        ('atomic', lambda: fx.atomic_test()), ('rocket', lambda: fx.rocket_launch())]
bad = 0
for name, fn in JOBS:
    common.reset_scene()
    try:
        fn(); bpy.context.view_layer.update()
        print(f'DRY OK {name}: {len(bpy.data.objects)} objects', flush=True)
    except Exception:
        bad += 1; print(f'DRY FAIL {name}', flush=True); traceback.print_exc()
print('DRY DONE', bad, 'failures', flush=True)
