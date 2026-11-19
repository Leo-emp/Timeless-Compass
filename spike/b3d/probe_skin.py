import sys; sys.path.insert(0, 'C:/Users/User/timeless-compass/blender')
import bpy
from lib import common, cast
common.reset_scene()
h, rig = cast.build_human({"macro": {"gender": 1.0, "age": 0.6, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5, "cupsize": 0.5, "firmness": 0.5, "race": {"asian": 0.3, "caucasian": 0.4, "african": 0.3}}, "tan": 0.7})
nt = h.material_slots[0].material.node_tree.nodes["Human.body"].node_tree
tex = nt.nodes["DiffuseTexture"]
print("LINKS", [(l.to_node.name, l.to_socket.name) for o in tex.outputs for l in o.links])
print("BC", [(l.from_node.name) for l in nt.nodes["Principled BSDF"].inputs["Base Color"].links])
raise SystemExit
m = h.material_slots[0].material
def walk(nt, depth=0):
    for n in nt.nodes:
        print('  ' * depth, n.type, n.name, getattr(getattr(n, 'image', None), 'name', ''), [i.name for i in n.inputs if i.is_linked][:6])
        if n.type == 'GROUP' and n.node_tree and depth < 2:
            walk(n.node_tree, depth + 1)
walk(m.node_tree)
