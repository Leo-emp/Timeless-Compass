import bpy
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
bpy.ops.wm.read_factory_settings(use_empty=True)
h = HumanService.create_human()
names = [g.name for g in h.vertex_groups]
print('GROUPS', len(names), [n for n in names if not n.startswith(('helper','joint'))][:120])
import collections
for want in ['head','neck','torso','body','Left','Right','Mid','pelvis','spine','chest']:
    hits=[n for n in names if want.lower() in n.lower()][:12]
    print(want, hits)
