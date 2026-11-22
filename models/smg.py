"""SMG -- compact boxy submachine gun with wire stock and reflex sight."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(1.3)

Z0 = 0.018
slate = paint("Paint_Slate", (0.16, 0.20, 0.22))
yellow = paint("Paint_Yellow", (0.85, 0.58, 0.06), wear=1.2)

# receiver with ejection port on the right
rec = sym("Receiver", [(-0.10, -0.028), (0.21, -0.028), (0.21, 0.046), (0.19, 0.058),
                       (-0.08, 0.058), (-0.10, 0.044)], 0.054)
finish(cut(rec, [prism("cut", box(0.07, 0.004, 0.14, 0.036), 0.0, 0.1)]), slate, bevel=0.004)
prism("Bolt", box(0.066, 0.0, 0.144, 0.04), -0.005, 0.016, "gun", bevel=0.002)
for side in (1, -1):
    y0, y1 = (0.026, 0.0295) if side > 0 else (-0.0295, -0.026)
    prism("SidePanel", [(-0.07, -0.02), (0.058, -0.02), (0.058, 0.045), (-0.055, 0.045),
                        (-0.07, 0.03)], y0, y1, yellow, bevel=0.0015)
    for x, z in [(-0.06, 0.038), (0.05, 0.038), (-0.06, -0.012), (0.05, -0.012)]:
        screw(x, z, side * 0.0295, side)

sym("LowerHousing", [(-0.095, -0.026), (0.16, -0.026), (0.16, -0.05), (0.13, -0.058),
                     (-0.08, -0.058), (-0.095, -0.045)], 0.046, "poly", bevel=0.004)
sym("MagWell", box(0.088, -0.072, 0.142, -0.02), 0.038, slate, bevel=0.003)
sym("Magazine", [(0.094, -0.065), (0.136, -0.065), (0.146, -0.22), (0.104, -0.224)], 0.026,
    "gun", bevel=0.003)
sym("MagBase", [(0.100, -0.218), (0.152, -0.214), (0.154, -0.229), (0.101, -0.233)], 0.031,
    "poly", bevel=0.003)
for z in (-0.10, -0.14, -0.18):
    sym("MagRib", [(0.099 + (z + 0.065) * -0.0645, z), (0.141 + (z + 0.065) * -0.0645, z),
                   (0.141 + (z + 0.065) * -0.0645, z - 0.004), (0.099 + (z + 0.065) * -0.0645, z - 0.004)],
        0.028, "gun", bevel=0.001)

grip("Grip", -0.17, 0.02)
sym("Trigger", [(0.030, -0.056), (0.040, -0.056), (0.042, -0.072), (0.035, -0.088),
                (0.027, -0.086), (0.032, -0.072)], 0.008, "steel", bevel=0.0012)
guard = sym("TriggerGuard", [(-0.01, -0.054), (0.09, -0.054), (0.092, -0.075), (0.077, -0.097),
                             (0.03, -0.102), (0.005, -0.092), (-0.008, -0.075)], 0.012)
finish(cut(guard, [sym("cut", [(0.004, -0.061), (0.082, -0.061), (0.083, -0.075), (0.071, -0.089),
                               (0.03, -0.094), (0.012, -0.086), (0.004, -0.073)], 0.1)]),
       "gun", bevel=0.002)
sym("HandStop", [(0.165, -0.026), (0.205, -0.026), (0.2, -0.05), (0.188, -0.054)], 0.03, "poly",
    bevel=0.004, seg=1, subsurf=2)

# perforated barrel shroud, barrel, compensator
shroud = cyl("Shroud", (0.205, 0, Z0), (0.33, 0, Z0), 0.021)
holes = []
for i, x in enumerate([0.225 + k * 0.022 for k in range(5)]):
    holes.append(cyl("cut", (x, -0.05, Z0), (x, 0.05, Z0), 0.0062, n=20))
    holes.append(cyl("cut", (x + 0.011, 0, Z0 - 0.05), (x + 0.011, 0, Z0 + 0.05), 0.0062, n=20))
finish(cut(shroud, holes), "gun", bevel=0.0015)
cyl("ShroudCap", (0.325, 0, Z0), (0.335, 0, Z0), 0.0235, mat=yellow, bevel=0.0012)
cyl("Barrel", (0.20, 0, Z0), (0.36, 0, Z0), 0.0085, mat="gun", bevel=0.001)
comp = cyl("Compensator", (0.345, 0, Z0), (0.378, 0, Z0), 0.0135, n=6)
finish(cut(comp, [cyl("cut", (0.33, 0, Z0), (0.4, 0, Z0), 0.0055, n=24)]), "gun", bevel=0.0015)
for x in (0.352, 0.364):  # port grooves
    cyl("CompGroove", (x, 0, Z0), (x + 0.004, 0, Z0), 0.0128, mat="poly", n=24, bevel=0)

# top rail + reflex sight
rail(-0.06, 0.19, 0.058)
sym("SightBase", box(0.0, 0.0705, 0.07, 0.08), 0.03, "gun", bevel=0.0015)
sight = sym("SightBody", [(0.004, 0.079), (0.066, 0.079), (0.066, 0.118), (0.056, 0.123),
                          (0.012, 0.123), (0.004, 0.112)], 0.034)
finish(cut(sight, [cyl("cut", (-0.01, 0, 0.101), (0.08, 0, 0.101), 0.0125)]), "gun", bevel=0.0025)
cyl("SightGlass", (0.058, 0, 0.101), (0.0605, 0, 0.101), 0.0126, mat="lens", bevel=0)
sphere("RedDot", (0.012, 0, 0.101), 0.0014, simple("Glow_Red", (1, 0.1, 0.05), 0, 0.4,
                                                   emit=(1, 0.08, 0.03), strength=20))
cyl("SightKnob", (0.035, 0.017, 0.1), (0.035, 0.024, 0.1), 0.006, mat=yellow, n=16, bevel=0.0008)

# cocking tube on the left
cyl("CockingTube", (-0.06, -0.03, 0.046), (0.2, -0.03, 0.046), 0.007, mat="gun", bevel=0.001)
cyl("CockingStem", (0.165, -0.034, 0.046), (0.165, -0.05, 0.046), 0.004, mat="gun", bevel=0.0006)
sphere("CockingKnob", (0.165, -0.056, 0.046), 0.0085, "poly")

# wire stock
sym("StockHinge", box(-0.118, -0.024, -0.095, 0.052), 0.05, "gun", bevel=0.003)
for y in (0.016, -0.016):
    tube("StockRod", [(-0.11, y, 0.038), (-0.22, y, 0.035), (-0.33, y, 0.03)], 0.0055, "steel")
tube("StockRodLow", [(-0.11, 0, -0.015), (-0.22, 0, -0.033), (-0.33, 0, -0.05)], 0.006, "steel")
sym("ButtFrame", box(-0.335, -0.062, -0.325, 0.046), 0.042, "gun", bevel=0.002)
sym("ButtPad", [(-0.349, 0.052), (-0.333, 0.052), (-0.333, -0.068), (-0.349, -0.074)], 0.046,
    "rubber", bevel=0.006, seg=1, subsurf=2)

stage((0.02, 0, -0.04), 0.5, -0.25)
render("smg", {
    "hero": ((0.82, 0.78, 0.30), (0.02, 0, -0.045), 40),
    "side_left": ((0.02, -1.15, 0.06), (0.02, 0, -0.045), 45),
})
