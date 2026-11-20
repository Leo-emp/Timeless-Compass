# DRAWN-LOOK TEST SHOT: two hoplites, helmets pushed up, half-body against a cloudy sky with the army's spears
# behind - framed like the owner's Heroes of Bronze reference frame - rendered with lib/drawn.py.
# Run: blender -b --python blender/scenes/drawn_test.py -- <out_dir> [res_scale%] [samples]
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from lib import build, common, drawn  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'spike/style2d'
SCALE = int(argv[1]) if len(argv) > 1 else 100
SAMPLES = int(argv[2]) if len(argv) > 2 else 32
os.makedirs(OUT, exist_ok=True)

common.reset_scene()
CAST = [('leonidas', (-0.48, 0.0, 0.0), -12.0), ('eurybiades', (0.62, 0.35, 0.0), 14.0)]
rigs, lasts = [], []
for name, mark, turn in CAST:
    spec = build.manifest('cast', name)
    spec['helmet'] = dict(spec.get('helmet') or {'crest': 'red'}, worn='up')
    rig, human, root, first, last = build.character(name, spec['wardrobe'], {'pose': 'stand_relaxed'},
                                                    mark=mark, turn_deg=turn, frames=24, spec=spec)
    rigs.append(rig); lasts.append((first, last))
sc = bpy.context.scene
first = max(f for f, _ in lasts); last = max(l for _, l in lasts)
sc.frame_start, sc.frame_end = 1, last
if any(m.type == 'CLOTH' for o in bpy.data.objects for m in o.modifiers):
    bpy.ops.ptcache.bake_all(bake=True)
sc.frame_set(first + 6)

# ---- GRIP CHECK (owner rule): every spear must pass through the hand that holds it
dg = bpy.context.evaluated_depsgraph_get()
for rig in rigs:
    pb = rig.pose.bones.get('wrist.R') or rig.pose.bones.get('lowerarm02.R')
    hand = rig.matrix_world @ pb.tail
    shafts = [o for o in bpy.data.objects if o.parent is rig and o.parent_bone == pb.name and o.type == 'MESH'
              and o.dimensions.z > 1.5]
    for s in shafts:
        a = s.matrix_world @ Vector((0, 0, -1.2)); b = s.matrix_world @ Vector((0, 0, 1.2))
        ab = b - a; t = max(0.0, min(1.0, (hand - a).dot(ab) / ab.length_squared))
        d = (a + ab * t - hand).length
        print(f'GRIP CHECK {rig.name}: spear axis {d * 100:.1f} cm from the right hand -> {"OK" if d < 0.05 else "FAIL"}')

# ---- ground + the army behind: rows of spears, crests and shield rims (cheap shapes, far and painted over)
bpy.ops.mesh.primitive_plane_add(size=400); g = bpy.context.object
g.data.materials.append(common.principled('drawn_ground', (0.52, 0.44, 0.24), rough=1.0))
wood = common.principled('army_wood', (0.30, 0.20, 0.11), rough=0.8)
bronze = common.principled('army_bronze', (0.62, 0.40, 0.18), metal=1.0, rough=0.5)
crest_cols = [common.principled(f'army_crest{i}', c, rough=0.9) for i, c in
              enumerate([(0.45, 0.06, 0.04), (0.08, 0.06, 0.05), (0.75, 0.72, 0.66)])]
shield_cols = [common.principled(f'army_shield{i}', c, rough=0.7) for i, c in
               enumerate([(0.40, 0.08, 0.05), (0.55, 0.36, 0.16), (0.12, 0.10, 0.09)])]
rnd = random.Random(480)
for row in range(7):
    y = 5.0 + row * 2.2
    for k in range(int(10 + row * 3)):
        x = -6 - row * 1.5 + k * (12 + row * 3) / (10 + row * 3) + rnd.uniform(-0.25, 0.25)
        h = rnd.uniform(1.62, 1.82)
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.016, depth=2.5, location=(x + 0.25, y, 1.25 + rnd.uniform(-0.1, 0.25)),
                                            rotation=(rnd.uniform(-0.05, 0.05), rnd.uniform(-0.06, 0.06), 0))
        bpy.context.object.data.materials.append(wood)
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.035, depth=0.28, location=bpy.context.object.location + Vector((0, 0, 1.38)))
        bpy.context.object.data.materials.append(bronze)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.13, location=(x, y, h))
        bpy.context.object.scale = (0.9, 1.0, 1.1); bpy.context.object.data.materials.append(bronze)
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, h + 0.17))
        bpy.context.object.scale = (0.03, 0.30, 0.14); bpy.context.object.data.materials.append(rnd.choice(crest_cols))
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.45, depth=0.06, location=(x - 0.12, y - 0.25, 1.05),
                                            rotation=(math.pi / 2, 0, rnd.uniform(-0.4, 0.4)))
        bpy.context.object.data.materials.append(rnd.choice(shield_cols))
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.2, depth=1.1, location=(x, y + 0.05, h - 0.55))
        bpy.context.object.data.materials.append(rnd.choice(shield_cols))

# ---- light: warm sun from camera-left, high; the cloud photo is the painted sky (gentle on the scene)
common.hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=1.0, lighting=0.12, rotate_deg=60)
common.sun_light('sun', 1.0, (1.0, 0.95, 0.86), 38, -42)

# ---- camera: low, slightly looking up at the two men, waist-up (as in the reference frame)
common.render_settings(res=(1920 * SCALE // 100, 1080 * SCALE // 100), samples=SAMPLES)
cam = common.camera('cam', Vector((0.15, -3.3, 1.12)), Vector((0.1, 0.2, 1.52)), lens=38)
drawn.apply_cycles(lines=1.6 * SCALE / 100 + 0.4, brush=max(3, 5 * SCALE // 100), samples=SAMPLES)
common.render(os.path.join(OUT, 'drawn_hoplites.png'))
print('DRAWN DONE')
