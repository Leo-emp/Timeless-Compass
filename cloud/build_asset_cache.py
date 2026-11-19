# BUILD ONE HEAVY ASSET ONCE and save it as a compressed .blend for the R2 asset cache (WS9 task 3). Runs IN Blender:
#   blender -b --python cloud/build_asset_cache.py -- cast themistocles out/built/cast/themistocles-<hash>.blend
#   blender -b --python cloud/build_asset_cache.py -- sets salamis_strait_dusk out/built/sets/salamis_strait_dusk-<hash>.blend
# The output path (with its hash) comes from  python -m tc cache built <job>, so a .blend is only reused while the
# manifest and the builder code are unchanged.
#
# Run it on a CLOUD machine (Kaggle / GitHub), never on the laptop while another session uses Blender (BLENDER_LOCK).
#
# What is saved:
#   cast: the character built from its cast manifest: MPFB body, sculpted face, groomed hair/beard, wardrobe
#         (cloth modifiers included but NOT simulated: each shot simulates its own motion), standing at the origin.
#   sets: the whole set from its builder + the set's film light (scattered scans are linked inside the .blend).
# Textures are packed into the .blend (bpy.ops.file.pack_all) so the file works on any machine without library/scans.
#
# HOW SHOTS WILL USE IT (hook for the shot pipeline, WS10 / blender/lib/build.py, not done here):
#   before building an asset, download built/<kind>/<name>-<hash>.blend from R2 if present and
#   bpy.ops.wm.append(...) its collection "TC_<kind>_<name>" instead of building from scratch.
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'blender')))
import bpy                      # noqa: E402
from lib import build, common   # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:]
KIND, NAME, OUT = argv[0], argv[1], argv[2]

common.reset_scene()
before = set(bpy.data.objects)
if KIND == 'cast':
    spec = build.manifest('cast', NAME)
    build.character(NAME, spec.get('wardrobe'), None, (0, 0, 0), 0.0, 24)     # no motion: a neutral standing build
elif KIND == 'sets':
    m = build.manifest('sets', NAME)
    build.build_set(m['builder'])
    if m.get('film_light'):
        build.build_set(m['film_light'])
else:
    sys.exit(f'unknown kind {KIND!r} (cast | sets)')

# Put everything that was built into ONE collection, so a shot can append it in one step.
col = bpy.data.collections.new(f'TC_{KIND}_{NAME}')
bpy.context.scene.collection.children.link(col)
for ob in set(bpy.data.objects) - before:
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    col.objects.link(ob)

bpy.ops.file.pack_all()                                   # textures inside the file: no scans needed to use it
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT), compress=True, copy=True)
print('BUILT', KIND, NAME, '->', OUT, f'{os.path.getsize(OUT) / 1024 ** 2:.0f} MB')
