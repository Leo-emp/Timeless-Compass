# BUILD + RENDER ONE SHOT from its recipe (jobs/<id>/recipes/<shot>.json, written by `tc assemble`).
# Run: blender -b --python blender/scenes/shot.py -- <recipe.json> <out_dir> [samples] [still|anim]
#   still = one frame from the middle of the shot (for the owner's contact-sheet review)
#   anim  = every frame of the shot, as PNGs in <out_dir>/frames/ (resumable: existing frames are skipped)
import json, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy
from mathutils import Vector
from lib import build, camera_moves, common, expressions, life, talk, lighting

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RECIPE = json.load(open(argv[0], encoding='utf-8'))
OUT_DIR = argv[1] if len(argv) > 1 else 'shot_out'
SAMPLES = int(argv[2]) if len(argv) > 2 else 32
MODE = argv[3] if len(argv) > 3 else 'still'
# FORMAT: long videos = 2.35:1 film frame (letterboxed in the 16:9 edit); Shorts = their OWN vertical 9:16 camera
# (owner rule: never crop a wide shot), framed tighter and slightly higher so faces sit in the upper third
SHORT = RECIPE.get('format') == 'short' or (len(argv) > 4 and argv[4] == 'short')
RES = (1080, 1920) if SHORT else (1280, 544)

if RECIPE['missing']:
    sys.exit('recipe has library gaps, build them first: ' + ', '.join(RECIPE['missing']))
common.reset_scene()
sc = bpy.context.scene
set_m = build.manifest('sets', RECIPE['set']['name'])
frames = max(RECIPE['frames'], 24)

# ---- cast: everyone built, dressed and moved onto the set's stage marks
people = []
for i, c in enumerate(RECIPE['cast']):
    walking = bool(RECIPE['motion'] and 'clip' in RECIPE['motion'])
    mark = set_m.get('walk_mark') if walking and set_m.get('walk_mark') else (set_m.get('marks') or [{"at": [0, 0, 0], "turn": 0}])[i % max(len(set_m.get('marks') or [1]), 1)]
    rig, human, root, first, last = build.character(c['name'], c['wardrobe'], RECIPE['motion'], tuple(mark['at']),
                                                    mark.get('turn', 0), frames)
    people.append((rig, first, last, mark.get('turn', 0), human, c['name']))
first = max([p[1] for p in people] or [1])
last = first + frames - 1

# ---- extras (generated unique people from the recipe): a loose group behind the main actors, facing them
if RECIPE.get('extras'):
    from lib import crowd as C
    base = Vector(people[0][0].matrix_world.translation) if people else Vector((0, 0, 0))
    ex = RECIPE['extras']
    marks = [tuple(base + Vector((-3.0 + 1.2 * (i % 6), 2.5 + 1.4 * (i // 6), 0.0))) for i in range(min(len(ex), 18))]
    mids = C.mid_crowd(ex[:18], marks, frames=frames, face_toward=tuple(base)[:2])
    if len(ex) > 18:
        C.far_crowd(mids, (base.x - 20, base.x + 20, base.y + 8, base.y + 30), len(ex) - 18, seed=1, face_toward=tuple(base)[:2])

# ---- acting: every face performs, the speaker talks, everyone is alive (blinks, eyes, breathing, weight)
TALK_WORDS = ('talk', 'speak', 'says', 'tells', 'argue', 'order', 'command', 'explain', 'shout', 'plead', 'warn')
action = (RECIPE.get('action') or '').lower()
for k, (rig, f0, f1, turn, human, name) in enumerate(people):
    expr = (RECIPE.get('expression') or {}).get(name, 'neutral')
    expr = expr if expr in expressions.EXPRESSIONS else 'neutral'
    lids = expressions.perform(human, rig, [(first, expr, 0.8)])
    if k == 0 and any(w in action for w in TALK_WORDS):
        talk.silent_talk(human, rig, first + 6, last, seed=k, energy=0.9 if expr in ('anger', 'rage') else 0.6)
    elif len(people) > 1:
        talk.listen(rig, first, last, seed=k)
    life.bring_to_life(rig, first, last, seed=k * 31 + 7, lid_open=lids[0][1],
                       standing=not (RECIPE.get('motion') or {}).get('clip'))

# ---- set + its tested film lighting
build.build_set(RECIPE['set']['builder'])
if set_m.get('film_light'):
    build.build_set(set_m['film_light'])

# ---- camera: the recipe's move around the first character's chest (or the set's centre for empty shots)
cam_spec = RECIPE['camera'] or {}
if people:
    rig = people[0][0]
    chest = 'Spine1' if 'Spine1' in rig.pose.bones else 'spine01'
    subject = build.head_point(rig, chest)
else:
    subject = Vector(set_m.get('marks', [{"at": [0, -6, 0.8]}])[0]['at']) + Vector((0, 0, 1.4))
cam = common.camera('cam', Vector((0, -10, 2)), Vector((0, 0, 1)), lens=cam_spec.get('lens', 40), fstop=cam_spec.get('fstop', 2.8))
if SHORT:                                   # vertical: closer, a wider lens (more height in frame), subject higher
    cam.data.lens = cam_spec.get('lens_short', 28)
    if people:
        base_subject = subject
        subject = (lambda f, b=base_subject: b(f) + Vector((0, 0, 0.15))) if callable(base_subject) else base_subject
camera_moves.apply_move(cam, cam_spec.get('move', 'static'), subject, first, last, frm=cam_spec.get('from', 'three_quarter'),
                        dist=cam_spec.get('dist', 3.6) * (0.8 if SHORT else 1.0), facing=people[0][3] if people else 0.0)
# film lighting around the actors (rule r10): key / rim / fill relative to the camera, mood from the recipe
if people:
    sc.frame_set((first + last) // 2)
    heads = sum((p[0].matrix_world @ p[0].pose.bones['head'].head for p in people), Vector()) / len(people)
    lighting.film_lights(heads, cam.location, mood=(RECIPE.get('camera') or {}).get('mood', 'dusk'))
# the sea keeps moving through the shot
if 'ocean' in bpy.data.objects:
    oc = bpy.data.objects['ocean'].modifiers['ocean']
    oc.time = first / 24; oc.keyframe_insert('time', frame=first)
    oc.time = last / 24; oc.keyframe_insert('time', frame=last)

common.render_settings(res=RES, samples=SAMPLES, path=os.path.join(OUT_DIR, RECIPE['shot'] + '.png'))
if set_m.get('film_light'):            # render_settings resets the look; the set's light wants its own
    sc.view_settings.look = 'AgX - High Contrast'; sc.view_settings.exposure = 0.4
sc.frame_start, sc.frame_end = 1, last
os.makedirs(OUT_DIR, exist_ok=True)
if any(m.type == 'CLOTH' for o in bpy.data.objects for m in o.modifiers):
    bpy.ops.ptcache.bake_all(bake=True)            # cloth simulates from frame 1 (pre-roll), then we render the shot
if MODE == 'still':
    sc.frame_set((first + last) // 2)
    common.render()
else:
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.render.use_persistent_data = False; sc.render.use_overwrite = False
    sc.frame_start = first
    sc.render.filepath = os.path.join(OUT_DIR, 'frames', 'f')
    sc.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(animation=True)
print('SHOT DONE', RECIPE['shot'], 'frames', first, '-', last)
