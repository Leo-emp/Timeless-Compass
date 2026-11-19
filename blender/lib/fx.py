# FX without fluid simulation (too heavy for the laptop; same trick film/game artists use for distant fire):
#   smoke_column - a tall volume whose density is animated 4D noise, rising, widening and thinning with height
#   flames       - a small glowing volume coloured by real fire temperature (blackbody ~1500-1900 K)
#   fire_light   - a point light that FLICKERS (keyframed noise), so firelight dances on faces and walls
#   embers       - tiny glowing sparks drifting up (particles)
# Burning Athens, braziers, camp fires, burning ships, battlefield smoke.
import math
import random

import bpy
from mathutils import Vector


def _volume_material(name, density, color, emission=0.0, temp=1700.0, rise_speed=0.6, scale=1.2, frames=(1, 240), wind=0.0):
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    out = nt.nodes['Material Output']; L = nt.links.new
    v = nt.nodes.new('ShaderNodeVolumePrincipled')
    v.inputs['Color'].default_value = (*color, 1)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'
    noise.inputs['Scale'].default_value = scale; noise.inputs['Detail'].default_value = 6; noise.inputs['Roughness'].default_value = 0.6
    # rise: sample the noise lower and lower over time -> the pattern moves UP through the column
    mp = nt.nodes.new('ShaderNodeMapping'); L(tc.outputs['Generated'], mp.inputs['Vector']); L(mp.outputs['Vector'], noise.inputs['Vector'])
    mp.inputs['Location'].default_value = (0, 0, 0); mp.inputs['Location'].keyframe_insert('default_value', frame=frames[0])
    mp.inputs['Location'].default_value = (0, 0, -rise_speed * (frames[1] - frames[0]) / 24)
    mp.inputs['Location'].keyframe_insert('default_value', frame=frames[1])
    noise.inputs['W'].default_value = 0.0; noise.inputs['W'].keyframe_insert('default_value', frame=frames[0])
    noise.inputs['W'].default_value = (frames[1] - frames[0]) / 24 * 0.3; noise.inputs['W'].keyframe_insert('default_value', frame=frames[1])
    for fc in (m.node_tree.animation_data.action.fcurves if m.node_tree.animation_data and hasattr(m.node_tree.animation_data.action, 'fcurves') else []):
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
    # shape: dense near the centre line, thinning with height; sharp-ish puffs from the noise
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs['Vector'])
    # WIND: the plume's centre line drifts downwind (+X) as it rises (shift grows with height^1.5, like real smoke)
    zp = nt.nodes.new('ShaderNodeMath'); zp.operation = 'POWER'; zp.inputs[1].default_value = 1.5; L(sep.outputs['Z'], zp.inputs[0])
    drift = nt.nodes.new('ShaderNodeMath'); drift.operation = 'MULTIPLY_ADD'; drift.inputs[1].default_value = wind
    drift.inputs[2].default_value = 0.5; L(zp.outputs[0], drift.inputs[0])
    dx = nt.nodes.new('ShaderNodeMath'); dx.operation = 'SUBTRACT'; L(sep.outputs['X'], dx.inputs[0]); L(drift.outputs[0], dx.inputs[1])
    dy = nt.nodes.new('ShaderNodeMath'); dy.operation = 'SUBTRACT'; dy.inputs[1].default_value = 0.5; L(sep.outputs['Y'], dy.inputs[0])
    cl = nt.nodes.new('ShaderNodeCombineXYZ'); L(dx.outputs[0], cl.inputs['X']); L(dy.outputs[0], cl.inputs['Y'])
    r = nt.nodes.new('ShaderNodeVectorMath'); r.operation = 'LENGTH'; L(cl.outputs['Vector'], r.inputs[0])
    widen = nt.nodes.new('ShaderNodeMath'); widen.operation = 'MULTIPLY_ADD'
    L(sep.outputs['Z'], widen.inputs[0]); widen.inputs[1].default_value = 0.32; widen.inputs[2].default_value = 0.14   # radius grows with height
    core = nt.nodes.new('ShaderNodeMath'); core.operation = 'DIVIDE'; L(r.outputs['Value'], core.inputs[0]); L(widen.outputs[0], core.inputs[1])
    fall = nt.nodes.new('ShaderNodeMapRange'); fall.inputs['From Min'].default_value = 0.0; fall.inputs['From Max'].default_value = 1.0
    fall.inputs['To Min'].default_value = 1.0; fall.inputs['To Max'].default_value = 0.0; L(core.outputs[0], fall.inputs['Value'])
    thin = nt.nodes.new('ShaderNodeMapRange'); thin.inputs['To Min'].default_value = 1.0; thin.inputs['To Max'].default_value = 0.25
    L(sep.outputs['Z'], thin.inputs['Value'])
    puffs = nt.nodes.new('ShaderNodeMapRange'); puffs.inputs['From Min'].default_value = 0.42; puffs.inputs['From Max'].default_value = 0.72
    L(noise.outputs['Fac'], puffs.inputs['Value'])
    d1 = nt.nodes.new('ShaderNodeMath'); d1.operation = 'MULTIPLY'; L(fall.outputs['Result'], d1.inputs[0]); L(thin.outputs['Result'], d1.inputs[1])
    d2 = nt.nodes.new('ShaderNodeMath'); d2.operation = 'MULTIPLY'; L(d1.outputs[0], d2.inputs[0]); L(puffs.outputs['Result'], d2.inputs[1])
    d3 = nt.nodes.new('ShaderNodeMath'); d3.operation = 'MULTIPLY'; d3.inputs[1].default_value = density; L(d2.outputs[0], d3.inputs[0])
    L(d3.outputs[0], v.inputs['Density'])
    if emission:
        L(d2.outputs[0], v.inputs['Emission Strength'])
        v.inputs['Emission Strength'].default_value = emission
        bb = nt.nodes.new('ShaderNodeBlackbody'); bb.inputs['Temperature'].default_value = temp
        L(bb.outputs['Color'], v.inputs['Emission Color'])
        em = nt.nodes.new('ShaderNodeMath'); em.operation = 'MULTIPLY'; em.inputs[1].default_value = emission
        L(d2.outputs[0], em.inputs[0]); L(em.outputs[0], v.inputs['Emission Strength'])
    L(v.outputs[0], out.inputs['Volume'])
    return m


def smoke_column(loc, height=60.0, width=14.0, density=0.25, color=(0.12, 0.11, 0.1), frames=(1, 240), name='smoke', wind=0.3):
    """A rising column of dark smoke (burning city, burning ship) that leans and spreads DOWNWIND (+X) as it rises.
    `density` per metre inside the plume; `wind` 0 = straight up, 0.3 = a steady sea breeze."""
    w = width * (2.2 + 2.0 * wind)                                # the domain must be wide enough for the drift
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0] + w * 0.5 * wind, loc[1], loc[2] + height / 2))
    o = bpy.context.object; o.name = name; o.scale = (w, width * 2.2, height)
    o.data.materials.append(_volume_material(f'{name}_mat', density, color, scale=1.4, rise_speed=0.9, frames=frames,
                                             wind=wind * 0.6))
    o.visible_shadow = True
    return o


def flames(loc, height=2.5, width=1.4, intensity=25.0, temp=1750.0, frames=(1, 240), name='flames'):
    """Glowing fire volume coloured by blackbody temperature (~1750 K = orange flame)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0], loc[1], loc[2] + height / 2))
    o = bpy.context.object; o.name = name; o.scale = (width, width, height)
    o.data.materials.append(_volume_material(f'{name}_mat', 1.5, (1.0, 0.55, 0.25), emission=intensity, temp=temp,
                                             scale=3.0, rise_speed=2.2, frames=frames))
    o.visible_shadow = False
    return o


def fire_light(loc, power=800.0, color=(1.0, 0.5, 0.18), radius=0.6, frames=(1, 240), seed=0, name='fire_light'):
    """A point light that flickers like real flames: random brightness every 2-3 frames (+-35 %)."""
    bpy.ops.object.light_add(type='POINT', location=tuple(loc))
    o = bpy.context.object; o.name = name
    o.data.color = color; o.data.shadow_soft_size = radius
    rnd = random.Random(seed)
    f = frames[0]
    while f <= frames[1]:
        o.data.energy = power * rnd.uniform(0.65, 1.35)
        o.data.keyframe_insert('energy', frame=f)
        f += rnd.choice((2, 3))
    return o


def embers(loc, count=300, area=3.0, rise=6.0, frames=(1, 240), name='embers'):
    """Small glowing sparks drifting upward from a fire."""
    bpy.ops.mesh.primitive_plane_add(size=area, location=tuple(loc))
    emitter = bpy.context.object; emitter.name = name; emitter.hide_render = True
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.012, location=(0, 0, -100))
    spark = bpy.context.object; spark.name = name + '_spark'
    m = bpy.data.materials.new(name + '_glow'); nt = m.node_tree
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 40
    bb = nt.nodes.new('ShaderNodeBlackbody'); bb.inputs['Temperature'].default_value = 1600
    nt.links.new(bb.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    spark.data.materials.append(m)
    ps = emitter.modifiers.new('sparks', 'PARTICLE_SYSTEM').particle_system.settings
    ps.count = count; ps.frame_start = frames[0] - 60; ps.frame_end = frames[1]; ps.lifetime = 70; ps.lifetime_random = 0.6
    ps.normal_factor = rise / 4; ps.factor_random = 1.2; ps.effector_weights.gravity = -0.05
    ps.render_type = 'OBJECT'; ps.instance_object = spark; ps.particle_size = 1.0; ps.size_random = 0.6
    ps.brownian_factor = 0.6
    return emitter


def bird_flock(center, count=24, radius=40.0, height=(18.0, 45.0), frames=(1, 240), wing=0.45, seed=0,
               color=(0.75, 0.74, 0.72), name='birds'):
    """Gulls wheeling over the sea / crows over a battlefield, read from a distance: each bird = a small body + two
    wings that FLAP (keyframed rotation, own rhythm) on its own circling path, height and speed. Cheap: ~10 faces."""
    import bmesh
    rnd = random.Random(seed)
    mat = bpy.data.materials.new(name + '_feathers'); mat.use_fake_user = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*color, 1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.8
    root = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(root)
    root.location = center
    for i in range(count):
        body = bpy.data.objects.new(f'{name}_{i}', None); bpy.context.scene.collection.objects.link(body)
        body.parent = root
        bpy.ops.mesh.primitive_uv_sphere_add(segments=6, ring_count=4, radius=0.08)
        torso = bpy.context.object; torso.scale = (0.45, 1.6, 0.45); torso.parent = body; torso.data.materials.append(mat)
        torso.location = (0, 0, 0)
        for sgn in (-1, 1):                                    # wings: thin triangles hinged at the shoulder
            me = bpy.data.meshes.new(f'{name}_{i}_w{sgn}')
            me.from_pydata([(0, 0.05, 0), (0, -0.07, 0), (sgn * wing, -0.02, 0)], [], [(0, 1, 2)])
            w = bpy.data.objects.new(f'{name}_{i}_wing{sgn}', me); bpy.context.scene.collection.objects.link(w)
            w.parent = body; w.data.materials.append(mat)
            flap_hz = rnd.uniform(2.2, 3.2); ph = rnd.uniform(0, 6.28)
            for f in range(frames[0], frames[1] + 1, 2):
                t = f / 24
                glide = 0.35 if math.sin(t * 0.7 + ph) > 0.6 else 1.0          # gulls glide between flaps
                w.rotation_euler = (0, sgn * math.radians(28 * glide * math.sin(2 * math.pi * flap_hz * t + ph)), 0)
                w.keyframe_insert('rotation_euler', frame=f)
        r = radius * rnd.uniform(0.4, 1.0); h = rnd.uniform(*height); sp = rnd.uniform(0.08, 0.18) * rnd.choice((-1, 1))
        a0 = rnd.uniform(0, 6.28)
        for f in range(frames[0], frames[1] + 1, 4):
            a = a0 + sp * f / 24 * 2 * math.pi / 6
            body.location = (r * math.cos(a), r * math.sin(a), h + 2.0 * math.sin(f / 24 * 0.5 + a0))
            body.rotation_euler = (0, math.radians(-12 * (1 if sp > 0 else -1)), a + (math.pi if sp > 0 else 0))
            body.keyframe_insert('location', frame=f); body.keyframe_insert('rotation_euler', frame=f)
    return root


def night_sky(moon_elev=24.0, moon_azimuth=200.0, moon_power=0.35, stars=1.0):
    """Night: deep blue-black sky gradient + a STARFIELD (tiny bright points from a thresholded noise, so they never
    tile), and cold moonlight as a weak sun lamp (key) - the classic film night look is blue key + warm practicals
    (lanterns, fires)."""
    w = bpy.data.worlds.new('night'); bpy.context.scene.world = w
    nt = w.node_tree; L = nt.links.new
    bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    grad = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], grad.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.5; ramp.color_ramp.elements[0].color = (0.012, 0.016, 0.03, 1)   # horizon
    ramp.color_ramp.elements[1].position = 0.9; ramp.color_ramp.elements[1].color = (0.002, 0.003, 0.008, 1)  # zenith
    L(grad.outputs['Z'], ramp.inputs['Fac'])
    vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 900
    L(tc.outputs['Generated'], vor.inputs['Vector'])
    thr = nt.nodes.new('ShaderNodeMapRange'); thr.inputs['From Min'].default_value = 0.0; thr.inputs['From Max'].default_value = 0.035
    thr.inputs['To Min'].default_value = 1.0; thr.inputs['To Max'].default_value = 0.0; L(vor.outputs['Distance'], thr.inputs['Value'])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 8.0; L(thr.outputs['Result'], pw.inputs[0])
    st = nt.nodes.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; st.inputs[1].default_value = 3.0 * stars; L(pw.outputs[0], st.inputs[0])
    add = nt.nodes.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'; add.inputs['Factor'].default_value = 1.0
    L(ramp.outputs['Color'], add.inputs['A']); L(st.outputs[0], add.inputs['B'])
    L(add.outputs['Result'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 1.0
    l = bpy.data.lights.new('moon', 'SUN'); l.energy = moon_power; l.color = (0.62, 0.72, 1.0); l.angle = math.radians(0.5)
    o = bpy.data.objects.new('moon', l); bpy.context.scene.collection.objects.link(o)
    o.rotation_euler = (math.radians(90 - moon_elev), 0, math.radians(moon_azimuth))
    return w


def wake(start, heading_deg, length=60.0, width=6.0, z=0.05, name='wake'):
    """A ship's foam wake: a V-shaped trail of churned white water spreading and fading behind the stern (plane with a
    noise-broken foam mask, transparent elsewhere). `start` = stern position, heading = the ship's travel direction."""
    import bmesh
    verts, faces = [], []
    n = 30
    for i in range(n + 1):
        t = i / n
        half = width * 0.3 + width * t
        verts += [(-half, -t * length, z), (half, -t * length, z)]
    for i in range(n):
        a = 2 * i
        faces.append((a, a + 1, a + 3, a + 2))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uv = me.uv_layers.new()
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            uv.data[li].uv = (vi % 2, (vi // 2) / n)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    m = bpy.data.materials.new(name + '_foam'); m.use_fake_user = True
    nt = m.node_tree; L = nt.links.new; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.85, 0.88, 0.9, 1); b.inputs['Roughness'].default_value = 0.6
    uvn = nt.nodes.new('ShaderNodeUVMap'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(uvn.outputs['UV'], sep.inputs[0])
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 14; noise.inputs['Detail'].default_value = 8
    tc = nt.nodes.new('ShaderNodeTexCoord'); L(tc.outputs['Object'], noise.inputs['Vector'])
    fade = nt.nodes.new('ShaderNodeMapRange'); fade.inputs['To Min'].default_value = 1.0; fade.inputs['To Max'].default_value = 0.0
    L(sep.outputs['Y'], fade.inputs['Value'])
    edge = nt.nodes.new('ShaderNodeMath'); edge.operation = 'PINGPONG'; edge.inputs[1].default_value = 0.5; L(sep.outputs['X'], edge.inputs[0])
    e2 = nt.nodes.new('ShaderNodeMapRange'); e2.inputs['From Max'].default_value = 0.25; L(edge.outputs[0], e2.inputs['Value'])
    foam = nt.nodes.new('ShaderNodeMapRange'); foam.inputs['From Min'].default_value = 0.45; foam.inputs['From Max'].default_value = 0.65
    L(noise.outputs['Fac'], foam.inputs['Value'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; L(foam.outputs['Result'], m1.inputs[0]); L(fade.outputs['Result'], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; L(m1.outputs[0], m2.inputs[0]); L(e2.outputs['Result'], m2.inputs[1])
    L(m2.outputs[0], b.inputs['Alpha'])
    m.blend_method = 'HASHED' if hasattr(m, 'blend_method') else None
    me.materials.append(m)
    o.location = start; o.rotation_euler.z = math.radians(heading_deg)
    return o
