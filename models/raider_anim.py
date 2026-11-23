"""Raider animation set: heavy, grounded, gear-laden movement in the Arc Raiders style.

Every clip is generated procedurally on the Raider_Skeleton from out/raider.blend (run models/raider.py
first). Poses are parent-relative rotations about rest-space axes; legs and weapon arms use analytic
two-bone IK, and every frame is baked.

Weight and balance:
- A centre-of-mass model (segment masses, a 11 kg backpack behind the chest, the rifle in the hands)
  is solved every frame: the pelvis slides until the CoM sits over the support (both boots, one boot,
  the ball of a heel-up foot, or a knee and toes when kneeling), then the legs are re-solved so the
  boots stay planted. Walking shifts the weight laterally onto each stance boot.
- Boots: soles stay flat on the ground, heels peel up over the ball, toes lift onto the heel, the
  pushing boot rolls onto its inner edge when strafing, and every knee tracks over its toes.
- Rifle holds (aim, low ready, sprint carry) place the weapon in the chest frame, then lock both
  hands to it (right hand on the pistol grip, left hand under the handguard). The rifle rides a
  `weapon_r` socket bone under hand_r; its rest transform is the attach offset for any weapon.

Run:  blender -b -P models/raider_anim.py                (bake clips, export, EEVEE preview videos)
      blender -b -P models/raider_anim.py -- quick       (Workbench previews, no export)
      blender -b -P models/raider_anim.py -- Walk Jog    (only the named clips)
      add `stills` for a contact sheet per clip, `noexport` to skip export, `norender` to skip previews.
Outputs out/raider_anim.blend, out/raider_anim.glb and .fbx (game mesh + weapon_r socket, every clip
as its own action), out/anim/<clip>.mp4 and out/anim/raider_reel.mp4.
All clips are in place (no root motion); CLIPS[...]["speed"] is the speed to move the capsule at.
Units metres, Z up, the raider faces -Y, its left is +X.
"""
import math
import os
import shutil
import subprocess
import sys

import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Quaternion, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "quick" in ARGS
FPS = 30

bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "raider.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["Raider_Skeleton"]
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
FWD = Vector((0, -1, 0))
SIDES = (("l", 1), ("r", -1))
FINGERS = ("index", "middle", "ring", "pinky")


def q(axis, deg):
    return Quaternion(axis, math.radians(deg))


def basis(d, l):
    e1 = d.normalized()
    e2 = (l - e1 * l.dot(e1)).normalized()
    return Matrix((e1, e2, e1.cross(e2))).transposed()


# ----------------------------------------------------------------------------- weapon + hand frames
# Rifle local frame (models/ar.py): barrel +X, up +Z. Held level and facing -Y it maps by W0.
W0 = q(Z, -90)
AR = dict(butt=Vector((-0.385, 0.0, -0.01)), grip=Vector((-0.048, 0.0, -0.085)),
          com=Vector((0.12, 0.0, -0.03)), mass=3.6)
GRIP = {  # palm contact (weapon local), wrist->knuckle direction, pinky->index line
    "r": (Vector((-0.048, -0.019, -0.085)), Vector((1.0, 0.0, -0.35)), Vector((0.35, 0.0, 1.0))),
    "l": (Vector((0.225, 0.012, -0.016)), Vector((0.0, -1.0, 0.15)), Vector((1.0, 0.0, 0.0))),
}
_H = {b.name: b.head_local.copy() for b in rig.data.bones}
LAT = {s: (_H[f"index_01_{s}"] - _H[f"pinky_01_{s}"]).normalized() for s, _ in SIDES}
CURL = {s: LAT[s] * sgn for s, sgn in SIDES}      # mirrored so both hands curl toward the palm
HAND = {}
for s, _ in SIDES:
    d0 = (_H[f"middle_01_{s}"] - _H[f"hand_{s}"]).normalized()
    v = _H[f"middle_02_{s}"] - _H[f"middle_01_{s}"]
    n = q(CURL[s], -40) @ v - v                      # fingers curl toward the palm
    n = (n - d0 * n.dot(d0)).normalized()
    palm = _H[f"hand_{s}"].lerp(_H[f"middle_01_{s}"], 0.55) + n * 0.022
    contact, dl, ll = GRIP[s]
    A = (basis(dl, ll) @ basis(d0, LAT[s]).transposed()).to_quaternion()
    HAND[s] = dict(A=A, palm=palm, normal=n, contact=contact)
# chirality check: the right palm must face the grip (+Y local), the left palm must face up (+Z local)
print(f"[anim] palm facing  r={(HAND['r']['A'] @ HAND['r']['normal']).y:+.2f} (want +)  "
      f"l={(HAND['l']['A'] @ HAND['l']['normal']).z:+.2f} (want +)")

# weapon_r socket: the rifle transform that matches the rest-pose right hand
R_REST = HAND["r"]["A"].inverted()
O_REST = HAND["r"]["palm"] - R_REST @ HAND["r"]["contact"]
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = rig.data.edit_bones.new("weapon_r")
eb.head = O_REST
eb.tail = O_REST + R_REST @ Vector((0.25, 0, 0))
eb.align_roll(R_REST @ Vector((0, 0, 1)))
eb.parent = rig.data.edit_bones["hand_r"]
eb.use_deform = False
bpy.ops.object.mode_set(mode="OBJECT")

BONES = rig.data.bones
PARENT = {b.name: (b.parent.name if b.parent else None) for b in BONES}
H0 = {b.name: b.head_local.copy() for b in BONES}
T0 = {b.name: b.tail_local.copy() for b in BONES}
R0 = {b.name: b.matrix_local.to_quaternion() for b in BONES}
ORDER = [b.name for b in BONES]          # parents come before children
Z0 = H0["foot_l"].z                      # ankle height with the boot flat on the ground
FOOT_TO_BALL = H0["ball_l"] - H0["foot_l"]
FOOT_TO_HEEL = Vector((0, 0.055, -Z0 + 0.004))
FOOT_MID = (FOOT_TO_BALL + FOOT_TO_HEEL) * 0.5
LEN = {b: (T0[b] - H0[b]).length for b in ORDER}

# segment masses (kg, ~80 kg raider + gear); CoM at 45 % along each bone
MASS = {"pelvis": 11, "spine_01": 7, "spine_02": 7, "spine_03": 17, "neck_01": 1.5, "head": 6.5,
        "clavicle_l": 1, "clavicle_r": 1, "upperarm_l": 2.3, "upperarm_r": 2.3, "lowerarm_l": 1.4,
        "lowerarm_r": 1.4, "hand_l": 0.6, "hand_r": 0.6, "thigh_l": 8.5, "thigh_r": 8.5,
        "calf_l": 3.8, "calf_r": 3.8, "foot_l": 2.0, "foot_r": 2.0}
PACK = (11.0, Vector((0, 0.20, 0.12)))  # backpack: mass, offset from spine_03 head in the chest frame


# ----------------------------------------------------------------------------- math helpers
def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def wrap(d):
    return (d + 0.5) % 1.0 - 0.5


def bump(phase, center, width):
    """Gaussian bump on a looping phase."""
    return math.exp(-(wrap(phase - center) / width) ** 2)


def keys(t, pts):
    """Smoothly interpolated value at time t through [(time, value), ...] (values: float or Vector)."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (ta, va), (tb, vb) in zip(pts, pts[1:]):
        if t <= tb:
            return lerp(va, vb, smooth((t - ta) / (tb - ta)))
    return pts[-1][1]


def yaw_of(v):
    """Heading of a world vector in degrees, 0 = facing -Y, + = turned to the raider's left (+X)."""
    return math.degrees(math.atan2(v.x, -v.y))


REACH = {"leg": 0.0, "arm": 0.0}


# ----------------------------------------------------------------------------- pose model
class Pose:
    """D[b]: rotation of bone b relative to its parent, about rest-space axes through its head.
    off: world translation of the pelvis. legs: IK records per side (re-solved after balancing and
    blending). spec/hold: the rifle hold and its solved world transform (O, R)."""

    def __init__(self):
        self.D = {b: Quaternion() for b in ORDER}
        self.off = Vector()
        self.legs = {}
        self.spec = None
        self.hold = None
        self.blade = 0.0
        self.kick = (0.0, 0.0)

    def rot(self, b, axis, deg):
        self.D[b] = q(axis, deg) @ self.D[b]

    def G(self, b):
        g = Quaternion()
        while b:
            g = self.D[b] @ g
            b = PARENT[b]
        return g

    def head(self, b):
        p = PARENT[b]
        if b == "pelvis":
            return H0[b] + self.off
        if p is None:
            return H0[b].copy()
        return self.head(p) + self.G(p) @ (H0[b] - H0[p])

    def fk(self):
        heads, gs = {}, {}
        for b in ORDER:
            p = PARENT[b]
            if p is None:
                heads[b], gs[b] = H0[b].copy(), self.D[b].copy()
                continue
            gs[b] = gs[p] @ self.D[b]
            heads[b] = H0[b] + self.off if b == "pelvis" else heads[p] + gs[p] @ (H0[b] - H0[p])
        return heads, gs

    def aim(self, b, world_dir):
        """Rotate b (minimal swing) so its head->tail points along world_dir."""
        gp = self.G(PARENT[b])
        cur = (gp @ self.D[b]) @ (T0[b] - H0[b]).normalized()
        self.D[b] = gp.inverted() @ cur.rotation_difference(world_dir.normalized()) @ gp @ self.D[b]

    def set_world(self, b, g_world):
        self.D[b] = self.G(PARENT[b]).inverted() @ g_world

    def two_bone(self, upper, lower, target, pole):
        h = self.head(upper)
        l1, l2 = LEN[upper], LEN[lower]
        v = target - h
        d = min(max(v.length, 0.05), 0.998 * (l1 + l2))
        u = v.normalized()
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        k = math.sqrt(max(l1 * l1 - a * a, 0.0))
        p = (pole - u * pole.dot(u)).normalized()
        knee = h + u * a + p * k
        self.aim(upper, knee - h)
        self.aim(lower, h + u * d - knee)
        return v.length - d                  # > 0: target out of reach (reported)

    def resolve_legs(self):
        for s, rec in self.legs.items():
            solve_leg(self, s, rec)

    def blend(self, other, t):
        out = Pose()
        for b in ORDER:
            a, c = self.D[b], other.D[b]
            if a.dot(c) < 0:
                c = -c
            out.D[b] = a.slerp(c, t)
        out.off = self.off.lerp(other.off, t)
        out.blade = lerp(self.blade, other.blade, t)
        if self.legs.keys() == other.legs.keys():
            for s in self.legs:
                a, c = self.legs[s], other.legs[s]
                rec = {k: lerp(a[k], c[k], t) for k in ("flat", "pitch", "lift", "splay", "knee_out", "roll", "w")}
                rec["sgn"] = a["sgn"]
                rec["toe"] = None if a["toe"] is None and c["toe"] is None else lerp(
                    toe_of(a), toe_of(c), t)
                out.legs[s] = rec
            out.resolve_legs()
        if self.hold and other.hold:
            (oa, ra), (oc, rc) = self.hold, other.hold
            if ra.dot(rc) < 0:
                rc = -rc
            out.hold = (oa.lerp(oc, t), ra.slerp(rc, t))
            out.spec = self.spec if t < 0.5 else other.spec
            grip_arms(out)
        return out


def toe_of(rec):
    if rec["toe"] is not None:
        return rec["toe"]
    return min(rec["pitch"], 0.0) if rec["lift"] < 0.01 else rec["pitch"] * 0.6


# ----------------------------------------------------------------------------- boots and legs
def foot_rot(sgn, splay, pitch, roll):
    """World rotation of a boot: toes turned out by splay, heel up by pitch, sole rolled onto its
    inner edge by roll (all degrees)."""
    return q(Z, sgn * splay) @ q(Y, sgn * roll) @ q(X, pitch)


def foot_place(flat_ankle, sgn, splay, pitch, roll):
    """Ankle position for a boot whose flat ankle position is flat_ankle: pitch > 0 rolls over the
    ball, pitch < 0 rocks on the heel, roll > 0 tips onto the inner edge (pivots stay on the ground)."""
    yaw = q(Z, sgn * splay)
    piv = yaw @ (FOOT_TO_BALL if pitch >= 0 else FOOT_TO_HEEL)
    a = flat_ankle + piv - yaw @ (q(X, pitch) @ (FOOT_TO_BALL if pitch >= 0 else FOOT_TO_HEEL))
    if roll:
        edge = yaw @ Vector((-sgn * 0.045, 0, -Z0 + 0.004))
        a = a + edge - q(yaw @ Y, sgn * roll) @ edge
    return a


def solve_leg(p, s, rec):
    sgn = rec["sgn"]
    ankle = foot_place(rec["flat"], sgn, rec["splay"], rec["pitch"], rec["roll"]) + Z * rec["lift"]
    toes = q(Z, sgn * rec["splay"]) @ FWD
    pole = (toes * 0.7 + p.G("pelvis") @ FWD * 0.3 + X * sgn * rec["knee_out"]).normalized()
    miss = p.two_bone(f"thigh_{s}", f"calf_{s}", ankle, pole)
    REACH["leg"] = max(REACH["leg"], miss)
    p.set_world(f"foot_{s}", foot_rot(sgn, rec["splay"], rec["pitch"], rec["roll"]))
    p.set_world(f"ball_{s}", foot_rot(sgn, rec["splay"], toe_of(rec), rec["roll"]))


def leg(p, s, sgn, flat_ankle, pitch=0.0, lift=0.0, toe=None, splay=8.0, knee_out=0.1, roll=0.0, w=1.0):
    """IK leg: flat_ankle is where the ankle sits when the boot is flat; toe = world pitch of the
    toes (None: flat on the ground while the heel is up, else follow the foot); w = share of weight."""
    rec = dict(sgn=sgn, flat=flat_ankle.copy(), pitch=pitch, lift=lift, toe=toe, splay=splay,
               knee_out=knee_out, roll=roll, w=w)
    p.legs[s] = rec
    solve_leg(p, s, rec)


# ----------------------------------------------------------------------------- balance
def com(p):
    heads, gs = p.fk()
    tot, acc = 0.0, Vector()
    for b, m in MASS.items():
        c = heads[b] + gs[b] @ ((T0[b] - H0[b]) * 0.45)
        acc += c * m
        tot += m
    acc += (heads["spine_03"] + gs["spine_03"] @ PACK[1]) * PACK[0]
    tot += PACK[0]
    if p.spec:
        o, r = weapon_xform(p, p.spec)
        acc += (o + r @ AR["com"]) * AR["mass"]
        tot += AR["mass"]
    return acc / tot


def support_point(rec):
    if rec["lift"] > 0.02:
        return None
    yaw = q(Z, rec["sgn"] * rec["splay"])
    off = FOOT_TO_BALL if rec["pitch"] > 6 else FOOT_TO_HEEL if rec["pitch"] < -6 else FOOT_MID
    return rec["flat"] + yaw @ off


def balance(p, gx=1.0, gy=1.0, support=None, iters=4):
    """Slide the pelvis so the centre of mass sits over the weighted support, re-solving the legs."""
    for _ in range(iters):
        pts = support(p) if callable(support) else support
        if pts is None:
            pts = [(support_point(r), r.get("w", 1.0)) for r in p.legs.values()]
        pts = [(pt, w) for pt, w in pts if pt is not None and w > 0]
        if not pts:
            return
        tw = sum(w for _, w in pts)
        tgt = sum((pt * w for pt, w in pts), Vector()) / tw
        c = com(p)
        p.off.x += (tgt.x - c.x) * gx
        p.off.y += (tgt.y - c.y) * gy
        p.resolve_legs()


# ----------------------------------------------------------------------------- body helpers
def spine(p, pitch=0.0, yaw=0.0, roll=0.0, w=(0.3, 0.3, 0.4)):
    for b, k in zip(("spine_01", "spine_02", "spine_03"), w):
        p.rot(b, X, pitch * k)
        p.rot(b, Z, yaw * k)
        p.rot(b, Y, roll * k)


def neck(p, pitch=0.0, yaw=0.0, roll=0.0):
    for b, k in (("neck_01", 0.45), ("head", 0.55)):
        p.rot(b, X, pitch * k)
        p.rot(b, Z, yaw * k)
        p.rot(b, Y, roll * k)


def shoulders(p, fwd=6.0, up=0.0, up_l=0.0, up_r=0.0, fwd_l=0.0, fwd_r=0.0):
    """fwd: shoulders rolled forward (hunch); up: shrug."""
    for s, sgn in SIDES:
        p.rot(f"clavicle_{s}", Z, -(fwd + (fwd_l if s == "l" else fwd_r)) * sgn)
        p.rot(f"clavicle_{s}", Y, -(up + (up_l if s == "l" else up_r)) * sgn)


def arm(p, s, sgn, swing=0.0, abduct=18.0, elbow=20.0, inward=0.0, wrist=0.0):
    """Arm FK in the chest frame: swing + = forward, abduct + = away from the body,
    elbow + = forearm folds forward/up, inward + = forearm turns toward the midline."""
    gc = p.G(f"clavicle_{s}")
    v = q(Y, -abduct * sgn) @ (q(X, -swing) @ Vector((0, 0, -1)))
    n = v.cross(FWD)
    f = q(n.normalized(), elbow) @ v if n.length > 1e-4 else v
    f = q(Z, -inward * sgn) @ f
    p.aim(f"upperarm_{s}", gc @ v)
    p.aim(f"lowerarm_{s}", gc @ f)
    p.D[f"hand_{s}"] = q(CURL[s], wrist)


def hands(p, curl=35.0, thumb=15.0, curl_l=None, curl_r=None, index_r=None):
    """Glove curl: 0 open, ~35 relaxed, ~85 fist. index_r: trigger finger."""
    for s, sgn in SIDES:
        c = curl_l if (s == "l" and curl_l is not None) else curl_r if (s == "r" and curl_r is not None) else curl
        for i, fname in enumerate(FINGERS):
            cc = index_r if (s == "r" and fname == "index" and index_r is not None) else c
            spread = (1.0 + 0.12 * i)         # pinky curls a touch more
            for j, k in ((1, 0.7), (2, 1.0), (3, 0.8)):
                p.D[f"{fname}_0{j}_{s}"] = q(CURL[s], -cc * k * spread)
        for j in (1, 2, 3):
            p.D[f"thumb_0{j}_{s}"] = q(Z, thumb * sgn * 0.5) @ q(CURL[s], -thumb * 0.5)


# ----------------------------------------------------------------------------- rifle holds
HOLDS = {
    # anchor point of the rifle placed at a chest-frame rest-space point; pitch + = muzzle down,
    # yaw + = muzzle to the raider's left; follow = how much the rifle turns with the chest
    "aim": dict(anchor="butt", at=Vector((-0.10, -0.12, 1.47)), yaw=0.0, pitch=0.0, roll=0.0, follow=1.0),
    "ready": dict(anchor="butt", at=Vector((-0.11, -0.13, 1.38)), yaw=12.0, pitch=24.0, roll=0.0, follow=1.0),
    "carry": dict(anchor="grip", at=Vector((-0.13, -0.27, 1.06)), yaw=58.0, pitch=-36.0, roll=18.0, follow=1.0),
}


def weapon_xform(p, spec):
    heads, gs = p.fk()
    gc = gs["spine_03"]
    anchor = heads["spine_03"] + gc @ (spec["at"] - H0["spine_03"])
    cy = yaw_of(gc @ FWD)
    back, up = p.kick
    r = q(Z, spec["yaw"] + spec["follow"] * (cy - p.blade)) @ q(X, spec["pitch"]) @ q(FWD, spec["roll"]) @ W0
    r = r @ q(Y, -up)                                     # muzzle climb about the anchor
    o = anchor - r @ AR[spec["anchor"]] - r @ Vector((back, 0, 0))
    return o, r


def grip_arms(p, left=None, curl_l=58):
    """Lock both hands onto the rifle at p.hold. left: optional (palm point, hand rotation) for the
    support hand when it leaves the handguard (reloads, throws)."""
    o, r = p.hold
    gc = p.G("spine_03")
    poles = {"r": gc @ Vector((-1.0, 0.3, -1.1)), "l": gc @ Vector((0.5, 0.1, -1.0))}
    for s, _ in SIDES:
        h = HAND[s]
        gh = r @ h["A"]
        palm_w = o + r @ h["contact"]
        if s == "l" and left is not None:
            palm_w, gh = left
        wrist = palm_w - gh @ (h["palm"] - H0[f"hand_{s}"])
        for _ in range(3):               # out of reach: the shoulder blade protracts toward the rifle
            reach = (wrist - p.head(f"upperarm_{s}")).length - 0.995 * (LEN[f"upperarm_{s}"] + LEN[f"lowerarm_{s}"])
            if reach <= 0.002:
                break
            cb = f"clavicle_{s}"
            ch = p.head(cb)
            cur = (p.G(cb) @ (T0[cb] - H0[cb])).normalized()
            full = cur.rotation_difference((wrist - ch).normalized())
            ang = min(full.angle, reach / LEN[cb], math.radians(32))
            if full.angle > 1e-4:
                p.set_world(cb, Quaternion(full.axis, ang) @ p.G(cb))
        miss = p.two_bone(f"upperarm_{s}", f"lowerarm_{s}", wrist, poles[s])
        REACH["arm"] = max(REACH["arm"], miss)
        p.set_world(f"hand_{s}", gh)
    hands(p, 0, thumb=30, curl_l=curl_l, curl_r=70, index_r=22)


def armed(p, spec):
    """Call after the body and legs are posed and balanced (balance counts the rifle via p.spec)."""
    p.spec = spec
    p.hold = weapon_xform(p, spec)
    grip_arms(p)


# ----------------------------------------------------------------------------- base stances
def stance(p, drop=0.04, lean=8.0, head_fwd=5.0, hunch=8.0, width=0.17, w_l=0.5):
    """Heavy idle stance: low hips, chest over the toes, head pushed forward, arms off the body."""
    p.off = Vector((0, 0.01, -drop))
    p.rot("pelvis", X, lean * 0.25)
    spine(p, pitch=lean)
    neck(p, pitch=-lean * 0.85 + head_fwd)
    p.rot("neck_01", X, head_fwd)
    shoulders(p, fwd=hunch, up=-2)
    leg(p, "l", 1, Vector((width, -0.03, Z0)), splay=11, w=w_l)
    leg(p, "r", -1, Vector((-width, 0.03, Z0)), splay=11, w=1 - w_l)
    hands(p, 35)


def rifle_stance(p, drop=0.07, lean=10.0, w_l=0.56, crouch=0.0):
    """Bladed shooting stance: support boot forward and straight, strong boot back and turned out,
    hips and chest turned toward the strong side, head turned back to the target."""
    blade = -22.0
    p.blade = blade
    p.off = Vector((0, 0.01, -lerp(drop, 0.33, crouch)))
    p.rot("pelvis", Z, blade * 0.6)
    p.rot("pelvis", X, lerp(lean * 0.3, 9, crouch))
    spine(p, pitch=lerp(lean, 22, crouch), yaw=blade * 0.4)
    neck(p, yaw=-blade, pitch=lerp(-lean * 0.8, -18, crouch))
    shoulders(p, fwd=8, fwd_l=6)
    if crouch:
        leg(p, "l", 1, Vector((0.17, -0.18, Z0)), splay=12, w=0.55)
        leg(p, "r", -1, Vector((-0.17, 0.22, Z0)), pitch=34, splay=30, roll=4, w=0.45)
    else:
        leg(p, "l", 1, Vector((0.14, -0.13, Z0)), splay=8, w=w_l)
        leg(p, "r", -1, Vector((-0.17, 0.13, Z0)), splay=32, roll=3, w=1 - w_l)


# ----------------------------------------------------------------------------- gait generator
GAITS = {
    # speed m/s, cycle s, stance fraction, lift, heel strike / toe-off deg, width, drop, bob, dip,
    # pelvis yaw/roll, lean, chest counter-yaw, arm swing/bias/abduct/elbow, hand curl
    "Walk": dict(speed=1.25, cycle=1.1, s=0.60, lift=0.11, heel=14, toe=26, width=0.15, drop=0.075,
                 bob=0.018, dip=0.022, yaw=7, roll=5, lean=9, chest=8, swing=20, bias=0,
                 abduct=17, elbow=24, elbow_swing=12, curl=38, head=4, hunch=9),
    "Jog": dict(speed=2.9, cycle=0.7333, s=0.36, lift=0.20, heel=8, toe=34, width=0.13, drop=0.095,
                bob=0.035, dip=0.03, yaw=9, roll=6, lean=15, chest=11, swing=34, bias=6,
                abduct=19, elbow=66, elbow_swing=10, curl=55, head=3, hunch=10),
    "Sprint": dict(speed=5.0, cycle=0.6, s=0.27, lift=0.30, heel=2, toe=44, width=0.11, drop=0.11,
                   bob=0.045, dip=0.035, yaw=11, roll=5, lean=27, chest=13, swing=52, bias=8,
                   abduct=12, elbow=96, elbow_swing=10, curl=80, head=0, hunch=12),
    "Crouch_Walk": dict(speed=1.0, cycle=1.2, s=0.66, lift=0.09, heel=10, toe=22, width=0.19, drop=0.33,
                        bob=0.012, dip=0.015, yaw=6, roll=4, lean=24, chest=6, swing=10, bias=10,
                        abduct=20, elbow=55, elbow_swing=8, curl=45, head=0, hunch=12),
    "Walk_Back": dict(speed=1.0, cycle=1.15, s=0.62, lift=0.09, heel=0, toe=14, width=0.16, drop=0.085,
                      bob=0.014, dip=0.02, yaw=5, roll=4, lean=6, chest=5, swing=10, bias=4,
                      abduct=18, elbow=30, elbow_swing=6, curl=38, head=4, hunch=9, dir=(0, 1, 0)),
    "Strafe_L": dict(speed=0.75, cycle=0.96, s=0.56, lift=0.08, heel=0, toe=10, width=0.21, drop=0.11,
                     bob=0.012, dip=0.02, yaw=2, roll=5, lean=9, chest=2, swing=4, bias=4,
                     abduct=20, elbow=30, elbow_swing=4, curl=38, head=4, hunch=9, dir=(1, 0, 0)),
    "Strafe_R": dict(speed=0.75, cycle=0.96, s=0.56, lift=0.08, heel=0, toe=10, width=0.21, drop=0.11,
                     bob=0.012, dip=0.02, yaw=2, roll=5, lean=9, chest=2, swing=4, bias=4,
                     abduct=20, elbow=30, elbow_swing=4, curl=38, head=4, hunch=9, dir=(-1, 0, 0)),
    "Aim_Walk": dict(speed=0.95, cycle=1.2, s=0.64, lift=0.07, heel=8, toe=16, width=0.16, drop=0.095,
                     bob=0.008, dip=0.012, yaw=4, roll=3, lean=10, chest=3, swing=0, bias=0,
                     abduct=18, elbow=30, elbow_swing=0, curl=40, head=0, hunch=9),
}
RIFLE_GAITS = {"Rifle_Walk": ("Walk", "ready"), "Rifle_Jog": ("Jog", "ready"), "Rifle_Sprint": ("Sprint", "carry"),
               "Rifle_Crouch_Walk": ("Crouch_Walk", "ready"), "Rifle_Walk_Back": ("Walk_Back", "ready"),
               "Rifle_Strafe_L": ("Strafe_L", "aim"), "Rifle_Strafe_R": ("Strafe_R", "aim"),
               "Rifle_Aim_Walk": ("Aim_Walk", "aim")}
GAIT_Y = {}


def gait_pose(phi, g, hold, yshift):
    p = Pose()
    d = Vector(g.get("dir", (0, -1, 0)))
    lateral = abs(d.x) > 0.5
    back = d.y > 0.5
    s = g["s"]
    travel = g["speed"] * g["cycle"] * s
    c2 = math.cos(2 * math.pi * phi)
    s2 = math.sin(2 * math.pi * phi)
    stab = 0.45 if hold else 1.0        # arms locked on the rifle damp the upper-body twist
    blade = -10.0 if hold == "ready" else (-14.0 if lateral else -18.0) if hold == "aim" else 0.0
    p.blade = blade
    # pelvis: low, bobs twice per cycle, slams down just after each contact
    flight = s < 0.5
    peak = s / 2 + (0.25 if flight else 0.0)
    z = -g["drop"] + g["bob"] * math.cos(4 * math.pi * (phi - peak))
    z -= g["dip"] * (bump(phi, 0.07, 0.07) + bump(phi, 0.57, 0.07))
    p.off = Vector((0, 0.012 + yshift, z))
    p.rot("pelvis", X, g["lean"] * 0.3 + 1.5 * math.cos(4 * math.pi * (phi - 0.1)))
    p.rot("pelvis", Z, blade * 0.5 - g["yaw"] * c2 * (-1 if back else 1))
    p.rot("pelvis", Y, -g["roll"] * s2)
    lag = 0.06
    cl = math.cos(2 * math.pi * (phi - lag))
    chest_yaw = (g["chest"] * cl * (-1 if back else 1) + g["yaw"] * c2 * 0.6) * stab
    spine(p, pitch=g["lean"] + 2.0 * math.cos(4 * math.pi * (phi - peak - 0.08)),
          yaw=chest_yaw + blade * 0.5, roll=g["roll"] * 0.6 * math.sin(2 * math.pi * (phi - lag)))
    neck(p, pitch=-g["lean"] * 0.8 + g["head"] - 1.5 * math.cos(4 * math.pi * (phi - peak - 0.12)),
         yaw=-(chest_yaw * 0.5) - blade, roll=-g["roll"] * 0.5 * s2)
    shoulders(p, fwd=g["hunch"], up=-1 + 1.5 * math.cos(4 * math.pi * (phi - peak - 0.1)))
    # legs; w = how loaded each boot is (smooth hand-over through double support)
    w_l = 0.5 + 0.5 * math.cos(2 * math.pi * (phi - s / 2))
    for side, sgn in SIDES:
        t = (phi + (0.0 if side == "l" else 0.5)) % 1.0
        base = Vector((sgn * g["width"], 0.02 * sgn if lateral else 0.0, Z0))
        roll = 0.0
        if t < s:
            k = t / s
            pos = base + d * (travel * (0.5 - k))
            pitch = -g["heel"] * (1 - smooth(k / 0.16)) + g["toe"] * smooth((k - 0.62) / 0.38)
            lift = 0.0
            if lateral and sgn * d.x < 0:   # the boot that pushes sideways rolls onto its inner edge
                roll = 12 * smooth((k - 0.45) / 0.45)
        else:
            u = (t - s) / (1 - s)
            e = 0.5 - 0.5 * math.cos(math.pi * u)
            pos = base + d * (travel * (e - 0.5))
            if lateral:                 # trailing boot swings wide so the boots never clip
                pos.x += sgn * 0.035 * math.sin(math.pi * u)
            lift = g["lift"] * math.sin(math.pi * min(u * 1.15, 1.0)) ** 1.3
            pitch = lerp(g["toe"] * 1.1, -g["heel"], smooth((u - 0.1) / 0.75))
        leg(p, side, sgn, pos, pitch, lift, splay=(5 if lateral else 9) + (8 if side == "r" and hold else 0),
            roll=roll, w=w_l if side == "l" else 1 - w_l)
    if hold:
        p.spec = HOLDS[hold]
    # weight rides over the loaded boot (lateral only: fore-aft is handled by the cycle mean below)
    lat_support = [(Vector((r["flat"].x, 0, 0)), r["w"]) for r in p.legs.values()]
    balance(p, gx=0.45, gy=0.0, support=lat_support)
    if hold:
        armed(p, HOLDS[hold])
        return p
    for side, sgn in SIDES:
        sw = g["swing"] * math.cos(2 * math.pi * (phi - 0.09)) * (-1 if side == "l" else 1)
        if back:
            sw = -sw
        sw += g["bias"]
        arm(p, side, sgn, swing=sw, abduct=g["abduct"] + 2 * math.sin(2 * math.pi * phi) * sgn,
            elbow=g["elbow"] + g["elbow_swing"] * max(sw - g["bias"], 0) / max(g["swing"], 1),
            inward=8 + (4 if g["elbow"] > 60 else 0), wrist=-6)
    hands(p, g["curl"])
    return p


def gait(phi, name, g, hold=None):
    """Gait pose with the fore-aft CoM centred over the boots on average across the cycle."""
    if name not in GAIT_Y:
        errs = []
        for i in range(12):
            p = gait_pose(i / 12, g, hold, 0.0)
            pts = [pt for pt in (support_point(r) for r in p.legs.values()) if pt is not None]
            if pts:                      # skip flight frames
                errs.append((sum(pts, Vector()) / len(pts)).y - com(p).y)
        GAIT_Y[name] = 0.85 * sum(errs) / len(errs)
    return gait_pose(phi, g, hold, GAIT_Y[name])


# ----------------------------------------------------------------------------- clips
CLIPS = {}


def clip(name, frames, loop=True, speed=0.0, armed_=False):
    def deco(fn):
        CLIPS[name] = dict(fn=fn, frames=frames, loop=loop, speed=speed, armed=armed_)
        return fn
    return deco


for _name, _g in GAITS.items():
    if _name == "Aim_Walk":
        continue
    CLIPS[_name] = dict(fn=(lambda nm, g: lambda f, n: gait(f / n, nm, g))(_name, _g),
                        frames=round(_g["cycle"] * FPS), loop=True, speed=_g["speed"], armed=False)
for _name, (_gn, _hold) in RIFLE_GAITS.items():
    _g = GAITS[_gn]
    CLIPS[_name] = dict(fn=(lambda nm, g, h: lambda f, n: gait(f / n, nm, g, h))(_name, _g, _hold),
                        frames=round(_g["cycle"] * FPS), loop=True, speed=_g["speed"], armed=True)


@clip("Idle", 120)
def idle(f, n):
    t = f / n
    p = Pose()
    br = math.sin(2 * math.pi * 2 * t)                      # two heavy breaths per loop
    sh = math.sin(2 * math.pi * t)                           # one slow weight shift
    stance(p, drop=0.04 + 0.004 * br, lean=8 - 1.2 * br, w_l=0.5 + 0.22 * sh)
    p.rot("pelvis", Y, -2.5 * sh)
    spine(p, roll=2.0 * sh, yaw=1.5 * math.sin(2 * math.pi * (t - 0.1)))
    neck(p, pitch=1.0 * br, yaw=4 * math.sin(2 * math.pi * (t + 0.2)), roll=-1.5 * sh)
    shoulders(p, fwd=0, up=1.8 * br)
    balance(p)
    for s, sgn in SIDES:
        sway = 2.0 * math.sin(2 * math.pi * (t - 0.15)) * sgn
        arm(p, s, sgn, swing=3 + sway, abduct=17 - 1.5 * br, elbow=20 + 3 * br, inward=6, wrist=-8)
    return p


@clip("Idle_Scan", 150)
def idle_scan(f, n):
    """Checks the left flank, then the right, chest following the head with a delay."""
    t = f / n
    p = Pose()
    br = math.sin(2 * math.pi * 3 * t)
    look = keys(t, [(0.0, 0.0), (0.12, 0.0), (0.3, 55.0), (0.45, 50.0), (0.62, -58.0), (0.78, -52.0), (0.95, 0.0)])
    body = keys(t, [(0.0, 0.0), (0.18, 0.0), (0.36, 22.0), (0.5, 20.0), (0.68, -24.0), (0.84, -20.0), (1.0, 0.0)])
    tilt = keys(t, [(0.0, 0.0), (0.3, -6.0), (0.45, 4.0), (0.62, -5.0), (0.8, 3.0), (1.0, 0.0)])
    stance(p, drop=0.045, lean=9 - br, w_l=0.5 + 0.12 * body / 22)
    p.rot("pelvis", Z, body * 0.25)
    spine(p, yaw=body * 0.75, pitch=0.6 * br)
    neck(p, yaw=look - body, pitch=tilt)
    shoulders(p, fwd=0, up=1.2 * br)
    balance(p)
    for s, sgn in SIDES:
        arm(p, s, sgn, swing=4 + 4 * (body / 22) * sgn, abduct=17, elbow=22, inward=6, wrist=-8)
    return p


@clip("Crouch_Idle", 90)
def crouch_idle(f, n):
    t = f / n
    p = Pose()
    br = math.sin(2 * math.pi * 2 * t)
    p.off = Vector((0, 0.03, -0.35 - 0.006 * br))
    p.rot("pelvis", X, 8)
    spine(p, pitch=24 - 2 * br)
    neck(p, pitch=-20 + br)
    shoulders(p, fwd=12, up=1.5 * br)
    sh = math.sin(2 * math.pi * t)
    leg(p, "l", 1, Vector((0.2, -0.16, Z0)), splay=12, w=0.6 + 0.08 * sh)
    leg(p, "r", -1, Vector((-0.19, 0.2, Z0)), pitch=32, splay=16, roll=3, w=0.4 - 0.08 * sh)
    balance(p)
    for s, sgn in SIDES:
        arm(p, s, sgn, swing=12, abduct=16, elbow=62 + 2 * br, inward=22, wrist=-10)
    hands(p, 45)
    return p


def stand_pose():
    p = Pose()
    stance(p, drop=0.045, lean=9)
    balance(p)
    for s, sgn in SIDES:
        arm(p, s, sgn, swing=4, abduct=17, elbow=22, inward=6, wrist=-8)
    return p


def crouch_land(drop, lean, arms_fwd, curl=45):
    p = Pose()
    p.off = Vector((0, 0.04, -drop))
    p.rot("pelvis", X, lean * 0.3)
    spine(p, pitch=lean)
    neck(p, pitch=-lean * 0.8)
    shoulders(p, fwd=12, up=-3)
    for s, sgn in SIDES:
        leg(p, s, sgn, Vector((sgn * 0.19, -0.03 * sgn, Z0)), splay=13)
    balance(p)
    for s, sgn in SIDES:
        arm(p, s, sgn, swing=arms_fwd, abduct=26, elbow=40, inward=10, wrist=-12)
    hands(p, curl)
    return p


def air(t_loop=0.0, tuck=1.0):
    p = Pose()
    w = math.sin(2 * math.pi * t_loop)
    p.off = Vector((0, 0.02, 0.32 + 0.01 * w))
    p.rot("pelvis", X, 6)
    spine(p, pitch=10 + 2 * w, roll=2 * w)
    neck(p, pitch=-8)
    shoulders(p, fwd=6, up=4 + 2 * w)
    leg(p, "l", 1, Vector((0.16, -0.12, Z0 + 0.30 + 0.12 * tuck)), pitch=18, lift=0.0, toe=10, splay=8)
    leg(p, "r", -1, Vector((-0.15, 0.12, Z0 + 0.26 + 0.08 * tuck)), pitch=30, lift=0.0, toe=20, splay=8)
    for s, sgn in SIDES:
        arm(p, s, sgn, swing=18 + 6 * w * sgn, abduct=38 + 4 * w * sgn, elbow=38, inward=0, wrist=-10)
    hands(p, 30)
    return p


@clip("Jump_Start", 14, loop=False)
def jump_start(f, n):
    """Wind-up, then a heavy two-leg push: the pack makes the launch late and low."""
    stand = stand_pose()
    load = crouch_land(0.17, 20, -28)
    if f <= 6:
        return stand.blend(load, smooth(f / 6))
    if f <= 10:                          # explode: legs extend over the balls of the feet, arms drive up
        u = (f - 6) / 4
        p = Pose()
        p.off = Vector((0, 0.02, lerp(-0.17, 0.08, smooth(u))))
        p.rot("pelvis", X, lerp(6, 2, u))
        spine(p, pitch=lerp(20, 6, u))
        neck(p, pitch=lerp(-16, -6, u))
        shoulders(p, fwd=8, up=lerp(-3, 6, u))
        for s, sgn in SIDES:
            leg(p, s, sgn, Vector((sgn * 0.19, -0.03 * sgn, Z0)), pitch=lerp(0, 40, smooth(u)), splay=13)
        balance(p, gx=1.0, gy=0.6)
        for s, sgn in SIDES:
            arm(p, s, sgn, swing=lerp(-28, 40, smooth(u)), abduct=lerp(26, 30, u), elbow=lerp(40, 30, u), wrist=-10)
        hands(p, 40)
        return p
    last = jump_start(10, n)
    return last.blend(air(0.0), smooth((f - 10) / (n - 10)))


@clip("Fall_Loop", 30)
def fall_loop(f, n):
    return air(f / n)


@clip("Jump_Land", 28, loop=False)
def jump_land(f, n):
    """Feet hit, the body keeps going: deep compression, arms thrown down/forward, slow recovery."""
    reach = Pose()
    reach.off = Vector((0, 0.02, 0.0))
    reach.rot("pelvis", X, 5)
    spine(reach, pitch=10)
    neck(reach, pitch=-8)
    shoulders(reach, fwd=6, up=5)
    for s, sgn in SIDES:
        leg(reach, s, sgn, Vector((sgn * 0.18, -0.04 * sgn, Z0)), pitch=12, splay=10)
        arm(reach, s, sgn, swing=22, abduct=40, elbow=36, wrist=-10)
    hands(reach, 30)
    low = crouch_land(0.26, 30, 34, curl=55)
    settle = crouch_land(0.12, 16, 12)
    stand = stand_pose()
    if f <= 2:
        return air(0.0).blend(reach, f / 2)
    if f <= 6:
        u = (f - 2) / 4
        return reach.blend(low, 1 - (1 - u) ** 2.2)          # fast hit
    if f <= 15:
        return low.blend(settle, smooth((f - 6) / 9))
    return settle.blend(stand, smooth((f - 15) / (n - 15)))


def curled():
    p = Pose()
    p.rot("pelvis", X, 40)
    spine(p, pitch=75)
    neck(p, pitch=35)
    shoulders(p, fwd=18, up=4)
    for s, sgn in SIDES:
        p.rot(f"thigh_{s}", X, -115)
        p.rot(f"thigh_{s}", Y, 8 * sgn)
        p.rot(f"calf_{s}", X, 135)
        p.rot(f"foot_{s}", X, 35)
        arm(p, s, sgn, swing=55, abduct=24, elbow=95, inward=35, wrist=-15)
    hands(p, 75)
    return p


CURL_HEADS = ("pelvis", "spine_03", "head", "calf_l", "calf_r", "foot_l", "foot_r", "hand_l", "hand_r")


@clip("Dodge_Roll", 30, loop=False)
def dodge_roll(f, n):
    """Combat roll over the shoulder and pack: drop, tuck, one full turn, come up low, stand."""
    stand = stand_pose()
    dive = Pose()
    dive.off = Vector((0, -0.06, -0.24))
    dive.rot("pelvis", X, 22)
    spine(dive, pitch=50)
    neck(dive, pitch=-10)
    shoulders(dive, fwd=16)
    leg(dive, "l", 1, Vector((0.17, -0.18, Z0)), splay=12)
    leg(dive, "r", -1, Vector((-0.17, 0.28, Z0)), pitch=40, splay=12)
    for s, sgn in SIDES:
        arm(dive, s, sgn, swing=60, abduct=20, elbow=35, inward=12, wrist=-20)
    hands(dive, 40)
    low = crouch_land(0.30, 30, 26, curl=50)
    # the curled ball turns about its own centre, one radius (pack included) above the floor
    c = curled()
    pts = [c.head(b) for b in CURL_HEADS]
    c0 = sum(pts, Vector()) / len(pts)
    radius = 0.53
    theta = keys(f, [(4, 0.0), (21, 360.0)]) if f > 4 else 0.0
    rolled = Pose()
    rolled.D = dict(c.D)
    rolled.D["pelvis"] = q(X, theta) @ c.D["pelvis"]
    ph = q(X, theta) @ (H0["pelvis"] - c0)
    rolled.off = Vector((0, 0, radius)) + ph - H0["pelvis"]
    if f <= 5:
        return stand.blend(dive, smooth(f / 5))
    if f <= 9:
        return dive.blend(rolled, smooth((f - 5) / 4))
    if f <= 18:
        return rolled
    if f <= 23:
        return rolled.blend(low, smooth((f - 18) / 5))
    return low.blend(stand, smooth((f - 23) / (n - 23)))


def kneel(t_rummage=0.0, depth=1.0):
    """Right knee down, left boot planted, right hand digging into a container in front."""
    p = Pose()
    w = math.sin(2 * math.pi * t_rummage)
    w2 = math.sin(2 * math.pi * 2 * t_rummage + 1.0)
    p.off = Vector((0.02, 0.06, lerp(-0.045, -0.44, depth)))
    p.rot("pelvis", X, 10 * depth)
    p.rot("pelvis", Z, -8 * depth)
    spine(p, pitch=lerp(9, 30 + 4 * w, depth), yaw=lerp(0, 8 + 3 * w2, depth))
    neck(p, pitch=lerp(-7, -4, depth), yaw=-6 * depth)
    shoulders(p, fwd=lerp(8, 14, depth), up_r=4 * w * depth)
    leg(p, "l", 1, Vector((0.17, lerp(-0.03, -0.30, depth), Z0)), splay=10)
    leg(p, "r", -1, Vector((-0.15, lerp(0.03, 0.40, depth), lerp(Z0, 0.17, depth))),
        pitch=lerp(0, 58, depth), toe=0, splay=lerp(10, 6, depth))

    def support(pp):                     # kneeling: left boot, right knee and right toes share the load
        if depth < 0.5:
            return None
        rl = pp.legs["l"]
        knee = pp.head("calf_r")
        toes = pp.legs["r"]["flat"] + FOOT_TO_BALL
        return [(support_point(rl), 0.45), (Vector((knee.x, knee.y, 0)), 0.35), (toes, 0.2)]
    balance(p, support=support)
    knee_l = p.head("calf_l")
    arm(p, "l", 1, swing=4, abduct=17, elbow=22, inward=6, wrist=-8)
    if depth > 0.01:                     # left hand braces on the left knee
        rest_hand = p.head("hand_l")
        target = rest_hand.lerp(knee_l + Vector((0.0, -0.02, 0.06)), depth)
        p.two_bone("upperarm_l", "lowerarm_l", target, p.G("spine_03") @ Vector((0.6, 0.6, -0.2)))
        p.D["hand_l"] = q(CURL["l"], 25 * depth)
    arm(p, "r", -1, swing=4, abduct=17, elbow=22, inward=6, wrist=-8)
    if depth > 0.01:                     # right hand rummages in a container in front of the knee
        rest_hand = p.head("hand_r")
        dig = Vector((-0.08 + 0.07 * w2, -0.62 + 0.05 * w, 0.46 + 0.06 * math.sin(2 * math.pi * 3 * t_rummage)))
        p.two_bone("upperarm_r", "lowerarm_r", rest_hand.lerp(dig, depth), p.G("spine_03") @ Vector((-0.7, 0.5, -0.2)))
        p.D["hand_r"] = q(CURL["r"], -20 * depth + 10 * w2)
    hands(p, 35, curl_l=lerp(35, 55, depth), curl_r=lerp(35, 50 + 25 * w, depth))
    return p


@clip("Loot", 105, loop=False)
def loot(f, n):
    """Kneel at a container, dig through it, stand back up."""
    if f <= 18:
        return kneel(0.0, smooth(f / 18))
    if f <= 84:
        return kneel((f - 18) / 33.0, 1.0)
    return kneel(0.0, 1.0 - smooth((f - 84) / (n - 84)))


# ----------------------------------------------------------------------------- rifle clips
def rifle_pose(hold, t=0.0, br=0.0, sh=0.0, crouch=0.0, kick=0.0):
    p = Pose()
    rifle_stance(p, w_l=0.56 + 0.06 * sh, crouch=crouch)
    p.off.z -= 0.004 * br + 0.012 * kick
    spine(p, pitch=-1.0 * br - 5.0 * kick, roll=1.2 * sh)
    shoulders(p, fwd=0, up=1.4 * br, fwd_r=-6 * kick)
    if hold == "aim":                    # cheek on the stock: head down and over toward the sights
        neck(p, pitch=10 - 3 * kick, roll=-9, yaw=-4)
    else:
        neck(p, pitch=2, yaw=6 * math.sin(2 * math.pi * (t + 0.15)))
    p.spec = HOLDS[hold]
    p.kick = (0.045 * kick, 8.0 * kick)
    balance(p)
    spec = dict(HOLDS[hold])
    spec["yaw"] += 0.5 * math.sin(2 * math.pi * t) * (1 - crouch * 0.5)        # breathing sway
    spec["pitch"] += 0.4 * math.sin(2 * math.pi * 2 * t + 0.6) + 0.6 * br
    armed(p, spec)
    return p


@clip("Rifle_Idle", 120, armed_=True)
def rifle_idle(f, n):
    t = f / n
    return rifle_pose("ready", t, br=math.sin(2 * math.pi * 2 * t), sh=math.sin(2 * math.pi * t))


@clip("Rifle_Aim", 90, armed_=True)
def rifle_aim(f, n):
    t = f / n
    return rifle_pose("aim", t, br=math.sin(2 * math.pi * 2 * t) * 0.6, sh=math.sin(2 * math.pi * t) * 0.5)


@clip("Rifle_Fire", 24, loop=False, armed_=True)
def rifle_fire(f, n):
    """One heavy shot from the aim: the stock slams the shoulder back, the muzzle climbs, the chest
    and hips absorb it, then the raider settles back onto the sights."""
    k = f / 1.0 if f <= 1 else math.exp(-(f - 1) / 3.5) * (1 + 0.15 * math.sin((f - 1) * 0.9))
    return rifle_pose("aim", 0.0, kick=max(k, 0.0))


@clip("Rifle_Crouch_Idle", 90, armed_=True)
def rifle_crouch_idle(f, n):
    t = f / n
    return rifle_pose("ready", t, br=math.sin(2 * math.pi * 2 * t), sh=math.sin(2 * math.pi * t) * 0.5, crouch=1.0)


def left_grip(p):
    """Palm point and hand rotation of the support hand on the handguard."""
    o, r = p.hold
    return o + r @ HAND["l"]["contact"], r @ HAND["l"]["A"]


@clip("Rifle_Reload", 66, loop=False, armed_=True)
def rifle_reload(f, n):
    """Magazine swap from the low ready: rifle canted toward the support side, mag stripped and
    stowed on the chest rig, fresh mag seated with a slap, hand back on the handguard."""
    tilt = keys(f, [(0, 0.0), (8, 1.0), (56, 1.0), (64, 0.0)])
    p = Pose()
    rifle_stance(p, w_l=0.56)
    neck(p, pitch=lerp(2, 16, tilt), yaw=lerp(0, 10, tilt))
    shoulders(p, fwd=0)
    spec = dict(HOLDS["ready"])
    spec["roll"] = 32 * tilt                              # cant the mag well toward the left hand
    spec["pitch"] = lerp(spec["pitch"], 6, tilt)
    spec["yaw"] = lerp(spec["yaw"], 26, tilt)
    p.spec = spec
    balance(p)
    p.hold = weapon_xform(p, spec)
    o, r = p.hold
    seat = (o + r @ Vector((0.12, 0.0, -0.16)), r @ q(X, -90) @ HAND["l"]["A"])
    gc = p.G("spine_03")
    pouch = (p.head("spine_03") + gc @ Vector((0.13, -0.17, -0.12)), gc @ q(X, 80) @ HAND["l"]["A"])
    slap = (seat[0] + r @ Vector((0, 0, -0.05)), seat[1])
    guard = left_grip(p)
    path = [(0, guard), (12, seat), (18, slap), (30, pouch), (36, pouch), (46, slap), (49, seat), (51, slap),
            (60, guard), (66, guard)]
    for (fa, a), (fb, b) in zip(path, path[1:]):
        if f <= fb:
            u = smooth((f - fa) / max(fb - fa, 1))
            ra, rb = a[1], b[1] if a[1].dot(b[1]) >= 0 else -b[1]
            left = (a[0].lerp(b[0], u), ra.slerp(rb, u))
            break
    grip_arms(p, left, curl_l=70 if 12 <= f <= 51 else 58)
    return p


@clip("Throw", 36, loop=False, armed_=True)
def throw(f, n):
    """Overhand grenade throw with the support hand while the rifle hangs in the strong hand:
    weight rocks back, the chest coils, then drives forward onto the front boot. Release at f15."""
    coil = keys(f, [(0, 0.0), (9, 1.0), (12, 1.0), (16, -1.0), (22, -0.8), (36, 0.0)])
    p = Pose()
    rifle_stance(p, w_l=lerp(0.56, 0.2, max(coil, 0)) if coil >= 0 else lerp(0.56, 0.85, -coil))
    spine(p, yaw=-14 * coil, pitch=-6 * coil)
    neck(p, yaw=14 * coil)
    shoulders(p, fwd=0, up_l=8 * max(coil, 0))
    spec = dict(HOLDS["ready"])
    spec["pitch"] = 40
    spec["yaw"] = 20
    p.spec = spec
    balance(p)
    p.hold = weapon_xform(p, spec)
    grip_arms(p, left_grip(p))
    # left arm FK: hand cocked high behind the head, then whips over the top and follows through
    sw = keys(f, [(0, 20.0), (9, 150.0), (12, 155.0), (15, 120.0), (18, 40.0), (24, 10.0), (36, 20.0)])
    ab = keys(f, [(0, 20.0), (9, 70.0), (12, 72.0), (16, 30.0), (36, 20.0)])
    el = keys(f, [(0, 60.0), (9, 120.0), (12, 125.0), (15, 40.0), (18, 15.0), (36, 60.0)])
    if f < 30:
        arm(p, "l", 1, swing=sw, abduct=ab, elbow=el, inward=0, wrist=-20 if f < 14 else 25)
        hands(p, 0, thumb=30, curl_l=55 if f < 15 else 20, curl_r=70, index_r=22)
    else:                               # hand back onto the handguard
        u = smooth((f - 30) / 6)
        free = Pose()
        free.D = dict(p.D)
        arm(free, "l", 1, swing=sw, abduct=ab, elbow=el, inward=0, wrist=25)
        for b in ("upperarm_l", "lowerarm_l", "hand_l"):
            p.D[b] = free.D[b].slerp(p.D[b] if free.D[b].dot(p.D[b]) >= 0 else -p.D[b], u)
    return p


@clip("Use_Item", 60, loop=False)
def use_item(f, n):
    """Field dressing: rifle slung, right forearm held across the chest while the left hand winds a
    bandage around it, head down, then a final tug."""
    inn = smooth(f / 8) * (1 - smooth((f - 52) / 8))
    p = Pose()
    stance(p, drop=0.05, lean=10 + 6 * inn)
    neck(p, pitch=14 * inn, yaw=-8 * inn)
    balance(p)
    arm(p, "r", -1, swing=lerp(4, 42, inn), abduct=lerp(17, 10, inn), elbow=lerp(22, 100, inn),
        inward=lerp(6, 55, inn), wrist=-10)
    fore = p.head("lowerarm_r").lerp(p.head("hand_r"), 0.55)
    ax = (p.head("hand_r") - p.head("lowerarm_r")).normalized()
    ang = 2 * math.pi * 2.5 * smooth((f - 8) / 40)
    e1 = ax.cross(Z).normalized()
    e2 = ax.cross(e1)
    tug = 0.06 * math.exp(-((f - 50) / 2.5) ** 2)
    target = fore + (e1 * math.cos(ang) + e2 * math.sin(ang)) * 0.075 + e1 * tug
    arm(p, "l", 1, swing=4, abduct=17, elbow=22, inward=6, wrist=-8)
    rest = p.head("hand_l")
    p.two_bone("upperarm_l", "lowerarm_l", rest.lerp(target, inn), p.G("spine_03") @ Vector((0.8, 0.4, -0.4)))
    hands(p, 40, curl_l=lerp(35, 60, inn), curl_r=lerp(35, 70, inn))
    return p


# ----------------------------------------------------------------------------- bake
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"
rig.animation_data_create()
only = [a for a in ARGS if a in CLIPS]
names = only or list(CLIPS)
actions = {}
for name in names:
    c = CLIPS[name]
    n = c["frames"]
    REACH["leg"] = REACH["arm"] = 0.0
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type="OBJECT", name=rig.name)
    bag = anim_utils.action_ensure_channelbag_for_slot(act, slot)
    data = {b: [] for b in ORDER}
    loc = []
    prev = {}
    worst = 0.0
    for f in range(n + 1):
        p = c["fn"](f if not c["loop"] or f < n else 0, n)
        if not c["speed"] and p.legs and name not in ("Jump_Start", "Dodge_Roll", "Fall_Loop"):
            pts = [(support_point(r), r["w"]) for r in p.legs.values()]
            pts = [(pt, w) for pt, w in pts if pt is not None and w > 0]
            if pts and name != "Loot":   # Loot balances over the knee too
                tgt = sum((pt * w for pt, w in pts), Vector()) / sum(w for _, w in pts)
                cm = com(p)
                worst = max(worst, Vector((cm.x - tgt.x, cm.y - tgt.y)).length)
        for b in ORDER:
            ql = R0[b].inverted() @ p.D[b] @ R0[b]
            if b in prev and ql.dot(prev[b]) < 0:
                ql = -ql
            prev[b] = ql
            data[b].append(ql)
        loc.append(R0["pelvis"].inverted() @ p.off)
    for b in ORDER:
        path = f'pose.bones["{b}"].rotation_quaternion'
        for i in range(4):
            fc = bag.fcurves.new(path, index=i, group_name=b)
            fc.keyframe_points.add(n + 1)
            fc.keyframe_points.foreach_set("co", [v for f, qq in enumerate(data[b]) for v in (f, qq[i])])
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.update()
    for i in range(3):
        fc = bag.fcurves.new('pose.bones["pelvis"].location', index=i, group_name="pelvis")
        fc.keyframe_points.add(n + 1)
        fc.keyframe_points.foreach_set("co", [v for f, l in enumerate(loc) for v in (f, l[i])])
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.update()
    act.frame_range = (0, n)
    act.use_frame_range = True
    act.use_cyclic = c["loop"]
    actions[name] = (act, slot)
    print(f"[anim] {name}: {n} frames ({n / FPS:.2f}s) loop={c['loop']} speed={c['speed']} m/s "
          f"leg_miss={REACH['leg'] * 100:.1f}cm arm_miss={REACH['arm'] * 100:.1f}cm "
          f"com_off_support={worst * 100:.1f}cm")

# light game mesh for preview and export
parts = [o for o in rig.children if o.type == "MESH" and not o.hide_render]
for o in parts:
    for m in o.modifiers:
        if m.type == "SUBSURF":
            m.levels = m.render_levels = 0
        elif m.type == "DISPLACE":
            m.show_viewport = m.show_render = False

# preview rifle (models/ar.py) riding the weapon_r socket
weapon = []
ar_path = os.path.join(OUT, "ar.blend")
if os.path.exists(ar_path):
    with bpy.data.libraries.load(ar_path) as (src, dst):
        dst.objects = list(src.objects)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    socket = rig.matrix_world @ Matrix.Translation(O_REST) @ R_REST.to_matrix().to_4x4()
    for o in dst.objects:
        if o is None or o.type != "MESH" or o.name.startswith("Floor"):
            continue
        scene.collection.objects.link(o)
        local = o.matrix_world.copy()
        o.parent = rig
        o.parent_type = "BONE"
        o.parent_bone = "weapon_r"
        bpy.context.view_layer.update()
        o.matrix_world = socket @ local
        weapon.append(o)

scene.render.fps = FPS


def use(name):
    act, slot = actions[name]
    rig.animation_data.action = act
    rig.animation_data.action_slot = slot
    scene.frame_start, scene.frame_end = 0, CLIPS[name]["frames"]
    for o in weapon:
        o.hide_render = o.hide_viewport = not CLIPS[name]["armed"]


os.makedirs(OUT, exist_ok=True)
use(names[0])
if not only:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "raider_anim.blend"), copy=True)

if "noexport" not in ARGS and not QUICK and not only:
    for o in bpy.context.view_layer.objects:
        o.select_set(o is rig or o in parts)
    bpy.context.view_layer.objects.active = rig
    rig.animation_data.action = None
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "raider_anim.glb"), export_format="GLB",
                              use_selection=True, export_apply=True, export_skins=True,
                              export_animations=True, export_animation_mode="ACTIONS",
                              export_force_sampling=True, export_frame_range=False, export_def_bones=False)
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "raider_anim.fbx"), use_selection=True,
                             add_leaf_bones=False, use_mesh_modifiers=True, mesh_smooth_type="FACE",
                             bake_anim=True, bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0)
    print("EXPORTED raider_anim.glb / raider_anim.fbx")

# ----------------------------------------------------------------------------- preview
if "norender" in ARGS:
    sys.exit(0)
cd = bpy.data.cameras.new("AnimCam")
cd.lens = 50
cam = bpy.data.objects.new("Cam_anim", cd)
cam.location = (-2.0, -3.1, 1.25)
scene.collection.objects.link(cam)
tgt = bpy.data.objects.new("Cam_anim_target", None)
tgt.location = (0, 0, 0.85)
scene.collection.objects.link(tgt)
tc = cam.constraints.new("TRACK_TO")
tc.target, tc.track_axis, tc.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
scene.camera = cam
r = scene.render
if QUICK:
    r.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
else:
    r.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 24
r.resolution_x = r.resolution_y = 540 if QUICK else 720
r.resolution_percentage = 100
r.image_settings.file_format = "PNG"
r.use_stamp = True                     # clip name burned into the corner
for attr in dir(r):
    if attr.startswith("use_stamp_") and attr not in ("use_stamp_note", "use_stamp_labels"):
        setattr(r, attr, False)
r.use_stamp_note = True
r.stamp_font_size = 22
adir = os.path.join(OUT, "anim")
os.makedirs(adir, exist_ok=True)
STILLS = "stills" in ARGS
ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def ff(*a):
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", *a], check=True)


videos = []
for name in names:
    use(name)
    c = CLIPS[name]
    n = c["frames"]
    r.stamp_note_text = f"{name}" + (f"  ({c['speed']} m/s in game)" if c["speed"] else "")
    fdir = os.path.join(adir, "frames", name)
    shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(fdir)
    # loops skip their last frame (it equals frame 0) so the video repeats seamlessly
    frames = list(range(0, n + 1, max(1, n // 12))) if STILLS else list(range(0, n if c["loop"] else n + 1))
    for i, f in enumerate(frames):
        scene.frame_set(f)
        r.filepath = os.path.join(fdir, f"{i:04d}.png")
        bpy.ops.render.render(write_still=True)
    src = os.path.join(fdir, "%04d.png")
    if STILLS:
        ff("-framerate", "1", "-i", src, "-vf", f"scale=360:360,tile=5x{math.ceil(len(frames) / 5)}",
           "-frames:v", "1", os.path.join(adir, f"{name}_sheet.png"))
    else:
        loops = max(1, round(4 * FPS / n)) if c["loop"] else 1      # loops play for about 4 s
        mp4 = os.path.join(adir, f"{name}.mp4")
        ff("-stream_loop", str(loops - 1), "-framerate", str(FPS), "-i", src,
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4)
        videos.append(mp4)
    shutil.rmtree(fdir, ignore_errors=True)
    print("PREVIEW", name)
shutil.rmtree(os.path.join(adir, "frames"), ignore_errors=True)
if len(videos) > 1:                     # every clip back to back in one file
    lst = os.path.join(adir, "reel.txt")
    with open(lst, "w") as fh:
        fh.writelines(f"file '{v}'\n" for v in videos)
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(adir, "raider_reel.mp4"))
    os.remove(lst)
    print("REEL", os.path.join(adir, "raider_reel.mp4"))
