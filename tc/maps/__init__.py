# WS19 MAPS (owner rule r14): animated parchment maps in the style of the Epic History TV "First Crusade" reference.
# See docs/MAP_STYLE.md. The work is split in two halves:
#   1. tc/maps (this package, plain Python + numpy + Pillow): PAINTS the map as big 2D textures —
#      parchment, engraved sea, coastlines, hand-drawn stamps (trees, mountains, dunes), rivers, territory fills,
#      labels, arrows — plus GRADIENT textures that let Blender animate them (territory grows, arrow draws itself).
#   2. blender/lib/maps.py: lays those textures on a crumpled 3D paper sheet with a low tilted drifting camera,
#      light, depth of field, spotlight, banners, city tags and 3D army blocks.
# Every pixel is drawn by our code from public-domain Natural Earth data (no AI images, no stock, no copied art).
