"""
Low-poly fox - animated 12 s short (288 frames @ 24 fps), autumn clearing.

Same discipline as the gardener: blender-lpm-skill primitives, flat shading, one palette
material per object, real metres, Z up, front = -Y; object rig (each limb its own object,
origin on its joint), poses written as WORLD angles.

    python fox_scene.py --save fox.blend --stats
    python fox_scene.py --frames 60,160,260 --res 640 --samples 12 --out frames
    python fox_scene.py --range 1 288 --step 4 --offset 0 --threads 1 --out frames
"""
import argparse, json, math, os, sys

SKILL = "/home/user/NaelAerts/.claude/skills/blender-lpm-skill/scripts"
sys.path.insert(0, SKILL)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bpy                                            # noqa: E402
from mathutils import Euler, Vector                   # noqa: E402
import lpm                                            # noqa: E402
import lpm_anim as A                                  # noqa: E402

FPS, DUR = 24, 288

PALETTE_FOX = [
    ("fur",        "#c6873c", 0.0, 0.72),
    ("fur_dark",   "#a06b35", 0.0, 0.72),
    ("fur_light",  "#f0e3d2", 0.0, 0.75),
    ("paw",        "#3a2a22", 0.0, 0.65),
    ("nose",       "#2a1f1a", 0.0, 0.50),
    ("eye",        "#241c18", 0.0, 0.35),
    ("grass",      "#7a9b43", 0.0, 0.85),
    ("grass_dark", "#5f8036", 0.0, 0.85),
    ("grass_dry",  "#a8a248", 0.0, 0.85),
    ("pine",       "#4e8259", 0.0, 0.80),
    ("pine_dark",  "#3d6b4a", 0.0, 0.80),
    ("trunk",      "#6b4a30", 0.0, 0.80),
    ("trunk_light","#9a7a52", 0.0, 0.80),
    ("birch",      "#ddd6c6", 0.0, 0.80),
    ("leaf_amber", "#dd9336", 0.0, 0.75),
    ("leaf_red",   "#c25733", 0.0, 0.75),
    ("leaf_gold",  "#e8c250", 0.0, 0.75),
    ("rock",       "#9b9589", 0.0, 0.90),
    ("rock_dark",  "#7a746a", 0.0, 0.90),
    ("earth",      "#7a5a3c", 0.0, 0.90),
    ("white",      "#f4f1e8", 0.0, 0.80),
]
P = None

# rest geometry of the fox (metres, facing -Y)
SHOULDER = (0.085, -0.195, 0.40)       # x offset, y, z of the front leg pivot
HIP = (0.100, 0.185, 0.42)
KNEE_Z = 0.20
HEAD_PIVOT = (0.0, -0.265, 0.455)
TAIL_PIVOT = (0.0, 0.265, 0.435)


def build_fox():
    """Rest pose: standing square on all fours. Returns the joint dict."""
    fur, fd, fl = P["fur"], P["fur_dark"], P["fur_light"]
    root = A.empty("FOX_Root", (0, 0, 0))
    spine = A.empty("FOX_Spine", (0, 0.12, 0.42), root)

    torso = lpm.box("f_torso", (0.21, 0.50, 0.22), at=(0, 0.0, 0.30), color=fur)
    lpm.paint(torso, fl, where=lambda c, n, i: n.z < -0.5)
    chest = lpm.box("f_chest", (0.23, 0.20, 0.25), at=(0, -0.22, 0.27), color=fur, taper=(0.92, 0.95))
    lpm.paint(chest, fl, where=lambda c, n, i: n.z < -0.5 or n.y < -0.5)
    rump = lpm.box("f_rump", (0.22, 0.16, 0.24), at=(0, 0.18, 0.28), color=fur, taper=(0.86, 0.9))
    neck = lpm.box("f_neck", (0.17, 0.17, 0.17), at=(0, -0.30, 0.355), color=fur, taper=(0.9, 0.92))
    lpm.rotate(neck, -22, "X", about=(0, -0.26, 0.36))
    ruff = lpm.prism("f_ruff", 8, 0.125, 0.06, at=(0, -0.30, 0.40), color=fl)
    lpm.rotate(ruff, -70, "X", about=(0, -0.30, 0.43))
    body = A.group("FOX_Body", [torso, chest, rump, neck, ruff], (0, 0.12, 0.42), spine)

    # --- head (pivot at the base of the skull)
    skull = lpm.box("h_skull", (0.165, 0.175, 0.145), at=(0, -0.345, 0.40), color=fur, taper=(0.88, 0.9))
    snout = lpm.box("h_snout", (0.095, 0.135, 0.085), at=(0, -0.455, 0.415), color=fl, taper=(0.68, 0.75))
    muzzle = lpm.box("h_muzzle", (0.105, 0.05, 0.055), at=(0, -0.44, 0.40), color=fur_or_light(fur))
    nose = lpm.box("h_nose", (0.05, 0.035, 0.04), at=(0, -0.585, 0.445), color=P["nose"], taper=(0.7, 0.7))
    cheekL = lpm.sweep("h_cheekL", [(0.0, 0), (0.048, 0.012), (0.036, 0.05), (0.0, 0.042)], depth=0.016,
                       at=(0.082, -0.40, 0.358), color=fl)
    cheekR = lpm.sweep("h_cheekR", [(0.0, 0), (-0.048, 0.012), (-0.036, 0.05), (0.0, 0.042)], depth=0.016,
                       at=(-0.082, -0.40, 0.358), color=fl)
    eyeL = lpm.box("h_eyeL", (0.028, 0.022, 0.026), at=(0.058, -0.425, 0.465), color=P["eye"])
    eyeR = lpm.box("h_eyeR", (0.028, 0.022, 0.026), at=(-0.058, -0.425, 0.465), color=P["eye"])
    parts = [skull, snout, muzzle, nose, cheekL, cheekR, eyeL, eyeR]
    head = A.group("FOX_Head", parts, HEAD_PIVOT, body)

    # --- ears (own objects so they can twitch)
    joints = {"root": root, "spine": spine, "body": body, "head": head}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        ear = lpm.sweep(f"e_ear{side}", [(-0.055, 0), (0.055, 0), (0.0, 0.135)], depth=0.022,
                        at=(sx * 0.072, -0.33, 0.525), color=fur)
        lpm.paint(ear, P["paw"], where=lambda c, n, i: c.z > 0.60)
        inner = lpm.sweep(f"e_in{side}", [(-0.024, 0), (0.024, 0), (0.0, 0.062)], depth=0.008,
                          at=(sx * 0.072, -0.344, 0.533), color=fl)
        joints[f"ear{side}"] = A.group(f"FOX_Ear{side}", [ear, inner], (sx * 0.072, -0.33, 0.515), head)

    # --- legs: upper (pivot at shoulder/hip) + lower (pivot at knee) with the paw
    for tag, pivot, up_r, lo_r in (("FL", (SHOULDER[0], SHOULDER[1], SHOULDER[2]), 0.052, 0.040),
                                   ("FR", (-SHOULDER[0], SHOULDER[1], SHOULDER[2]), 0.052, 0.040),
                                   ("BL", (HIP[0], HIP[1], HIP[2]), 0.060, 0.042),
                                   ("BR", (-HIP[0], HIP[1], HIP[2]), 0.060, 0.042)):
        px, py, pz = pivot
        thigh = lpm.prism(f"l_up{tag}", 6, up_r, pz - KNEE_Z, at=(px, py, KNEE_Z), color=fur, radius_top=up_r * 1.25)
        if tag[0] == "B":
            haunch = lpm.lathe(f"l_ha{tag}", [(0.085, 0), (0.105, 0.06), (0.08, 0.14), (0, 0.17)], segments=6,
                               at=(px, py + 0.02, pz - 0.12), color=fur)
            parts_u = [thigh, haunch]
        else:
            parts_u = [thigh]
        joints[tag + "_up"] = A.group(f"FOX_{tag}Up", parts_u, (px, py, pz), spine)

        shin = lpm.prism(f"l_lo{tag}", 6, lo_r, KNEE_Z - 0.035, at=(px, py, 0.035), color=fur, radius_top=lo_r * 1.1)
        lpm.paint(shin, P["paw"], where=lambda c, n, i: c.z < 0.10)
        paw = lpm.box(f"l_paw{tag}", (0.072, 0.095, 0.045), at=(px, py - 0.015, 0.0), color=P["paw"], taper=(0.85, 0.8))
        joints[tag + "_lo"] = A.group(f"FOX_{tag}Lo", [shin, paw], (px, py, KNEE_Z), joints[tag + "_up"])

    # --- tail: three chained segments, white tip
    t1 = lpm.prism("t_1", 6, 0.062, 0.17, at=TAIL_PIVOT, color=fur, radius_top=0.070)
    tail1 = A.group("FOX_Tail1", [t1], TAIL_PIVOT, spine)
    p2 = (TAIL_PIVOT[0], TAIL_PIVOT[1], TAIL_PIVOT[2] + 0.17)
    t2 = lpm.prism("t_2", 6, 0.070, 0.15, at=p2, color=fur, radius_top=0.058)
    tail2 = A.group("FOX_Tail2", [t2], p2, tail1)
    p3 = (p2[0], p2[1], p2[2] + 0.15)
    t3 = lpm.lathe("t_3", [(0.058, 0), (0.062, 0.05), (0.045, 0.11), (0, 0.145)], segments=6, at=p3, color=P["fur_light"])
    tail3 = A.group("FOX_Tail3", [t3], p3, tail2)
    joints.update({"tail1": tail1, "tail2": tail2, "tail3": tail3})
    return joints


def fur_or_light(fur):
    return fur


# --------------------------------------------------------------------------- clearing

def build_env():
    g, gd, dry = P["grass"], P["grass_dark"], P["grass_dry"]
    ground = lpm.box("e_ground", (56, 56, 0.06), at=(0, 4, -0.06), color=g)
    patches = []
    for i, (px, py, r, col) in enumerate([(-2.6, 1.4, 1.9, gd), (2.2, 0.6, 2.2, dry), (-5.0, -0.8, 1.6, dry),
                                          (4.6, 2.0, 1.8, gd), (0.4, 3.2, 2.4, gd), (-7.0, 2.2, 2.0, gd),
                                          (6.8, -0.6, 1.7, dry)]):
        # each patch sits at its own height: two coplanar tops shadow each other and render black
        patches.append(lpm.prism(f"e_patch{i}", 7, r, 0.010, at=(px, py, 0.004 + i * 0.0016), color=col, rotate=i * 23))
    for i, (hx, hy, hr, hh) in enumerate([(-16, 26, 9.0, 3.4), (8, 30, 11.0, 4.2), (24, 24, 7.5, 2.6)]):
        patches.append(lpm.lathe(f"e_hill{i}", [(hr, 0), (hr * 0.7, hh * 0.45), (hr * 0.36, hh * 0.8), (0, hh)],
                                 segments=8, at=(hx, hy, 0.030 + i * 0.002), color=P["pine_dark"] if i % 2 else gd))
    A.group("ENV_Ground", [ground] + patches)

    # pines ringing the clearing
    pines = []
    spots = [(-7.5, 7.0, 1.15), (-4.6, 8.4, 0.9), (-1.2, 9.2, 1.25), (2.4, 8.6, 1.0), (6.0, 7.6, 1.2),
             (9.0, 6.0, 0.95), (-9.5, 4.2, 1.05), (11.0, 3.0, 1.1), (-6.0, 11.0, 0.85), (3.5, 11.5, 0.95)]
    for i, (tx, ty, ts) in enumerate(spots):
        pines.append(lpm.prism(f"p_tr{i}", 6, 0.16 * ts, 1.1 * ts, at=(tx, ty, 0), color=P["trunk"], radius_top=0.11 * ts))
        for k, (cz, cr, ch) in enumerate([(0.85, 1.05, 1.5), (1.75, 0.82, 1.3), (2.55, 0.56, 1.1), (3.2, 0.3, 0.8)]):
            pines.append(lpm.lathe(f"p_c{i}{k}", [(cr * ts, 0), (cr * 0.55 * ts, ch * 0.55 * ts), (0, ch * ts)],
                                   segments=7, at=(tx, ty, cz * ts), color=P["pine"] if k % 2 else P["pine_dark"]))
    A.group("ENV_Pines", pines)

    # birches with amber crowns, closer in
    birch = []
    for i, (tx, ty, ts, col) in enumerate([(-3.4, 4.6, 1.0, "leaf_amber"), (4.2, 4.0, 0.85, "leaf_red"),
                                           (8.2, 5.2, 0.95, "leaf_gold"), (-8.0, 2.6, 0.8, "leaf_amber")]):
        tr = lpm.prism(f"b_tr{i}", 7, 0.13 * ts, 2.3 * ts, at=(tx, ty, 0), color=P["birch"], radius_top=0.10 * ts)
        lpm.paint(tr, P["trunk"], where=lambda c, n, i2: int((c.z + 10) / 0.33) % 3 == 0)
        birch.append(tr)
        for k, (ox, oy, oz, orr) in enumerate([(0, 0, 2.5, 0.95), (0.35, 0.2, 2.95, 0.62), (-0.3, -0.15, 2.85, 0.55)]):
            birch.append(lpm.lathe(f"b_c{i}{k}", [(orr * ts, 0), (orr * 1.02 * ts, orr * 0.5 * ts),
                                                  (orr * 0.72 * ts, orr * 1.1 * ts), (0, orr * 1.6 * ts)],
                                   segments=7, at=(tx + ox * ts, ty + oy * ts, oz * ts), color=P[col]))
    A.group("ENV_Birch", birch)

    # rocks, fallen log, bushes, tufts
    props = []
    for i, (rx, ry, rr) in enumerate([(-2.1, 2.3, 0.38), (3.3, 1.9, 0.30), (-4.3, 0.7, 0.22), (5.6, 2.6, 0.42)]):
        props.append(lpm.lathe(f"r_rock{i}", [(rr, 0), (rr * 1.08, rr * 0.5), (rr * 0.7, rr * 1.1), (0, rr * 1.35)],
                               segments=6, at=(rx, ry, 0), color=P["rock"] if i % 2 else P["rock_dark"]))
    log = lpm.prism("r_log", 8, 0.19, 2.3, at=(0, 0, 0), color=P["trunk"])
    lpm.rotate(log, 90, "Y", about=(0, 0, 0))
    lpm.rotate(log, 14, "Z", about=(0, 0, 0))
    lpm.move(log, -4.3, 3.3, 0.19)
    cut = lpm.prism("r_cut", 8, 0.19, 0.03, at=(0, 0, 0), color=P["trunk_light"])
    lpm.rotate(cut, 90, "Y", about=(0, 0, 0))
    lpm.rotate(cut, 14, "Z", about=(0, 0, 0))
    lpm.move(cut, -5.43, 3.02, 0.19)
    props += [log, cut]
    for i, (bx, by, br) in enumerate([(1.9, 3.4, 0.55), (-1.4, 4.2, 0.42), (6.4, 3.4, 0.48), (-6.2, 3.8, 0.5),
                                      (9.4, 1.6, 0.44)]):
        props.append(lpm.lathe(f"r_bush{i}", [(br, 0), (br * 1.05, br * 0.45), (br * 0.8, br * 1.05),
                                              (br * 0.42, br * 1.45), (0, br * 1.62)], segments=7,
                               at=(bx, by, 0), color=P["pine_dark"] if i % 2 else P["grass_dark"]))
    for i in range(26):
        a = i * 2.39996
        tx, ty = 3.6 * math.cos(a) * (0.4 + (i % 5) * 0.22), 2.4 + 2.6 * math.sin(a) * (0.3 + (i % 4) * 0.25)
        h = 0.14 + 0.05 * (i % 3)
        props.append(lpm.sweep(f"r_tuft{i}", [(-0.035, 0), (0.035, 0), (0.012, h), (-0.012, h * 0.8)], depth=0.012,
                               at=(tx, ty, 0), color=P["grass_dry"] if i % 3 else P["grass_dark"]))
    A.group("ENV_Props", props)


def build_leaves(n=16):
    """Autumn leaves that keep drifting down through the whole shot."""
    leaves = []
    cols = ["leaf_amber", "leaf_red", "leaf_gold"]
    for i in range(n):
        lf = lpm.sweep(f"lf_{i}", [(0.0, 0.0), (0.055, 0.035), (0.085, 0.0), (0.055, -0.035)], depth=0.004,
                       at=(0, 0, 0), color=P[cols[i % 3]], axis="z")
        leaves.append(A.group(f"LEAF_{i}", [lf], (0, 0, 0)))
    return leaves


# --------------------------------------------------------------------------- posing

FRONT = dict(pz=SHOULDER[2], Lu=0.20, Ll=0.20)
HIND = dict(pz=HIP[2], Lu=0.22, Ll=0.20)
STOP_X, PATH_Y = 1.05, 0.10


def solve_lower(geo, u_w, paw_z=0.0, dz=0.0):
    """World angle of the lower segment that puts the paw at `paw_z`, with the spine raised/lowered
    by `dz` from its rest height (the joint rides with it, so the solve must know)."""
    c = (geo["pz"] + dz - paw_z - geo["Lu"] * math.cos(math.radians(u_w))) / geo["Ll"]
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def leg(J, f, tag, u_w, lower_w, interp="BEZIER"):
    A.kr(J[tag + "_up"], f, u_w, 0, 0, interp)
    A.kr(J[tag + "_lo"], f, lower_w - u_w, 0, 0, interp)


def stance(J, f, tag, u_w, paw_z=0.0, interp="BEZIER", spine_z=0.42):
    geo = FRONT if tag[0] == "F" else HIND
    leg(J, f, tag, u_w, solve_lower(geo, u_w, paw_z, spine_z - 0.42), interp)


def trot(J, f0, f1, x0, x1, y, period=16.0, amp_f=19.0, amp_h=22.0, lift=52.0):
    """Diagonal trot: FL+BR in phase, FR+BL half a cycle later. Stance legs are solved so the
    paw stays on the ground; swing legs flex to clear it."""
    legs = (("FL", 0.0, amp_f), ("BR", 0.0, amp_h), ("FR", 0.5, amp_f), ("BL", 0.5, amp_h))
    f = f0
    while f <= f1:
        t = (f - f0) / max(f1 - f0, 1)
        p = ((f - f0) % period) / period
        A.kl(J["root"], f, x0 + (x1 - x0) * t, y, 0.0, interp="LINEAR")
        A.kr(J["root"], f, 0, 0, 90)
        sz = 0.42 + 0.013 * math.cos(4 * math.pi * p)
        A.kl(J["spine"], f, 0, 0.12, sz)
        A.kr(J["body"], f, 2.5 * math.sin(4 * math.pi * p), 0, 1.5 * math.sin(2 * math.pi * p))
        A.kr(J["head"], f, -2.5 * math.sin(4 * math.pi * p) - 4, 0, 0)
        A.kr(J["tail1"], f, -64 + 5 * math.sin(2 * math.pi * p), 0, 6 * math.sin(2 * math.pi * p))
        A.kr(J["tail2"], f, -12 + 4 * math.sin(2 * math.pi * p + 0.7), 0, 4 * math.sin(2 * math.pi * p + 0.7))
        A.kr(J["tail3"], f, -10 + 4 * math.sin(2 * math.pi * p + 1.4), 0, 3 * math.sin(2 * math.pi * p + 1.4))
        for tag, ph, amp in legs:
            pp = (p + ph) % 1.0
            u = -amp * math.cos(2 * math.pi * pp)
            if pp < 0.5:                                    # stance: paw pinned to the ground
                stance(J, f, tag, u, 0.0, interp="LINEAR", spine_z=sz)
            else:                                           # swing: knee flexes to clear it
                s = (pp - 0.5) / 0.5
                flex = lift * math.sin(math.pi * s)
                geo = FRONT if tag[0] == "F" else HIND
                leg(J, f, tag, u, u + flex + solve_lower(geo, 0.0, 0.0, sz - 0.42) * 0.25, interp="BEZIER")
        f += period / 8.0


def square(J, f, spine_z=0.42, body_rx=0.0, u_front=-2.0, u_hind=4.0):
    """Four-square standing pose with every paw on the ground."""
    A.kl(J["spine"], f, 0, 0.12, spine_z)
    A.kr(J["body"], f, body_rx, 0, 0)
    for tag in ("FL", "FR"):
        stance(J, f, tag, u_front, spine_z=spine_z)
    for tag in ("BL", "BR"):
        stance(J, f, tag, u_hind, spine_z=spine_z)


def head(J, f, rx_w, rz_w=0.0, body_rx=0.0):
    A.kr(J["head"], f, rx_w - body_rx, 0, rz_w)


def ears(J, f, rxL, rxR, rzL=0.0, rzR=0.0):
    A.kr(J["earL"], f, rxL, 0, rzL)
    A.kr(J["earR"], f, rxR, 0, rzR)


def tail(J, f, a1, a2, a3, z1=0.0, z2=0.0, z3=0.0):
    A.kr(J["tail1"], f, a1, 0, z1)
    A.kr(J["tail2"], f, a2 - a1, 0, z2 - z1)
    A.kr(J["tail3"], f, a3 - a2, 0, z3 - z2)


# --------------------------------------------------------------------------- storyboard (288 frames @ 24 fps)
#   1-118   trot across the clearing
# 118-146   slow down, settle four-square
# 146-192   sniff the ground, ears forward
# 192-216   head up, follows a falling leaf
# 216-258   sits back, tail curls round
# 258-288   sitting: looks to camera, ear twitch, tail flick

def animate(J, leaves):
    trot(J, 1, 118, -4.20, STOP_X, PATH_Y, period=16.0)

    def hold_root(f, x=STOP_X):
        A.kl(J["root"], f, x, PATH_Y, 0.0)
        A.kr(J["root"], f, 0, 0, 90)

    # --- settle
    for f in (126, 134, 146):
        hold_root(f)
    square(J, 126, spine_z=0.425, body_rx=1.5, u_front=-9, u_hind=10)
    head(J, 126, -2, 0, 1.5); ears(J, 126, -6, -6); tail(J, 126, -58, -14, -12)
    square(J, 134, spine_z=0.418, body_rx=0.5, u_front=-1, u_hind=5)
    head(J, 134, 2, -6, 0.5); ears(J, 134, -4, -2); tail(J, 134, -62, -10, -8, z1=-6, z2=-10, z3=-14)
    square(J, 146, spine_z=0.420, body_rx=0.0, u_front=-2, u_hind=4)
    head(J, 146, 6, 4); ears(J, 146, -2, -4, rzL=4, rzR=-6); tail(J, 146, -60, -12, -10)

    # --- sniff the ground
    for f in (158, 166, 174, 182, 192):
        hold_root(f)
    square(J, 158, spine_z=0.405, body_rx=6, u_front=4, u_hind=2)
    head(J, 158, 52, -8, body_rx=6); ears(J, 158, -16, -14, rzL=6, rzR=-6); tail(J, 158, -48, -10, -8)
    square(J, 166, spine_z=0.400, body_rx=8, u_front=5, u_hind=2)
    head(J, 166, 60, 4, body_rx=8); ears(J, 166, -20, -12, rzL=8, rzR=-4)
    tail(J, 166, -44, -8, -6, z1=10, z2=14, z3=18)
    square(J, 174, spine_z=0.402, body_rx=7, u_front=4, u_hind=2)
    head(J, 174, 55, -10, body_rx=7); ears(J, 174, -14, -20, rzL=4, rzR=-10)
    tail(J, 174, -46, -10, -8, z1=-10, z2=-14, z3=-18)
    square(J, 182, spine_z=0.400, body_rx=8, u_front=5, u_hind=2)
    head(J, 182, 58, 8, body_rx=8); ears(J, 182, -22, -16, rzL=8, rzR=-6)
    tail(J, 182, -45, -9, -7, z1=8, z2=12, z3=16)

    # --- head up, tracks a leaf drifting down on his left
    square(J, 192, spine_z=0.415, body_rx=2, u_front=0, u_hind=3)
    head(J, 192, 6, 0, body_rx=2); ears(J, 192, -8, -8); tail(J, 192, -58, -12, -10)
    for f in (202, 210, 216):
        hold_root(f)
    square(J, 202, spine_z=0.420, body_rx=-2, u_front=-3, u_hind=4)
    head(J, 202, -26, 22, body_rx=-2); ears(J, 202, -14, -10, rzL=10, rzR=4)
    tail(J, 202, -62, -14, -10, z1=8, z2=12, z3=16)
    square(J, 210, spine_z=0.420, body_rx=-2, u_front=-3, u_hind=4)
    head(J, 210, -18, -14, body_rx=-2); ears(J, 210, -10, -16, rzL=4, rzR=-10)
    tail(J, 210, -60, -12, -10, z1=-6, z2=-10, z3=-12)

    # --- he settles down and curls up
    A.kl(J["spine"], 216, 0, 0.12, 0.420); A.kr(J["body"], 216, -4, 0, 0)
    for t in ("FL", "FR"):
        stance(J, 216, t, -4, spine_z=0.420)
    for t in ("BL", "BR"):
        stance(J, 216, t, 6, spine_z=0.420)
    head(J, 216, -6, -8, body_rx=-4); ears(J, 216, -8, -8); tail(J, 216, -60, -12, -10)
    hold_root(216)

    A.kl(J["spine"], 232, 0, 0.12, 0.330); A.kr(J["body"], 232, -6, 0, 0)
    for t in ("FL", "FR"):
        stance(J, 232, t, -22, spine_z=0.330)
    for t in ("BL", "BR"):
        stance(J, 232, t, -26, spine_z=0.330)
    head(J, 232, -4, -4, body_rx=-6); ears(J, 232, -6, -6)
    tail(J, 232, -78, -24, -18, z1=18, z2=30, z3=44)
    hold_root(232)

    A.kl(J["spine"], 252, 0, 0.12, 0.245); A.kr(J["body"], 252, 1, 0, 0)
    leg(J, 252, "FL", -52, 72); leg(J, 252, "FR", -52, 72)
    leg(J, 252, "BL", -58, 78); leg(J, 252, "BR", -58, 78)
    head(J, 252, -2, 6, body_rx=1); ears(J, 252, -4, -4)
    tail(J, 252, -97, -34, -26, z1=42, z2=74, z3=104)
    hold_root(252)

    # --- lying in the clearing: looks to camera, ear twitch, tail tip flick, head tilt
    for f, (hrx, hrz, e1, e2, tz) in ((262, (-3, -20, -12, -4, 48)), (270, (0, -16, -4, -4, 36)),
                                      (278, (-5, -24, -6, -16, 54)), (288, (-2, -18, -5, -5, 44))):
        A.kl(J["spine"], f, 0, 0.12, 0.243)
        A.kr(J["body"], f, 1, 0, 0)
        leg(J, f, "FL", -52, 72); leg(J, f, "FR", -52, 72)
        leg(J, f, "BL", -58, 78); leg(J, f, "BR", -58, 78)
        head(J, f, hrx, hrz, body_rx=1)
        ears(J, f, e1, e2, rzL=6, rzR=-6)
        tail(J, f, -97, -34, -26, z1=tz, z2=tz * 1.6, z3=tz * 2.2)
        hold_root(f)

    # --- drifting leaves, looping through the whole shot
    for i, lf in enumerate(leaves):
        x0 = -5.5 + (i * 1.37) % 9.5
        y0 = -0.9 + (i * 2.11) % 5.0
        speed = 70 + (i % 5) * 12                       # frames to fall
        start = 1 - (i * 17) % speed
        spin = 180 + (i % 4) * 90
        f = start
        while f < DUR + speed:
            for k in range(0, 5):
                ff = f + k * speed / 4.0
                if ff < 1 or ff > DUR + 4:
                    continue
                t = k / 4.0
                A.kl(lf, int(ff), x0 + 0.45 * math.sin(t * 6.0 + i), y0 + 0.30 * math.cos(t * 5.0 + i),
                     3.4 * (1 - t) + 0.02, interp="LINEAR" if k in (0, 4) else "BEZIER")
                A.kr(lf, int(ff), 25 * math.sin(t * 7 + i), spin * t, 18 * math.cos(t * 6 + i))
            f += speed


# --------------------------------------------------------------------------- cameras & assembly

def build_cameras(J):
    sc = bpy.context.scene
    cams = {}
    cams["A"], ta = A.camera("CAM_A", (-4.8, -3.5, 0.95), (-4.2, 0.1, 0.42), lens=46)
    cams["B"], tb = A.camera("CAM_B", (3.00, -2.55, 1.00), (STOP_X, 0.10, 0.36), lens=50)
    cams["C"], tc = A.camera("CAM_C", (2.45, -3.00, 1.30), (STOP_X, 0.10, 0.42), lens=48)

    # A tracks the trot from the side, slightly ahead of him
    for f in range(1, 121, 20):
        t = (f - 1) / 117.0
        fx = -4.20 + (STOP_X + 4.20) * min(1.0, t)
        A.kl(cams["A"], f, fx - 0.55, -3.45, 0.93)
        A.kl(ta, f, fx + 0.55, 0.10, 0.40)
    A.kl(cams["B"], 119, 3.00, -2.55, 1.00); A.kl(tb, 119, STOP_X, 0.10, 0.36)
    A.kl(cams["B"], 215, 2.55, -2.30, 0.82); A.kl(tb, 215, STOP_X, 0.06, 0.44)
    A.kl(cams["C"], 216, 2.30, -2.85, 1.15); A.kl(tc, 216, STOP_X, 0.10, 0.40)
    A.kl(cams["C"], 288, 1.70, -2.05, 0.58); A.kl(tc, 288, STOP_X - 0.02, 0.08, 0.26)

    sc.camera = cams["A"]
    for f, key in ((1, "A"), (119, "B"), (216, "C")):
        mk = sc.timeline_markers.new(f"SHOT_{key}", frame=f)
        mk.camera = cams[key]
    return cams


def build():
    global P
    lpm.reset()
    P = A.set_palette(lpm.Palette(PALETTE_FOX))
    build_env()
    J = build_fox()
    leaves = build_leaves()
    A.sky_and_sun(sun_energy=3.9, sky_strength=0.34, elevation=34, rotation=168,
                  sun_euler=(52, 0, 26), fill={"energy": 80, "loc": (-3.0, -5.0, 4.0), "rot": (54, 0, -28)})
    build_cameras(J)
    animate(J, leaves)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, DUR
    return J, leaves


def probe(J, frames):
    out = {}
    for f in frames:
        row = {}
        for tag in ("FL", "FR", "BL", "BR"):
            geo = FRONT if tag[0] == "F" else HIND
            row[tag] = [round(v, 3) for v in A.world_point(J[tag + "_lo"], (0, 0, -geo["Ll"]), f)]
        row["nose"] = [round(v, 3) for v in A.world_point(J["head"], (0, -0.32, -0.01), f)]
        row["spine"] = [round(v, 3) for v in A.world_point(J["spine"], (0, 0, 0), f)]
        out[f] = row
    print("##PROBE##" + json.dumps(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save"); ap.add_argument("--out", default="frames")
    ap.add_argument("--frames"); ap.add_argument("--range", nargs=2, type=int)
    ap.add_argument("--step", type=int, default=1); ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--samples", type=int, default=16); ap.add_argument("--res", type=int, default=960)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--probe"); ap.add_argument("--stats", action="store_true")
    a = ap.parse_args(sys.argv[1:])

    J, _ = build()
    if a.stats:
        tot, rows = 0, []
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            t = lpm.tri_count(ob)
            tot += t
            rows.append((ob.name, t))
        rows.sort(key=lambda r: -r[1])
        fox = sum(t for n, t in rows if n.startswith("FOX_"))
        print("##STATS##" + json.dumps({"total_tris": tot, "fox_tris": fox, "objects": len(rows), "top": rows[:12]}))
    if a.probe:
        probe(J, [int(x) for x in a.probe.split(",")])
    if a.save:
        print("[saved]", lpm.save(a.save))
    A.setup_render(a.samples, a.res, a.threads)
    frames = []
    if a.frames:
        frames = [int(x) for x in a.frames.split(",")]
    elif a.range:
        frames = list(range(a.range[0] + a.offset, a.range[1] + 1, a.step))
    if frames:
        A.render_frames(frames, a.out)


if __name__ == "__main__":
    main()
