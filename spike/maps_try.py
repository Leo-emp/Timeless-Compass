# quick try-out of territories on the cached base (WS19)
import sys, numpy as np, os
sys.path.insert(0, '.')
from tc.maps import geo, base, stamps, territory as T, raster as R
v = geo.view_16x9(25, 40, 44, width=2048)
cache = 'spike/lib_stills/maps/_base2048.npz'
if os.path.exists(cache):
    z = np.load(cache); img, land = z['img'], z['land']
else:
    img, land = base.paint_base(v); img = stamps.paint_stamps(img, v, land)
    np.savez(cache, img=img, land=land)
rng = np.random.default_rng(5)
realms = [
  ("purple", "chirho", (24, 39), [(19,42),(23,44.5),(28.5,43.5),(29,41.5),(31.5,41.2),(32,40),(30,38.5),(28,36.5),(26,36),(22,36.3),(20,39)]),
  ("teal", "star8", (33, 38.5), [(29,41),(33,42),(37,41.5),(41,41),(44,39),(44,36.5),(38,36),(35,36.2),(32,36.1),(30,37),(30,39.5)]),
  ("green", "crescent", (31, 30), [(24,32),(30,31.6),(34,31.5),(35.5,33.5),(36.5,35),(37,34),(36,31),(35,29),(33,27),(25,27)]),
  ("crimson", "cross_patee", (12, 42), [(6,44),(9,46.5),(13.5,46.5),(14,45),(16,41.5),(18.6,40),(16,38),(12,37.5),(12,40),(9,43)]),
]
out = img.copy()
ms = T.exclusive([T.territory_mask(v, r[3], land, rng) for r in realms])
for (col, emb, seed, poly), m in zip(realms, ms):
    e = T.emblem_layer(v, m, emb, rng)
    out = T.paint_territory(out, m, col, e, v)
R.save(out, 'spike/lib_stills/maps/terr_v1.png')
from PIL import Image
Image.open('spike/lib_stills/maps/terr_v1.png').crop((700,350,1340,710)).resize((1280,720)).save('spike/lib_stills/maps/terr_v1_zoom.png')
