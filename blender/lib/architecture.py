# GREEK ARCHITECTURE KIT (Archaic / early Classical, c. 500-450 BC), built by code from the real rules of the Doric
# order (Vitruvius IV; measured temples: Aphaia at Aegina c. 500 BC, the Old Temple of Athena, Zeus at Olympia c. 460).
# Everything is measured in the column's lower diameter D ("module"), the way Greek builders worked:
#   column height ~ 5.5 D, 20 shallow flutes, entasis (a slight swell, max ~1/3 up), capital = echinus cushion + abacus
#   architrave (plain beam) ~ 0.75 D, frieze ~ 0.75 D with triglyphs over every column + between, metopes between
#   cornice, low pediment (slope ~ 12-15 deg), stylobate on a 3-step crepidoma
# Temples were PAINTED (traces survive on the Aphaia sculptures, the Peplos Kore...): triglyphs dark blue/black,
# regulae + mutules blue, taenia + cornice mouldings red, metope backgrounds red or plain marble, pediment field blue.
# Columns and walls: marble or limestone stucco left pale. Never copied from other productions: design from sources.
import math

import bpy
import numpy as np
from mathutils import Vector

from lib.common import link, mesh_obj, principled

PAINT = {
    'blue': (0.025, 0.06, 0.22), 'red': (0.42, 0.05, 0.03), 'ochre': (0.55, 0.36, 0.1), 'black': (0.02, 0.02, 0.025),
    'green': (0.04, 0.16, 0.07), 'gold': (0.6, 0.42, 0.12),
}


def stone(name='temple_marble', scan='marble_01', tint=(1.0, 0.97, 0.9), tiles=1.5):
    """Weathered marble from the Poly Haven scan (falls back to a code material if the scan is missing)."""
    try:
        from lib import scatter
        return scatter.scan_material(name, scan, tint=tint, tiles=tiles, rough=(0.45, 0.8))
    except Exception:
        return principled(name, (0.78, 0.74, 0.66), rough=0.6, bump=0.25, bump_scale=40)


def paint(name, color, rough=0.75):
    """Matte mineral paint (ochre, Egyptian blue, cinnabar...) slightly worn."""
    m = principled(name, color, rough=rough, bump=0.1, bump_scale=60)
    return m


def column(loc, D=1.0, H=None, flutes=20, segs=48, rows=40, entasis=0.018, taper=0.78, mat=None, name='column'):
    """One Doric column shaft with flutes and entasis + capital. Returns the shaft object (capital parented)."""
    H = H or 5.5 * D
    shaft_h = H - 0.45 * D                                    # capital ~0.45 D
    verts, faces = [], []
    for j in range(rows + 1):
        t = j / rows
        # taper from D (bottom) to taper*D (top), plus the entasis swell (max near t = 0.35)
        r = 0.5 * D * (1 - (1 - taper) * t) + entasis * D * math.sin(math.pi * min(t / 0.7, 1.0))
        for i in range(segs):
            a = 2 * math.pi * i / segs
            # Doric flutes: shallow concave scallops meeting at sharp arrises (no flat fillets)
            k = (i * flutes / segs) % 1.0
            rr = r * (1 - 0.035 * math.sin(math.pi * k))
            verts.append((rr * math.cos(a), rr * math.sin(a), t * shaft_h))
    for j in range(rows):
        for i in range(segs):
            a, b = j * segs + i, j * segs + (i + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    shaft = mesh_obj(name, verts, faces, mat)
    shaft.location = loc
    for p in shaft.data.polygons:
        p.use_smooth = True
    # capital: echinus (a flaring cushion) + square abacus
    top_r = 0.5 * D * taper
    prof = [(0.0, top_r), (0.05 * D, top_r * 1.02), (0.12 * D, top_r * 1.18), (0.2 * D, top_r * 1.42), (0.24 * D, top_r * 1.5)]
    cv, cf = [], []
    for z, r in prof:
        for i in range(segs):
            a = 2 * math.pi * i / segs
            cv.append((r * math.cos(a), r * math.sin(a), shaft_h + z))
    for j in range(len(prof) - 1):
        for i in range(segs):
            a, b = j * segs + i, j * segs + (i + 1) % segs
            cf.append((a, b, b + segs, a + segs))
    bpy.context.view_layer.update()                           # shaft.matrix_world must be current before parenting
    ech = mesh_obj(name + '_echinus', cv, cf, mat); ech.location = loc; ech.parent = shaft
    ech.matrix_parent_inverse = shaft.matrix_world.inverted()
    for p in ech.data.polygons:
        p.use_smooth = True
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], loc[2] + shaft_h + 0.24 * D + 0.1 * D))
    ab = bpy.context.object; ab.name = name + '_abacus'; ab.scale = (1.15 * D, 1.15 * D, 0.2 * D)   # square slab ~1.15 D
    ab.data.materials.append(mat)
    bpy.context.view_layer.update()
    ab.parent = shaft; ab.matrix_parent_inverse = shaft.matrix_world.inverted()        # moves with its column
    return shaft


def _box(name, center, size, mat, bevel=None):      # bevel accepted for call compatibility (unused)
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object; o.name = name; o.scale = size
    bv = o.modifiers.new('bevel', 'BEVEL'); bv.width = min(size) * 0.04; bv.segments = 2
    o.data.materials.append(mat)
    return o


def temple(loc=(0, 0, 0), columns_front=6, columns_side=13, D=1.6, heading_deg=0.0, painted=True, name='temple'):
    """A Doric peripteral temple (hexastyle like Aphaia / Zeus at Olympia). Returns the root empty.
    D = lower column diameter in metres (Aphaia ~1.0, Zeus at Olympia ~2.2)."""
    root = bpy.data.objects.new(name, None); link(root)
    marble = stone()
    blue, red, black = (paint(f'{name}_{c}', PAINT[c]) for c in ('blue', 'red', 'black'))
    tiles = principled(f'{name}_roof_tiles', (0.32, 0.12, 0.06), rough=0.85, bump=0.5, bump_scale=6)
    H = 5.5 * D
    axial = 2.4 * D                                            # column spacing (centre to centre), ~2.4 D
    W = (columns_front - 1) * axial; L = (columns_side - 1) * axial
    parts = []
    # crepidoma: 3 steps, then the stylobate the columns stand on
    step_h = 0.33 * D
    for k in range(3):
        grow = (3 - k) * 0.45 * D
        parts.append(_box(f'{name}_step{k}', (0, 0, step_h * (k + 0.5)), (W + 2 * D + grow, L + 2 * D + grow, step_h), marble))
    base_z = 3 * step_h
    # peristyle columns
    for i in range(columns_front):
        for j in range(columns_side):
            if 0 < i < columns_front - 1 and 0 < j < columns_side - 1:
                continue                                       # only the outer ring
            x, y = -W / 2 + i * axial, -L / 2 + j * axial
            parts.append(column((x, y, base_z), D=D, H=H, mat=marble, name=f'{name}_col_{i}_{j}'))
    # cella (inner walls) behind the columns
    parts.append(_box(f'{name}_cella', (0, 0.1 * L, base_z + H * 0.48), (W - 2.2 * axial, L - 3.2 * axial, H * 0.96), marble))
    # entablature: architrave + taenia (red) + frieze (triglyphs blue/black, metopes red) + cornice
    z = base_z + H
    arch_h = 0.75 * D
    parts.append(_box(f'{name}_architrave', (0, 0, z + arch_h / 2), (W + D * 1.1, L + D * 1.1, arch_h), marble))
    z += arch_h
    parts.append(_box(f'{name}_taenia', (0, 0, z + 0.04 * D), (W + D * 1.14, L + D * 1.14, 0.08 * D), red if painted else marble))
    z += 0.08 * D
    fr_h = 0.75 * D
    parts.append(_box(f'{name}_frieze', (0, 0, z + fr_h / 2), (W + D * 1.08, L + D * 1.08, fr_h), red if painted else marble))
    # triglyphs: over every column and over every gap, on all four sides
    tw = 0.5 * D
    for side in range(4):
        n = (columns_front if side % 2 == 0 else columns_side) * 2 - 1
        span = W if side % 2 == 0 else L
        for k in range(n):
            u = -span / 2 + k * (span / (n - 1))
            if side == 0:   c, s = (u, -(L + D * 1.1) / 2, z + fr_h / 2), (tw, 0.12 * D, fr_h)
            elif side == 2: c, s = (u, (L + D * 1.1) / 2, z + fr_h / 2), (tw, 0.12 * D, fr_h)
            elif side == 1: c, s = ((W + D * 1.1) / 2, u, z + fr_h / 2), (0.12 * D, tw, fr_h)
            else:           c, s = (-(W + D * 1.1) / 2, u, z + fr_h / 2), (0.12 * D, tw, fr_h)
            parts.append(_box(f'{name}_triglyph_{side}_{k}', c, s, black if painted else marble))
    z += fr_h
    corn_h = 0.35 * D
    parts.append(_box(f'{name}_cornice', (0, 0, z + corn_h / 2), (W + D * 1.5, L + D * 1.5, corn_h), blue if painted else marble))
    z += corn_h
    # pediments (front + back): low triangle, blue field; roof planes covered in marble tiles
    slope = math.radians(13)
    rise = (W + D * 1.5) / 2 * math.tan(slope)
    hw = (W + D * 1.5) / 2
    for sgn in (-1, 1):
        y = sgn * (L + D * 1.5) / 2
        v = [(-hw, y, z), (hw, y, z), (0, y, z + rise)]
        parts.append(mesh_obj(f'{name}_pediment_{sgn}', v, [(0, 1, 2)], blue if painted else marble))
    for sgn in (-1, 1):
        v = [(0, -(L + D * 1.6) / 2, z + rise), (0, (L + D * 1.6) / 2, z + rise),
             (sgn * (hw + 0.2 * D), (L + D * 1.6) / 2, z - 0.05 * D), (sgn * (hw + 0.2 * D), -(L + D * 1.6) / 2, z - 0.05 * D)]
        roof = mesh_obj(f'{name}_roof_{sgn}', v, [(0, 1, 2, 3)], tiles)      # rough fired-clay roof tiles
        roof.modifiers.new('thick', 'SOLIDIFY').thickness = 0.15 * D
        parts.append(roof)
    for p in parts:
        if p.parent is None:
            p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def house(loc, w=8.0, d=10.0, h=3.2, heading_deg=0.0, seed=0, name='house'):
    """Athenian house c. 480 BC: mud-brick walls on a rubble-stone socle, lime-plastered, a terracotta-tiled pitched
    roof (low slope), small high windows, a plain wooden door to the street (houses faced inward to a courtyard)."""
    rng = np.random.default_rng(seed)
    root = bpy.data.objects.new(name, None); link(root)
    try:
        from lib import scatter
        plaster = scatter.scan_material(f'{name}_plaster', 'plastered_wall_02', tint=(rng.uniform(0.7, 0.9), rng.uniform(0.58, 0.75), rng.uniform(0.42, 0.58)), tiles=2.0)   # sun-faded ochre / clay lime wash
        socle_m = scatter.scan_material(f'{name}_socle', 'rock_boulder_dry', tint=(0.8, 0.76, 0.7), tiles=1.0)
    except Exception:
        plaster = principled(f'{name}_plaster', (0.75, 0.68, 0.56), rough=0.9, bump=0.2)
        socle_m = principled(f'{name}_socle', (0.45, 0.42, 0.38), rough=0.9, bump=0.4)
    tiles = principled(f'{name}_tiles', (0.28, 0.09, 0.04), rough=0.75, bump=0.4, bump_scale=8)
    wood = principled(f'{name}_door', (0.18, 0.11, 0.06), rough=0.8, bump=0.3, bump_scale=30)
    parts = [_box(f'{name}_socle', (0, 0, 0.3), (w, d, 0.6), socle_m), _box(f'{name}_walls', (0, 0, 0.6 + h / 2), (w * 0.98, d * 0.98, h), plaster)]
    rise = w / 2 * math.tan(math.radians(16))
    z = 0.6 + h
    for sgn in (-1, 1):
        v = [(0, -d / 2 - 0.3, z + rise), (0, d / 2 + 0.3, z + rise), (sgn * (w / 2 + 0.35), d / 2 + 0.3, z - 0.1), (sgn * (w / 2 + 0.35), -d / 2 - 0.3, z - 0.1)]
        r = mesh_obj(f'{name}_roof_{sgn}', v, [(0, 1, 2, 3)], tiles); r.modifiers.new('thick', 'SOLIDIFY').thickness = 0.12
        parts.append(r)
    for sgn in (-1, 1):
        parts.append(mesh_obj(f'{name}_gable_{sgn}', [(-w / 2 * 0.98, sgn * d / 2 * 0.98, z), (w / 2 * 0.98, sgn * d / 2 * 0.98, z), (0, sgn * d / 2 * 0.98, z + rise)], [(0, 1, 2)], plaster))
    parts.append(_box(f'{name}_door', (rng.uniform(-w / 4, w / 4), -d / 2 * 0.99, 0.6 + 1.0), (1.1, 0.12, 2.0), wood))
    for p in parts:
        p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def persian_column(loc, h=12.0, r=0.38, mat=None, cap_mat=None, name='pcol'):
    """Persepolis-style column: bell-shaped base, slender fluted shaft (~40 shallow flutes), DOUBLE-BULL capital
    (two kneeling bull foreparts back to back, holding the beams) - simplified into readable masses."""
    root = bpy.data.objects.new(name, None); link(root)
    parts = []
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r * 2.0, radius2=r * 1.1, depth=0.9, location=(0, 0, 0.45))
    b = bpy.context.object; b.data.materials.append(mat); parts.append(b)                  # bell base
    shaft = column((0, 0, 0.9), D=2 * r, H=h - 2.6, flutes=40, segs=80, entasis=0.0, taper=0.92, mat=mat, name=name + '_shaft')
    parts.append(shaft)
    z = 0.9 + h - 2.6 - 0.2
    for sgn in (-1, 1):                                                                      # the two bull foreparts
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.55, location=(sgn * 0.75, 0, z + 1.1))
        body = bpy.context.object; body.scale = (1.5, 0.7, 0.75); body.data.materials.append(cap_mat or mat); parts.append(body)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.28, location=(sgn * 1.55, 0, z + 1.45))
        head = bpy.context.object; head.scale = (1.2, 0.8, 0.9); head.data.materials.append(cap_mat or mat); parts.append(head)
    _box_ = _box(name + '_saddle', (0, 0, z + 1.75), (1.2, 0.9, 0.35), cap_mat or mat); parts.append(_box_)
    for p in parts:
        if p.parent is None:
            p.parent = root
    root.location = loc
    return root


def palace_hall(loc=(0, 0, 0), cols=(6, 6), spacing=8.5, height=14.0, name='apadana'):
    """A Persian audience hall (after the Apadana of Persepolis, built under Darius and Xerxes): a forest of tall
    columns under a flat cedar-beam roof, thick mud-brick walls, high window openings that let in SHAFTS of sunlight
    (the volume haze makes them visible). Polished stone floor. Returns (root, floor_object)."""
    root = bpy.data.objects.new(name, None); link(root)
    try:
        from lib import scatter
        stone = scatter.scan_material(f'{name}_stone', 'old_sandstone_02', tint=(0.62, 0.6, 0.58), tiles=2.0)
        floor_m = scatter.scan_material(f'{name}_floor', 'marble_01', tint=(0.35, 0.33, 0.32), tiles=3.0, rough=(0.15, 0.4))
    except Exception:
        stone = principled(f'{name}_stone', (0.4, 0.38, 0.35), rough=0.7)
        floor_m = principled(f'{name}_floor', (0.2, 0.19, 0.18), rough=0.25)
    cedar = principled(f'{name}_cedar', (0.16, 0.08, 0.04), rough=0.7, bump=0.3, bump_scale=40)
    wall_m = principled(f'{name}_wall', (0.42, 0.33, 0.25), rough=0.9, bump=0.3, bump_scale=10)
    gold_m = principled(f'{name}_gilt', (0.7, 0.52, 0.22), metal=1.0, rough=0.35)
    W, D = (cols[0] + 1) * spacing, (cols[1] + 1) * spacing
    parts = []
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); fl = bpy.context.object; fl.name = f'{name}_floor'
    fl.scale = (W, D, 1); fl.data.materials.append(floor_m); parts.append(fl)
    for i in range(cols[0]):
        for j in range(cols[1]):
            x = -W / 2 + spacing * (i + 1); y = -D / 2 + spacing * (j + 1)
            parts.append(persian_column((x, y, 0), h=height, mat=stone, cap_mat=stone, name=f'{name}_c{i}{j}'))
    # roof beams + ceiling
    for j in range(cols[1]):
        y = -D / 2 + spacing * (j + 1)
        parts.append(_box(f'{name}_beam{j}', (0, y, height + 0.35), (W, 0.7, 0.7), cedar))
    parts.append(_box(f'{name}_ceiling', (0, 0, height + 0.95), (W, D, 0.5), cedar))
    # walls with high windows (gaps) on the sun side (+X): light shafts slant down into the hall
    t = 3.0
    parts.append(_box(f'{name}_wall_w', (-W / 2 - t / 2, 0, height / 2), (t, D, height + 1.2), wall_m))
    parts.append(_box(f'{name}_wall_n', (0, D / 2 + t / 2, height / 2), (W + 2 * t, t, height + 1.2), wall_m))
    parts.append(_box(f'{name}_wall_s', (0, -D / 2 - t / 2, height / 2), (W + 2 * t, t, height + 1.2), wall_m))
    n_win = cols[1] + 1
    for k in range(n_win + 1):                                   # east wall = piers between window gaps
        y = -D / 2 + k * D / n_win
        parts.append(_box(f'{name}_pier{k}', (W / 2 + t / 2, y, height / 2), (t, D / n_win * 0.55, height + 1.2), wall_m))
    parts.append(_box(f'{name}_lintel', (W / 2 + t / 2, 0, height * 0.82), (t, D, height * 0.4), wall_m))
    parts.append(_box(f'{name}_sill', (W / 2 + t / 2, 0, height * 0.28), (t, D, height * 0.56), wall_m))
    # the king's dais at the far end (-X) with a gilded edge
    parts.append(_box(f'{name}_dais', (-W / 2 + 4.0, 0, 0.45), (6.0, 9.0, 0.9), stone))
    parts.append(_box(f'{name}_dais_trim', (-W / 2 + 7.02, 0, 0.88), (0.06, 9.0, 0.06), gold_m))
    for p in parts:
        if p.parent is None:
            p.parent = root
    root.location = loc
    return root, fl


def courtyard_house(loc=(0, 0, 0), w=14.0, d=12.0, h=3.4, seed=0, name='oikos'):
    """Inside an Athenian house c. 480 BC (excavated houses of the Athenian agora area, Olynthus plans): an open
    courtyard (aule) of beaten earth with a cobbled patch, plastered rooms all round, a PORTICO (pastas) of wooden posts
    along the north side, the household altar of Zeus Herkeios, a well-head, storage amphorae, a bench, a tree.
    Origin = courtyard centre; doorways lead into dark rooms (good for moody light)."""
    rng = np.random.default_rng(seed)
    root = bpy.data.objects.new(name, None); link(root)
    try:
        from lib import scatter
        plaster = scatter.scan_material(f'{name}_plaster', 'plastered_wall_02', tint=(0.82, 0.72, 0.58), tiles=2.0)
        earth = scatter.scan_material(f'{name}_earth', 'brown_mud_dry', tint=(0.95, 0.85, 0.72), tiles=2.5)
        stonem = scatter.scan_material(f'{name}_stone', 'rock_boulder_dry', tint=(0.75, 0.7, 0.62), tiles=1.0)
    except Exception:
        plaster = principled(f'{name}_plaster', (0.7, 0.6, 0.48), rough=0.9)
        earth = principled(f'{name}_earth', (0.42, 0.34, 0.25), rough=0.95)
        stonem = principled(f'{name}_stone', (0.5, 0.47, 0.42), rough=0.9)
    wood = principled(f'{name}_wood', (0.22, 0.13, 0.07), rough=0.75, bump=0.3, bump_scale=30)
    tiles = principled(f'{name}_tiles', (0.28, 0.09, 0.04), rough=0.75, bump=0.4, bump_scale=8)
    dark = principled(f'{name}_doorway', (0.01, 0.008, 0.006), rough=1.0)
    parts = [_box(f'{name}_ground', (0, 0, -0.05), (w + 8, d + 8, 0.1), earth)]
    t = 0.45
    for (x, y, sw, sd) in ((0, d / 2 + t / 2, w + 2 * t, t), (0, -d / 2 - t / 2, w + 2 * t, t), (w / 2 + t / 2, 0, t, d), (-w / 2 - t / 2, 0, t, d)):
        parts.append(_box(f'{name}_wall_{x}_{y}', (x, y, h / 2), (sw, sd, h), plaster))
    for k, x in enumerate((-4.0, 0.5, 4.5)):                     # doorways into the rooms (dark openings)
        parts.append(_box(f'{name}_door{k}', (x, d / 2 - 0.02, 1.0), (1.0, 0.06, 2.0), dark, 0))
    parts.append(_box(f'{name}_door_s', (-w / 2 + 0.02, -2.0, 1.0), (0.06, 1.0, 2.0), dark, 0))
    for k in range(6):                                            # the portico: wooden posts + a tiled lean-to roof
        x = -w / 2 + 1.2 + k * (w - 2.4) / 5
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.11, depth=h - 0.3, location=(x, d / 2 - 2.6, (h - 0.3) / 2))
        po = bpy.context.object; po.data.materials.append(wood); parts.append(po)
    roof = mesh_obj(f'{name}_portico_roof', [(-w / 2, d / 2, h), (w / 2, d / 2, h), (w / 2, d / 2 - 3.0, h - 0.6), (-w / 2, d / 2 - 3.0, h - 0.6)],
                    [(0, 1, 2, 3)], tiles)
    roof.modifiers.new('thick', 'SOLIDIFY').thickness = 0.12; parts.append(roof)
    parts.append(_box(f'{name}_altar', (2.5, -1.5, 0.45), (0.8, 0.8, 0.9), stonem))            # Zeus Herkeios
    parts.append(_box(f'{name}_altar_top', (2.5, -1.5, 0.93), (0.95, 0.95, 0.08), stonem))
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.55, depth=0.7, location=(-3.0, -2.5, 0.35))
    well = bpy.context.object; well.data.materials.append(stonem); parts.append(well)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.42, depth=0.72, location=(-3.0, -2.5, 0.36))
    hole = bpy.context.object; hole.data.materials.append(dark); parts.append(hole)
    parts.append(_box(f'{name}_bench', (w / 2 - 1.0, -1.0, 0.25), (0.5, 3.0, 0.5), stonem))
    for p in parts:
        if p.parent is None:
            p.parent = root
    try:
        from lib import props as P
        for k, (x, y) in enumerate([(-w / 2 + 0.8, d / 2 - 0.8), (-w / 2 + 1.5, d / 2 - 0.7), (w / 2 - 0.8, d / 2 - 0.9)]):
            P.amphora((loc[0] + x, loc[1] + y, loc[2]), seed=k + 20)
        from lib import scatter
        tree = scatter.load_scan('island_tree_02', 1)[0]
        inst = bpy.data.objects.new(f'{name}_tree', None); inst.instance_type = 'COLLECTION'; inst.instance_collection = tree
        inst.location = (loc[0] - 4.5, loc[1] + 1.5, loc[2]); inst.scale = (0.8, 0.8, 0.8); link(inst)
    except Exception as e:
        print('courtyard extras skipped:', e)
    root.location = loc
    return root


# ------------------------------------------------------------------ Egypt, New Kingdom (c. 1250 BC, Ramesses II)
EGYPT_PAINT = {'blue': (0.03, 0.12, 0.3), 'red': (0.4, 0.07, 0.03), 'yellow': (0.6, 0.42, 0.1), 'green': (0.06, 0.22, 0.12),
               'white': (0.75, 0.72, 0.62), 'black': (0.02, 0.02, 0.02)}


def _battered(name, base_w, base_d, top_w, top_d, h, mat):
    """A tower with SLOPED (battered) walls, the defining shape of Egyptian pylons and mud-brick walls."""
    v = [(-base_w / 2, -base_d / 2, 0), (base_w / 2, -base_d / 2, 0), (base_w / 2, base_d / 2, 0), (-base_w / 2, base_d / 2, 0),
         (-top_w / 2, -top_d / 2, h), (top_w / 2, -top_d / 2, h), (top_w / 2, top_d / 2, h), (-top_w / 2, top_d / 2, h)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)]
    return mesh_obj(name, v, f, mat)


def egypt_pylon(loc=(0, 0, 0), w=40.0, h=22.0, d=8.0, heading_deg=0.0, name='pylon'):
    """Temple PYLON gateway (Luxor, Karnak, Ramesseum): two battered towers with a painted relief band and a cavetto
    cornice, a tall gateway between them, flagpole niches, a pair of granite obelisks with gilded tips in front."""
    root = bpy.data.objects.new(name, None); link(root)
    try:
        from lib import scatter
        sand = scatter.scan_material(f'{name}_sandstone', 'old_sandstone_02', tint=(1.0, 0.86, 0.66), tiles=2.0)
        granite = scatter.scan_material(f'{name}_granite', 'rock_boulder_dry', tint=(0.55, 0.32, 0.28), tiles=0.8)
    except Exception:
        sand = principled(f'{name}_sandstone', (0.7, 0.55, 0.36), rough=0.85)
        granite = principled(f'{name}_granite', (0.4, 0.22, 0.18), rough=0.5)
    paint = {k: principled(f'{name}_{k}', c, rough=0.8) for k, c in EGYPT_PAINT.items()}
    gold = principled(f'{name}_gold', (0.83, 0.62, 0.26), metal=1.0, rough=0.3)
    parts = []
    tw = (w - 6.0) / 2
    for sgn in (-1, 1):
        x = sgn * (3.0 + tw / 2)
        t = _battered(f'{name}_tower_{sgn}', tw, d, tw * 0.86, d * 0.8, h, sand); t.location = (x, 0, 0); parts.append(t)
        band = _box(f'{name}_relief_{sgn}', (x, -d * 0.43, h * 0.55), (tw * 0.82, 0.05, h * 0.5), paint['white'], 0)
        parts.append(band)                                       # the painted relief field (pharaoh smiting enemies)
        for k, col in enumerate(('blue', 'red', 'yellow', 'green')):
            parts.append(_box(f'{name}_frieze_{sgn}_{k}', (x, -d * 0.44, h * 0.82 + k * 0.35), (tw * 0.8, 0.06, 0.3), paint[col], 0))
        parts.append(_box(f'{name}_cornice_{sgn}', (x, 0, h + 0.5), (tw * 0.9, d * 0.86, 1.0), sand))
        for k in range(2):                                       # flagpoles of cedar in their niches
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.25, depth=h * 1.35, location=(x + (k - 0.5) * tw * 0.4, -d * 0.48, h * 0.67))
            fp = bpy.context.object; fp.data.materials.append(principled(f'{name}_cedar', (0.25, 0.15, 0.08), rough=0.7)); parts.append(fp)
    parts.append(_box(f'{name}_gate', (0, 0, h * 0.38), (6.0, d * 0.7, h * 0.76), sand))
    parts.append(_box(f'{name}_door', (0, -d * 0.36, h * 0.3), (3.6, 0.1, h * 0.6), principled(f'{name}_doorway', (0.02, 0.015, 0.01), rough=1.0), 0))
    for sgn in (-1, 1):                                          # granite obelisks with gilded pyramidions
        ob = _battered(f'{name}_obelisk_{sgn}', 2.4, 2.4, 1.6, 1.6, 24.0, granite); ob.location = (sgn * 8.0, -d - 8.0, 0); parts.append(ob)
        tip = mesh_obj(f'{name}_pyramidion_{sgn}', [(-0.8, -0.8, 0), (0.8, -0.8, 0), (0.8, 0.8, 0), (-0.8, 0.8, 0), (0, 0, 1.6)],
                       [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)], gold)
        tip.location = (sgn * 8.0, -d - 8.0, 24.0); parts.append(tip)
    for p in parts:
        if p.parent is None:
            p.parent = root
    root.location = loc; root.rotation_euler.z = math.radians(heading_deg)
    return root


def papyrus_column(loc, h=10.0, r=1.0, mat=None, paint=None, name='papyrus'):
    """Closed-bud papyrus column: a bundle of stems (the shaft is lobed), binding bands painted in colour, a swelling
    bud capital and a square abacus."""
    root = bpy.data.objects.new(name, None); link(root)
    shaft = column((0, 0, 0), D=2 * r, H=h * 0.85, flutes=8, segs=64, entasis=0.0, taper=0.82, mat=mat, name=name + '_shaft')
    shaft.parent = root
    for k in range(5):                                           # the binding bands under the capital
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r * 0.84, depth=0.12, location=(0, 0, h * 0.72 + k * 0.14))
        b = bpy.context.object; b.data.materials.append(paint or mat); b.parent = root
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=16, radius=r * 1.05, location=(0, 0, h * 0.88))
    bud = bpy.context.object; bud.scale = (1.0, 1.0, 1.15); bud.data.materials.append(mat); bud.parent = root
    root.location = loc
    return root
