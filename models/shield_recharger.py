"""Shield recharger -- handheld injector cell with a caged glowing blue core."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(3.0)

C = 0.037  # axis height (rests on the floor)
blue = simple("Glow_Blue", (0.2, 0.6, 1.0), 0, 0.4, emit=(0.12, 0.5, 1.0), strength=14)
A = lambda x, y=0.0, z=0.0: (x, y, C + z)

# rear grip cap
cyl("EndPlate", A(-0.006), A(0.0), 0.03, mat="gun", bevel=0.0015)
cyl("RearCap", A(0.0), A(0.045), 0.036, mat="cream", bevel=0.003)
for x in (0.008, 0.018, 0.028):
    cyl("GripRing", A(x), A(x + 0.006), 0.0373, mat="rubber", bevel=0.0012)
cyl("ButtonCollar", A(0.038, 0, 0.03), A(0.038, 0, 0.039), 0.011, mat="gun", n=32, bevel=0.001)
cyl("Button", A(0.038, 0, 0.039), A(0.038, 0, 0.045), 0.0085, mat="orange", n=32, bevel=0.0015)

# glass core section
cyl("Glass", A(0.045), A(0.135), 0.029, mat="glass", bevel=0)
cyl("Core", A(0.046), A(0.134), 0.016, mat=blue, bevel=0)
for x in (0.058, 0.078, 0.098, 0.118):
    cyl("Coil", A(x), A(x + 0.005), 0.0215, mat="gun", n=32, bevel=0.0008)
for k in range(4):
    a = math.pi / 4 + k * math.pi / 2
    y, z = math.cos(a) * 0.0315, math.sin(a) * 0.0315
    cyl("CageBar", A(0.044, y, z), A(0.136, y, z), 0.0036, mat="gun", n=16, bevel=0.0006)

# front cap, glow ring, nozzle and contact prongs
cyl("FrontCap", A(0.135), A(0.175), 0.036, 0.031, mat="cream", bevel=0.003)
cyl("GlowRing", A(0.148), A(0.153), 0.0352, mat=blue, bevel=0)
cyl("Nozzle", A(0.175), A(0.19), 0.022, 0.019, mat="gun", bevel=0.0015)
cyl("Injector", A(0.19), A(0.212), 0.0055, 0.0035, mat="steel", n=24, bevel=0.0006)
for y in (0.011, -0.011):
    cyl("Prong", A(0.19, y), A(0.204, y), 0.0026, mat="steel", n=16, bevel=0.0005)

stage((0.1, 0, C), 0.18, 0.0)
render("shield_recharger", {
    "hero": ((0.33, 0.24, 0.16), (0.1, 0, 0.035), 50),
    "side": ((0.1, -0.36, 0.09), (0.1, 0, 0.035), 50),
})
