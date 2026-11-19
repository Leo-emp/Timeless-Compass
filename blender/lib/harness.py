# HARNESS: everything an animal PULLS or CARRIES, built by code (Session G, WS18).
#
#   wheel(...)               - a spoked wheel (hub, spokes, felloe, tyre, optional bronze/iron studs)
#   chariot_egypt(...)       - New Kingdom war chariot, c. 1250 BC (Ramesses II at Kadesh)
#   chariot_persia(...)      - Achaemenid chariot, c. 500-480 BC (Persepolis reliefs, the Oxus Treasure model)
#   wagon(...)               - four-wheeled farm / baggage wagon (Roman carrus -> medieval -> 18th-19th c. wagon)
#   limber(...)              - Napoleonic artillery limber (two wheels + ammunition chest + pintle hook)
#   limber_gun(...)          - hook cannon.build('field')'s gun onto a limber, trail up, muzzle backwards
#   panniers(...)            - a pack saddle (Greek 'sagma') with two wicker baskets for a donkey or mule
#   yoke_pair(...)           - a wooden neck yoke for two oxen (or a chariot yoke with yoke saddles for horses)
#   roll(obj_or_root, path)  - turn every wheel of a vehicle by the distance it travels (no skidding wheels)
#
# CONVENTION (same as the horse scan + tools.cart): the vehicle FACES -Y at heading 0 (the pole points to -Y), the
# origin is on the ground under the axle. Every builder returns its root empty; root['wheels'] lists wheel names and
# root['hitch'] is the point (local) where the yoke / pole end is, root['wheel_r'] the wheel radius.
#
# Sources for the shapes and sizes (rule r9: designed from museum pieces, never copied from films / games):
#   Egyptian chariot  - Tutankhamun's chariots (Cairo, Egyptian Museum JE 61989-61996; Littauer & Crouwel, "Chariots
#                       and Related Equipment from the Tomb of Tut'ankhamun", 1985): wheel ~0.9-1.0 m with SIX spokes,
#                       axle at the very BACK of the car, D-shaped floor ~1.0 x 0.5 m of interwoven leather thongs,
#                       side screens ~0.75 m high, a pole running under the floor and curving up to a yoke with
#                       Y-shaped YOKE SADDLES on the horses' withers; bow case + quiver strapped on the sides.
#   Persian chariot   - Persepolis Apadana reliefs (Lydian / Elamite delegations), the gold chariot model of the Oxus
#                       Treasure (British Museum 123908), the Darius seal (BM 89132): bigger wheels (~1.1-1.2 m) with
#                       many spokes (we use 12) and studded tyres, a box car with a high front, axle at the back.
#   Wagon             - Roman 'plaustrum'/'carrus' reliefs and the medieval Luttrell Psalter (BL Add MS 42130):
#                       small front wheels on a turning fore-carriage, bigger rear wheels, slatted sides.
#   Limber            - French Gribeauval system (1765-1820s) and British Napoleonic 9-pdr/12-pdr limbers (Royal
#                       Artillery Museum drawings): two ~1.37 m wheels, an AMMUNITION CHEST on the frame (gunners
#                       could sit on it), a POLE for the wheel pair of horses, a PINTLE hook at the back that takes
#                       the trail eye of the gun. Teams of 6 horses, drivers ride the LEFT (near) horse of each pair.
#   Pack saddle       - Greek 'kanthelia' panniers on donkeys on Attic vases + terracotta figurines (e.g. Boeotian
#                       donkey with panniers, 5th c. BC): a wooden frame saddle on a pad, two baskets, a girth rope.
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

from lib.common import aged_bronze, link, mesh_obj, principled


# ------------------------------------------------------------------ materials (shared, created once)
def _wood(name='harness_wood', color=(0.36, 0.24, 0.13)):
    """Oiled, weathered wood from the scanned plank texture (Session E's props.scan_surface, read-only use)."""
    from lib import props
    return props.scan_surface(name, 'brown_planks_04', color, tile=0.5, rough=(0.5, 0.85), normal=0.8, age=(0.2, 0.35))


def _painted(name, color):
    """Painted wood (limbers were painted olive / grey; Egyptian chariots were covered in coloured leather / gilded)."""
    from lib import props
    return props.scan_surface(name, 'brown_planks_04', color, tile=0.5, rough=(0.45, 0.7), normal=0.35, age=(0.25, 0.3))


def _leather(name='harness_leather', color=(0.10, 0.055, 0.03)):
    from lib import props
    return props.leather(name, color)


def _iron():
    return bpy.data.materials.get('harness_iron') or principled('harness_iron', (0.06, 0.055, 0.05), metal=0.85, rough=0.55,
                                                                bump=0.2, bump_scale=200)


def _bronze():
    return bpy.data.materials.get('bronze') or aged_bronze('bronze')


def _gold():
    return bpy.data.materials.get('harness_gold') or principled('harness_gold', (0.85, 0.62, 0.27), metal=1.0, rough=0.28)


# ------------------------------------------------------------------ small mesh helpers
def _root(name, loc=(0, 0, 0), heading_deg=0.0):
    r = link(bpy.data.objects.new(name, None))
    r.location = loc; r.rotation_euler = (0, 0, math.radians(heading_deg))
    r['wheels'] = []
    return r


def _box(name, c, size, mat, parent, rot=(0, 0, 0)):
    """Bevelled box (centre c, full size), size baked into the mesh so textures keep real scale."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(mat)
    b = o.modifiers.new('bevel', 'BEVEL'); b.width = min(0.006, 0.4 * min(size)); b.segments = 2
    o.location = c; o.rotation_euler = rot; o.parent = parent
    return o


def _tube(name, pts, r, mat, parent, seg=12, r_end=None):
    """Round bar through a list of points (poles, rails, axles). r_end tapers it."""
    pts = [Vector(p) for p in pts]
    verts, faces = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        d = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = d.orthogonal().normalized(); b = d.cross(a)
        rr = r if r_end is None else r + (r_end - r) * i / (n - 1)
        for k in range(seg):
            t = 2 * math.pi * k / seg
            verts.append(tuple(p + (a * math.cos(t) + b * math.sin(t)) * rr))
    for i in range(n - 1):
        for k in range(seg):
            a0 = i * seg + k; a1 = i * seg + (k + 1) % seg
            faces.append((a0, a1, a1 + seg, a0 + seg))
    faces.append(tuple(range(seg))[::-1]); faces.append(tuple(range((n - 1) * seg, n * seg)))
    o = mesh_obj(name, verts, faces, mat); o.parent = parent
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _ring(name, radius, tube_r, mat, parent, seg=64, tube_seg=8, sx=1.0):
    """A torus (felloe / tyre / rail ring) lying in the YZ plane (a wheel's plane when the axle is along X)."""
    verts, faces = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        c = Vector((0, math.cos(a) * radius, math.sin(a) * radius))
        out = Vector((0, math.cos(a), math.sin(a)))
        for j in range(tube_seg):
            b = 2 * math.pi * j / tube_seg
            v = c + out * math.cos(b) * tube_r + Vector((1, 0, 0)) * math.sin(b) * tube_r * sx
            verts.append(tuple(v))
    for i in range(seg):
        for j in range(tube_seg):
            a = i * tube_seg + j; b = i * tube_seg + (j + 1) % tube_seg
            c = ((i + 1) % seg) * tube_seg + (j + 1) % tube_seg; d = ((i + 1) % seg) * tube_seg + j
            faces.append((a, b, c, d))
    o = mesh_obj(name, verts, faces, mat); o.parent = parent
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _lathe_x(name, profile, mat, parent, seg=32):
    """Solid of revolution around the X axis (a hub). profile = [(radius, x), ...]."""
    verts, faces = [], []
    for (r, x) in profile:
        for k in range(seg):
            t = 2 * math.pi * k / seg
            verts.append((x, math.cos(t) * r, math.sin(t) * r))
    n = len(profile)
    for i in range(n - 1):
        for k in range(seg):
            a = i * seg + k; b = i * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    faces.append(tuple(range(seg))[::-1]); faces.append(tuple(range((n - 1) * seg, n * seg)))
    o = mesh_obj(name, verts, faces, mat); o.parent = parent
    for p in o.data.polygons:
        p.use_smooth = True
    return o


# ------------------------------------------------------------------ the wheel
def wheel(name, radius=0.48, spokes=6, width=0.06, wood=None, tyre=None, studs=0, hub_len=0.32, dish=0.0,
          parent=None, loc=(0, 0, 0), spoke_r=None):
    """A spoked wheel standing in the YZ plane, axle along X, centre at `loc` (local to parent).
    tyre  = material of the rim band (rawhide for Bronze Age chariots, iron for Roman -> modern, bronze studs for
            the Persian royal chariot); studs = number of nail heads round the tyre (0 = none).
    dish  = how far the rim sits outboard of the hub (m) - real cart wheels are dished, an old wheelwright trick
            that keeps them from collapsing when the cart sways. Returns the wheel's root empty (spin it about X)."""
    wood = wood or _wood()
    tyre = tyre or _iron()
    w = link(bpy.data.objects.new(name, None)); w.parent = parent; w.location = loc
    w['wheel_r'] = radius
    felloe_r = radius - width * 0.45
    fw = max(0.022, radius * 0.06)                                   # felloe (rim) thickness
    _ring(name + '_felloe', felloe_r - fw * 0.5, fw * 0.6, wood, w, seg=72, tube_seg=8, sx=width / (fw * 1.2))
    _ring(name + '_tyre', radius - 0.008, 0.012, tyre, w, seg=96, tube_seg=6, sx=width / 0.026)
    # hub (nave): fat in the middle where the spokes are mortised, narrower at the ends
    hr = max(0.045, radius * 0.13)
    _lathe_x(name + '_hub', [(0.001, -hub_len / 2), (hr * 0.55, -hub_len / 2), (hr * 0.8, -hub_len * 0.3), (hr, -0.02),
                             (hr, 0.02), (hr * 0.8, hub_len * 0.3), (hr * 0.55, hub_len / 2), (0.001, hub_len / 2)], wood, w)
    sr = spoke_r or max(0.012, radius * 0.032)
    for k in range(spokes):
        a = 2 * math.pi * (k + 0.5) / spokes
        d = Vector((0, math.cos(a), math.sin(a)))
        p0 = d * hr * 0.9; p1 = d * (felloe_r - fw) + Vector((dish, 0, 0))
        _tube(f'{name}_spoke{k}', [p0, (p0 + p1) / 2, p1], sr, wood, w, seg=8, r_end=sr * 0.8)
    if studs:
        stud_m = tyre
        bm = bmesh.new()
        for k in range(studs):
            a = 2 * math.pi * k / studs
            c = Vector((0, math.cos(a) * (radius + 0.004), math.sin(a) * (radius + 0.004)))
            r = bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.012)
            bmesh.ops.translate(bm, vec=c, verts=r['verts'])
        me = bpy.data.meshes.new(name + '_studs'); bm.to_mesh(me); bm.free()
        s = link(bpy.data.objects.new(name + '_studs', me)); s.data.materials.append(stud_m); s.parent = w
    return w


def _add_wheel(root, w):
    root['wheels'] = list(root['wheels']) + [w.name]
    root['wheel_r'] = w['wheel_r']


# ------------------------------------------------------------------ yokes
def yoke_pair(name, parent, loc, span=1.1, kind='ox', mat=None):
    """A wooden yoke across two animals' necks at `loc` (local; centre between the animals).
    kind='ox'     : a heavy NECK yoke beam with bows (U-shaped wooden bows round each neck), the Greek/Roman ox yoke
    kind='saddle' : a light chariot yoke with Y-shaped YOKE SADDLES that sit on each horse's withers (Bronze Age)"""
    mat = mat or _wood(name + '_wood', (0.33, 0.22, 0.12))
    y = link(bpy.data.objects.new(name, None)); y.parent = parent; y.location = loc
    half = span / 2 + 0.25
    # the beam: thicker in the middle, ends curl up slightly (Egyptian yokes end in finials)
    _tube(name + '_beam', [(-half, 0, 0.04), (-span / 2, 0, 0.0), (0, 0, -0.02), (span / 2, 0, 0.0), (half, 0, 0.04)],
          0.045 if kind == 'ox' else 0.03, mat, y, seg=10)
    for sx in (-1, 1):
        cx = sx * span / 2
        if kind == 'ox':                                            # bow round the neck: U under the throat
            pts = [(cx + 0.17 * math.cos(math.radians(a)), 0.0, -0.22 + 0.22 * math.sin(math.radians(a)) * -1)
                   for a in range(0, 181, 20)]
            pts = [(cx - 0.17, 0, 0), (cx - 0.18, 0, -0.18), (cx - 0.1, 0, -0.33), (cx, 0, -0.36), (cx + 0.1, 0, -0.33),
                   (cx + 0.18, 0, -0.18), (cx + 0.17, 0, 0)]
            _tube(f'{name}_bow{sx}', pts, 0.02, mat, y, seg=8)
        else:                                                       # yoke saddle: stem down + two legs over the shoulders
            stem_top = Vector((cx, 0, -0.01)); fork = Vector((cx, 0, -0.14))
            _tube(f'{name}_stem{sx}', [stem_top, fork], 0.022, mat, y, seg=8)
            for lx in (-1, 1):
                _tube(f'{name}_leg{sx}{lx}', [fork, fork + Vector((lx * 0.12, 0.03, -0.12)), fork + Vector((lx * 0.2, 0.05, -0.3))],
                      0.016, mat, y, seg=8, r_end=0.012)
    return y


# ------------------------------------------------------------------ chariots
def chariot_egypt(loc=(0, 0, 0), heading_deg=0.0, name='chariot_egypt', royal=False, seed=0):
    """New Kingdom two-horse war chariot. The car sits IN FRONT of the axle (axle at the floor's back edge), so the
    crew's weight rests partly on the pole and the horses - that's why it was fast and stable at speed."""
    r = _root(name, loc, heading_deg)
    wood = _wood(name + '_wood', (0.42, 0.28, 0.15))
    hide = _leather(name + '_hide', (0.32, 0.17, 0.07))            # rawhide tyres + leather-covered siding
    cover = _painted(name + '_cover', (0.55, 0.12, 0.06) if not royal else (0.85, 0.62, 0.27))
    R = 0.46                                                       # wheel radius (Tut A1: ~0.92 m diameter)
    track = 0.87                                                   # half the axle width (axle ~1.74 m between wheels)
    axle_z = R
    _tube(name + '_axle', [(-track - 0.14, 0, axle_z), (track + 0.14, 0, axle_z)], 0.035, wood, r)
    for sx in (-1, 1):
        w = wheel(f'{name}_wheel{sx}', R, spokes=6, width=0.055, wood=wood, tyre=hide, hub_len=0.36, parent=r,
                  loc=(sx * track, 0, axle_z))
        _add_wheel(r, w)
    # floor: D-shaped (straight back over the axle, rounded front), a frame of bent wood + leather webbing
    fz = axle_z + 0.04
    depth, half_w = 0.52, 0.5
    ring = []
    for k in range(25):                                           # D outline: back edge straight on the axle line
        a = math.pi * k / 24
        ring.append(Vector((math.cos(a) * half_w, -math.sin(a) * depth, fz)))
    _tube(name + '_floorframe', ring + [ring[0]], 0.022, wood, r, seg=8)
    floor = mesh_obj(name + '_floor', [tuple(p + Vector((0, 0, -0.005))) for p in ring], [tuple(range(len(ring)))], hide)
    floor.parent = r
    floor.modifiers.new('t', 'SOLIDIFY').thickness = 0.015
    # siding: a top rail ~0.75 m above the floor at the front, sloping down towards the open back
    rail = []
    for k in range(25):
        a = math.pi * k / 24
        h = 0.32 + 0.43 * math.sin(a)                              # front highest, sides lower toward the back
        rail.append(Vector((math.cos(a) * (half_w - 0.02), -math.sin(a) * (depth - 0.02), fz + h)))
    _tube(name + '_rail', rail, 0.016, wood, r, seg=8)
    for k in (3, 7, 12, 17, 21):                                   # uprights
        _tube(f'{name}_post{k}', [ring[k] + Vector((0, 0, 0.0)), rail[k]], 0.013, wood, r, seg=6)
    # leather side screens (filled panels) between floor and rail, front and sides; a band of coloured appliqué
    verts, faces = [], []
    for k in range(2, 23):
        verts += [tuple(ring[k] + Vector((0, 0, 0.01))), tuple(rail[k] - Vector((0, 0, 0.02)))]
    for i in range(len(verts) // 2 - 1):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    scr = mesh_obj(name + '_screen', verts, faces, cover); scr.parent = r
    scr.modifiers.new('t', 'SOLIDIFY').thickness = 0.006
    # pole: from under the back of the floor, along the floor, then sweeping up to the yoke ~2.6 m forward
    yoke_y, yoke_z = -2.75, 1.08
    pole = [(0, 0.12, fz - 0.05), (0, -0.3, fz - 0.06), (0, -0.9, fz - 0.03), (0, -1.6, fz + 0.12),
            (0, -2.2, yoke_z - 0.12), (0, yoke_y, yoke_z)]
    _tube(name + '_pole', pole, 0.035, wood, r, seg=10, r_end=0.028)
    yoke_pair(name + '_yoke', r, (0, yoke_y, yoke_z + 0.02), span=0.95, kind='saddle')
    # bow case + quiver strapped diagonally on the right side (Kadesh reliefs)
    case = _box(name + '_bowcase', (half_w + 0.03, -0.25, fz + 0.45), (0.05, 0.22, 0.95), cover, r,
                rot=(math.radians(-38), 0, 0))
    qv = _box(name + '_quiver', (-(half_w + 0.03), -0.2, fz + 0.4), (0.07, 0.12, 0.7), hide, r, rot=(math.radians(-30), 0, 0))
    if royal:
        for o in (case,):
            o.data.materials[0] = _gold()
    r['hitch'] = (0, yoke_y, yoke_z)
    r['team'] = 2
    r['floor_z'] = fz
    r['crew_marks'] = [(0.18, -0.25, fz), (-0.18, -0.22, fz)]        # driver (left), archer (right)
    return r


def chariot_persia(loc=(0, 0, 0), heading_deg=0.0, name='chariot_persia', royal=True, seed=0):
    """Achaemenid chariot (Persepolis / Oxus model): bigger 12-spoke wheels with STUDDED tyres, a box car with a
    high front panel and open back, axle at the rear; four horses abreast for the king (two for others)."""
    r = _root(name, loc, heading_deg)
    wood = _wood(name + '_wood', (0.34, 0.22, 0.12))
    paint = _painted(name + '_paint', (0.12, 0.17, 0.33) if royal else (0.42, 0.2, 0.08))   # blue + gold royal car
    gold = _gold() if royal else _bronze()
    R = 0.58
    track = 0.86
    axle_z = R
    _tube(name + '_axle', [(-track - 0.16, 0, axle_z), (track + 0.16, 0, axle_z)], 0.04, wood, r)
    for sx in (-1, 1):
        w = wheel(f'{name}_wheel{sx}', R, spokes=12, width=0.07, wood=wood, tyre=_bronze(), studs=40, hub_len=0.42,
                  parent=r, loc=(sx * track, 0, axle_z))
        _add_wheel(r, w)
    fz = axle_z + 0.06
    W, D = 1.0, 0.75
    _box(name + '_floor', (0, -D / 2 + 0.08, fz), (W, D, 0.05), wood, r)
    _box(name + '_front', (0, -D + 0.1, fz + 0.5), (W, 0.05, 1.0), paint, r)                   # high front panel
    for sx in (-1, 1):
        _box(f'{name}_side{sx}', (sx * W / 2, -D / 2 + 0.08, fz + 0.32), (0.05, D, 0.62), paint, r)
    _tube(name + '_toprail', [(-W / 2, 0.1, fz + 0.64), (-W / 2, -D + 0.1, fz + 1.0), (W / 2, -D + 0.1, fz + 1.0),
                              (W / 2, 0.1, fz + 0.64)], 0.02, gold, r, seg=8)
    # gold border lines on the front panel + a rosette roundel (Persepolis rosettes)
    for z in (fz + 0.1, fz + 0.9):
        _box(f'{name}_trim{int(z * 100)}', (0, -D + 0.07, z), (W, 0.012, 0.035), gold, r)
    ros = _ring(name + '_rosette', 0.13, 0.018, gold, r, seg=36, tube_seg=6)
    ros.rotation_euler.z = math.pi / 2; ros.location = (0, -D + 0.065, fz + 0.5)
    yoke_y, yoke_z = -3.05, 1.12
    _tube(name + '_pole', [(0, 0.1, fz - 0.06), (0, -D, fz - 0.05), (0, -1.6, fz + 0.05), (0, -2.4, yoke_z - 0.12),
                           (0, yoke_y, yoke_z)], 0.04, wood, r, seg=10)
    _tube(name + '_polecap', [(0, yoke_y - 0.02, yoke_z), (0, yoke_y - 0.14, yoke_z + 0.03)], 0.045, gold, r, seg=10)
    yoke_pair(name + '_yoke', r, (0, yoke_y + 0.05, yoke_z + 0.02), span=1.0, kind='saddle')
    r['hitch'] = (0, yoke_y, yoke_z)
    r['team'] = 4 if royal else 2
    r['floor_z'] = fz
    r['crew_marks'] = [(0.2, -0.35, fz), (-0.2, -0.35, fz)]
    return r


# ------------------------------------------------------------------ wagon
def wagon(loc=(0, 0, 0), heading_deg=0.0, name='wagon', load='sacks', cover=False, seed=0, era='medieval'):
    """Four-wheeled wagon: small front wheels on the turning fore-carriage, bigger back wheels, slatted sloping
    sides, a pole for a pair (horses / oxen / mules). load: 'sacks' | 'hay' | 'barrels' | None; cover = canvas tilt
    on hoops (baggage trains, 17th-19th c.)."""
    rnd = random.Random(seed)
    r = _root(name, loc, heading_deg)
    wood = _wood(name + '_wood', (0.38, 0.26, 0.14))
    Rf, Rb = 0.42, 0.6
    L = 3.3
    yf, yb = -L / 2 + 0.35, L / 2 - 0.35
    for (y, R, nm) in ((yf, Rf, 'f'), (yb, Rb, 'b')):
        _tube(f'{name}_axle{nm}', [(-0.95, y, R), (0.95, y, R)], 0.045, wood, r)
        for sx in (-1, 1):
            w = wheel(f'{name}_wheel{nm}{sx}', R, spokes=10 if nm == 'f' else 12, width=0.07, wood=wood, tyre=_iron(),
                      hub_len=0.36, parent=r, loc=(sx * 0.82, y, R), dish=0.03)
            _add_wheel(r, w)
    bz = Rb + 0.12
    _box(name + '_bed', (0, 0, bz), (1.15, L, 0.06), wood, r)
    _tube(name + '_reach', [(0, yf, Rf + 0.05), (0, yb, Rb - 0.02)], 0.05, wood, r)       # perch joining the axles
    for sx in (-1, 1):                                              # sloping slatted sides
        for k in range(3):
            z = bz + 0.15 + k * 0.17
            _box(f'{name}_slat{sx}{k}', (sx * (0.6 + k * 0.06), 0, z), (0.03, L + k * 0.1, 0.07), wood, r)
        for y in (-L / 2 + 0.1, -L / 4, 0, L / 4, L / 2 - 0.1):
            _box(f'{name}_stake{sx}{int(y * 10)}', (sx * 0.66, y, bz + 0.3), (0.04, 0.05, 0.6), wood, r,
                 rot=(0, math.radians(sx * 14), 0))
    _box(name + '_tail', (0, L / 2, bz + 0.25), (1.2, 0.04, 0.45), wood, r)
    _tube(name + '_pole', [(0, yf, Rf + 0.02), (0, yf - 1.2, 0.75), (0, yf - 3.0, 0.9)], 0.045, wood, r, r_end=0.035)
    if load == 'sacks':
        try:
            from lib import market                                       # Session D's grain sacks (read-only use)
            for i in range(8):
                market.grain_sack(Vector(((i % 2 - 0.5) * 0.5, (i // 2 - 1.5) * 0.7, bz + 0.04)), parent=r, seed=seed + i,
                                  name=f'{name}_sack{i}')
        except Exception as e:
            print('wagon: sacks unavailable -', e)
    elif load == 'hay':
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * 0.85, v.co.y * L * 0.55, max(-0.05, v.co.z) * 0.9 + 0.1))
        me = bpy.data.meshes.new(name + '_hay'); bm.to_mesh(me); bm.free()
        h = link(bpy.data.objects.new(name + '_hay', me))
        h.data.materials.append(principled('hay_load', (0.55, 0.43, 0.2), rough=0.95, bump=1.0, bump_scale=220))
        h.parent = r; h.location = (0, 0, bz)
    elif load == 'barrels':
        for i in range(6):
            b = _lathe_x(f'{name}_barrel{i}', [(0.001, -0.38), (0.22, -0.38), (0.27, -0.15), (0.28, 0), (0.27, 0.15),
                                               (0.22, 0.38), (0.001, 0.38)], wood, r)
            b.rotation_euler.z = math.pi / 2
            b.location = ((i % 2 - 0.5) * 0.56, (i // 2 - 1) * 0.85, bz + 0.31)
    if cover:
        canvas = principled(name + '_canvas', (0.62, 0.57, 0.46), rough=0.95, bump=0.3, bump_scale=300)
        verts, faces = [], []
        n_arc, n_len = 14, 6
        for i in range(n_len + 1):
            y = -L / 2 + 0.1 + (L - 0.2) * i / n_len
            sag = 0.05 * (i % 2)                                      # canvas sags between the hoops
            for j in range(n_arc + 1):
                a = math.pi * j / n_arc
                verts.append((math.cos(a) * 0.75, y, bz + 0.65 + math.sin(a) * (0.85 - sag)))
        for i in range(n_len):
            for j in range(n_arc):
                a = i * (n_arc + 1) + j
                faces.append((a, a + 1, a + n_arc + 2, a + n_arc + 1))
        c = mesh_obj(name + '_tilt', verts, faces, canvas); c.parent = r
        c.modifiers.new('t', 'SOLIDIFY').thickness = 0.01
        for p in c.data.polygons:
            p.use_smooth = True
    r['hitch'] = (0, yf - 3.0, 0.9)
    r['team'] = 2
    return r


# ------------------------------------------------------------------ Napoleonic limber
def limber(loc=(0, 0, 0), heading_deg=0.0, name='limber', color=(0.27, 0.3, 0.2)):
    """Two-wheeled artillery limber: axle, a short frame (hounds) carrying the AMMUNITION CHEST, a pole for the
    wheel pair, and the PINTLE hook at the back (root['pintle'] = local point where the gun's trail eye sits).
    Colour: French artillery olive-green (vert olive), British grey / blue-grey - pass color=(0.33, 0.35, 0.38)."""
    r = _root(name, loc, heading_deg)
    wood = _wood(name + '_wood', (0.36, 0.24, 0.13))
    paint = _painted(name + '_paint', color)
    R = 0.68                                                         # 1.37 m wheels, same as the gun's
    _box(name + '_axletree', (0, 0, R), (1.45, 0.14, 0.13), paint, r)
    for sx in (-1, 1):
        w = wheel(f'{name}_wheel{sx}', R, spokes=12, width=0.075, wood=paint, tyre=_iron(), hub_len=0.4, parent=r,
                  loc=(sx * 0.78, 0, R), dish=0.035)
        _add_wheel(r, w)
    for sx in (-1, 1):                                              # the hounds: two beams fore and aft
        _box(f'{name}_hound{sx}', (sx * 0.3, -0.2, R + 0.12), (0.09, 1.7, 0.1), paint, r)
    _box(name + '_bolster', (0, 0, R + 0.2), (1.3, 0.12, 0.08), paint, r)
    # ammunition chest (coffret) with a lid and handles; gunners sat on it on the march
    _box(name + '_chest', (0, 0.05, R + 0.45), (1.2, 0.62, 0.48), paint, r)
    _box(name + '_lid', (0, 0.05, R + 0.71), (1.24, 0.66, 0.05), paint, r)
    for sx in (-1, 1):
        _tube(f'{name}_handle{sx}', [(sx * 0.63, -0.05, R + 0.52), (sx * 0.66, 0.05, R + 0.55), (sx * 0.63, 0.15, R + 0.52)],
              0.008, _iron(), r, seg=6)
    for sx in (-1, 1):
        _box(f'{name}_strap{sx}', (sx * 0.35, 0.05, R + 0.47), (0.04, 0.66, 0.52), _iron(), r)
    # pole forward to the wheel pair + a swingle-tree bar for their traces
    _tube(name + '_pole', [(0, -0.9, R + 0.1), (0, -2.0, R + 0.18), (0, -3.6, R + 0.25)], 0.045, wood, r, r_end=0.035)
    _tube(name + '_splinter', [(-0.75, -1.05, R + 0.12), (0.75, -1.05, R + 0.12)], 0.035, paint, r)
    # pintle: a hook on the rear cross-bar
    _box(name + '_rearbar', (0, 0.62, R + 0.1), (0.7, 0.1, 0.09), paint, r)
    _tube(name + '_pintle', [(0, 0.66, R + 0.08), (0, 0.76, R + 0.08), (0, 0.78, R + 0.16)], 0.02, _iron(), r, seg=8)
    r['pintle'] = (0, 0.74, R + 0.12)
    r['hitch'] = (0, -3.6, R + 0.25)
    r['team'] = 6
    return r


def limber_gun(limber_root, gun_root, trail_len=None):
    """Hook a cannon.build('field') gun behind the limber for travel: the gun turns round (muzzle pointing BACK,
    away from the team), its trail end rests on the pintle, so the gun tips up around its axle.
    The gun is parented to the limber (it follows) but keeps its own wheels for roll(). Returns the gun root."""
    bpy.context.view_layer.update()
    pin_local = Vector(limber_root['pintle'])
    gun_axle_h = 0.72                                                 # cannon.py field gun: axle 0.72 m up
    # the field gun's trail end in its own frame: trail box from cannon.build (centre x=-1.5, length 2.6, sloped)
    trail_len = trail_len or 2.75
    rise = pin_local.z - 0.05                                         # trail end lifted from the ground to the pintle
    drop = gun_axle_h - rise                                          # how far the trail end is below the axle
    horiz = math.sqrt(max(trail_len ** 2 - drop ** 2, 0.1))
    # resting angle on the ground: trail end on ground, axle at 0.72 -> angle a0; on the pintle -> a1
    a0 = math.asin(min(1.0, gun_axle_h / trail_len)); a1 = math.asin(max(-1.0, min(1.0, drop / trail_len)))
    pitch = a0 - a1                                                   # tip the gun forward (trail up) by this much
    gun_root.parent = limber_root
    gun_root.matrix_parent_inverse = Matrix.Identity(4)
    # muzzle points +X at gun heading 0; we want the muzzle BACK (+Y in limber frame) and the trail forward (-Y)
    gun_root.rotation_euler = (0, 0, math.radians(90))
    gun_root.location = (0, pin_local.y + horiz, 0)
    # tip around the axle: rotate about the gun's local Y axis (its axle line) through axle height. Put the tilt on
    # a child pivot so the gun's own origin math stays simple.
    pivot = link(bpy.data.objects.new(gun_root.name + '_tilt', None))
    pivot.parent = limber_root
    pivot.location = (0, pin_local.y + horiz, gun_axle_h)
    gun_root.parent = pivot
    gun_root.location = (0, 0, -gun_axle_h)
    pivot.rotation_euler = (-pitch, 0, 0)                             # trail (-Y side) goes up
    limber_root['gun'] = gun_root.name
    return gun_root


# ------------------------------------------------------------------ pack saddle + panniers
def panniers(back_point, girth_z, side_x, name='panniers', parent=None, load='produce', seed=0, length=0.55):
    """A wooden pack saddle on a felt pad across the back at `back_point` (world, the top of the back over the
    middle of the body), with a wicker basket hanging on each side (their outside at +-side_x from the spine,
    bottoms ~girth_z), roped under the belly. load: 'produce' | 'amphorae' | 'firewood' | None.
    Pass parent = the bone-following empty to make it move with the animal. Returns the root empty."""
    from lib import props
    rnd = random.Random(seed)
    root = link(bpy.data.objects.new(name, None)); root.location = back_point
    wood = _wood(name + '_wood', (0.32, 0.21, 0.11))
    felt = principled(name + '_felt', (0.3, 0.22, 0.15), rough=0.98, bump=0.4, bump_scale=200)
    wick = props.wicker(name + '_wicker')
    rope = props.rope_fibre(name + '_rope')
    top = 0.0
    # the pad: a curved slab over the spine
    verts, faces = [], []
    n = 12
    for i in range(2):
        y = (i - 0.5) * length
        for j in range(n + 1):
            a = math.radians(-70 + 140 * j / n)
            verts.append((math.sin(a) * side_x * 0.9, y, top - (1 - math.cos(a)) * 0.22))
    for j in range(n):
        faces.append((j, j + 1, n + 2 + j, n + 1 + j))
    pad = mesh_obj(name + '_pad', verts, faces, felt); pad.parent = root
    pad.modifiers.new('t', 'SOLIDIFY').thickness = 0.03
    # saddle frame: two crossed-stick arches (sawbuck), front and back
    for y in (-length * 0.38, length * 0.38):
        for sx in (-1, 1):
            _tube(f'{name}_buck{sx}{int(y * 100)}', [(sx * side_x * 0.85, y, -0.16), (0, y, 0.12)], 0.022, wood, root, seg=6)
    _tube(name + '_ridge', [(0, -length * 0.45, 0.1), (0, length * 0.45, 0.1)], 0.02, wood, root, seg=6)
    depth = max(0.22, -girth_z * 0.55)                 # baskets reach about half way down the ribs
    for sx in (-1, 1):
        cx = sx * (side_x + 0.11)
        # basket: an open-topped tapered wicker tub, hanging from the frame on ropes
        bm = bmesh.new()
        r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=20, radius1=0.12, radius2=0.16, depth=depth)
        top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
        bmesh.ops.delete(bm, geom=[top_face], context='FACES_ONLY')
        for v in bm.verts:
            v.co.y *= length / 0.36
        me = bpy.data.meshes.new(f'{name}_basket{sx}'); bm.to_mesh(me); bm.free()
        b = link(bpy.data.objects.new(f'{name}_basket{sx}', me)); b.data.materials.append(wick); b.parent = root
        b.location = (cx, 0, -0.06 - depth / 2)
        b.rotation_euler.y = math.radians(-sx * 6)                     # hangs slightly in against the belly
        b.modifiers.new('t', 'SOLIDIFY').thickness = 0.012
        for y in (-0.15, 0.15):
            _tube(f'{name}_hang{sx}{y}', [(sx * side_x * 0.85, y * length / 0.36, -0.15), (cx, y * length / 0.36, -0.13)],
                  0.008, rope, root, seg=6)
        # the load inside: domed heap of produce / stacked sticks / a jar neck
        if load == 'produce':
            # a heap of separate vegetables (onions, cabbages, gourds, leeks) - never one smooth blob
            kinds = [((0.55, 0.32, 0.12), 0.035, 1.0), ((0.28, 0.4, 0.12), 0.06, 0.85), ((0.62, 0.48, 0.18), 0.05, 1.25),
                     ((0.42, 0.12, 0.14), 0.03, 1.0)]
            mats = [principled(f'{name}_veg{k}', c, rough=0.55, bump=0.35, bump_scale=90) for k, (c, _, _) in enumerate(kinds)]
            wy = 0.16 * length / 0.36
            for k in range(26):
                ci = rnd.randrange(len(kinds)); col, rad, elong = kinds[ci]
                rad *= rnd.uniform(0.8, 1.2)
                bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=rad)
                for v in bm.verts:
                    v.co.z *= elong; v.co += v.co.normalized() * rnd.uniform(-0.12, 0.12) * rad * 0.5
                me = bpy.data.meshes.new(f'{name}_veg{sx}_{k}'); bm.to_mesh(me); bm.free()
                ob = link(bpy.data.objects.new(f'{name}_veg{sx}_{k}', me)); ob.data.materials.append(mats[ci])
                for pl in ob.data.polygons:
                    pl.use_smooth = True
                rr = 0.13 * math.sqrt(rnd.random()); aa = rnd.uniform(0, 2 * math.pi)
                hx, hy = math.cos(aa) * rr, math.sin(aa) * rr * wy / 0.13
                dome = 0.06 * (1 - (rr / 0.14) ** 2)
                ob.parent = root; ob.location = (cx + hx, hy, -0.07 + dome + rad * 0.4)
                ob.rotation_euler = (rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0, 6.3))
        elif load == 'firewood':
            for k in range(7):
                y0 = rnd.uniform(-0.1, 0.1)
                _tube(f'{name}_stick{sx}{k}', [(cx + rnd.uniform(-0.1, 0.1), -length * 0.6 + y0, -0.12 + rnd.uniform(0, 0.12)),
                                                (cx + rnd.uniform(-0.1, 0.1), length * 0.6 + y0, -0.1 + rnd.uniform(0, 0.12))],
                      rnd.uniform(0.018, 0.03), wood, root, seg=6)
        elif load == 'amphorae':
            try:
                a = props.amphora((0, 0, 0), height=0.5, seed=seed + sx, name=f'{name}_amph{sx}')
                a.parent = root; a.location = (cx, 0, -0.12 - depth + 0.05)
            except Exception as e:
                print('panniers: amphora unavailable -', e)
    # girth rope under the belly
    _tube(name + '_girth', [(-side_x * 0.85, 0, -0.15), (-side_x * 0.95, 0, girth_z * 0.6), (0, 0, girth_z),
                            (side_x * 0.95, 0, girth_z * 0.6), (side_x * 0.85, 0, -0.15)], 0.01, rope, root, seg=6)
    if parent is not None:
        bpy.context.view_layer.update()                  # matrix_world is only recomputed on update
        w = Matrix.Translation(Vector(back_point)); root.parent = parent; root.matrix_world = w
    return root


# ------------------------------------------------------------------ rolling wheels
def roll(root, frames, path_len=None):
    """Spin every wheel of `root` so it ROLLS with the vehicle's travel between frames[0] and frames[1]
    (angle = distance / radius). path_len = distance travelled; default: measured from root's own location keys."""
    sc = bpy.context.scene
    f0, f1 = frames
    if path_len is None:
        sc.frame_set(f0); p0 = root.matrix_world.translation.copy()
        sc.frame_set(f1); p1 = root.matrix_world.translation.copy()
        path_len = (p1 - p0).length
    for wn in root.get('wheels', []):
        w = bpy.data.objects.get(wn)
        if w is None:
            continue
        rr = w.get('wheel_r', 0.5)
        ang = path_len / rr
        w.rotation_euler.x = 0.0; w.keyframe_insert('rotation_euler', index=0, frame=f0)
        w.rotation_euler.x = -ang; w.keyframe_insert('rotation_euler', index=0, frame=f1)   # forward = -Y -> spin -X
        ad = w.animation_data
        if ad and ad.action and hasattr(ad.action, 'fcurves'):
            for fc in ad.action.fcurves:
                for k in fc.keyframe_points:
                    k.interpolation = 'LINEAR'
    gun = root.get('gun')
    if gun and bpy.data.objects.get(gun):
        roll(bpy.data.objects[gun], frames, path_len)
