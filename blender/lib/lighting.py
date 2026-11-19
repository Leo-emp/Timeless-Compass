# FILM LIGHTING PRESETS (rule r10): light placed RELATIVE to the camera and the subject, like a cinematographer:
#   key  - from ~45 deg to one side of the camera and above: faces get a lit side and a SHADOW side (modelling)
#   rim  - from behind, on the opposite side: bright edges on hair / shoulders separate people from the background
#          (a tight SPOT so it lights people, not the ground)
#   fill - very weak, from the camera side: keeps shadows dark but not dead
# The reference's strongest trait is this contrast; flat front light is what makes CG look cheap.
import math

import bpy
from mathutils import Vector

from lib.common import area_light, look_at

MOODS = {   # key (W, colour), rim (W, colour), fill (W, colour), key side (+1 = camera-right), key height (m)
    'dusk':     {'key': (90, (1.0, 0.72, 0.5)), 'rim': (2400, (1.0, 0.55, 0.26)), 'fill': (8, (0.5, 0.58, 1.0)), 'side': 1, 'h': 0.6},
    'day':      {'key': (160, (1.0, 0.95, 0.88)), 'rim': (1200, (1.0, 0.95, 0.85)), 'fill': (18, (0.75, 0.82, 1.0)), 'side': 1, 'h': 1.2},
    'night':    {'key': (25, (0.55, 0.65, 1.0)), 'rim': (900, (0.6, 0.7, 1.0)), 'fill': (3, (0.4, 0.45, 0.8)), 'side': -1, 'h': 1.4},
    'firelit':  {'key': (70, (1.0, 0.5, 0.18)), 'rim': (600, (0.5, 0.6, 1.0)), 'fill': (4, (1.0, 0.45, 0.2)), 'side': -1, 'h': -0.2},
    'interior': {'key': (60, (1.0, 0.82, 0.62)), 'rim': (700, (1.0, 0.75, 0.5)), 'fill': (5, (0.6, 0.65, 0.9)), 'side': 1, 'h': 0.9},
    'menace':   {'key': (40, (0.9, 0.85, 0.8)), 'rim': (1500, (1.0, 0.6, 0.35)), 'fill': (1, (0.4, 0.45, 0.6)), 'side': -1, 'h': 1.6},
}


def _spot(name, energy, color, loc, target, cone_deg=18, soft=0.3):
    bpy.ops.object.light_add(type='SPOT', location=tuple(loc))
    o = bpy.context.object; o.name = name
    o.data.energy = energy; o.data.color = color
    o.data.spot_size = math.radians(cone_deg); o.data.spot_blend = 0.6; o.data.shadow_soft_size = soft
    look_at(o, target)
    return o


def film_lights(subject, camera_loc, mood='dusk', dist=2.6, name='film'):
    """Key / rim / fill around `subject` (world point, e.g. between the actors' heads) as seen from `camera_loc`.
    Returns the three light objects."""
    m = MOODS[mood]
    subject, cam = Vector(subject), Vector(camera_loc)
    to_cam = (cam - subject); to_cam.z = 0; to_cam.normalize()
    right = Vector((to_cam.y, -to_cam.x, 0.0))                  # camera-right, seen from the subject
    s = m['side']
    key_dir = (to_cam * math.cos(math.radians(45)) + right * s * math.sin(math.radians(45))).normalized()
    key = area_light(f'{name}_key', m['key'][0], m['key'][1], subject + key_dir * dist + Vector((0, 0, m['h'])), subject, 1.4)
    rim_dir = (-to_cam * 0.8 - right * s * 0.6).normalized()     # behind, opposite the key
    rim = _spot(f'{name}_rim', m['rim'][0], m['rim'][1], subject + rim_dir * (dist + 0.6) + Vector((0, 0, 0.9)),
                subject + Vector((0, 0, 0.1)), cone_deg=20)
    fill = area_light(f'{name}_fill', m['fill'][0], m['fill'][1], subject + to_cam * dist * 1.2 + Vector((0, 0, 0.3)), subject, 2.5)
    return key, rim, fill
