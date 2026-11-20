# WS19 MAP TEST: one parchment-map shot from a painted pack (python -m tc map paint ...).
# Run: blender -b --python blender/scenes/map_test.py -- <pack_dir> <out> [frames e.g. "150" or "1-250"]
#      [engine EEVEE|CYCLES] [samples] [seconds] [tilt] [dist] [target_u,target_v]
# Stills: give one frame -> <out>.png. Animation: a range -> <out>_####.png frames (edit with ffmpeg).
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from lib import common, maps

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PACK = argv[0]
OUT = os.path.abspath(argv[1] if len(argv) > 1 else 'map.png')
FRAMES = argv[2] if len(argv) > 2 else '150'
ENGINE = (argv[3] if len(argv) > 3 else 'EEVEE').upper()
SAMPLES = int(argv[4]) if len(argv) > 4 else 64
SECONDS = float(argv[5]) if len(argv) > 5 else 12.0
TILT = float(argv[6]) if len(argv) > 6 else 46.0
DIST = float(argv[7]) if len(argv) > 7 else 7.0
TARGET = [float(x) for x in argv[8].split(',')] if len(argv) > 8 else None

common.reset_scene()
maps.build(PACK, seconds=SECONDS, target_uv=TARGET, tilt_deg=TILT, dist=DIST)
engine = 'CYCLES' if ENGINE == 'CYCLES' else 'BLENDER_EEVEE'
if engine == 'BLENDER_EEVEE' and 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]:
    engine = 'BLENDER_EEVEE_NEXT'
common.render_settings(res=(1920, 1080), samples=SAMPLES, engine=engine, path=OUT)
sc = bpy.context.scene
sc.render.resolution_percentage = int(os.environ.get('MAP_PCT', '100'))   # 67 = 1280x720 quick review clips
maps.grade(sc)
if engine != 'CYCLES':
    try:
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
    except AttributeError:
        pass
if '-' in FRAMES:
    a, b = (int(x) for x in FRAMES.split('-'))
    sc.frame_start, sc.frame_end = a, b
    sc.render.filepath = OUT + '_'
    bpy.ops.render.render(animation=True)
else:
    sc.frame_set(int(FRAMES))
    common.render(OUT if OUT.endswith('.png') else OUT + '.png')
