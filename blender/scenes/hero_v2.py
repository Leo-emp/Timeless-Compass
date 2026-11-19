# HERO SHOT v2 - "That night, Themistocles sent his most trusted servant across the water..."
# Everything ALIVE: both men breathe, blink, move their eyes and shift their weight; Themistocles reaches out with the
# sealed message, Sicinnus takes it and bows his head; their faces act (resolve / unease -> determination, a faint
# cunning smile); garments follow the bodies; the sea moves; slow eased camera push-in. Set = Salamis v2 (scans).
# Run: blender -b --python blender/scenes/hero_v2.py -- <out_dir> [samples] [still|anim] [res_scale]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import cast, common, expressions, life, pose, sets, wardrobe, camera_moves

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'hero_v2'
SAMPLES = int(argv[1]) if len(argv) > 1 else 32
MODE = argv[2] if len(argv) > 2 else 'still'
RES_K = float(argv[3]) if len(argv) > 3 else 1.0
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
PRE, FIRST, LAST = 30, 31, 150                    # frames 1-30: cloth settles + bodies ease into pose (not shown)
WALL_TOP = 0.8

common.reset_scene()
sc = bpy.context.scene                            # (after the reset: it creates a fresh scene)


def person(spec, mark, turn_deg, chiton_mat, himation_mat=None, seed=0):
    """Build at the origin facing -Y, groom, drape garments standing still, bind them to follow the body,
    then carry everything to its mark with one root empty."""
    before = set(bpy.data.objects)
    human, rig = cast.build_human(spec)
    if spec.get('hair'):
        cast.scalp_hair(human, rig, spec['hair'], seed=seed + 2)
    if spec.get('beard'):
        cast.beard(human, rig, spec['beard'], seed=seed + 1)
    pos, _, _ = cast.rest_surface(human)
    wardrobe.add_collision(human)
    ch = wardrobe.chiton(human, rig, pos, chiton_mat)
    wardrobe.settle_then_follow(ch, human, rig, frames=45, soft=0.25, air=1.0)
    ch.modifiers.new('collision', 'COLLISION'); ch.collision.thickness_outer = 0.012; ch.collision.use_culling = False
    garments = [ch]
    if himation_mat:
        hm = wardrobe.himation(human, rig, pos, himation_mat, side='L', over=ch)
        wardrobe.settle_then_follow(hm, human, rig, frames=60, soft=0.35, mass=0.45, air=0.5)
        garments.append(hm)
    for g in garments:
        for m in g.modifiers:
            if m.type == 'CLOTH':
                m.point_cache.frame_start, m.point_cache.frame_end = 1, LAST
    human.modifiers.new('smooth', 'SUBSURF').levels = 1
    root = bpy.data.objects.new(f'{rig.name}_root', None); sc.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    root.location = mark; root.rotation_euler.z = math.radians(turn_deg)
    bpy.context.view_layer.update()
    return human, rig


themis = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
SICINNUS = {"macro": {"gender": 1.0, "age": 0.5, "muscle": 0.55, "weight": 0.45, "proportions": 0.65, "height": 0.55,
                      "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.12, "caucasian": 0.6, "african": 0.28}},
            "skin": "young_caucasian_male", "tan": 1.0, "tan_color": (0.62, 0.42, 0.3), "brows": "eyebrow002",
            "face": {"head-oval": 0.4, "nose-hump-incr": 0.2, "cheek-bones-incr": 0.2, "chin-prominent-incr": 0.2,
                     "eyebrows-trans-down": 0.15},
            "age_lines": 0.3, "stubble": 0.8,
            "hair": {"density": 30000, "length": 0.022, "curl": 0.003, "melanin": 0.99},
            "beard": {"density": 14000, "length": 0.007, "curl": 0.001, "melanin": 0.99}}     # short stubble: a servant

LINEN = wardrobe.scan_cloth('linen_v2', 'rough_linen', (0.52, 0.47, 0.37), band=(0.07, 0.10, 0.26), tiles=(7, 5), width=0.035, sheen=0.15)
WOOL = wardrobe.scan_cloth('wool_v2', 'caban', (0.30, 0.05, 0.035), band=(0.05, 0.035, 0.025), tiles=(4, 12), edge=1,
                           width=0.025, grime=0.25, sheen=0.15)
COARSE = wardrobe.scan_cloth('coarse_v2', 'hessian_230', (0.40, 0.34, 0.26), tiles=(6, 5), grime=0.45, sheen=0.1)   # servant's undyed tunic

t_h, t_rig = person(themis, (-0.5, -6.0, WALL_TOP), 62, LINEN, WOOL, seed=0)
s_h, s_rig = person(SICINNUS, (0.36, -5.95, WALL_TOP), -70, COARSE, seed=10)

# ---------------- acting (frames 1-30 = ease from rest into the opening pose while the cloth settles)
pose.blend_into_pose(t_rig, 'stand_relaxed', start=1, end=PRE)
pose.blend_into_pose(s_rig, 'stand_relaxed', start=1, end=PRE)
# the HAND-OVER: both men's hands meet at one point between them, at chest height (two-bone reach, not fixed poses)
sc.frame_set(PRE)
t_chest = t_rig.matrix_world @ t_rig.pose.bones['spine01'].head
s_chest = s_rig.matrix_world @ s_rig.pose.bones['spine01'].head
meet = (t_chest + s_chest) / 2 + Vector((0, -0.08, -0.05))       # a little toward the camera so we SEE the scroll
for side in ('R',):
    pose.key_arm(t_rig, side, 60)
    pose.reach(t_rig, side, meet + Vector((-0.05, 0, 0)))
    pose.key_arm(t_rig, side, 78); pose.key_arm(t_rig, side, 150)
for side, off in (('L', Vector((0.06, 0.04, 0.03))), ('R', Vector((0.06, -0.05, -0.03)))):
    pose.key_arm(s_rig, side, 66)
    pose.reach(s_rig, side, meet + off)
    pose.key_arm(s_rig, side, 86); pose.key_arm(s_rig, side, 150)
# ...then Sicinnus bows his head as he takes it (neck + head only, his hands stay on the scroll)
for n in ('neck01', 'head'):
    pb = s_rig.pose.bones[n]; pb.keyframe_insert('rotation_quaternion', frame=98)
pose.aim(s_rig, 'neck01', (0.0, -0.35, 1.0)); pose.aim(s_rig, 'head', (0.0, -0.5, 1.0))
for n in ('neck01', 'head'):
    pb = s_rig.pose.bones[n]; pb.keyframe_insert('rotation_quaternion', frame=116); pb.keyframe_insert('rotation_quaternion', frame=150)
t_lids = expressions.perform(t_h, t_rig, [(FIRST, 'resolve', 0.9), (108, 'cunning', 0.6)])
s_lids = expressions.perform(s_h, s_rig, [(FIRST, 'fear', 0.45), (102, 'resolve', 0.6)])
life.bring_to_life(t_rig, FIRST, LAST, seed=3, look=(0.0, -3.0), lid_open=t_lids[0][1])
life.bring_to_life(s_rig, FIRST, LAST, seed=7, look=(0.0, 2.0), lid_open=s_lids[0][1])

# the sealed message in Themistocles' hand
sc.frame_set(78)
hand = t_rig.matrix_world @ t_rig.pose.bones['wrist.R'].tail
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.026, depth=0.30, location=hand + Vector((0.05, -0.04, 0.04)), rotation=(0, math.radians(90), math.radians(-25)))
scroll = bpy.context.object; scroll.data.materials.append(common.principled('papyrus', (0.75, 0.62, 0.42), rough=0.8, bump=0.3, bump_scale=200))
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.02, depth=0.008, location=hand + Vector((0.05, -0.068, 0.04)), rotation=(math.radians(90), 0, 0))
seal = bpy.context.object; seal.data.materials.append(common.principled('wax_seal', (0.35, 0.02, 0.02), rough=0.35))
for o in (scroll, seal):
    cast.parent_to_bone(o, t_rig, 'wrist.R')

# ---------------- set + light (moody: rule r10, keep real shadows)
sets.salamis_dusk_v2(density=1.0)
sets.salamis_film_light()
bpy.data.objects['fill'].data.energy = 12                                # less fill = deeper shadows on the far side
# warm sunset RIM from behind the men (sea side): bright edges on hair, beards and cloth separate them from the
# background (the reference's strongest lighting trait); low and to the side so faces keep a shadow side
# hot sunset RIM as a tight SPOT on heads + shoulders only (an area light also lit the wall white)
bpy.ops.object.light_add(type='SPOT', location=(-2.6, -2.0, 3.1))
rim = bpy.context.object; rim.name = 'rim_chars'
rim.data.energy = 2600; rim.data.color = (1.0, 0.55, 0.26); rim.data.spot_size = math.radians(16); rim.data.spot_blend = 0.6
rim.data.shadow_soft_size = 0.25
common.look_at(rim, Vector((0.0, -6.0, 2.35)))
common.area_light('key_chars', 60, (1.0, 0.78, 0.58), Vector((3.2, -8.6, 2.6)), Vector((0.0, -6.0, 2.2)), 1.5)
cam = common.camera('cam', Vector((2.7, -11.4, 2.45)), Vector((0.0, -6.0, 2.0)), lens=35, fstop=2.4)   # wall under their feet AND hills above
heads = (t_rig.matrix_world @ t_rig.pose.bones['head'].head + s_rig.matrix_world @ s_rig.pose.bones['head'].head) / 2
cam.data.dof.focus_distance = (heads - cam.location).length
cam.location = Vector((2.7, -11.4, 2.45)); cam.keyframe_insert('location', frame=FIRST)
cam.location = Vector((1.6, -9.3, 2.3)); cam.keyframe_insert('location', frame=LAST)
camera_moves._ease(cam)
oc = bpy.data.objects['ocean'].modifiers['ocean']
oc.time = FIRST / 24; oc.keyframe_insert('time', frame=FIRST)
oc.time = LAST / 24; oc.keyframe_insert('time', frame=LAST)

common.render_settings(res=(int(1280 * RES_K), int(544 * RES_K)), samples=SAMPLES)
sc.view_settings.look = 'AgX - High Contrast'
sc.view_settings.exposure = 0.1
sc.frame_start, sc.frame_end = 1, LAST
os.makedirs(OUT, exist_ok=True)
bpy.ops.ptcache.bake_all(bake=True)                                      # cloth from frame 1, then render the shot
if MODE == 'best':                              # ONE frame at final quality: shows the real ceiling, not a test
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.cycles.samples = SAMPLES
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.frame_set(118)
    common.render(os.path.join(OUT, 'best_0118.png'))
elif MODE == 'still':
    for f in (FIRST + 10, 84, 120):
        sc.frame_set(f)
        common.render(os.path.join(OUT, f'still_{f:04d}.png'))
else:
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.render.use_persistent_data = False; sc.render.use_overwrite = False
    sc.frame_start = FIRST
    sc.render.filepath = os.path.join(OUT, 'frames', 'f')
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True)
print('HERO V2 DONE')
