# WS3 WARDROBE TEST STILLS (Greek, c. 480 BC): one dressed character per run, cloth-simulated, at dusk.
# Run: blender -b --python blender/scenes/ws3_wardrobe.py -- <out.png> [samples] [outfit] [shot]
#   outfit: woman       peplos (saffron wool, overfold, belt over it, long dress pins) + veil over the head + sandals
#           woman_pins  the same peplos without the veil: shows the pins, belt, earrings, necklace (use shot=med)
#           servant     exomis (one shoulder bare) in WORN coarse cloth: patches, frayed hem, dirt (crowd 'poor')
#           child       child's tunic (chitoniskos), cord belt, barefoot
#           priest      long white linen chiton + pale himation with a purple border, wool fillet, sandals
#           priestess   long white chiton + mantle drawn over the head, gold stephane, earrings, necklace, sandals
#           crowd:<role>:<seed>[:<era>]  a tc/crowd.py extra dressed by wardrobe.dress() (e.g. crowd:servant:7)
#           traveller   short chiton + chlamys (fibula on the right shoulder) + petasos + sandals
#           woman_ionic long dotted chiton with meander hem + madder himation + sakkos + jewellery
#           patterns    no person: 12 cloths showing every woven/painted ornament (borders + strewn fields)
#           swatches    no person: four hanging cloths, WEAR BY RANK royal / rich / common / poor (tc/crowd dyes)
#   shot:   full (default) | med | head
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from lib import common, pose, wardrobe
import ws3_common as W

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else 'ws3.png'
SAMPLES = int(argv[1]) if len(argv) > 1 else 20
OUTFIT = argv[2] if len(argv) > 2 else 'woman'
SHOT = argv[3] if len(argv) > 3 else 'full'

# standing, arms hanging a little away from the body (hands clear of the hips, so skirts fall between them);
# added here at run time (pose.py belongs to WS5)
pose.POSES.setdefault('stand_open', {**pose.POSES['stand_relaxed'],
                                     "upperarm01.R": (-0.22, 0.02, -1), "lowerarm01.R": (-0.1, -0.14, -1),
                                     "upperarm01.L": (0.22, 0.02, -1), "lowerarm01.L": (0.1, -0.14, -1)})

common.reset_scene()
bronze, gold, leather = W.metals()

# Era dyes (linear RGB), as in tc/crowd.py: saffron/ochre, madder red, woad blue, undyed wool and linen
SAFFRON, MADDER, WOAD = (0.45, 0.30, 0.10), (0.30, 0.05, 0.035), (0.07, 0.10, 0.26)
UNDYED_WOOL, WHITE_LINEN, PURPLE = (0.50, 0.46, 0.38), (0.60, 0.57, 0.50), (0.20, 0.02, 0.12)


def wool(name, dye, band=None, grime=0.2):
    return wardrobe.scan_cloth(name, 'caban', dye, band=band, tiles=(4, 12), width=0.03, grime=grime, sheen=0.15)


def linen(name, dye, band=None, grime=0.15):
    return wardrobe.scan_cloth(name, 'rough_linen', dye, band=band, tiles=(7, 5), width=0.035, grime=grime, sheen=0.15)


def swatches():
    """Four cloths on a pole, one per rank, using exactly the dye dicts tc/crowd.py gives its extras."""
    ranks = [('royal', {"rank": "royal", "main": (0.20, 0.02, 0.12), "band": (0.55, 0.38, 0.08), "grime": 0.08, "patched": False}),
             ('rich', {"rank": "rich", "main": (0.07, 0.10, 0.26), "band": (0.30, 0.05, 0.035), "grime": 0.2, "patched": False}),
             ('common', {"rank": "common", "main": (0.40, 0.30, 0.18), "band": None, "grime": 0.38, "patched": False}),
             ('poor', {"rank": "poor", "main": (0.33, 0.28, 0.21), "band": None, "grime": 0.62, "patched": True})]
    cloths = []
    for i, (rank, dye) in enumerate(ranks):
        x0 = (i - 1.5) * 0.62
        nx, ny, w, h = 26, 46, 0.5, 0.9
        # the top edge is gathered onto the pole (70% of the cloth's width), so the cloth falls in real folds
        verts = [(x0 + (u / (nx - 1) - 0.5) * w * (0.7 if v == 0 else 1.0), 0.03 * ((u % 4) in (1, 2)) * min(1, v / 4),
                  1.6 - v / (ny - 1) * h) for v in range(ny) for u in range(nx)]
        faces = [(v * nx + u, v * nx + u + 1, (v + 1) * nx + u + 1, (v + 1) * nx + u) for v in range(ny - 1) for u in range(nx - 1)]
        me = bpy.data.meshes.new(rank); me.from_pydata(verts, [], faces); me.update()
        o = common.link(bpy.data.objects.new('swatch_' + rank, me))
        o.data.materials.append(wardrobe.crowd_cloth('cloth_' + rank, dye, seed=i * 7 + 3))
        wardrobe.set_uv(o, [((k % nx) / (nx - 1), 1 - (k // nx) / (ny - 1)) for k in range(len(verts))])
        vg = o.vertex_groups.new(name='pin')
        vg.add(list(range(nx)), 1.0, 'REPLACE')                            # the whole top edge on the pole
        cm = wardrobe._cloth(o, 'pin', mass=0.15, tension=40, bending=0.3)
        cm.settings.quality = 8
        o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.003
        cloths.append(o)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=2.8, location=(0, 0, 1.612), rotation=(0, 1.5708, 0))
    bpy.context.object.data.materials.append(common.principled('pole', (0.18, 0.11, 0.06), rough=0.6))
    wardrobe.simulate(40)
    bpy.ops.mesh.primitive_plane_add(size=30); g = bpy.context.object
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.reset(); bpy.ops.object.mode_set(mode='OBJECT')
    g.data.materials.append(wardrobe.scan_cloth('ground', 'coast_sand_rocks_02', (0.55, 0.49, 0.41), tiles=(15, 15), grime=0, sheen=0))
    common.hdri_world('qwantani_sunset_puresky', strength=0.45, rotate_deg=140)
    c = Vector((0, 0, 1.2))
    common.sun_light('sun', 2.6, (1.0, 0.6, 0.34), 14, 215)
    common.area_light('key', 70, (1.0, 0.76, 0.55), c + Vector((1.8, -2.0, 0.5)), c, 1.5)
    common.area_light('rim', 220, (1.0, 0.6, 0.35), c + Vector((-1.5, 1.8, 0.4)), c, 1.0)
    if SHOT == 'close':                                           # close-up of the poor cloth's hem and patches
        common.camera('cam', Vector((0.95, -1.1, 0.95)), Vector((0.93, 0, 0.85)), lens=50, fstop=8)
    else:
        common.camera('cam', Vector((0.5, -3.1, 1.15)), Vector((0, 0, 1.12)), lens=40, fstop=8)
    bpy.context.scene.world.node_tree.nodes.get('Background') and None
    common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
    bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'


def pattern_sampler():
    """Twelve hanging cloths, one per ornament (borders on the hem + strewn fields), in era dyes."""
    dark, ochre, navy = (0.04, 0.03, 0.025), (0.5, 0.34, 0.1), (0.06, 0.09, 0.24)
    looks = [('meander', None, MADDER, dark, SAFFRON), ('wave', None, WOAD, SAFFRON, UNDYED_WOOL),
             ('zigzag', None, dark, MADDER, SAFFRON), ('tongues', None, MADDER, dark, WHITE_LINEN),
             ('lines', 'dots', WOAD, ochre, MADDER), ('meander', 'crosses', dark, MADDER, SAFFRON),
             ('wave', 'stars', MADDER, ochre, WOAD), (None, 'rosettes', None, ochre, PURPLE),
             ('lines', 'rosette_grid', ochre, PURPLE, navy), (None, 'checker', None, dark, WHITE_LINEN),
             (None, 'stripes', None, MADDER, UNDYED_WOOL), ('tongues', 'dots', dark, SAFFRON, MADDER)]
    for i, (border, field, band, pcol, dye) in enumerate(looks):
        x0, z0 = ((i % 6) - 2.5) * 0.55, 2.3 if i < 6 else 1.25
        nx, ny, w, h = 22, 40, 0.42, 0.8
        verts = [(x0 + (u / (nx - 1) - 0.5) * w * (0.75 if v == 0 else 1.0), 0.03 * ((u % 4) in (1, 2)) * min(1, v / 4),
                  z0 - v / (ny - 1) * h) for v in range(ny) for u in range(nx)]
        faces = [(v * nx + u, v * nx + u + 1, (v + 1) * nx + u + 1, (v + 1) * nx + u) for v in range(ny - 1) for u in range(nx - 1)]
        me = bpy.data.meshes.new(f'pat{i}'); me.from_pydata(verts, [], faces); me.update()
        o = common.link(bpy.data.objects.new(f'pattern_{i}', me))
        o.data.materials.append(wardrobe.patterned_cloth(f'patcloth{i}', 'rough_linen', dye, band=band, border=border,
                                                         border_color=pcol, field=field, field_color=pcol,
                                                         border_repeat=6, field_repeat=(5, 9), width=0.14,
                                                         tiles=(3, 3), grime=0.05, sheen=0.15))
        wardrobe.set_uv(o, [((k % nx) / (nx - 1), 1 - (k // nx) / (ny - 1)) for k in range(len(verts))])
        vg = o.vertex_groups.new(name='pin'); vg.add(list(range(nx)), 1.0, 'REPLACE')
        cm = wardrobe._cloth(o, 'pin', mass=0.12, tension=40, bending=0.3); cm.settings.quality = 8
        o.modifiers.new('thick', 'SOLIDIFY').thickness = 0.003
        o.modifiers.new('smooth', 'SUBSURF').levels = 1
        bpy.ops.mesh.primitive_cylinder_add(radius=0.01, depth=0.5, location=(x0, 0, z0 + 0.012), rotation=(0, 1.5708, 0))
        bpy.context.object.data.materials.append(common.principled('pole', (0.18, 0.11, 0.06), rough=0.6))
    wardrobe.simulate(40)
    bpy.ops.mesh.primitive_plane_add(size=30); g = bpy.context.object
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.reset(); bpy.ops.object.mode_set(mode='OBJECT')
    g.data.materials.append(wardrobe.scan_cloth('ground', 'coast_sand_rocks_02', (0.55, 0.49, 0.41), tiles=(15, 15), grime=0, sheen=0))
    common.hdri_world('qwantani_sunset_puresky', strength=0.38, rotate_deg=140)
    c = Vector((0, 0, 1.6))
    common.sun_light('sun', 2.6, (1.0, 0.6, 0.34), 14, 215)
    common.area_light('key', 120, (1.0, 0.8, 0.6), c + Vector((1.5, -3.0, 0.8)), c, 2.5)
    common.area_light('rim', 200, (1.0, 0.6, 0.35), c + Vector((-1.5, 1.8, 0.4)), c, 1.0)
    common.camera('cam', Vector((0.0, -4.4, 1.75)), Vector((0, 0, 1.68)), lens=40, fstop=11)
    common.render_settings(res=(960, 540), samples=SAMPLES, path=OUT)
    bpy.context.scene.view_settings.look = 'AgX - Medium High Contrast'


if OUTFIT == 'swatches':
    swatches()

elif OUTFIT == 'patterns':
    pattern_sampler()

elif OUTFIT == 'traveller':
    # a traveller / rider: short chiton, chlamys pinned on the right shoulder with a fibula, petasos hat, sandals
    human, rig, pos = W.make_person(W.SERVANT)
    pose.blend_into_pose(rig, 'stand_open', start=1, end=15)
    ch = wardrobe.chiton(human, rig, pos, linen('trav_linen', (0.52, 0.47, 0.37), band=MADDER, grime=0.25))
    wardrobe._sim_freeze([ch], 45)
    rig.animation_data_clear(); pose.apply_pose(rig, 'stand_open')
    cl = wardrobe.chlamys(human, rig, wardrobe.patterned_cloth('chlamys_wool', 'caban', MADDER, band=(0.04, 0.03, 0.025),
                                                               border='wave', border_color=SAFFRON, tiles=(4, 10), width=0.06,
                                                               grime=0.2, sheen=0.15))
    wardrobe.dress_pins(cl, rig, bronze, kind='fibula', per_side=1)
    wardrobe.greek_hat(human, rig, wool('petasos_felt', (0.36, 0.28, 0.17), grime=0.2), kind='petasos')
    wardrobe.sandals(human, rig, leather)
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

elif OUTFIT == 'woman_ionic':
    # the Ionic look: long linen chiton (dotted, meander hem) + madder himation with a wave border, hair in a sakkos
    human, rig, pos = W.make_person(W.WOMAN)
    pose.blend_into_pose(rig, 'stand_open', start=1, end=15)
    ch = wardrobe.chiton(human, rig, pos, wardrobe.patterned_cloth('ionic_linen', 'rough_linen', WHITE_LINEN, band=MADDER,
                                                                   border='meander', border_color=(0.04, 0.03, 0.025),
                                                                   field='dots', field_color=MADDER, field_repeat=(44, 22),
                                                                   tiles=(7, 5), width=0.06, grime=0.08, sheen=0.15),
                         length='ankle')
    wardrobe._sim_freeze([ch], 45)
    rig.animation_data_clear(); pose.apply_pose(rig, 'stand_open')
    hm = wardrobe.himation(human, rig, pos, wardrobe.patterned_cloth('ionic_wool', 'caban', MADDER, band=(0.04, 0.03, 0.025),
                                                                     border='wave', border_color=SAFFRON, edge=1,
                                                                     tiles=(4, 12), width=0.05, grime=0.08, sheen=0.15),
                           side='L', over=ch)
    wardrobe._sim_freeze([hm], 60)
    wardrobe.greek_hat(human, rig, wardrobe.patterned_cloth('sakkos_cloth', 'rough_linen', SAFFRON, field='crosses',
                                                            field_color=MADDER, field_repeat=(8, 6), tiles=(3, 3), grime=0.05),
                       kind='sakkos')
    wardrobe.earrings(human, rig, gold); wardrobe.necklace(human, rig, gold); wardrobe.sandals(human, rig, leather)
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

elif OUTFIT in ('woman', 'woman_pins'):
    human, rig, pos = W.make_person(W.WOMAN)
    pose.blend_into_pose(rig, 'stand_open', start=1, end=15)
    PEPLOS = wool('peplos_wool', SAFFRON, band=WOAD)                 # saffron wool, woad-blue woven border
    body, over = wardrobe.peplos(human, rig, pos, PEPLOS, belt_over=True)
    rig.animation_data_clear(); pose.apply_pose(rig, 'stand_open')
    wardrobe.belt(rig, over, wool('girdle', MADDER, grime=0.05))
    wardrobe.dress_pins(over, rig, bronze, kind='perone', per_side=1)
    wardrobe.sandals(human, rig, leather)
    wardrobe.earrings(human, rig, gold)
    wardrobe.necklace(human, rig, gold)
    if OUTFIT == 'woman':
        wardrobe.veil(human, rig, wool('veil_wool', UNDYED_WOOL, band=MADDER, grime=0.05))
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

elif OUTFIT == 'woman_static':
    # robustness test: the peplos built WITHOUT the pose blend (arms already hanging), as the old card path did -
    # the skirt must still close (no side splits), now that it is never narrower than hips + thighs
    human, rig, pos = W.make_person(W.WOMAN)
    pose.apply_pose(rig, 'stand_relaxed')
    body, over = wardrobe.peplos(human, rig, pos, wool('peplos_static', MADDER, band=WOAD), belt_over=True)
    wardrobe.belt(rig, over, wool('girdle_s', SAFFRON, grime=0.05))
    wardrobe.diadem(human, rig, gold)
    wardrobe.earrings(human, rig, gold)
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

elif OUTFIT == 'servant':
    human, rig, pos = W.make_person(W.SERVANT)
    pose.blend_into_pose(rig, 'stand_relaxed', start=1, end=15)
    poor = {"rank": "poor", "main": (0.33, 0.28, 0.21), "band": None, "grime": 0.62, "patched": True}
    ex = wardrobe.exomis(human, rig, pos, wardrobe.crowd_cloth('exomis_poor', poor, seed=11))
    rig.animation_data_clear(); pose.apply_pose(rig, 'stand_relaxed')
    wardrobe.belt(rig, ex, common.principled('rope', (0.24, 0.18, 0.11), rough=0.9, bump=0.4, bump_scale=300))
    wardrobe.dress_pins(ex, rig, bronze, kind='fibula', per_side=1)  # a bronze fibula on the fastened shoulder
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

elif OUTFIT == 'child':
    human, rig, pos = W.make_person(W.CHILD)
    pose.blend_into_pose(rig, 'stand_open', start=1, end=15)
    tunic = wardrobe.child_tunic(human, rig, pos, linen('child_linen', (0.52, 0.47, 0.37), band=MADDER, grime=0.3))
    rig.animation_data_clear(); pose.apply_pose(rig, 'stand_open')
    wardrobe.belt(rig, tunic, wool('child_girdle', WOAD, grime=0.1), max_r=0.13)
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT, cam_dist=0.85)

elif OUTFIT in ('priest', 'priestess'):
    female = OUTFIT == 'priestess'
    human, rig, pos = W.make_person(W.PRIESTESS if female else W.PRIEST)
    pose.blend_into_pose(rig, 'stand_open', start=1, end=15)
    ch, mantle = wardrobe.priest_robes(human, rig, pos, linen('ritual_linen', WHITE_LINEN, grime=0.05),
                                       wool('ritual_wool', UNDYED_WOOL, band=PURPLE if not female else SAFFRON, grime=0.05),
                                       female=female, pose_name='stand_open')
    wardrobe.sandals(human, rig, leather)
    if female:
        wardrobe.diadem(human, rig, gold, front=0.03, over=mantle)   # a gold stephane worn over the veil
        wardrobe.earrings(human, rig, gold)
        wardrobe.necklace(human, rig, gold)
    else:
        wardrobe.fillet(human, rig, wool('fillet_wool', (0.62, 0.6, 0.55), grime=0.0))
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

elif OUTFIT.startswith('crowd:'):
    # crowd:<role>:<seed>[:<era>] -> a generated extra from tc/crowd.py, dressed by wardrobe.dress()
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    from tc import crowd
    _, role, seed, *era = OUTFIT.split(':')
    person = crowd.person(int(seed), role, era[0] if era else 'greece_480bc')
    print('crowd person:', person['role'], person['wardrobe'], person['dye'])
    if person.get('hair', {}).get('length', 0) > 0.08:                # long women's hair is WS1's: keep it short here
        person['hair']['length'] = 0.06
    human, rig, pos = W.make_person(person)
    wardrobe.dress(human, rig, pos, person)
    W.dusk_set(rig, SHOT, samples=SAMPLES, out=OUT)

else:
    raise SystemExit(f'unknown outfit {OUTFIT!r}')

if globals().get('human') is not None:                              # smooth the body like the other test scenes
    human.modifiers.new('smooth', 'SUBSURF').levels = 1
common.render()
