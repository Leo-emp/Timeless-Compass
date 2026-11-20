# WS19 PARCHMENT MAP — the 3D half (the 2D textures come from `python -m tc map paint`, tc/maps/build.py).
#
# What makes the reference maps feel cinematic (docs/MAP_STYLE.md) and how we build each part here:
#   1. the map is a REAL crumpled sheet: a finely subdivided plane, displaced by a crumple pattern (Voronoi
#      facets + creases), so warm low light rakes across folds and leaves soft shadows in them
#   2. a LOW TILTED camera (35-55° down), always gliding slowly, with depth of field (far edge soft)
#   3. warm key light from the top-left, a soft cool fill, the edges of the sheet falling off into darkness
#   4. territories are composited LIVE in the material: each one's area (R) is shown where its grow map (G)
#      is below an animated `progress` value -> the colour spreads across the land like soaking ink
#   5. labels are thin decal planes SHRINKWRAPPED onto the crumpled sheet (they bend with the paper);
#      city tags STAND UP on the map facing the camera, casting small shadows
#   6. arrows are raised 3D ribbons (a bevelled curve) whose end grows along the route, with an arrowhead riding
#      the tip; pulse rings are glowing rings that expand and fade; battles pop crossed swords + a fire flash
#   7. SPOTLIGHT: the whole sheet darkens and a warm pool of light sits on one place (reference frame 04)
# Coordinates: the sheet is MAP_W metres wide, centred on the origin, +y = north. uv (0..1) -> world via uv_to_xy.
import json
import math
import os

import bpy
from mathutils import Vector

FPS = 24                     # same as tc/assemble.py (the whole pipeline runs at 24 fps)
MAP_W = 16.0                 # sheet width in metres (height follows the map's aspect)


# ------------------------------------------------------------------ helpers
def uv_to_xy(uv, aspect):
    return Vector(((uv[0] - 0.5) * MAP_W, (uv[1] - 0.5) * MAP_W / aspect, 0.0))


def _img(path, non_color=False):
    im = bpy.data.images.load(path, check_existing=True)
    if non_color:
        im.colorspace_settings.name = 'Non-Color'
    return im


def _key(sock_or_obj, path, frame, value, interp='BEZIER'):
    """Keyframe a value at a frame (socket default_value or object attribute)."""
    setattr(sock_or_obj, path, value)
    sock_or_obj.keyframe_insert(data_path=path, frame=frame)
    ad = getattr(sock_or_obj, 'id_data', sock_or_obj).animation_data
    if ad and ad.action:
        for fc in _fcurves(ad.action):
            for kp in fc.keyframe_points:
                if abs(kp.co[0] - frame) < 0.01:
                    kp.interpolation = interp


def _fcurves(action):
    """Blender 4.4+ 'layered actions' keep F-curves in layers/strips/channelbags; older ones in action.fcurves."""
    try:
        return list(action.fcurves)
    except AttributeError:
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
        return out


# ------------------------------------------------------------------ the sheet
def _crumple_height(nt, coord):
    """Crumpled paper height from the texture coordinate: big soft folds + Voronoi facets with sharp creases."""
    folds = nt.nodes.new('ShaderNodeTexNoise'); folds.inputs['Scale'].default_value = 1.6
    folds.inputs['Detail'].default_value = 2.0; folds.inputs['Roughness'].default_value = 0.4
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 0.9
    vor2 = nt.nodes.new('ShaderNodeTexVoronoi'); vor2.feature = 'DISTANCE_TO_EDGE'
    vor2.inputs['Scale'].default_value = 2.2
    for n in (folds, vor, vor2):
        nt.links.new(coord, n.inputs['Vector'])
    # creases = thin valleys along the Voronoi cell edges (1 - smoothstep of distance to edge)
    def crease(v, width):
        mr = nt.nodes.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'
        mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = width
        mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 1.0
        nt.links.new(v.outputs['Distance'], mr.inputs['Value'])
        return mr.outputs['Result']
    c1, c2 = crease(vor, 0.025), crease(vor2, 0.012)
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'
    nt.links.new(c1, m1.inputs[0]); nt.links.new(c2, m1.inputs[1])           # 1 on flat facets, 0 in creases
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY_ADD'
    nt.links.new(folds.outputs['Fac'], m2.inputs[0]); m2.inputs[1].default_value = 0.6
    nt.links.new(m1.outputs[0], m2.inputs[2])
    return m2.outputs[0]


def sheet_material(pack_dir, man, name='map_sheet'):
    """The paper material: base texture, territories composited live (animated progress), crumple bump,
    darkening for the spotlight (`spot_dark` input on the group)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.82
    bsdf.inputs['Specular IOR Level'].default_value = 0.25
    uvn = nt.nodes.new('ShaderNodeUVMap')
    base = nt.nodes.new('ShaderNodeTexImage'); base.image = _img(os.path.join(pack_dir, man['base']))
    base.interpolation = 'Cubic'
    nt.links.new(uvn.outputs['UV'], base.inputs['Vector'])
    col = base.outputs['Color']
    controls = {}
    for t in man['territories']:
        tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = _img(os.path.join(pack_dir, t['file']), non_color=True)
        tex.interpolation = 'Linear'
        nt.links.new(uvn.outputs['UV'], tex.inputs['Vector'])
        sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(tex.outputs['Color'], sep.inputs['Color'])
        prog = nt.nodes.new('ShaderNodeValue'); prog.label = prog.name = f"progress_{t['id']}"
        prog.outputs[0].default_value = 0.0
        # shown = area * smoothstep(grow - 0.03, grow, progress): soft spreading front
        sub = nt.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'
        nt.links.new(prog.outputs[0], sub.inputs[0]); nt.links.new(sep.outputs['Green'], sub.inputs[1])
        front = nt.nodes.new('ShaderNodeMapRange'); front.interpolation_type = 'SMOOTHSTEP'
        front.inputs['From Min'].default_value = -0.03; front.inputs['From Max'].default_value = 0.0
        nt.links.new(sub.outputs[0], front.inputs['Value'])
        shown = nt.nodes.new('ShaderNodeMath'); shown.operation = 'MULTIPLY'
        nt.links.new(front.outputs['Result'], shown.inputs[0]); nt.links.new(sep.outputs['Red'], shown.inputs[1])
        # ink colour multiplies the paper (grain, trees and mountains show through)
        tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
        tint.inputs['B'].default_value = (*[min(1.0, c * 1.45) for c in t['color']], 1)
        nt.links.new(shown.outputs[0], tint.inputs['Factor']); nt.links.new(col, tint.inputs['A'])
        fac = nt.nodes.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = 0.9
        nt.links.new(shown.outputs[0], fac.inputs[0]); nt.links.new(fac.outputs[0], tint.inputs['Factor'])
        # pure ink on top of the multiply (45 %): on tan paper a pure multiply turns purple into brown-pink
        pure = nt.nodes.new('ShaderNodeMix'); pure.data_type = 'RGBA'
        pure.inputs['B'].default_value = (*t['color'], 1)
        pf = nt.nodes.new('ShaderNodeMath'); pf.operation = 'MULTIPLY'; pf.inputs[1].default_value = 0.28
        nt.links.new(shown.outputs[0], pf.inputs[0]); nt.links.new(pf.outputs[0], pure.inputs['Factor'])
        nt.links.new(tint.outputs['Result'], pure.inputs['A'])
        tint = pure
        # emblem medallions (B channel) in pale cream on top, only where the realm is shown
        em = nt.nodes.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = 1.0
        nt.links.new(sep.outputs['Blue'], em.inputs[0])
        em2 = nt.nodes.new('ShaderNodeMath'); em2.operation = 'MULTIPLY'
        nt.links.new(em.outputs[0], em2.inputs[0]); nt.links.new(shown.outputs[0], em2.inputs[1])
        em3 = nt.nodes.new('ShaderNodeMath'); em3.operation = 'MULTIPLY'; em3.inputs[1].default_value = 0.55
        nt.links.new(em2.outputs[0], em3.inputs[0])
        emb = nt.nodes.new('ShaderNodeMix'); emb.data_type = 'RGBA'
        emb.inputs['B'].default_value = (0.92, 0.88, 0.78, 1)
        nt.links.new(em3.outputs[0], emb.inputs['Factor']); nt.links.new(tint.outputs['Result'], emb.inputs['A'])
        col = emb.outputs['Result']
        controls[t['id']] = prog.outputs[0]
    # spotlight darkening: whole sheet multiplied down (keyframed), the spot lamp then lights one place
    dark = nt.nodes.new('ShaderNodeValue'); dark.name = dark.label = 'spot_dark'; dark.outputs[0].default_value = 1.0
    dm = nt.nodes.new('ShaderNodeVectorMath'); dm.operation = 'SCALE'
    nt.links.new(col, dm.inputs[0]); nt.links.new(dark.outputs[0], dm.inputs['Scale'])
    nt.links.new(dm.outputs[0], bsdf.inputs['Base Color'])
    controls['spot_dark'] = dark.outputs[0]
    # crumple bump (fine creases the geometry is too coarse for)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    h = _crumple_height(nt, tc.outputs['Object'])
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12
    bump.inputs['Distance'].default_value = 0.02
    nt.links.new(h, bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    return m, controls


def sheet(pack_dir, man, subdiv=360, crumple=0.09, name='map'):
    """The crumpled map sheet. Returns (object, material controls dict)."""
    aspect = man['aspect']
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=subdiv, y_subdivisions=int(subdiv / aspect),
                                    size=1.0, location=(0, 0, 0))
    ob = bpy.context.object; ob.name = name
    ob.scale = (MAP_W, MAP_W / aspect, 1); bpy.ops.object.transform_apply(scale=True)
    # UVs: a primitive grid already has 0..1 UVs across the whole sheet
    tex = bpy.data.textures.new(f'{name}_crumple', 'VORONOI')
    tex.distance_metric = 'DISTANCE'; tex.noise_scale = 3.5; tex.noise_intensity = 1.0   # a few big facets
    tex.color_mode = 'INTENSITY'
    d = ob.modifiers.new('crumple', 'DISPLACE'); d.texture = tex; d.strength = crumple * 0.5; d.mid_level = 0.5
    d.texture_coords = 'OBJECT'
    tex2 = bpy.data.textures.new(f'{name}_folds', 'CLOUDS'); tex2.noise_scale = 4.5; tex2.noise_depth = 1   # soft rolling folds
    d2 = ob.modifiers.new('folds', 'DISPLACE'); d2.texture = tex2; d2.strength = crumple * 2.6; d2.mid_level = 0.5
    bpy.ops.object.shade_smooth()
    m, controls = sheet_material(pack_dir, man)
    ob.data.materials.append(m)
    # dark table/cloth under and around the sheet (the edges of frame fall into this)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.15))
    under = bpy.context.object; under.name = f'{name}_table'
    um = bpy.data.materials.new('map_table'); um.use_nodes = True
    ub = um.node_tree.nodes['Principled BSDF']; ub.inputs['Base Color'].default_value = (0.035, 0.025, 0.018, 1)
    ub.inputs['Roughness'].default_value = 0.9
    under.data.materials.append(um)
    return ob, controls


# ------------------------------------------------------------------ labels
def _decal_material(path, name, self_lit=0.0):
    """Image with alpha on a plane; an `opacity` value node (keyframed for fades).
    self_lit (0..1): share of the image's own colour emitted, so standing cards / screen cards read clearly
    whatever side the key light is on (they are 'printed' graphics, like the reference's tags)."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = _img(path); tex.extension = 'CLIP'
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled'); bsdf.inputs['Roughness'].default_value = 0.8
    op = nt.nodes.new('ShaderNodeValue'); op.name = op.label = 'opacity'; op.outputs[0].default_value = 1.0
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'
    nt.links.new(tex.outputs['Alpha'], mul.inputs[0]); nt.links.new(op.outputs[0], mul.inputs[1])
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color']); nt.links.new(mul.outputs[0], bsdf.inputs['Alpha'])
    if self_lit:
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Emission Color'])
        bsdf.inputs['Emission Strength'].default_value = self_lit
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    try:
        m.surface_render_method = 'BLENDED'
    except AttributeError:
        m.blend_method = 'BLEND'
    return m, op.outputs[0]


def labels(pack_dir, man, sheet_ob):
    """Region/sea names as decals hugging the paper; place tags as standing cards facing the camera.
    Returns {label id: opacity socket}."""
    aspect = man['aspect']; ctl = {}
    for e in man['labels']:
        w = e['w'] * MAP_W; h = e['h'] * MAP_W
        p = uv_to_xy(e['uv'], aspect)
        m, op = _decal_material(os.path.join(pack_dir, e['file']), f"lbl_{e['id']}", 0.55 if e['kind'] == 'place' else 0.0)
        if e['kind'] == 'place':
            # standing card: bottom edge on the city point, upright, turned to the camera by a constraint later
            bpy.ops.mesh.primitive_plane_add(size=1, location=(p.x, p.y, h / 2 + 0.02))
            ob = bpy.context.object; ob.scale = (w, h, 1); ob.rotation_euler = (math.radians(90), 0, 0)
            bpy.ops.object.transform_apply(scale=True)
            ob['standing'] = True
        else:
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=24, y_subdivisions=8, size=1, location=(p.x, p.y, 0.3))
            ob = bpy.context.object; ob.scale = (w, h, 1); bpy.ops.object.transform_apply(scale=True)
            sw = ob.modifiers.new('hug', 'SHRINKWRAP'); sw.target = sheet_ob; sw.wrap_method = 'PROJECT'
            sw.use_project_z = True; sw.use_negative_direction = True; sw.offset = 0.006
        ob.name = f"lbl_{e['id']}"
        ob.data.materials.append(m)
        ob.visible_shadow = e['kind'] == 'place'
        ctl[e['id']] = op
    return ctl


def face_camera(cam):
    """Point every standing tag at the camera (yaw only: they stay upright like cards on a table)."""
    for ob in bpy.data.objects:
        if ob.get('standing'):
            # cards and banners face -Y after being stood up; spin them about Z only so that face looks at the camera
            c = ob.constraints.new('LOCKED_TRACK'); c.target = cam
            c.track_axis = 'TRACK_NEGATIVE_Y'; c.lock_axis = 'LOCK_Z'


# ------------------------------------------------------------------ arrows, rings, battles
def _emit_mat(name, color, strength=0.0, rough=0.55):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    if strength:
        b.inputs['Emission Color'].default_value = (*color, 1); b.inputs['Emission Strength'].default_value = strength
    return m


def _ribbon(name, pts, width, height, z, mat, start_f, end_f):
    """A flat raised ribbon along points (bezier curve + rectangle profile), growing from tail to head."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.twist_mode = 'Z_UP'
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = (p.x, p.y, z); bp.handle_left_type = bp.handle_right_type = 'AUTO'
    prof = bpy.data.curves.new(f"{name}_prof", 'CURVE'); prof.dimensions = '2D'
    ps = prof.splines.new('POLY'); ps.points.add(3)
    hw = width / 2
    for i, (x, y) in enumerate([(-hw, 0), (hw, 0), (hw * 0.92, height), (-hw * 0.92, height)]):   # slight bevel on top
        ps.points[i].co = (x, y, 0, 1)
    ps.use_cyclic_u = True
    pob = bpy.data.objects.new(f"{name}_prof", prof); bpy.context.collection.objects.link(pob)
    pob.hide_render = pob.hide_viewport = True
    cu.bevel_mode = 'OBJECT'; cu.bevel_object = pob; cu.use_fill_caps = True
    cu.bevel_factor_mapping_end = 'SPLINE'
    ob = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    _key(cu, 'bevel_factor_end', start_f, 0.0); _key(cu, 'bevel_factor_end', end_f, 1.0)
    return ob


def arrow(entry, aspect, start_f, end_f, lift=0.03):
    """Reference arrow: a flat, slightly raised RED ribbon with a darker red outline, growing tail -> head,
    a broad arrowhead riding the tip; it casts a soft shadow on the paper."""
    pts = [uv_to_xy(p, aspect) for p in entry['uv']]
    width = entry['width'] * MAP_W
    col = tuple(c ** 1.6 for c in entry['color'])     # deeper, more saturated than the paper ink (reads as a 3D object)
    body = _emit_mat(f"arrow_{entry['id']}", col, 0.0, 0.5)
    edge = _emit_mat(f"arrow_edge_{entry['id']}", tuple(c * 0.45 for c in col), 0.0, 0.6)
    ob = _ribbon(f"arrow_{entry['id']}", pts, width, width * 0.1, lift, body, start_f, end_f)
    _ribbon(f"arrow_out_{entry['id']}", pts, width * 1.22, width * 0.07, lift - 0.004, edge, start_f, end_f)
    # arrowhead: flat triangle prism (+ dark outline copy) following the path's growing end
    def head(name, scale, mat, dz):
        bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=width * 1.3 * scale, depth=width * 0.12, location=(0, 0, 0))
        h = bpy.context.object; h.name = name
        h.rotation_euler = (0, 0, math.radians(-90)); bpy.ops.object.transform_apply(rotation=True)
        h.scale = (1.0, 1.25, 1); bpy.ops.object.transform_apply(scale=True)
        h.data.materials.append(mat)
        fp = h.constraints.new('FOLLOW_PATH'); fp.target = ob; fp.use_curve_follow = True
        fp.use_fixed_location = True; fp.forward_axis = 'FORWARD_Y'; fp.up_axis = 'UP_Z'
        _key(fp, 'offset_factor', start_f, 0.0); _key(fp, 'offset_factor', end_f, 1.0)
        h.location = (0, width * 0.5, dz)
        _key(h, 'scale', start_f, (0.0, 0.0, 0.0)); _key(h, 'scale', start_f + 4, (1.0, 1.0, 1.0))
        return h
    head(f"arrowhead_{entry['id']}", 1.0, body, width * 0.06)
    head(f"arrowhead_out_{entry['id']}", 1.18, edge, width * 0.02)
    return ob


def pulse(entry, aspect, frame, rings=4, color=(1.0, 0.72, 0.3), radius=2.6):
    """Concentric glowing rings expanding from a place and fading (reference frame 03)."""
    p = uv_to_xy(entry['uv'], aspect)
    for k in range(rings):
        f0 = frame + k * 10
        bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.025, location=(p.x, p.y, 0.08))
        ob = bpy.context.object; ob.name = f"pulse_{entry['id']}_{k}"
        m = _emit_mat(ob.name, color, 1.6)
        b = m.node_tree.nodes['Principled BSDF']
        try:
            m.surface_render_method = 'BLENDED'
        except AttributeError:
            m.blend_method = 'BLEND'
        ob.data.materials.append(m); ob.visible_shadow = False
        _key(ob, 'scale', f0, (0.05, 0.05, 1.0), 'LINEAR'); _key(ob, 'scale', f0 + 40, (radius, radius, 1.0), 'LINEAR')
        a = b.inputs['Alpha']
        _key(a, 'default_value', f0 - 1, 0.0); _key(a, 'default_value', f0, 0.75); _key(a, 'default_value', f0 + 40, 0.0)
    # a soft golden glow disc on the paper that swells with the first ring (the light of the news spreading)
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=1.0, fill_type='TRIFAN', location=(p.x, p.y, 0.06))
    disc = bpy.context.object; disc.name = f"pulse_{entry['id']}_glow"
    gm = _emit_mat(disc.name, color, 1.5)
    try:
        gm.surface_render_method = 'BLENDED'
    except AttributeError:
        gm.blend_method = 'BLEND'
    disc.data.materials.append(gm); disc.visible_shadow = False
    ga = gm.node_tree.nodes['Principled BSDF'].inputs['Alpha']
    _key(ga, 'default_value', frame - 1, 0.0); _key(ga, 'default_value', frame + 8, 0.35); _key(ga, 'default_value', frame + 60, 0.0)
    _key(disc, 'scale', frame, (0.1, 0.1, 1)); _key(disc, 'scale', frame + 60, (radius * 0.8, radius * 0.8, 1))
    lamp = bpy.data.lights.new(f"pulse_{entry['id']}_light", 'POINT'); lamp.color = color
    lo = bpy.data.objects.new(lamp.name, lamp); bpy.context.collection.objects.link(lo); lo.location = (p.x, p.y, 0.6)
    _key(lamp, 'energy', frame - 1, 0.0); _key(lamp, 'energy', frame + 5, 60.0); _key(lamp, 'energy', frame + 60, 0.0)


def battle(entry, aspect, frame, size=0.55):
    """Crossed swords that pop up on the place with a fire flash (reference frame 04)."""
    p = uv_to_xy(entry['uv'], aspect)
    # light steel that does not mirror the dark room (pure metal reflects the black world and reads as a black X)
    steel = _emit_mat('sword_steel', (0.82, 0.82, 0.86), 0.0, 0.3)
    steel.node_tree.nodes['Principled BSDF'].inputs['Metallic'].default_value = 0.35
    gold = _emit_mat('sword_gold', (0.75, 0.55, 0.2), 0.0, 0.3)
    root = bpy.data.objects.new(f"battle_{entry['id']}", None); bpy.context.collection.objects.link(root)
    root.location = (p.x, p.y, size * 0.75)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1); blade = bpy.context.object
        blade.scale = (size * 0.06, 0.012, size * 0.9); blade.location = (0, 0, size * 0.15)
        bpy.ops.mesh.primitive_cube_add(size=1); guard = bpy.context.object
        guard.scale = (size * 0.32, 0.03, 0.03); guard.location = (0, 0, -size * 0.32)
        bpy.ops.mesh.primitive_cylinder_add(radius=size * 0.035, depth=size * 0.3); grip = bpy.context.object
        grip.location = (0, 0, -size * 0.5)
        blade.data.materials.append(steel); guard.data.materials.append(gold); grip.data.materials.append(gold)
        piv = bpy.data.objects.new(f"sword_{side}", None); bpy.context.collection.objects.link(piv)
        for o in (blade, guard, grip):
            o.parent = piv
        piv.parent = root; piv.rotation_euler = (0, math.radians(32 * side), 0)
    root.rotation_euler = (math.radians(70), 0, 0)
    _key(root, 'scale', frame - 1, (0.0, 0.0, 0.0)); _key(root, 'scale', frame + 5, (1.2, 1.2, 1.2))
    _key(root, 'scale', frame + 9, (1.0, 1.0, 1.0))
    # fire flash: an emissive burst sphere + light
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=size * 0.5, location=(p.x, p.y, 0.15))
    fl = bpy.context.object; fl.name = f"flash_{entry['id']}"
    fm = _emit_mat('flash', (1.0, 0.38, 0.06), 5.0)      # too bright turns white under the film curve
    try:
        fm.surface_render_method = 'BLENDED'
    except AttributeError:
        fm.blend_method = 'BLEND'
    fl.data.materials.append(fm); fl.visible_shadow = False
    a = fm.node_tree.nodes['Principled BSDF'].inputs['Alpha']
    _key(a, 'default_value', frame - 1, 0.0); _key(a, 'default_value', frame + 2, 0.9); _key(a, 'default_value', frame + 22, 0.0)
    _key(fl, 'scale', frame, (0.3, 0.3, 0.2)); _key(fl, 'scale', frame + 22, (2.2, 2.2, 0.8))
    lamp = bpy.data.lights.new(f"battle_{entry['id']}_light", 'POINT'); lamp.color = (1.0, 0.5, 0.15)
    lo = bpy.data.objects.new(lamp.name, lamp); bpy.context.collection.objects.link(lo); lo.location = (p.x, p.y, 0.8)
    _key(lamp, 'energy', frame - 1, 0.0); _key(lamp, 'energy', frame + 2, 400.0); _key(lamp, 'energy', frame + 30, 60.0)
    return root


# ------------------------------------------------------------------ armies (battle maps + world maps)
def _bar_mesh(name, length, width, height):
    """One soldiers' rank: a long rounded bar (bevelled box), like the reference's red/teal blocks."""
    bpy.ops.mesh.primitive_cube_add(size=1); ob = bpy.context.object; ob.name = name
    ob.scale = (length, width, height); bpy.ops.object.transform_apply(scale=True)
    bv = ob.modifiers.new('round', 'BEVEL'); bv.width = min(width, height) * 0.22; bv.segments = 4
    bpy.ops.object.shade_smooth()
    return ob


def banner_flag(pack_dir, file, name, height=0.5, cloth_w=0.2, seed=0):
    """A tall pole with a cloth banner on a crossbar; the cloth ripples (Wave modifier, no cloth sim needed)."""
    root = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(root)
    wood = _emit_mat('pole_wood', (0.22, 0.14, 0.08), 0.0, 0.6)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.008, depth=height, location=(0, 0, height / 2))
    pole = bpy.context.object; pole.data.materials.append(wood); pole.parent = root
    bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=cloth_w * 1.15, location=(0, 0, height - 0.015),
                                        rotation=(0, math.radians(90), 0))
    bar = bpy.context.object; bar.data.materials.append(wood); bar.parent = root
    bpy.ops.mesh.primitive_cone_add(radius1=0.014, depth=0.04, location=(0, 0, height + 0.02))
    tip = bpy.context.object; tip.data.materials.append(_emit_mat('pole_tip', (0.6, 0.5, 0.3), 0.0, 0.3)); tip.parent = root
    ch = cloth_w * 1.25
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=12, y_subdivisions=14, size=1, location=(0, 0.003, height - 0.02 - ch / 2))
    cl = bpy.context.object; cl.scale = (cloth_w, ch, 1); cl.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)
    m, _ = _decal_material(os.path.join(pack_dir, file), f'banner_{file}', 0.6)
    m.use_backface_culling = False
    cl.data.materials.append(m); cl.parent = root
    wv = cl.modifiers.new('ripple', 'WAVE'); wv.use_x = True; wv.use_y = False
    wv.height = 0.006; wv.width = 0.09; wv.speed = 0.012; wv.narrowness = 1.2
    wv.time_offset = -seed * 7; wv.start_position_x = -cloth_w / 2
    cl.visible_shadow = True
    return root


def army(pack_dir, entry, aspect, scale=1.0):
    """One unit: rows x cols of rounded bars in the side's colour + banners standing behind.
    Returns the root empty (move it with keyframes)."""
    p = uv_to_xy(entry['uv'], aspect)
    root = bpy.data.objects.new(f"unit_{entry['id']}", None); bpy.context.collection.objects.link(root)
    root.location = (p.x, p.y, 0.03); root.rotation_euler = (0, 0, math.radians(-entry.get('facing', 0)))
    mat = _emit_mat(f"unit_{entry['side'] if 'side' in entry else 'x'}", tuple(c ** 2.0 for c in entry.get('color', (0.6, 0.06, 0.07))), 0.0, 0.6)
    rows, cols = entry.get('rows', 3), entry.get('cols', 2)
    L_, Wd, Hh = 0.42 * scale, 0.075 * scale, 0.038 * scale      # flat-topped ranks, not tubes
    for c in range(cols):
        for r in range(rows):
            b = _bar_mesh(f"unit_{entry['id']}_{c}_{r}", L_, Wd, Hh)
            b.location = ((c - (cols - 1) / 2) * (L_ + 0.008 * scale), (r - (rows - 1) / 2) * (Wd + 0.004 * scale), Hh / 2)
            b.data.materials.append(mat); b.parent = root
    for k in range(entry.get('banners', 1)):
        if 'banner' not in entry:
            break
        fl = banner_flag(pack_dir, entry['banner'], f"unit_{entry['id']}_banner{k}", 0.36 * scale, 0.22 * scale, seed=k)
        n = entry.get('banners', 1)
        fl.parent = root
        fl.location = ((k - (n - 1) / 2) * (L_ * cols / max(n, 1)), -(rows / 2) * Wd * 0.2, Hh)
        fl['standing'] = True                       # turns to face the camera (yaw only)
    return root


def move_along(root, aspect, path_uv, f0, f1):
    """March along a route (the arrow's points): constant speed, keyed at every route point."""
    pts = [uv_to_xy(p, aspect) for p in path_uv]
    seg = [(b - a).length for a, b in zip(pts[:-1], pts[1:])]; total = sum(seg) or 1.0
    z = root.location.z; acc = 0.0
    _key(root, 'location', f0, (pts[0].x, pts[0].y, z), 'LINEAR')
    for p, s_ in zip(pts[1:], seg):
        acc += s_
        _key(root, 'location', f0 + (f1 - f0) * acc / total, (p.x, p.y, z), 'LINEAR')


def move(root, aspect, to_uv, f0, f1):
    """Slide a unit across the map (ease in/out), turning to face where it goes."""
    t = uv_to_xy(to_uv, aspect)
    start = root.location.copy()
    heading = math.atan2(t.x - start.x, t.y - start.y)
    _key(root, 'location', f0, start); _key(root, 'location', f1, (t.x, t.y, start.z))
    _key(root, 'rotation_euler', f0, root.rotation_euler.copy())
    _key(root, 'rotation_euler', f0 + 12, (0, 0, -heading))


# ------------------------------------------------------------------ light, camera, world
def lights(center=(0, 0, 0), warmth=1.0):
    """Warm key from top-left (low, rakes across the creases), soft cool fill, faint rim."""
    def area(name, energy, color, loc, size):
        l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color; l.size = size
        o = bpy.data.objects.new(name, l); bpy.context.collection.objects.link(o); o.location = loc
        d = Vector(center) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return l
    key = area('map_key', 2300 * warmth, (1.0, 0.8, 0.55), (center[0] - 8, center[1] + 3, 7.5), 6.0)
    fill = area('map_fill', 450, (0.75, 0.82, 1.0), (center[0] + 8, center[1] - 9, 8), 12.0)
    w = bpy.context.scene.world or bpy.data.worlds.new('map_world'); bpy.context.scene.world = w
    w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.016, 0.012, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.3
    return key, fill


def spot(aspect, uv, frame_in, frame_out=None, radius=1.6, controls=None):
    """Spotlight beat: the sheet darkens to ~15 % and a warm pool of light sits on one place."""
    p = uv_to_xy(uv, aspect)
    l = bpy.data.lights.new('map_spot', 'SPOT'); l.color = (1.0, 0.78, 0.5); l.spot_size = math.radians(24)
    l.spot_blend = 0.6; l.shadow_soft_size = 0.4
    o = bpy.data.objects.new('map_spot', l); bpy.context.collection.objects.link(o)
    o.location = (p.x - 1.0, p.y - 1.5, 6.0)
    o.rotation_euler = (Vector((p.x, p.y, 0)) - o.location).to_track_quat('-Z', 'Y').to_euler()
    _key(l, 'energy', frame_in, 0.0); _key(l, 'energy', frame_in + 15, 5000.0)
    if controls and 'spot_dark' in controls:
        s = controls['spot_dark']
        _key(s, 'default_value', frame_in, 1.0); _key(s, 'default_value', frame_in + 15, 0.18)
        if frame_out:
            _key(s, 'default_value', frame_out, 0.18); _key(s, 'default_value', frame_out + 15, 1.0)
    if frame_out:
        _key(l, 'energy', frame_out, 5000.0); _key(l, 'energy', frame_out + 15, 0.0)


def camera(aspect, target_uv, frames, tilt_deg=48.0, dist=7.5, drift=(0.9, 0.35), push=0.12, yaw_deg=0.0,
           focal=45.0, fstop=1.0):
    """Low tilted camera looking at target_uv, gliding slowly (drift metres over the shot) and pushing in a little.
    Depth of field focused on the target: the far edge of the map goes soft, like the reference."""
    t = uv_to_xy(target_uv, aspect)
    cd = bpy.data.cameras.new('map_cam'); cd.lens = focal
    cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new('map_cam', cd); bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    aim = bpy.data.objects.new('map_cam_aim', None); bpy.context.collection.objects.link(aim)
    cd.dof.focus_object = aim
    tilt, yaw = math.radians(tilt_deg), math.radians(yaw_deg)
    def pos(d):
        return t + Vector((-math.sin(yaw) * d * math.cos(tilt), -math.cos(yaw) * d * math.cos(tilt), d * math.sin(tilt)))
    f0, f1 = frames
    dvec = Vector((drift[0] * math.cos(yaw) + drift[1] * math.sin(yaw), -drift[0] * math.sin(yaw) + drift[1] * math.cos(yaw), 0))
    _key(aim, 'location', f0, t - dvec / 2, 'LINEAR'); _key(aim, 'location', f1, t + dvec / 2, 'LINEAR')
    _key(cam, 'location', f0, pos(dist) - dvec / 2, 'LINEAR'); _key(cam, 'location', f1, pos(dist * (1 - push)) + dvec / 2, 'LINEAR')
    c = cam.constraints.new('TRACK_TO'); c.target = aim; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    return cam


def vignette(cam, strength=0.85):
    """Dark edges like the reference (the map seems lit by one lamp in a dark room): a camera-locked card with a
    radial black gradient drawn into a small generated image."""
    W, H = 320, 180
    im = bpy.data.images.new('map_vignette', W, H, alpha=True)
    px = []
    for y in range(H):
        for x in range(W):
            dx, dy = (x / (W - 1) - 0.5) * 2, (y / (H - 1) - 0.5) * 2
            r = math.sqrt(dx * dx * 0.9 + dy * dy * 1.1)
            a = max(0.0, min(1.0, (r - 0.55) / 0.75)) ** 1.6 * strength
            px += [0.0, 0.0, 0.0, a]
    im.pixels = px
    m = bpy.data.materials.new('map_vignette'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = im
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0, 0, 0, 1)
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tex.outputs['Alpha'], mix.inputs['Fac']); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    try:
        m.surface_render_method = 'BLENDED'
    except AttributeError:
        m.blend_method = 'BLEND'
    bpy.ops.mesh.primitive_plane_add(size=1); ob = bpy.context.object; ob.name = 'map_vignette'
    D = 0.5; fw = D * cam.data.sensor_width / cam.data.lens
    ob.scale = (fw * 1.02, fw * 9 / 16 * 1.02, 1); ob.parent = cam; ob.location = (0, 0, -D)
    ob.data.materials.append(m); ob.visible_shadow = False
    return ob


def date_card(pack_dir, man, cam, frame):
    """The torn date strip, pinned to the top-right of frame (child of the camera, so it stays put)."""
    if 'date' not in man:
        return
    e = man['date']
    m, op = _decal_material(os.path.join(pack_dir, e['file']), 'date_strip', 1.0)
    bpy.ops.mesh.primitive_plane_add(size=1); ob = bpy.context.object; ob.name = 'date_strip'
    # frame width at depth D in front of the lens = D * sensor / focal. Strip = 13 % of the frame width, top right.
    D = 1.0; fw = D * cam.data.sensor_width / cam.data.lens; fh = fw * 9 / 16
    sw = fw * 0.13; sh = sw * e['h'] / e['w']
    ob.scale = (sw, sh, 1)
    ob.parent = cam; ob.location = (fw / 2 - sw / 2 - fw * 0.04, fh / 2 - sh / 2 - fh * 0.06, -D); ob.data.materials.append(m)
    ob.visible_shadow = False
    _key(op, 'default_value', frame - 1, 0.0); _key(op, 'default_value', frame + 10, 1.0)


def portrait_card(pack_dir, entry, cam, f_in, f_out=None, side='right'):
    """A leader card that slides in from the frame edge and holds (reference frame 07), child of the camera."""
    m, op = _decal_material(os.path.join(pack_dir, entry['file']), f"card_{entry['id']}", 0.9)
    bpy.ops.mesh.primitive_plane_add(size=1); ob = bpy.context.object; ob.name = f"card_{entry['id']}"
    D = 1.0; fw = D * cam.data.sensor_width / cam.data.lens; fh = fw * 9 / 16
    ch = fh * 0.62; cw = ch * entry['aspect']
    ob.scale = (cw, ch, 1); ob.parent = cam; ob.data.materials.append(m); ob.visible_shadow = False
    sgn = 1 if side == 'right' else -1
    x_in = sgn * (fw / 2 - cw / 2 - fw * 0.03); x_out = sgn * (fw / 2 + cw)
    y = -fh * 0.06
    _key(ob, 'location', f_in, (x_out, y, -D)); _key(ob, 'location', f_in + 14, (x_in, y, -D))
    _key(op, 'default_value', f_in, 1.0, 'CONSTANT')
    if f_out:
        _key(ob, 'location', f_out, (x_in, y, -D)); _key(ob, 'location', f_out + 14, (x_out, y, -D))


def grade(scene):
    """Map colour grade: maps are GRAPHICS (the reference's teal, purple and crimson are rich and clean), so use the
    plain Standard transform with a gentle contrast look instead of AgX (AgX is tuned for skin + skies and turns
    flat map colours milky)."""
    vs = scene.view_settings
    vs.view_transform = 'Standard'
    for look in ('Medium High Contrast', 'Standard - Medium High Contrast', 'None'):
        try:
            vs.look = look; break
        except TypeError:
            continue
    vs.exposure = -0.55


# ------------------------------------------------------------------ the whole map shot
def build(pack_dir, seconds=10.0, target_uv=None, tilt_deg=48.0, dist=7.5, yaw_deg=0.0, beats=None, crumple=0.09):
    """Everything for one map shot from a painted pack. Beats (seconds) drive the animation:
    show/hide (instant territory or label), grow/shrink (territory over dur), arrow (route over dur),
    pulse, battle, spotlight {uv or id, until}, date."""
    pack_dir = os.path.abspath(pack_dir)          # Blender resolves relative image paths against the .blend, not cwd
    man = json.load(open(os.path.join(pack_dir, 'manifest.json'), encoding='utf-8'))
    aspect = man['aspect']
    sc = bpy.context.scene; sc.render.fps = FPS
    f_end = int(seconds * FPS); sc.frame_start, sc.frame_end = 1, f_end
    ob, ctl = sheet(pack_dir, man, crumple=crumple)
    lbl = labels(pack_dir, man, ob)
    lights()
    tgt = target_uv or [0.5, 0.5]
    cam = camera(aspect, tgt, (1, f_end), tilt_deg=tilt_deg, dist=dist, yaw_deg=yaw_deg)
    vignette(cam)
    beats = man['beats'] if beats is None else beats
    shown_terr = {b['id'] for b in beats if b['do'] in ('show', 'grow') and b['id'] in ctl}
    shown_lbl = set()
    for tid in ctl:                         # territories start hidden unless a beat brings them in
        if tid != 'spot_dark':
            _key(ctl[tid], 'default_value', 1, 0.0, 'CONSTANT')
    for lid, op in lbl.items():
        _key(op, 'default_value', 1, 0.0, 'CONSTANT')
    arrows = {a['id']: a for a in man['arrows']}; pulses = {p['id']: p for p in man['pulses']}
    battles = {b['id']: b for b in man['battles']}
    labels_by_id = {e['id']: e for e in man['labels']}
    units = {u['id']: army(pack_dir, u, aspect, u.get('scale', 1.0)) for u in man.get('units', [])}
    face_camera(cam)
    for b in beats:
        f = int(b['t'] * FPS) + 1; d = int(b.get('dur', 1.0) * FPS)
        i = b.get('id')
        if b['do'] == 'show':
            if i in ctl:
                _key(ctl[i], 'default_value', f, 1.0, 'CONSTANT')
            if i in lbl:
                _key(lbl[i], 'default_value', f, 1.0, 'CONSTANT')
        elif b['do'] == 'grow' and i in ctl:
            _key(ctl[i], 'default_value', f, 0.0); _key(ctl[i], 'default_value', f + d, 1.0)
            if i in lbl:
                _key(lbl[i], 'default_value', f + d // 2, 0.0); _key(lbl[i], 'default_value', f + d, 1.0)
        elif b['do'] == 'shrink' and i in ctl:
            _key(ctl[i], 'default_value', f, 1.0); _key(ctl[i], 'default_value', f + d, 0.0)
        elif b['do'] == 'hide' and i in lbl:
            _key(lbl[i], 'default_value', f, 1.0); _key(lbl[i], 'default_value', f + 8, 0.0)
        elif b['do'] == 'arrow' and i in arrows:
            arrow(arrows[i], aspect, f, f + d)
        elif b['do'] == 'pulse' and i in pulses:
            pulse(pulses[i], aspect, f)
        elif b['do'] == 'battle' and i in battles:
            battle(battles[i], aspect, f)
        elif b['do'] == 'spotlight':
            uvp = b.get('uv') or (labels_by_id.get(i) or pulses.get(i) or battles.get(i) or {}).get('uv', tgt)
            spot(aspect, uvp, f, int(b['until'] * FPS) + 1 if 'until' in b else None, controls=ctl)
        elif b['do'] == 'move' and i in units:
            if b.get('path_uv'):
                move_along(units[i], aspect, b['path_uv'], f, f + d)
            else:
                move(units[i], aspect, b['to_uv'], f, f + d)
        elif b['do'] == 'card':
            c = {e['id']: e for e in man.get('cards', [])}.get(i)
            if c:
                portrait_card(pack_dir, c, cam, f, int(b['until'] * FPS) + 1 if 'until' in b else None, b.get('side', 'right'))
        elif b['do'] == 'date':
            date_card(pack_dir, man, cam, f)
    # labels of shown territories + all seas/places fade in at their territory's show time (or frame 1)
    for e in man['labels']:
        if e['id'] in shown_lbl:
            continue
        if e['kind'] in ('sea', 'place'):
            _key(lbl[e['id']], 'default_value', 1, 1.0, 'CONSTANT')
    return {'sheet': ob, 'camera': cam, 'controls': ctl, 'labels': lbl, 'manifest': man}
