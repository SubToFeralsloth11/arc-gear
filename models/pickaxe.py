"""Raider pickaxe -- steel-tube handle with ribbed rubber grip, forged curved pick and adze."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(1.5)


def taper_y(o, z0, z1, end=0.25):
    """Thin the part along Y as |z| goes from z0 to z1 (forged point)."""
    for v in o.data.vertices:
        t = min(max((abs(v.co.z) - z0) / (z1 - z0), 0.0), 1.0)
        v.co.y *= 1.0 - (1.0 - end) * t


steel = worn("ForgedSteel", (0.07, 0.072, 0.075), 1, 0.42, (0.62, 0.62, 0.6), 1, 0.18, wear=1.3,
             grime=0.45, chip_depth=0.03, micro=0.06, primer=None, brushed=True)

# handle + ribbed grip + pommel + lanyard
cyl("Handle", (0.0, 0, 0), (0.53, 0, 0), 0.0135, mat="gun", bevel=0.001)
prof = [(0.0, -0.004), (0.0205, -0.004), (0.0205, 0.004), (0.0175, 0.008)]
h = 0.012
while h < 0.19:
    prof += [(0.0182, h), (0.0182, h + 0.005), (0.0168, h + 0.008)]
    h += 0.01
prof += [(0.0168, 0.198), (0.0145, 0.204), (0.0, 0.204)]
revolve("GripSleeve", prof, axis=(1, 0, 0), n=40, mat="rubber", bevel=0)
cyl("Pommel", (-0.014, 0, 0), (-0.003, 0, 0), 0.0215, 0.0205, mat="orange", bevel=0.002)
tube("Lanyard", [(-0.012, 0, 0.0), (-0.026, 0, 0.012), (-0.04, 0, 0.0), (-0.026, 0, -0.012)],
     0.0025, cloth("Cord", (0.25, 0.22, 0.18), stain=None, weave_scale=900), closed=True)
cyl("HazardBand", (0.30, 0, 0), (0.33, 0, 0), 0.0145, mat="hazard", bevel=0.0008)
for x in (0.205, 0.215):  # tape wrap end
    cyl("Tape", (x, 0, 0), (x + 0.008, 0, 0), 0.0148, mat="rubber", bevel=0.0008)

# head: socket, side plates, bolts, glow strip
sym("Socket", box(0.485, -0.034, 0.556, 0.034), 0.042, "orange", bevel=0.004)
for side in (1, -1):
    y0, y1 = (0.020, 0.025) if side > 0 else (-0.025, -0.020)
    prism("HeadPlate", [(0.49, -0.028), (0.55, -0.028), (0.552, 0.028), (0.49, 0.028)], y0, y1,
          "gun", bevel=0.0015)
    for x, z in [(0.499, 0.019), (0.541, 0.019), (0.499, -0.019), (0.541, -0.019)]:
        screw(x, z, side * 0.025, side)
    prism("GlowStrip", box(0.505, -0.003, 0.535, 0.003), side * 0.025, side * 0.0262, "glow", bevel=0)

pick = sym("Pick", [(0.49, 0.03), (0.552, 0.03), (0.55, 0.07), (0.538, 0.12), (0.515, 0.17),
                    (0.485, 0.215), (0.458, 0.246), (0.468, 0.21), (0.486, 0.16), (0.497, 0.11),
                    (0.50, 0.07)], 0.028)
taper_y(pick, 0.035, 0.246, 0.2)
finish(pick, steel, bevel=0.0025)
adze = sym("Adze", [(0.49, -0.03), (0.552, -0.03), (0.566, -0.07), (0.586, -0.115), (0.596, -0.136),
                    (0.548, -0.146), (0.514, -0.11), (0.498, -0.07)], 0.05)
taper_y(adze, 0.03, 0.146, 0.85)
finish(adze, steel, bevel=0.0025)

stage((0.27, 0, 0.02), 0.45, -0.16)
render("pickaxe", {
    "hero": ((1.05, 0.80, 0.32), (0.29, 0, 0.03), 35),
    "side": ((0.29, 1.15, 0.04), (0.29, 0, 0.03), 40),
})
