# WS7 TEST: the Akhal-Teke scan (CC-BY, Animal Animator) at ancient-horse size, with an era-correct SADDLE CLOTH
# and a simple BRIDLE (no saddle, no stirrups in 480 BC), playing one of its own animations.
# Run: blender -b --python blender/scenes/ws7_horse.py -- <out.png> [samples] [clip] [frame]
#   clip = Trot | Run_Gallop | Chewing  (default Trot); frame = which frame of the shot to render
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, scans_glb, scatter

OUT, SAMPLES, CLIP = W.args('horse_v1.png')
CLIP = CLIP or 'Trot'
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
FRAME = int(argv[3]) if len(argv) > 3 else 12

common.reset_scene()
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, 120
# ground: dry earth (scanned) + a dusk sky
gm = scatter.scan_material('ws7_ground', 'brown_mud_dry', tint=(0.9, 0.82, 0.72), tiles=3.0)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0)); bpy.context.object.data.materials.append(gm)
common.sky_world(sun_elev_deg=9.0, sun_rot_deg=120.0, strength=0.2)
common.sun_light('sun', 3.5, (1.0, 0.78, 0.55), 14, 120)

horse = scans_glb.load_glb('horse_akhalteke', loc=(0, 0, 0), rot_z_deg=0)
scans_glb.play(horse, CLIP, frame_start=1)
props.horse_tack(horse, cloth='persian' if 'persian' in os.path.basename(OUT) else 'greek')
sc.frame_set(FRAME)

common.camera('cam', Vector((6.2, -1.6, 1.3)), Vector((0.0, 0.05, 1.0)), lens=40)
common.area_light('rim', 120.0, (0.75, 0.82, 1.0), (-3.0, 3.0, 2.8), (0, 0, 1.0), size=2.0)
W.finish(OUT, SAMPLES, exposure=-1.1)
