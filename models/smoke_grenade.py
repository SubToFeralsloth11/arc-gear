"""Smoke grenade -- tall vented canister with spoon, pin and pull ring."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(3.5)

green = paint("Paint_SmokeGreen", (0.17, 0.23, 0.15), wear=1.2)

body = revolve("Body", [(0, 0.0), (0.027, 0.0), (0.03, 0.004), (0.03, 0.105), (0.027, 0.11),
                        (0.0, 0.11)], n=64)
vents = [cyl("cut", (math.cos(a) * 0.019, math.sin(a) * 0.019, 0.095),
             (math.cos(a) * 0.019, math.sin(a) * 0.019, 0.13), 0.0042, n=20)
         for a in (k * math.tau / 6 for k in range(6))]
finish(cut(body, vents), green, bevel=0.0015)
cyl("Band", (0, 0, 0.04), (0, 0, 0.068), 0.0303, mat="cream", n=64, bevel=0.0008)
cyl("Stripe", (0, 0, 0.074), (0, 0, 0.079), 0.0303, mat="hazard", n=64, bevel=0.0006)
cyl("BaseRing", (0, 0, 0.0), (0, 0, 0.006), 0.0306, mat="gun", n=64, bevel=0.001)

# fuze, spoon, pin, ring
cyl("Fuze", (0, 0, 0.108), (0, 0, 0.125), 0.0115, mat="gun", n=32, bevel=0.0012)
cyl("FuzeCap", (0, 0, 0.125), (0, 0, 0.131), 0.008, mat="gun", n=32, bevel=0.001)
prism("Spoon", [(0.004, 0.1335), (0.021, 0.1335), (0.0345, 0.124), (0.0345, 0.058), (0.0315, 0.054),
                (0.0315, 0.06), (0.0315, 0.122), (0.0195, 0.1305), (0.004, 0.1305)],
      -0.0065, 0.0065, "orange", bevel=0.0007, seg=2)
cyl("Pin", (0.016, -0.016, 0.121), (0.016, 0.015, 0.121), 0.0011, mat="steel", n=12, bevel=0)
tube("PullRing", [(0.016, 0.015, 0.121), (0.016, 0.024, 0.13), (0.016, 0.033, 0.121),
                  (0.016, 0.024, 0.112)], 0.0012, "steel", closed=True)

stage((0, 0, 0.06), 0.14, 0.0)
render("smoke_grenade", {
    "hero": ((0.30, 0.26, 0.18), (0, 0, 0.065), 50),
    "top": ((-0.18, 0.2, 0.3), (0, 0, 0.07), 50),
})
