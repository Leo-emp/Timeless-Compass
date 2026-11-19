# WS7 DIAGNOSTIC: how deep does the simulated sail belly get at different wind strengths? (prints CLOTHDBG lines)
# Run: blender -b --python blender/scenes/ws7_debug_cloth.py -- <out.png>
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import bpy

from lib import common, props

common.reset_scene()
for wind in (40, 120, 300, 700):
    for frames in (60, 100):
        me = props.trireme_sail_cloth(name=f'dbg_{wind}_{frames}', wind=wind, frames=frames)
        xs = [v.co.x for v in me.vertices]; zs = [v.co.z for v in me.vertices]
        print('CLOTHDBG wind', wind, 'frames', frames, 'belly', round(max(xs), 2), 'min x', round(min(xs), 2), 'foot z', round(min(zs), 2))
