# WS18 HORSE-DRAWN TEST (blender/lib/harness.py): vehicles pulled by teams that walk / trot with the right clip
# speed, wheels ROLLING with the distance travelled:
#   egypt  : New Kingdom chariot, 2 horses, galloping (Kadesh 1274 BC)
#   persia : Achaemenid royal chariot, 4 horses abreast, trotting
#   wagon  : 4-wheeled wagon with a canvas tilt, 2 mules walking
#   limber : Napoleonic limber + cannon.build('field') hooked on behind, 6 horses in 3 pairs, trotting
# One part per run (memory: each horse is its own rig). Stills at 3 moments + a side view.
# Run: blender -b --python blender/scenes/animals_harness_test.py -- <out_dir> <part> [samples]
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import animals, cavalry, common, harness, scatter

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'harness_test'
PART = argv[1] if len(argv) > 1 else 'egypt'
SAMPLES = int(argv[2]) if len(argv) > 2 else 24
FRAMES = (1, 96)
common.reset_scene()
sc = bpy.context.scene; sc.frame_start, sc.frame_end = FRAMES
desert = PART in ('egypt', 'persia')
gm = scatter.scan_material('h_ground', 'brown_mud_dry', tint=(0.95, 0.82, 0.6) if desert else (0.75, 0.72, 0.6), tiles=4.0)
bpy.ops.mesh.primitive_plane_add(size=600); bpy.context.object.data.materials.append(gm)
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.65)
common.sun_light('sun', 4.0, (1.0, 0.88, 0.7), 30, 230)

team = bpy.data.objects.new('team', None); sc.collection.objects.link(team); team['kind'] = 'team'


def hitch_horses(vehicle, n, gait, speed, cloth='greek', kinds='horse', pairs_back=0.0):
    """Put n animals under the vehicle's yoke (abreast) or in pairs ahead of it (n=6: 3 pairs), parented to the
    team empty; each plays `gait` at the rate that matches `speed`."""
    hx, hy, hz = vehicle['hitch']
    made = []
    if n in (2, 4):
        span = 1.0
        xs = [(i - (n - 1) / 2) * span for i in range(n)]
        rows = [(x, hy + 0.5) for x in xs]
    else:                                            # 6: three pairs one in front of the other
        rows = [(sx * 0.55, hy + 0.5 - k * 3.0) for k in range(n // 2) for sx in (-1, 1)]
    for i, (x, y) in enumerate(rows):
        if kinds == 'horse':
            h = cavalry.horse((0, 0, 0), 0.0, cloth=cloth, name=f'team_{PART}_{i}')
        else:
            h = animals.load(kinds, (0, 0, 0), 0.0, name=f'team_{PART}_{i}')
        h.parent = team; h.location = (x, y, 0)
        rate = speed / max(animals.clip_speed(h, gait), 1e-3)
        animals.play(h, gait, start=FRAMES[0] - 10, end=FRAMES[1], phase_s=i * 0.13, speed=max(0.55, min(1.7, rate)))
        made.append(h)
    return made


if PART == 'egypt':
    v = harness.chariot_egypt((0, 0, 0), 0.0, royal=True)
    SPEED, GAIT = 9.0, 'gallop'
    hitch_horses(v, 2, GAIT, SPEED, cloth=None)
elif PART == 'persia':
    v = harness.chariot_persia((0, 0, 0), 0.0, royal=True)
    SPEED, GAIT = 3.6, 'trot'
    hitch_horses(v, 4, GAIT, SPEED, cloth='persian')
elif PART == 'wagon':
    v = harness.wagon((0, 0, 0), 0.0, load='sacks', cover=True)
    SPEED, GAIT = 1.3, 'walk'
    hitch_horses(v, 2, GAIT, SPEED, kinds='mule')
else:
    from lib import cannon
    v = harness.limber((0, 0, 0), 0.0)
    gun = cannon.build('field', (0, 0, 0), 0.0, elevation_deg=0.0)
    harness.limber_gun(v, gun)
    SPEED, GAIT = 3.6, 'trot'
    hitch_horses(v, 6, GAIT, SPEED, cloth=None)
v.parent = team
dist = SPEED * (FRAMES[1] - FRAMES[0]) / 24
animals.walk_path(team, [(0, dist * 0.5), (0, -dist * 0.5)], SPEED, start=FRAMES[0], play_clip=False)
harness.roll(v, FRAMES, path_len=dist)

common.render_settings(res=(1280, 720), samples=SAMPLES)
os.makedirs(OUT, exist_ok=True)
# tracking 3/4 front camera that travels with the team (parented) + a fixed side view
cam = common.camera('cam_track', Vector((5.5, -7.5, 1.6)), Vector((0, -1.0, 0.9)), lens=35)
bpy.context.view_layer.update(); sc.frame_set(1)
cam.parent = team; cam.matrix_parent_inverse = team.matrix_world.inverted()
sc.camera = cam
for f in (1, 40, 80):
    sc.frame_set(f)
    common.render(os.path.join(OUT, f'{PART}_track_f{f:03d}.png'))
side = common.camera('cam_side', Vector((9.0, 0, 1.3)), Vector((0, 0, 1.0)), lens=35)
sc.camera = side
sc.frame_set(int(FRAMES[0] + (FRAMES[1] - FRAMES[0]) * 0.5))
common.render(os.path.join(OUT, f'{PART}_side.png'))
print('HARNESS DONE', PART)
