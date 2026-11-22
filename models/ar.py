"""AR -- olive/tan assault rifle with curved mag, slotted handguard and holo sight."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(1.1)

Z0 = 0.03
olive = paint("Paint_Olive", (0.20, 0.23, 0.13))
tan = paint("Paint_Tan", (0.50, 0.40, 0.26), wear=1.2)

# upper with ejection port, bolt carrier and brass deflector
up = sym("Upper", [(-0.13, 0.005), (0.21, 0.005), (0.21, 0.058), (0.19, 0.066), (-0.11, 0.066),
                   (-0.13, 0.052)], 0.05)
finish(cut(up, [prism("cut", box(0.02, 0.018, 0.10, 0.046), 0.0, 0.1)]), olive, bevel=0.004)
prism("BoltCarrier", box(0.016, 0.015, 0.104, 0.05), -0.01, 0.014, "gun", bevel=0.002)
prism("Deflector", [(0.104, 0.036), (0.126, 0.036), (0.126, 0.06), (0.11, 0.064)], 0.024, 0.034,
      olive, bevel=0.002)
cyl("ForwardAssist", (-0.035, 0.02, 0.04), (-0.035, 0.037, 0.04), 0.008, mat="gun", n=24, bevel=0.001)
sym("ChargingHandle", [(-0.152, 0.054), (-0.112, 0.054), (-0.112, 0.064), (-0.152, 0.067)], 0.052,
    "gun", bevel=0.002)

# lower, mag well, curved magazine
sym("Lower", [(-0.12, 0.008), (0.17, 0.008), (0.17, -0.015), (0.13, -0.035), (0.11, -0.035),
              (-0.02, -0.035), (-0.07, -0.02), (-0.12, -0.012)], 0.048, tan, bevel=0.004)
sym("MagWell", box(0.045, -0.056, 0.112, 0.0), 0.04, tan, bevel=0.003)
front, back = [], []
for i in range(9):
    t = i / 8
    xc, z = 0.078 + 0.065 * t * t, -0.045 - 0.19 * t
    front.append((xc + 0.031, z))
    back.append((xc - 0.031, z))
sym("Magazine", front + back[::-1], 0.026, "poly", bevel=0.003)
xc = 0.078 + 0.065
sym("MagBase", box(xc - 0.035, -0.244, xc + 0.035, -0.232), 0.03, olive, bevel=0.003)

grip("Grip", -0.165, 0.05)
sym("Trigger", [(0.028, -0.033), (0.038, -0.033), (0.040, -0.049), (0.033, -0.065),
                (0.025, -0.063), (0.030, -0.049)], 0.008, "steel", bevel=0.0012)
guard = sym("TriggerGuard", [(-0.004, -0.031), (0.052, -0.031), (0.054, -0.05), (0.044, -0.071),
                             (0.015, -0.076), (0.0, -0.066), (-0.009, -0.05)], 0.012)
finish(cut(guard, [sym("cut", [(0.007, -0.038), (0.046, -0.038), (0.047, -0.05), (0.039, -0.064),
                               (0.016, -0.068), (0.007, -0.06), (0.003, -0.049)], 0.1)]),
       "gun", bevel=0.002)

# handguard, barrel, gas block, flash hider
hg = sym("Handguard", box(0.205, -0.004, 0.53, 0.064), 0.058)
slots = prism("cut", [[(x, 0.018), (x + 0.032, 0.018), (x + 0.036, 0.026), (x + 0.032, 0.034),
                       (x, 0.034), (x - 0.004, 0.026)] for x in (0.24 + k * 0.05 for k in range(6))],
              -0.1, 0.1)
finish(cut(hg, [slots, cyl("cut", (0.15, 0, Z0), (0.6, 0, Z0), 0.021)]), tan, bevel=0.012, seg=4)
cyl("Barrel", (0.2, 0, Z0), (0.69, 0, Z0), 0.0095, mat="gun", bevel=0.001)
sym("GasBlock", box(0.548, 0.012, 0.574, 0.048), 0.03, "gun", bevel=0.002)
sym("FrontPost", [(0.556, 0.048), (0.566, 0.048), (0.564, 0.07), (0.558, 0.07)], 0.006, "gun",
    bevel=0.001)
fh = cyl("FlashHider", (0.66, 0, Z0), (0.722, 0, Z0), 0.0125, n=32)
finish(cut(fh, [cyl("cut", (0.6, 0, Z0), (0.8, 0, Z0), 0.0055),
                prism("cut", box(0.684, Z0 - 0.0028, 0.73, Z0 + 0.0028), -0.1, 0.1),
                prism("cut", box(0.684, Z0 - 0.1, 0.73, Z0 + 0.1), -0.0028, 0.0028)]),
       "gun", bevel=0.0012)
for side in (1, -1):
    for x in (0.215, 0.515):
        screw(x, 0.05, side * 0.029, side)

# rail + holo sight
rail(-0.095, 0.525, 0.066)
sym("HoloBase", box(0.0, 0.078, 0.08, 0.087), 0.034, "gun", bevel=0.0015)
holo = sym("HoloBody", [(0.004, 0.086), (0.08, 0.086), (0.08, 0.135), (0.07, 0.141), (0.012, 0.141),
                        (0.004, 0.13)], 0.04)
finish(cut(holo, [prism("cut", box(-0.01, 0.095, 0.1, 0.13), -0.014, 0.014)]), "gun", bevel=0.003)
sym("HoloGlass", box(0.068, 0.095, 0.0705, 0.13), 0.028, "lens", bevel=0)
cyl("HoloBattery", (0.03, 0.02, 0.11), (0.03, 0.032, 0.11), 0.009, mat="orange", n=24, bevel=0.001)

# stock
cyl("BufferTube", (-0.12, 0, Z0), (-0.33, 0, Z0), 0.015, mat="gun", bevel=0.001)
cyl("CastleNut", (-0.138, 0, Z0), (-0.126, 0, Z0), 0.019, mat="gun", n=8, bevel=0.001)
stock = sym("Stock", [(-0.2, 0.056), (-0.36, 0.051), (-0.375, 0.058), (-0.375, -0.075),
                      (-0.355, -0.08), (-0.25, -0.01), (-0.2, 0.005)], 0.045)
finish(cut(stock, [sym("cut", [(-0.335, 0.0), (-0.27, 0.006), (-0.292, -0.03), (-0.34, -0.048)], 0.1)]),
       olive, bevel=0.006)
sym("ButtPad", [(-0.391, 0.062), (-0.373, 0.062), (-0.373, -0.078), (-0.391, -0.084)], 0.05,
    "rubber", bevel=0.006, seg=1, subsurf=2)
sym("StockLever", [(-0.24, 0.0), (-0.205, 0.004), (-0.207, -0.006), (-0.24, -0.008)], 0.014, "gun",
    bevel=0.0015)

stage((0.17, 0, 0), 0.65, -0.27)
render("ar", {
    "hero": ((1.20, 1.00, 0.36), (0.17, 0, -0.03), 38),
    "side_right": ((0.17, 1.65, 0.03), (0.17, 0, -0.02), 45),
})
