import bpy, numpy as np
c = bpy.data.hair_curves.new("t")
c.add_curves([4]*3)
print("points", len(c.points), "curves", len(c.curves))
print([a.name for a in c.attributes])
pos = np.zeros(12*3, dtype=np.float32); c.attributes['position'].data.foreach_set('vector', pos)
print("ok radius?", 'radius' in c.attributes)
print([n for n in dir(c) if not n.startswith('_')][:80])
