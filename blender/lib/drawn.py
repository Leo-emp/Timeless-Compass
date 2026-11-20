# DRAWN LOOK: turns any of our 3D scenes into hand-drawn-looking frames (the "3D drawn by the computer" style the
# owner chose to test on 2026-11-20 against a Heroes of Bronze reference frame). Same characters, rigs, motion,
# props and sets - only the paint changes:
#   1. toon()        every material -> its own flat colour in 3 tones (lit / shadow / deep shadow), shadows tinted
#                    cool like a painter's, not just darker. Hair and beards become solid shapes of colour.
#   2. ink()         Freestyle ink lines: thin where lit, thicker in shadow and at the silhouette (calligraphic pen),
#                    dark warm brown, never pure black; inner lines for brows, nose, wrinkles (ridges/valleys).
#   3. paint_post()  compositor: Kuwahara filter = brush-stroke look on colour areas (the sky photo becomes painted
#                    clouds), ink laid on top AFTER the filter so lines stay crisp, then a muted warm grade.
# EEVEE only (Shader-to-RGB). Call after the scene is built, before rendering:  drawn.apply(sun_dir=...)
import math

import bpy

INK = (0.085, 0.052, 0.038)                     # warm dark brown ink


def _hair_rgb(node):
    """Flat colour of a Principled Hair BSDF (melanin or absorption parametrisation)."""
    if node.parametrization == 'ABSORPTION':
        a = node.inputs['Absorption Coefficient'].default_value
        return tuple(math.exp(-c / 0.9) for c in a[:3])
    m = node.inputs['Melanin'].default_value
    r = node.inputs['Melanin Redness'].default_value
    t = m ** 0.65
    blond, dark = (0.62, 0.48, 0.30), (0.05, 0.034, 0.024)
    c = [b + (d - b) * t for b, d in zip(blond, dark)]
    c[0] *= 1 + 0.35 * r; c[2] *= 1 - 0.3 * r
    return tuple(min(1.0, x) for x in c)


def _ramp(nt, tones, steps):
    """Constant colour ramp: tones = [(deep), (shadow), (lit)] multipliers, steps = (deep->shadow, shadow->lit)."""
    rp = nt.nodes.new('ShaderNodeValToRGB'); cr = rp.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0; cr.elements[0].color = (*tones[0], 1)
    cr.elements[1].position = steps[0]; cr.elements[1].color = (*tones[1], 1)
    e = cr.elements.new(steps[1]); e.color = (*tones[2], 1)
    return rp


# painter's tones: the shadow side goes cooler and a little purple, the lit side a touch warm
SKIN_TONE = (0.62, 0.38, 0.24)        # sun-tanned Greek skin, as painted
SKIN_FLAT = 0.6
TONES = [(0.40, 0.36, 0.50), (0.68, 0.62, 0.70), (1.0, 0.97, 0.92)]
STEPS = (0.10, 0.36)


def toon_material(mat, tones=TONES, steps=STEPS, mode='eevee'):
    if not mat or not mat.use_nodes or mat.get('drawn'):
        return
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None) or \
        next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if out is None:
        return
    pr = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    hair = next((n for n in nt.nodes if n.type == 'BSDF_HAIR_PRINCIPLED'), None)
    col_src, col_val, alpha_src, clear = None, None, None, False
    if pr is not None:
        bc = pr.inputs['Base Color']
        col_src = bc.links[0].from_socket if bc.is_linked else None
        col_val = tuple(bc.default_value)[:3]
        a = pr.inputs['Alpha']
        alpha_src = a.links[0].from_socket if a.is_linked else None
        tw = pr.inputs.get('Transmission Weight')
        if (tw is not None and not tw.is_linked and tw.default_value > 0.5) or (not a.is_linked and a.default_value < 0.5):
            clear = True                                           # cornea / glass: let what is behind show
        if pr.inputs['Metallic'].default_value > 0.5 and col_src is None:
            col_val = tuple(min(1.0, c * 1.15) for c in col_val)   # metals: their tint, a bit brighter
    elif hair is not None:
        col_val = _hair_rgb(hair)
        grey_mix = next((n for n in nt.nodes if n.type == 'MIX_SHADER'), None)
        thr = next((n for n in nt.nodes if n.type == 'MATH' and n.operation == 'LESS_THAN'), None)
        if grey_mix is not None and thr is not None:               # grey strands keep their share
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
            nt.links.new(thr.outputs[0], mx.inputs['Factor'])
            mx.inputs['A'].default_value = (*col_val, 1); mx.inputs['B'].default_value = (0.58, 0.57, 0.55, 1)
            col_src = mx.outputs['Result']
    else:
        col_val = tuple(mat.diffuse_color)[:3]
    if clear:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); nt.links.new(tr.outputs[0], out.inputs['Surface'])
        mat['drawn'] = 1
        return
    if mode == 'cycles':                                            # flat colour only; light is toned in the compositor
        diff = nt.nodes.new('ShaderNodeBsdfDiffuse')
        if 'skin' in mat.name.lower() and col_src is not None:      # painted skin: one warm tan, the texture only a hint
            sk = nt.nodes.new('ShaderNodeMix'); sk.data_type = 'RGBA'; sk.blend_type = 'MIX'
            sk.inputs['Factor'].default_value = SKIN_FLAT
            nt.links.new(col_src, sk.inputs['A']); sk.inputs['B'].default_value = (*SKIN_TONE, 1)
            col_src = sk.outputs['Result']
        if col_src is not None:
            nt.links.new(col_src, diff.inputs['Color'])
        else:
            diff.inputs['Color'].default_value = (*col_val, 1)
        shader = diff.outputs[0]
        if alpha_src is not None:
            tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(alpha_src, mx.inputs['Fac']); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(diff.outputs[0], mx.inputs[2])
            shader = mx.outputs[0]
        nt.links.new(shader, out.inputs['Surface'])
        for s_ in ('Displacement', 'Volume'):
            if s_ in out.inputs and out.inputs[s_].is_linked:
                nt.links.remove(out.inputs[s_].links[0])
        mat['drawn'] = 1
        return
    diff = nt.nodes.new('ShaderNodeBsdfDiffuse'); diff.inputs['Color'].default_value = (1, 1, 1, 1)
    s2r = nt.nodes.new('ShaderNodeShaderToRGB'); nt.links.new(diff.outputs[0], s2r.inputs[0])
    bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(s2r.outputs['Color'], bw.inputs[0])
    rp = _ramp(nt, tones, steps); nt.links.new(bw.outputs[0], rp.inputs['Fac'])
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    if col_src is not None:
        nt.links.new(col_src, mul.inputs['A'])
    else:
        mul.inputs['A'].default_value = (*col_val, 1)
    nt.links.new(rp.outputs['Color'], mul.inputs['B'])
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(mul.outputs['Result'], em.inputs['Color'])
    shader = em.outputs[0]
    if alpha_src is not None:                                       # lashes, brows cards: keep their cut-out
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(alpha_src, mx.inputs['Fac']); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        shader = mx.outputs[0]
    nt.links.new(shader, out.inputs['Surface'])
    for s in ('Displacement', 'Volume'):
        if s in out.inputs and out.inputs[s].is_linked:
            nt.links.remove(out.inputs[s].links[0])
    mat['drawn'] = 1


def toon(skip=(), mode='eevee'):
    for m in bpy.data.materials:
        if m.name not in skip:
            toon_material(m, mode=mode)


def ink(thickness=1.7, color=INK, crease_deg=134.0, inner=True, skip=()):
    """Freestyle pen lines, rendered as their own pass (paint_post lays them on after the brush filter)."""
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = 'ABSOLUTE'
    main = sc.view_layers[0]
    vl = main
    if skip:                                             # far crowds etc: no ink (and Freestyle never sees them -
        main.use_freestyle = False                       # tracing ~90 full soldiers took 45+ min). Lines are drawn
        vl = sc.view_layers.get('ink') or sc.view_layers.new('ink')   # on their own layer, 1 sample, near things only
        vl.use_freestyle = True; vl.samples = 1
        for lc in vl.layer_collection.children:
            if lc.name in skip:
                lc.exclude = True
    fs = vl.freestyle_settings; fs.as_render_pass = True
    fs.crease_angle = math.radians(crease_deg); fs.use_smoothness = True
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new('ink')
    ls.select_by_visibility = True; ls.visibility = 'VISIBLE'
    ls.select_silhouette = ls.select_border = True
    # creases / ridges on dense body meshes draw every skin bump as a scribble: outlines only (artists draw
    # the shape, not the texture); inner lines come from material edges (border) and contours
    ls.select_crease = False; ls.select_ridge_valley = False; ls.select_suggestive_contour = False
    ls.select_contour = True; ls.select_external_contour = True
    st = ls.linestyle or bpy.data.linestyles.new('ink'); ls.linestyle = st
    st.color = color; st.thickness = thickness; st.thickness_position = 'CENTER'
    st.use_chaining = True; st.chaining = 'PLAIN'
    st.caps = 'ROUND'
    if not any(m.type == 'CALLIGRAPHY' for m in st.thickness_modifiers):
        cal = st.thickness_modifiers.new('pen', 'CALLIGRAPHY')       # a nib: thick one way, thin the other
        cal.thickness_min = thickness * 0.35; cal.thickness_max = thickness * 1.35; cal.orientation = math.radians(60)
        tap = st.thickness_modifiers.new('taper', 'ALONG_STROKE')      # strokes start and end thin, like a brush
        tap.blend = 'MULTIPLY'; tap.mapping = 'CURVE'
        cv = tap.curve; pts = cv.curves[0].points
        pts[0].location = (0.0, 0.25); pts[1].location = (1.0, 0.25)
        pts.new(0.2, 1.0); pts.new(0.8, 1.0); cv.update()
        noise = st.geometry_modifiers.new('wobble', 'PERLIN_NOISE_1D')  # a hand is never perfectly steady
        noise.frequency = 12.0; noise.amplitude = 0.9
    return st


def paint_post(brush=5, grade=True):
    """Kuwahara brush filter on colour, ink on top, then a muted warm film grade."""
    sc = bpy.context.scene
    ng = bpy.data.node_groups.new('drawn_comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
    if not any(s.in_out == 'OUTPUT' for s in ng.interface.items_tree):
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = ng.nodes.new('CompositorNodeRLayers')
    ku = ng.nodes.new('CompositorNodeKuwahara')
    ku.inputs['Size'].default_value = brush
    try:
        ku.inputs['Type'].default_value = 'Anisotropic'
    except (TypeError, ValueError):
        pass
    ng.links.new(rl.outputs['Image'], ku.inputs['Image'])
    last = ku.outputs[0]
    if 'Freestyle' in rl.outputs:
        ao = ng.nodes.new('CompositorNodeAlphaOver')
        ng.links.new(last, ao.inputs['Background']); ng.links.new(rl.outputs['Freestyle'], ao.inputs['Foreground'])
        last = ao.outputs[0]
    if grade:
        hsv = ng.nodes.new('CompositorNodeHueSat')
        for k, v in (('Saturation', 0.88), ('Value', 1.0)):
            if k in hsv.inputs:
                hsv.inputs[k].default_value = v
        ng.links.new(last, hsv.inputs['Image']); last = hsv.outputs['Image']
    go = ng.nodes.new('NodeGroupOutput')
    ng.links.new(last, go.inputs[0])
    return ng


def _out(rl, *names):
    for n in names:
        if n in rl.outputs:
            return rl.outputs[n]
    raise KeyError(f'none of {names} in render layer outputs {[o.name for o in rl.outputs]}')


def paint_post_cycles(brush=5, tones=TONES, steps=STEPS, light_scale=1.0):
    """Toon from passes: tone = ramp(brightness of the diffuse light that reached the surface, shadows included),
    colour = the flat diffuse colour; sky = environment pass; brush filter; ink on top; muted grade."""
    sc = bpy.context.scene
    vl = sc.view_layers[0]                               # colour/light passes from the main layer
    vl.use_pass_diffuse_direct = vl.use_pass_diffuse_indirect = vl.use_pass_diffuse_color = True
    vl.use_pass_environment = True
    vl.cycles.denoising_store_passes = True
    sc.render.film_transparent = True
    ng = bpy.data.node_groups.new('drawn_comp', 'CompositorNodeTree'); sc.compositing_node_group = ng
    if not any(getattr(s, 'in_out', '') == 'OUTPUT' for s in ng.interface.items_tree):
        ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    N = ng.nodes.new; L = ng.links.new
    rl = N('CompositorNodeRLayers')
    def mixrgb(blend):                                               # Blender 5 compositor: the shared Mix node
        m = N('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = blend; m.inputs[0].default_value = 1.0
        return m                                                     # colour sockets: inputs[6] A, [7] B, outputs[2]
    light = mixrgb('ADD')
    L(_out(rl, 'Diffuse Direct', 'DiffDir'), light.inputs[6]); L(_out(rl, 'Diffuse Indirect', 'DiffInd'), light.inputs[7])
    dn = N('CompositorNodeDenoise')                                  # clean light = clean tone edges
    L(light.outputs[2], dn.inputs['Image'])
    try:
        L(_out(rl, 'Denoising Normal'), dn.inputs['Normal']); L(_out(rl, 'Denoising Albedo'), dn.inputs['Albedo'])
    except KeyError:
        pass
    bw = N('CompositorNodeRGBToBW'); L(dn.outputs[0], bw.inputs[0])
    mul = N('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = light_scale
    L(bw.outputs[0], mul.inputs[0])
    rp = N('ShaderNodeValToRGB'); cr = rp.color_ramp; cr.interpolation = 'CONSTANT'
    cr.elements[0].position = 0.0; cr.elements[0].color = (*tones[0], 1)
    cr.elements[1].position = steps[0]; cr.elements[1].color = (*tones[1], 1)
    e = cr.elements.new(steps[1]); e.color = (*tones[2], 1)
    L(mul.outputs[0], rp.inputs[0])
    col = mixrgb('MULTIPLY')
    L(_out(rl, 'Diffuse Color', 'DiffCol'), col.inputs[6]); L(rp.outputs['Color'], col.inputs[7])
    sa = N('CompositorNodeSetAlpha'); L(col.outputs[2], sa.inputs['Image']); L(rl.outputs['Alpha'], sa.inputs['Alpha'])
    ao_sky = N('CompositorNodeAlphaOver')
    L(_out(rl, 'Environment', 'Env'), ao_sky.inputs['Background']); L(sa.outputs[0], ao_sky.inputs['Foreground'])
    ku = N('CompositorNodeKuwahara'); ku.inputs['Size'].default_value = brush
    try:
        ku.inputs['Type'].default_value = 'Anisotropic'
    except (TypeError, ValueError):
        pass
    L(ao_sky.outputs[0], ku.inputs['Image']); last = ku.outputs[0]
    rli = rl
    if sc.view_layers.get('ink') is not None:            # lines come from the ink-only layer
        rli = N('CompositorNodeRLayers'); rli.layer = 'ink'
    if 'Freestyle' in rli.outputs:
        ao = N('CompositorNodeAlphaOver'); L(last, ao.inputs['Background']); L(rli.outputs['Freestyle'], ao.inputs['Foreground'])
        last = ao.outputs[0]
    hsv = N('CompositorNodeHueSat')
    if 'Saturation' in hsv.inputs:
        hsv.inputs['Saturation'].default_value = 0.9
    L(last, hsv.inputs['Image']); last = hsv.outputs['Image']
    go = N('NodeGroupOutput'); L(last, go.inputs[0])
    return ng


def apply_cycles(lines=1.7, brush=5, samples=32, light_scale=1.0, no_ink=('far_crowd',)):
    """The drawn look on CYCLES (CPU, laptop RAM or the cloud) - same look as apply(), no GPU needed."""
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 2
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'; sc.view_settings.exposure = 0.0
    toon(mode='cycles')
    ink(lines, skip=tuple(c for c in no_ink if c in bpy.data.collections))
    paint_post_cycles(brush, light_scale=light_scale)


def apply(lines=1.7, brush=5):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    toon()
    ink(lines)
    paint_post(brush)
