# HERO TEST SHOT (library integration): "That night, Themistocles sent his most trusted servant across the water..."
# Themistocles hands the sealed message to Sicinnus on the harbour wall at dusk; the rowboat waits below.
# Run: blender -b --python blender/scenes/hero_salamis.py -- <out.png> [samples]
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import common, cast, pose, wardrobe, sets

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'hero_salamis.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 64
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
WALL_TOP = 0.8

common.reset_scene()


def person(spec, pose_name, loc, turn_deg, chiton_mat, himation_mat=None, hair=True, after_pose=None):
    """Build one dressed character at the ORIGIN facing -Y (the garment builders assume that), simulate and
    freeze the cloth, then move + turn EVERYTHING that belongs to the character together with one parent empty."""
    before = set(bpy.data.objects)
    human, rig = cast.build_human(spec)
    bpy.context.view_layer.update()
    if hair and spec.get('hair'):
        cast.scalp_hair(human, rig, spec['hair'])
    if spec.get('beard'):
        cast.beard(human, rig, spec['beard'])
    pos, _, _ = cast.rest_surface(human)
    wardrobe.add_collision(human)
    pose.blend_into_pose(rig, pose_name, start=1, end=15)
    ch = wardrobe.chiton(human, rig, pos, chiton_mat)
    wardrobe.simulate(45); wardrobe.freeze(ch)
    rig.animation_data_clear(); pose.apply_pose(rig, pose_name)
    garments = [ch]
    if himation_mat:
        hm = wardrobe.himation(human, rig, pos, himation_mat, side='L', over=ch)
        wardrobe.simulate(60); wardrobe.freeze(hm); garments.append(hm)
    if after_pose:                                      # e.g. a bow of the head, added after the cloth has settled
        pose.apply_pose(rig, after_pose)
    human.modifiers.new('smooth', 'SUBSURF').levels = 1
    # one empty carries the whole character (body, rig, garments, eyes, hair...) to its place
    root = bpy.data.objects.new(f"{rig.name}_root", None); bpy.context.scene.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(turn_deg)
    bpy.context.view_layer.update()
    return rig, human


themis_spec = json.load(open(os.path.join(ROOT, 'library', 'cast', 'themistocles.json'), encoding='utf-8'))
SICINNUS = {"macro": {"gender": 1.0, "age": 0.5, "muscle": 0.55, "weight": 0.45, "proportions": 0.65, "height": 0.55,
                      "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.12, "caucasian": 0.6, "african": 0.28}},
            "skin": "young_caucasian_male", "tan": 1.0, "tan_color": (0.62, 0.42, 0.3), "brows": "eyebrow002",
            "hair": {"density": 30000, "length": 0.02, "curl": 0.003, "melanin": 0.99},
            "beard": {"density": 14000, "length": 0.008, "curl": 0.001, "melanin": 0.99}}       # short stubble: a servant

LINEN = wardrobe.border_material('linen_border', (0.80, 0.75, 0.64), (0.08, 0.12, 0.30), width=0.035)
WOOL = wardrobe.border_material('wool_madder', (0.22, 0.035, 0.03), (0.05, 0.04, 0.03), edge=1, width=0.025)
ROUGH = wardrobe.border_material('undyed_wool', (0.42, 0.36, 0.28), (0.25, 0.2, 0.15), width=0.02)   # plain servant's tunic

# facing -Y is "toward the camera"; +turn rotates toward +X. Three-quarter views, facing each other.
t_rig, t_h = person(themis_spec, 'hand_over', (-0.5, -6.0, WALL_TOP), 62, LINEN, WOOL)
s_rig, s_h = person(SICINNUS, 'receive_body', (0.36, -5.95, WALL_TOP), -70, ROUGH, after_pose='receive')
ANIM = os.environ.get('ANIM') == '1'

# the sealed message in Themistocles' hand
hand = t_rig.matrix_world @ t_rig.pose.bones['wrist.R'].tail
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.017, depth=0.2, location=hand, rotation=(0, math.radians(90), 0))
scroll = bpy.context.object; scroll.data.materials.append(common.principled('papyrus', (0.75, 0.62, 0.42), rough=0.8, bump=0.3, bump_scale=200))
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.012, depth=0.006, location=hand + Vector((0, -0.016, 0)), rotation=(math.radians(90), 0, 0))
seal = bpy.context.object; seal.data.materials.append(common.principled('wax_seal', (0.35, 0.02, 0.02), rough=0.35))
for o in (scroll, seal):
    cast.parent_to_bone(o, t_rig, 'wrist.R')

sets.salamis_dusk()
# FILM LIGHTING: one strong low sun behind-left = golden rim on hair, beard, cloth edges + long shadows;
# a dim cool sky fill only (no flat front light); the lantern adds a warm motivated kick from the boat side.
sun = bpy.data.objects['sun']; sun.data.energy = 9.0; sun.data.color = (1.0, 0.55, 0.28); sun.data.angle = math.radians(0.8)
sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(118))        # golden side light from the left-behind: faces half lit, half in shadow
bpy.data.materials['haze'].node_tree.nodes['Principled Volume'].inputs['Density'].default_value = 0.00003
bpy.context.scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.22
common.area_light('bounce', 60, (1.0, 0.7, 0.5), Vector((0.0, -7.5, 0.9)), Vector((0, -6, 2.0)), 3.0)   # warm stone bounce from below
common.area_light('fill', 25, (0.45, 0.55, 1.0), Vector((3.5, -10.0, 2.4)), Vector((0, -6, 2.0)), 4.0)
common.camera('cam', Vector((2.1, -10.0, 2.05)), Vector((0.0, -6.0, 2.05)), lens=40, fstop=2.4)   # heads are at ~2.55 m (wall 0.8 + body)
common.render_settings(res=(1280, 544), samples=SAMPLES, path=OUT)
bpy.context.scene.view_settings.look = 'AgX - High Contrast'
bpy.context.scene.view_settings.exposure = 0.4
if not ANIM:
    common.render()
else:
    # ---------------- 5-second animated shot ----------------
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, int(os.environ.get('FRAMES', 120)); sc.render.fps = 24
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5      # film-like motion blur
    sc.render.use_persistent_data = False                                       # low-memory laptop: rebuild per frame (slower, ~2 GB less RAM)
    sc.render.use_overwrite = False                                             # resume: skip frames already rendered
    sc.cycles.samples = SAMPLES
    cam = sc.camera
    # slow cinematic push-in (eased): wide two-shot -> closer on the hand-over
    cam.location = Vector((2.7, -11.4, 2.12)); cam.keyframe_insert('location', frame=1)
    cam.location = Vector((1.55, -9.0, 2.06)); cam.keyframe_insert('location', frame=120)
    for fc in cam.animation_data.action.fcurves if cam.animation_data.action and hasattr(cam.animation_data.action, 'fcurves') else []:
        for k in fc.keyframe_points:
            k.interpolation = 'BEZIER'; k.easing = 'EASE_IN_OUT'
    # the sea keeps moving
    oc = bpy.data.objects['ocean'].modifiers['ocean']
    oc.time = 1 / 24; oc.keyframe_insert('time', frame=1)
    oc.time = 120 / 24; oc.keyframe_insert('time', frame=120)
    # the servant bows his head as he takes the message (head bones only; garments stay put)
    pose.apply_pose(s_rig, 'receive_body'); pose.keyframe_pose(s_rig, 1); pose.keyframe_pose(s_rig, 30)
    pose.apply_pose(s_rig, 'receive'); pose.keyframe_pose(s_rig, 80); pose.keyframe_pose(s_rig, 120)
    frames_dir = os.path.join(os.path.dirname(OUT), 'hero_anim_frames')
    os.makedirs(frames_dir, exist_ok=True)
    sc.render.filepath = os.path.join(frames_dir, 'f')
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True)
    print('frames done ->', frames_dir)
