# SETS: places, built from code. First set: the strait of Salamis at dusk, September 480 BC.
# Real ocean waves (Blender's Ocean modifier = a physically based wave spectrum), physical sky, terrain,
# a stone harbour wall, a rowboat with a lantern, the glow of burning Athens, the Persian fleet's lights, haze.
# Geography (design source): the strait between Salamis island and the Attic coast; Mount Aigaleos above it.
import math

import bpy
import numpy as np
from mathutils import Vector

from lib.common import area_light, link, principled, sky_world, sun_light


def water_material():
    m = bpy.data.materials.new('sea'); m.use_fake_user = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.004, 0.018, 0.03, 1)
    b.inputs['Coat Weight'].default_value = 0.0
    b.inputs['Roughness'].default_value = 0.06
    b.inputs['IOR'].default_value = 1.33
    b.inputs['Specular IOR Level'].default_value = 0.6
    return m


def ocean(size=60.0, choppiness=1.2, wave_scale=0.6, repeat=4, resolution=12, frame=1):
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    o = bpy.context.object; o.name = 'ocean'
    oc = o.modifiers.new('ocean', 'OCEAN')
    oc.geometry_mode = 'GENERATE'; oc.size = 1.0; oc.spatial_size = int(size); oc.resolution = resolution
    oc.repeat_x = repeat; oc.repeat_y = repeat
    oc.use_foam = False
    oc.choppiness = choppiness; oc.wave_scale = wave_scale; oc.wind_velocity = 6.0; oc.time = frame / 24.0
    oc.use_normals = True
    o.location = (-size * repeat / 2, -size * 0.6, 0)
    o.data.materials.append(water_material())
    bpy.ops.object.shade_smooth()
    return o


def hillside_material(name, rock=(0.22, 0.18, 0.15)):
    """Greek hillside: pale limestone rock with dark patches of scrub (maquis), fine rocky bump."""
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    co = nt.nodes.new('ShaderNodeTexCoord')
    patch = nt.nodes.new('ShaderNodeTexNoise'); patch.inputs['Scale'].default_value = 0.02; patch.inputs['Detail'].default_value = 12
    L(co.outputs['Object'], patch.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (0.05, 0.06, 0.035, 1)   # scrub
    ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (*rock, 1)              # rock
    L(patch.outputs['Fac'], ramp.inputs['Fac']); L(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.95
    grain = nt.nodes.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 0.6; grain.inputs['Detail'].default_value = 14
    L(co.outputs['Object'], grain.inputs['Vector'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.7; bp.inputs['Distance'].default_value = 3.0
    L(grain.outputs['Fac'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def land(name, loc, scale, height, rough=1.0, color=(0.22, 0.18, 0.15), noise=30.0, seed=0):
    """A hill/mountain/island: a dense plane pushed up by noise, falling to the sea at its edges."""
    res = 260 if height > 80 else 160                           # big hills need more points to carry ridges
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=res, y_subdivisions=res, size=1, location=loc)
    o = bpy.context.object; o.name = name
    vg = o.vertex_groups.new(name='inland')                     # how much rough detail each point gets
    for v in o.data.vertices:                                    # shape the hill in unit space ...
        r = math.hypot(v.co.x * 2, v.co.y * 2)
        falloff = max(0.0, 1 - r) ** 1.4
        v.co.x *= scale[0]; v.co.y *= scale[1]; v.co.z = falloff * height   # ... then size it in METRES
        vg.add([v.index], min(1.0, falloff * 1.6), 'REPLACE')
    o.data.update()                                              # (scaling the object instead would also scale
                                                                 #  the noise displacement by up to 200x)
    tex = bpy.data.textures.new(f'{name}_n', 'MUSGRAVE') if hasattr(bpy.types, 'MusgraveTexture') else bpy.data.textures.new(f'{name}_n', 'CLOUDS')
    tex.noise_scale = noise
    if hasattr(tex, 'noise_depth'):
        tex.noise_depth = 6
    d = o.modifiers.new('rough', 'DISPLACE'); d.texture = tex; d.strength = rough; d.mid_level = 0.35
    d.direction = 'Z'; d.vertex_group = 'inland'; d.texture_coords = 'GLOBAL'   # straight up, fading at the shore
    fine = bpy.data.textures.new(f'{name}_fine', 'CLOUDS'); fine.noise_scale = noise / 6; fine.noise_depth = 6
    d2 = o.modifiers.new('rocks', 'DISPLACE'); d2.texture = fine; d2.strength = rough * 0.18; d2.mid_level = 0.5
    d2.direction = 'Z'; d2.vertex_group = 'inland'; d2.texture_coords = 'GLOBAL'  # gullies and rocks
    if height > 80:
        # RIDGES: real Greek hills are carved by erosion into spines and gullies, not smooth cones.
        # Voronoi "F2 - F1" = distance between the two nearest cells -> sharp crease lines = ridgelines.
        rt = bpy.data.textures.new(f'{name}_ridges', 'VORONOI')
        rt.distance_metric = 'DISTANCE'; rt.color_mode = 'INTENSITY'
        rt.weight_1, rt.weight_2, rt.weight_3, rt.weight_4 = -1.0, 1.0, 0.0, 0.0
        rt.noise_scale = noise * 0.9; rt.noise_intensity = 1.0
        d3 = o.modifiers.new('ridges', 'DISPLACE'); d3.texture = rt; d3.strength = rough * 0.55; d3.mid_level = 0.15
        d3.direction = 'Z'; d3.vertex_group = 'inland'; d3.texture_coords = 'GLOBAL'
        o.modifiers.move(len(o.modifiers) - 1, 1)                  # before the fine rocks
    o.data.materials.append(hillside_material(f'{name}_mat', color))
    bpy.ops.object.shade_smooth()
    return o


def weathered_stone():
    """Old harbour limestone: blotchy light/dark colour, lichen-dark patches, pitted bump."""
    m = bpy.data.materials.new('weathered_stone'); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 3.0; n.inputs['Detail'].default_value = 10
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.09, 0.08, 0.07, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.33, 0.29, 0.24, 1)
    L(n.outputs['Fac'], ramp.inputs['Fac']); L(ramp.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.93
    pit = nt.nodes.new('ShaderNodeTexVoronoi'); pit.inputs['Scale'].default_value = 40
    fine = nt.nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 60; fine.inputs['Detail'].default_value = 12
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
    L(pit.outputs['Distance'], add.inputs[0]); L(fine.outputs['Fac'], add.inputs[1])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6
    L(add.outputs[0], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def stone_wall(x0, x1, y, top_z, depth=2.0):
    """A harbour wall of big cut stone blocks (slightly irregular), the dock the camera stands on."""
    mat = weathered_stone()
    rng = np.random.default_rng(3)
    blocks = []
    x = x0
    row_h = 0.42
    for row in range(int((top_z + 0.6) / row_h) + 1):
        x = x0 - rng.random() * 0.6
        z = top_z - row * row_h - row_h / 2
        while x < x1:
            w = 0.9 + rng.random() * 0.7
            bpy.ops.mesh.primitive_cube_add(size=1, location=(x + w / 2, y, z))
            b = bpy.context.object; b.scale = (w - 0.02, depth, row_h - 0.02)
            bv = b.modifiers.new('bevel', 'BEVEL'); bv.width = 0.025; bv.segments = 3
            b.rotation_euler = (0, 0, (rng.random() - 0.5) * 0.01)
            b.data.materials.append(mat)
            blocks.append(b); x += w
    return blocks


def rowboat(loc, rot_z=0.0):
    """Small wooden rowing boat: half an ellipsoid hull with thickness, two thwarts, oars resting."""
    wood = principled('boat_wood', (0.18, 0.11, 0.06), rough=0.7, bump=0.4, bump_scale=60)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=loc)
    h = bpy.context.object; h.name = 'rowboat'
    for v in h.data.vertices:
        if v.co.z > 0:
            v.co.z = 0
    h.scale = (2.2, 0.75, 0.55); h.rotation_euler = (0, 0, rot_z)
    h.modifiers.new('thick', 'SOLIDIFY').thickness = 0.04
    h.data.materials.append(wood); bpy.ops.object.shade_smooth()
    parts = [h]
    for k, dx in enumerate((-0.6, 0.5)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(loc[0] + dx * math.cos(rot_z), loc[1] + dx * math.sin(rot_z), loc[2] - 0.08))
        t = bpy.context.object; t.scale = (0.18, 1.35, 0.04); t.rotation_euler = (0, 0, rot_z); t.data.materials.append(wood); parts.append(t)
    return parts


def lantern(loc, power=60.0):
    """Clay/bronze lantern with a flame: warm emissive core + a small point light."""
    glow = bpy.data.materials.new('flame'); glow.use_fake_user = True
    b = glow.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (1.0, 0.55, 0.18, 1); b.inputs['Emission Strength'].default_value = 25
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=loc); f = bpy.context.object; f.data.materials.append(glow)
    l = bpy.data.lights.new('lantern', 'POINT'); l.energy = power; l.color = (1.0, 0.6, 0.25); l.shadow_soft_size = 0.05
    lo = link(bpy.data.objects.new('lantern_light', l)); lo.location = loc
    return f, lo


def distant_lights(center, spread, count, z=0.25, seed=5, power=6.0):
    """Many tiny flames far away: the Persian fleet waiting in the dark."""
    glow = bpy.data.materials.new('far_flame'); glow.use_fake_user = True
    b = glow.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (1.0, 0.6, 0.25, 1); b.inputs['Emission Strength'].default_value = power
    rng = np.random.default_rng(seed)
    for i in range(count):
        p = (center[0] + (rng.random() - 0.5) * spread[0], center[1] + (rng.random() - 0.5) * spread[1], z + rng.random() * 0.4)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.12, location=p)
        bpy.context.object.data.materials.append(glow)


def fire_glow(loc, radius=8.0, strength=40.0):
    """The glow of a burning city on the horizon: a big soft emissive shape."""
    m = bpy.data.materials.new('city_fire'); m.use_fake_user = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Emission Color'].default_value = (1.0, 0.35, 0.08, 1); b.inputs['Emission Strength'].default_value = strength
    b.inputs['Base Color'].default_value = (0, 0, 0, 1)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc); s = bpy.context.object
    s.scale = (1.6, 0.4, 0.35); s.data.materials.append(m)
    return s


def haze(size=(7000, 7000, 700), density=0.00009, color=(1.0, 0.62, 0.42)):
    """Thin atmosphere so distance fades into the dusk (cinematic depth)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, size[1] * 0.35, size[2] / 2 - 1))
    c = bpy.context.object; c.name = 'haze'; c.scale = size
    m = bpy.data.materials.new('haze'); m.use_fake_user = True
    nt = m.node_tree; nt.nodes.remove(nt.nodes['Principled BSDF'])
    v = nt.nodes.new('ShaderNodeVolumePrincipled'); v.inputs['Density'].default_value = density
    v.inputs['Color'].default_value = (*color, 1)
    nt.links.new(v.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
    c.data.materials.append(m)
    return c


def far_sea(size=12000.0):
    """Calm water from the end of the wave tile to the horizon."""
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, size / 2 - 60, -0.6))   # below the wave troughs (else flat mirror patches)
    o = bpy.context.object; o.name = 'far_sea'
    o.data.materials.append(bpy.data.materials.get('sea') or water_material())
    return o


def salamis_dusk(sun_elev=4.0, sun_azimuth=0.0):
    """The whole strait. Camera side = -Y (on the harbour wall); the sunset is ahead (+Y)."""
    sky_world(sun_elev_deg=sun_elev, sun_rot_deg=sun_azimuth, strength=1.0, dust=9.0, air=2.2)
    sun_light('sun', 4.0, (1.0, 0.5, 0.25), sun_elev, sun_azimuth + 180, angle_deg=1.0)
    ocean()
    # real scale: the strait is ~1.5 km wide; Salamis' hills ~150-250 m; Mount Aigaleos ~450 m, farther off
    land('salamis_island', (300, 1500, 0), (3200, 700, 1), 160, rough=120, noise=260, seed=1)
    land('aigaleos', (-2200, 2600, 0), (3000, 1100, 1), 420, rough=260, noise=420, seed=2)
    land('attic_coast', (-260, 260, 0), (420, 160, 1), 18, rough=14, noise=60, color=(0.2, 0.17, 0.14), seed=3)
    far_sea()
    fire_glow((-1600, 2300, 25), radius=60, strength=30)               # Athens burning, far away
    distant_lights((150, 600, 0), (900, 250), 220, power=10)          # Persian ships' lanterns
    stone_wall(-8, 8, -6, 0.8, depth=2.2)
    rowboat((2.4, -3.4, 0.32), rot_z=math.radians(12))
    lantern((3.4, -3.25, 0.95))
    haze()


def salamis_film_light():
    """Shot lighting for salamis_dusk (tested in hero_salamis): strong low golden sun from behind-left (rim on hair,
    beard and cloth edges + long shadows), dim cool sky fill, warm stone bounce from below. No flat front light."""
    sun = bpy.data.objects['sun']; sun.data.energy = 9.0; sun.data.color = (1.0, 0.55, 0.28); sun.data.angle = math.radians(0.8)
    sun.rotation_euler = (math.radians(90 - 12), 0, math.radians(118))
    bpy.data.materials['haze'].node_tree.nodes['Principled Volume'].inputs['Density'].default_value = 0.0005   # aerial depth: hills 1.5-3 km away fade into the dusk
    bpy.data.materials['haze'].node_tree.nodes['Principled Volume'].inputs['Color'].default_value = (0.78, 0.74, 0.86, 1)   # distance turns cool
    bpy.context.scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.22
    area_light('bounce', 60, (1.0, 0.7, 0.5), Vector((0.0, -7.5, 0.9)), Vector((0, -6, 2.0)), 3.0)
    area_light('fill', 25, (0.45, 0.55, 1.0), Vector((3.5, -10.0, 2.4)), Vector((0, -6, 2.0)), 4.0)
    bpy.context.scene.view_settings.look = 'AgX - High Contrast'
    bpy.context.scene.view_settings.exposure = 0.4


# ---------------------------------------------------------------- Salamis v2 (real scans)
def _cove_shore(name='shore', x_span=70.0, y_back=-50.0, y_front=30.0, step=0.5, seed=4):
    """Land around the harbour shaped as a COVE: behind the wall (y < -7) and curving forward on both sides,
    so the camera's view to the sea is framed by land. Seaward points sink below the water."""
    rng = np.random.default_rng(seed)
    nx, ny = int(2 * x_span / step) + 1, int((y_front - y_back) / step) + 1
    xs = np.linspace(-x_span, x_span, nx); ys = np.linspace(y_back, y_front, ny)
    X, Y = np.meshgrid(xs, ys)
    edge = np.where(np.abs(X) < 10, -7.0, -7.0 + (np.abs(X) - 10) * 0.65)          # the shoreline y for each x
    inland = edge - Y                                                                   # metres inland (>0 = land)
    # gentle rise from the water, bumpy terraces further in (random smooth noise from a few sines)
    ph = rng.random(6) * 6.28
    bumps = (0.6 * np.sin(X * 0.11 + ph[0]) * np.sin(Y * 0.09 + ph[1]) + 0.35 * np.sin(X * 0.31 + ph[2]) * np.sin(Y * 0.27 + ph[3])
             + 0.15 * np.sin(X * 0.9 + ph[4]) * np.sin(Y * 0.8 + ph[5]))
    Z = np.where(inland > 0, 0.35 + 0.14 * inland ** 1.05 + bumps * np.clip(inland / 8, 0, 1), -0.8 + inland * 0.3)
    Z = np.maximum(Z, -2.0)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts.tolist(), [], faces); me.update()
    o = link(bpy.data.objects.new(name, me))
    for p in me.polygons:
        p.use_smooth = True
    return o


def salamis_dusk_v2(sun_elev=4.0, sun_azimuth=0.0, density=1.0):
    """Salamis strait v2: the real-scale geography of v1 plus a scanned harbour cove: weathered stone wall, rocky
    sand shore, real grass / shrubs / mastic bushes / boulders / trees scattered in natural patches, coastal rocks
    at the waterline, amphorae and baskets on the wall. density scales plant counts (0.3 for quick tests)."""
    from lib import scatter
    salamis_dusk(sun_elev, sun_azimuth)
    wall_mat = scatter.scan_material('wall_scan', 'rock_boulder_dry', tint=(0.72, 0.66, 0.58), tiles=1.5, rough=(0.7, 0.95))   # weathered, sea-darkened   # weathered sandstone blocks
    blocks = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.materials and o.data.materials[0]
              and o.data.materials[0].name.startswith('weathered_stone')]
    for o in blocks:
        o.data.materials[0] = wall_mat
    # blocks are scaled cubes: bake the scale into the mesh, or the stone texture stretches along each block
    with bpy.context.temp_override(selected_editable_objects=blocks, selected_objects=blocks, active_object=blocks[0]):
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    shore = _cove_shore()
    shore.data.materials.append(scatter.scan_material('shore_scan', 'coast_sand_rocks_02', tint=(1.0, 0.93, 0.82), tiles=3.0))
    clear = [(0, -6, 9.5), (2.4, -3.4, 2.5)]                   # the wall + the boat stay clear
    n = lambda k: max(1, int(k * density))
    cam = (2.0, -10.0)
    near_area = (-45, 45, -42, 18)                             # what the cameras actually see: plants go HERE
    scatter.scatter(shore, ['grass_medium_01'], n(9000), near_area, seed=1, size=(1.0, 1.8), clusters=160, min_z=0.8,
                    cluster_r=3.5, keep_clear=clear, near=cam, collection_name='grass', lod=1)
    scatter.scatter(shore, ['dry_branches_medium_01', 'grass_medium_01'], n(1400), near_area, seed=2, size=(1.4, 2.4), min_z=0.9,
                    clusters=90, cluster_r=2.5, keep_clear=clear, near=cam, collection_name='shrubs', lod=1)
    scatter.scatter(shore, ['searsia_lucida'], n(220), near_area, seed=3, size=(0.7, 1.4), clusters=40, min_z=0.9,
                    cluster_r=4.0, keep_clear=clear, near=cam, collection_name='bushes', lod=1)
    scatter.scatter(shore, ['searsia_lucida'], n(300), (-70, 70, -50, 30), seed=6, size=(0.8, 1.5), clusters=40,
                    cluster_r=6.0, keep_clear=clear, collection_name='bushes_far', lod=1)
    scatter.scatter(shore, ['dry_branches_medium_01', 'boulder_01'], n(80), (-70, 70, -50, 30), seed=4, size=(0.5, 1.4),
                    clusters=40, cluster_r=5.0, keep_clear=clear, near=cam, collection_name='debris', lod=1)
    scatter.scatter(shore, [('tree_olive_zakynthos', 2.0), ('tree_cypress', 1.0)], n(16), (-70, 70, -50, 30), seed=9,
                    size=(0.8, 1.2), clusters=8, cluster_r=8.0, min_z=1.5, keep_clear=clear + [(0, -6, 16)],
                    collection_name='olives_cypress', lod=1)          # THE trees of the Greek coast
    scatter.scatter(shore, ['island_tree_02'], n(8), (-70, 70, -50, 30), seed=5, size=(0.9, 1.4), clusters=8,
                    cluster_r=7.0, min_z=1.5, keep_clear=clear + [(0, -6, 16)], collection_name='trees', lod=1)
    # big coastal rocks where the land meets the sea, either side of the wall
    rocks = scatter.load_scan('coast_land_rocks_02', 1)
    rnd = np.random.default_rng(7)
    for i, (x, y) in enumerate([(-11.5, -6.6), (11.0, -6.4), (-16, -3.6), (17, -2.8), (-24, 1.2), (26, 2.5)]):
        inst = bpy.data.objects.new(f'coast_rock_{i}', None); inst.instance_type = 'COLLECTION'
        inst.instance_collection = rocks[i % len(rocks)]; inst.location = (x, y, -0.6)
        inst.rotation_euler = (0, 0, rnd.uniform(0, 6.28)); s = rnd.uniform(0.5, 0.9); inst.scale = (s, s, s)
        link(inst)
    from lib import fx
    fx.bird_flock((20.0, 60.0, 0.0), count=18, radius=60.0, height=(12.0, 40.0), seed=8, name='gulls')   # gulls over the strait
    # life on the wall: amphorae and baskets (stored goods of a working harbour)
    from lib import props as P
    for i, (x, y, lean) in enumerate([(4.6, -6.3, 0), (4.95, -6.05, 0.05), (5.25, -6.45, -0.04), (5.0, -6.7, 0.0)]):
        P.amphora((x, y, 0.8), lean=lean, seed=i)              # terracotta transport amphorae (code-built, era shape)
    for i, (x, y) in enumerate([(3.9, -6.6), (-4.2, -6.2)]):
        col = scatter.load_scan('wicker_basket_01', 0)[0]
        inst = bpy.data.objects.new(f'basket_{i}', None); inst.instance_type = 'COLLECTION'; inst.instance_collection = col
        inst.location = (x, y, 0.8); inst.rotation_euler = (0, 0, rnd.uniform(0, 6.28)); link(inst)
    return shore


def mesa(name, loc, size=(320.0, 150.0), height=70.0, cliff=0.18, step=2.0, seed=0):
    """A FLAT-TOPPED rock with cliffs (the Athenian Acropolis: ~270 x 150 m summit, ~70 m above the city): a plateau
    whose edge drops in a steep cliff band, then a rocky talus slope. size = (length x, width y) of the summit."""
    rng = np.random.default_rng(seed)
    sx, sy = size[0] / 2, size[1] / 2
    ext = 1.9
    xs = np.arange(-sx * ext, sx * ext + step, step); ys = np.arange(-sy * ext, sy * ext + step, step)
    X, Y = np.meshgrid(xs, ys)
    ph = rng.random(4) * 6.28
    wob = 1 + 0.06 * np.sin(np.arctan2(Y, X) * 5 + ph[0]) + 0.04 * np.sin(np.arctan2(Y, X) * 11 + ph[1])
    r = np.sqrt((X / sx) ** 2 + (Y / sy) ** 2) / wob                 # 1 = edge of the summit
    top = np.clip((1.0 + cliff - r) / cliff, 0, 1)                    # 1 on the plateau, 0 below the cliff
    top = top * top * (3 - 2 * top)
    talus = np.clip((ext - r) / (ext - 1.0 - cliff), 0, 1) ** 1.6 * 0.38
    Z = height * np.maximum(top, talus)
    Z += (0.6 * np.sin(X * 0.21 + ph[2]) * np.sin(Y * 0.19 + ph[3])) * (top > 0.98)   # gentle unevenness on top
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    nx, ny = len(xs), len(ys)
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i) for j in range(ny - 1) for i in range(nx - 1)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts.tolist(), [], faces); me.update()
    o = link(bpy.data.objects.new(name, me)); o.location = loc
    rt = bpy.data.textures.new(f'{name}_rock', 'CLOUDS'); rt.noise_scale = 6.0; rt.noise_depth = 6
    d = o.modifiers.new('rock', 'DISPLACE'); d.texture = rt; d.strength = 2.5; d.texture_coords = 'GLOBAL'
    for pf in me.polygons:
        pf.use_smooth = True
    return o


def athens_480bc(density=1.0, burning=False):
    """Athens in 480 BC seen from below the Acropolis: the rock (~70 m high), on top the OLD TEMPLE OF ATHENA
    (Doric 6 x 12; the Parthenon did not exist yet - built from 447 BC), houses of the lower city with tiled roofs,
    dry scrub and trees between them. `burning=True` = the Persian sack of September 480 BC (fire glow, smoke haze).
    Camera side = -Y (the lower city), the Acropolis rises at +Y."""
    from lib import architecture as A, scatter
    from lib.common import hdri_sky
    hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=0.9, lighting=0.35, rotate_deg=40)   # real clouds
    sun_light('sun', 3.2, (1.0, 0.82, 0.62), 22, 230 + 180, angle_deg=1.0)       # afternoon side light
    rock = mesa('acropolis_rock', (0, 180, 0), size=(270, 140), height=70, seed=11)
    rock.data.materials.append(scatter.scan_material('acropolis_stone', 'cliff_side', tint=(0.5, 0.52, 0.55), tiles=8.0))   # grey-blue limestone (the warm sun adds the gold)
    A.temple(loc=(-20, 182, 70.2), columns_front=6, columns_side=12, D=1.6, heading_deg=0, name='old_temple_of_athena')
    ground = _cove_shore('city_ground', x_span=160, y_back=-140, y_front=90, step=1.0, seed=12)
    for v in ground.data.vertices:                              # the lower city sits on dry land, not at a shore
        v.co.z = max(v.co.z, 0.0) * 0.15 + 1.0
    ground.data.update()
    ground.data.materials.append(scatter.scan_material('city_earth', 'brown_mud_dry', tint=(1.05, 0.95, 0.82), tiles=4.0))
    rng = np.random.default_rng(3)
    n = 0
    for gx in range(-6, 7):                                     # irregular blocks of houses along narrow streets
        for gy in range(-5, 3):
            if rng.random() < 0.25 or (abs(gx) < 1 and gy > -2):
                continue
            x = gx * 22 + rng.uniform(-4, 4); y = gy * 20 + rng.uniform(-4, 4)
            A.house((x, y, 1.0), w=rng.uniform(7, 12), d=rng.uniform(8, 14), h=rng.uniform(2.8, 4.2),
                    heading_deg=rng.choice([0, 90]) + rng.uniform(-6, 6), seed=n, name=f'house_{n}')
            n += 1
    clear = [(0, -20, 6)]
    scatter.scatter(ground, ['grass_medium_01', 'dry_branches_medium_01'], int(2500 * density), (-150, 150, -130, 80),
                    seed=21, size=(1.0, 1.8), clusters=120, cluster_r=4.0, keep_clear=clear, collection_name='city_grass', lod=1)
    scatter.scatter(ground, [('tree_olive_zakynthos', 3.0), ('tree_cypress', 1.5), ('island_tree_02', 1.0)], int(70 * density),
                    (-150, 150, -130, 80), seed=22, size=(0.8, 1.3), clusters=30, cluster_r=8.0, keep_clear=clear,
                    collection_name='city_trees', lod=1)               # olive groves + cypresses around the city
    haze(density=0.00025, color=(0.85, 0.8, 0.75) if not burning else (0.6, 0.45, 0.35))
    if burning:                                                  # September 480 BC: the Persians sack the Acropolis
        from lib import fx                                        # (no glow spheres: they render as white blobs)
        fx.flames((-20, 182, 70), height=14, width=22, intensity=2.5, name='temple_fire')
        fx.fire_light((-20, 182, 80), power=40000, radius=8, name='temple_fire_light')
        fx.smoke_column((-20, 182, 78), height=220, width=34, density=0.6, color=(0.06, 0.055, 0.05), name='acropolis_smoke')
        for k in range(8):
            x, y = rng.uniform(-120, 120), rng.uniform(-100, 60)
            fx.flames((x, y, 1.0), height=6, width=8, intensity=2.0, name=f'house_fire_{k}')
            fx.fire_light((x, y, 5.0), power=6000, radius=3, seed=k, name=f'house_fire_light_{k}')
            fx.smoke_column((x, y, 6), height=110, width=14, density=0.5, color=(0.07, 0.065, 0.06), name=f'house_smoke_{k}')
    return rock



def thermopylae_480bc(density=1.0, dawn=False):
    """The pass of Thermopylae, August 480 BC (Herodotus 7.175-7.200): a strip of coast a few dozen metres wide
    between the cliffs of Mount Kallidromos (south) and the Malian Gulf (north) - in antiquity the sea came almost
    to the cliffs (the coastline is now kilometres away). Across the narrowest point: the old PHOCIAN WALL of
    rough fieldstone, rebuilt by the Greeks (7.176). Camera side = -X (the Greek side), the Persians come from +X."""
    from lib import scatter
    elev = 6 if dawn else 20
    sky_world(sun_elev_deg=elev, sun_rot_deg=95 if dawn else 160, strength=0.5, dust=5.0, air=1.6)
    sun_light('sun', 3.6, (1.0, 0.7, 0.45) if dawn else (1.0, 0.88, 0.72), elev, (95 if dawn else 160) + 180, angle_deg=1.0)
    ocean(size=80, choppiness=0.8, wave_scale=0.35)
    far_sea()
    # the mountain wall: a long ridge whose foot comes down to the pass (south side, +Y)
    mt = land('kallidromos', (0, 520, 0), (3200, 900, 1), 900, rough=260, noise=380, color=(0.3, 0.27, 0.22), seed=31)
    mt.data.materials[0] = scatter.scan_material('kallidromos_rock', 'cliff_side', tint=(0.5, 0.47, 0.42), tiles=30.0)
    # mesa centre far enough back that its rubble slope (to 1.9 x half-width) stops at the inner edge of the pass
    cliff = mesa('kallidromos_cliffs', (0, 140, 0), size=(1400, 80), height=60, cliff=0.12, step=3.0, seed=32)
    cliff.data.materials.append(scatter.scan_material('pass_cliffs', 'rock_boulder_dry', tint=(0.5, 0.46, 0.41), tiles=6.0))
    # the pass itself: a narrow coastal shelf between the cliffs and the water
    shelf = _cove_shore('pass_shelf', x_span=300, y_back=-12, y_front=60, step=1.0, seed=33)
    for v in shelf.data.vertices:
        v.co.z = max(-1.5, min(2.5, 0.08 * (v.co.y + 12)) + 0.15 * math.sin(v.co.x * 0.3))
    shelf.data.update()
    shelf.data.materials.append(scatter.scan_material('pass_ground', 'coast_land_rocks_01', tint=(0.95, 0.9, 0.82), tiles=3.0))
    # the Phocian wall: rough fieldstone, ~2 m high, across the shelf at x = 0
    rng = np.random.default_rng(34)
    stone = scatter.scan_material('phocian_stone', 'rock_boulder_dry', tint=(0.7, 0.66, 0.6), tiles=1.0)
    for i in range(160):
        y = rng.uniform(-6, 58); z = rng.uniform(0.2, 2.2)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=rng.uniform(0.35, 0.7),
                                              location=(rng.uniform(-1.2, 1.2), y, z + 0.08 * (y + 12)))
        b = bpy.context.object; b.scale = (rng.uniform(0.7, 1.1), rng.uniform(0.9, 1.6), rng.uniform(0.5, 0.8))
        b.rotation_euler = tuple(rng.uniform(0, 3.14, 3)); b.data.materials.append(stone)
    clear = [(0, y, 4) for y in range(-6, 60, 6)] + [(-30, 20, 15)]          # wall + where the Greeks stand
    scatter.scatter(shelf, ['grass_medium_01', 'dry_branches_medium_01'], int(2000 * density), (-200, 200, -10, 58),
                    seed=35, size=(0.9, 1.6), clusters=90, cluster_r=4.0, min_z=0.3, keep_clear=clear, collection_name='pass_grass', lod=1)
    scatter.scatter(shelf, ['searsia_lucida', 'boulder_01'], int(220 * density), (-200, 200, 20, 58), seed=36,
                    size=(0.6, 1.3), clusters=40, cluster_r=6.0, keep_clear=clear, collection_name='pass_bushes', lod=1)
    haze(density=0.00035, color=(0.9, 0.82, 0.72))
    return shelf



def xerxes_throne_aigaleos(density=1.0):
    """Herodotus 8.90: during the battle Xerxes sat at the foot of Mount Aigaleos, opposite Salamis, and whenever he
    saw one of his men do a great deed he asked his name, and his scribes wrote it down.
    A slope above the strait: royal pavilion + golden throne on a stone platform, Persian standards, the camp's tents
    behind, the strait and Salamis beyond (the real-scale v1 geography). The throne faces the strait (+Y)."""
    from lib import props as P, scatter
    salamis_dusk(sun_elev=14, sun_azimuth=40)
    slope = _cove_shore('aigaleos_slope', x_span=90, y_back=-90, y_front=10, step=1.0, seed=41)
    for v in slope.data.vertices:                                     # ONE formula: a hillside rising away from the water
        v.co.z = 0.18 * max(0.0, -v.co.y - 6) + 0.5 + 0.35 * math.sin(v.co.x * 0.17) * math.sin(v.co.y * 0.13)             if v.co.y < -6 else min(v.co.z, 0.5)                        # (v1 added the cove's own height too: 3.5 m too high)
    slope.data.update()
    slope.data.materials.append(scatter.scan_material('aigaleos_ground', 'coast_land_rocks_01', tint=(0.92, 0.86, 0.76), tiles=3.0))
    z0 = 0.18 * 34 + 0.5                                               # ground height at y = -40
    # TERRACED STONE PODIUM (Persepolis-style ashlar terrace), sunk into the slope - a flat slab on an 18 % hill
    # floated ~0.6 m at its downhill edge with its underside showing (Session E's review). Its body reaches 2 m down
    # into the hill; a flight of steps descends toward the strait (+Y), each step meeting the ground.
    ground_z = lambda y: 0.18 * (-y - 6) + 0.5                        # the slope formula above
    ashlar = scatter.scan_material('platform_stone', 'old_sandstone_02', tint=(0.9, 0.85, 0.78), tiles=0.8)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -40, z0 - 0.8)); plat = bpy.context.object
    plat.name = 'throne_podium'; plat.scale = (8, 7, 2.4)
    bv = plat.modifiers.new('arris', 'BEVEL'); bv.width = 0.03; bv.segments = 2
    plat.data.materials.append(ashlar)
    y_edge, step_d = -36.5, 0.45
    top = z0 + 0.4
    k = 0
    while True:                                                       # steps down until they reach the ground
        y_c = y_edge + step_d * (k + 0.5)
        z_top = top - 0.32 * (k + 1)
        if z_top < ground_z(y_c) - 0.05:
            break
        h = z_top - (ground_z(y_c) - 0.5)                             # each step sits 0.5 m into the hill
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, y_c, z_top - h / 2))
        st = bpy.context.object; st.name = f'podium_step_{k}'; st.scale = (3.2, step_d, h)
        st.data.materials.append(ashlar); st.modifiers.new('arris', 'BEVEL').width = 0.02
        k += 1
    for sgn in (-1, 1):                                               # low parapet on the downhill corners
        bpy.ops.mesh.primitive_cube_add(size=1, location=(sgn * 3.0, -36.75, top + 0.25))
        pp = bpy.context.object; pp.scale = (2.0, 0.4, 0.5); pp.data.materials.append(ashlar)
    pav = P.pavilion((0, -40, z0 + 0.4), heading_deg=0)
    thr = P.throne((0, -40.6, z0 + 0.4), heading_deg=180)
    P.royal_dress_up(thr, pav)                                         # folded valances, lion-paw feet, carpet
    colors = [(0.45, 0.05, 0.05), (0.75, 0.55, 0.15), (0.06, 0.12, 0.35), (0.45, 0.05, 0.05)]
    for i, x in enumerate((-5.5, -3.5, 3.5, 5.5)):
        P.banner((x, -36.5, z0 + 0.4), color=colors[i], name=f'std_{i}')
    rng = np.random.default_rng(42)
    for i in range(60):                                                # the camp spreads over the slope behind
        x, y = rng.uniform(-80, 80), rng.uniform(-85, -50)
        P.tent((x, y, 0.18 * max(0, -y - 6) + 0.5), r=rng.uniform(1.8, 2.8), h=rng.uniform(2.2, 3.0),
               color=tuple(rng.uniform([0.45, 0.38, 0.28], [0.62, 0.53, 0.42])), name=f'tent_{i}')
    clear = [(0, -40, 9)]
    scatter.scatter(slope, ['grass_medium_01', 'dry_branches_medium_01'], int(2500 * density), (-90, 90, -90, 8), seed=43,
                    size=(1.0, 1.6), clusters=110, cluster_r=4.0, min_z=0.8, keep_clear=clear, collection_name='slope_grass', lod=1)
    scatter.scatter(slope, ['searsia_lucida', 'boulder_01'], int(220 * density), (-90, 90, -90, 8), seed=44, size=(0.6, 1.3),
                    clusters=40, cluster_r=6.0, min_z=0.8, keep_clear=clear, collection_name='slope_bushes', lod=1)
    return plat


def persian_palace_interior(time='afternoon'):
    """Inside the king's audience hall: a dark forest of columns, light shafts from the high east windows (visible in
    the hall's haze), the dais at the far end for the throne. Pair with props.throne + lighting mood 'interior'."""
    from lib import architecture as A
    from lib.common import sky_world, sun_light
    hall, floor = A.palace_hall()
    sky_world(sun_elev_deg=28, sun_rot_deg=270, strength=0.25)
    sun = sun_light('sun', 40.0, (1.0, 0.84, 0.62), 24, 90, angle_deg=0.6)    # low through the east windows
    haze(size=(140, 140, 30), density=0.0025, color=(1.0, 0.92, 0.82))       # dusty air -> visible light shafts (thin!)
    bpy.data.objects['haze'].location = (0, 0, 14)
    from lib.common import area_light
    from mathutils import Vector as V
    area_light('floor_bounce', 4000, (1.0, 0.78, 0.55), V((10, 0, 0.3)), V((-10, 0, 8)), 30.0)  # sunlit floor bounces warm light up
    area_light('dais_glow', 600, (1.0, 0.7, 0.45), V((-24, 0, 4)), V((-31, 0, 1.5)), 4.0)            # torches by the throne
    area_light('hall_fill', 120, (0.6, 0.65, 0.85), V((0, 0, 13)), V((0, 0, 0)), 40.0)          # faint sky light from above
    return hall


def salamis_night_v2(density=1.0):
    """The night of 19/20 September 480 BC (Herodotus 8.75-76): Sicinnus rows across to the Persians; the Persian
    fleet moves in the dark. Salamis v2 geography + cold moonlight and stars, the harbour lantern, distant fleet lights,
    the boat's own lamp. Pair with lighting mood 'night'."""
    from lib import fx
    shore = salamis_dusk_v2(sun_elev=-8.0, density=density)       # sun below the horizon
    for n in ('sun',):
        if n in bpy.data.objects:
            bpy.data.objects[n].data.energy = 0.0
    fx.night_sky(moon_elev=26, moon_azimuth=160, moon_power=0.3)
    if 'haze' in bpy.data.materials:
        v = bpy.data.materials['haze'].node_tree.nodes['Principled Volume']
        v.inputs['Density'].default_value = 0.0004; v.inputs['Color'].default_value = (0.5, 0.58, 0.8, 1)
    lantern((2.6, -3.3, 0.65), power=25)                            # the rowboat's own lamp
    return shore


def thebes_1250bc(density=1.0):
    """Thebes (Luxor) in the reign of Ramesses II: a temple pylon with obelisks facing the Nile, date palms along the
    river, sand and dry mud ground, harsh high sun and a hazy sky. Camera side = -Y (the river bank)."""
    from lib import architecture as A, scatter
    from lib.common import hdri_sky
    hdri_sky('kloofendal_48d_partly_cloudy_puresky', background=1.0, lighting=0.35, rotate_deg=80)
    sun_light('sun', 5.0, (1.0, 0.92, 0.78), 48, 200, angle_deg=0.8)
    ground = _cove_shore('thebes_ground', x_span=160, y_back=-120, y_front=120, step=1.5, seed=51)
    for v in ground.data.vertices:
        v.co.z = 0.6 + 0.25 * math.sin(v.co.x * 0.05) * math.sin(v.co.y * 0.04) if v.co.y > -60 else -0.6
    ground.data.update()
    ground.data.materials.append(scatter.scan_material('thebes_sand', 'brown_mud_dry', tint=(1.15, 0.95, 0.7), tiles=4.0))
    ocean(size=80, choppiness=0.3, wave_scale=0.2)                # the Nile: slow, smooth
    bpy.data.objects['ocean'].location = (0, -100, 0)
    A.egypt_pylon(loc=(0, 40, 0.6), name='temple_pylon')
    scatter.scatter(ground, ['tree_date_palm'], int(60 * density), (-150, 150, -58, 10), seed=52, size=(0.8, 1.2), clusters=18,
                    cluster_r=10.0, keep_clear=[(0, 20, 30)], collection_name='palms', lod=1)
    scatter.scatter(ground, ['grass_medium_01', 'dry_branches_medium_01'], int(1200 * density), (-150, 150, -58, 30), seed=53,
                    size=(0.8, 1.4), clusters=60, cluster_r=5.0, keep_clear=[(0, 20, 30)], collection_name='riverbank_grass', lod=1)
    haze(density=0.0002, color=(1.0, 0.92, 0.8))
    return ground
