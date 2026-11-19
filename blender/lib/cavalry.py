# CAVALRY: horsemen of each era, mounted, armed and riding in FORMATION at walk / trot / gallop / charge
# (Session G, WS18). Builds on Session E's horse + tack (scans_glb.load_glb('horse_akhalteke'), props.horse_tack)
# and the main session's rider seat (riding.mount: astride, no stirrups, heading 0 = correct for this horse).
#
#   horse(loc, heading, cloth)          one horse with era tack; its root works with animals.play / walk_path
#   rider(era, seed)                    one dressed + armed rider (MakeHuman), sitting astride
#   horseman(era, seed, ...)            horse + rider together (a UNIT: a root that carries both)
#   squadron(era, n, formation, ...)    n horsemen: k unique units + cheap instances, each with its own phase
#   charge(units, schedule, ...)        speed ramps (trot -> canter -> gallop) with clip cross-fades, no sliding
#
# ERA DRESS + WEAPONS (sources, rule r9):
#   greece_480bc : short chiton + CHLAMYS cloak + PETASOS hat, bareback or a plain saddle cloth, TWO JAVELINS
#                  (Parthenon frieze riders; Xenophon, On Horsemanship 12.12: two javelins, one to throw, one to keep)
#   persia_480bc : Median dress = trousers, sleeved tunic, felt cap (bashlyk); checked saddle cloth; two cornel-wood
#                  PALTA javelins + bow and gorytos (Hdt. 7.84: Persian horse armed like the foot, some with bronze
#                  helmets; Xenophon Anabasis 1.8; the Alexander Sarcophagus riders)
#   rome_100bc   : tunic, saddle cloth, HASTA spear (Polybius 6.25: Roman cavalry took Greek-style spears + shields)
#   medieval     : the crowd/wardrobe libraries have no medieval era yet -> Roman body + COUCHED LANCE (flagged)
# No stirrups before the early medieval period (they reach Europe c. 600 AD with the Avars): riders' legs hang,
# toes down - riding.mount already does that.
import math
import random

import bpy
from mathutils import Matrix, Vector

from lib import animals, scans_glb
from lib.common import link, principled

FPS = 24

ERAS = {
    'greece_480bc': {'crowd_era': 'greece_480bc', 'role': 'hoplite', 'cloth': 'greek', 'weapon': 'javelins',
                     'dress': 'greek_rider'},
    'persia_480bc': {'crowd_era': 'persia_480bc', 'role': 'soldier', 'cloth': 'persian', 'weapon': 'javelins_bow',
                     'dress': 'persian_soldier_480bc'},
    'rome_100bc': {'crowd_era': 'rome_100bc', 'role': 'legionary', 'cloth': 'greek', 'weapon': 'spear',
                   'dress': 'roman_legionary_100bc'},
    'medieval': {'crowd_era': 'rome_100bc', 'role': 'legionary', 'cloth': 'greek', 'weapon': 'lance',
                 'dress': 'roman_legionary_100bc', 'todo': 'no medieval wardrobe yet'},
}


# ------------------------------------------------------------------ the horse
def horse(loc=(0, 0, 0), heading_deg=0.0, cloth='greek', name=None):
    """One horse (own rig) with era tack. The root also gets the keys animals.py needs (kind/rig/actions/slot), so
    animals.play(root, 'trot'), animals.clip_speed and animals.walk_path work on it."""
    acts_before = set(a.name for a in bpy.data.actions)
    root = scans_glb.load_glb('horse_akhalteke', loc=loc, rot_z_deg=heading_deg)
    if name:
        root.name = name
    rig = scans_glb.rig_of(root)
    root['kind'] = 'horse'
    if rig is None:                                          # placeholder (scan not on this machine)
        return root
    root['rig'] = rig.name
    root['actions'] = [a.name for a in bpy.data.actions if a.name not in acts_before] or \
        [a.name for a in bpy.data.actions if a.name.split('.')[0] in ('Chewing', 'Trot', 'Run_Gallop')]
    ad = rig.animation_data
    sl = getattr(ad, 'action_slot', None) if ad else None
    root['slot'] = sl.identifier if sl is not None else 'OB' + rig.name
    try:
        from lib import props
        props.horse_tack(root, cloth=cloth)
    except Exception as e:
        print('cavalry: tack skipped -', e)
    rig.data.pose_position = 'POSE'
    return root


def seat_of(horse_root):
    """The 'rider_seat' marker props.horse_tack made for THIS horse."""
    for o in horse_root.children_recursive:
        if o.get('role') == 'rider_seat':
            return o
    nm = horse_root.name + '_tack_rider_seat'
    return bpy.data.objects.get(nm) or next((o for o in bpy.data.objects if o.get('role') == 'rider_seat'
                                            and o.name.startswith(horse_root.name)), None)


# ------------------------------------------------------------------ weapons held while riding
def _wood():
    return bpy.data.materials.get('spear_ash') or principled('spear_ash', (0.35, 0.24, 0.13), rough=0.7, bump=0.2,
                                                             bump_scale=300)


def _bronze():
    return bpy.data.materials.get('bronze') or __import__('lib.common', fromlist=['aged_bronze']).aged_bronze('bronze')


def _iron():
    return bpy.data.materials.get('harness_iron') or principled('harness_iron', (0.06, 0.055, 0.05), metal=0.85, rough=0.5)


def spear(name, length=2.0, head='leaf', metal=None, butt=True):
    """A spear / javelin along +Z from its GRIP point (origin) - shaft runs length*0.4 below the grip and
    length*0.6 above. head: 'leaf' (Greek/Persian bronze leaf blade), 'socket' (iron lance head)."""
    root = link(bpy.data.objects.new(name, None))
    metal = metal or _bronze()
    lo, hi = -length * 0.4, length * 0.6
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.012 if length < 2.5 else 0.018, depth=length,
                                        location=(0, 0, (lo + hi) / 2))
    sh = bpy.context.object; sh.name = name + '_shaft'; sh.data.materials.append(_wood()); sh.parent = root
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=0.026, depth=0.24 if head == 'leaf' else 0.3,
                                    location=(0, 0, hi + 0.11))
    tp = bpy.context.object; tp.name = name + '_head'; tp.scale = (1, 0.3 if head == 'leaf' else 0.8, 1)
    tp.data.materials.append(metal); tp.parent = root
    if butt:
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=0.014, depth=0.1, location=(0, 0, lo - 0.04),
                                        rotation=(math.pi, 0, 0))
        bt = bpy.context.object; bt.name = name + '_butt'; bt.data.materials.append(metal); bt.parent = root
    for o in root.children:
        for p in o.data.polygons:
            p.use_smooth = True
    return root


def arm_rider(rig, era, seed=0, charge=False):
    """Era weapons in the rider's hands. Ride pose: both hands forward on the reins; the RIGHT hand holds the spear
    / javelins upright-forward (on the march) or levelled (charge=True: spear forward over the horse's head, a lance
    couched under the arm)."""
    from lib import tools
    w = ERAS[era]['weapon']
    made = []
    if w in ('javelins', 'javelins_bow'):
        for i in range(2):                                    # two javelins held together, slightly fanned
            j = spear(f'jav_{seed}_{i}', 1.75, 'leaf')
            tools.hold(j, rig, side='R', offset=(0.0, 0.0, 0.01 * i), rot_deg=(-75 if charge else -25, 4 * i, 0))
            made.append(j)
    elif w == 'spear':
        s = spear(f'hasta_{seed}', 2.6, 'leaf', metal=_iron())
        tools.hold(s, rig, side='R', rot_deg=(-80 if charge else -20, 0, 0))
        made.append(s)
    elif w == 'lance':
        s = spear(f'lance_{seed}', 3.4, 'socket', metal=_iron(), butt=False)
        tools.hold(s, rig, side='R', rot_deg=(-88 if charge else -10, 0, -6))
        made.append(s)
    if w == 'javelins_bow':
        try:
            from lib import armour
            wood = bpy.data.materials.get('bow_horn') or principled('bow_horn', (0.25, 0.17, 0.09), rough=0.5)
            leather = bpy.data.materials.get('costume_leather') or principled('costume_leather', (0.22, 0.13, 0.07), rough=0.75)
            made += list(armour.toxon(rig, wood, leather, side='L'))
        except Exception as e:
            print('cavalry: bow skipped -', e)
    return made


# ------------------------------------------------------------------ the rider
def rider(era='greece_480bc', seed=0):
    """A unique rider: MakeHuman body from tc/crowd.py (era faces, ages), groomed, DRESSED for riding, armed.
    Built at the origin facing -Y. Returns (root, rig). Garments are simulated standing, frozen, skinned to the
    body, so they follow the astride pose of riding.mount()."""
    from lib import cast, costume, wardrobe
    from tc import crowd as tcrowd
    E = ERAS[era]
    p = tcrowd.person(seed, E['role'], E['crowd_era'])
    before = set(bpy.data.objects)
    human, rig = cast.build_human(p)
    cast.groom(human, rig, p, seed=p['seed'])
    pos, _, _ = cast.rest_surface(human)
    wardrobe.add_collision(human)
    dye = p.get('dye')
    if E['dress'] == 'greek_rider':
        # Parthenon-frieze rider: a short belted chiton (thigh length so it rides up over the horse) + chlamys + petasos
        main = wardrobe.crowd_cloth(f'rider_chiton_{seed}', dye, seed=seed)
        ch = wardrobe.chiton(human, rig, pos, main, length='knee')
        wardrobe.simulate(40); wardrobe.freeze(ch); wardrobe.bind_to_skeleton(ch, human, rig)
        wool = wardrobe.crowd_cloth(f'rider_chlamys_{seed}', {**dye, 'main': random.Random(seed).choice(
            [(0.42, 0.08, 0.05), (0.2, 0.18, 0.14), (0.48, 0.38, 0.22), (0.12, 0.16, 0.26)])}, wool=True, seed=seed + 1)
        try:
            cl = wardrobe.chlamys(human, rig, wool)
            for g in (cl if isinstance(cl, (list, tuple)) else [cl]):
                if g is not None and g.type == 'MESH' and g.parent is None:
                    wardrobe.bind_to_skeleton(g, human, rig)
        except Exception as e:
            print('cavalry: chlamys skipped -', e)
        try:
            hat = wardrobe.crowd_cloth(f'rider_hat_{seed}', {**dye, 'main': (0.4, 0.31, 0.18), 'patched': False}, wool=True,
                                       seed=seed)
            wardrobe.greek_hat(human, rig, hat, kind='petasos')
        except Exception as e:
            print('cavalry: hat skipped -', e)
    else:
        costume.dress(human, rig, pos, E['dress'], dye=dye, seed=seed)
    root = link(bpy.data.objects.new(f'rider_{era}_{seed}', None))
    for o in set(bpy.data.objects) - before:
        if o.parent is None and o is not root:
            o.parent = root
    human.modifiers.new('smooth', 'SUBSURF').levels = 0
    return root, rig


def horseman(era='greece_480bc', seed=0, loc=(0, 0, 0), heading_deg=0.0, charge=False, name=None):
    """Horse + rider + weapons as ONE unit. Returns the horse root (rider parented to its seat, so the rider rides
    every step). The root works with animals.play / walk_path / charge."""
    E = ERAS[era]
    h = horse((0, 0, 0), 0.0, cloth=E['cloth'] if (seed % 3 or era != 'greece_480bc') else None,
              name=name or f'horse_{era}_{seed}')       # some Greek riders bareback (Parthenon frieze)
    seat = seat_of(h)
    r_root, r_rig = rider(era, seed)
    from lib import riding
    if seat is not None:
        riding.mount(r_rig, r_root, seat, heading_deg=0.0)
    arm_rider(r_rig, era, seed, charge=charge)
    h['rider'] = r_root.name; h['rider_rig'] = r_rig.name
    h.location = loc; h.rotation_euler.z = math.radians(heading_deg)
    return h


# ------------------------------------------------------------------ formations
def formation_marks(n, kind='line', spacing=(1.6, 3.2), seed=0, jitter=0.25):
    """Positions (x, y) relative to the formation centre, front rank at y=0, ranks behind at +y (the formation
    faces -Y). spacing = (between files, between ranks): Xenophon / Asclepiodotus give ~1 m per horse front +
    ~2-3 m depth per rank; we leave a little room for the gallop.
      line   : 2 ranks deep (Greek / Roman ilai and turmae)
      column : 2 files wide (on the march)
      wedge  : the Thracian / Macedonian wedge (embolon) - point first (Asclepiodotus 7.3; Arrian Tactica 16)
      rhombus: the Thessalian rhombus"""
    rnd = random.Random(seed)
    sx, sy = spacing
    out = []
    if kind == 'line':
        per = math.ceil(n / 2)
        for i in range(n):
            r, c = divmod(i, per)
            out.append(((c - (per - 1) / 2) * sx + (sx / 2 if r % 2 else 0), r * sy))
    elif kind == 'column':
        for i in range(n):
            r, c = divmod(i, 2)
            out.append(((c - 0.5) * sx, r * sy))
    elif kind == 'wedge':
        r = 0
        while len(out) < n:
            for c in range(r + 1):
                if len(out) < n:
                    out.append(((c - r / 2) * sx, r * sy))
            r += 1
    else:                                                     # rhombus: widen then narrow
        r, width, grow = 0, 1, True
        while len(out) < n:
            for c in range(width):
                if len(out) < n:
                    out.append(((c - (width - 1) / 2) * sx, r * sy))
            r += 1
            width = width + 1 if grow else width - 1
            if width >= max(3, int(math.sqrt(n)) + 1):
                grow = False
            width = max(1, width)
    return [(x + rnd.uniform(-jitter, jitter), y + rnd.uniform(-jitter, jitter)) for (x, y) in out]


def _unit_collection(unit):
    """Move a built unit (horse root + everything under it, incl. the rider) into its own collection so it can be
    instanced. The unit is parked at the origin."""
    col = bpy.data.collections.new(unit.name + '_unit')
    holder = bpy.data.collections.get('cavalry_sources') or bpy.data.collections.new('cavalry_sources')
    if holder.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(holder)
    holder.children.link(col)
    objs = [unit] + list(unit.children_recursive)
    rr = bpy.data.objects.get(unit.get('rider', ''))
    if rr is not None:
        objs += [rr] + list(rr.children_recursive)
    for o in set(objs):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    lc = bpy.context.view_layer.layer_collection.children.get(holder.name)
    if lc:
        lc.hide_viewport = True
    holder.hide_render = True
    return col


def squadron(era='greece_480bc', n=8, formation='line', center=(0, 0), heading_deg=0.0, unique=3, gait='trot',
             frames=(1, 96), seed=0, spacing=(1.6, 3.2), charge=False):
    """A squadron of n horsemen. `unique` units are fully built (own rider faces, own horse rig, own clip phase);
    the rest are collection INSTANCES of them (each unit costs ~1 rider + 1 horse in memory).
    Returns a list of 'movers' (the unique roots + instance empties) laid out on formation_marks, all facing
    heading_deg. Move them with march(...) or charge(...)."""
    rnd = random.Random(seed)
    units = []
    for u in range(min(unique, n)):
        h = horseman(era, seed * 100 + u, charge=charge)
        clip_ok = animals._action(h, gait) is not None
        if clip_ok:
            animals.play(h, gait, start=frames[0] - 30, end=frames[1], phase_s=rnd.uniform(0, 2), speed=1.0)
        units.append(h)
    marks = formation_marks(n, formation, spacing, seed)
    movers = []
    rot = Matrix.Rotation(math.radians(heading_deg), 2)
    for i, (mx, my) in enumerate(marks):
        p = Vector(center) + rot @ Vector((mx, my))
        if i < len(units):
            u = units[i]; u.location = (p.x, p.y, 0); u.rotation_euler.z = math.radians(heading_deg + rnd.uniform(-3, 3))
            movers.append(u)
        else:
            if i == len(units):                                   # first instance: turn the sources into collections
                srcs = [_unit_collection(u) for u in units]
                movers = [animals.instance(c, tuple(m.location), math.degrees(m.rotation_euler.z), name=m.name + '_lead')
                          for c, m in zip(srcs, movers)]
                for u in units:
                    u.location = (0, 0, 0); u.rotation_euler.z = 0
            e = animals.instance(srcs[i % len(srcs)], (p.x, p.y, 0), heading_deg + rnd.uniform(-3, 3),
                                 name=f'horseman_{era}_{seed}_{i}')
            movers.append(e)
    return movers


def march(movers, distance_or_path, speed, start=1, gait_speed=None):
    """Move every mover straight ahead (its own heading) by `distance` metres at `speed` m/s - or along offsets of
    a path [(x, y)...] relative to each mover. Clips were set in squadron(); gait_speed = the clip's own ground
    speed (measured on the first unique unit) - used to warn if the clip would slide."""
    out_end = start
    for m in movers:
        h = m.rotation_euler.z
        fwd = Vector((math.sin(h), -math.cos(h)))
        p0 = Vector((m.location.x, m.location.y))
        if isinstance(distance_or_path, (int, float)):
            pts = [tuple(p0), tuple(p0 + fwd * distance_or_path)]
        else:
            o = Vector(distance_or_path[0])
            pts = [tuple(p0 + (Vector(q) - o)) for q in distance_or_path]
        m['kind'] = m.get('kind', 'horse')
        out_end = animals.walk_path(m, pts, speed, start=start, play_clip=False)
    return out_end


def charge(movers, schedule, start=1, seed=0, units=None):
    """A CHARGE: speeds ramp through `schedule` = [(seconds_from_start, speed_m_s), ...] e.g.
    [(0, 3.5), (2.0, 6.0), (3.5, 11.0)] trot -> canter -> full gallop. Each mover's root travels the integrated
    distance (ramped speed, no jumps), small per-horse speed differences break the line a little (as in reality),
    and the unique units' clips cross-fade trot -> gallop when speed passes 6 m/s, played at the rate that
    matches the speed (no sliding)."""
    rnd = random.Random(seed)
    sched = sorted(schedule)
    t_end = sched[-1][0] + 3.0

    def v_at(t):
        if t <= sched[0][0]:
            return sched[0][1]
        for (t0, v0), (t1, v1) in zip(sched, sched[1:]):
            if t <= t1:
                a = (t - t0) / max(t1 - t0, 1e-6)
                return v0 + (v1 - v0) * (a * a * (3 - 2 * a))     # smooth ramp
        return sched[-1][1]
    for m in movers:
        k = rnd.uniform(0.94, 1.06)
        h = m.rotation_euler.z
        fwd = Vector((math.sin(h), -math.cos(h)))
        p = Vector((m.location.x, m.location.y)); z = m.location.z
        dist = 0.0
        for f in range(int(start), int(start + t_end * FPS) + 1, 2):
            t = (f - start) / FPS
            m.location = (p.x + fwd.x * dist, p.y + fwd.y * dist, z)
            m.keyframe_insert('location', frame=f)
            dist += v_at(t) * k * 2 / FPS
    # gait clips on the unique units: trot track + gallop track with animated influence (cross-fade at 6 m/s)
    for u in units or []:
        rig = animals.rig_of(u)
        if rig is None:
            continue
        v_tr = animals.clip_speed(u, 'trot'); v_ga = animals.clip_speed(u, 'gallop')
        st_t = animals.play(u, 'trot', start=start - 20, end=int(start + t_end * FPS), phase_s=rnd.uniform(0, 1),
                            speed=max(0.6, min(1.6, sched[0][1] / max(v_tr, 1e-3))))
        st_g = animals.play(u, 'gallop', start=start - 20, end=int(start + t_end * FPS), phase_s=rnd.uniform(0, 1),
                            speed=max(0.6, min(1.5, sched[-1][1] / max(v_ga, 1e-3))), track='gallop')
        if st_g is None:
            continue
        st_g.use_animated_influence = True
        t_switch = next((t for t in [i / 4 for i in range(int(t_end * 4))] if v_at(t) >= 6.0), t_end)
        f_sw = start + t_switch * FPS
        st_g.influence = 0.0; st_g.keyframe_insert('influence', frame=int(f_sw - 6))
        st_g.influence = 1.0; st_g.keyframe_insert('influence', frame=int(f_sw + 6))
        print(f'CHARGE unit {u.name}: trot clip {v_tr:.2f} m/s, gallop clip {v_ga:.2f} m/s, switch at {t_switch:.2f} s')
    return int(start + t_end * FPS)
