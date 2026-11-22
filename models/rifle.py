"""HCR-1 "Breaker" -- heavy single-shot sci-fi rifle (Arc Raiders inspired)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *

Z0 = 0.012  # bore axis height

# --- receiver --------------------------------------------------------------
def pocket_cutter():  # chamber window on the right side
    return prism("cut", box(0.112, -0.008, 0.238, 0.035), -0.02, 0.2)


rec = sym("Receiver", [(-0.06, -0.035), (0.40, -0.035), (0.40, 0.048), (0.37, 0.065),
                       (-0.03, 0.065), (-0.06, 0.045)], 0.072)
finish(cut(rec, [pocket_cutter()]), "gun", bevel=0.004)

plate_pts = [(0.04, -0.028), (0.30, -0.028), (0.33, 0.0), (0.33, 0.040), (0.30, 0.056),
             (0.07, 0.056), (0.04, 0.030)]
rp = prism("SidePlate_R", plate_pts, 0.035, 0.044)
finish(cut(rp, [pocket_cutter()]), "cream", bevel=0.0025)
prism("SidePlate_L", plate_pts, -0.044, -0.035, "cream", bevel=0.0025)
for x, z in [(0.058, 0.040), (0.312, 0.038), (0.058, -0.016), (0.312, -0.016)]:
    screw(x, z, 0.044, 1)
    screw(x, z, -0.044, -1)

# trigger housing + grip + trigger
sym("TriggerHousing", [(0.02, -0.034), (0.27, -0.034), (0.255, -0.06), (0.24, -0.078),
                       (0.06, -0.078), (0.03, -0.06)], 0.06, "poly", bevel=0.004)
sym("Grip", [(0.100, -0.072), (0.170, -0.072), (0.164, -0.098), (0.152, -0.114),
             (0.156, -0.128), (0.143, -0.144), (0.147, -0.160), (0.135, -0.176),
             (0.133, -0.196), (0.126, -0.214), (0.078, -0.218), (0.068, -0.204),
             (0.078, -0.150), (0.090, -0.108), (0.094, -0.088)], 0.036, "poly",
    bevel=0.006, seg=1, subsurf=2)
sym("Trigger", [(0.198, -0.076), (0.208, -0.076), (0.210, -0.092), (0.203, -0.108),
                (0.195, -0.106), (0.200, -0.092)], 0.008, "steel", bevel=0.0012)
guard = sym("TriggerGuard", [(0.145, -0.074), (0.245, -0.071), (0.253, -0.095), (0.237, -0.119),
                             (0.19, -0.125), (0.160, -0.113), (0.147, -0.098)], 0.014)
finish(cut(guard, [sym("cut", [(0.160, -0.081), (0.239, -0.081), (0.242, -0.097), (0.230, -0.111),
                               (0.19, -0.116), (0.166, -0.106), (0.158, -0.094)], 0.1)]),
       "gun", bevel=0.0025)

# breech cover, hinge, latch
sym("BreechCover", [(0.08, 0.060), (0.31, 0.060), (0.31, 0.072), (0.29, 0.088),
                    (0.12, 0.091), (0.09, 0.081)], 0.06, "orange", bevel=0.004)
cyl("CoverHinge", (0.305, -0.033, 0.072), (0.305, 0.033, 0.072), 0.0085, mat="gun", bevel=0.001)
sym("CoverLatch", [(0.085, 0.078), (0.11, 0.084), (0.108, 0.094), (0.078, 0.092)], 0.03, "gun",
    bevel=0.0015)
for x in (0.16, 0.20, 0.24):  # ribs on the cover
    sym("CoverRib", box(x, 0.086, x + 0.012, 0.094), 0.05, "orange", bevel=0.002)

# the single heavy round, visible in the chamber window
cyl("Case", (0.118, 0, Z0), (0.214, 0, Z0), 0.0165, mat="brass", bevel=0.0008)
cyl("CaseRim", (0.114, 0, Z0), (0.118, 0, Z0), 0.0172, mat="brass", bevel=0.0006)
cyl("CaseNeck", (0.214, 0, Z0), (0.236, 0, Z0), 0.0165, 0.0112, mat="brass", bevel=0.0006)
cyl("CaseBand", (0.150, 0, Z0), (0.156, 0, Z0), 0.01675, mat="glow", bevel=0)
cyl("CaseBand2", (0.160, 0, Z0), (0.163, 0, Z0), 0.01675, mat="glow", bevel=0)

# bolt handle (right, rear)
cyl("BoltStem", (0.068, 0.034, 0.032), (0.058, 0.084, 0.004), 0.0065, mat="gun", bevel=0.001)
sphere("BoltKnob", (0.056, 0.093, 0.0), 0.0155, "poly", scale=(1, 1.1, 1))

# capacitor cell (left side)
CY, CZ = -0.064, -0.008
cyl("CellCapRear", (0.068, CY, CZ), (0.095, CY, CZ), 0.020, mat="gun", bevel=0.0018)
cyl("CellCapFront", (0.215, CY, CZ), (0.242, CY, CZ), 0.020, 0.017, mat="gun", bevel=0.0018)
cyl("CellGlass", (0.095, CY, CZ), (0.215, CY, CZ), 0.0165, mat="glass", bevel=0)
cyl("CellCore", (0.097, CY, CZ), (0.213, CY, CZ), 0.0085, mat="glow", bevel=0)
for x in (0.122, 0.152, 0.182):
    cyl("CellRing", (x, CY, CZ), (x + 0.005, CY, CZ), 0.018, mat="gun", bevel=0.0008)
for x in (0.10, 0.19):
    prism("CellBracket", [(x, -0.022), (x + 0.03, -0.022), (x + 0.03, 0.006), (x, 0.006)],
          -0.060, -0.043, "gun", bevel=0.002)
cyl("CellCable", (0.242, CY, CZ), (0.25, CY, CZ), 0.006, mat="rubber", bevel=0)
tube("CellCableRun", [(0.248, CY, CZ), (0.27, -0.058, -0.012), (0.30, -0.046, -0.004)],
     0.0035, "rubber")

# --- barrel group ------------------------------------------------------------
barrel = cyl("Barrel", (0.40, 0, Z0), (1.035, 0, Z0), 0.0225, n=64)
flutes = []
for i in range(6):
    a = i * math.tau / 6
    y, z = math.cos(a) * 0.0248, Z0 + math.sin(a) * 0.0248
    flutes.append(cyl("cut", (0.825, y, z), (0.985, y, z), 0.0052, n=16))
finish(cut(barrel, flutes), "gun", bevel=0.0012, angle=25)

shroud = sym("Shroud", [(0.395, -0.045), (0.74, -0.045), (0.80, -0.025), (0.80, 0.042),
                        (0.77, 0.058), (0.395, 0.058)], 0.076)
vent_side = prism("cut", [[(x, -0.002), (x + 0.03, -0.002), (x + 0.042, 0.028), (x + 0.012, 0.028)]
                          for x in (0.47 + i * 0.055 for i in range(5))], -0.1, 0.1)
vent_top = prism("cut", [box(x + 0.008, 0.035, x + 0.03, 0.1)
                         for x in (0.47 + i * 0.055 for i in range(5))], -0.012, 0.012)
bore = cyl("cut", (0.3, 0, Z0), (0.9, 0, Z0), 0.0265, n=48)
finish(cut(shroud, [vent_side, vent_top, bore]), "cream", bevel=0.004)
for x, z in [(0.418, 0.045), (0.775, 0.040)]:
    screw(x, z, 0.038, 1)
    screw(x, z, -0.038, -1)
for side in (1, -1):  # dark lower strip along the shroud
    y0, y1 = (0.037, 0.0415) if side > 0 else (-0.0415, -0.037)
    prism("ShroudStrip", [(0.40, -0.043), (0.735, -0.043), (0.765, -0.033), (0.40, -0.033)],
          y0, y1, "gun", bevel=0.0012)
    for x in (0.418, 0.58, 0.72):
        screw(x, -0.038, side * 0.0415, side)

# top rail on shroud
prism("RailBase", box(0.42, 0.058, 0.745, 0.065), -0.011, 0.011, "gun", bevel=0.0012)
prism("RailTeeth", [box(x, 0.065, x + 0.0055, 0.0705)
                    for x in (0.426 + i * 0.0105 for i in range(30))], -0.011, 0.011, "gun",
      bevel=0.0008, seg=2)

# foregrip
sym("GripMount", box(0.565, -0.053, 0.66, -0.043), 0.044, "gun", bevel=0.002)
sym("Foregrip", [(0.58, -0.048), (0.645, -0.048), (0.640, -0.062), (0.632, -0.120),
                 (0.626, -0.152), (0.590, -0.155), (0.586, -0.120), (0.580, -0.062)],
    0.032, "poly", bevel=0.005, seg=1, subsurf=2)
for z in (-0.08, -0.10, -0.12, -0.14):
    sym("ForegripRing", [(0.583, z), (0.640, z), (0.638, z - 0.006), (0.584, z - 0.006)],
        0.0345, "rubber", bevel=0.002, seg=2, subsurf=1)

# front block, guide rod, hazard band
sym("FrontBlock", [(0.86, -0.036), (0.90, -0.036), (0.90, 0.038), (0.887, 0.054),
                   (0.873, 0.054), (0.86, 0.038)], 0.058, "gun", bevel=0.003)
sym("FrontSight", [(0.874, 0.054), (0.886, 0.054), (0.884, 0.076), (0.876, 0.076)], 0.006, "gun",
    bevel=0.001)
sphere("SightDot", (0.880, 0.0, 0.073), 0.0022, "glow")
cyl("GuideRod", (0.80, 0, -0.024), (0.997, 0, -0.024), 0.006, mat="steel", bevel=0.0008)
for x in (0.92, 0.935, 0.95):
    cyl("BarrelCollar", (x, 0, Z0), (x + 0.009, 0, Z0), 0.0262, mat="gun", n=24, bevel=0.001)
cyl("RodCap", (0.985, 0, -0.024), (0.998, 0, -0.024), 0.009, mat="gun", bevel=0.0012)

# muzzle brake
brake = sym("MuzzleBrake", [(0.995, Z0 - 0.040), (1.14, Z0 - 0.040), (1.172, Z0 - 0.022),
                            (1.172, Z0 + 0.026), (1.14, Z0 + 0.043), (0.995, Z0 + 0.043)], 0.074)
ports = prism("cut", [box(x, Z0 - 0.023, x + 0.024, Z0 + 0.023) for x in (1.024, 1.063, 1.102)],
              -0.1, 0.1)
tops = [cyl("cut", (x, 0, Z0), (x, 0, 0.2), 0.007, n=24) for x in (1.036, 1.075, 1.114)]
mbore = cyl("cut", (0.95, 0, Z0), (1.3, 0, Z0), 0.0125, n=48)
finish(cut(brake, [ports, mbore] + tops), "gun", bevel=0.006)
ring = cyl("BrakeRing", (1.170, 0, Z0), (1.176, 0, Z0), 0.021)
finish(cut(ring, [cyl("cut", (1.16, 0, Z0), (1.19, 0, Z0), 0.0135)]), "orange", bevel=0.001)
cyl("BrakeCollar", (0.985, 0, Z0), (1.0, 0, Z0), 0.03, mat="gun", n=6, bevel=0.0015)

# --- optic --------------------------------------------------------------------
sym("MountRear", [(0.02, 0.064), (0.07, 0.064), (0.065, 0.118), (0.025, 0.118)], 0.04, "gun",
    bevel=0.003)
sym("MountFront", [(0.316, 0.064), (0.362, 0.064), (0.357, 0.118), (0.321, 0.118)], 0.04, "gun",
    bevel=0.003)
sym("ScopeBody", [(0.0, 0.112), (0.30, 0.112), (0.315, 0.125), (0.315, 0.160), (0.29, 0.174),
                  (0.03, 0.174), (0.0, 0.156)], 0.066, "cream", bevel=0.005)
prism("ScopePanel_R", [(0.05, 0.122), (0.25, 0.122), (0.27, 0.136), (0.27, 0.152),
                       (0.06, 0.163), (0.04, 0.150)], 0.032, 0.036, "orange", bevel=0.0015)
prism("ScopePanel_L", [(0.05, 0.122), (0.25, 0.122), (0.27, 0.136), (0.27, 0.152),
                       (0.06, 0.163), (0.04, 0.150)], -0.036, -0.032, "orange", bevel=0.0015)
SZ = 0.143
cyl("ObjectiveTube", (0.30, 0, SZ), (0.372, 0, SZ), 0.034, mat="gun", bevel=0.002)
hood = cyl("LensHood", (0.365, 0, SZ), (0.392, 0, SZ), 0.036, 0.039)
finish(cut(hood, [cyl("cut", (0.37, 0, SZ), (0.45, 0, SZ), 0.031)]), "gun", bevel=0.0012)
cyl("FrontLens", (0.3705, 0, SZ), (0.3735, 0, SZ), 0.031, mat="lens", bevel=0)
cyl("Eyepiece", (-0.045, 0, SZ), (0.002, 0, SZ), 0.024, mat="gun", bevel=0.002)
for x in (-0.035, -0.025, -0.015):
    cyl("EyeKnurl", (x, 0, SZ), (x + 0.006, 0, SZ), 0.0255, mat="gun", n=24, bevel=0.0008)
cup = cyl("EyeCup", (-0.072, 0, SZ), (-0.044, 0, SZ), 0.029, 0.025)
finish(cut(cup, [cyl("cut", (-0.09, 0, SZ), (-0.05, 0, SZ), 0.0205)]), "rubber", bevel=0.004,
       seg=1, subsurf=2)
cyl("RearLens", (-0.051, 0, SZ), (-0.048, 0, SZ), 0.021, mat="lens", bevel=0)
cyl("TurretTop", (0.15, 0, 0.172), (0.15, 0, 0.192), 0.014, mat="gun", n=24, bevel=0.0015)
cyl("TurretTopCap", (0.15, 0, 0.192), (0.15, 0, 0.197), 0.0115, mat="orange", bevel=0.001)
cyl("TurretSide", (0.15, 0.031, SZ), (0.15, 0.052, SZ), 0.013, mat="gun", n=24, bevel=0.0015)
cyl("TurretSideCap", (0.15, 0.052, SZ), (0.15, 0.057, SZ), 0.0105, mat="orange", bevel=0.001)
sym("ScopeLED", box(0.012, 0.150, 0.022, 0.156), 0.067, "glow", bevel=0.0005)

# --- stock ---------------------------------------------------------------------
sym("StockHinge", box(-0.095, -0.03, -0.055, 0.05), 0.062, "gun", bevel=0.004)
cyl("HingePin", (-0.075, -0.034, 0.03), (-0.075, 0.034, 0.03), 0.007, mat="steel", bevel=0.001)
stock = sym("Stock", [(-0.09, 0.046), (-0.36, 0.042), (-0.386, 0.052), (-0.386, -0.106),
                      (-0.36, -0.116), (-0.25, -0.09), (-0.09, -0.03)], 0.05)
hole = sym("cut", [(-0.31, 0.012), (-0.13, 0.012), (-0.115, -0.004), (-0.135, -0.028),
                   (-0.28, -0.064), (-0.315, -0.045)], 0.2)
finish(cut(stock, [hole]), "cream", bevel=0.006)
sym("CheekPad", [(-0.33, 0.040), (-0.12, 0.044), (-0.13, 0.063), (-0.31, 0.063)], 0.042,
    "rubber", bevel=0.006, seg=1, subsurf=2)
sym("ButtPad", [(-0.412, 0.058), (-0.383, 0.058), (-0.383, -0.114), (-0.412, -0.121)], 0.058,
    "rubber", bevel=0.007, seg=1, subsurf=2)
for side in (1, -1):
    y0, y1 = (0.025, 0.028) if side > 0 else (-0.028, -0.025)
    prism("StockStripe", box(-0.372, -0.07, -0.338, 0.024), y0, y1, "hazard", bevel=0.001)
tube("SlingLoop", [(-0.35, 0, -0.112), (-0.338, 0, -0.124), (-0.35, 0, -0.136), (-0.362, 0, -0.124)],
     0.0028, "steel", closed=True)
for x, z in [(-0.075, -0.012), (-0.075, 0.042)]:
    screw(x, z, 0.031, 1)
    screw(x, z, -0.031, -1)


stage((0.37, 0, 0), 1.0, -0.30)
render("rifle", {
    "hero": ((1.55, 1.45, 0.55), (0.40, 0, -0.02), 35),
    "side_right": ((0.37, 2.45, 0.02), (0.37, 0, -0.02), 50),
    "side_left": ((0.45, -1.55, 0.42), (0.37, 0, -0.02), 35),
    "breech": ((0.36, 0.42, 0.10), (0.17, 0, -0.03), 42),
    "muzzle": ((1.45, 0.38, 0.17), (0.92, 0, 0.0), 50),
})
