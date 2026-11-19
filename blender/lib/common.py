# Shared Blender helpers for the Timeless Compass 3D library.
# Runs INSIDE Blender (bpy). Scene scripts do:  sys.path.insert(0, <repo>/blender); from lib import common
import math
import os

import bpy
from mathutils import Matrix, Vector

def _mpfb_data():
    """Where MPFB keeps its user data (the CC0 asset pack): works on Windows (laptop) and Linux (cloud)."""
    try:
        return os.path.join(bpy.utils.extension_path_user('bl_ext.blender_org.mpfb'), 'data')
    except Exception:
        return os.path.join(os.environ.get('APPDATA', ''), 'Blender Foundation', 'Blender', '5.3', 'extensions',
                            '.user', 'blender_org', 'mpfb', 'data')


MPFB_DATA = _mpfb_data()


def mpfb_asset(*parts):
    return os.path.join(MPFB_DATA, *parts)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


# ------------------------------------------------------------------ materials
def principled(name, color, metal=0.0, rough=0.5, bump=0.0, bump_scale=60.0, sss=0.0):
    """A simple PBR material. fake_user: MakeHuman's loader purges unused materials otherwise."""
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    if bump:
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = bump_scale; n.inputs['Detail'].default_value = 8
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump
        nt.links.new(n.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def hair_material(name, melanin=0.85, redness=0.3, rough=0.35, grey=0.0):
    """Physically based hair (Cycles Principled Hair, melanin model). grey>0 mixes in white for old men."""
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    # GREY = salt and pepper: a share of strands (`grey`) are WHITE, the rest keep their full colour. (Lowering the
    # melanin of every strand instead turns dark hair ginger, which is what v1 did.)
    h = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    h.parametrization = 'MELANIN'
    h.inputs['Melanin'].default_value = melanin
    h.inputs['Melanin Redness'].default_value = redness
    h.inputs['Roughness'].default_value = rough
    h.inputs['Random Color'].default_value = 0.24           # strand-to-strand colour variation
    h.inputs['Random Roughness'].default_value = 0.2
    if grey > 0:
        white = nt.nodes.new('ShaderNodeBsdfHairPrincipled'); white.parametrization = 'MELANIN'
        white.inputs['Melanin'].default_value = 0.08; white.inputs['Melanin Redness'].default_value = 0.1
        white.inputs['Roughness'].default_value = rough
        info = nt.nodes.new('ShaderNodeHairInfo')
        thr = nt.nodes.new('ShaderNodeMath'); thr.operation = 'LESS_THAN'; thr.inputs[1].default_value = grey
        nt.links.new(info.outputs['Random'], thr.inputs[0])
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(thr.outputs[0], mix.inputs['Fac']); nt.links.new(h.outputs[0], mix.inputs[1]); nt.links.new(white.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs['Surface'])
    else:
        nt.links.new(h.outputs[0], out.inputs['Surface'])
    return m


def dyed_hair_material(name, color, rough=0.45):
    """Dyed horsehair (helmet crests): hair BSDF with a direct colour instead of natural melanin."""
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    h = nt.nodes.new('ShaderNodeBsdfHairPrincipled'); h.parametrization = 'ABSORPTION'
    # absorption: how much each colour is swallowed per strand (high green+blue absorption = deep red)
    h.inputs['Absorption Coefficient'].default_value = tuple(max(0.02, -math.log(max(c, 1e-3)) * 0.9) for c in color)
    h.inputs['Roughness'].default_value = rough
    if 'Random Roughness' in h.inputs:
        h.inputs['Random Roughness'].default_value = 0.25
    nt.links.new(h.outputs[0], out.inputs['Surface'])
    return m


def aged_bronze(name='aged_bronze'):
    """Bronze that looks 2,500 years real: hammered surface, dark worn tone, green patina in the creases (AO)."""
    m = bpy.data.materials.new(name); m.use_fake_user = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; L = nt.links.new
    b.inputs['Metallic'].default_value = 1.0
    ao = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.02
    noise = nt.nodes.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 25; noise.inputs['Detail'].default_value = 10
    ramp = nt.nodes.new('ShaderNodeValToRGB')                       # bronze tones: dark worn -> bright edges
    ramp.color_ramp.elements[0].color = (0.30, 0.17, 0.065, 1); ramp.color_ramp.elements[1].color = (0.70, 0.46, 0.22, 1)   # worn, not new gold
    L(noise.outputs['Fac'], ramp.inputs['Fac'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'       # patina where AO is dark
    mix.inputs['B'].default_value = (0.16, 0.30, 0.24, 1)
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'POWER'; inv.inputs[1].default_value = 3.0
    one = nt.nodes.new('ShaderNodeMath'); one.operation = 'SUBTRACT'; one.inputs[0].default_value = 1.0
    L(ao.outputs['AO'], inv.inputs[0]); L(inv.outputs[0], one.inputs[1]); L(one.outputs[0], mix.inputs['Factor'])
    L(ramp.outputs['Color'], mix.inputs['A']); L(mix.outputs['Result'], b.inputs['Base Color'])
    rough = nt.nodes.new('ShaderNodeMapRange'); rough.inputs['To Min'].default_value = 0.3; rough.inputs['To Max'].default_value = 0.58
    L(noise.outputs['Fac'], rough.inputs['Value']); L(rough.outputs['Result'], b.inputs['Roughness'])
    hammer = nt.nodes.new('ShaderNodeTexVoronoi'); hammer.inputs['Scale'].default_value = 70     # visible hammer facets
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.22
    L(hammer.outputs['Distance'], bp.inputs['Height']); L(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def fabric(name, color, rough=0.9, weave_scale=900.0):
    """Linen/wool: fine woven bump + soft sheen."""
    m = principled(name, color, rough=rough)
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Sheen Weight'].default_value = 0.15
    b.inputs['Sheen Tint'].default_value = (*color, 1)
    w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = weave_scale; w.wave_type = 'BANDS'
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08
    nt.links.new(w.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m


# ------------------------------------------------------------------ objects
def link(o):
    bpy.context.scene.collection.objects.link(o)
    return o


def mesh_obj(name, verts, faces, material=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = link(bpy.data.objects.new(name, me))
    if material:
        o.data.materials.append(material)
    return o


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def area_light(name, energy, color, loc, target, size=1.0):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.color = color; l.size = size
    o = link(bpy.data.objects.new(name, l)); o.location = loc; look_at(o, target)
    return o


def sun_light(name, energy, color, elevation_deg, azimuth_deg, angle_deg=1.5):
    l = bpy.data.lights.new(name, 'SUN'); l.energy = energy; l.color = color; l.angle = math.radians(angle_deg)
    o = link(bpy.data.objects.new(name, l))
    o.rotation_euler = (math.radians(90 - elevation_deg), 0, math.radians(azimuth_deg))
    return o


def camera(name, loc, target, lens=50, fstop=None, focus=None):
    """focus = the point that must be sharp (for faces: the EYES, as on a film set); default = the target."""
    c = link(bpy.data.objects.new(name, bpy.data.cameras.new(name)))
    c.location = loc; c.data.lens = lens; look_at(c, target)
    c.data.clip_start = 0.05; c.data.clip_end = 20000.0        # see distant mountains (default is only 100 m)
    bpy.context.scene.camera = c
    if fstop:
        c.data.dof.use_dof = True; c.data.dof.focus_distance = (Vector(focus if focus is not None else target) - Vector(loc)).length; c.data.dof.aperture_fstop = fstop
    return c


def sky_world(sun_elev_deg=4.0, sun_rot_deg=200.0, strength=0.4, dust=3.0, air=1.5):
    """Physical sunset sky (Blender's built-in sky model)."""
    w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w
    nt = w.node_tree; bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    for attr, val in [('sun_elevation', math.radians(sun_elev_deg)), ('sun_rotation', math.radians(sun_rot_deg)),
                      ('air_density', air), ('dust_density', dust)]:
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    nt.links.new(sky.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    return w


SCANS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'library', 'scans')


def hdri_world(asset_id, strength=1.0, rotate_deg=0.0, res='2k'):
    """Light the scene with a REAL photographed sky (Poly Haven CC0 HDRI, fetched with `tc assets fetch`):
    natural soft light and colour on skin and cloth that a code sky can't give. rotate_deg turns the sun."""
    path = os.path.join(SCANS, asset_id, f'{asset_id}_{res}.hdr')
    w = bpy.data.worlds.new('hdri'); bpy.context.scene.world = w
    nt = w.node_tree; bg = nt.nodes['Background']
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path, check_existing=True)
    mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord')
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(rotate_deg))
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength
    return w


def render_settings(res=(1280, 720), samples=96, engine='CYCLES', path='out.png'):
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = res
    s.render.engine = engine
    if engine == 'CYCLES':
        s.cycles.samples = samples; s.cycles.use_denoising = True
        s.cycles.device = 'CPU'
        if os.environ.get('TC_GPU') == '1':                       # cloud GPU (Kaggle T4/P100): CUDA or OptiX
            prefs = bpy.context.preferences.addons['cycles'].preferences
            for kind in ('OPTIX', 'CUDA'):
                try:
                    prefs.compute_device_type = kind; prefs.get_devices()
                    if any(d.type == kind for d in prefs.devices):
                        for d in prefs.devices:
                            d.use = d.type == kind
                        s.cycles.device = 'GPU'; break
                except TypeError:
                    continue
    else:
        s.eevee.taa_render_samples = samples
    s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Punchy'
    s.view_settings.exposure = -0.3
    s.render.film_transparent = False
    s.render.filepath = path


def render(path=None):
    if path:
        bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('saved', bpy.context.scene.render.filepath)


def hdri_sky(asset_id, background=1.0, lighting=0.35, rotate_deg=0.0, res='2k'):
    """A REAL photographed sky with clouds as the background, but only gentle light on the scene (our sun lamp is
    the key light, so the HDRI's own sun must not double it): camera rays see the sky at `background`, every other
    ray (reflections, bounce) at `lighting`. Uses Poly Haven *_puresky HDRIs (no ground in the photo)."""
    w = hdri_world(asset_id, strength=1.0, rotate_deg=rotate_deg, res=res)
    nt = w.node_tree; bg = nt.nodes['Background']
    env_out = bg.inputs['Color'].links[0].from_socket
    lp = nt.nodes.new('ShaderNodeLightPath')
    cam_bg = nt.nodes.new('ShaderNodeBackground'); cam_bg.inputs['Strength'].default_value = background
    light_bg = nt.nodes.new('ShaderNodeBackground'); light_bg.inputs['Strength'].default_value = lighting
    nt.links.new(env_out, cam_bg.inputs['Color']); nt.links.new(env_out, light_bg.inputs['Color'])
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
    nt.links.new(light_bg.outputs[0], mix.inputs[1]); nt.links.new(cam_bg.outputs[0], mix.inputs[2])
    out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    return w
