# WS7 TEST: the museum scans at REAL size, side by side in a lamp-lit storeroom, with a 1.75 m scale post.
# Run: blender -b --python blender/scenes/ws7_pottery.py -- <out.png> [samples] [variant]
#   variant ''      = all five pots + the helmet on a chest (wide)
#   variant 'close' = close-up on the black-figure amphora + kylix + helmet (surface/material check)
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ws7_common as W
import bpy
from mathutils import Vector

from lib import common, props, scans_glb

OUT, SAMPLES, VARIANT = W.args('pottery_v1.png')
common.reset_scene()
W.room(w=7.0, d=5.0, floor_tint=(0.55, 0.55, 0.55), wall_tint=(0.62, 0.62, 0.62))   # grey down the orange stone
W.dark_world()

# the five museum pots in a row on the floor, left to right, each at its museum size
pots = ['amphora_terracotta_met', 'amphora_blackfigure_cleveland', 'amphora_neck_cleveland', 'krater_bell_met']
xs = [-1.05, -0.5, 0.05, 0.6]
for a, x in zip(pots, xs):
    scans_glb.load_glb(a, loc=(x, 0.9, 0.0), rot_z_deg=200)

# a painted chest to hold the kylix and the helmet at a height you can see into
ch = props.chest((1.35, 0.95, 0), heading_deg=0, size=(0.8, 0.45, 0.42), name='store_chest')
top = 0.07 + 0.42 + 0.04                                    # foot + box + lid (see props.chest)
scans_glb.load_glb('kylix_cleveland', loc=(1.15, 0.95, top), rot_z_deg=30)
scans_glb.load_glb('helmet_corinthian_cleveland', loc=(1.55, 0.95, top), rot_z_deg=-115)

# scale reference: a 1.75 m pole (the height of a man) at the back - delete for real shots
pole = props.principled('scale_pole', (0.08, 0.07, 0.06), rough=0.8)
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.015, depth=1.75, location=(-1.6, 1.4, 0.875))
bpy.context.object.data.materials.append(pole)

# light: warm low key from camera-right (a doorway at late afternoon) + a lamp-glow fill + a cool rim
W.window_light((0.3, 0.9, 0.35), energy=200.0, loc=(2.6, -1.4, 1.6), size=1.2, color=(1.0, 0.93, 0.84))
common.area_light('fill', 8.0, (1.0, 0.62, 0.35), (-2.2, -1.2, 0.9), (0.0, 0.9, 0.3), size=0.8)
common.area_light('rim', 60.0, (0.7, 0.78, 1.0), (-0.8, 2.3, 2.2), (0.3, 0.9, 0.3), size=1.0)

if VARIANT == 'close':
    common.camera('cam', Vector((1.2, -0.25, 0.85)), Vector((1.35, 0.95, 0.6)), lens=50, fstop=4.0,
                  focus=(1.35, 0.95, 0.62))
else:
    common.camera('cam', Vector((0.2, -2.6, 1.05)), Vector((0.25, 0.9, 0.38)), lens=35)
W.finish(OUT, SAMPLES, exposure=-0.6)
