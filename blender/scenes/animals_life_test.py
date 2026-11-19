# WS18 ANIMAL LIFE: animals MOVING in a farm landscape (blender/lib/animals.py + harness.py):
#   - a grazing herd of goats + oxen resting, sheep flock DRIVEN along a track by a walking shepherd with his crook
#   - a pair of oxen pulling Session D's farm cart (tools.cart, wheels rolling), a donkey with panniers walking
#   - a hound trotting along the track, chickens pecking + stepping in the yard, a pig rooting
# Motion is judged from 4 stills 1 s apart (rule r13: no full video renders until the stills pass).
# Laptop only (Sketchfab scans + MakeHuman).
# Run: blender -b --python blender/scenes/animals_life_test.py -- <out_dir> [samples] [parts=all|herd,flock,cart,donkey,hound,yard]
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', '..'))
import bpy
from mathutils import Vector
from lib import animals, common, harness, scatter

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'animals_life'
SAMPLES = int(argv[1]) if len(argv) > 1 else 24
PARTS = set((argv[2] if len(argv) > 2 else 'all').split(','))
ALL = 'all' in PARTS
FRAMES = (1, 96)
common.reset_scene()
sc = bpy.context.scene; sc.frame_start, sc.frame_end = FRAMES
sc.render.fps = 24

# ---------------------------------------------------------------- ground + light (warm late afternoon)
gm = scatter.scan_material('life_ground', 'brown_mud_dry', tint=(0.82, 0.78, 0.62), tiles=4.0)
bpy.ops.mesh.primitive_plane_add(size=300); bpy.context.object.data.materials.append(gm)
track_m = scatter.scan_material('life_track', 'brown_mud_dry', tint=(0.95, 0.85, 0.7), tiles=2.0)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -50)); tr = bpy.context.object; tr.hide_render = True   # (track strip off: a hard edge read as a ruler line)
tr.data.transform(__import__('mathutils').Matrix.Diagonal((3.2, 120, 1, 1))); tr.data.materials.append(track_m)
common.hdri_world('kloofendal_48d_partly_cloudy_puresky', strength=0.7)
common.sun_light('sun', 3.6, (1.0, 0.86, 0.68), 24, 235)

# real ground cover (scanned grass / shrubs / stones / olive trees), kept off the tracks the animals use
ground = bpy.data.objects['Plane']
clear = [(x, y, r) for y in range(-40, 45, 3) for (x, r) in ((0.0, 2.6), (-7.2, 2.4), (2.4, 1.6))]
clear += [(-4.0, -1.5, 2.8), (4.5, -3.0, 1.6)]                     # the yard + the doves
for i, (sid, n, area, size) in enumerate([('grass_medium_01', 7000, (-30, 30, -30, 60), (0.7, 1.3)),
                                          ('shrub_01', 120, (-30, 30, -20, 60), (0.7, 1.3)),
                                          ('boulder_01', 40, (-30, 30, -20, 60), (0.25, 0.6)),
                                          ('tree_olive_zakynthos', 12, (-60, 60, 35, 110), (0.8, 1.2)),
                                          ]):
    try:
        scatter.scatter(ground, [sid], n, area, seed=4 + i, size=size, min_z=-1.0, keep_clear=clear, near=(6, -10),
                        clusters=40, collection_name=f'life_{sid}')
    except Exception as e:
        import traceback; traceback.print_exc()
        print('LIFE ground cover skipped -', sid, e)
from lib import sets
sets.haze(size=(900, 900, 120), density=0.0004, color=(1.0, 0.86, 0.7))

TRACK_X = 0.0         # the farm track runs along Y; everything travels toward -Y (toward the camera's left)

# ---------------------------------------------------------------- grazing herd (instances of 4 actors each)
if ALL or 'herd' in PARTS:
    animals.herd('goat', center=(-9, 6), count=9, radius=5, heading_deg=30, seed=3, name='goats')
    animals.herd('ox', center=(11, 14), count=3, radius=4, heading_deg=-60, clips=('eat', 'idle', 'idle2'), seed=5,
                 variants=3, name='oxen_rest')
    animals.herd('pig', center=(-6, -6), count=3, radius=2, heading_deg=120, clips=('idle',), variants=2, seed=8, name='pigs')

# ---------------------------------------------------------------- a flock driven down the track + the shepherd
if ALL or 'flock' in PARTS:
    FLOCK = []
    path = [(TRACK_X + 0.3, 22), (TRACK_X, 8), (TRACK_X - 0.4, -10), (TRACK_X - 0.6, -30)]
    FLOCK = animals.flock_move('sheep', path, count=26, speed=1.0, start=1, spread=5.0, depth=10.0, variants=4, seed=11,
                               name='flock')
    try:
        from tc import crowd as tcrowd
        from lib import crowd, tools
        p = tcrowd.person(41, 'shepherd', 'greece_480bc')
        p['motion'] = {'clip': 'walking', 'offset_s': 0.0}
        shep = crowd.build_person(p, (0, 0, 0), 0.0, frames=FRAMES[1] + 10)
        rig = next(o for o in shep.children_recursive if o.type == 'ARMATURE')
        crook = tools.crook('shep_crook'); tools.hold(crook, rig, side='R')
        shep['kind'] = 'person'
        # the shepherd walks 2 m behind the last sheep at the flock's pace (Mixamo 'walking' ~1.3 m/s native)
        animals.walk_path(shep, [(TRACK_X + 1.2, 33), (TRACK_X + 1.0, 8), (TRACK_X + 0.6, -30)], 1.0, start=1,
                          play_clip=False)
    except Exception as e:
        print('LIFE shepherd skipped -', e)

# ---------------------------------------------------------------- ox team pulling the farm cart
if ALL or 'cart' in PARTS:
    team = bpy.data.objects.new('ox_team', None); sc.collection.objects.link(team); team['kind'] = 'team'
    try:
        from lib import tools
        cart = tools.cart((0, 0, 0), 0.0, load='sacks', seed=4, name='farmcart')
        cart.parent = team
        # spin Session D's disc wheels about their own axis (their mesh axis is local Z, turned by Y 90 deg)
        bpy.context.view_layer.update()
        wheels = [o for o in cart.children if '_wheel' in o.name]
        for w in wheels:
            for b in [o for o in cart.children if o.name.startswith('farmcart_bar') and abs(o.location.x - w.location.x) < 0.1]:
                m = b.matrix_world.copy(); b.parent = w; b.matrix_world = m
            w.rotation_mode = 'ZYX'
    except Exception as e:
        print('LIFE cart skipped -', e); wheels = []
    oxen = []
    for i, sx in enumerate((-1, 1)):
        ox = animals.load('ox', (sx * 0.62, -2.55, 0), 0.0, name=f'cart_ox{i}'); ox.parent = team; oxen.append(ox)
    harness.yoke_pair('cart_yoke', team, (0, -3.05, 1.02), span=1.24, kind='ox')
    SP = 0.85
    animals.walk_path(team, [(-7, 30), (-7.2, 0), (-7.5, -30)], SP, start=1, play_clip=False)
    for i, ox in enumerate(oxen):
        rate = SP / max(animals.clip_speed(ox, 'walk'), 1e-3)
        animals.play(ox, 'walk', start=1, end=FRAMES[1], phase_s=i * 0.45, speed=max(0.5, min(1.8, rate)))
    for w in wheels:
        dist = SP * (FRAMES[1] - FRAMES[0]) / 24
        w.rotation_euler.z = 0.0; w.keyframe_insert('rotation_euler', index=2, frame=FRAMES[0])
        w.rotation_euler.z = dist / 0.48; w.keyframe_insert('rotation_euler', index=2, frame=FRAMES[1])
        for fc in (w.animation_data.action.fcurves if hasattr(w.animation_data.action, 'fcurves') else []):
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'

# ---------------------------------------------------------------- donkey with panniers
if ALL or 'donkey' in PARTS:
    dk = animals.load('donkey', (0, 0, 0), 0.0, name='pack_donkey')
    rig = animals.rig_of(dk)
    bpy.context.view_layer.update()
    # hang the pack saddle on the spine bone so it rides the donkey's back through the walk cycle
    sb = animals._bone(rig, 'Spine1_014')
    pb = rig.pose.bones[sb.name]
    meshes = [bpy.data.objects[n] for n in dk['mesh_names']]
    lo, hi = animals._mesh_bbox(meshes)
    back = Vector((dk.location.x, (rig.matrix_world @ pb.head).y, 0))
    # top of the back over the middle of the body = highest skin point near the spine bone
    back.z = max((m.matrix_world @ v.co).z for m in meshes for v in m.data.vertices
                 if abs((m.matrix_world @ v.co).y - back.y) < 0.08 and abs((m.matrix_world @ v.co).x) < 0.08)
    half_w = (hi.x - lo.x) / 2 * 0.72
    pan = harness.panniers(back, girth_z=-(back.z * 0.42), side_x=half_w, name='donkey_pack', load='produce', seed=2)
    bpy.context.view_layer.update()                    # (matrix_world is stale until an update)
    m = pan.matrix_world.copy(); pan.parent = rig; pan.parent_type = 'BONE'; pan.parent_bone = sb.name
    pan.matrix_world = m
    animals.walk_path(dk, [(2.6, 26), (2.5, 0), (2.3, -30)], 1.15, start=1, gait='walk', phase_s=0.3)

# ---------------------------------------------------------------- hound trotting ahead of the flock
if ALL or 'hound' in PARTS:
    hd = animals.load('dog', (0, 0, 0), 0.0, name='hound')
    end = animals.walk_path(hd, [(1.8, 14), (1.2, 4), (2.2, -6), (1.0, -30)], 2.6, start=1, play_clip=False)
    animals.gait(hd, 1, min(end, FRAMES[1]), speed=2.6, kind='trot')
    idle_dog = animals.load('dog', (-2.2, -3.5, 0), 140.0, name='yard_dog')      # a second dog sniffing the yard
    animals.play(idle_dog, 'idle', start=1, end=FRAMES[1], phase_s=2.0)

# ---------------------------------------------------------------- the yard: chickens + pigeons
if ALL or 'yard' in PARTS:
    animals.poultry('chicken', center=(-4.0, -1.5), count=7, radius=2.2, frames=FRAMES, seed=21, name='hens')
    animals.poultry('pigeon', center=(4.5, -3.0), count=4, radius=1.2, frames=FRAMES, seed=23, name='doves')

# ---------------------------------------------------------------- cameras + stills 1 s apart
common.render_settings(res=(1280, 720), samples=SAMPLES)
os.makedirs(OUT, exist_ok=True)
views = {'wide': (Vector((16, -16, 4.0)), Vector((-1, 3, 0.8)), 30),
         'track': (Vector((5.5, -9, 1.3)), Vector((0, 2, 0.7)), 35)}
for vn, (loc, tgt, lens) in views.items():
    sc.camera = common.camera('cam_' + vn, loc, tgt, lens=lens)
    for f in (25, 61):
        sc.frame_set(f)
        common.render(os.path.join(OUT, f'{vn}_f{f:03d}.png'))


def follow(obj, name, offset, look, lens=50):
    """A camera that travels WITH a moving animal (parented to its root), offset in the animal's own frame
    (the animal faces -Y): judge the gait close up."""
    if obj is None:
        return None
    c = common.camera(name, Vector(offset), Vector(look), lens=lens)
    c.parent = obj
    return c


sc.frame_set(1)
follows = []
if ALL or 'flock' in PARTS:
    lead = min(FLOCK, key=lambda e: e.location.y) if FLOCK else None
    follows.append(follow(lead, 'cam_flock', (4.5, -3.5, 1.1), (0.0, 1.5, 0.45), 40))
if ALL or 'cart' in PARTS:
    follows.append(follow(bpy.data.objects.get('ox_team'), 'cam_cart', (4.2, -6.0, 1.4), (0.0, -2.0, 0.9), 35))
if ALL or 'donkey' in PARTS:
    follows.append(follow(bpy.data.objects.get('pack_donkey'), 'cam_donkey', (4.2, -2.4, 1.3), (0, 0.1, 0.7), 40))
if ALL or 'hound' in PARTS:
    follows.append(follow(bpy.data.objects.get('hound'), 'cam_dog', (2.4, -0.6, 0.55), (0, 0, 0.35), 50))
if ALL or 'yard' in PARTS:
    follows.append(common.camera('cam_yard', Vector((-2.0, -5.0, 0.6)), Vector((-4.0, -1.5, 0.15)), lens=50))
for c in follows:
    if c is None:
        continue
    sc.camera = c
    for f in (25, 31, 61):
        sc.frame_set(f)
        common.render(os.path.join(OUT, f'{c.name[4:]}_f{f:03d}.png'))
print('LIFE DONE')
