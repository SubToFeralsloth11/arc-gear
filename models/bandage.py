"""Bandage -- tight-wound elastic crepe bandage with edge stripes, unrolled tail and clip,
next to a sealed field-dressing pouch with a red cross."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *
set_texture_scale(3.0)

crepe = cloth("Crepe", (0.62, 0.50, 0.36), stain=(0.30, 0.06, 0.04), weave_scale=320)
stripe = cloth("CrepeStripe", (0.08, 0.16, 0.42), stain=None, weave_scale=320)
pouch = paint("Pouch_Olive", (0.20, 0.22, 0.13), wear=0.6, sand=0.8)
red = paint("Paint_Red", (0.55, 0.04, 0.03), wear=0.8)

R, W, HOLE = 0.022, 0.075, 0.0035  # elastic bandages wind tight: small core, wide strip
CZ = R


def wound_end(h, sign):
    """End face stepped every layer so the winding reads as tight rings."""
    pts, r, k = [], HOLE, 0
    while r < R - 0.001:
        pts.append((r, h - sign * (0.0003 if k % 2 else 0.0)))
        r += 0.0011
        k += 1
    return pts


prof = (wound_end(-W / 2, -1) + [(R - 0.0008, -W / 2), (R, -W / 2 + 0.0015), (R, W / 2 - 0.0015),
                                 (R - 0.0008, W / 2)] + wound_end(W / 2, 1)[::-1] + [(HOLE, -W / 2)])
revolve("Roll", prof, base=(0, 0, CZ), axis=(0, 1, 0), n=64, mat=crepe, bevel=0)
for y in (-W / 2 + 0.004, W / 2 - 0.007):  # woven edge stripes
    cyl("EdgeStripe", (0, y, CZ), (0, y + 0.003, CZ), R + 0.0003, mat=stripe, n=64, bevel=0)

# tail: wraps off the front of the roll and lies rippled on the floor
ny = 8
bm = bmesh.new()
Rt = R + 0.0008
X0, X1 = Rt + 0.024, Rt + 0.2  # where the tail lands and ends


def floor_z(x):
    return 0.0012 + 0.0016 * math.sin(x * 160) ** 2 + max(x - (X1 - 0.025), 0) ** 2 * 6


path = [(Rt * math.cos(a), CZ + Rt * math.sin(a))  # over the top and down the front
        for a in (math.pi / 2 * (1 - k / 14) for k in range(15))]
for k in range(1, 13):  # drape: bezier from the roll front to the floor
    t = k / 12
    p0, p1, p2 = (Rt, CZ), (Rt, 0.0012), (X0, floor_z(X0))
    path.append(((1 - t) ** 2 * p0[0] + 2 * t * (1 - t) * p1[0] + t * t * p2[0],
                 (1 - t) ** 2 * p0[1] + 2 * t * (1 - t) * p1[1] + t * t * p2[1]))
for k in range(1, 61):
    x = X0 + (X1 - X0) * k / 60
    path.append((x, floor_z(x)))
rows = []
for i, (x, z) in enumerate(path):
    drift = 0.004 * math.sin(i / len(path) * 9)
    rows.append([bm.verts.new((x, -W / 2 + W * j / (ny - 1) + drift, z)) for j in range(ny)])
nx = len(rows)
for i in range(nx - 1):
    for j in range(ny - 1):
        bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
tail = mesh_obj("Tail", bm)
sol = tail.modifiers.new("Solidify", "SOLIDIFY")
sol.thickness = 0.0012
sol.offset = 0
finish(tail, crepe, bevel=0, subsurf=1)

# elastic clip (two hooked prongs on a strip) holding the tail
cx = Rt + 0.11
lift = floor_z(cx)
prism("ClipBand", box(cx - 0.003, lift + 0.0008, cx + 0.003, lift + 0.0018), -0.03, 0.03,
      cloth("ClipElastic", (0.05, 0.05, 0.05), stain=None, weave_scale=900), bevel=0.0004, seg=1)
for y in (-0.034, 0.034):
    prism("ClipHook", [(cx - 0.007, lift + 0.0018), (cx + 0.007, lift + 0.0018),
                       (cx + 0.004, lift - 0.0005), (cx - 0.004, lift - 0.0005)],
          y - 0.004, y + 0.004, "steel", bevel=0.0004, seg=1)

# sealed field dressing pouch with red cross
pz = 0.009
sym_pts = box(-0.17, 0.0, -0.06, 2 * pz)
p = prism("Pouch", sym_pts, -0.04, 0.05)
finish(p, pouch, bevel=0.006, seg=1, subsurf=2)
prism("PouchSeam", box(-0.172, pz - 0.0015, -0.058, pz + 0.0015), -0.042, 0.052, pouch,
      bevel=0.001, seg=1)
prism("CrossV", box(-0.122, 2 * pz - 0.0005, -0.108, 2 * pz + 0.0012), -0.012, 0.022, red,
      bevel=0.0005, seg=1)
prism("CrossH", box(-0.132, 2 * pz - 0.0005, -0.098, 2 * pz + 0.0009), -0.002, 0.012, red,
      bevel=0.0005, seg=1)
prism("TearTab", [(-0.064, pz - 0.001), (-0.05, pz - 0.001), (-0.048, pz + 0.001),
                  (-0.064, pz + 0.001)], 0.03, 0.045, "orange", bevel=0.0005, seg=1)

stage((-0.03, 0.0, 0.02), 0.22, 0.0)
render("bandage", {
    "hero": ((0.22, 0.26, 0.19), (-0.02, 0.0, 0.012), 40),
    "low": ((0.26, -0.2, 0.08), (0.0, 0.0, 0.015), 45),
})
