"""HCR-1 "Breaker" -- heavy single-shot sci-fi assault rifle (Arc Raiders inspired).

Run:  blender -b -P build.py            (full quality renders)
      blender -b -P build.py -- quick   (fast low-res preview)
Outputs breaker_rifle.blend and renders/*.png next to this file.
Axis: muzzle +X, up +Z, right side +Y. Units: metres.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

OUT = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "quick" in ARGS

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COL = bpy.data.collections.new("Breaker")
scene.collection.children.link(COL)

Z0 = 0.012  # bore axis height


# ----------------------------------------------------------------- materials
def sock(socks, ident):
    return next(s for s in socks if s.identifier == ident)


def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m, nt, b


def ramp(nt, src, a, b, ca=0.0, cb=1.0, constant=False):
    n = nt.nodes.new("ShaderNodeValToRGB")
    e = n.color_ramp.elements
    e[0].position, e[1].position = a, b
    e[0].color = (ca, ca, ca, 1)
    e[1].color = (cb, cb, cb, 1)
    if constant:
        n.color_ramp.interpolation = "CONSTANT"
    nt.links.new(src, n.inputs["Fac"])
    return n.outputs["Color"]


def math_n(nt, op, a, b):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def maprange(nt, src, lo, hi):
    n = nt.nodes.new("ShaderNodeMapRange")
    nt.links.new(src, n.inputs["Value"])
    n.inputs["To Min"].default_value = lo
    n.inputs["To Max"].default_value = hi
    return n.outputs["Result"]


def mix_col(nt, fac, a, b, blend="MIX"):
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    n.blend_type = blend
    for ident, v in (("Factor_Float", fac), ("A_Color", a), ("B_Color", b)):
        s = sock(n.inputs, ident)
        if isinstance(v, (int, float)):
            s.default_value = v
        elif isinstance(v, tuple):
            s.default_value = (*v, 1) if len(v) == 3 else v
        else:
            nt.links.new(v, s)
    return sock(n.outputs, "Result_Color")


def noise(nt, scale, detail=8, rough=0.6, coord="Object", stretch=None):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    tc = nt.nodes.new("ShaderNodeTexCoord")
    src = tc.outputs[coord]
    if stretch:
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = stretch
        nt.links.new(src, mp.inputs["Vector"])
        src = mp.outputs["Vector"]
    nt.links.new(src, n.inputs["Vector"])
    return n.outputs["Fac"]


def worn(name, col, metal, rough, wcol, wmetal, wrough, wear=1.0, grime=0.5,
         chip_depth=0.25, micro=0.04, sand=0.6, primer=(0.23, 0.2, 0.17), brushed=False):
    """Layered material: tinted paint -> primer -> bare metal chips, cavity grime,
    scratches, smudged roughness, and sand/dust settling on top faces and in crevices."""
    m, nt, b = new_mat(name)
    L = nt.links.new
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    bev = nt.nodes.new("ShaderNodeBevel")  # rounded-normal vs true normal = edge mask
    bev.samples = 8
    bev.inputs["Radius"].default_value = 0.008
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L(bev.outputs["Normal"], dot.inputs[0])
    L(geo.outputs["Normal"], dot.inputs[1])
    edge = ramp(nt, dot.outputs["Value"], 0.80, 0.985, 1.0, 0.0)
    n_chip = noise(nt, 30, 14, 0.7)
    n_spot = noise(nt, 7, 10, 0.7)
    scratch = noise(nt, 60, 4, 0.5, stretch=(1, 1, 35))
    s = math_n(nt, "ADD", math_n(nt, "MULTIPLY", edge, 0.8), math_n(nt, "MULTIPLY", n_chip, 0.6))
    t = 1.02 - 0.08 * wear
    edge_wear = ramp(nt, s, t, t + 0.03)
    edge_primer = ramp(nt, s, t - 0.07, t - 0.04)
    st = 0.69 - 0.03 * wear
    spot_wear = ramp(nt, n_spot, st, st + 0.01)
    spot_primer = ramp(nt, n_spot, st - 0.025, st - 0.015)
    scr = ramp(nt, scratch, 0.66, 0.68)
    scr = math_n(nt, "MULTIPLY", scr, 0.7 * wear)
    wmask = math_n(nt, "MAXIMUM", math_n(nt, "MAXIMUM", edge_wear, spot_wear), scr)
    wmask = math_n(nt, "MINIMUM", wmask, 1.0)
    pmask = math_n(nt, "MAXIMUM", edge_primer, spot_primer)
    # grime: large blotches + cavities (AO) + vertical streaks
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 12
    ao.inputs["Distance"].default_value = 0.02
    cav = ramp(nt, ao.outputs["AO"], 0.35, 1.0, 1.0, 0.0)
    blot = ramp(nt, noise(nt, 3.5, 6, 0.55), 0.4, 0.75)
    streak = ramp(nt, noise(nt, 45, 6, 0.6, stretch=(1, 1, 0.08)), 0.55, 0.78)
    g = math_n(nt, "ADD", math_n(nt, "MULTIPLY", cav, 1.0), math_n(nt, "MULTIPLY", blot, 0.5))
    g = math_n(nt, "MINIMUM", math_n(nt, "ADD", g, math_n(nt, "MULTIPLY", streak, 0.35)), 1.0)
    g = math_n(nt, "MULTIPLY", g, grime)
    # paint: low-frequency tint/fade variation + speckle
    tint = math_n(nt, "MULTIPLY", ramp(nt, noise(nt, 2.2, 4, 0.5), 0.3, 0.7), 0.5)
    faded = tuple(min(1.0, c * 1.12 + 0.03) for c in col)
    shaded = tuple(c * 0.8 for c in col)
    base = mix_col(nt, tint, shaded, faded)
    speck = math_n(nt, "MULTIPLY", ramp(nt, noise(nt, 700, 2, 0.5), 0.6, 0.75), 0.12)
    base = mix_col(nt, speck, base, tuple(c * 0.6 for c in col))
    dirty = tuple(c * 0.35 for c in col)
    base = mix_col(nt, g, base, (dirty[0] * 0.9, dirty[1] * 0.85, dirty[2] * 0.7))
    if primer:
        base = mix_col(nt, pmask, base, primer)
    final = mix_col(nt, wmask, base, wcol)
    # sand: settles on upward faces (clumpy) and packs into crevices
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L(geo.outputs["Normal"], sep.inputs[0])
    up = ramp(nt, sep.outputs["Z"], 0.25, 0.85)
    grain = ramp(nt, noise(nt, 90, 10, 0.75), 0.42, 0.62)
    clump = ramp(nt, noise(nt, 6, 5, 0.6), 0.35, 0.7)
    top = math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", up, grain), clump)
    crev = math_n(nt, "MULTIPLY", math_n(nt, "MULTIPLY", ramp(nt, cav, 0.5, 1.0), grain), 0.65)
    smask = math_n(nt, "MINIMUM", math_n(nt, "MULTIPLY", math_n(nt, "ADD", top, crev), sand * 1.45), 1.0)
    sand_col = mix_col(nt, noise(nt, 140, 4, 0.6), (0.48, 0.38, 0.25), (0.72, 0.62, 0.46))
    L(mix_col(nt, smask, final, sand_col), b.inputs["Base Color"])
    met = math_n(nt, "MULTIPLY", maprange(nt, wmask, metal, wmetal),
                 math_n(nt, "SUBTRACT", 1.0, smask))
    L(met, b.inputs["Metallic"])
    # roughness: base variation, smudges, optional brushing, grime, chips, sand
    rvar = maprange(nt, noise(nt, 9, 6, 0.6), rough - 0.07, rough + 0.09)
    smudge = maprange(nt, ramp(nt, noise(nt, 22, 3, 0.5), 0.45, 0.7), 0.0, -0.14)
    rvar = math_n(nt, "ADD", rvar, smudge)
    if brushed:
        rvar = math_n(nt, "ADD", rvar, maprange(nt, noise(nt, 30, 3, 0.5, stretch=(0.03, 1, 1)), -0.08, 0.08))
    rg = math_n(nt, "ADD", rvar, math_n(nt, "MULTIPLY", g, 0.15))
    rr = nt.nodes.new("ShaderNodeMix")
    rr.data_type = "FLOAT"
    L(wmask, sock(rr.inputs, "Factor_Float"))
    L(rg, sock(rr.inputs, "A_Float"))
    sock(rr.inputs, "B_Float").default_value = wrough
    rs = nt.nodes.new("ShaderNodeMix")
    rs.data_type = "FLOAT"
    L(smask, sock(rs.inputs, "Factor_Float"))
    L(sock(rr.outputs, "Result_Float"), sock(rs.inputs, "A_Float"))
    sock(rs.inputs, "B_Float").default_value = 0.95
    L(sock(rs.outputs, "Result_Float"), b.inputs["Roughness"])
    # bump: chips recessed, fine surface grain, gritty sand
    b1 = nt.nodes.new("ShaderNodeBump")
    b1.inputs["Strength"].default_value = chip_depth
    b1.inputs["Distance"].default_value = 0.0004
    L(math_n(nt, "SUBTRACT", 1.0, math_n(nt, "MAXIMUM", wmask, math_n(nt, "MULTIPLY", pmask, 0.5))),
      b1.inputs["Height"])
    b2 = nt.nodes.new("ShaderNodeBump")
    b2.inputs["Strength"].default_value = micro
    b2.inputs["Distance"].default_value = 0.0002
    L(noise(nt, 420, 4, 0.5), b2.inputs["Height"])
    b3 = nt.nodes.new("ShaderNodeBump")
    b3.inputs["Distance"].default_value = 0.0006
    L(math_n(nt, "MULTIPLY", smask, 0.8), b3.inputs["Strength"])
    L(noise(nt, 1100, 3, 0.6), b3.inputs["Height"])
    L(b1.outputs["Normal"], b2.inputs["Normal"])
    L(b2.outputs["Normal"], b3.inputs["Normal"])
    L(b3.outputs["Normal"], b.inputs["Normal"])
    return m


def simple(name, col, metal=0.0, rough=0.5, emit=None, strength=0.0, coat=0.0,
           trans=0.0, bump=0.0, bump_scale=300):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Transmission Weight"].default_value = trans
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    if bump:
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        bn.inputs["Distance"].default_value = 0.0005
        nt.links.new(noise(nt, bump_scale, 3, 0.5), bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], b.inputs["Normal"])
    return m


def hazard():
    m, nt, b = new_mat("Hazard")
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = "BANDS"
    w.bands_direction = "DIAGONAL"
    w.inputs["Scale"].default_value = 28
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    f = ramp(nt, w.outputs["Fac"], 0.5, 0.51, constant=True)
    nt.links.new(mix_col(nt, f, (0.02, 0.02, 0.02), (0.85, 0.42, 0.03)), b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    return m


M = {
    "cream": worn("Paint_Cream", (0.50, 0.465, 0.38), 0, 0.52, (0.20, 0.20, 0.205), 1, 0.35, wear=1.3, grime=0.6),
    "orange": worn("Paint_Orange", (0.80, 0.26, 0.035), 0, 0.48, (0.20, 0.20, 0.205), 1, 0.35, wear=1.2, grime=0.5),
    "gun": worn("Gunmetal", (0.030, 0.032, 0.036), 1, 0.38, (0.30, 0.30, 0.31), 1, 0.22, wear=0.7, grime=0.35, chip_depth=0.05, micro=0.05, primer=None, brushed=True, sand=0.35),
    "poly": worn("Polymer", (0.032, 0.032, 0.03), 0, 0.62, (0.11, 0.105, 0.1), 0, 0.45, wear=0.6, grime=0.3, chip_depth=0.02, micro=0.25, primer=None, sand=0.45),
    "rubber": worn("Rubber", (0.02, 0.02, 0.019), 0, 0.86, (0.06, 0.058, 0.055), 0, 0.7, wear=0.3, grime=0.3, chip_depth=0.0, micro=0.4, primer=None, sand=0.8),
    "brass": worn("Brass", (0.78, 0.52, 0.22), 1, 0.25, (0.9, 0.7, 0.4), 1, 0.15, wear=0.3, grime=0.25, chip_depth=0.0, primer=None, sand=0.1),
    "steel": worn("Steel", (0.62, 0.62, 0.63), 1, 0.2, (0.8, 0.8, 0.8), 1, 0.12, wear=0.3, grime=0.4, chip_depth=0.0, primer=None, brushed=True, sand=0.3),
    "lens": simple("Lens", (0.01, 0.012, 0.015), 0, 0.03, emit=(1.0, 0.35, 0.04), strength=0.25, coat=1.0),
    "glass": simple("Glass", (0.9, 0.95, 1.0), 0, 0.06, trans=1.0),
    "glow": simple("Glow_Amber", (1.0, 0.45, 0.05), 0, 0.4, emit=(1.0, 0.42, 0.05), strength=16.0),
    "hazard": hazard(),
}


# ------------------------------------------------------------------ geometry
def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    COL.objects.link(o)
    return o


def finish(o, mat, bevel=0.003, seg=3, angle=35, subsurf=0):
    o.data.materials.clear()
    o.data.materials.append(M[mat] if isinstance(mat, str) else mat)
    if bevel > 0:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = seg
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(angle)
        b.use_clamp_overlap = True
        b.miter_outer = "MITER_ARC"
        b.harden_normals = not subsurf
    if subsurf:
        s = o.modifiers.new("Subsurf", "SUBSURF")
        s.levels = s.render_levels = subsurf
    else:
        w = o.modifiers.new("WeightedNormal", "WEIGHTED_NORMAL")
        w.keep_sharp = True
    o.data.shade_smooth()
    return o


def prism(name, polys, y0, y1, mat=None, **kw):
    """Extrude one or more XZ side-profile polygons along Y."""
    if isinstance(polys[0][0], (int, float)):
        polys = [polys]
    bm = bmesh.new()
    for pts in polys:
        a = [bm.verts.new((x, y0, z)) for x, z in pts]
        c = [bm.verts.new((x, y1, z)) for x, z in pts]
        bm.faces.new(a)
        bm.faces.new(list(reversed(c)))
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], c[j], c[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_obj(name, bm)
    return finish(o, mat, **kw) if mat else o


def sym(name, pts, w, mat=None, **kw):
    return prism(name, pts, -w / 2, w / 2, mat, **kw)


def cyl(name, p0, p1, r, r2=None, n=48, mat=None, **kw):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r,
                          radius2=r if r2 is None else r2, depth=d.length,
                          matrix=Matrix.Translation((p0 + p1) / 2) @ rot)
    o = mesh_obj(name, bm)
    return finish(o, mat, **kw) if mat else o


def sphere(name, c, r, mat, scale=(1, 1, 1)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r,
                              matrix=Matrix.Translation(c) @ Matrix.Diagonal((*scale, 1)))
    return finish(mesh_obj(name, bm), mat, bevel=0)


def tube(name, pts, r, mat, closed=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.use_cyclic_u = closed
    tmp = bpy.data.objects.new(name + "_crv", cu)
    COL.objects.link(tmp)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(tmp)
    o = bpy.data.objects.new(name, me)
    COL.objects.link(o)
    return finish(o, mat, bevel=0)


def cut(o, cutters, op="DIFFERENCE"):
    """Apply exact booleans destructively, then delete the cutters."""
    for c in cutters:
        m = o.modifiers.new("Bool", "BOOLEAN")
        m.operation = op
        m.object = c
        m.solver = "EXACT"
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    o.modifiers.clear()
    old, o.data = o.data, me
    bpy.data.meshes.remove(old)
    for c in cutters:
        bpy.data.objects.remove(c)
    return o


def box(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def screw(x, z, y, side):
    return cyl("Screw", (x, y, z), (x, y + side * 0.0028, z), 0.0042, 0.0036, n=6, mat="gun",
               bevel=0.0007, seg=2)


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


# ----------------------------------------------------------- scene / render
def look(obj, target):
    c = obj.constraints.new("TRACK_TO")
    e = bpy.data.objects.new(obj.name + "_target", None)
    e.location = target
    scene.collection.objects.link(e)
    c.target = e
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"


def area(name, loc, energy, size, color, target=(0.37, 0, 0), shape="SQUARE", size_y=None):
    l = bpy.data.lights.new(name, "AREA")
    l.energy = energy
    l.color = color
    l.shape = shape
    l.size = size
    if size_y:
        l.size_y = size_y
    o = bpy.data.objects.new(name, l)
    o.location = loc
    scene.collection.objects.link(o)
    look(o, target)


world = bpy.data.worlds.new("World")
scene.world = world
try:
    world.use_nodes = True
except Exception:
    pass
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.010, 0.011, 0.013, 1)

floor_bm = bmesh.new()
bmesh.ops.create_grid(floor_bm, x_segments=1, y_segments=1, size=6,
                      matrix=Matrix.Translation((0.4, 0, -0.30)))
floor = bpy.data.objects.new("Floor", bpy.data.meshes.new("Floor"))
floor_bm.to_mesh(floor.data)
floor_bm.free()
scene.collection.objects.link(floor)
floor.data.materials.append(simple("Floor", (0.018, 0.018, 0.02), 0, 0.55))

area("Key", (0.7, 1.5, 1.2), 95, 1.3, (1.0, 0.92, 0.82))
area("Rim", (-0.5, -1.3, 0.9), 220, 1.0, (0.72, 0.82, 1.0))
area("Top", (0.37, 0.1, 1.3), 45, 1.8, (1, 1, 1), shape="RECTANGLE", size_y=0.35)
area("Fill", (1.8, 0.4, 0.05), 18, 1.0, (1, 0.95, 0.9))
area("Kick", (2.2, -0.6, 0.4), 70, 0.6, (1.0, 0.6, 0.3), target=(0.9, 0, 0))

cams = {
    "hero": ((1.55, 1.45, 0.55), (0.40, 0, -0.02), 35),
    "side_right": ((0.37, 2.45, 0.02), (0.37, 0, -0.02), 50),
    "side_left": ((0.45, -1.55, 0.42), (0.37, 0, -0.02), 35),
    "breech": ((0.36, 0.42, 0.10), (0.17, 0, -0.03), 42),
    "muzzle": ((1.45, 0.38, 0.17), (0.92, 0, 0.0), 50),
}
cam_objs = {}
for name, (loc, tgt, lens) in cams.items():
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    co = bpy.data.objects.new("Cam_" + name, cd)
    co.location = loc
    scene.collection.objects.link(co)
    look(co, tgt)
    cam_objs[name] = co

r = scene.render
r.engine = "CYCLES"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:
    print("GPU setup failed, using CPU:", e)
scene.cycles.samples = 32 if QUICK else 160
scene.cycles.use_denoising = True
r.resolution_x, r.resolution_y = 1600, 900
r.resolution_percentage = 50 if QUICK else 100
scene.view_settings.view_transform = "AgX"
for look_name in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try:
        scene.view_settings.look = look_name
        break
    except TypeError:
        pass

scene.camera = cam_objs["hero"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "breaker_rifle.blend"))

only = [a for a in ARGS if a in cams]
for name in (only or cams):
    scene.camera = cam_objs[name]
    r.filepath = os.path.join(OUT, "renders", f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", r.filepath)
