# WARDROBE: era clothing made the way real cloth behaves: CLOTH SIMULATION.
# A garment starts as a simple sheet/tube around the body in its rest A-pose, a few points are pinned
# (shoulder brooches, belt), then the body moves into its final pose while the fabric falls, drapes and folds.
#   chiton   : Greek tunic (linen), pinned along the shoulders, belted at the waist
#   himation : large wool mantle draped over the left shoulder (statesmen, philosophers, gods)
# Era references (design source, not copied art): Classical Greek vase painting and sculpture, c. 500-450 BC.
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib.common import link


BONE_ALIASES = {}          # e.g. {'upperarm01.L': 'LeftArm', ...} for motion-capture (cmu_mb) skeletons


def body_measure(human, rig, pos):
    """Key heights/sizes at rest pose (world space). pos = rest positions from cast.rest_surface()."""
    B = lambda n: rig.matrix_world @ rig.data.bones[BONE_ALIASES.get(n, n) if BONE_ALIASES.get(n, n) in rig.data.bones else n].head_local
    shoulder = (B('upperarm01.L') + B('upperarm01.R')) / 2
    hip = (B('upperleg01.L') + B('upperleg01.R')) / 2
    knee_z = (B('lowerleg01.L').z + B('lowerleg01.R').z) / 2
    neck = B('neck01')
    waist_z = hip.z + 0.17
    band = (np.abs(pos[:, 2] - waist_z) < 0.02) & (np.abs(pos[:, 0]) < 0.2)
    waist_rx = np.abs(pos[band][:, 0]).max(); waist_ry = np.abs(pos[band][:, 1] - pos[band][:, 1].mean()).max()
    cy = pos[band][:, 1].mean()
    return {"shoulder_z": shoulder.z, "shoulder_x": abs(B('upperarm01.L').x), "neck": neck, "hip_z": hip.z,
            "knee_z": knee_z, "waist_z": waist_z, "waist_rx": waist_rx, "waist_ry": waist_ry, "cy": cy}


def shoulder_top(pos, x, cy, max_z=None):
    """Height of the body's top surface at a given x over the shoulder line, ignoring the head/neck above
    max_z (otherwise points near the centre would find the top of the head)."""
    sel = (np.abs(pos[:, 0] - x) < 0.015) & (np.abs(pos[:, 1] - cy) < 0.07)
    if max_z is not None:
        sel &= pos[:, 2] < max_z
    return pos[sel][:, 2].max() if sel.any() else None


def surface_y(pos, x, z, front=True):
    """Front (min y) or back (max y) body surface at a given x and height."""
    sel = (np.abs(pos[:, 0] - x) < 0.015) & (np.abs(pos[:, 2] - z) < 0.015)
    if not sel.any():
        return None
    return pos[sel][:, 1].min() if front else pos[sel][:, 1].max()


def set_uv(obj, uvs):
    """uvs: one (u, v) per vertex. Lets materials paint border bands along a garment's edges."""
    me = obj.data
    layer = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            layer.data[li].uv = uvs[me.loops[li].vertex_index]


def border_material(name, cloth, band, v_from=None, v_to=None, edge=0.0, width=0.04):
    """Fabric with a coloured woven border band: along the hem (v near v_from/v_to) or all edges (edge mode)."""
    from lib.common import fabric
    m = fabric(name, cloth)
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    uv = nt.nodes.new('ShaderNodeUVMap'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs[0])
    # distance to the band edge(s) in UV space -> 1 inside the band
    if edge:
        mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'
        a = nt.nodes.new('ShaderNodeMath'); a.operation = 'PINGPONG'; a.inputs[1].default_value = 0.5
        bb = nt.nodes.new('ShaderNodeMath'); bb.operation = 'PINGPONG'; bb.inputs[1].default_value = 0.5
        L(sep.outputs['X'], a.inputs[0]); L(sep.outputs['Y'], bb.inputs[0]); L(a.outputs[0], mn.inputs[0]); L(bb.outputs[0], mn.inputs[1])
        d = mn.outputs[0]
    else:
        d = sep.outputs['Y']
    lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = width
    L(d, lt.inputs[0])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    mix.inputs['A'].default_value = (*cloth, 1); mix.inputs['B'].default_value = (*band, 1)
    L(lt.outputs[0], mix.inputs['Factor']); L(mix.outputs['Result'], b.inputs['Base Color'])
    return m


def scan_cloth(name, scan, dye, band=None, tiles=(6.0, 5.0), edge=0.0, width=0.04, grime=0.35, sheen=0.5):
    """Garment material from a REAL scanned fabric (Poly Haven CC0, e.g. 'rough_linen', 'caban', 'hessian_230'):
    the weave's own colour detail, normal map and roughness, re-dyed to an era-correct colour (`dye`, linear RGB),
    an optional woven border `band`, grime toward the hem (v = 0) and the soft sheen of fibres at grazing angles.
    `tiles` = how many times the scan repeats across the garment's UV (garments are ~1-2 m, scans ~0.2-0.3 m)."""
    import os
    from lib.common import SCANS
    d = os.path.join(SCANS, scan)
    def img(suffix, color=True):
        f = next((x for x in os.listdir(d) if f'_{suffix}_' in x), None)
        if f is None:
            return None
        im = bpy.data.images.load(os.path.join(d, f), check_existing=True)
        if not color:
            im.colorspace_settings.name = 'Non-Color'
        return im
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new
    b = nt.nodes['Principled BSDF']
    uv = nt.nodes.new('ShaderNodeUVMap')
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (tiles[0], tiles[1], 1)
    L(uv.outputs['UV'], mp.inputs['Vector'])
    def tex(image):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = image; L(mp.outputs['Vector'], t.inputs['Vector']); return t
    diff = tex(img('diff'))
    # re-dye: keep the weave's light/dark detail, replace its colour
    bw = nt.nodes.new('ShaderNodeRGBToBW'); L(diff.outputs['Color'], bw.inputs['Color'])
    lift = nt.nodes.new('ShaderNodeMapRange'); lift.inputs['To Min'].default_value = 0.55; lift.inputs['To Max'].default_value = 1.25
    L(bw.outputs['Val'], lift.inputs['Value'])
    dyed = nt.nodes.new('ShaderNodeMix'); dyed.data_type = 'RGBA'; dyed.blend_type = 'MULTIPLY'; dyed.inputs['Factor'].default_value = 1.0
    L(lift.outputs['Result'], dyed.inputs['A'])
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs[0])
    if band is not None:                                         # woven border band: hem (v near 0) or all edges
        if edge:
            mn = nt.nodes.new('ShaderNodeMath'); mn.operation = 'MINIMUM'
            a = nt.nodes.new('ShaderNodeMath'); a.operation = 'PINGPONG'; a.inputs[1].default_value = 0.5
            bb = nt.nodes.new('ShaderNodeMath'); bb.operation = 'PINGPONG'; bb.inputs[1].default_value = 0.5
            L(sep.outputs['X'], a.inputs[0]); L(sep.outputs['Y'], bb.inputs[0]); L(a.outputs[0], mn.inputs[0]); L(bb.outputs[0], mn.inputs[1])
            dist = mn.outputs[0]
        else:
            dist = sep.outputs['Y']
        lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = width
        L(dist, lt.inputs[0])
        col = nt.nodes.new('ShaderNodeMix'); col.data_type = 'RGBA'
        col.inputs['A'].default_value = (*dye, 1); col.inputs['B'].default_value = (*band, 1)
        L(lt.outputs[0], col.inputs['Factor']); L(col.outputs['Result'], dyed.inputs['B'])
    else:
        dyed.inputs['B'].default_value = (*dye, 1)
    # grime: dust and wear darken the cloth toward the hem, broken up by noise
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 9.0
    L(uv.outputs['UV'], noise.inputs['Vector'])
    g = nt.nodes.new('ShaderNodeMapRange'); g.inputs['From Min'].default_value = 0.0; g.inputs['From Max'].default_value = 0.35
    g.inputs['To Min'].default_value = grime; g.inputs['To Max'].default_value = 0.0
    L(sep.outputs['Y'], g.inputs['Value'])
    gn = nt.nodes.new('ShaderNodeMath'); gn.operation = 'MULTIPLY'; L(g.outputs['Result'], gn.inputs[0]); L(noise.outputs['Fac'], gn.inputs[1])
    dirt = nt.nodes.new('ShaderNodeMix'); dirt.data_type = 'RGBA'; dirt.blend_type = 'MULTIPLY'
    dirt.inputs['B'].default_value = (0.45, 0.38, 0.3, 1)
    L(gn.outputs[0], dirt.inputs['Factor']); L(dyed.outputs['Result'], dirt.inputs['A'])
    L(dirt.outputs['Result'], b.inputs['Base Color'])
    rough = img('rough', False)
    if rough:                                                        # fibres are matte: keep the scan's variation
        rr = nt.nodes.new('ShaderNodeMapRange'); rr.inputs['To Min'].default_value = 0.72; rr.inputs['To Max'].default_value = 0.95
        L(tex(rough).outputs['Color'], rr.inputs['Value']); L(rr.outputs['Result'], b.inputs['Roughness'])
    else:
        b.inputs['Roughness'].default_value = 0.85
    nor = img('nor_gl', False)
    if nor:
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.2
        L(tex(nor).outputs['Color'], nm.inputs['Color']); L(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Sheen Weight'].default_value = sheen; b.inputs['Sheen Roughness'].default_value = 0.5
    b.inputs['Specular IOR Level'].default_value = 0.3
    return m


def add_collision(human):
    """The body pushes cloth away. Placed after the armature so it collides with the POSED body."""
    if not any(m.type == 'COLLISION' for m in human.modifiers):
        c = human.modifiers.new('collision', 'COLLISION')
        human.collision.thickness_outer = 0.006
        human.collision.cloth_friction = 8.0


def bind_to_skeleton(garment, human, rig):
    """Make a garment FOLLOW the skeleton: copy the body's bone weights onto it (nearest surface), then add an
    Armature modifier. Placed BEFORE the cloth modifier, so pinned points (shoulder seams, belt) ride on the
    bones while the free fabric is simulated: walking, turning and gestures move the clothes naturally."""
    bpy.context.view_layer.objects.active = garment
    dt = garment.modifiers.new('weights', 'DATA_TRANSFER')
    dt.object = human; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    with bpy.context.temp_override(object=garment, active_object=garment, selected_objects=[garment]):
        bpy.ops.object.datalayout_transfer(modifier=dt.name)          # create the bone groups on the garment
        bpy.ops.object.modifier_apply(modifier=dt.name)
    arm = garment.modifiers.new('skeleton', 'ARMATURE'); arm.object = rig
    # also ride along when the whole skeleton object moves (walking forward, being carried)
    garment.parent = rig; garment.matrix_parent_inverse = rig.matrix_world.inverted()
    return arm


def _cloth(obj, pin_group, mass=0.15, tension=12, bending=0.6, shrink=0.0, self_collide=False):
    m = obj.modifiers.new('cloth', 'CLOTH')
    s = m.settings
    s.quality = 7; s.mass = mass
    s.tension_stiffness = tension; s.compression_stiffness = tension; s.shear_stiffness = 6
    s.bending_stiffness = bending; s.air_damping = 1.5
    s.vertex_group_mass = pin_group
    s.shrink_min = shrink
    cs = m.collision_settings
    cs.distance_min = 0.004; cs.use_self_collision = self_collide
    if self_collide:
        cs.self_distance_min = 0.003
    m.point_cache.frame_start = 1; m.point_cache.frame_end = 60
    return m


def chiton(human, rig, pos, material, length='knee', follow=False):
    """Tube of linen from the shoulders down, pinned on the shoulder seams and at the belt."""
    M = body_measure(human, rig, pos)
    top_z = M['shoulder_z'] + 0.02
    bottom_z = (M['knee_z'] + 0.06) if length == 'knee' else 0.07                # 'ankle' = long robe (kings, priests, older men)
    # a real Ionic chiton is a WIDE rectangle (about arm span) sewn into a tube: the belt gathers the excess linen
    # into many vertical folds and it falls over the upper arms like sleeves
    rx, ry, cy = max(M['shoulder_x'] + 0.12, 0.31), 0.21, M['cy']
    seg, ring_h = 144, 0.014
    rings = int((top_z - bottom_z) / ring_h) + 1
    verts, faces, pin = [], [], []
    belt_ring = int((top_z - M['waist_z']) / ring_h)
    for r in range(rings):
        z = top_z - r * ring_h
        for k in range(seg):
            a = 2 * math.pi * k / seg
            x, y = rx * math.cos(a), cy + ry * math.sin(a)
            w = 0.0
            if r == 0 and 0.07 <= abs(x) < M['shoulder_x'] + 0.02:     # shoulder seam: front + back meet on top
                st = shoulder_top(pos, x, cy, M['shoulder_z'] + 0.085)
                if st is not None:
                    y, z = cy + 0.25 * (y - cy), st + 0.006
                    w = 1.0
            elif r == 0 and abs(x) < 0.07:                              # neckline: lies on the collarbones / upper back
                nz = M['shoulder_z'] - (0.035 if y < cy else 0.0)
                sy = surface_y(pos, x, nz, front=y < cy)
                if sy is not None:                                      # SOFT pin: the neckline can sag into a
                    y, z = sy + (-0.006 if y < cy else 0.006), nz         # curve but the tunic stays on the shoulders
                    w = 0.35
            if r == belt_ring:                                          # the belt pulls the tunic to the waist
                x, y = (M['waist_rx'] + 0.012) * math.cos(a), cy + (M['waist_ry'] + 0.012) * math.sin(a)
                z = M['waist_z']; w = 1.0
            verts.append((x, y, z)); pin.append(w)
    for r in range(rings - 1):
        for k in range(seg):
            a, b = r * seg + k, r * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    me = bpy.data.meshes.new('chiton'); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new('chiton', me)); o.data.materials.append(material)
    set_uv(o, [((i % seg) / seg, 1 - (i // seg) / (rings - 1)) for i in range(len(verts))])   # v = 0 at the hem
    vg = o.vertex_groups.new(name='pin')
    for i, w in enumerate(pin):
        if w:
            vg.add([i], w, 'REPLACE')
    if follow:
        bind_to_skeleton(o, human, rig)                                # before the cloth: pins follow the bones
    cm = _cloth(o, 'pin', mass=0.09, tension=10, bending=0.08)        # thin linen: many small folds
    cm.settings.quality = 10
    o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.0025
    o.modifiers.new('smooth', 'SUBSURF').levels = 1
    return o


def himation(human, rig, pos, material, side='L', over=None, follow=False):
    """A large wool mantle over one shoulder: a sheet whose middle strip lies on the shoulder, front and back
    halves hanging free so they fall and fold over the chest, arm and back."""
    M = body_measure(human, rig, pos)
    # drape over the frozen tunic if there is one: its surface is the "skin" the mantle starts on
    under = pos
    if over is not None:
        dg = bpy.context.evaluated_depsgraph_get(); ev = over.evaluated_get(dg)
        cloth_pts = np.array([ev.matrix_world @ v.co for v in ev.data.vertices])
        under = np.vstack([pos, cloth_pts])
    sgn = 1 if side == 'L' else -1
    # inner edge ~9 cm from the midline: the mantle lies on the shoulder and collarbone, never around the
    # neck (a sheet starting at the neck rides up over the chin/beard once the body moves)
    length, width, step = 2.0, 0.52, 0.02
    cx, cy = sgn * 0.35, M['cy']
    nx, ny = int(width / step) + 1, int(length / step) + 1
    verts, faces, pin = [], [], []
    for j in range(ny):
        for i in range(nx):
            x = cx + (i / (nx - 1) - 0.5) * width
            y = cy + (j / (ny - 1) - 0.5) * length
            st = shoulder_top(under, x, cy, M['shoulder_z'] + 0.085)
            base = (st if st is not None else M['shoulder_z']) + 0.022
            on_shoulder = abs(y - cy) < 0.09 and st is not None and 0.05 < abs(x) < M['shoulder_x'] + 0.05
            # start as an inverted V draped from the shoulder, so the fabric never begins over the head
            z = base if on_shoulder else base - (abs(y - cy) - 0.09) * 0.3
            if abs(x) < 0.09:                                          # inner edge near the neck starts lower
                z -= (0.09 - abs(x)) * 1.5
            verts.append((x, y, z)); pin.append(1.0 if on_shoulder else 0.0)
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new('himation'); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new('himation', me)); o.data.materials.append(material)
    set_uv(o, [((i % nx) / (nx - 1), (i // nx) / (ny - 1)) for i in range(len(verts))])
    vg = o.vertex_groups.new(name='pin')
    for i, w in enumerate(pin):
        if w:
            vg.add([i], w, 'REPLACE')
    if follow:
        bind_to_skeleton(o, human, rig)
    cm = _cloth(o, 'pin', mass=0.3, tension=15, bending=0.4)         # wool: heavy, soft folds
    cm.collision_settings.distance_min = 0.01                          # keep clear of the tunic underneath
    cm.collision_settings.collision_quality = 6
    cm.settings.quality = 12
    sol = o.modifiers.new('thick', 'SOLIDIFY'); sol.thickness = 0.004; sol.offset = 1.0
    o.modifiers.new('smooth', 'SUBSURF').levels = 1
    return o


def freeze(obj):
    """Bake a simulated garment into a plain mesh at the current frame, then let later garments collide
    with it (so a cloak drapes OVER the tunic instead of the tunic poking through)."""
    bpy.context.view_layer.objects.active = obj
    for m in list(obj.modifiers):
        if m.type == 'CLOTH':
            bpy.ops.object.modifier_apply(modifier=m.name)
    c = obj.modifiers.new('collision', 'COLLISION')
    obj.collision.thickness_outer = 0.02
    obj.collision.use_culling = False                 # collide from both sides of the thin tunic
    obj.collision.cloth_friction = 10.0


def simulate(frames=45):
    """Step the timeline so every cloth modifier simulates up to `frames`."""
    s = bpy.context.scene
    s.frame_start, s.frame_end = 1, frames
    for f in range(1, frames + 1):
        s.frame_set(f)


def settle_then_follow(garment, human, rig, frames=60, soft=0.3, near=0.035, mass=None, air=0.6):
    """For moving shots: drape `garment` (built with follow=False) while the body stands still, make that settled
    drape its new starting shape, then bind it to the skeleton and simulate again during the motion.
    Points lying against the body (within `near` m) get a soft pin (`soft`), so the wrapped part moves with the
    torso and only the free ends swing; air drag is lowered so heavy wool does not stream out like a cape."""
    simulate(frames)
    bpy.context.view_layer.objects.active = garment
    old = next(m for m in garment.modifiers if m.type == 'CLOTH')
    s0 = old.settings
    keep = dict(mass=s0.mass, tension=s0.tension_stiffness, bending=s0.bending_stiffness)
    dmin, quality, cq = old.collision_settings.distance_min, s0.quality, old.collision_settings.collision_quality
    with bpy.context.temp_override(object=garment, active_object=garment):
        bpy.ops.object.modifier_apply(modifier=old.name)
    # soft pins: distance from every garment point to the (still) body surface
    dg = bpy.context.evaluated_depsgraph_get()
    body = human.evaluated_get(dg)
    bw = body.matrix_world
    from mathutils.kdtree import KDTree
    kd = KDTree(len(body.data.vertices))
    for i, v in enumerate(body.data.vertices):
        kd.insert(bw @ v.co, i)
    kd.balance()
    vg = garment.vertex_groups['pin']
    gw = garment.matrix_world
    for v in garment.data.vertices:
        hard = any(g.group == vg.index and g.weight >= 0.99 for g in v.groups)
        if not hard:
            _, _, dist = kd.find(gw @ v.co)
            if dist < near:
                vg.add([v.index], soft * (1 - dist / near) + 0.05, 'REPLACE')
    others = [m for m in garment.modifiers]                        # solidify / subsurf / collision: re-added after
    saved = [(m.type, m.name) for m in others]
    for m in others:
        garment.modifiers.remove(m)
    bind_to_skeleton(garment, human, rig)
    cm = _cloth(garment, 'pin', mass=mass or keep['mass'], tension=keep['tension'], bending=keep['bending'])
    cm.settings.air_damping = air; cm.settings.quality = quality
    cm.settings.pin_stiffness = 2.0
    cm.collision_settings.distance_min = dmin; cm.collision_settings.collision_quality = cq
    for typ, name in saved:
        m = garment.modifiers.new(name, typ)
        if typ == 'SOLIDIFY':
            m.thickness = 0.004 if 'himation' in garment.name else 0.0025
            m.offset = 1.0 if 'himation' in garment.name else -1.0
        elif typ == 'SUBSURF':
            m.levels = 1
        elif typ == 'COLLISION':
            garment.collision.thickness_outer = 0.012; garment.collision.use_culling = False
    return cm



# ======================================================================================================
#  WARDROBE v2 (WS3, Session D, 2026-11-19)
#  New garments: peplos + veil (Greek women), exomis (workers), child's tunic, priest/priestess robes,
#  Persian court dress (candys robe with wide sleeves, trousers, sleeved Median tunic, tiara / kidaris / cap),
#  accessories (belts, sandals, dress pins, diadem, fillet, earrings, necklace) and WEAR by rank
#  (patches, frayed hems, crease dirt) driven by the crowd generator's dye fields (tc/crowd.py).
#
#  Two ways a garment gets its shape (both are cloth simulation):
#   A. "blend" garments (peplos, exomis, child tunic): built around the REST body, simulated while the body
#      moves into its pose (the scene calls pose.blend_into_pose first). Same proven method as chiton().
#   B. "posed" garments (veil, all Persian pieces, sleeves): built around the body AFTER it is in its final
#      pose (scene calls rig.animation_data_clear(); pose.apply_pose(...)); the body stays still while the
#      cloth falls. Needed when arms stick out forward (sleeves) or the cloth starts on the head (veil).
#  Every new garment function simulates AND freezes itself when sim=True (default), so the next layer
#  drapes over it. Accessories are rigid meshes parented to a bone: build them once the pose is final.
# ======================================================================================================


# ------------------------------------------------------------------ small geometry helpers
def posed_surface(human):
    """Body vertex positions at the CURRENT pose (armature applied), same vertex order as cast.rest_surface()
    (helper mask + subdivision switched off while reading), in world space. Used by 'posed' garments."""
    mods = [m for m in human.modifiers if m.type in ('MASK', 'SUBSURF')]
    for m in mods:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = human.evaluated_get(dg); me = ev.to_mesh()
    pos = np.zeros(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get('co', pos)
    ev.to_mesh_clear()
    for m in mods:
        m.show_viewport = True
    mw = np.array(human.matrix_world)
    return pos.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]


def bone_pos(rig, name, tail=False):
    """World position of a bone's head (or tail) in the CURRENT pose."""
    pb = rig.pose.bones[name]
    return np.array(rig.matrix_world @ (pb.tail if tail else pb.head), dtype=np.float32)


def _hull2d(P):
    """Convex hull of 2-D points (monotone chain), counter-clockwise. Used to wrap a belt / strap / band
    around a slice of the body: the hull is the outline a tight cord would follow."""
    P = sorted(set(map(tuple, np.round(np.asarray(P, dtype=np.float64), 5))))
    if len(P) < 3:
        return np.array(P)
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return np.array(lo[:-1] + hi[:-1])


def _resample(loop, n):
    """n points evenly spaced along a closed 2-D outline (so cords and beads are spaced evenly)."""
    pts = np.vstack([loop, loop[:1]])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.stack([np.interp(t, s, pts[:, i]) for i in range(2)], axis=1)


def _slice_loop(P, axis, value, off, n=96, tol=0.006, mask=None):
    """Closed outline around the points of P lying in the plane P[:, axis] == value (+- tol), pushed outward by
    `off` metres, as an (n, 3) array. axis 2 = horizontal slice (belt, necklace, diadem), axis 1 = a slice
    across the foot (sandal strap). None if the slice is empty."""
    sel = np.abs(P[:, axis] - value) < tol
    if mask is not None:
        sel &= mask
    if sel.sum() < 3:
        return None
    other = [i for i in range(3) if i != axis]
    hull = _hull2d(P[sel][:, other])
    if len(hull) < 3:
        return None
    loop = _resample(hull, n)
    c = loop.mean(axis=0)
    d = loop - c
    d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9
    loop = loop + d * off                                             # push outward (clears skin / cloth)
    out = np.zeros((n, 3), dtype=np.float32)
    out[:, other[0]], out[:, other[1]], out[:, axis] = loop[:, 0], loop[:, 1], value
    return out


def _mesh_from_curve(name, pts, radius, material, closed=True, extrude=0.0):
    """A cord / strap / wire along a polyline: a Blender curve with a round bevel (radius) and optional flat
    extrusion (a band `extrude` m tall), converted to a plain mesh (meshes can be colliders and export cleanly)."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (float(p[0]), float(p[1]), float(p[2]), 1.0)
    sp.use_cyclic_u = closed
    cu.bevel_depth = radius; cu.bevel_resolution = 2; cu.extrude = extrude
    tmp = link(bpy.data.objects.new(name + '_curve', cu))
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    o = link(bpy.data.objects.new(name, me))
    o.data.materials.clear(); o.data.materials.append(material)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _loft(name, rings, material, cap_top=False, closed=True):
    """Skin a stack of rings (each (n, 3), bottom first) into a mesh: hats, bands, sandal soles.
    UV: u around, v up (0 at the bottom ring)."""
    n = len(rings[0]); R = len(rings)
    verts = [tuple(map(float, p)) for ring in rings for p in ring]
    cols = n if closed else n - 1
    faces = [(r * n + k, r * n + (k + 1) % n, (r + 1) * n + (k + 1) % n, (r + 1) * n + k)
             for r in range(R - 1) for k in range(cols)]
    if cap_top:                                                       # close the top with a fan to its centre
        verts.append(tuple(map(float, np.mean(rings[-1], axis=0))))
        c = len(verts) - 1
        faces += [((R - 1) * n + k, (R - 1) * n + (k + 1) % n, c) for k in range(n)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(material)
    uvs = [((i % n) / n, (i // n) / max(1, R - 1)) for i in range(R * n)] + ([(0.5, 1.0)] if cap_top else [])
    set_uv(o, uvs)
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def _nearest_bone(rig, z, names):
    """The bone (from `names`) whose head is closest in height to z: what a belt or band should ride on."""
    return min(names, key=lambda n: abs(bone_pos(rig, n)[2] - z))


def _garment_object(name, verts, pins, rows, seg, material, slits=None):
    """Grid of `rows` rings x `seg` points (row 0 = top) -> closed tube mesh with UVs (v = 0 at the hem, so the
    woven border band and the hem grime land on the hem) and a 'pin' vertex group.
    slits = (n_rows, half_width): leave the tube OPEN at both sides (angle 0 and 180 deg) for the top n_rows rows,
    `half_width` (in sin(angle)) wide: the armholes of a peplos, where the arms come out between front and back."""
    def open_side(r, k):
        if not slits or r >= slits[0]:
            return False
        a = 2 * math.pi * (k + 0.5) / seg
        return abs(math.sin(a)) < slits[1]
    faces = [(r * seg + k, r * seg + (k + 1) % seg, (r + 1) * seg + (k + 1) % seg, (r + 1) * seg + k)
             for r in range(rows - 1) for k in range(seg) if not open_side(r, k)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(material)
    set_uv(o, [((i % seg) / seg, 1 - (i // seg) / (rows - 1)) for i in range(len(verts))])
    vg = o.vertex_groups.new(name='pin')
    for i, w in enumerate(pins):
        if w > 0:
            vg.add([i], float(w), 'REPLACE')
    return o


def _finish(o, thick=0.0025, offset=-1.0):
    """Cloth thickness (solidify) + one level of smoothing, like the chiton."""
    s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = thick; s.offset = offset
    o.modifiers.new('smooth', 'SUBSURF').levels = 1


def _sim_freeze(objs, frames, shell=None):
    """Simulate every cloth in the scene up to `frames`, then freeze `objs` so later layers drape over them.
    Garments that were bound to the skeleton lose their armature modifier here: the frozen shape is ALREADY
    the posed shape (keeping the modifier would pose it a second time)."""
    for o in objs:
        for m in o.modifiers:
            if m.type == 'CLOTH':
                m.point_cache.frame_end = max(m.point_cache.frame_end, frames)
    simulate(frames)
    for o in objs:
        freeze(o)
        if shell is not None:                                         # thinner collision shell: the next layer
            o.collision.thickness_outer = shell                       # lies ON it instead of tenting 2 cm above
        for m in [m for m in o.modifiers if m.type == 'ARMATURE']:
            o.modifiers.remove(m)


def _column_tube(name, seg, top_fn, waist_z, bottom_fn, upper_xy, skirt_xy, belt_xy=None, ring_h=0.014,
                 material=None, slit_z=None, slit_w=0.32):
    """General tunic/robe builder. A tube of `seg` columns (angle a around the body):
         row 0          : top_fn(a) -> (x, y, z, pin)    shoulder seam / neckline / one-shoulder diagonal
         rows to waist  : upper_xy(a, z) -> (x, y)        chest part, top -> waist
         waist row      : belt_xy(a) -> (x, y), pinned    the belt pulls the cloth in (None = no belt)
         rows to hem    : skirt_xy(a, z, t) -> (x, y)     t = 0 at the waist -> 1 at the hem
         hem height     : bottom_fn(a) -> z               (can vary: Persian side-hitched hem)
       Each column is spaced evenly between its own top, the waist and its own hem, so tops and hems of
       different heights (exomis diagonal, hitched hem) still give a clean grid."""
    tops = [top_fn(2 * math.pi * k / seg) for k in range(seg)]
    bots = [bottom_fn(2 * math.pi * k / seg) for k in range(seg)]
    n1 = max(3, int(round((max(t[2] for t in tops) - waist_z) / ring_h)))
    n2 = max(3, int(round((waist_z - min(bots)) / ring_h)))
    rows = n1 + n2 + 1
    verts = [None] * (rows * seg); pins = [0.0] * (rows * seg)
    for k in range(seg):
        a = 2 * math.pi * k / seg
        x0, y0, z0, w0 = tops[k]
        verts[k] = (x0, y0, z0); pins[k] = w0
        for r in range(1, n1 + 1):
            z = z0 + (waist_z - z0) * r / n1
            if r == n1 and belt_xy is not None:
                x, y = belt_xy(a); pins[r * seg + k] = 1.0
            else:
                x, y = upper_xy(a, z)
            verts[r * seg + k] = (x, y, z)
        for j in range(1, n2 + 1):
            t = j / n2
            z = waist_z + (bots[k] - waist_z) * t
            x, y = skirt_xy(a, z, t)
            verts[(n1 + j) * seg + k] = (x, y, z)
    slits = None
    if slit_z is not None:                                            # armholes: open sides down to slit_z
        top_max = max(t[2] for t in tops)
        slits = (max(1, int(round((top_max - slit_z) / (top_max - waist_z) * n1))), slit_w)
    o = _garment_object(name, verts, pins, rows, seg, material, slits)
    o['waist_z'] = float(waist_z)                                    # belt() finds the belt line from this
    return o


def _seam_top(pos, M, rx, ry, top_z, pinned=lambda x: True, neck_w=0.35, seam_lo=0.07, seam_hi=None, lift=0.006):
    """top_fn for a garment sewn/pinned along both shoulders (chiton style): front and back halves meet on top of
    the shoulder; the neckline lies softly on the collarbones. `pinned(x)` chooses which seam points are hard
    pins (all = sewn seam; a few = dress pins, the cloth between them sags)."""
    cy = M['cy']; hi = seam_hi if seam_hi is not None else M['shoulder_x'] + 0.02
    def f(a):
        x, y = rx * math.cos(a), cy + ry * math.sin(a)
        if seam_lo <= abs(x) < hi:
            st = shoulder_top(pos, x, cy, M['shoulder_z'] + 0.085)
            if st is not None:
                return x, cy + 0.25 * (y - cy), st + lift, (1.0 if pinned(x) else 0.0)
        elif abs(x) < seam_lo:
            nz = M['shoulder_z'] - (0.035 if y < cy else 0.0)
            sy = surface_y(pos, x, nz, front=y < cy)
            if sy is not None:
                return x, sy + (-0.006 if y < cy else 0.006), nz, neck_w
        return x, y, top_z, 0.0
    return f


def _chest(pos, M, z):
    """Half-width / half-depth of the torso at height z (arms excluded)."""
    band = (np.abs(pos[:, 2] - z) < 0.015) & (np.abs(pos[:, 0]) < M['shoulder_x'] - 0.015)
    if not band.any():
        return M['waist_rx'] + 0.04, M['waist_ry'] + 0.04
    return float(np.abs(pos[band][:, 0]).max()), float(np.abs(pos[band][:, 1] - M['cy']).max())


# ------------------------------------------------------------------ GREEK WOMEN: peplos + veil
def peplos(human, rig, pos, material, overfold=None, belt_over=True, frames=45, seg=144, ring_h=0.014, sim=True):
    """The Doric PEPLOS (Greek women, c. 500-450 BC): one large rectangle of WOOL, its top folded over
    (the overfold, 'apoptygma') and fastened on each shoulder with long dress pins, belted at the waist.
    Herodotus (5.87-88) tells how Athenian women used those long pins as weapons, which is why the pinned
    peplos is the iconic early-5th-century dress (Peplos Kore, Olympia west pediment, Athena on vases).
    Built as two tubes: the full-length body and a shorter overfold over it reaching the hips. Both are pinned
    at 2 points per shoulder (between the pins the wool sags) and OPEN AT THE SIDES down to the armpit, so the
    arms come out between front and back panels. The skirt is narrow at the hands and widens to the feet,
    so the hanging hands stay outside the cloth.
    belt_over=True: the belt goes over the overfold (Athena Parthenos type); False: the overfold hangs free
    over a hidden belt (Peplos Kore type). Body must be blending into its pose (pose.blend_into_pose; a pose
    with the hands a little away from the hips works best, e.g. 'stand_open' in ws3_wardrobe.py).
    Returns (body, overfold), both frozen."""
    M = body_measure(human, rig, pos)
    s, cy = M['shoulder_x'], M['cy']
    zones = [(0.42 * s, 0.6 * s), (0.78 * s, 0.98 * s)]          # two pins per shoulder (inner + outer)
    pinned = lambda x: any(a <= abs(x) < b for a, b in zones)
    top_z = M['shoulder_z'] + 0.02
    armpit_z = M['shoulder_z'] - 0.17
    rx, ry = max(s + 0.14, 0.32), 0.22                              # wide: wool falls in deep folds
    wrx, wry = M['waist_rx'] + 0.012, M['waist_ry'] + 0.012
    hand_z = M['hip_z'] - 0.12
    def belt(pad):
        return lambda a: ((M['waist_rx'] + pad) * math.cos(a), cy + (M['waist_ry'] + pad) * math.sin(a))
    def ring(X, Y):
        return lambda a, z, *t: (X * math.cos(a), cy + Y * math.sin(a))
    def a_line(a, z, t):
        # waist -> hands: close to the hips (0.215 m half-width at the hands) -> floor: full width
        if z > hand_z:
            f = (M['waist_z'] - z) / max(1e-6, M['waist_z'] - hand_z)
            X, Y = wrx + (0.215 - wrx) * f, wry + (0.17 - wry) * f
        else:
            f = (hand_z - z) / max(1e-6, hand_z - 0.035)
            X, Y = 0.215 + (rx - 0.215) * f ** 0.8, 0.17 + (ry - 0.17) * f ** 0.8
        return X * math.cos(a), cy + Y * math.sin(a)
    main = _column_tube('peplos', seg, _seam_top(pos, M, rx, ry, top_z, pinned, neck_w=0.12, seam_lo=0.42 * s),
                        M['waist_z'], lambda a: 0.035, ring(rx, ry), a_line, belt(0.012), ring_h, material,
                        slit_z=armpit_z)
    cm = _cloth(main, 'pin', mass=0.25, tension=14, bending=0.15)   # wool: heavy, but soft enough to fold
    cm.settings.quality = 10; cm.collision_settings.collision_quality = 4
    _finish(main, 0.003)
    if not sim:
        return main, None
    _sim_freeze([main], frames, shell=0.006)
    # overfold: same pins (a little higher, it lies on top), slightly wider, down to the hips, no flare
    ofl = overfold if overfold is not None else (M['shoulder_z'] - M['waist_z']) + 0.13
    R2, Y2 = rx + 0.012, ry + 0.012
    def over_skirt(a, z, t):
        return ((wrx + 0.03 + 0.03 * t) * math.cos(a), cy + (wry + 0.03 + 0.03 * t) * math.sin(a))
    over = _column_tube('peplos_overfold', seg, _seam_top(pos, M, R2, Y2, top_z, pinned, neck_w=0.12,
                                                          seam_lo=0.42 * s, lift=0.01),
                        M['waist_z'], lambda a: top_z - ofl, ring(R2, Y2), over_skirt,
                        belt(0.03) if belt_over else None, ring_h, material, slit_z=armpit_z)
    cm = _cloth(over, 'pin', mass=0.25, tension=14, bending=0.15)
    cm.settings.quality = 10; cm.collision_settings.distance_min = 0.006; cm.collision_settings.collision_quality = 4
    _finish(over, 0.003)
    _sim_freeze([over], frames, shell=0.006)
    return main, over


def veil(human, rig, material, size=(1.35, 1.55), hair_room=0.014, frames=60, sim=True):
    """A Greek woman's mantle drawn up OVER THE HEAD as a veil (married women in public, mourners, brides:
    Attic white-ground lekythoi, grave stelai such as the Hegeso stele, c. 410 BC; Penelope on red-figure vases).
    A large wool sheet laid over the crown (hard-pinned in a small patch on top of the head) falls over the
    head, shoulders, back and arms. `hair_room`: the veil floats that far above the scalp, over the hair.
    POSED garment: call after the body is in its final, still pose (and over frozen garments)."""
    ppos = posed_surface(human)
    head = bone_pos(rig, 'head')
    eye_z = (bone_pos(rig, 'eye.L')[2] + bone_pos(rig, 'eye.R')[2]) / 2
    on_head = (np.linalg.norm(ppos - head, axis=1) < 0.25) & (ppos[:, 2] > eye_z - 0.02)
    hp = ppos[on_head]
    top = hp[np.argmax(hp[:, 2])]                                    # crown of the head
    brow = hp[(np.abs(hp[:, 2] - (eye_z + 0.04)) < 0.01) & (np.abs(hp[:, 0]) < 0.02)]
    front_y = brow[:, 1].min() if len(brow) else top[1] - 0.1
    W, L = size; step = 0.02
    nx, ny = int(W / step) + 1, int(L / step) + 1
    y0 = front_y + 0.015                                             # front edge sits on the forehead hairline
    # height of the scalp under each point near the crown: the pinned patch is laid ON the head's own round
    # shape (a flat pinned patch made a box-like tent above the crown)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(hp))
    for i, q in enumerate(hp):
        kd.insert((float(q[0]), float(q[1]), 0.0), i)
    kd.balance()
    def scalp_z(x, y):
        found = kd.find_range((x, y, 0.0), 0.014)
        return max(float(hp[i][2]) for _, i, _ in found) if found else None
    verts, faces, pin = [], [], []
    for j in range(ny):
        for i in range(nx):
            x = top[0] + (i / (nx - 1) - 0.5) * W
            y = y0 + j / (ny - 1) * L
            d = math.hypot(x - top[0], y - top[1])
            z = top[2] + hair_room + 0.004 - 0.45 * max(0.0, d - 0.09)  # a low dome: never starts inside the body
            w = 0.0
            if d < 0.13:
                sz = scalp_z(x, y)
                if sz is not None:
                    z = max(sz + hair_room, z - 0.03) if d >= 0.1 else sz + hair_room
                    w = 1.0 if d < 0.1 else 0.0                       # the veil rests on the top of the head
            verts.append((x, y, z)); pin.append(w)
    for j in range(ny - 1):
        for i in range(nx - 1):
            a = j * nx + i
            faces.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new('veil'); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new('veil', me)); o.data.materials.append(material)
    set_uv(o, [((i % nx) / (nx - 1), (i // nx) / (ny - 1)) for i in range(len(verts))])
    vg = o.vertex_groups.new(name='pin')
    for i, w in enumerate(pin):
        if w:
            vg.add([i], w, 'REPLACE')
    cm = _cloth(o, 'pin', mass=0.18, tension=12, bending=0.1)       # fine wool: soft, many folds
    cm.settings.quality = 10
    cm.collision_settings.distance_min = hair_room                   # rides over the hair, not through it
    cm.collision_settings.collision_quality = 5
    _finish(o, 0.003, offset=1.0)
    if sim:
        _sim_freeze([o], frames)
    return o


# ------------------------------------------------------------------ workers and children
def exomis(human, rig, pos, material, length='thigh', bare='R', frames=45, seg=128, ring_h=0.014, sim=True):
    """The EXOMIS: short tunic fastened on ONE shoulder only, the other shoulder and side of the chest bare,
    belted. Worn by craftsmen, rowers, farmers, slaves and Hephaistos himself (Attic vases with smiths and
    potters at work). Wool or coarse cloth, mid-thigh length. `bare` = the uncovered side ('R' = right
    shoulder bare, the usual way: the working arm free). Body must be blending into its pose."""
    M = body_measure(human, rig, pos)
    s, cy = M['shoulder_x'], M['cy']
    sgn = 1 if bare == 'L' else -1                                  # x side that is bare (L = +x)
    armpit_z = M['shoulder_z'] - 0.13
    crx, cry = _chest(pos, M, armpit_z)
    urx, ury = crx + 0.045, cry + 0.05
    top_z = M['shoulder_z'] + 0.02
    seam = _seam_top(pos, M, urx, ury, top_z, seam_lo=0.07)
    def top(a):
        x = urx * math.cos(a)
        if x * sgn <= -0.07:                                         # fastened shoulder: a normal seam
            return seam(a)
        # bare side: the top edge runs diagonally from the fastened side's neck down under the bare armpit,
        # lying (soft-pinned) on the chest and back
        t = min(1.0, max(0.0, (x * sgn + 0.07) / (0.07 + crx)))
        z = (M['shoulder_z'] - 0.03) + (armpit_z - (M['shoulder_z'] - 0.03)) * t ** 0.7
        y_ring = cy + (cry + 0.012) * math.sin(a)
        sy = surface_y(pos, x, z, front=y_ring < cy) if abs(x) < crx - 0.02 else None
        if sy is not None:
            return x, sy + (-0.01 if y_ring < cy else 0.01), z, 0.6
        return (crx + 0.014) * math.cos(a), y_ring, z, 0.6
    rx, ry = max(s + 0.08, 0.27), 0.2
    bottom = M['knee_z'] + (0.16 if length == 'thigh' else 0.05)
    wrx, wry = M['waist_rx'] + 0.02, M['waist_ry'] + 0.02
    def skirt(a, z, t):
        f = min(1.0, t * 2.5)                                        # flares out quickly below the belt
        return ((wrx + (rx - wrx) * f) * math.cos(a), cy + (wry + (ry - wry) * f) * math.sin(a))
    o = _column_tube('exomis', seg, top, M['waist_z'], lambda a: bottom,
                     lambda a, z: (urx * math.cos(a), cy + ury * math.sin(a)), skirt,
                     lambda a: ((M['waist_rx'] + 0.012) * math.cos(a), cy + (M['waist_ry'] + 0.012) * math.sin(a)),
                     ring_h, material)
    _cloth(o, 'pin', mass=0.16, tension=12, bending=0.3).settings.quality = 10     # coarse wool
    _finish(o, 0.003)
    if sim:
        _sim_freeze([o], frames)
    return o


def child_tunic(human, rig, pos, material, frames=45, seg=112, sim=True):
    """A child's short tunic (chitoniskos): a small linen or wool tube sewn on both shoulders, belted, knee-length,
    as boys and girls wear it on Attic choes (little jugs given to children at the Anthesteria, c. 420 BC) and
    grave reliefs. Sized from the child's own body (the adult chiton's minimum width would drown a child)."""
    M = dict(body_measure(human, rig, pos))
    s, cy = M['shoulder_x'], M['cy']
    # a child's torso is short: the adult rule (waist = hips + 17 cm) would belt the tunic at the chest
    M['waist_z'] = M['hip_z'] + 0.36 * (M['shoulder_z'] - M['hip_z']) + 0.02
    M['waist_rx'], M['waist_ry'] = _chest(pos, M, M['waist_z'])
    crx, cry = _chest(pos, M, M['shoulder_z'] - 0.09)
    rx, ry = crx + 0.022, cry + 0.045                                 # inside the arms: they pass the armholes
    top_z = M['shoulder_z'] + 0.015
    wrx, wry = M['waist_rx'] + 0.01, M['waist_ry'] + 0.01
    ring = lambda a, z, *t: (rx * math.cos(a), cy + ry * math.sin(a))
    def skirt(a, z, t):                                              # close at the hips (hands stay outside),
        X, Y = wrx + 0.02 + 0.04 * t, wry + 0.02 + 0.04 * t          # a little wider at the hem
        return X * math.cos(a), cy + Y * math.sin(a)
    o = _column_tube('child_tunic', seg, _seam_top(pos, M, rx, ry, top_z, seam_lo=0.05, seam_hi=s + 0.015, lift=0.005),
                     M['waist_z'] - 0.02, lambda a: M['knee_z'] + 0.03, ring, skirt,
                     lambda a: (wrx * math.cos(a), cy + wry * math.sin(a)),
                     0.011, material, slit_z=M['shoulder_z'] - 0.16)
    _cloth(o, 'pin', mass=0.1, tension=10, bending=0.05).settings.quality = 10
    _finish(o, 0.0022)
    if sim:
        _sim_freeze([o], frames)
    return o


def priest_robes(human, rig, pos, linen, wool, pose_name='stand_relaxed', female=False, frames=45):
    """Ritual dress of a priest or priestess: an ANKLE-LENGTH chiton of pale, clean linen (purity: priests wore
    white, unstained cloth; long robes mark age and dignity) with a pale wool himation over it; a priestess
    draws hers over her head as a veil. Design sources: the Parthenon frieze east side (priest and priestess
    handling the peplos, c. 440 BC), priestess grave stelai, red-figure sacrifice scenes. Add a fillet
    (`fillet()`) or a diadem (`diadem()`), sandals and jewellery afterwards.
    Body must be blending into `pose_name`. Returns (chiton, mantle)."""
    ch = chiton(human, rig, pos, linen, length='ankle')
    _sim_freeze([ch], frames)
    rig.animation_data_clear()
    from lib import pose as _pose
    _pose.apply_pose(rig, pose_name)
    if female:
        return ch, veil(human, rig, wool, frames=60)
    m = himation(human, rig, pos, wool, side='L', over=ch)
    _sim_freeze([m], 60)
    return ch, m



# ------------------------------------------------------------------ PERSIAN court dress, 480 BC
def trousers(human, rig, material, frames=40, ring_h=0.012, seg=48, sim=False):
    """Trousers ('anaxyrides'): the Iranian riders' garment the Greeks found so strange (Herodotus 1.71, 5.49,
    7.61). Two loose wool legs from the upper thigh, gathered at the ankle; worn under the tunic or robe. POSED.
    By default NOT simulated: a closed tube pinned at both ends sagged into accordion rings in every test, so the
    legs are built as a fitted shape with procedural folds (long soft vertical folds + bunching above the ankle,
    where the cloth gathers into the cuff) and become a collider for the robe/tunic. sim=True = cloth (experimental)."""
    ppos = posed_surface(human)
    verts, pins, parts = [], [], []
    for side in 'LR':
        sgn = 1 if side == 'L' else -1
        hip, knee, ank = (bone_pos(rig, f'{b}.{side}') for b in ('upperleg01', 'lowerleg01', 'foot'))
        # start on the upper thigh (always hidden under the tunic/robe): at the hip joint itself a 'leg slice'
        # is really half the pelvis and the tube balloons into a box
        z_top, z_bot = hip[2] - 0.17, ank[2] + 0.01
        rows = int((z_top - z_bot) / ring_h) + 1
        # leg radius per row. MakeHuman's leg has edge loops a few cm apart: a thin slice alternately catches a
        # whole loop or almost nothing, which made regular bulging RINGS. So: thick slices (+-3 cm), then smooth.
        cs, rads = [], []
        for r in range(rows):
            z = z_top - r * ring_h
            if z >= knee[2]:                                          # leg axis at this height: hip -> knee -> ankle
                c = hip + (knee - hip) * (hip[2] - z) / max(1e-6, hip[2] - knee[2])
            else:
                c = knee + (ank - knee) * (knee[2] - z) / max(1e-6, knee[2] - ank[2])
            sl = (np.abs(ppos[:, 2] - z) < 0.03) & (ppos[:, 0] * sgn > 0.005) &                  (np.linalg.norm(ppos[:, :2] - c[:2], axis=1) < 0.15)
            cs.append(c)
            rads.append(float(np.percentile(np.linalg.norm(ppos[sl][:, :2] - c[:2], axis=1), 92)) if sl.sum() > 5 else np.nan)
        rads = np.array(rads)
        good = ~np.isnan(rads)
        rads = np.interp(np.arange(rows), np.where(good)[0], rads[good])
        rads = np.convolve(np.pad(rads, 3, mode='edge'), np.ones(7) / 7, mode='valid')   # smooth along the leg
        for r in range(rows):
            z = z_top - r * ring_h
            c, rad = cs[r], float(rads[r])
            last = r == rows - 1
            # snug at the hips (they go under a robe or tunic), loose from mid-thigh, gathered tight at the ankle
            R = rad + (0.008 if last else 0.008 + 0.014 * min(1.0, r / max(1, rows * 0.3)))
            bunch = max(0.0, 1 - (z - z_bot) / 0.16) if not last else 0.0    # 1 at the ankle -> 0 16 cm above
            for k in range(seg):
                a = 2 * math.pi * k / seg
                RR = R
                if not sim:
                    RR += 0.006 * math.sin(5 * a + 7 * z + sgn) * (1 - bunch)          # long vertical folds
                    RR += 0.012 * bunch * math.sin(z * 140 + 2.5 * math.sin(3 * a)) ** 2   # gathered rolls
                verts.append((float(c[0] + RR * math.cos(a)), float(c[1] + RR * math.sin(a)), float(z)))
                pins.append(1.0 if (r == 0 or last) else 0.0)
        parts.append(rows)
    faces, uv, base = [], [], 0                                       # two separate tubes in one mesh
    for rows in parts:
        faces += [(base + r * seg + k, base + r * seg + (k + 1) % seg, base + (r + 1) * seg + (k + 1) % seg,
                   base + (r + 1) * seg + k) for r in range(rows - 1) for k in range(seg)]
        uv += [((i % seg) / seg, 1 - (i // seg) / (rows - 1)) for i in range(rows * seg)]
        base += rows * seg
    me = bpy.data.meshes.new('trousers'); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new('trousers', me)); o.data.materials.append(material)
    set_uv(o, uv)
    vg = o.vertex_groups.new(name='pin')
    for i, w in enumerate(pins):
        if w:
            vg.add([i], w, 'REPLACE')
    # cloth mass is PER VERTEX in Blender: a fine tube of 2 x 48 x ~45 points must be light, and stiff against
    # stretching, or it sags down the leg into accordion rings
    _finish(o, 0.003)
    if sim:
        cm = _cloth(o, 'pin', mass=0.04, tension=40, bending=0.5); cm.settings.quality = 10
        o.modifiers.move(len(o.modifiers) - 1, 0)                     # cloth before thickness / smoothing
        _sim_freeze([o], frames, shell=0.008)
    else:
        o.modifiers.new('collision', 'COLLISION')
        o.collision.thickness_outer = 0.008; o.collision.use_culling = False
    return o


def candys(human, rig, pos, material, pleats=24, hitch=0.11, frames=45, seg=192, ring_h=0.014, sim=True):
    """Body of the Persian court robe (Greek 'kandys'; the 'Persian robe' of the Persepolis reliefs, c. 500-480 BC:
    Apadana stairs, Treasury audience relief, the king on the palace door jambs). An ankle-length robe,
    girdled, the skirt falling in stacked PLEATS (the reliefs carve a central cascade of zigzag folds) and
    HITCHED UP AT THE SIDES so the hem rises at the hips and hangs lowest front and back.
    The wide sleeves are separate: `wide_sleeves()` after this one is frozen. POSED garment: the arms must
    already stand a little away from the body (see the royal pose in blender/scenes/xerxes_v2.py)."""
    M = body_measure(human, rig, pos)
    ppos = posed_surface(human)
    cy = M['cy']
    crx, cry = _chest(ppos, M, M['shoulder_z'] - 0.12)
    urx, ury = crx + 0.03, cry + 0.045                               # close over the chest, under the sleeves
    top_z = M['shoulder_z'] + 0.02
    wrx, wry = M['waist_rx'] + 0.012, M['waist_ry'] + 0.012
    hrx, hry = 0.30, 0.25                                            # hem
    def skirt(a, z, t):
        tri = abs(((pleats * a / (2 * math.pi)) % 1.0) - 0.5) * 4 - 1   # zigzag -1..1: accordion pleats
        k = 1 + 0.07 * tri * min(1.0, t * 3)                            # pleats open up below the belt
        f = t ** 0.5                                                    # flares quickly: room for the legs
        return ((wrx + (hrx - wrx) * f) * k * math.cos(a), cy + (wry + (hry - wry) * f) * k * math.sin(a))
    o = _column_tube('candys', seg, _seam_top(ppos, M, urx, ury, top_z, seam_hi=urx + 0.02),
                     M['waist_z'], lambda a: 0.04 + hitch * abs(math.cos(a)) ** 1.5,
                     lambda a, z: (urx * math.cos(a), cy + ury * math.sin(a)), skirt,
                     lambda a: (wrx * math.cos(a), cy + wry * math.sin(a)), ring_h, material)
    _cloth(o, 'pin', mass=0.14, tension=14, bending=0.9).settings.quality = 10     # stiffer: pleats hold
    _finish(o, 0.003)
    if sim:
        _sim_freeze([o], frames)
    return o


def _arm_frame(P0, P1, P2, l, blend=0.06):
    """Point and direction along the arm (shoulder P0 -> elbow P1 -> wrist P2) at arc length l, the direction
    blended smoothly around the elbow so sleeve rings turn the corner gently."""
    L1 = float(np.linalg.norm(P1 - P0)); d1 = (P1 - P0) / L1
    d2 = (P2 - P1) / float(np.linalg.norm(P2 - P1))
    c = P0 + d1 * l if l <= L1 else P1 + d2 * (l - L1)
    w = min(1.0, max(0.0, (l - (L1 - blend)) / (2 * blend)))
    w = w * w * (3 - 2 * w)
    d = d1 * (1 - w) + d2 * w
    return c, d / (np.linalg.norm(d) + 1e-9)


def _arm_tube(name, rig, ppos, side, l0, l1, radius_fn, pin_fn, hang=False, ring_h=0.02, seg=48, material=None):
    """A cloth tube around one (posed) arm between arc lengths l0..l1 along shoulder -> elbow -> wrist.
    radius_fn(l, arm_r) -> tube radius; pin_fn(row, rows, theta) -> pin weight (theta = 90 deg is the top of the
    arm). hang=True: the ring hangs from the TOP of the arm (wide Persian sleeve: the cloth falls below the
    forearm in a deep bag); False: centred on the arm (tight sleeve)."""
    P0, P1, P2 = (bone_pos(rig, f'{b}.{side}') for b in ('upperarm01', 'lowerarm01', 'wrist'))
    sgn = 1 if side == 'L' else -1
    rows = max(3, int((l1 - l0) / ring_h) + 1)
    verts, pins = [], []
    for r in range(rows):
        l = l0 + (l1 - l0) * r / (rows - 1)
        c, d = _arm_frame(P0, P1, P2, l)
        ref = np.array([0, 0, 1.0]) if abs(d[2]) < 0.8 else np.array([sgn, 0, 0.0])
        up = ref - d * (ref @ d); up /= np.linalg.norm(up)
        sd = np.cross(d, up)
        rel = ppos - c
        perp = rel - np.outer(rel @ d, d)
        near = (np.abs(rel @ d) < 0.012) & (np.linalg.norm(perp, axis=1) < 0.075)
        arm_r = float(np.percentile(np.linalg.norm(perp[near], axis=1), 95)) if near.sum() > 4 else 0.04
        top = float((perp[near] @ up).max()) if near.sum() > 4 else arm_r
        R = radius_fn(l, arm_r)
        cc = c + up * (top + 0.008 - R) if hang else c
        for k in range(seg):
            th = 2 * math.pi * k / seg
            p = cc + R * (math.cos(th) * sd + math.sin(th) * up)
            verts.append(tuple(map(float, p))); pins.append(pin_fn(r, rows, th))
    return _garment_object(name, verts, pins, rows, seg, material)


def wide_sleeves(human, rig, material, wrist_r=0.2, frames=40, sim=True):
    """The great hanging SLEEVES of the Persian robe (Persepolis reliefs: from the raised forearm the cloth falls
    in a long curve toward the knee, carved as rows of curving folds). Two parts per arm: a sleeve around the
    upper arm hanging from the shoulder, then a wide bag hanging from the top of the forearm, small at the elbow
    and widest at the wrist (open end). POSED garment, after candys() is frozen. Returns the 4 pieces."""
    ppos = posed_surface(human)
    uppers = []
    for side in 'LR':
        P0, P1 = bone_pos(rig, f'upperarm01.{side}'), bone_pos(rig, f'lowerarm01.{side}')
        L1 = float(np.linalg.norm(P1 - P0))
        o = _arm_tube(f'sleeve_upper.{side}', rig, ppos, side, 0.03, L1 + 0.02, lambda l, ar: ar + 0.035,
                      lambda r, rows, th: 1.0 if r == 0 else 0.0, ring_h=0.018, seg=40, material=material)
        _cloth(o, 'pin', mass=0.12, tension=12, bending=0.3).settings.quality = 8
        _finish(o, 0.0025)
        uppers.append(o)
    if not sim:
        return uppers
    _sim_freeze(uppers, frames)
    bags = []
    for side in 'LR':
        P0, P1, P2 = (bone_pos(rig, f'{b}.{side}') for b in ('upperarm01', 'lowerarm01', 'wrist'))
        L1, L2 = float(np.linalg.norm(P1 - P0)), float(np.linalg.norm(P2 - P1))
        l0, l1 = L1 - 0.07, L1 + L2 + 0.015
        def rad(l, ar, l0=l0, L2=L2):
            t = min(1.0, max(0.0, (l - l0) / (0.85 * L2)))
            return ar + 0.03 + (wrist_r - ar - 0.03) * (t * t * (3 - 2 * t))
        o = _arm_tube(f'sleeve.{side}', rig, ppos, side, l0, l1, rad,
                      lambda r, rows, th: 1.0 if abs(th - math.pi / 2) < math.radians(9) else 0.0,
                      hang=True, ring_h=0.016, seg=64, material=material)
        cm = _cloth(o, 'pin', mass=0.14, tension=12, bending=0.35)
        cm.settings.quality = 10; cm.collision_settings.distance_min = 0.008
        _finish(o, 0.0025)
        bags.append(o)
    _sim_freeze(bags, frames)
    return uppers + bags


def tight_sleeves(human, rig, material, frames=35, sim=True):
    """Long close-fitting sleeves of the Median riding tunic (Persepolis: the 'Median' dress of guards, ushers and
    nobles: belted knee-length tunic with long sleeves, trousers, rounded cap). Pinned at the shoulder and the
    wrist cuff, lightly along the top of the arm. POSED garment."""
    ppos = posed_surface(human)
    out = []
    for side in 'LR':
        P0, P1, P2 = (bone_pos(rig, f'{b}.{side}') for b in ('upperarm01', 'lowerarm01', 'wrist'))
        Lt = float(np.linalg.norm(P1 - P0) + np.linalg.norm(P2 - P1))
        o = _arm_tube(f'sleeve.{side}', rig, ppos, side, 0.02, Lt - 0.01,
                      lambda l, ar, Lt=Lt: ar + (0.009 if l > Lt - 0.05 else 0.02),
                      lambda r, rows, th: 1.0 if r in (0, rows - 1) else (0.3 if abs(th - math.pi / 2) < 0.3 else 0.0),
                      ring_h=0.016, seg=36, material=material)
        _cloth(o, 'pin', mass=0.1, tension=12, bending=0.2).settings.quality = 8
        _finish(o, 0.0022)
        out.append(o)
    if sim:
        _sim_freeze(out, frames)
    return out


def median_tunic(human, rig, pos, material, frames=45, seg=144, sim=True):
    """Body of the 'Median' tunic (Persepolis reliefs): belted, knee-length, slightly flared skirt; sleeves
    from tight_sleeves(). Worn with trousers and the rounded cap (persian_cap(kind='median')). POSED garment."""
    M = body_measure(human, rig, pos)
    ppos = posed_surface(human)
    cy = M['cy']
    crx, cry = _chest(ppos, M, M['shoulder_z'] - 0.12)
    urx, ury = crx + 0.025, cry + 0.04
    wrx, wry = M['waist_rx'] + 0.012, M['waist_ry'] + 0.012
    def skirt(a, z, t):
        f = t ** 0.4                                                  # flares fast: room for the trouser legs
        return ((wrx + (0.27 - wrx) * f) * math.cos(a), cy + (wry + (0.21 - wry) * f) * math.sin(a))
    o = _column_tube('median_tunic', seg, _seam_top(ppos, M, urx, ury, M['shoulder_z'] + 0.02, seam_hi=urx + 0.02),
                     M['waist_z'], lambda a: M['knee_z'] - 0.02, lambda a, z: (urx * math.cos(a), cy + ury * math.sin(a)),
                     skirt, lambda a: (wrx * math.cos(a), cy + wry * math.sin(a)), 0.014, material)
    _cloth(o, 'pin', mass=0.15, tension=13, bending=0.4).settings.quality = 10
    _finish(o, 0.003)
    if sim:
        _sim_freeze([o], frames)
    return o


def _eye_z(rig):
    return float((bone_pos(rig, 'eye.L')[2] + bone_pos(rig, 'eye.R')[2]) / 2)


def _head_ring(human, rig, z, lift, n=64, ppos=None):
    """Outline of the (posed) head at height z, pushed out by `lift` (room for hair): the base of a hat or band."""
    ppos = posed_surface(human) if ppos is None else ppos
    head = bone_pos(rig, 'head')
    mask = np.linalg.norm(ppos - head, axis=1) < 0.2
    return _slice_loop(ppos, 2, z, lift, n=n, tol=0.008, mask=mask)


def persian_cap(human, rig, felt, band=None, kind='royal', height=None, lift=0.014):
    """Persian headwear (Persepolis reliefs, c. 500-480 BC):
      royal  : the king's tall upright headdress (Greek 'kidaris' / 'tiara orthe': Xenophon, Anabasis 2.5.23 —
               only the king may wear it upright): a tall, slightly flaring cylinder, flat top, with a band of
               gold rosettes at the base (gold rosette dress-plaques are real Achaemenid finds)
      fluted : the lower, flaring, vertically ribbed headdress of Persian nobles and the 'Immortals'
      median : the rounded felt cap of the Median dress, its flaps covering the back of the neck and the ears
    Rigid mesh parented to the head bone. `band` = gold material for the rosette band (royal / fluted)."""
    import bmesh
    ppos = posed_surface(human)
    zb = _eye_z(rig) + (0.035 if kind != 'median' else 0.045)
    base = _head_ring(human, rig, zb, lift, ppos=ppos)
    c = base.mean(axis=0)
    if kind in ('royal', 'fluted'):          # Persepolis reliefs: the tiara sits CLOSE to the head (hair is pressed
        base = c + (base - c) * 0.8          # under it), not as wide as a bushy hairstyle - otherwise it reads as a drum
    th = np.arctan2(base[:, 1] - c[1], base[:, 0] - c[0])
    parts = []
    if kind in ('royal', 'fluted'):
        H = height or (0.155 if kind == 'royal' else 0.13)   # Persepolis: about the height of the face, not taller
        flare = 0.1 if kind == 'royal' else 0.18           # royal: gently flaring toward the top
        rings = []
        for t in np.linspace(0, 1, 14):
            k = np.full(len(base), 1 + flare * t)
            if kind == 'fluted':
                k = k * (1 + 0.025 * np.cos(th * 18))                   # vertical ribs
            elif kind == 'royal':                                       # fine vertical fluting (Persepolis reliefs)
                k = k * (1 + 0.012 * np.cos(th * 28))
            ring = c + (base - c) * k[:, None]
            ring[:, 2] = zb - 0.008 + H * t
            rings.append(ring)
        cap = _loft('persian_' + kind, rings, felt, cap_top=True)
        s = cap.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.004; s.offset = 1.0
        parts.append(cap)
        if band is not None:                                          # gold band with rosettes at the base
            b0 = c + (base - c) * 1.03; b0[:, 2] = zb
            b1 = c + (base - c) * 1.035; b1[:, 2] = zb + 0.03
            bo = _loft('cap_band', [b0, b1], band); bo.modifiers.new('thick', 'SOLIDIFY').thickness = 0.002
            parts.append(bo)
            bm = bmesh.new()
            for i in range(0, len(base), 4):                          # 16 rosettes: a disc ringed by 8 petals
                p = c + (base[i] - c) * 1.05; p[2] = zb + 0.015
                nrm = Vector((float(p[0] - c[0]), float(p[1] - c[1]), 0.0)).normalized()
                rot = nrm.to_track_quat('Z', 'Y').to_matrix().to_4x4()
                bmesh.ops.create_circle(bm, cap_ends=True, radius=0.006, segments=10,
                                        matrix=Matrix.Translation(Vector(p)) @ rot)
                for j in range(8):
                    a = j * math.pi / 4
                    q = Vector(p) + rot.to_3x3() @ Vector((math.cos(a) * 0.009, math.sin(a) * 0.009, 0.001))
                    bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.0028,
                                              matrix=Matrix.Translation(q))
            me = bpy.data.meshes.new('rosettes'); bm.to_mesh(me); bm.free()
            ro = link(bpy.data.objects.new('rosettes', me)); ro.data.materials.append(band); parts.append(ro)
    else:                                                             # median: flaps + rounded dome (one mesh)
        back = np.clip(np.sin(th), 0, 1)                              # +y = back of the head
        side = np.clip(np.abs(np.cos(th)) * 1.4 - 0.4, 0, 1)
        drop = 0.03 + 0.11 * back + 0.06 * (1 - back) * side
        front = np.clip(-np.sin(th), 0, 1)
        drop = drop * (1 - front ** 3)                                # open in front of the face
        rings = []
        for t in np.linspace(1, 0, 6):                                # flaps: from their lower edge up to the base
            ring = c + (base - c) * (1.06 + 0.04 * t)
            ring[:, 2] = zb - drop * t
            rings.append(ring)
        Hd = height or 0.11
        for t in np.linspace(0.12, 0.96, 9):                          # rounded dome, tip leaning a little forward
            k = math.sqrt(max(0.0, 1 - t * t)) * 1.06
            ring = c + (base - c) * k
            ring[:, 1] -= 0.025 * t * t; ring[:, 2] = zb + Hd * t
            rings.append(ring)
        cap = _loft('median_cap', rings, felt, cap_top=True)
        s = cap.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.004; s.offset = 1.0
        cap.modifiers.new('smooth', 'SUBSURF').levels = 1
        parts.append(cap)
    from lib import cast as _cast
    for o in parts:
        _cast.parent_to_bone(o, rig, 'head')
    return parts


# ------------------------------------------------------------------ accessories (rigid, parented to bones)
def _evaluated_points(objs):
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    pts = []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        p = np.zeros(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get('co', p)
        mw = np.array(ev.matrix_world); pts.append(p.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3])
        ev.to_mesh_clear()
    return np.vstack(pts)


def belt(rig, over, material, z=None, kind='cord', knot=True, max_r=0.2):
    """A belt around the outermost frozen garment(s) `over` at height z (default: the natural waist).
    kind 'cord' = a woven wool girdle (zone) tied in a knot at the front with two hanging ends (Greek);
    'strap' = a flat band 1.3 cm tall (Persian robes, workers). Rides on the nearest spine bone and is a
    collider, so a veil or mantle added later drapes over it."""
    over = over if isinstance(over, (list, tuple)) else [over]
    P = _evaluated_points(over)
    if z is None and 'waist_z' in over[0]:                           # the garment remembers where it is belted
        z = float(over[0]['waist_z'])
    if z is None:
        hips = (bone_pos(rig, 'upperleg01.L') + bone_pos(rig, 'upperleg01.R')) / 2
        z = float(hips[2] + 0.17)
    r = 0.006 if kind == 'cord' else 0.0025
    # only cloth close around the waist (not drapes hanging over the arms)
    hips = (bone_pos(rig, 'upperleg01.L') + bone_pos(rig, 'upperleg01.R')) / 2
    near = np.linalg.norm(P[:, :2] - hips[:2], axis=1) < max_r
    loop = _slice_loop(P, 2, z, r + 0.001, n=120, tol=0.01, mask=near)
    if kind == 'strap':                                               # the band's centre line sits half its height lower
        loop[:, 2] -= 0.0065
    parts = [_mesh_from_curve('belt', loop, r, material, extrude=0.0 if kind == 'cord' else 0.0065)]
    if knot and kind == 'cord':
        f = loop[np.argmin(loop[:, 1])]                               # front of the waist
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.011, location=tuple(map(float, f + np.array([0, -0.004, 0]))))
        k = bpy.context.object; k.name = 'belt_knot'; k.scale = (1.3, 0.8, 0.9); k.data.materials.append(material)
        parts.append(k)
        for dx, ln in ((-0.012, 0.16), (0.014, 0.12)):                # two loose ends hanging from the knot
            ends = [f + np.array([dx * t, -0.008 - 0.004 * t, -ln * t]) for t in np.linspace(0, 1, 8)]
            parts.append(_mesh_from_curve('belt_end', ends, 0.0045, material, closed=False))
    bone = _nearest_bone(rig, z, ['spine05', 'spine04', 'spine03'])
    from lib import cast as _cast
    for o in parts:
        _cast.parent_to_bone(o, rig, bone)
        o.modifiers.new('collision', 'COLLISION')
    return parts


def dress_pins(garment, rig, metal, kind='perone', per_side=2):
    """Pins at the hard-pinned shoulder points of a frozen garment:
      perone : long straight dress pin with a ball + disc head, pushed through front and back cloth (peplos;
               the pins of Herodotus 5.87; bronze/silver pins 14-20 cm long are common sanctuary finds)
      fibula : small arched safety-pin brooch (cloaks, chlamys, the Ionic chiton's sleeve fastenings)
    `per_side` pins spread over each shoulder's pinned stretch. Rides on the clavicle bones."""
    vg = garment.vertex_groups['pin']
    mw = garment.matrix_world
    pts = [np.array(mw @ v.co) for v in garment.data.vertices
           if any(g.group == vg.index and g.weight >= 0.99 for g in v.groups)]
    if not pts:
        return []
    P = np.array(pts)
    P = P[(P[:, 2] > P[:, 2].max() - 0.08) & (np.abs(P[:, 0]) > 0.04)]   # shoulder seam points (not the belt)
    parts = []
    from lib import cast as _cast
    C = _evaluated_points([garment])                                  # the cloth as rendered (with thickness)
    def cloth_top(q, r=0.025):
        near = np.linalg.norm(C[:, :2] - q[:2], axis=1) < r
        return float(C[near][:, 2].max()) if near.any() else float(q[2])
    for side, sgn in (('L', 1), ('R', -1)):
        S = P[P[:, 0] * sgn > 0]
        if not len(S):
            continue
        xs = np.sort(np.abs(S[:, 0]))
        for q in (np.linspace(0.15, 0.85, per_side) if per_side > 1 else [0.5]):
            x = xs[int(q * (len(xs) - 1))]
            near = S[np.abs(np.abs(S[:, 0]) - x) < 0.012]
            p = near.mean(axis=0); p[2] = cloth_top(p) + 0.004              # ON the cloth, never under it
            made = []
            if kind == 'perone':                                      # lies front-to-back over the shoulder,
                # lies along the top of the shoulder, front to back, ball head standing up a little in front
                # (as on the Peplos Kore / bronze peplophoroi); each point is lifted onto the cloth's surface
                a = p + np.array([0, -0.06, 0.0]); b = p + np.array([0, 0.07, 0.0])
                line = []
                for t in np.linspace(0, 1, 10):
                    q = a + (b - a) * t
                    q[2] = max(q[2] - 0.03 * t, cloth_top(q, 0.012) + 0.002)
                    line.append(q)
                a = line[0] + np.array([0, -0.004, 0.006])
                made.append(_mesh_from_curve('dress_pin', line, 0.0025, metal, closed=False))
                bpy.ops.mesh.primitive_uv_sphere_add(radius=0.011, location=tuple(map(float, a)))
                hd = bpy.context.object; hd.name = 'pin_head'; hd.data.materials.append(metal); made.append(hd)
                bpy.ops.mesh.primitive_cylinder_add(radius=0.016, depth=0.003,
                                                    location=tuple(map(float, a + np.array([0, 0.008, 0.004]))),
                                                    rotation=(math.radians(60), 0, 0))
                dk = bpy.context.object; dk.name = 'pin_disc'; dk.data.materials.append(metal); made.append(dk)
            else:                                                     # fibula: an arched bow + straight pin
                a = p + np.array([sgn * -0.026, -0.012, 0.002]); b = p + np.array([sgn * 0.026, -0.012, 0.002])
                bow = [a + (b - a) * t + np.array([0, -0.009 * math.sin(math.pi * t), 0.016 * math.sin(math.pi * t)])
                       for t in np.linspace(0, 1, 10)]
                made.append(_mesh_from_curve('fibula_bow', bow, 0.0035, metal, closed=False))
                made.append(_mesh_from_curve('fibula_pin', [a, b], 0.0013, metal, closed=False))
            for o in made:
                _cast.parent_to_bone(o, rig, f'clavicle.{side}')
            parts += made
    return parts


def diadem(human, rig, metal, height=0.012, front=0.04, lift=0.012, z_up=0.05, kind='stephane', over=None):
    """A band round the head just above the forehead:
      stephane : metal crown-band, taller over the forehead (goddesses, priestesses, brides: Hera and Aphrodite
                 on Attic vases)
      fillet   : a plain wool band (tainia) of equal height (priests, victors, sacrificers)
    `lift` = room for the hair under it. over = a frozen veil: the band then wraps the veil's own surface
    (a stephane worn over the veil, like Hera's) instead of floating at a guessed distance. Rides on the head bone."""
    z = _eye_z(rig) + z_up
    if over is not None:
        # over a veil: follow the HEAD's outline (the veil's own outline at this height is much wider where it
        # falls away at the sides, which made a flat brim), pushed out by how far the veil really sits from the
        # scalp, measured from the frozen veil itself
        P = _evaluated_points([over])
        hr = _head_ring(human, rig, z, 0.0, n=96)
        from mathutils.kdtree import KDTree
        kd = KDTree(len(P))
        for i, q in enumerate(P):
            kd.insert(tuple(map(float, q)), i)
        kd.balance()
        gaps = [kd.find(tuple(map(float, q)))[2] for q in hr]
        lift = float(np.clip(np.percentile(gaps, 50), 0.008, 0.035)) + 0.004
    base = _head_ring(human, rig, z, lift, n=96)
    # smooth the outline (a metal band has no kinks)
    for _ in range(3):
        base = (np.roll(base, 1, axis=0) + base * 2 + np.roll(base, -1, axis=0)) / 4
    c = base.mean(axis=0)
    ny = (base[:, 1] - c[1]) / (np.abs(base[:, 1] - c[1]).max() + 1e-9)
    h = height + (front - height) * np.clip(-ny, 0, 1) ** 2.5 if kind == 'stephane' else np.full(len(base), height)
    top = c + (base - c) * 1.02; top[:, 2] = z + h
    o = _loft(kind, [base, top], metal)
    s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.0015 if kind == 'stephane' else 0.004; s.offset = 1.0
    from lib import cast as _cast
    _cast.parent_to_bone(o, rig, 'head')
    return o


def fillet(human, rig, wool, lift=0.012):
    """Plain wool head-band (tainia) of priests and sacrificers: diadem(kind='fillet')."""
    return diadem(human, rig, wool, height=0.016, front=0.016, lift=lift, z_up=0.045, kind='fillet')


def earrings(human, rig, metal, drop=0.012):
    """Gold earrings: a small ring through the lobe with a hanging drop (disc- and boat-earrings with pendants
    are common Greek finds c. 500-450 BC; Persian nobles wear gold hoops on the reliefs). Head bone."""
    import bmesh
    ppos = posed_surface(human)
    head = bone_pos(rig, 'head'); ez = _eye_z(rig)
    bm = bmesh.new()
    for sgn in (1, -1):
        rel = ppos - head
        ear = (rel[:, 0] * sgn > 0.055) & (np.abs(rel[:, 1]) < 0.045) & (ppos[:, 2] < ez) & (ppos[:, 2] > ez - 0.07)
        if not ear.any():
            continue
        E = ppos[ear]
        outer = E[E[:, 0] * sgn >= np.percentile(E[:, 0] * sgn, 60)]   # the ear flap, not the cheek
        lobe = outer[np.argmin(outer[:, 2])]
        p = Vector(tuple(map(float, lobe))) + Vector((sgn * 0.001, 0, -0.003))
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.0022, matrix=Matrix.Translation(p))
        for t in np.linspace(0, 1, 6):                               # little chain of tiny links to the drop
            bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.0011,
                                      matrix=Matrix.Translation(p + Vector((0, 0, -drop * 0.6 * t))))
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.0035,
                                  matrix=Matrix.Translation(p + Vector((0, 0, -drop))))
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0032, radius2=0.0001, depth=0.006,
                              matrix=Matrix.Translation(p + Vector((0, 0, -drop - 0.005))))
    me = bpy.data.meshes.new('earrings'); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new('earrings', me)); o.data.materials.append(metal)
    for pg in o.data.polygons:
        pg.use_smooth = True
    from lib import cast as _cast
    _cast.parent_to_bone(o, rig, 'head')
    return [o]


def necklace(human, rig, metal, beads=None, drop=0.035, lift=0.007, bead_r=0.0045, spacing=0.011):
    """A bead necklace lying on the collarbones and upper chest (gold, glass and carnelian beads: very common in
    Greek and Persian graves). The loop follows the base of the neck, sinking `drop` m lower in front; beads
    only along the front half. Rides on neck01."""
    import bmesh
    ppos = posed_surface(human)
    sz = (bone_pos(rig, 'upperarm01.L')[2] + bone_pos(rig, 'upperarm01.R')[2]) / 2
    z = float(sz + 0.045)
    neck = bone_pos(rig, 'neck01')
    loop = _slice_loop(ppos, 2, z, lift, n=120, tol=0.008, mask=np.linalg.norm(ppos[:, :2] - neck[:2], axis=1) < 0.12)
    c = loop.mean(axis=0)
    fy = np.clip(-(loop[:, 1] - c[1]) / (np.abs(loop[:, 1] - c[1]).max() + 1e-9), 0, 1)
    loop[:, 2] -= drop * fy ** 1.5
    loop[:, 1] -= 0.012 * fy ** 1.5                                   # lie ON the chest as it slopes forward
    parts = [_mesh_from_curve('necklace_cord', loop, 0.0012, metal)]
    bm = bmesh.new()
    seg = np.linalg.norm(np.diff(np.vstack([loop, loop[:1]]), axis=0), axis=1)
    acc = 0.0
    for i, p in enumerate(loop):
        acc += seg[i - 1] if i else 0.0
        if fy[i] > 0.15 and acc >= spacing:
            acc = 0.0
            bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=bead_r * (1.5 if fy[i] > 0.97 else 1.0),
                                      matrix=Matrix.Translation(Vector(tuple(map(float, p)))))
    me = bpy.data.meshes.new('necklace_beads'); bm.to_mesh(me); bm.free()
    bo = link(bpy.data.objects.new('necklace_beads', me)); bo.data.materials.append(beads or metal)
    for pg in bo.data.polygons:
        pg.use_smooth = True
    parts.append(bo)
    from lib import cast as _cast
    for o in parts:
        _cast.parent_to_bone(o, rig, 'neck01')
    return parts


def sandals(human, rig, leather, sole=None):
    """Greek sandals (pedila): a flat leather sole the shape of the foot, a thong between the first two toes,
    straps across the forefoot and instep and round the ankle (Attic vases; the Delphi Charioteer's feet; the
    sandal-binder relief of the Nike temple parapet, c. 410 BC). Per foot, parented to the foot bone.
    Build at the final pose (the feet are measured where they stand)."""
    ppos = posed_surface(human)
    sole = sole or leather
    parts = []
    from lib import cast as _cast
    for side, sgn in (('L', 1), ('R', -1)):
        made = []
        ft = bone_pos(rig, f'foot.{side}')
        F = (ppos[:, 2] < ft[2] + 0.05) & (np.abs(ppos[:, 0] - ft[0]) < 0.08) & (np.abs(ppos[:, 1] - ft[1]) < 0.22)
        FP = ppos[F]
        zmin = float(FP[:, 2].min())
        low = FP[FP[:, 2] < zmin + 0.022].copy(); low[:, 2] = zmin
        out = _slice_loop(low, 2, zmin, 0.006, n=64, tol=1.0)
        top = out.copy(); top[:, 2] = zmin + 0.001
        bot = out.copy(); bot[:, 2] = zmin - 0.011
        made.append(_loft('sandal_sole.' + side, [bot, top], sole, cap_top=True))
        y_toe, y_heel = float(FP[:, 1].min()), float(FP[:, 1].max())
        Lf = y_heel - y_toe
        for f, name in ((0.27, 'strap_fore'), (0.5, 'strap_instep')):  # straps over the foot (and under the sole)
            lp = _slice_loop(FP, 1, y_toe + f * Lf, 0.0025, n=48, tol=0.005)
            if lp is not None:
                lp[:, 2] = np.maximum(lp[:, 2], zmin - 0.004)
                made.append(_mesh_from_curve(f'{name}.{side}', lp, 0.0028, leather))
        A = (np.abs(ppos[:, 0] - ft[0]) < 0.07) & (np.abs(ppos[:, 1] - ft[1]) < 0.09)
        lp = _slice_loop(ppos, 2, float(ft[2] + 0.01), 0.003, n=48, tol=0.006, mask=A)   # ankle strap
        if lp is not None:
            made.append(_mesh_from_curve('strap_ankle.' + side, lp, 0.003, leather))
            # thong: from between the first two toes up to the instep strap, then on to the ankle strap
            toe = np.array([ft[0] - sgn * 0.012, y_toe + 0.035, zmin + 0.004])
            ins = _slice_loop(FP, 1, y_toe + 0.5 * Lf, 0.0025, n=48, tol=0.005)
            if ins is not None:
                mid = ins[np.argmax(ins[:, 2])]
                ank = lp[np.argmin(lp[:, 1])]
                path = [toe + (mid - toe) * t for t in np.linspace(0, 1, 6)] + \
                       [mid + (ank - mid) * t for t in np.linspace(0.2, 1, 5)]
                made.append(_mesh_from_curve('strap_thong.' + side, path, 0.0026, leather, closed=False))
        for o in made:
            _cast.parent_to_bone(o, rig, f'foot.{side}')
        parts += made
    return parts


# ------------------------------------------------------------------ WEAR by rank
def worn_cloth(name, scan, dye, band=None, grime=0.3, patched=False, fray=0.0, patch_scan='hessian_230',
               patch_dye=None, patch_frac=0.1, seed=0, crease_dirt=True, **kw):
    """scan_cloth() plus the marks of a hard life, scaled by `grime` (crowd dye.grime: royal ~0.05 .. poor ~0.65):
      dinginess   : poorer, dirtier cloth is duller and darker overall
      crease dirt : dirt collects in folds and creases (ambient occlusion inside the shader)
      patches     : `patched` (crowd dye.patched): sewn-on rectangles of another, coarser cloth with darker
                    stitched seams, slightly raised (bump)
      frayed hem  : `fray` m of ragged hem: holes open and threads hang loose toward the edge (transparency)
    `seed` shifts where the patches fall, so two poor men are never patched alike. Extra keyword arguments
    (tiles, edge, width, sheen) go to scan_cloth()."""
    import os
    from lib.common import SCANS
    m = scan_cloth(name, scan, dye, band=band, grime=min(0.6, grime + 0.1), **kw)
    nt = m.node_tree; L = nt.links.new
    b = nt.nodes['Principled BSDF']
    col = b.inputs['Base Color'].links[0].from_socket
    uv = nt.nodes.new('ShaderNodeUVMap')
    def math_node(op, a=None, c=None, clamp=False):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        for i, v in enumerate((a, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[i].default_value = v
            else:
                L(v, n.inputs[i])
        return n.outputs[0]
    # 1. dinginess
    hs = nt.nodes.new('ShaderNodeHueSaturation')
    hs.inputs['Saturation'].default_value = 1 - 0.55 * grime; hs.inputs['Value'].default_value = 1 - 0.3 * grime
    L(col, hs.inputs['Color']); col = hs.outputs['Color']
    # 2. crease dirt
    if crease_dirt and grime > 0.08:
        ao = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.inputs['Distance'].default_value = 0.04
        k = math_node('MULTIPLY', math_node('SUBTRACT', 1.0, ao.outputs['AO']), min(1.0, 1.4 * grime))
        dm = nt.nodes.new('ShaderNodeMix'); dm.data_type = 'RGBA'; dm.blend_type = 'MULTIPLY'
        dm.inputs['B'].default_value = (0.36, 0.3, 0.24, 1)
        L(k, dm.inputs['Factor']); L(col, dm.inputs['A']); col = dm.outputs['Result']
    # 2b. stains: large soft blotches of sweat, smoke and mud (only on dirty, hard-worn cloth)
    if grime > 0.25:
        tco = nt.nodes.new('ShaderNodeTexCoord')
        bl = nt.nodes.new('ShaderNodeTexNoise'); bl.inputs['Scale'].default_value = 3.5; bl.inputs['Detail'].default_value = 4.0
        L(tco.outputs['Object'], bl.inputs['Vector'])
        ramp = nt.nodes.new('ShaderNodeMapRange'); ramp.inputs['From Min'].default_value = 0.52; ramp.inputs['From Max'].default_value = 0.68
        ramp.inputs['To Max'].default_value = min(0.85, grime * 1.2)
        L(bl.outputs['Fac'], ramp.inputs['Value'])
        sm = nt.nodes.new('ShaderNodeMix'); sm.data_type = 'RGBA'; sm.blend_type = 'MULTIPLY'
        sm.inputs['B'].default_value = (0.5, 0.42, 0.33, 1)
        L(ramp.outputs['Result'], sm.inputs['Factor']); L(col, sm.inputs['A']); col = sm.outputs['Result']
    height = None
    # 3. patches: a grid of cells over the garment's UV; a few random cells get a sewn rectangle
    if patched:
        sc = nt.nodes.new('ShaderNodeVectorMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = (10.0, 7.0, 1.0)      # ~15 cm cells around a body
        L(uv.outputs['UV'], sc.inputs[0])
        off = nt.nodes.new('ShaderNodeVectorMath'); off.operation = 'ADD'
        off.inputs[1].default_value = (seed * 0.37 % 7, seed * 0.61 % 7, 0)
        L(sc.outputs[0], off.inputs[0])
        cell = nt.nodes.new('ShaderNodeVectorMath'); cell.operation = 'FLOOR'; L(off.outputs[0], cell.inputs[0])
        loc = nt.nodes.new('ShaderNodeVectorMath'); loc.operation = 'FRACTION'; L(off.outputs[0], loc.inputs[0])
        wn = nt.nodes.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '3D'; L(cell.outputs[0], wn.inputs['Vector'])
        sel = math_node('LESS_THAN', wn.outputs['Value'], patch_frac)
        ls = nt.nodes.new('ShaderNodeSeparateXYZ'); L(loc.outputs[0], ls.inputs[0])
        def inside(sock, lo, hi):
            return math_node('MULTIPLY', math_node('GREATER_THAN', sock, lo), math_node('LESS_THAN', sock, hi))
        box = math_node('MULTIPLY', math_node('MULTIPLY', inside(ls.outputs['X'], 0.12, 0.82), inside(ls.outputs['Y'], 0.1, 0.7)), sel)
        inner = math_node('MULTIPLY', math_node('MULTIPLY', inside(ls.outputs['X'], 0.135, 0.805),
                                                inside(ls.outputs['Y'], 0.115, 0.685)), sel)
        seam = math_node('SUBTRACT', box, inner)
        # patch cloth: another (coarser) scanned weave, in its own duller colour
        d = os.path.join(SCANS, patch_scan)
        f = next((x for x in os.listdir(d) if '_diff_' in x), None) if os.path.isdir(d) else None
        # leftover cloth of another colour: darker undyed wool, faded brown, a scrap of old madder
        pd = patch_dye or [(0.2, 0.16, 0.11), (0.3, 0.24, 0.16), (0.24, 0.17, 0.11)][seed % 3]
        pc = nt.nodes.new('ShaderNodeMix'); pc.data_type = 'RGBA'; pc.blend_type = 'MULTIPLY'; pc.inputs['Factor'].default_value = 1.0
        pc.inputs['B'].default_value = (*pd, 1)
        if f:
            ptex = nt.nodes.new('ShaderNodeTexImage'); ptex.image = bpy.data.images.load(os.path.join(d, f), check_existing=True)
            pm = nt.nodes.new('ShaderNodeVectorMath'); pm.operation = 'MULTIPLY'; pm.inputs[1].default_value = (14.0, 20.0, 1.0)
            L(uv.outputs['UV'], pm.inputs[0]); L(pm.outputs[0], ptex.inputs['Vector'])
            bw = nt.nodes.new('ShaderNodeRGBToBW'); L(ptex.outputs['Color'], bw.inputs['Color'])
            lift = nt.nodes.new('ShaderNodeMapRange'); lift.inputs['To Min'].default_value = 0.5; lift.inputs['To Max'].default_value = 1.3
            L(bw.outputs['Val'], lift.inputs['Value']); L(lift.outputs['Result'], pc.inputs['A'])
        else:
            pc.inputs['A'].default_value = (1, 1, 1, 1)
        pm2 = nt.nodes.new('ShaderNodeMix'); pm2.data_type = 'RGBA'
        L(inner, pm2.inputs['Factor']); L(col, pm2.inputs['A']); L(pc.outputs['Result'], pm2.inputs['B'])
        st = nt.nodes.new('ShaderNodeMix'); st.data_type = 'RGBA'; st.blend_type = 'MULTIPLY'
        st.inputs['B'].default_value = (0.35, 0.3, 0.25, 1)
        L(seam, st.inputs['Factor']); L(pm2.outputs['Result'], st.inputs['A'])
        col = st.outputs['Result']
        height = math_node('ADD', math_node('MULTIPLY', inner, 0.5), seam)
    L(col, b.inputs['Base Color'])
    if height is not None:                                            # raised patch + stitched seam
        bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.6; bump.inputs['Distance'].default_value = 0.002
        L(height, bump.inputs['Height'])
        if b.inputs['Normal'].is_linked:
            L(b.inputs['Normal'].links[0].from_socket, bump.inputs['Normal'])
        L(bump.outputs['Normal'], b.inputs['Normal'])
    # 4. frayed hem: holes and loose threads toward v = 0 (the hem)
    if fray > 0:
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs[0])
        th = nt.nodes.new('ShaderNodeVectorMath'); th.operation = 'MULTIPLY'; th.inputs[1].default_value = (160.0, 14.0, 1.0)
        L(uv.outputs['UV'], th.inputs[0])
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 3.0
        L(th.outputs[0], nz.inputs['Vector'])                         # long thin noise streaks = threads
        big = nt.nodes.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 25.0
        L(uv.outputs['UV'], big.inputs['Vector'])
        ln = math_node('MULTIPLY_ADD', big.outputs['Fac'], fray * 1.2)  # ragged: the fray depth varies along the hem
        ln.node.inputs[2].default_value = fray * 0.3
        e = math_node('DIVIDE', sep.outputs['Y'], ln, clamp=True)       # 0 at the hem edge -> 1 above the fray
        thr = math_node('MULTIPLY_ADD', e, 0.75); thr.node.inputs[2].default_value = 0.4
        keep = math_node('LESS_THAN', nz.outputs['Fac'], thr)
        out = next(x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL')
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mx = nt.nodes.new('ShaderNodeMixShader')
        L(keep, mx.inputs['Fac']); L(tr.outputs[0], mx.inputs[1]); L(b.outputs[0], mx.inputs[2])
        L(mx.outputs[0], out.inputs['Surface'])
    return m


RANK_SCAN = {'royal': 'rough_linen', 'rich': 'rough_linen', 'common': 'rough_linen', 'poor': 'hessian_230'}
RANK_FRAY = {'royal': 0.0, 'rich': 0.0, 'common': 0.012, 'poor': 0.035}


def crowd_cloth(name, dye, wool=False, scan=None, seed=0, ornament=None):
    """Garment material for a crowd extra, straight from tc/crowd.py person()['dye'] =
    {rank, main, band, grime, patched}: the rank picks the cloth (linen / wool for the better-off, a coarse
    hessian-like weave for the poor), how ragged the hem is, whether there is a woven border; grime and patches
    come from the person's own seed. wool=True for mantles and peploi."""
    rank = dye.get('rank', 'common')
    if scan is None:
        scan = 'caban' if (wool and rank != 'poor') else RANK_SCAN.get(rank, 'rough_linen')
    band = tuple(dye['band']) if dye.get('band') and rank in ('royal', 'rich') else None
    tiles = (4, 10) if scan == 'caban' else (7, 5)
    border, field = ornament or (None, None)
    if (border or field) and not dye.get('patched'):                  # woven ornament (see ornament_for())
        r = __import__('random').Random(f'orn-col:{seed}:{name}')
        band = band or tuple(dye.get('band') or (0.07, 0.10, 0.26))
        dark = (0.04, 0.03, 0.025); ochre = (0.5, 0.34, 0.1)
        return patterned_cloth(name, scan, tuple(dye['main']), band=band, border=border,
                               border_color=r.choice((dark, tuple(dye['main']), ochre)), field=field,
                               field_color=r.choice((dark, band, ochre)), grime=float(dye.get('grime', 0.3)),
                               tiles=tiles, width=0.07, sheen=0.15)
    return worn_cloth(name, scan, tuple(dye['main']), band=band, grime=float(dye.get('grime', 0.3)),
                      patched=bool(dye.get('patched', False)), fray=RANK_FRAY.get(rank, 0.0), seed=seed,
                      tiles=tiles, width=0.035, sheen=0.15 if rank != 'poor' else 0.05)


# ------------------------------------------------------------------ PATTERNS: woven / painted cloth ornament
# Greek dress on vases is rarely plain: borders of meander (Greek key), running waves, zigzags and tongues, and
# whole garments strewn with dots, crosses or stars (e.g. the Francois Vase, Exekias, the Berlin Painter's women).
# The Persian court wore patterned robes too (Susa glazed-brick archers: rosettes in squares, stars, "castle"
# motifs). Each motif is DRAWN BY CODE into a small tileable mask image (numpy -> Blender image, no AI, no
# copying): 1 = ornament, 0 = background. The materials then tile the masks along the hem or across the cloth.

def _grid_mask(rows, res=256):
    """Pixel-art motif (list of strings, '#' = ornament) scaled up to a res x res mask."""
    h, w = len(rows), len(rows[0])
    a = np.array([[1.0 if ch == '#' else 0.0 for ch in r] for r in rows], dtype=np.float32)
    ys = (np.arange(res) * h // res); xs = (np.arange(res) * w // res)
    return a[ys][:, xs]


def pattern_mask(kind, res=256):
    """Tileable ornament mask (res x res, float 0..1), row 0 = bottom of the tile.
    Borders (drawn for a band: x along the hem, y across it):
      meander  Greek key, framed by two lines        wave     running wave (Vitruvian scroll)
      zigzag   framed zigzag                         tongues  row of rounded tongues (egg pattern)
      lines    two thin stripes
    Fields (strewn over the whole cloth):
      dots, crosses, stars (8 points), rosettes (8 petals), rosette_grid (Susa: rosette in a square frame),
      checker, stripes"""
    y, x = np.mgrid[0:res, 0:res].astype(np.float32) / res
    if kind == 'meander':
        m = _grid_mask(['##########',
                        '..........',
                        '#######.#.',
                        '#.....#.#.',
                        '#.###.#.#.',
                        '#.#.#...#.',
                        '#.#.#####.',
                        '#.#.......',
                        '..........',
                        '##########'][::-1], res)
    elif kind == 'wave':
        # running wave (Vitruvian scroll): each wave rises as a slope, rolls over into a round crest with a
        # spiral hollow, and the next wave starts from its foot
        def disc(cx, cy, r):
            return np.hypot(x - cx, y - cy) < r
        ramp = (y < 0.18 + 0.9 * x) & (x < 0.62) & ~disc(0.66, 0.53, 0.12)
        crest = disc(0.62, 0.5, 0.27) & ~disc(0.66, 0.53, 0.12) & ~((x > 0.64) & (y < 0.5) & (x < 0.95))
        m = (y < 0.2) | ramp | crest | disc(0.66, 0.53, 0.04)
        m = (m & (y > 0.08)) | (y < 0.05) | (y > 0.95)
    elif kind == 'zigzag':
        tri = np.abs((x * 2) % 2 - 1)
        m = (np.abs(y - (0.25 + 0.5 * tri)) < 0.09) | (y < 0.06) | (y > 0.94)
    elif kind == 'tongues':
        cx = (x % 1.0) - 0.5
        m = ((np.abs(cx) < 0.36) & (y > 0.15) & ((y < 0.6) | (np.hypot(cx, y - 0.6) < 0.36))) | (y < 0.07)
    elif kind == 'lines':
        m = (np.abs(y - 0.25) < 0.08) | (np.abs(y - 0.75) < 0.08)
    else:
        cx, cy = x - 0.5, y - 0.5
        r, th = np.hypot(cx, cy), np.arctan2(cy, cx)
        if kind == 'dots':
            m = r < 0.13
        elif kind == 'crosses':
            m = ((np.abs(cx) < 0.04) & (np.abs(cy) < 0.2)) | ((np.abs(cy) < 0.04) & (np.abs(cx) < 0.2))
        elif kind == 'stars':
            m = r < 0.09 + 0.16 * np.abs(np.cos(4 * th)) ** 3
        elif kind == 'rosettes':
            m = (r < 0.27 * (0.55 + 0.45 * np.abs(np.cos(4 * th)))) & ~((r > 0.07) & (r < 0.1))
        elif kind == 'rosette_grid':
            frame = (np.abs(cx) > 0.42) | (np.abs(cy) > 0.42)
            m = frame | (r < 0.3 * (0.55 + 0.45 * np.abs(np.cos(4 * th))))
        elif kind == 'checker':
            m = ((x * 2).astype(int) + (y * 2).astype(int)) % 2 == 0
        elif kind == 'stripes':
            m = (x % 0.5) < 0.18
        else:
            raise KeyError(f'unknown pattern {kind!r}')
    m = np.asarray(m, dtype=np.float32)
    # soften the edges a little (woven / painted, not laser-cut): 3x3 box blur, wrapping (tileable)
    m = (m + np.roll(m, 1, 0) + np.roll(m, -1, 0) + np.roll(m, 1, 1) + np.roll(m, -1, 1)) / 5
    return m


BORDERS = ('meander', 'wave', 'zigzag', 'tongues', 'lines')
FIELDS = ('dots', 'crosses', 'stars', 'rosettes', 'rosette_grid', 'checker', 'stripes')


def _pattern_image(kind, res=256):
    name = f'tc_pattern_{kind}'
    im = bpy.data.images.get(name)
    if im is None:
        import os, tempfile
        m = pattern_mask(kind, res)
        tmp = bpy.data.images.new(name + '_draw', res, res, alpha=False, float_buffer=False)
        px = np.ones((res, res, 4), dtype=np.float32); px[..., 0] = px[..., 1] = px[..., 2] = m
        tmp.pixels.foreach_set(px.ravel()); tmp.update()
        # an image filled in memory is NOT seen by Cycles (it renders the blank 'generated' image): save it as a
        # PNG in the temp folder, load that file as a normal image, and pack it into the .blend
        path = os.path.join(bpy.app.tempdir or tempfile.gettempdir(), name + '.png')
        tmp.filepath_raw = path; tmp.file_format = 'PNG'; tmp.save()
        bpy.data.images.remove(tmp)
        im = bpy.data.images.load(path, check_existing=False); im.name = name
        im.colorspace_settings.name = 'Non-Color'
        im.pack()
        im.use_fake_user = True
    return im


def patterned_cloth(name, scan, dye, band=None, border=None, border_color=None, border_repeat=36, width=0.07,
                    field=None, field_color=None, field_repeat=(16, 22), edge=0.0, **kw):
    """scan_cloth() + ornament:
      band + border : a woven border band of colour `band` along the hem (or all edges with edge=1) carrying a
                      pattern (meander, wave, ...) in `border_color` (default: the main dye), repeated
                      `border_repeat` times around the garment, `width` = band height in UV
      field         : a strewn pattern over the whole cloth (dots, stars, ...) in `field_color`
    The real weave of the scan shows through all colours (they are multiplied by the weave's light/dark)."""
    m = scan_cloth(name, scan, dye, band=None, edge=edge, width=width, **kw)
    nt = m.node_tree; L = nt.links.new
    b = nt.nodes['Principled BSDF']
    mixer = b.inputs['Base Color'].links[0].from_node                   # the grime mix: input A = dyed weave
    dyed_sock = mixer.inputs['A'].links[0].from_socket
    diff = next(n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and '_diff_' in n.image.name)
    bw = nt.nodes.new('ShaderNodeRGBToBW'); L(diff.outputs['Color'], bw.inputs['Color'])
    weave = nt.nodes.new('ShaderNodeMapRange'); weave.inputs['To Min'].default_value = 0.55; weave.inputs['To Max'].default_value = 1.25
    L(bw.outputs['Val'], weave.inputs['Value'])
    def woven(color):                                                   # a flat colour with the scan's weave in it
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
        L(weave.outputs['Result'], mx.inputs['A']); mx.inputs['B'].default_value = (*color, 1)
        return mx.outputs['Result']
    def sample(kind, vec):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = _pattern_image(kind); t.interpolation = 'Linear'
        L(vec, t.inputs['Vector'])
        return t.outputs['Color']
    def mix(fac, a, c):
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        L(fac, mx.inputs['Factor']); L(a, mx.inputs['A']); L(c, mx.inputs['B'])
        return mx.outputs['Result']
    uv = nt.nodes.new('ShaderNodeUVMap')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uv.outputs['UV'], sep.inputs[0])
    col = dyed_sock
    if field:
        fv = nt.nodes.new('ShaderNodeVectorMath'); fv.operation = 'MULTIPLY'; fv.inputs[1].default_value = (*field_repeat, 1)
        L(uv.outputs['UV'], fv.inputs[0])
        f = sample(field, fv.outputs[0])
        col = mix(f, col, woven(field_color or (0.05, 0.04, 0.03)))
    if band is not None:
        # distance to the band edge (hem: v; edge mode: nearest of the 4 sheet edges) and position along it
        if edge:
            pu = nt.nodes.new('ShaderNodeMath'); pu.operation = 'PINGPONG'; pu.inputs[1].default_value = 0.5
            pv = nt.nodes.new('ShaderNodeMath'); pv.operation = 'PINGPONG'; pv.inputs[1].default_value = 0.5
            L(sep.outputs['X'], pu.inputs[0]); L(sep.outputs['Y'], pv.inputs[0])
            dist = nt.nodes.new('ShaderNodeMath'); dist.operation = 'MINIMUM'; L(pu.outputs[0], dist.inputs[0]); L(pv.outputs[0], dist.inputs[1])
            along = nt.nodes.new('ShaderNodeMath'); along.operation = 'ADD'; L(sep.outputs['X'], along.inputs[0]); L(sep.outputs['Y'], along.inputs[1])
            d_sock, a_sock = dist.outputs[0], along.outputs[0]
        else:
            d_sock, a_sock = sep.outputs['Y'], sep.outputs['X']
        inb = nt.nodes.new('ShaderNodeMath'); inb.operation = 'LESS_THAN'; inb.inputs[1].default_value = width
        L(d_sock, inb.inputs[0])
        band_col = woven(band)
        if border:
            au = nt.nodes.new('ShaderNodeMath'); au.operation = 'MULTIPLY'; au.inputs[1].default_value = border_repeat
            L(a_sock, au.inputs[0])
            av = nt.nodes.new('ShaderNodeMath'); av.operation = 'DIVIDE'; av.inputs[1].default_value = width
            L(d_sock, av.inputs[0])
            comb = nt.nodes.new('ShaderNodeCombineXYZ'); L(au.outputs[0], comb.inputs['X']); L(av.outputs[0], comb.inputs['Y'])
            pat = sample(border, comb.outputs[0])
            band_col = mix(pat, band_col, woven(border_color or dye))
        col = mix(inb.outputs[0], col, band_col)
    L(col, mixer.inputs['A'])
    return m


def ornament_for(rank, seed, wardrobe=''):
    """Era-plausible ornament choice for a crowd extra: (border, field) or Nones. Rich and royal cloth carries
    woven borders, women's and royal garments often an all-over strewn pattern; the poor wear plain cloth.
    Persian robes favour rosettes and rosette grids (Susa), Greek ones meanders, waves and dots."""
    import random
    r = random.Random(f'ornament:{seed}:{wardrobe}')
    persian = wardrobe.startswith('persian')
    if rank == 'poor':
        return None, None
    if rank == 'common':
        return (r.choice(('lines', 'zigzag')) if r.random() < 0.35 else None), None
    border = r.choice(('rosette_grid', 'lines', 'zigzag') if persian else ('meander', 'wave', 'tongues', 'meander', 'zigzag'))
    if border == 'rosette_grid':
        border = 'lines'
    field = None
    if r.random() < (0.7 if rank == 'royal' else 0.35):
        field = r.choice(('rosettes', 'rosette_grid', 'stars') if persian else ('dots', 'crosses', 'stars', 'dots'))
    return border, field


# ------------------------------------------------------------------ more Greek garments + hats
def chlamys(human, rig, material, length=0.85, frames=55, seg=112, ring_h=0.016, sim=True):
    """The CHLAMYS: a short wool cloak, a rectangle fastened with a brooch on the RIGHT shoulder, covering the left
    arm and the back and hanging open down the right side (travellers, riders, hunters, heralds, ephebes; Hermes
    and the Parthenon frieze horsemen, Attic vases). Built as a cape around the shoulders whose top edge lies on
    the shoulders/upper chest (soft pins), hard-pinned at the right shoulder where the two edges meet, OPEN on the
    right side. POSED garment (body still, over frozen tunic). Fasten with dress_pins(kind='fibula')."""
    ppos = posed_surface(human)
    rest = cast_rest(human)
    M = body_measure(human, rig, rest)
    cy = M['cy']
    sz = M['shoulder_z']
    crx, cry = _chest(ppos, M, sz - 0.05)
    R, Ry = crx + 0.07, cry + 0.07
    pin_a = math.pi                                                   # the RIGHT side (-x) is where it opens
    rows = int(length / ring_h) + 1
    verts, pins = [], []
    for r in range(rows):
        z = sz + 0.03 - r * ring_h
        grow = 1 + 0.18 * (r / (rows - 1))                            # the cloak widens a little as it falls
        for k in range(seg):
            a = pin_a + 2 * math.pi * (k + 0.5) / seg                 # start and end at the right shoulder
            x, y = R * grow * math.cos(a), cy + Ry * grow * math.sin(a)
            w = 0.0
            if r == 0:
                # top edge lies on the shoulders and around the neck base, softly; hard at the right shoulder pin
                x, y = x * 0.75, cy + (y - cy) * 0.8
                if abs(x) < 0.09:                                     # across the throat / upper back: on the
                    z = sz - (0.02 if y < cy else 0.0)                # collarbones, lying on the body surface
                    sy = surface_y(ppos, x, z, front=y < cy)
                    if sy is not None:
                        y = sy + (-0.012 if y < cy else 0.012)
                else:
                    st = shoulder_top(ppos, x, cy, sz + 0.085)
                    if st is not None:
                        z = st + 0.012
                frac = min(k, seg - 1 - k) / (seg / 2)                 # 0 at the pin -> 1 opposite it
                # hard pin at the brooch; the top edge rests on the shoulders (soft) but hangs free across the
                # front of the chest, so the open side can fall away from the right arm
                front = y < cy - 0.02 and abs(x) < 0.12
                w = 1.0 if frac < 0.05 else (0.08 if front else 0.4)
            verts.append((x, y, z)); pins.append(w)
    faces = [(r * seg + k, r * seg + k + 1, (r + 1) * seg + k + 1, (r + 1) * seg + k)
             for r in range(rows - 1) for k in range(seg - 1)]       # no face across the opening
    me = bpy.data.meshes.new('chlamys'); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new('chlamys', me)); o.data.materials.append(material)
    set_uv(o, [((i % seg) / (seg - 1), 1 - (i // seg) / (rows - 1)) for i in range(len(verts))])
    vg = o.vertex_groups.new(name='pin')
    for i, w in enumerate(pins):
        if w:
            vg.add([i], w, 'REPLACE')
    cm = _cloth(o, 'pin', mass=0.22, tension=14, bending=0.1)        # soft wool: falls in folds, not a tent
    cm.settings.quality = 10; cm.collision_settings.distance_min = 0.008; cm.collision_settings.collision_quality = 4
    _finish(o, 0.0035, offset=1.0)
    if sim:
        _sim_freeze([o], frames)
    return o


def cast_rest(human):
    from lib import cast as _cast
    return _cast.rest_surface(human)[0]


def greek_hat(human, rig, material, kind='petasos', lift=0.012):
    """Greek headwear (rigid, parented to the head bone):
      petasos : broad-brimmed felt or straw travel hat with a low crown (travellers, herdsmen, riders, Hermes;
                worn with the chlamys on the Parthenon frieze)
      pilos   : a brimless conical felt cap (workers, sailors, craftsmen; Odysseus and Hephaistos on vases)
      sakkos  : a women's cloth bag holding the hair up at the back of the head (Attic red-figure women)"""
    ppos = posed_surface(human)
    ez = _eye_z(rig)
    zb = ez + (0.055 if kind == 'petasos' else 0.05 if kind == 'pilos' else 0.02)
    base = _head_ring(human, rig, zb, lift, ppos=ppos)
    c = base.mean(axis=0)
    if kind == 'petasos':
        rings = []
        for k, dz in ((1.0, 0.0), (1.0, 0.04), (0.85, 0.07), (0.5, 0.085)):   # low rounded crown
            ring = c + (base - c) * k; ring[:, 2] = zb + dz; rings.append(ring)
        crown = _loft('petasos_crown', rings, material, cap_top=True)
        th = np.arctan2(base[:, 1] - c[1], base[:, 0] - c[0])
        d = base - c; d[:, 2] = 0; d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9
        brim_in = base.copy(); brim_in[:, 2] = zb + 0.004
        brim_out = base + d * (0.11 + 0.01 * np.cos(2 * th))[:, None]
        brim_out[:, 2] = zb - 0.012 - 0.01 * np.abs(np.sin(th))      # droops a little front and back
        brim = _loft('petasos_brim', [brim_in, brim_out], material)
        parts = [crown, brim]
        for o in parts:
            s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.004; s.offset = 1.0
            o.modifiers.new('smooth', 'SUBSURF').levels = 1
    elif kind == 'pilos':
        rings = []
        for t in np.linspace(0, 1, 10):
            k = (1 - t) ** 0.9 * 1.0 + 0.04
            ring = c + (base - c) * k; ring[:, 2] = zb + 0.16 * t; ring[:, 1] += 0.01 * t * t
            rings.append(ring)
        o = _loft('pilos', rings, material, cap_top=True)
        s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.004; s.offset = 1.0
        parts = [o]
    elif kind == 'sakkos':
        # a soft bag: from a band round the head it swells into a rounded bundle at the back of the head
        head = bone_pos(rig, 'head')
        th = np.arctan2(base[:, 1] - c[1], base[:, 0] - c[0])
        back = np.clip(np.sin(th), 0, 1)                              # +y = back
        rings = []
        for t in np.linspace(0, 1, 14):
            # a ROUND soft bag: follows the head's own curve up to the crown (cosine profile, no point), and
            # swells into a bundle of hair at the back of the head that sags a little
            dome = np.cos(t * np.pi / 2) ** 0.7
            bulge = 1.06 + 0.6 * back * np.sin(np.pi * t) ** 1.2
            k = dome * bulge + 0.02
            ring = c + (base - c) * k[:, None]
            ring[:, 2] = zb + 0.105 * np.sin(t * np.pi / 2) - 0.035 * back * np.sin(np.pi * t)
            ring[:, 1] += 0.06 * back * np.sin(np.pi * t)
            rings.append(ring)
        o = _loft('sakkos', rings, material, cap_top=True)
        s = o.modifiers.new('thick', 'SOLIDIFY'); s.thickness = 0.003; s.offset = 1.0
        o.modifiers.new('smooth', 'SUBSURF').levels = 1
        parts = [o]
    else:
        raise KeyError(kind)
    from lib import cast as _cast
    for o in parts:
        _cast.parent_to_bone(o, rig, 'head')
    return parts


def perizoma(human, rig, pos, material, frames=40, seg=96, sim=True):
    """The PERIZOMA: a short loincloth wrapped round the hips, worn by fishermen, rowers, farm hands and athletes'
    trainers in heat and hard work (Attic vases of fishermen and of men at the rowing benches; Thucydides 1.6 on
    loincloths). A short tube from the hip bones to the upper thigh, tight at the top (tucked waist band).
    Body must be blending into its pose (pose.blend_into_pose)."""
    M = body_measure(human, rig, pos)
    cy = M['cy']
    top = M['hip_z'] + 0.07
    hrx, hry = _chest(pos, M, M['hip_z'])
    wrx, wry = hrx + 0.012, hry + 0.012
    def top_fn(a):
        return (wrx * math.cos(a), cy + wry * math.sin(a), top, 1.0)
    o = _column_tube('perizoma', seg, top_fn, top - 0.03, lambda a: M['hip_z'] - 0.2 + 0.04 * abs(math.sin(a)),
                     lambda a, z: (wrx * math.cos(a), cy + wry * math.sin(a)),
                     lambda a, z, t: ((wrx + 0.03 * t) * math.cos(a), cy + (wry + 0.03 * t) * math.sin(a)),
                     lambda a: (wrx * math.cos(a), cy + wry * math.sin(a)), 0.012, material)
    _cloth(o, 'pin', mass=0.1, tension=12, bending=0.15).settings.quality = 8
    _finish(o, 0.003)
    if sim:
        _sim_freeze([o], frames)
    return o


def purse(rig, leather, side='L', name='purse'):
    """A small leather money pouch hanging from the belt (traders, shoppers: coins were also carried in the mouth,
    Aristophanes, Wasps 791!). A soft bag shape tied at the neck, on the hip bone."""
    import bmesh
    hip = bone_pos(rig, f'upperleg01.{side}')
    sgn = 1 if side == 'L' else -1
    p = Vector((float(hip[0]) + sgn * 0.13, float(hip[1]) - 0.04, float(hip[2]) + 0.06))
    bm = bmesh.new()
    prof = [(0.001, -0.07), (0.035, -0.06), (0.045, -0.03), (0.035, 0.0), (0.012, 0.012), (0.018, 0.02)]
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new(p + Vector((r * math.cos(2 * math.pi * k / 16), r * 0.7 * math.sin(2 * math.pi * k / 16), z)))
                      for k in range(16)])
    for a, b in zip(rings[:-1], rings[1:]):
        for k in range(16):
            bm.faces.new((a[k], a[(k + 1) % 16], b[(k + 1) % 16], b[k]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.data.materials.append(leather)
    for pg in o.data.polygons:
        pg.use_smooth = True
    from lib import cast as _cast
    _cast.parent_to_bone(o, rig, 'spine05')
    return o


# ------------------------------------------------------------------ DRESS A CROWD EXTRA (tc/crowd.py person -> clothes)
# tc/crowd.py gives every generated person a 'wardrobe' name (the manifests in library/wardrobe/) and a 'dye' dict
# (rank, main colour, border colour, grime, patched). dress() turns that into simulated clothes in one call, so the
# crowd builder (WS2) and the shot pipeline (WS10) never need to know which garment functions make which outfit.
# Each outfit follows the same recipe as its test still (blender/scenes/ws3_wardrobe.py, xerxes_v2.py).

GREEK_WARDROBES = ('greek_civilian_480bc', 'greek_woman_480bc', 'greek_child_480bc', 'greek_servant_480bc',
                   'greek_priest_480bc', 'greek_priestess_480bc', 'greek_hoplite_480bc')
PERSIAN_WARDROBES = ('persian_king_480bc', 'persian_court_480bc', 'persian_servant_480bc', 'persian_soldier_480bc',
                     'persian_immortal_480bc', 'persian_woman_480bc')
WARDROBES = GREEK_WARDROBES + PERSIAN_WARDROBES


def _ensure_poses():
    """Two standing poses the garments are tuned for (added at run time; pose.py belongs to WS5):
      stand_open     : arms hanging a little away from the body (hands clear of the hips, skirts fall between)
      royal_audience : upper arms out, forearms raised forward (Persepolis audience pose; room for wide sleeves)"""
    from lib import pose as _pose
    P = _pose.POSES
    P.setdefault('stand_open', {**P['stand_relaxed'],
                                "upperarm01.R": (-0.22, 0.02, -1), "lowerarm01.R": (-0.1, -0.14, -1),
                                "upperarm01.L": (0.22, 0.02, -1), "lowerarm01.L": (0.1, -0.14, -1)})
    P.setdefault('royal_audience', {**P['stand_relaxed'],
                                    "upperarm01.R": (-0.5, -0.22, -1), "lowerarm01.R": (-0.12, -1, 0.3),
                                    "upperarm01.L": (0.5, -0.22, -1), "lowerarm01.L": (0.12, -1, 0.12),
                                    "_fingers": 0.6})
    return _pose


def _metal(name, color, rough):
    from lib.common import principled
    m = bpy.data.materials.get(name)
    if m is None:
        m = principled(name, color, metal=1.0, rough=rough, bump=0.02, bump_scale=300); m.use_fake_user = True
    return m


def dress(human, rig, pos, person, pose_name=None, tools=True):
    """Dress one person from tc/crowd.py (or a library/cast spec with 'wardrobe' + 'dye').
    human, rig  = cast.build_human(spec); pos = cast.rest_surface(human)[0]; the body should be at rest.
    pose_name   = final pose (default: 'stand_open' for Greeks, 'royal_audience' for the Persian robe, else
                  'stand_open'). The body ends in that pose, still. Returns the list of garment/accessory objects.
    The person's own seed decides small choices (a married woman's veil, which jewellery), so two extras of the
    same rank are never dressed alike; cloth colour/wear come from person['dye'] through crowd_cloth()."""
    from lib import pose as _pose
    _ensure_poses()
    w = person.get('wardrobe') or 'greek_civilian_480bc'
    if w not in WARDROBES:
        raise KeyError(f'no 480 BC garments for wardrobe {w!r} (yet): known {WARDROBES}')
    dye = person.get('dye') or {"rank": "common", "main": (0.52, 0.47, 0.37), "band": None, "grime": 0.3, "patched": False}
    seed = int(person.get('seed', 0)); rank = dye.get('rank', 'common')
    role = person.get('role', '')                                     # fisherman, farmer, trader... (tc/crowd.py)
    female = (person.get('macro') or {}).get('gender', 1.0) < 0.5
    tag = f'{w}_{seed}'
    border, field = ornament_for(rank, seed, w)                       # woven borders / strewn patterns by rank
    main = crowd_cloth(tag + '_main', dye, seed=seed, ornament=(border, None))           # tunics (linen / coarse)
    wool = crowd_cloth(tag + '_wool', dye, wool=True, seed=seed + 1, ornament=(border, field))   # mantles, peplos
    bronze = _metal('pin_bronze', (0.55, 0.36, 0.16), 0.35)
    gold = _metal('jewel_gold', (0.92, 0.66, 0.26), 0.22)
    leather = bpy.data.materials.get('sandal_leather')
    if leather is None:
        from lib.common import principled
        leather = principled('sandal_leather', (0.16, 0.08, 0.04), rough=0.6, bump=0.15, bump_scale=120)
        leather.use_fake_user = True
    add_collision(human)
    before = set(bpy.data.objects)
    wealthy = rank in ('royal', 'rich')

    if w in GREEK_WARDROBES:
        pn = pose_name or 'stand_open'
        _pose.blend_into_pose(rig, pn, start=1, end=15)            # 'blend' garments: simulated as the body poses
        def settle():
            rig.animation_data_clear(); _pose.apply_pose(rig, pn)
        if w == 'greek_woman_480bc' and seed % 2 == 1:
            # IONIC look (the commonest Classical women's dress): long linen chiton + wool himation diagonally
            ch = chiton(human, rig, pos, main, length='ankle')
            _sim_freeze([ch], 45)
            settle()
            if seed % 3 == 1:                                         # hair up in a sakkos, mantle on the shoulder
                hm = himation(human, rig, pos, wool, side='L', over=ch)
                _sim_freeze([hm], 60)
                greek_hat(human, rig, crowd_cloth(tag + '_sakkos', {**dye, "main": tuple(dye.get('band') or (0.3, 0.05, 0.035))},
                                                  seed=seed), kind='sakkos')
            else:
                veil(human, rig, wool)
            if wealthy or seed % 2 == 0:
                earrings(human, rig, gold)
            if wealthy:
                necklace(human, rig, gold)
        elif w == 'greek_woman_480bc':
            body, over = peplos(human, rig, pos, wool)
            settle()
            belt(rig, over, main)
            dress_pins(over, rig, gold if wealthy else bronze, per_side=1)
            if wealthy or seed % 2 == 0:
                earrings(human, rig, gold)
            if wealthy:
                necklace(human, rig, gold)
            if seed % 3 != 1:                                         # most women outdoors draw the mantle over the head
                veil(human, rig, crowd_cloth(tag + '_veil', {**dye, "main": (0.5, 0.46, 0.38)}, wool=True, seed=seed + 2))
        elif w == 'greek_servant_480bc' and role in ('fisherman', 'rower') and seed % 2 == 0:
            # at the oars or the nets: just a loincloth, a felt pilos against the sun for the fishermen
            perizoma(human, rig, pos, main)
            settle()
            if role == 'fisherman':
                greek_hat(human, rig, crowd_cloth(tag + '_pilos', {**dye, "patched": False}, wool=True, seed=seed), kind='pilos')
        elif w == 'greek_servant_480bc':
            ex = exomis(human, rig, pos, main)
            settle()
            belt(rig, ex, main)
            dress_pins(ex, rig, bronze, kind='fibula', per_side=1)
            if role in ('fisherman', 'rower', 'potter', 'smith') or seed % 3 == 0:
                greek_hat(human, rig, crowd_cloth(tag + '_pilos', {**dye, "patched": False}, wool=True, seed=seed), kind='pilos')
            elif role in ('farmer', 'shepherd'):
                greek_hat(human, rig, crowd_cloth(tag + '_hat', {**dye, "main": (0.4, 0.31, 0.18), "patched": False},
                                                  wool=True, seed=seed), kind='petasos')
        elif w == 'greek_child_480bc':
            t = child_tunic(human, rig, pos, main)
            settle()
            belt(rig, t, wool, max_r=0.13)
        elif w in ('greek_priest_480bc', 'greek_priestess_480bc'):
            white = crowd_cloth(tag + '_white', {**dye, "main": (0.6, 0.57, 0.5), "grime": 0.05, "patched": False}, seed=seed)
            pale = crowd_cloth(tag + '_pale', {**dye, "main": (0.5, 0.46, 0.38), "grime": 0.05, "patched": False}, wool=True, seed=seed)
            ch, mantle = priest_robes(human, rig, pos, white, pale, pose_name=pn, female=female)
            if female:
                diadem(human, rig, gold, front=0.03, over=mantle); earrings(human, rig, gold); necklace(human, rig, gold)
            else:
                fillet(human, rig, pale)
        elif w == 'greek_civilian_480bc' and rank == 'poor':          # a working man: exomis + felt pilos
            ex = exomis(human, rig, pos, main)
            settle()
            belt(rig, ex, main)
            if seed % 2 == 0:
                greek_hat(human, rig, crowd_cloth(tag + '_felt', {**dye, "patched": False}, wool=True, seed=seed), kind='pilos')
        else:                                                         # civilian / hoplite: chiton (+ mantle)
            ch = chiton(human, rig, pos, main, length='knee')
            _sim_freeze([ch], 45)
            settle()
            if w == 'greek_civilian_480bc' and seed % 3 == 0:         # a traveller / rider: chlamys + petasos
                cl = chlamys(human, rig, wool)
                dress_pins(cl, rig, bronze, kind='fibula', per_side=1)
                greek_hat(human, rig, crowd_cloth(tag + '_hat', {**dye, "main": (0.36, 0.28, 0.17), "patched": False},
                                                  wool=True, seed=seed), kind='petasos')
            elif w == 'greek_civilian_480bc':                          # a citizen in his himation
                m = himation(human, rig, pos, wool, side='L', over=ch)
                _sim_freeze([m], 60)
            if role in ('trader', 'merchant', 'shopper') or (w == 'greek_civilian_480bc' and seed % 4 == 1):
                purse(rig, leather)                                   # money pouch at the hip
            # hoplite armour (helmet, cuirass, greaves, shield) is WS4's armour.py, added on top by the caller
        if rank != 'poor' and w != 'greek_child_480bc':
            sandals(human, rig, leather)
    else:
        robe_outfit = w in ('persian_king_480bc', 'persian_immortal_480bc', 'persian_woman_480bc')
        pn = pose_name or ('royal_audience' if w == 'persian_king_480bc' else 'stand_open')
        _pose.apply_pose(rig, pn)                                     # 'posed' garments: body still, cloth falls
        trousers(human, rig, crowd_cloth(tag + '_trousers', dye, wool=True, seed=seed + 3))
        if robe_outfit:
            if wealthy:                                               # patterned court robes (Susa archers)
                main = crowd_cloth(tag + '_robe', dye, seed=seed, ornament=('lines', field or 'rosettes'))
            robe = candys(human, rig, pos, main)
            if w != 'persian_woman_480bc':
                wide_sleeves(human, rig, main)
            belt(rig, robe, gold if wealthy else leather, kind='strap', knot=False)
            if w == 'persian_king_480bc':
                persian_cap(human, rig, wool, band=gold, kind='royal')
            elif w == 'persian_immortal_480bc':
                fillet(human, rig, wool)                              # Susa glazed-brick archers: a twisted headband
            else:
                veil(human, rig, wool)                                # Achaemenid women: long robe + veil (seals, stelai)
        else:                                                         # court / servant / soldier: Median dress
            tunic = median_tunic(human, rig, pos, main)
            tight_sleeves(human, rig, main)
            belt(rig, tunic, leather, kind='strap', knot=False)
            persian_cap(human, rig, wool, kind='median')
        if wealthy:
            earrings(human, rig, gold)
    if tools and female and role in ('villager', 'servant', 'citizen') and w.startswith('greek'):
        # women's daily work: a water jar carried on the head (to/from the fountain) or spinning as they walk
        from lib import market as _market, tools as _tools, cast as _cast
        if seed % 2 == 0:
            ppos = posed_surface(human)
            head = bone_pos(rig, 'head')
            near = (np.linalg.norm(ppos[:, :2] - head[:2], axis=1) < 0.06) & (ppos[:, 2] > head[2])   # the crown only
            top = float(ppos[near][:, 2].max()) if near.any() else float(head[2]) + 0.2
            h = _market.hydria((float(head[0]), float(head[1]) + 0.01, top + 0.012), height=0.4, seed=seed, name=f'{tag}_hydria')
            # the ring pad of rolled cloth women set under a jar carried on the head
            bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.014, location=(float(head[0]), float(head[1]) + 0.01, top + 0.008))
            pad = bpy.context.object; pad.name = f'{tag}_headpad'; pad.data.materials.append(main)
            _cast.parent_to_bone(pad, rig, 'head')
            _cast.parent_to_bone(h, rig, 'head')
        else:
            _tools.hold(_market.spindle(f'{tag}_spindle'), rig, 'R')
        role = ''                                                     # (no trade tool on top of that)
    if tools:                                                         # the tool of the trade (lib/tools.py)
        from lib import tools as _tools
        t = _tools.tool_for(role, seed)
        if t is not None:
            if t.name.startswith('carrying_pole'):
                _tools.hold(t, rig, bone='clavicle.R', offset=(0.0, 0.0, 0.06), rot_deg=(0, 0, 90))
            else:
                _tools.hold(t, rig, 'R')
    return [o for o in bpy.data.objects if o not in before]
