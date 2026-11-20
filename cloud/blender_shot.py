# CLOUD WRAPPER around blender/scenes/shot.py (WS9). Runs INSIDE Blender:
#   blender -b --python cloud/blender_shot.py -- <recipe.json> <out_dir> <samples> anim
#
# Why a wrapper: shot.py (owned by the shot-pipeline workstream) builds and renders one shot. The render FARM wants
# to choose the engine and the speed settings per shot (tc/render_plan.py) without editing shot.py. So this file:
#   1. reads the settings the worker passes in environment variables (TC_ENGINE, TC_SAMPLES, TC_DENOISER, ...),
#   2. wraps lib.common.render_settings() so that, when shot.py calls it, our settings are applied on top,
#   3. then runs shot.py exactly as if Blender had been started with it (same command-line arguments).
#
# Settings applied:
#   Cycles: OpenImageDenoise (the free Intel AI denoiser, on the GPU when there is one), albedo+normal passes
#           (keeps fabric/skin detail sharp after denoising), adaptive sampling (stops early on clean pixels),
#           fewer light bounces (8 is plenty for daylight scenes), GPU tiles sized for a T4.
#   Eevee:  the real-time engine for wide + landscape shots: raytraced reflections/shadows on, samples from the plan.
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLENDER_DIR = os.path.join(HERE, '..', 'blender')
sys.path.insert(0, os.path.abspath(BLENDER_DIR))   # same folder shot.py adds, so `lib.common` is the SAME module

import bpy                                            # noqa: E402  (only exists inside Blender)
from lib import common                                # noqa: E402

ENGINE = os.environ.get('TC_ENGINE', 'CYCLES').upper()
SAMPLES = int(os.environ.get('TC_SAMPLES') or 0)
DENOISER = os.environ.get('TC_DENOISER', '')
ADAPTIVE = float(os.environ.get('TC_ADAPTIVE') or 0)
if os.environ.get('TC_FORCE_CYCLES') == '1' and ENGINE == 'EEVEE':   # machine has no OpenGL for Eevee
    ENGINE, DENOISER, ADAPTIVE = 'CYCLES', DENOISER or 'OPENIMAGEDENOISE', ADAPTIVE or 0.02


def eevee_id():
    """Blender renamed Eevee between versions ('BLENDER_EEVEE_NEXT' in 4.2-4.x, 'BLENDER_EEVEE' in 5.x)."""
    names = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    return 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'


_original = common.render_settings


def render_settings(res=(1280, 720), samples=96, engine='CYCLES', path='out.png'):
    """Same arguments as lib.common.render_settings; the farm's engine + samples win over shot.py's."""
    want = eevee_id() if ENGINE == 'EEVEE' else 'CYCLES'
    _original(res=res, samples=SAMPLES or samples, engine=want, path=path)
    s = bpy.context.scene
    if want == 'CYCLES':
        c = s.cycles
        if DENOISER:
            c.use_denoising = True
            c.denoiser = DENOISER                              # 'OPENIMAGEDENOISE'
            c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'     # albedo + normal guide = sharper detail
            c.denoising_prefilter = 'ACCURATE'
            if hasattr(c, 'denoising_use_gpu'):
                c.denoising_use_gpu = c.device == 'GPU'        # OIDN on the GPU (Blender 4.1+)
        if ADAPTIVE:
            c.use_adaptive_sampling = True
            c.adaptive_threshold = ADAPTIVE
        c.max_bounces = 8                                      # default 12: the extra bounces are nearly invisible
        c.transparent_max_bounces = 16                         # hair cards / leaves need some transparency depth
    else:
        e = s.eevee
        for attr, val in (('use_raytracing', True), ('use_shadows', True)):
            if hasattr(e, attr):
                setattr(e, attr, val)
    print(f'TC FARM: engine={want} samples={SAMPLES or samples} denoiser={DENOISER or "-"} adaptive={ADAPTIVE or "-"}')


common.render_settings = render_settings

# Run the scene with the same "-- ..." arguments Blender gave us:
#   default        blender/scenes/shot.py (render farm: one shot from its recipe)
#   TC_SCRIPT=...  any scene script (cloud queue stills, e.g. blender/scenes/cannon_test.py), so stills get the same
#                  GPU + OpenImageDenoise settings as shots. Their own sample count is kept when TC_SAMPLES is unset.
SHOT = os.path.abspath(os.environ.get('TC_SCRIPT') or os.path.join(BLENDER_DIR, 'scenes', 'shot.py'))
sys.argv[0] = SHOT
sys.path.insert(0, os.path.dirname(SHOT))           # like `blender --python <script>` would do
runpy.run_path(SHOT, run_name='__main__')
