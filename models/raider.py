"""Raider: a scavenger in field gear, original design in the Arc Raiders style.

Built on an anatomical MakeHuman (MPFB) body. Every garment is a shell grown from the body
surface (inflated, smoothed, trimmed by planes, thickened, subdivided and given cloth folds), so the
layers sit on a real human form. Hard gear (helmet, respirator, goggles, pads, pack) is modelled on top.

Run:  blender -b -P models/raider.py            (full quality, ~millions of polys)
      blender -b -P models/raider.py -- quick   (preview)
Needs the MPFB extension. Outputs out/raider.blend, out/raider.glb, out/raider_<view>.png.
Units metres, Z up, the raider faces -Y.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from kit import *  # noqa: E402,F403  (resets the scene)
import addon_utils  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

HEIGHT = 1.80
SUBD = 1 if QUICK else 2           # subsurf levels on every piece
PRESUB = 0 if QUICK else 1         # extra pre-subdivision for the big garments
Z = Vector((0, 0, 1))

MOD = next(m.__name__ for m in addon_utils.modules() if m.__name__.split(".")[-1] == "mpfb")
addon_utils.enable(MOD, default_set=True)
HS = importlib.import_module(MOD + ".services.humanservice").HumanService
TSV = importlib.import_module(MOD + ".services.targetservice").TargetService


# ----------------------------------------------------------------------------- helpers
def get_co(me):
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def set_co(me, co):
    me.vertices.foreach_set("co", co.ravel())
    me.update()


def weights(obj):
    nv = len(obj.data.vertices)
    w = np.zeros((nv, len(obj.vertex_groups)))
    for v in obj.data.vertices:
        for g in v.groups:
            w[v.index, g.group] = g.weight
    return {g.name: w[:, g.index] for g in obj.vertex_groups}


def wsum(W, names):
    return sum((W[n] for n in names if n in W), np.zeros(len(next(iter(W.values())))))


def activate(obj):
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)


def apply_modifiers(obj):
    activate(obj)
    for m in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)


def subset_bmesh(obj, vmask):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if vmask is not None:
        dead = [f for f in bm.faces if not all(vmask[v.index] for v in f.verts)]
        bmesh.ops.delete(bm, geom=dead, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    return bm


def bisect(bm, keep):
    for pco, pno in keep:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                               plane_co=pco, plane_no=pno, clear_outer=True)


def link(name, bm):
    me = bpy.data.meshes.new(name)
    for lay in list(bm.verts.layers.deform.values()):   # drop the body's weights; skinning sets fresh ones
        bm.verts.layers.deform.remove(lay)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    COL.objects.link(o)
    return o


TEX = {}


def fold_tex(kind, size, **kw):
    key = (kind, size)
    if key not in TEX:
        t = bpy.data.textures.new(f"{kind}_{size}", kind)
        t.noise_scale = size
        for k, v in kw.items():
            setattr(t, k, v)
        TEX[key] = t
    return TEX[key]


def shell(name, mask, mat, inflate, thick, keep=(), smooth=0, src=None, presub=0, folds=0.0,
          subd=None):
    """Garment layer grown from src (default body): faces in mask, pushed out along the normals,
    relaxed, trimmed by planes (keep = (point, normal); the side the normal points to is cut),
    then subdivided, given cloth folds and thickened."""
    bm = subset_bmesh(src or body, mask)
    if presub:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=presub, use_grid_fill=True, smooth=1.0)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * inflate
    inner = [v for v in bm.verts if not v.is_boundary]
    for _ in range(smooth):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bisect(bm, keep)
    o = link(name, bm)
    s = o.modifiers.new("Subsurf", "SUBSURF")
    s.levels = s.render_levels = SUBD if subd is None else subd
    if folds:
        for kind, size, amp, kw in (("CLOUDS", 0.07, 1.0, dict(noise_depth=2)),
                                    ("MARBLE", 0.045, 0.45, dict(marble_type="SHARPER", turbulence=7.0,
                                                                 noise_depth=3))):
            d = o.modifiers.new(kind, "DISPLACE")
            d.texture = fold_tex(kind, size, **kw)
            d.strength = folds * amp
            d.mid_level = 0.5
    sol = o.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1.0
    sol.use_quality_normals = True
    sol.use_even_offset = False             # even offset spikes to infinity at sharp creases
    o.data.materials.append(mat)
    o.data.shade_smooth()
    return o


def last(name, mask, top=None, voxel=0.008, smooth=16):
    """Closed, voxel-remeshed copy of a body region (fuses toes, ears, folds into one form)."""
    bm = subset_bmesh(body, mask)
    if top is not None:
        bisect(bm, [(Vector((0, 0, top)), Z)])
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary])
    o = link(name, bm)
    r = o.modifiers.new("remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    sm = o.modifiers.new("smooth", "SMOOTH")
    sm.factor = 1.0
    sm.iterations = smooth
    apply_modifiers(o)
    return o


def rbox(name, center, size, mat, quat=None, bevel=0.012, subd=None):
    """Rounded box (pouches, pack), local -Y faces along quat."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    o = link(name, bm)
    o.location = center
    if quat is not None:
        o.rotation_mode = "QUATERNION"
        o.rotation_quaternion = quat
    b = o.modifiers.new("Bevel", "BEVEL")
    b.width = bevel
    b.segments = 3
    s = o.modifiers.new("Subsurf", "SUBSURF")
    s.levels = s.render_levels = SUBD if subd is None else subd
    d = o.modifiers.new("lumps", "DISPLACE")
    d.texture = fold_tex("CLOUDS", 0.05, noise_depth=2)
    d.strength = 0.004
    o.data.materials.append(mat)
    o.data.shade_smooth()
    return o


def facing(n):
    """Quaternion turning local -Y to the horizontal direction n."""
    h = Vector((n.x, n.y, 0)).normalized()
    return Vector((0, -1, 0)).rotation_difference(h)


def bvh(obj):
    bpy.context.view_layer.update()
    return BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())


# ----------------------------------------------------------------------------- materials
def leather(name, col, rough=0.5):
    m = simple(name, col, 0, rough, coat=0.15, bump=0.35, bump_scale=420)
    return m


MAT = dict(
    jacket=cloth("Jacket", (0.105, 0.10, 0.07), stain=(0.12, 0.09, 0.06), weave_scale=700),
    pants=cloth("Pants", (0.055, 0.055, 0.058), stain=(0.13, 0.10, 0.07), weave_scale=650),
    hood=cloth("Balaclava", (0.025, 0.025, 0.026), stain=None, weave_scale=900),
    scarf=cloth("Scarf", (0.42, 0.11, 0.035), stain=(0.12, 0.08, 0.05), weave_scale=420),
    cordura=cloth("Cordura", (0.24, 0.18, 0.105), stain=(0.10, 0.08, 0.05), weave_scale=520),
    webbing=cloth("Webbing", (0.04, 0.04, 0.036), stain=None, weave_scale=380),
    boot=leather("Boot_Leather", (0.065, 0.04, 0.025), 0.55),
    glove=leather("Glove_Leather", (0.03, 0.026, 0.022), 0.45),
    rubber=M["rubber"], poly=M["poly"], steel=M["steel"], gun=M["gun"],
    helmet=M["cream"], orange=M["orange"],
    lens=simple("Goggle_Lens", (0.12, 0.05, 0.008), 0.7, 0.06, emit=(1.0, 0.4, 0.05), strength=0.15, coat=1.0),
    glow=M["glow"],
)

# ----------------------------------------------------------------------------- 1. body
macro = TSV.get_default_macro_info_dict()
macro.update(gender=1.0, age=0.45, muscle=0.7, weight=0.55, proportions=0.85, height=0.6)
body = HS.create_human(macro_detail_dict=macro)
TSV.bake_targets(body)
body.name = "Raider_BaseBody"
co = get_co(body.data)
W0 = weights(body)
in_body = W0["body"] > 0.5
zmin, zmax = co[in_body, 2].min(), co[in_body, 2].max()
co[:, 2] -= zmin
co *= HEIGHT / (zmax - zmin)
set_co(body.data, co)
eye_c = [Vector(co[W0[g] > 0.5].mean(axis=0)) for g in ("helper-l-eye", "helper-r-eye")]
teeth = co[(W0["helper-upper-teeth"] > 0.5) | (W0["helper-lower-teeth"] > 0.5)]
mouth_c = Vector((0.0, teeth[:, 1].min(), teeth[:, 2].mean()))

rig = HS.add_builtin_rig(body, "game_engine")
B = {b.name: b.head_local.copy() for b in rig.data.bones}
BT = {b.name: b.tail_local.copy() for b in rig.data.bones}
for m in list(body.modifiers):
    if m.type == "ARMATURE":
        body.modifiers.remove(m)
apply_modifiers(body)                       # MASK modifier: drops eye/teeth/hair helpers
for c in rig.users_collection:               # keep the skeleton; it drives every garment
    c.objects.unlink(rig)
COL.objects.link(rig)
rig.name = rig.data.name = "Raider_Skeleton"
if body.name not in COL.objects:
    for c in body.users_collection:
        c.objects.unlink(body)
    COL.objects.link(body)

co = get_co(body.data)
W = weights(body)
FING = [f"{f}_0{i}" for f in ("index", "middle", "ring", "pinky", "thumb") for i in (1, 2, 3)]
hand_w = {s: wsum(W, [f"hand_{s}"] + [f"{f}_{s}" for f in FING]) for s in "lr"}
hands = hand_w["l"] + hand_w["r"]
arm_w = wsum(W, ["upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r"]) + hands
leg_w = wsum(W, [f"{b}_{s}" for b in ("thigh", "calf", "foot", "ball") for s in "lr"])
head_w = wsum(W, ["head", "neck_01"])
x, y, z = co[:, 0], co[:, 1], co[:, 2]

pel = B["pelvis"]
neck = B["neck_01"]
head_b = B["head"]
shoulder_z = B["upperarm_l"].z
knee_z = B["calf_l"].z
boot_top = knee_z - 0.13
belt_z = pel.z + 0.045
eye_z = (eye_c[0].z + eye_c[1].z) / 2
spine_y = B["spine_03"].y

# ----------------------------------------------------------------------------- 2. head: balaclava, helmet, goggles, respirator
head_last = last("head_last", (head_w > 0.15) & (arm_w < 0.1), voxel=0.009, smooth=12)
hood = shell("Balaclava", None, MAT["hood"], 0.003, 0.003, src=head_last, folds=0.0015,
             keep=[(Vector((0, 0, neck.z - 0.035)), -Z)])
HT = bvh(head_last)
head_top = max(v.co.z for v in head_last.data.vertices)
front_y = min(v.co.y for v in head_last.data.vertices if abs(v.co.z - eye_z) < 0.02)
back_y = max(v.co.y for v in head_last.data.vertices if abs(v.co.z - eye_z) < 0.02)
hx = max(abs(v.co.x) for v in head_last.data.vertices)

# helmet shell: brim at the brow, dropping toward the nape
slope = Vector((0, -0.38, -1)).normalized()
helmet = shell("Helmet", None, MAT["helmet"], 0.017, 0.006, src=head_last, smooth=12,
               keep=[(Vector((0, front_y, eye_z + 0.032)), slope)])
bev = helmet.modifiers.new("Bevel", "BEVEL")
bev.width = 0.002
bev.segments = 2
helmet.modifiers.move(helmet.modifiers.find("Bevel"), 0)
# raised centre ridge and a brow lip
ridge = shell("Helmet_Ridge", None, MAT["orange"], 0.026, 0.004, src=head_last, smooth=12,
              keep=[(Vector((0.022, 0, 0)), Vector((1, 0, 0))), (Vector((-0.022, 0, 0)), Vector((-1, 0, 0))),
                    (Vector((0, front_y, eye_z + 0.05)), slope)])
# ear comms pucks
for s, sgn in (("l", 1), ("r", -1)):
    c = Vector((sgn * (hx + 0.012), (front_y + back_y) / 2 + 0.01, eye_z - 0.03))
    revolve(f"Ear_Puck_{s}", [(0, 0), (0.036, 0), (0.038, 0.01), (0.034, 0.024), (0.022, 0.03), (0, 0.031)],
            base=c, axis=(sgn, 0, 0), n=64, mat=MAT["poly"], bevel=0.0015, seg=2)
    cyl(f"Ear_Mic_Boom_{s}", c + Vector((sgn * 0.02, -0.01, -0.01)), c + Vector((sgn * 0.004, -0.11, -0.05)),
        0.003, n=16, mat=MAT["gun"], bevel=0) if s == "r" else None
    cyl(f"Ear_Antenna_{s}", c + Vector((sgn * 0.025, 0.02, 0.01)), c + Vector((sgn * 0.035, 0.06, 0.16)),
        0.0025, 0.0015, n=16, mat=MAT["gun"], bevel=0) if s == "l" else None

# goggles: frame + lens per eye, strap around the head
for i, (s, sgn) in enumerate((("l", 1), ("r", -1))):
    e = eye_c[i]
    hit = HT.ray_cast(Vector((e.x, e.y - 0.3, e.z)), Vector((0, 1, 0)))[0] or Vector((e.x, front_y, e.z))
    axis = Vector((sgn * 0.25, -1, 0.05)).normalized()
    base = hit + Vector((0, 0.004, 0))
    revolve(f"Goggle_Frame_{s}", [(0.0235, 0), (0.030, 0.0), (0.031, 0.012), (0.028, 0.022), (0.022, 0.024),
                                  (0.021, 0.018)], base=base, axis=tuple(axis), n=72, mat=MAT["rubber"],
            bevel=0.001, seg=2)
    revolve(f"Goggle_Lens_{s}", [(0, 0.019), (0.0225, 0.0165), (0.0225, 0.012), (0, 0.012)], base=base,
            axis=tuple(axis), n=72, mat=MAT["lens"], bevel=0)
    revolve(f"Goggle_Bezel_{s}", [(0.0215, 0.019), (0.0245, 0.0195), (0.0245, 0.023), (0.0215, 0.0225)],
            base=base, axis=tuple(axis), n=72, mat=MAT["steel"], bevel=0.0006, seg=2)
cyl("Goggle_Bridge", eye_c[1] + Vector((0.02, -0.035 + (front_y - eye_c[1].y) * 0.0, 0.004)),
    eye_c[0] + Vector((-0.02, -0.035, 0.004)), 0.005, n=24, mat=MAT["rubber"], bevel=0)
shell("Goggle_Strap", None, MAT["webbing"], 0.010, 0.003, src=head_last,
      keep=[(Vector((0, 0, eye_z + 0.012)), Z), (Vector((0, 0, eye_z - 0.012)), -Z),
            (Vector((0, front_y + 0.03, 0)), Vector((0, -1, 0)))])

# respirator: rubber face piece over nose and mouth, twin filters, centre valve
resp = shell("Respirator", None, MAT["rubber"], 0.013, 0.006, src=head_last, smooth=18,
             keep=[(Vector((0, 0, eye_z - 0.018)), Z), (Vector((0, 0, mouth_c.z - 0.06)), -Z),
                   (Vector((0, mouth_c.y + 0.055, mouth_c.z)), Vector((0, 1, 0.35)).normalized())])
valve_c = Vector((0, mouth_c.y - 0.03, mouth_c.z - 0.008))
hitv = HT.ray_cast(Vector((0, -0.5, mouth_c.z - 0.008)), Vector((0, 1, 0)))[0]
if hitv:
    valve_c = hitv + Vector((0, -0.016, 0))
revolve("Resp_Valve", [(0, 0), (0.024, 0), (0.026, 0.008), (0.022, 0.022), (0.016, 0.03), (0, 0.031)],
        base=valve_c, axis=(0, -1, -0.25), n=64, mat=MAT["poly"], bevel=0.001, seg=2)
for k in range(5):
    cyl(f"Resp_Valve_Slat_{k}", valve_c + Vector((-0.014, -0.03 + 0.0005 * k, -0.012 + 0.006 * k)),
        valve_c + Vector((0.014, -0.03 + 0.0005 * k, -0.012 + 0.006 * k)), 0.0016, n=12, mat=MAT["steel"], bevel=0)
for s, sgn in (("l", 1), ("r", -1)):
    root = valve_c + Vector((sgn * 0.034, 0.012, 0.004))
    ax = Vector((sgn * 0.75, -0.55, -0.35)).normalized()
    revolve(f"Filter_Seat_{s}", [(0, 0), (0.024, 0), (0.024, 0.012), (0, 0.012)], base=root, axis=tuple(ax),
            n=64, mat=MAT["rubber"], bevel=0.001, seg=2)
    prof = [(0, 0.010), (0.033, 0.010)]
    for r_i in range(6):                          # ribbed canister wall
        h = 0.014 + r_i * 0.0065
        prof += [(0.0345, h), (0.0335, h + 0.0032)]
    prof += [(0.034, 0.053), (0.030, 0.058), (0, 0.058)]
    revolve(f"Filter_{s}", prof, base=root, axis=tuple(ax), n=96, mat=MAT["orange"], bevel=0.0008, seg=2)
    revolve(f"Filter_Cap_{s}", [(0, 0.0575), (0.026, 0.0575), (0.026, 0.0615), (0, 0.0615)], base=root,
            axis=tuple(ax), n=96, mat=MAT["gun"], bevel=0.0008, seg=2)

# ----------------------------------------------------------------------------- 3. jacket, scarf
jacket_mask = (z > pel.z - 0.06) & (hands < 0.4) & ((head_w < 0.6) | (z < neck.z + 0.06))
keep = [(Vector((0, 0, pel.z - 0.035)), -Z),
        (Vector((0, spine_y, neck.z + 0.035)), Vector((0, 0.45, 1)).normalized())]
for s in "lr":
    wr = B[f"hand_{s}"]
    fdir = (wr - B[f"lowerarm_{s}"]).normalized()
    keep.append((wr - fdir * 0.03, fdir))
jacket = shell("Jacket", jacket_mask, MAT["jacket"], 0.02, 0.004, keep=keep, smooth=8, presub=PRESUB,
               folds=0.011)
# sleeve cuffs and hem band (ribbed knit look via tighter folds)
for s in "lr":
    wr = B[f"hand_{s}"]
    fdir = (wr - B[f"lowerarm_{s}"]).normalized()
    shell(f"Jacket_Cuff_{s}", (arm_w > 0.3), MAT["jacket"], 0.016, 0.004,
          keep=[(wr - fdir * 0.032, fdir), (wr - fdir * 0.075, -fdir)], smooth=3)
# scarf: thick wrapped tube around the collar, plus a loose tail on the chest
ring = []
for a in np.linspace(0, 2 * math.pi, 48, endpoint=False):
    d = Vector((math.cos(a), math.sin(a), 0))
    o = Vector((0, neck.y, neck.z - 0.005 + 0.025 * math.sin(a)))
    hit = HT.ray_cast(o + d * 0.4, -d)[0]
    r_n = (hit - o).length if hit else 0.07
    ring.append(o + d * (max(r_n, 0.055) + 0.022))
scarf = tube("Scarf", ring, 0.03, MAT["scarf"], closed=True)
scarf.modifiers.new("Subsurf", "SUBSURF").levels = 2
sd = scarf.modifiers.new("lumps", "DISPLACE")
sd.texture = fold_tex("MARBLE", 0.03, marble_type="SHARPER", turbulence=7.0, noise_depth=3)
sd.strength = 0.012
tail = [ring[36] + Vector((0.01, -0.01, -0.02)), ring[36] + Vector((0.03, -0.035, -0.09)),
        ring[36] + Vector((0.035, -0.045, -0.17))]
st = tube("Scarf_Tail", tail, 0.022, MAT["scarf"])
st.modifiers.new("Subsurf", "SUBSURF").levels = 2
std = st.modifiers.new("lumps", "DISPLACE")
std.texture = sd.texture
std.strength = 0.01

# ----------------------------------------------------------------------------- 4. trousers, pockets, knee pads
pants_mask = ((leg_w > 0.2) | (z < pel.z + 0.1)) & (arm_w < 0.1) & (z > boot_top - 0.08) & (head_w < 0.1)
pants = shell("Trousers", pants_mask, MAT["pants"], 0.016, 0.004, smooth=8, presub=PRESUB, folds=0.012,
              keep=[(Vector((0, 0, pel.z + 0.085)), Z), (Vector((0, 0, boot_top - 0.04)), -Z)])
for s, sgn in (("l", 1), ("r", -1)):
    th, ca = B[f"thigh_{s}"], B[f"calf_{s}"]
    side = (leg_w > 0.3) & (sgn * x > 0)
    zc = knee_z + 0.17
    shell(f"Cargo_Pocket_{s}", side, MAT["pants"], 0.022, 0.005, smooth=4, presub=PRESUB, folds=0.003,
          keep=[(Vector((0, 0, zc + 0.09)), Z), (Vector((0, 0, zc - 0.09)), -Z),
                (Vector((0, th.y - 0.055, 0)), Vector((0, -1, 0))), (Vector((0, th.y + 0.05, 0)), Vector((0, 1, 0))),
                (Vector((th.x + sgn * 0.035, 0, 0)), Vector((-sgn, 0, 0)))])
    shell(f"Cargo_Flap_{s}", side, MAT["pants"], 0.03, 0.004, smooth=4,
          keep=[(Vector((0, 0, zc + 0.095)), Z), (Vector((0, 0, zc + 0.05)), -Z),
                (Vector((0, th.y - 0.06, 0)), Vector((0, -1, 0))), (Vector((0, th.y + 0.055, 0)), Vector((0, 1, 0))),
                (Vector((th.x + sgn * 0.03, 0, 0)), Vector((-sgn, 0, 0)))])
    # knee pad: hard shell over a strap
    front = (leg_w > 0.3) & (y < ca.y)
    shell(f"Knee_Pad_{s}", front, MAT["poly"], 0.03, 0.012, smooth=10,
          keep=[(Vector((0, 0, knee_z + 0.075)), Z), (Vector((0, 0, knee_z - 0.07)), -Z),
                (Vector((ca.x + 0.055, 0, 0)), Vector((1, 0, 0))), (Vector((ca.x - 0.055, 0, 0)), Vector((-1, 0, 0)))])
    shell(f"Knee_Strap_{s}", (leg_w > 0.3), MAT["webbing"], 0.017, 0.003,
          keep=[(Vector((0, 0, knee_z + 0.02)), Z), (Vector((0, 0, knee_z - 0.005)), -Z)])

# ----------------------------------------------------------------------------- 5. boots
blast = last("boot_last", (z < boot_top + 0.1) & (arm_w < 0.1), top=boot_top + 0.08, voxel=0.007)
boots = shell("Boots", None, MAT["boot"], 0.006, 0.005, src=blast, keep=[(Vector((0, 0, boot_top)), Z)])
shell("Boot_Cuffs", None, MAT["boot"], 0.012, 0.005, src=blast,
      keep=[(Vector((0, 0, boot_top)), Z), (Vector((0, 0, boot_top - 0.04)), -Z)])
shell("Boot_Soles", None, MAT["rubber"], 0.014, 0.008, src=blast, smooth=4,
      keep=[(Vector((0, 0, 0.028)), Z)])
shell("Boot_Toecaps", None, MAT["rubber"], 0.010, 0.004, src=blast,
      keep=[(Vector((0, 0, 0.07)), Z), (Vector((0, B["ball_l"].y + 0.01, 0)), Vector((0, 1, 0)))])
for s in "lr":                                   # buckle straps across the shaft
    f = B[f"foot_{s}"]
    for k, zz in enumerate((boot_top - 0.07, boot_top - 0.15)):
        m = (np.abs(x - f.x) < 0.09) & (z < boot_top + 0.1)
        shell(f"Boot_Strap_{s}{k}", None, MAT["webbing"], 0.015, 0.003, src=blast,
              keep=[(Vector((0, 0, zz + 0.012)), Z), (Vector((0, 0, zz - 0.012)), -Z),
                    (Vector((0, 0, 0.02)), -Z)] + ([(Vector((0, 0, 0)), Vector((-1, 0, 0)))] if s == "l"
                                                     else [(Vector((0, 0, 0)), Vector((1, 0, 0)))]))
bpy.data.objects.remove(blast)

# ----------------------------------------------------------------------------- 6. gloves
for s in "lr":
    wr = B[f"hand_{s}"]
    fdir = (wr - B[f"lowerarm_{s}"]).normalized()
    t = (co - np.array(wr)) @ np.array(fdir)
    near = (t > -0.12) & (wsum(W, [f"lowerarm_{s}"]) + hand_w[s] > 0.5)
    shell(f"Glove_{s}", near, MAT["glove"], 0.0025, 0.002, keep=[(wr - fdir * 0.07, -fdir)])
    shell(f"Glove_Cuff_{s}", near, MAT["glove"], 0.008, 0.004, smooth=3,
          keep=[(wr - fdir * 0.075, -fdir), (wr - fdir * 0.02, fdir)])
    knuck = hand_w[s] > 0.3
    # knuckle guard on the back of the hand: palm normal from the knuckle line
    up = (B[f"index_01_{s}"] - B[f"pinky_01_{s}"]).cross(B[f"middle_01_{s}"] - wr).normalized()
    if up.dot(B[f"thumb_03_{s}"] - B[f"middle_01_{s}"]) > 0:
        up = -up
    kc = (B[f"index_01_{s}"] + B[f"pinky_01_{s}"]) / 2
    shell(f"Knuckle_Guard_{s}", knuck, MAT["poly"], 0.008, 0.004, smooth=6,
          keep=[(kc + up * 0.0, -up), (kc + fdir * 0.02, fdir), (kc - fdir * 0.035, -fdir)])

# ----------------------------------------------------------------------------- 7. harness, chest rig, belt, shoulder pad
torso = (arm_w < 0.2) & (head_w < 0.3) & (leg_w < 0.3)
for s, sgn in (("l", 1), ("r", -1)):
    shell(f"Harness_Strap_{s}", torso, MAT["webbing"], 0.026, 0.004, smooth=6,
          keep=[(Vector((sgn * 0.072, 0, 0)), Vector((-sgn, 0, 0))), (Vector((sgn * 0.118, 0, 0)), Vector((sgn, 0, 0))),
                (Vector((0, 0, belt_z + 0.02)), -Z)])
plate = shell("Chest_Rig", torso & (y < spine_y), MAT["cordura"], 0.034, 0.014, smooth=14, presub=PRESUB,
              keep=[(Vector((0, 0, shoulder_z - 0.07)), Z), (Vector((0, 0, shoulder_z - 0.33)), -Z),
                    (Vector((0.135, 0, 0)), Vector((1, 0, 0))), (Vector((-0.135, 0, 0)), Vector((-1, 0, 0)))])
shell("Chest_Plate", torso & (y < spine_y), MAT["helmet"], 0.05, 0.008, smooth=16,
      keep=[(Vector((0, 0, shoulder_z - 0.09)), Z), (Vector((0, 0, shoulder_z - 0.22)), -Z),
            (Vector((0.11, 0, 0)), Vector((1, 0, 0))), (Vector((-0.11, 0, 0)), Vector((-1, 0, 0)))])
PT = bvh(plate)
for k, px in enumerate((-0.085, 0.0, 0.085)):    # mag pouches along the bottom of the rig
    zc = shoulder_z - 0.275
    hit, n, _, _ = PT.ray_cast(Vector((px, -0.6, zc)), Vector((0, 1, 0)))
    if hit:
        q = facing(n)
        rbox(f"Rig_Pouch_{k}", hit + n.normalized() * 0.03 + Vector((0, 0, 0.0)), (0.075, 0.05, 0.11),
             MAT["cordura"], q, bevel=0.012)
        rbox(f"Rig_Pouch_Flap_{k}", hit + n.normalized() * 0.058 + Vector((0, 0, 0.045)), (0.08, 0.012, 0.035),
             MAT["cordura"], q, bevel=0.005)
# radio on the left chest with antenna
hit, n, _, _ = PT.ray_cast(Vector((0.1, -0.6, shoulder_z - 0.14)), Vector((0, 1, 0)))
if hit:
    rbox("Radio", hit + n * 0.025, (0.05, 0.035, 0.09), MAT["poly"], facing(n), bevel=0.006)
    cyl("Radio_Antenna", hit + n * 0.03 + Vector((0.012, 0, 0.04)), hit + n * 0.03 + Vector((0.02, 0.0, 0.2)),
        0.0035, 0.002, n=16, mat=MAT["rubber"], bevel=0)
    sphere("Radio_LED", hit + n * 0.044 + Vector((-0.012, 0, 0.032)), 0.0035, MAT["glow"])

belt = shell("Belt", (np.abs(z - belt_z) < 0.07) & (arm_w < 0.1), MAT["webbing"], 0.024, 0.006, smooth=4,
             keep=[(Vector((0, 0, belt_z + 0.024)), Z), (Vector((0, 0, belt_z - 0.024)), -Z)])
BT_ = bvh(belt)
hit, n, _, _ = BT_.ray_cast(Vector((0, -0.6, belt_z)), Vector((0, 1, 0)))
if hit:
    rbox("Belt_Buckle", hit + n * 0.006, (0.07, 0.012, 0.05), MAT["steel"], facing(n), bevel=0.004, subd=1)
for k, ang in enumerate((50, 95, 140, 215, 265)):   # pouches round the belt (0 deg = front)
    a = math.radians(ang)
    d = Vector((math.sin(a), -math.cos(a), 0))
    o = Vector((0, B["pelvis"].y, belt_z - 0.02))
    hit, n, _, _ = BT_.ray_cast(o + d * 0.6, -d)
    if hit:
        size = (0.10, 0.06, 0.12) if k in (2, 3) else (0.065, 0.045, 0.09)
        rbox(f"Belt_Pouch_{k}", hit + d * (size[1] / 2 + 0.004) + Vector((0, 0, -0.025)), size, MAT["cordura"],
             facing(d), bevel=0.01)
        rbox(f"Belt_Pouch_Flap_{k}", hit + d * (size[1] + 0.006) + Vector((0, 0, size[2] / 2 - 0.035)),
             (size[0] * 1.04, 0.01, 0.04), MAT["cordura"], facing(d), bevel=0.004)
# canteen on the right hip
hit, n, _, _ = BT_.ray_cast(Vector((-0.6, B["pelvis"].y + 0.05, belt_z)), Vector((1, 0, 0)))
if hit:
    c = hit + Vector((-0.045, 0, -0.1))
    revolve("Canteen", [(0, 0), (0.038, 0.0), (0.042, 0.02), (0.042, 0.12), (0.03, 0.15), (0.012, 0.16),
                        (0.012, 0.175), (0, 0.175)], base=c, n=64, mat=MAT["orange"], bevel=0.001, seg=2)
# left shoulder pad (asymmetric armour)
up_arm = (B["lowerarm_l"] - B["upperarm_l"]).normalized()
t = (co - np.array(B["upperarm_l"])) @ np.array(up_arm)
upn = (Z - up_arm * up_arm.z).normalized()
shell("Shoulder_Pad_l", (wsum(W, ["upperarm_l", "clavicle_l"]) > 0.3) & (t > -0.06) & (t < 0.16),
      MAT["orange"], 0.034, 0.008, smooth=10,
      keep=[(B["upperarm_l"] - upn * 0.005, -upn), (B["upperarm_l"] + up_arm * 0.15, up_arm),
            (B["upperarm_l"] - up_arm * 0.05, -up_arm)])
shell("Shoulder_Pad_l_Lower", (wsum(W, ["upperarm_l"]) > 0.3) & (t > 0.06) & (t < 0.2),
      MAT["orange"], 0.028, 0.007, smooth=10,
      keep=[(B["upperarm_l"] - upn * 0.015, -upn), (B["upperarm_l"] + up_arm * 0.2, up_arm),
            (B["upperarm_l"] + up_arm * 0.11, -up_arm)])
shell("Arm_Band_r", (wsum(W, ["upperarm_r"]) > 0.4), MAT["scarf"], 0.02, 0.004,
      keep=[(B["upperarm_r"] + (B["lowerarm_r"] - B["upperarm_r"]).normalized() * 0.15,
             (B["lowerarm_r"] - B["upperarm_r"]).normalized()),
            (B["upperarm_r"] + (B["lowerarm_r"] - B["upperarm_r"]).normalized() * 0.11,
             -(B["lowerarm_r"] - B["upperarm_r"]).normalized())])

# ----------------------------------------------------------------------------- 8. backpack
JT = bvh(jacket)
hit = JT.ray_cast(Vector((0, 0.6, shoulder_z - 0.22)), Vector((0, -1, 0)))[0]
back_y = hit.y if hit else spine_y + 0.12
pc = Vector((0, back_y + 0.04 + 0.1, shoulder_z - 0.24))
rbox("Pack_Body", pc, (0.34, 0.2, 0.44), MAT["cordura"], bevel=0.05)
rbox("Pack_Lid", pc + Vector((0, 0.01, 0.235)), (0.35, 0.215, 0.07), MAT["cordura"], bevel=0.03)
rbox("Pack_Front_Pocket", pc + Vector((0, 0.12, -0.08)), (0.26, 0.06, 0.22), MAT["cordura"], bevel=0.025)
for sx in (-0.21, 0.21):
    rbox(f"Pack_Side_Pocket_{sx:+.0f}", pc + Vector((sx * 0.98, 0.0, -0.1)), (0.06, 0.13, 0.2), MAT["cordura"],
         bevel=0.02)
for sx in (-0.09, 0.09):                         # compression straps over the lid
    rbox(f"Pack_Strap_{sx:+.2f}", pc + Vector((sx, 0.11, 0.05)), (0.028, 0.008, 0.42), MAT["webbing"],
         bevel=0.003, subd=1)
    cyl(f"Pack_Buckle_{sx:+.2f}", pc + Vector((sx - 0.018, 0.118, -0.06)), pc + Vector((sx + 0.018, 0.118, -0.06)),
        0.007, n=24, mat=MAT["poly"], bevel=0.001, seg=1)
# bedroll on top, cinched by two straps
br0, br1 = pc + Vector((-0.22, 0.0, 0.32)), pc + Vector((0.22, 0.0, 0.32))
roll = cyl("Bedroll", br0, br1, 0.06, n=64, mat=MAT["scarf"], bevel=0.02, seg=4)
rd = roll.modifiers.new("lumps", "DISPLACE")
rd.texture = fold_tex("MARBLE", 0.03, marble_type="SHARPER", turbulence=7.0, noise_depth=3)
rd.strength = 0.008
for k in (-0.13, 0.13):
    cyl(f"Bedroll_Strap_{k:+.2f}", pc + Vector((k - 0.014, 0, 0.32)), pc + Vector((k + 0.014, 0, 0.32)),
        0.064, n=64, mat=MAT["webbing"], bevel=0.003, seg=2)
# external frame + salvaged canister clipped to the side
frame = [pc + Vector(p) for p in ((-0.19, -0.11, -0.25), (-0.2, -0.11, 0.27), (0.2, -0.11, 0.27),
                                   (0.19, -0.11, -0.25))]
tube("Pack_Frame", frame, 0.009, MAT["gun"], closed=True)
can0 = pc + Vector((0.255, 0.04, -0.2))
revolve("Pack_Canister", [(0, 0), (0.045, 0), (0.048, 0.01), (0.048, 0.25), (0.04, 0.27), (0.016, 0.275),
                          (0.016, 0.29), (0, 0.29)], base=can0, n=64, mat=MAT["orange"], bevel=0.001, seg=2)
revolve("Pack_Canister_Band", [(0.0485, 0.08), (0.051, 0.08), (0.051, 0.1), (0.0485, 0.1)], base=can0, n=64,
        mat=MAT["webbing"], bevel=0)
sphere("Pack_Canister_Light", can0 + Vector((0.0, -0.047, 0.2)), 0.007, MAT["glow"])
ant = [pc + Vector(p) for p in ((-0.15, 0.02, 0.27), (-0.16, 0.03, 0.5), (-0.18, 0.06, 0.72))]
tube("Pack_Antenna", ant, 0.003, MAT["rubber"])
for s, sgn in (("l", 1), ("r", -1)):            # shoulder straps into the pack
    pts = [Vector((sgn * 0.095, back_y + 0.012, shoulder_z - 0.02)),
           Vector((sgn * 0.11, back_y + 0.03, shoulder_z - 0.12)),
           Vector((sgn * 0.12, pc.y - 0.1, pc.z + 0.05))]
    tube(f"Pack_Shoulder_Strap_{s}", pts, 0.012, MAT["webbing"])

# ----------------------------------------------------------------------------- 9. finish: hide base body, ground, report
body.hide_render = True
body.hide_viewport = True
bpy.data.objects.remove(head_last)

# skinning: hard gear rides one bone rigidly, everything else copies the weights of the nearest
# body vertex (weights live on the base mesh and are interpolated through subsurf/solidify)
RIGID = [("Helmet", "head"), ("Ear_", "head"), ("Goggle", "head"), ("Resp", "head"), ("Filter", "head"),
         ("Chest_Plate", "spine_03"), ("Radio", "spine_03"), ("Rig_Pouch", "spine_02"),
         ("Pack_", "spine_03"), ("Bedroll", "spine_03"), ("Belt_", "pelvis"), ("Canteen", "pelvis"),
         ("Shoulder_Pad_l", "upperarm_l"), ("Knee_Pad_l", "calf_l"), ("Knee_Pad_r", "calf_r"),
         ("Knuckle_Guard_l", "hand_l"), ("Knuckle_Guard_r", "hand_r")]
bones = {b.name for b in rig.data.bones}
bco = get_co(body.data)
kd = KDTree(len(bco))
for i, p in enumerate(bco):
    kd.insert(p, i)
kd.balance()
gname = {g.index: g.name for g in body.vertex_groups}
vw = [[(gname[g.group], g.weight) for g in v.groups if gname[g.group] in bones and g.weight > 0.01]
      for v in body.data.vertices]
parts = [o for o in COL.objects if o.type == "MESH" and o is not body]
for o in parts:
    rigid = next((b for p, b in RIGID if o.name.startswith(p)), None)
    if rigid:
        o.vertex_groups.new(name=rigid).add(range(len(o.data.vertices)), 1.0, "REPLACE")
    else:
        mw = o.matrix_world
        groups = {}
        for v in o.data.vertices:
            for name, w in vw[kd.find(mw @ v.co)[1]]:
                g = groups.get(name) or groups.setdefault(name, o.vertex_groups.new(name=name))
                g.add([v.index], w, "REPLACE")
    arm = o.modifiers.new("Armature", "ARMATURE")
    arm.object = rig
    o.parent = rig
    o.matrix_parent_inverse = Matrix.Identity(4)

bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
low = min((o.evaluated_get(dg).matrix_world @ v.co).z for o in parts if o.name == "Boot_Soles"
          for v in o.evaluated_get(dg).data.vertices)
rig.location.z -= low
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
tris = 0
for o in COL.objects:
    if o.type == "MESH" and not o.hide_render:
        me = o.evaluated_get(dg).data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
print(f"[raider] parts={sum(1 for o in COL.objects if not o.hide_render)} tris={tris:,}")

# ----------------------------------------------------------------------------- 10. stage + render
world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.032, 0.036, 1)
bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, radius=6, segments=64)
floor = link("Floor", bm)
floor.data.materials.append(worn("Concrete", (0.11, 0.105, 0.1), 0, 0.85, (0.16, 0.15, 0.14), 0, 0.9, wear=0.4,
                                 grime=0.8, chip_depth=0.0, primer=None, sand=0.9))
C = Vector((0, 0, 0.95))
area("Key", (-2.2, -2.6, 3.0), 420, 1.6, (1.0, 0.9, 0.78), C + Vector((0, 0, 0.2)))
area("Fill", (2.6, -1.8, 1.3), 70, 2.5, (0.85, 0.9, 1.0), C)
area("Rim", (1.8, 2.6, 2.6), 700, 1.2, (0.7, 0.82, 1.0), C + Vector((0, 0, 0.4)))
area("Rim2", (-2.0, 2.2, 1.6), 300, 1.0, (1.0, 0.6, 0.3), C)
area("Top", (0, 0, 4.0), 90, 3.0, (1, 1, 1), C)
cams = {
    "hero": ((-1.55, -3.6, 1.35), (0, 0, 0.98), 55),
    "front": ((0, -4.6, 1.0), (0, 0, 0.95), 50),
    "back": ((2.2, 3.4, 1.4), (0, 0, 0.98), 55),
    "head": ((-0.45, -0.95, 1.72), (0, 0, 1.62), 85),
}
cam_objs = {}
for view, (loc, tgt, lens) in cams.items():
    cd = bpy.data.cameras.new(view)
    cd.lens = lens
    co_ = bpy.data.objects.new("Cam_" + view, cd)
    co_.location = loc
    scene.collection.objects.link(co_)
    look(co_, tgt)
    cam_objs[view] = co_
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
scene.cycles.samples = 24 if QUICK else 128
scene.cycles.use_denoising = True
r.resolution_x, r.resolution_y = 1080, 1350
r.resolution_percentage = 50 if QUICK else 100
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = -1.0
for look_name in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try:
        scene.view_settings.look = look_name
        break
    except TypeError:
        pass
os.makedirs(OUT, exist_ok=True)
scene.camera = cam_objs["hero"]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "raider.blend"))
only = [a for a in ARGS if a in cams]
for view in (only or cams):
    scene.camera = cam_objs[view]
    r.filepath = os.path.join(OUT, f"raider_{view}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", r.filepath)


# rig test: an action pose rendered from the hero camera (exports below stay in the rest A-pose)
def rotate_world(pb, axis, angle):
    h = pb.head.copy()
    pb.matrix = (Matrix.Translation(h) @ Matrix.Rotation(angle, 4, axis.normalized())
                 @ Matrix.Translation(-h) @ pb.matrix)
    bpy.context.view_layer.update()


P = rig.pose.bones
if not only or "pose" in ARGS:
    for s, sgn in (("l", 1), ("r", -1)):
        rotate_world(P[f"upperarm_{s}"], Vector((0, sgn, 0)), math.radians(48))
        d = (P[f"lowerarm_{s}"].tail - P[f"lowerarm_{s}"].head).normalized()
        rotate_world(P[f"lowerarm_{s}"], d.cross(Vector((0, -1, 0))), math.radians(35))
    rotate_world(P["thigh_r"], Vector((1, 0, 0)), math.radians(-28))
    rotate_world(P["calf_r"], Vector((1, 0, 0)), math.radians(45))
    rotate_world(P["thigh_l"], Vector((1, 0, 0)), math.radians(8))
    rotate_world(P["spine_03"], Z, math.radians(12))
    rotate_world(P["head"], Z, math.radians(-18))
    scene.camera = cam_objs["hero"]
    r.filepath = os.path.join(OUT, "raider_pose.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", r.filepath)
    for pb in P:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

if "noexport" not in ARGS and not QUICK:
    def select_model():
        for o in bpy.context.view_layer.objects:
            o.select_set(o is rig or (o in parts and not o.hide_render))

    select_model()
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "raider.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_skins=True)
    print("EXPORTED", os.path.join(OUT, "raider.glb"))
    # game version: no subdivision or fold displacement, same skeleton and skinning
    for o in parts:
        for m in o.modifiers:
            if m.type == "SUBSURF":
                m.levels = 0
            elif m.type == "DISPLACE":
                m.show_viewport = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    game_tris = 0
    for o in parts:
        me = o.evaluated_get(dg).data
        me.calc_loop_triangles()
        game_tris += len(me.loop_triangles)
    print(f"[raider] game tris={game_tris:,}")
    select_model()
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "raider_game.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_skins=True)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "raider_game.fbx"), use_selection=True,
                             add_leaf_bones=False, use_mesh_modifiers=True, mesh_smooth_type="FACE")
    print("EXPORTED game versions")
