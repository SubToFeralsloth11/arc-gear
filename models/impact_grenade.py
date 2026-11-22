"""Impact grenade -- squat canister with glowing contact pins and a domed impact fuze."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(3.5)

body = paint("Paint_Gunship", (0.11, 0.12, 0.13), wear=1.2)

revolve("Body", [(0, 0.004), (0.024, 0.004), (0.029, 0.007), (0.031, 0.013), (0.031, 0.052),
                 (0.028, 0.06), (0.018, 0.066), (0, 0.066)], n=64, mat=body, bevel=0.0015)
cyl("Foot", (0, 0, 0.0), (0, 0, 0.0045), 0.025, mat="rubber", n=64, bevel=0.0012)
cyl("BandLow", (0, 0, 0.017), (0, 0, 0.025), 0.0318, mat="orange", n=64, bevel=0.0008)
cyl("BandHazard", (0, 0, 0.042), (0, 0, 0.047), 0.0316, mat="hazard", n=64, bevel=0.0006)
for i in range(8):  # contact pins around the waist
    a = i * math.tau / 8
    c, s = math.cos(a), math.sin(a)
    cyl("PinBase", (c * 0.029, s * 0.029, 0.0335), (c * 0.0335, s * 0.0335, 0.0335), 0.0045,
        mat="gun", n=16, bevel=0.0006)
    cyl("Pin", (c * 0.0335, s * 0.0335, 0.0335), (c * 0.0355, s * 0.0355, 0.0335), 0.0026,
        mat="glow", n=16, bevel=0.0004)

# fuze: collar, glass dome with glowing core, safety pin and ring
cyl("FuzeCollar", (0, 0, 0.062), (0, 0, 0.073), 0.0165, mat="gun", n=48, bevel=0.0012)
cyl("FuzeGrip", (0, 0, 0.064), (0, 0, 0.071), 0.0172, mat="gun", n=20, bevel=0.0005)
sphere("FuzeDome", (0, 0, 0.073), 0.0125, "glass", scale=(1, 1, 0.75))
sphere("FuzeCore", (0, 0, 0.073), 0.0075, "glow", scale=(1, 1, 0.75))
cyl("SafetyPin", (0.012, 0, 0.068), (0.026, 0, 0.068), 0.0012, mat="steel", n=12, bevel=0)
tube("PullRing", [(0.026, 0, 0.068), (0.034, 0.0, 0.076), (0.042, 0, 0.068), (0.034, 0, 0.06)],
     0.0013, "steel", closed=True)

stage((0, 0, 0.035), 0.12, 0.0)
render("impact_grenade", {
    "hero": ((0.25, 0.21, 0.16), (0, 0, 0.036), 50),
    "low": ((-0.18, 0.25, 0.07), (0, 0, 0.038), 50),
})
