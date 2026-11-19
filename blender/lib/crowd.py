# CROWDS IN BLENDER: turns tc/crowd.py people (unique, era-correct, seeded) into 3D people on a set.
# Detail by distance, so a crowd of thousands stays affordable:
#   mid  (10-40 m): every person FULLY built - own face, body, hair, dyed garment (cloth draped once, then frozen),
#                   own motion clip with its own start offset + speed, own life seed (no two move in sync)
#   far  (40 m+)  : lightweight INSTANCES of the mid people (shared meshes), shuffled turn / scale / place - at that
#                   distance nobody can tell, and it costs almost nothing
# Spec dicts come from tc.crowd.person()/cast() (run in normal Python, passed in as JSON).
import math
import random

import bpy
from mathutils import Vector

from lib import cast, life, motion, pose, wardrobe

DYE_SCAN = {'royal': 'caban', 'rich': 'caban', 'common': 'rough_linen', 'poor': 'hessian_230'}


def _garment_material(p, k):
    d = p['dye']
    scan = DYE_SCAN.get(d['rank'], 'rough_linen')
    band = tuple(d['band']) if d['rank'] in ('royal', 'rich') else None
    return wardrobe.scan_cloth(f"crowd_{p['seed']}_{k}", scan, tuple(d['main']), band=band, tiles=(6, 5),
                               grime=d['grime'], sheen=0.15)


CREST = {'red': (0.16, 0.008, 0.006), 'black': (0.02, 0.02, 0.02), 'white': (0.85, 0.82, 0.75),
         'tall_red': (0.16, 0.008, 0.006), 'tall_white': (0.85, 0.82, 0.75)}


def arm_hoplite(p, human, rig, chiton):
    """Full hoplite kit for a crowd soldier, unique per man: crest colour, his OWN painted shield emblem (tc.emblems,
    vase-painting style), then the bronze pieces ride his bones (armour.follow_body) so the kit moves when he marches."""
    import os, sys
    from lib import armour, common
    root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
    bronze = bpy.data.materials.get('aged_bronze') or common.aged_bronze()
    leather = bpy.data.materials.get('pteruges_leather') or common.principled('pteruges_leather', (0.18, 0.1, 0.05), rough=0.8)
    wood = bpy.data.materials.get('spear_ash') or common.principled('spear_ash', (0.35, 0.24, 0.13), rough=0.7)
    helm = p.get('helmet') or {'crest': 'red'}
    seed = p.get('seed', abs(hash(p.get('name', 'hoplite'))) % 1000)
    if helm.get('crest', 'none') != 'none':
        armour.corinthian_helmet(human, rig, bronze, crest_color=CREST.get(helm['crest'], CREST['red']))
    cu, hem_z, cy = armour.muscle_cuirass(human, rig, bronze)
    armour.delete_verts(chiton, lambda q: q.z > hem_z - 0.02)               # only the tunic skirt shows below the bronze
    pt = armour.pteruges(hem_z, cy, 0.205, 0.165, leather)
    gr = armour.greaves(human, rig, bronze)
    sh = p.get('shield') or {'emblem': 'lambda', 'wear': 0.5}
    img = os.path.join(root_dir, 'spike', 'emblems_gen', f"{sh['emblem']}_{seed}.png")
    if not os.path.exists(img):
        try:
            from tc import emblems                     # needs Pillow (not in Blender's own Python on every machine)
            emblems.paint(sh['emblem'], img, size=512, seed=seed)
        except ImportError:                            # Blender's own Python has no Pillow: paint with the system one
            import subprocess
            subprocess.run(['python', '-c', f"from tc import emblems; emblems.paint({sh['emblem']!r}, {img!r}, size=512, seed={seed})"],
                           cwd=root_dir, check=False)
    armour.aspis(rig, bronze, emblem_image=img)
    if p.get('weapon') == 'sword':                     # spear broken / close fight: the xiphos is drawn
        armour.xiphos(rig, bronze, wood)
    else:
        armour.dory(rig, bronze, wood)
    armour.follow_body(rig, cu, pt, gr)
    if p.get('cloak') == 'crimson':                    # the Spartan phoinikis, draped over the bronze from the shoulders
        from lib import wardrobe
        red = bpy.data.materials.get('phoinikis') or wardrobe.scan_cloth('phoinikis', 'caban', (0.36, 0.035, 0.03),
                                                                         tiles=(4, 12), grime=0.3, sheen=0.12)
        pos, _, _ = cast.rest_surface(human)
        cl = wardrobe.himation(human, rig, pos, red, side='L', over=cu)
        wardrobe.simulate(50); wardrobe.freeze(cl)
        wardrobe.bind_to_skeleton(cl, human, rig)


def build_person(p, mark=(0, 0, 0), turn_deg=0.0, frames=96, settle=40):
    """One mid-ground person from a crowd spec. Garment draped while standing (cloth simulated `settle` frames), then
    FROZEN (no per-frame cloth for extras = big saving), motion clip retargeted with its own offset. Returns root."""
    before = set(bpy.data.objects)
    human, rig = cast.build_human(p)
    cast.groom(human, rig, p, seed=p['seed'])
    pos, _, _ = cast.rest_surface(human)
    wardrobe.add_collision(human)
    w = p.get('wardrobe') or ''
    if w.endswith('hoplite_480bc') or not w:
        length = 'ankle' if p['macro']['gender'] < 0.5 or p.get('rank') in ('royal',) else 'knee'
        ch = wardrobe.chiton(human, rig, pos, _garment_material(p, 0), length=length)
        wardrobe.simulate(settle); wardrobe.freeze(ch)
        wardrobe.bind_to_skeleton(ch, human, rig)            # frozen garment still follows the body (skinned)
        if w.endswith('hoplite_480bc'):
            arm_hoplite(p, human, rig, ch)
    else:                                                     # the full era outfit for this role (Session D garments)
        from lib import costume
        costume.dress(human, rig, pos, w, dye=p.get('dye'), seed=p['seed'])
        if p.get('role') == 'archer' and p.get('era') == 'greece_480bc':      # light troops: no bronze, bow + quiver
            from lib import armour, common
            wood = bpy.data.materials.get('bow_horn') or common.principled('bow_horn', (0.25, 0.17, 0.09), rough=0.5)
            leather = bpy.data.materials.get('costume_leather') or common.principled('costume_leather', (0.22, 0.13, 0.07), rough=0.75)
            armour.toxon(rig, wood, leather)
        if p.get('role') in ('immortal', 'soldier', 'archer') and p.get('era') == 'persia_480bc':
            from lib import armour, common
            gold = bpy.data.materials.get('costume_gold') or common.principled('costume_gold', (0.83, 0.62, 0.26), metal=1.0, rough=0.3)
            wood = bpy.data.materials.get('spear_ash') or common.principled('spear_ash', (0.35, 0.24, 0.13), rough=0.7)
            leather = bpy.data.materials.get('costume_leather') or common.principled('costume_leather', (0.22, 0.13, 0.07), rough=0.75)
            armour.immortal_kit(rig, gold, wood, leather)     # spear + pomegranate, bow, quiver
            if p.get('role') == 'soldier':
                armour.spara(rig)                             # front-rank sparabara: big wicker shield
    m = p.get('motion') or {}
    clip = m.get('clip')
    if clip:
        skip = int(m.get('offset_s', 0) * 24)                 # each extra starts the clip at a different moment
        try:
            motion.apply_bvh(rig, clip, start=1, hold=0, max_frames=frames, skip=skip, travel=False)
        except Exception:
            pose.apply_pose(rig, 'stand_relaxed')
    else:
        pose.apply_pose(rig, 'stand_relaxed')
    life.bring_to_life(rig, 1, frames, seed=m.get('life_seed', p['seed']), standing=not clip)
    human.modifiers.new('smooth', 'SUBSURF').levels = 0     # extras: no subdivision (they are 10 m+ away)
    root = bpy.data.objects.new(f"extra_{p['seed']}", None); bpy.context.scene.collection.objects.link(root)
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    root.location = mark; root.rotation_euler.z = math.radians(turn_deg)
    return root


def mid_crowd(people, marks, frames=96, face_toward=None):
    """Build `people` on `marks` [(x, y, z)]; if face_toward = (x, y), everyone turns roughly toward it (an audience,
    a phalanx facing the enemy) with a little personal variation."""
    roots = []
    rnd = random.Random(len(people))
    for p, mk in zip(people, marks):
        turn = rnd.uniform(-180, 180)
        if face_toward is not None:
            dx, dy = face_toward[0] - mk[0], face_toward[1] - mk[1]
            turn = math.degrees(math.atan2(dx, -dy)) + rnd.gauss(0, 12)     # 0 deg = facing -Y
        roots.append(build_person(p, mk, turn, frames))
    return roots


def far_crowd(source_roots, area, count, z_fn=None, seed=0, face_toward=None, collection_name='far_crowd'):
    """Instances of the built mid-crowd people, scattered over `area` (xmin, xmax, ymin, ymax). Each source person is
    wrapped in a collection once; instances share all meshes. z_fn(x, y) -> ground height."""
    rnd = random.Random(seed)
    cols = []
    for r in source_roots:
        col = bpy.data.collections.new(f'{r.name}_inst')
        def add(o):
            col.objects.link(o)
            for c in o.children:
                add(c)
        add(r)
        col.instance_offset = r.location
        cols.append(col)
    out = bpy.data.collections.new(collection_name); bpy.context.scene.collection.children.link(out)
    x0, x1, y0, y1 = area
    for i in range(count):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        inst = bpy.data.objects.new(f'{collection_name}_{i}', None)
        inst.instance_type = 'COLLECTION'; inst.instance_collection = rnd.choice(cols)
        inst.location = (x, y, z_fn(x, y) if z_fn else 0.0)
        turn = rnd.uniform(0, 2 * math.pi)
        if face_toward is not None:
            turn = math.atan2(face_toward[0] - x, -(face_toward[1] - y)) + rnd.gauss(0, 0.2)
        inst.rotation_euler.z = turn
        s = rnd.uniform(0.94, 1.06); inst.scale = (s, s, s)
        out.objects.link(inst)
    return out
