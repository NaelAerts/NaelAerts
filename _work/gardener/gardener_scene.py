"""
Low-poly gardener - animated 20 s short (480 frames @ 24 fps).

Built with the blender-lpm-skill toolkit (.claude/skills/blender-lpm-skill/scripts/lpm.py):
flat shading, one palette material per object, real metres, Z up, front = -Y.

The character is NOT one joined mesh: every limb is its own lpm object whose origin sits on
its joint, parented into a small hierarchy, then keyframed (object-level rig, no armature).

Usage (inside a Python that has `bpy` installed, e.g. /tmp/bpyenv/bin/python):
    python gardener_scene.py --save scene.blend
    python gardener_scene.py --frames 1,120,260,400 --out frames --samples 16 --res 480
    python gardener_scene.py --range 1 480 --step 1 --out frames --samples 24 --res 960
"""
import argparse, json, math, os, sys

SKILL = "/home/user/NaelAerts/.claude/skills/blender-lpm-skill/scripts"
sys.path.insert(0, SKILL)

import bpy, bmesh                                  # noqa: E402
from mathutils import Matrix, Vector, Euler        # noqa: E402
import lpm                                         # noqa: E402

FPS = 24
DUR = 480                                          # 20 s

# --------------------------------------------------------------------------- palette
PALETTE = [
    ("skin",        "#e0a878", 0.0, 0.55),
    ("skin_dark",   "#c08a5e", 0.0, 0.55),
    ("shirt",       "#4f7fb5", 0.0, 0.70),
    ("shirt_dark",  "#3a5f8a", 0.0, 0.70),
    ("pants",       "#6b5436", 0.0, 0.75),
    ("boot",        "#4a3728", 0.0, 0.60),
    ("straw",       "#d9b15e", 0.0, 0.80),
    ("straw_dark",  "#b8904a", 0.0, 0.80),
    ("hair",        "#4a3220", 0.0, 0.70),
    ("wood",        "#8a5f32", 0.0, 0.75),
    ("wood_dark",   "#6b4a2e", 0.0, 0.75),
    ("wood_light",  "#b58a4e", 0.0, 0.75),
    ("metal",       "#b8bcc2", 1.0, 0.35),
    ("metal_dark",  "#7a7f86", 1.0, 0.45),
    ("grass",       "#5d9148", 0.0, 0.85),
    ("grass_dark",  "#4a7a3a", 0.0, 0.85),
    ("grass_light", "#6ea254", 0.0, 0.85),
    ("soil",        "#8d6741", 0.0, 0.90),
    ("soil_dark",   "#74512f", 0.0, 0.90),
    ("leaf",        "#4f8f3f", 0.0, 0.80),
    ("leaf_dark",   "#3d7230", 0.0, 0.80),
    ("red",         "#d4483f", 0.0, 0.70),
    ("yellow",      "#e8c44a", 0.0, 0.70),
    ("pink",        "#e0809f", 0.0, 0.70),
    ("violet",      "#9a74c0", 0.0, 0.70),
    ("terracotta",  "#b5643c", 0.0, 0.85),
    ("stone",       "#a8a39a", 0.0, 0.90),
    ("stone_dark",  "#8a857c", 0.0, 0.90),
    ("water",       "#79b7d9", 0.0, 0.25),
    ("white",       "#f2f0ea", 0.0, 0.80),
    ("black",       "#2a2724", 0.0, 0.60),
]
P = None                                           # set in build()

# --------------------------------------------------------------------------- helpers

def empty(name, at=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.08
    lpm._col("COL_Rig").objects.link(e)
    e.location = at
    if parent is not None:
        set_parent(e, parent)
    return e


def set_parent(ob, parent):
    """Parent keeping the current world transform (rest pose bind)."""
    bpy.context.view_layer.update()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()


def group(name, parts, pivot=(0, 0, 0), parent=None, budget=None):
    """finish() the parts in place, move the origin onto `pivot`, parent it."""
    ob = lpm.finish(name, parts, P, budget=budget, ground=False, center=False)
    ob.data.transform(Matrix.Translation(-Vector(pivot)))
    ob.location = Vector(pivot)
    ob.rotation_mode = "XYZ"
    if parent is not None:
        set_parent(ob, parent)
    return ob


def kr(ob, f, rx=0.0, ry=0.0, rz=0.0, interp="BEZIER"):
    ob.rotation_euler = Euler((math.radians(rx), math.radians(ry), math.radians(rz)), "XYZ")
    ob.keyframe_insert("rotation_euler", frame=f)
    _interp(ob, "rotation_euler", f, interp)


def kl(ob, f, x=None, y=None, z=None, interp="BEZIER"):
    loc = list(ob.location)
    if x is not None: loc[0] = x
    if y is not None: loc[1] = y
    if z is not None: loc[2] = z
    ob.location = loc
    ob.keyframe_insert("location", frame=f)
    _interp(ob, "location", f, interp)


def ks(ob, f, s, interp="BEZIER"):
    ob.scale = (s, s, s) if not isinstance(s, (tuple, list)) else s
    ob.keyframe_insert("scale", frame=f)
    _interp(ob, "scale", f, interp)


def kvis(ob, f, visible):
    """Keyframe render + viewport visibility (used to swap a prop between hand and ground)."""
    ob.hide_render = not visible
    ob.hide_viewport = not visible
    ob.keyframe_insert("hide_render", frame=f)
    ob.keyframe_insert("hide_viewport", frame=f)
    for path in ("hide_render", "hide_viewport"):
        _interp(ob, path, f, "CONSTANT")


def _fcurves(ob):
    """Blender 5.x slotted actions: fcurves live in a channelbag, not on the action."""
    ad = ob.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    fc = getattr(act, "fcurves", None)
    if fc is not None:
        return list(fc)
    out = []
    slot = getattr(ad, "action_slot", None)
    for layer in act.layers:
        for strip in layer.strips:
            try:
                cb = strip.channelbag(slot) if slot is not None else None
            except Exception:
                cb = None
            if cb is None:
                cb = next(iter(getattr(strip, "channelbags", [])), None)
            if cb is not None:
                out.extend(cb.fcurves)
    return out


def _interp(ob, path, f, interp):
    for fc in _fcurves(ob):
        if fc.data_path != path:
            continue
        for k in fc.keyframe_points:
            if abs(k.co.x - f) < 0.5:
                k.interpolation = interp


# --------------------------------------------------------------------------- the gardener

def build_gardener():
    """Rest pose: standing, arms down. Returns the joint dict."""
    s, sd = P["skin"], P["skin_dark"]
    sh, shd = P["shirt"], P["shirt_dark"]
    pa, bo = P["pants"], P["boot"]

    root = empty("RIG_Root", (0, 0, 0))
    hips = empty("RIG_Hips", (0, 0, 0.92), root)

    # --- torso 0.92 -> 1.50, shoulders at 1.42
    chest = lpm.box("t_chest", (0.40, 0.23, 0.34), at=(0, 0, 1.16), color=sh, taper=(1.05, 1.0))
    waist = lpm.box("t_waist", (0.33, 0.21, 0.26), at=(0, 0, 0.92), color=pa, taper=(1.15, 1.07))
    bib   = lpm.box("t_bib",   (0.20, 0.025, 0.30), at=(0, -0.118, 1.10), color=pa)
    strapL = lpm.box("t_strapL", (0.05, 0.02, 0.30), at=(0.10, -0.115, 1.12), color=pa)
    strapR = lpm.box("t_strapR", (0.05, 0.02, 0.30), at=(-0.10, -0.115, 1.12), color=pa)
    collar = lpm.box("t_collar", (0.22, 0.20, 0.05), at=(0, 0, 1.46), color=shd)
    shoL  = lpm.prism("t_shoL", 6, 0.075, 0.07, at=(0.195, 0, 1.38), color=sh)
    shoR  = lpm.prism("t_shoR", 6, 0.075, 0.07, at=(-0.195, 0, 1.38), color=sh)
    torso = group("G_Torso", [chest, waist, bib, strapL, strapR, collar, shoL, shoR], (0, 0, 0.92), hips)

    # --- head 1.50 -> 1.86 (neck, head, face, straw hat)
    neck = lpm.prism("h_neck", 6, 0.055, 0.09, at=(0, 0, 1.48), color=s)
    skull = lpm.box("h_skull", (0.21, 0.20, 0.23), at=(0, 0, 1.56), color=s, taper=(0.92, 0.92))
    jaw   = lpm.box("h_jaw", (0.17, 0.17, 0.05), at=(0, 0.005, 1.54), color=sd)
    nose  = lpm.sweep("h_nose", [(-0.022, 0), (0.022, 0), (0.0, 0.035)], depth=0.05,
                      at=(0, -0.112, 1.655), color=sd)
    eyeL  = lpm.box("h_eyeL", (0.030, 0.012, 0.022), at=(0.055, -0.100, 1.695), color=P["black"])
    eyeR  = lpm.box("h_eyeR", (0.030, 0.012, 0.022), at=(-0.055, -0.100, 1.695), color=P["black"])
    browL = lpm.box("h_browL", (0.040, 0.012, 0.012), at=(0.055, -0.101, 1.726), color=P["hair"])
    browR = lpm.box("h_browR", (0.040, 0.012, 0.012), at=(-0.055, -0.101, 1.726), color=P["hair"])
    mouth = lpm.box("h_mouth", (0.050, 0.012, 0.012), at=(0, -0.090, 1.600), color=P["black"])
    hair  = lpm.box("h_hair", (0.215, 0.205, 0.05), at=(0, 0.01, 1.745), color=P["hair"], taper=(0.95, 0.95))
    brim  = lpm.prism("h_brim", 10, 0.28, 0.022, at=(0, 0.01, 1.775), color=P["straw"])
    crown = lpm.lathe("h_crown", [(0.125, 0), (0.125, 0.015), (0.115, 0.075), (0.085, 0.10)],
                      segments=10, at=(0, 0.01, 1.790), color=P["straw"])
    band  = lpm.prism("h_band", 10, 0.129, 0.028, at=(0, 0.01, 1.800), color=P["wood_dark"])
    head = group("G_Head", [neck, skull, jaw, nose, eyeL, eyeR, browL, browR, mouth, hair, brim, crown, band],
                 (0, 0, 1.50), torso)

    # --- arms (shoulder 1.42, elbow 1.14, wrist 0.88)
    joints = {"root": root, "hips": hips, "torso": torso, "head": head}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        up = lpm.prism(f"a_up{side}", 6, 0.052, 0.30, at=(sx * 0.235, 0, 1.12), color=sh, radius_top=0.058)
        cuf = lpm.prism(f"a_cuf{side}", 6, 0.056, 0.035, at=(sx * 0.235, 0, 1.125), color=shd)
        joints[f"arm{side}"] = group(f"G_ArmUp{side}", [up, cuf], (sx * 0.235, 0, 1.42), torso)

        lo = lpm.prism(f"a_lo{side}", 6, 0.044, 0.26, at=(sx * 0.235, 0, 0.88), color=s, radius_top=0.050)
        palm = lpm.box(f"a_palm{side}", (0.085, 0.075, 0.095), at=(sx * 0.235, -0.005, 0.785), color=s)
        thumb = lpm.box(f"a_thumb{side}", (0.028, 0.028, 0.055), at=(sx * 0.282, -0.005, 0.805), color=sd)
        joints[f"fore{side}"] = group(f"G_ArmLo{side}", [lo, palm, thumb], (sx * 0.235, 0, 1.14),
                                      joints[f"arm{side}"])

    # --- legs (hip 0.92, knee 0.50, ankle 0.10)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        th = lpm.prism(f"l_th{side}", 6, 0.078, 0.44, at=(sx * 0.105, 0, 0.48), color=pa, radius_top=0.085)
        joints[f"leg{side}"] = group(f"G_LegUp{side}", [th], (sx * 0.105, 0, 0.92), hips)

        sk = lpm.prism(f"l_sk{side}", 6, 0.058, 0.42, at=(sx * 0.105, 0, 0.10), color=pa, radius_top=0.070)
        boot = lpm.box(f"l_boot{side}", (0.125, 0.235, 0.095), at=(sx * 0.105, -0.035, 0.0), color=bo)
        toe = lpm.box(f"l_toe{side}", (0.115, 0.07, 0.06), at=(sx * 0.105, -0.145, 0.0), color=bo, taper=(0.9, 0.7))
        joints[f"shin{side}"] = group(f"G_LegLo{side}", [sk, boot, toe], (sx * 0.105, 0, 0.50),
                                      joints[f"leg{side}"])
    return joints


# --------------------------------------------------------------------------- props

def _dup(ob, name):
    d = ob.copy()
    d.data = ob.data.copy()
    d.name = name
    d.data.name = name
    for c in ob.users_collection:
        c.objects.link(d)
    return d


def build_can():
    """Watering can, origin at the handle grip. Returns the object (rest: upright)."""
    w, m, md = P["metal"], P["metal_dark"], P["metal"]
    body = lpm.lathe("c_body", [(0.0, 0), (0.105, 0), (0.115, 0.03), (0.115, 0.20), (0.100, 0.235), (0.070, 0.245), (0.0, 0.245)],
                     segments=10, at=(0, 0, 0), color=P["metal"])
    rim = lpm.prism("c_rim", 10, 0.077, 0.018, at=(0, 0, 0.243), color=md)
    # spout: tapered prism tilted forward
    spout = lpm.prism("c_spout", 6, 0.040, 0.42, at=(0, 0, 0), color=P["metal"], radius_top=0.028)
    lpm.rotate(spout, 62, "X", about=(0, 0, 0))
    lpm.move(spout, 0, -0.085, 0.085)
    nozzle = lpm.prism("c_nozzle", 8, 0.038, 0.035, at=(0, -0.456, 0.282), color=md)
    lpm.rotate(nozzle, 62, "X", about=(0, -0.456, 0.282))
    # handle arc over the top
    arcs = []
    for i in range(5):
        a0 = math.pi * i / 5
        a1 = math.pi * (i + 1) / 5
        r = 0.115
        x0, z0 = r * math.cos(a0), r * math.sin(a0)
        x1, z1 = r * math.cos(a1), r * math.sin(a1)
        seg = lpm.box(f"c_h{i}", (math.hypot(x1 - x0, z1 - z0) + 0.012, 0.030, 0.026), at=(0, 0, 0), color=md)
        lpm.rotate(seg, math.degrees(math.atan2(z1 - z0, x1 - x0)), "Y", about=(0, 0, 0))
        lpm.move(seg, (x0 + x1) / 2, 0.0, 0.252 + (z0 + z1) / 2)
        arcs.append(seg)
    band = lpm.prism("c_band", 10, 0.118, 0.022, at=(0, 0, 0.145), color=md)
    can = group("PR_Can", [body, rim, spout, nozzle, band] + arcs, (0, 0, 0.37), budget=900)
    return can


def build_shovel():
    """Shovel, origin at the upper grip. Rest: blade down at z=0."""
    shaft = lpm.prism("s_shaft", 6, 0.024, 0.60, at=(0, 0, 0.22), color=P["wood_light"], radius_top=0.027)
    grip = lpm.box("s_grip", (0.13, 0.035, 0.035), at=(0, 0, 0.82), color=P["wood_dark"])
    gripL = lpm.box("s_gripL", (0.030, 0.035, 0.075), at=(-0.05, 0, 0.745), color=P["wood_dark"])
    gripR = lpm.box("s_gripR", (0.030, 0.035, 0.075), at=(0.05, 0, 0.745), color=P["wood_dark"])
    socket = lpm.prism("s_socket", 6, 0.030, 0.10, at=(0, 0, 0.20), color=P["metal_dark"])
    blade = lpm.sweep("s_blade", [(-0.105, 0.22), (0.105, 0.22), (0.095, 0.06), (0.045, -0.005), (-0.045, -0.005), (-0.095, 0.06)],
                      depth=0.016, at=(0, 0, 0.0), color=P["metal"])
    return group("PR_Shovel", [shaft, grip, gripL, gripR, socket, blade], (0, 0, 0.82), budget=600)


def build_flower(name, color, scale=1.0, petals=6, at=(0, 0, 0)):
    """Stem + two leaves + petal ring + centre. Origin at the base."""
    c = P[color]
    st = lpm.prism(f"{name}_stem", 5, 0.014 * scale, 0.30 * scale, at=(0, 0, 0), color=P["leaf_dark"])
    lv1 = lpm.sweep(f"{name}_lv1", [(0, 0), (0.09, 0.03), (0.13, 0.085), (0.055, 0.075), (0.0, 0.035)],
                    depth=0.008, at=(0, 0, 0.10 * scale), color=P["leaf"])
    lv2 = lpm.sweep(f"{name}_lv2", [(0, 0), (-0.09, 0.03), (-0.13, 0.085), (-0.055, 0.075), (0.0, 0.035)],
                    depth=0.008, at=(0, 0, 0.17 * scale), color=P["leaf"])
    for lv in (lv1, lv2):
        lpm.scale(lv, scale, 1.0, scale, about=(0, 0, 0))
    parts = [st, lv1, lv2]
    for i in range(petals):
        a = 2 * math.pi * i / petals
        pe = lpm.box(f"{name}_p{i}", (0.055 * scale, 0.055 * scale, 0.014 * scale), at=(0, 0, 0), color=c, taper=(0.55, 0.55))
        lpm.move(pe, 0.055 * scale * math.cos(a), 0.055 * scale * math.sin(a), 0.295 * scale)
        lpm.rotate(pe, math.degrees(a), "Z", about=(0.055 * scale * math.cos(a), 0.055 * scale * math.sin(a), 0.30 * scale))
        parts.append(pe)
    core = lpm.lathe(f"{name}_core", [(0.030 * scale, 0), (0.034 * scale, 0.012 * scale), (0.022 * scale, 0.030 * scale)],
                     segments=6, at=(0, 0, 0.300 * scale), color=P["yellow"])
    parts.append(core)
    ob = group(name, parts, (0, 0, 0))
    ob.location = Vector(at)
    return ob


# --------------------------------------------------------------------------- environment

def build_env():
    g, gd, gl = P["grass"], P["grass_dark"], P["grass_light"]
    # ground + patches (patches sit 3 mm proud: never coplanar)
    ground = lpm.box("e_ground", (44, 44, 0.06), at=(0, 2, -0.06), color=g)
    patches = []
    for i, (px, py, r, col) in enumerate([(-2.4, 1.2, 1.5, gd), (2.9, 1.0, 1.7, gl), (-4.6, -1.2, 1.3, gd),
                                          (4.4, -1.6, 1.4, gd), (0.2, 3.4, 2.1, gl), (-6.0, 2.6, 1.8, gl)]):
        pt = lpm.prism(f"e_patch{i}", 7, r, 0.012, at=(px, py, 0.0), color=col, rotate=i * 17)
        patches.append(pt)
    hills = []
    for i, (hx, hr, hh) in enumerate([(-13, 7.0, 2.2), (6, 9.0, 2.8), (17, 6.0, 1.8)]):
        hl = lpm.lathe(f"e_hill{i}", [(hr, 0), (hr * 0.72, hh * 0.45), (hr * 0.38, hh * 0.82), (0, hh)],
                       segments=8, at=(hx, 19 + i * 1.5, 0), color=gd if i % 2 else gl)
        hills.append(hl)
    group("ENV_Ground", [ground] + patches + hills)

    # flower bed: soil slab + mounds, 2.9 x 1.25 centred on (0.6, -0.85)
    # tilled rows: a grid box whose top strips alternate between the two browns
    soil = lpm.grid_box("e_soil", (2.9, 1.46, 0.16), at=(0.6, -0.88, 0.0), color=P["soil"], nx=10, nz=1)
    lpm.paint(soil, P["soil_dark"], where=lambda c, n, i: n.z > 0.5 and int((c.x + 10.0) / 0.29) % 2 == 0)
    edges = []
    for i in range(4):
        ex = -0.85 + i * 0.95
        plank = lpm.box(f"e_plank{i}", (0.95, 0.045, 0.19), at=(ex + 0.475, -1.61, 0.0), color=P["wood"])
        edges.append(plank)
    mounds = []
    for i, (mx, my, mr) in enumerate([(-0.5, -0.55, 0.26), (1.3, -1.15, 0.30), (1.9, -0.5, 0.22)]):
        md = lpm.lathe(f"e_mound{i}", [(mr, 0), (mr * 0.6, 0.045), (0, 0.075)], segments=6, at=(mx, my, 0.16), color=P["soil_dark"])
        mounds.append(md)
    hole = lpm.lathe("e_hole", [(0.20, 0.162), (0.16, 0.125), (0.09, 0.105)], segments=7, at=(HOLE[0], HOLE[1], 0), color=P["soil_dark"])
    group("ENV_Bed", [soil, hole] + edges + mounds)

    # stone path leading in from the left
    slabs = []
    for i in range(8):
        sx = -5.6 + i * 0.68
        sl = lpm.prism(f"e_slab{i}", 6, 0.30, 0.035, at=(sx, 0.58 + (0.09 if i % 2 else -0.07), 0.0),
                       color=P["stone"] if i % 2 else P["stone_dark"], rotate=i * 23)
        slabs.append(sl)
    group("ENV_Path", slabs)

    # fence behind, y = 2.9
    fence = []
    for i in range(13):
        fx = -6.0 + i
        post = lpm.box(f"e_post{i}", (0.10, 0.10, 1.05), at=(fx, 2.9, 0.0), color=P["wood_dark"], taper=(0.85, 0.85))
        cap = lpm.prism(f"e_cap{i}", 4, 0.085, 0.055, at=(fx, 2.9, 1.05), color=P["wood"], rotate=45)
        fence += [post, cap]
    for k, z in ((0, 0.42), (1, 0.78)):
        rail = lpm.box(f"e_rail{k}", (13.0, 0.045, 0.11), at=(0.0, 2.93, z), color=P["wood"])
        fence.append(rail)
    group("ENV_Fence", fence)

    # tree, bushes, pots
    trees = []
    for i, (tx, ty, ts) in enumerate([(-4.3, 2.1, 1.0), (5.3, 2.4, 0.78)]):
        tr = lpm.prism(f"e_trunk{i}", 7, 0.19 * ts, 1.5 * ts, at=(tx, ty, 0), color=P["wood_dark"], radius_top=0.14 * ts)
        trees.append(tr)
        for k, (cz, cr, ch) in enumerate([(1.25, 1.00, 1.15), (2.05, 0.78, 1.00), (2.70, 0.50, 0.80)]):
            cone = lpm.lathe(f"e_leaf{i}{k}", [(cr * ts, 0), (cr * 0.74 * ts, ch * 0.42 * ts), (cr * 0.42 * ts, ch * 0.78 * ts), (0, ch * ts)],
                             segments=8, at=(tx, ty, cz * ts), color=P["leaf"] if k % 2 else P["leaf_dark"])
            trees.append(cone)
    bushes = []
    for i, (bx, by, br) in enumerate([(3.1, 1.5, 0.52), (-2.6, 2.2, 0.44), (-5.6, 1.1, 0.38), (2.0, 2.3, 0.34)]):
        bs = lpm.lathe(f"e_bush{i}", [(br, 0), (br * 1.05, br * 0.45), (br * 0.80, br * 1.05), (br * 0.40, br * 1.45), (0, br * 1.65)],
                       segments=7, at=(bx, by, 0), color=P["leaf_dark"] if i % 2 else P["leaf"])
        bushes.append(bs)
    group("ENV_Plants", trees + bushes)

    pots = []
    for i, (px, py, pr) in enumerate([(2.45, -0.45, 0.22), (2.95, -0.05, 0.17)]):
        pot = lpm.lathe(f"e_pot{i}", [(pr * 0.65, 0), (pr * 0.72, 0.02), (pr * 0.92, pr * 1.3), (pr, pr * 1.45), (pr * 0.88, pr * 1.5), (pr * 0.80, pr * 0.35)],
                        segments=8, at=(px, py, 0), color=P["terracotta"])
        dirt = lpm.prism(f"e_dirt{i}", 8, pr * 0.84, 0.02, at=(px, py, pr * 1.32), color=P["soil_dark"])
        pots += [pot, dirt]
    group("ENV_Pots", pots)

    # flowers already in the bed
    for i, (fx, fy, col, sc) in enumerate([(-0.62, -0.70, "red", 0.9), (-0.30, -1.25, "yellow", 0.8),
                                           (1.50, -0.60, "pink", 0.95), (1.95, -1.20, "violet", 0.85),
                                           (1.05, -1.35, "red", 0.75)]):
        build_flower(f"FL_Bed{i}", col, scale=sc, at=(fx, fy, 0.16))
    build_flower("FL_Pot0", "pink", scale=0.7, at=(2.45, -0.45, 0.29))


def build_water():
    """A ring of droplets that fall from the can's spout while watering."""
    drops = []
    for i in range(12):
        d = lpm.lathe(f"w_d{i}", [(0, 0), (0.022, 0.022), (0.016, 0.05), (0, 0.075)], segments=5, at=(0, 0, 0), color=P["water"])
        ob = group(f"WD_{i}", [d], (0, 0, 0))
        ob.hide_render = True
        drops.append(ob)
    return drops


def build_butterfly(name):
    body = lpm.prism(f"{name}_b", 5, 0.022, 0.15, at=(0, 0, 0), color=P["black"])
    lpm.rotate(body, 90, "X", about=(0, 0, 0))
    core = group(f"{name}", [body], (0, 0, 0))
    wings = []
    for side, sx in (("L", 1.0), ("R", -1.0)):
        w1 = lpm.sweep(f"{name}_w{side}", [(0.01, 0.015), (0.075, 0.075), (0.125, 0.055), (0.115, -0.005),
                                           (0.085, -0.025), (0.100, -0.080), (0.055, -0.100), (0.015, -0.050)],
                       depth=0.005, at=(0, 0, 0), color=P["white"], axis="z")
        lpm.paint(w1, P["yellow"], where=lambda c, n, i: abs(c.x) > 0.085)
        if sx < 0:
            lpm.scale(w1, -1, 1, 1, about=(0, 0, 0))
            w1.data.flip_normals()
        wg = group(f"{name}_W{side}", [w1], (0, 0, 0), core)
        wings.append(wg)
    return core, wings


# --------------------------------------------------------------------------- world, light, cameras

def build_world_and_light():
    w = bpy.data.worlds.new("W_Garden")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = nt.nodes.new("ShaderNodeTexSky")
    for st in ("MULTIPLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
        try:
            sky.sky_type = st
            break
        except TypeError:
            continue
    for attr, val in (("sun_elevation", math.radians(38)), ("sun_rotation", math.radians(205)),
                      ("sun_disc", False), ("air_density", 1.0), ("dust_density", 0.8)):
        try:
            setattr(sky, attr, val)
        except Exception:
            pass
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.28

    sun_data = bpy.data.lights.new("L_Sun", "SUN")
    sun_data.energy = 4.6
    sun_data.angle = math.radians(12)
    sun_data.color = (1.0, 0.95, 0.86)
    sun = bpy.data.objects.new("L_Sun", sun_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.rotation_euler = Euler((math.radians(52), 0, math.radians(38)), "XYZ")

    fill_data = bpy.data.lights.new("L_Fill", "AREA")
    fill_data.energy = 90
    fill_data.size = 6.0
    fill_data.color = (1.0, 0.97, 0.92)
    fill = bpy.data.objects.new("L_Fill", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (-4.5, -6.0, 4.2)
    fill.rotation_euler = Euler((math.radians(52), 0, math.radians(-38)), "XYZ")
    return sun


def camera(name, loc, look, lens=40.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    tgt = empty(f"{name}_TGT", look)
    tgt.parent = None
    c = cam.constraints.new("TRACK_TO")
    c.target = tgt
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return cam, tgt


def build_cameras():
    cams = {}
    cams["A"], ta = camera("CAM_A", (-3.6, -6.4, 2.95), (-1.2, 0.2, 1.05), lens=42)
    cams["B"], tb = camera("CAM_B", (-2.70, -4.75, 2.15), (0.30, -0.45, 0.85), lens=44)
    cams["C"], tc = camera("CAM_C", (3.35, -5.40, 2.15), (0.45, -0.55, 0.80), lens=40)

    # slow dollies + pans (one keyframe pair per shot)
    kl(cams["A"], 1, -3.6, -6.4, 2.95); kl(ta, 1, -1.2, 0.2, 1.05)
    kl(cams["A"], 168, -2.3, -6.15, 2.75); kl(ta, 168, 0.35, 0.05, 1.00)
    kl(cams["B"], 169, -2.70, -4.75, 2.15); kl(tb, 169, 0.30, -0.45, 0.85)
    kl(cams["B"], 336, -1.75, -4.95, 1.95); kl(tb, 336, 0.40, -0.60, 0.70)
    kl(cams["C"], 337, 3.35, -5.40, 2.15); kl(tc, 337, 0.45, -0.55, 0.80)
    kl(cams["C"], 480, -1.05, -4.85, 2.15); kl(tc, 480, 0.12, -0.66, 0.78)

    sc = bpy.context.scene
    sc.camera = cams["A"]
    for f, key in ((1, "A"), (169, "B"), (337, "C")):
        mk = sc.timeline_markers.new(f"SHOT_{key}", frame=f)
        mk.camera = cams[key]
    return cams


# --------------------------------------------------------------------------- posing

ROT = {"torso": "torso", "head": "head", "aL": "armL", "aR": "armR", "fL": "foreL", "fR": "foreR",
       "lL": "legL", "lR": "legR", "sL": "shinL", "sR": "shinR"}


def pose(J, f, interp="BEZIER", **kw):
    """pose(J, 120, torso=(-18, 0, 6), aR=-40, root=(0.3, 0.45), rz=0, hz=0.92)"""
    for k, v in kw.items():
        if k == "root":
            kl(J["root"], f, v[0], v[1], v[2] if len(v) > 2 else 0.0, interp=interp)
        elif k == "rz":
            kr(J["root"], f, 0, 0, v, interp=interp)
        elif k == "hz":
            kl(J["hips"], f, 0, 0, v, interp=interp)
        elif k == "hips":
            kr(J["hips"], f, *(v if isinstance(v, (tuple, list)) else (v, 0, 0)), interp=interp)
        elif k in ROT:
            t = v if isinstance(v, (tuple, list)) else (v, 0, 0)
            kr(J[ROT[k]], f, *t, interp=interp)
        else:
            raise KeyError(k)


REST = dict(torso=(0, 0, 0), head=(0, 0, 0), aL=(0, 0, 4), aR=(0, 0, -4), fL=(0, 0, 0), fR=(0, 0, 0),
            lL=(0, 0, 0), lR=(0, 0, 0), sL=(0, 0, 0), sR=(0, 0, 0), hz=0.92)


def walk(J, f0, f1, x0, x1, y, period=32.0, carry=True, prop_up=None):
    """Keyframe a walk cycle between two frames; root moves x0 -> x1 at y, facing +X (rz=90)."""
    n = int(f1 - f0)
    kr(J["root"], f0, 0, 0, 90); kr(J["root"], f1, 0, 0, 90)
    step = 0
    f = f0
    while f <= f1:
        t = (f - f0) / max(n, 1)
        x = x0 + (x1 - x0) * t
        ph = ((f - f0) % period) / period                      # 0 .. 1
        a = 2 * math.pi * ph
        swing = math.sin(a)
        lift = abs(math.cos(a))
        kl(J["root"], f, x, y, 0.0, interp="LINEAR")
        kl(J["hips"], f, 0, 0, 0.92 - 0.018 + 0.030 * (1 - lift), interp="BEZIER")
        kr(J["hips"], f, 0, 0, -5 * swing)
        tor = 7 - 2 * math.cos(a)
        kr(J["torso"], f, tor, 0, 5 * swing)
        kr(J["head"], f, -2 - tor, 0, -3 * swing)
        # legs: left leads on swing>0
        kr(J["legL"], f, -26 * swing - 2, 0, 0)
        kr(J["shinL"], f, max(0.0, 30 * -swing) + 6 + 14 * (1 - lift), 0, 0)
        kr(J["legR"], f, 26 * swing - 2, 0, 0)
        kr(J["shinR"], f, max(0.0, 30 * swing) + 6 + 14 * (1 - lift), 0, 0)
        # arms (world angles, converted to local): left swings freely, right carries the can
        awl, fwl = -8 + 26 * swing, -24 + 26 * swing - 8 * max(0.0, swing)
        kr(J["armL"], f, awl - tor, 0, 5)
        kr(J["foreL"], f, fwl - awl, 0, 0)
        if carry:
            awr, fwr = -10 - 7 * swing, -28 - 5 * swing
            kr(J["armR"], f, awr - tor, 0, -7)
            kr(J["foreR"], f, fwr - awr, 0, 0)
            if prop_up is not None:
                aim_dir(prop_up, int(round(f)), DOWN, DOWN)
        else:
            awr, fwr = -8 - 26 * swing, -24 - 26 * swing + 8 * min(0.0, swing)
            kr(J["armR"], f, awr - tor, 0, -5)
            kr(J["foreR"], f, fwr - awr, 0, 0)
        step += 1
        f += period / 8.0
    return x1


# --------------------------------------------------------------------------- exact prop aiming

def _bind_frame(ob, dg):
    """The 4x4 frame the object's own local matrix is expressed in (parent world x parent inverse)."""
    par = ob.parent.evaluated_get(dg).matrix_world
    return par @ ob.matrix_parent_inverse


def aim_dir(ob, f, local_vec, world_dir):
    """Key ob's local rotation at frame f so that `local_vec` points along `world_dir` in world space.
    Minimal rotation, so a shaft gets no parasitic roll. The arm keys for frame f must exist already."""
    sc = bpy.context.scene
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    M3 = _bind_frame(ob, dg).to_3x3()
    v = Vector(local_vec)
    u = M3.inverted() @ Vector(world_dir)
    ob.rotation_euler = v.rotation_difference(u).to_euler("XYZ")
    ob.keyframe_insert("rotation_euler", frame=f)
    _interp(ob, "rotation_euler", f, "BEZIER")


def aim_at(ob, f, local_vec, target):
    """Same, but aim `local_vec` at a world point (the dig spot, the seedling, ...)."""
    sc = bpy.context.scene
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    M = _bind_frame(ob, dg)
    origin = M @ Vector(ob.location)
    aim_dir(ob, f, local_vec, Vector(target) - origin)


def aim_tip_z(ob, f, local_vec, tip_z, toward):
    """Aim so the tip sits exactly at height `tip_z` while pointing toward the (x, y) of `toward`.
    The reach is whatever the arm allows - height errors read, a few cm of reach do not."""
    sc = bpy.context.scene
    sc.frame_set(f)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    origin = _bind_frame(ob, dg) @ Vector(ob.location)
    L = Vector(local_vec).length
    cos = max(-1.0, min(1.0, (origin.z - tip_z) / L))
    sin = math.sqrt(max(0.0, 1.0 - cos * cos))
    h = Vector((toward[0] - origin.x, toward[1] - origin.y, 0))
    h = h.normalized() if h.length > 1e-6 else Vector((0, -1, 0))
    aim_dir(ob, f, local_vec, Vector((h.x * sin, h.y * sin, -cos)))


SHAFT = (0, 0, -0.825)          # grip -> blade tip, in the shovel's local frame
SPOUT = (0, -0.487, -0.072)     # grip -> spout tip, in the can's local frame
DOWN = (0, 0, -1)


# --------------------------------------------------------------------------- storyboard
# 24 fps, 480 frames = 20 s
#   1- 88  walk in along the path, watering can in the right hand
#  88-130  stop, turn to the bed, step up to it
# 130-166  set the can down, reach for the shovel
# 166-268  three digging strokes
# 268-286  plant the shovel back in the soil
# 286-330  squat, put the seedling in the hole, pat the soil
# 330-356  pick the can back up
# 356-432  water: can tilts, droplets fall, the flower grows and blooms
# 432-480  set the can down, step back, wipe the brow, look at the flower

WORK = (0.35, 0.18)            # where he works, facing -Y
PATH_Y = 0.58
CAN_GND = (-0.30, 0.15, 0.0)
SHOVEL_GND = (1.05, -0.19, 1.23)       # origin = grip, blade tip ends in the soil
HOLE = (0.00, -0.76, 0.16)


def animate(J, props):
    """All arm/head angles below are WORLD angles (deg): negative = limb swings forward (-Y),
    positive on the torso/head = leaning or nodding forward. The helpers subtract the parent's
    angle, because arms and head hang off the torso."""
    can_h, can_g, sho_h, sho_g, clod, seedling, drops, bflies = (
        props["can_h"], props["can_g"], props["sho_h"], props["sho_g"],
        props["clod"], props["seedling"], props["drops"], props["bflies"])
    DX, DY = HOLE[0], HOLE[1]
    cur = {"torso": 0.0}

    def body(f, torso, head_w, hz, lu=-3, ll=5, twist=0.0):
        cur["torso"] = torso
        pose(J, f, torso=(torso, 0, twist), head=(head_w - torso, 0, -twist * 0.6), hz=hz,
             lL=(lu, 0, 0), sL=(ll, 0, 0), lR=(lu, 0, 0), sR=(ll, 0, 0))

    def arm(f, side, aw, fw, rz=8):
        t = cur["torso"]
        kr(J["arm" + side], f, aw - t, 0, rz)
        kr(J["fore" + side], f, fw - aw, 0, 0)

    def arms(f, awl, fwl, awr, fwr, rzl=8, rzr=-8):
        arm(f, "L", awl, fwl, rzl)
        arm(f, "R", awr, fwr, rzr)

    # ---------------- 1-88  walk in along the path, can in the right hand
    walk(J, 1, 88, -2.96, WORK[0], PATH_Y, period=32.0, carry=True, prop_up=can_h)
    kvis(can_h, 1, True); kvis(can_g, 1, False)
    kvis(sho_h, 1, False); kvis(sho_g, 1, True)
    kvis(clod, 1, False)

    # ---------------- 88-130  stop, turn to the bed, step up to it
    pose(J, 104, root=(WORK[0], PATH_Y, 0.0), rz=90)
    body(104, 5, -2, 0.92, -2, 4); arms(104, -8, -24, -10, -26)
    aim_dir(can_h, 104, DOWN, DOWN)
    pose(J, 122, root=(WORK[0], 0.30, 0.0), rz=12)
    body(122, 7, 0, 0.905, -15, 18); arms(122, -10, -26, -11, -27)
    aim_dir(can_h, 122, DOWN, DOWN)
    pose(J, 130, root=(WORK[0], WORK[1], 0.0), rz=0)
    body(130, 4, 8, 0.92, -3, 5); arms(130, -8, -22, -9, -24)
    aim_dir(can_h, 130, DOWN, DOWN)

    # keep him planted at the work spot between beats (Bezier between distant keys drifts)
    for f in (142, 154, 164, 176, 200, 234, 252, 268, 278, 290, 306, 320, 330, 338, 348, 366, 384, 412, 424, 436, 446):
        kl(J["root"], f, WORK[0], WORK[1], 0.0)
        kr(J["root"], f, 0, 0, 0)

    # ---------------- 130-154  squat, set the can down on the grass beside him
    body(142, 42, 26, 0.78, -46, 66); arms(142, -8, -16, -3, -7, rzl=14, rzr=-40)
    aim_dir(can_h, 142, DOWN, DOWN)
    kvis(can_h, 143, False); kvis(can_g, 143, True)
    body(154, 8, 6, 0.90, -8, 12); arms(154, -8, -22, -9, -23)

    # ---------------- 154-166  reach left, pull the shovel out of the soil
    body(164, 18, 22, 0.87, -16, 22, twist=12); arms(164, -16, -34, -36, -58, rzl=20, rzr=-14)
    aim_tip_z(sho_h, 164, SHAFT, 0.02, (DX + 0.55, DY + 0.10))
    kvis(sho_h, 165, True); kvis(sho_g, 165, False)

    # ---------------- 166-268  three digging strokes (34 frames each)
    for stroke in range(3):
        fs = 166 + stroke * 34
        body(fs, 14, 24, 0.90, -10, 16); arms(fs, -14, -32, -38, -58, rzl=16)
        aim_tip_z(sho_h, fs, SHAFT, 0.26, (DX, DY))
        body(fs + 9, 6, 16, 0.92, -6, 10); arms(fs + 9, -22, -42, -58, -78, rzl=18)
        aim_at(sho_h, fs + 9, SHAFT, (DX, DY + 0.45, 1.15))
        body(fs + 18, 32, 30, 0.85, -22, 34); arms(fs + 18, 2, -26, -24, -62, rzl=20)
        aim_tip_z(sho_h, fs + 18, SHAFT, -0.02, (DX, DY))
        body(fs + 26, 16, 26, 0.90, -12, 18); arms(fs + 26, -18, -38, -44, -68, rzl=18)
        aim_tip_z(sho_h, fs + 26, SHAFT, 0.34, (DX, DY))
        body(fs + 32, 12, 16, 0.91, -8, 12, twist=-16); arms(fs + 32, -26, -46, -36, -48, rzl=22, rzr=-26)
        aim_tip_z(sho_h, fs + 32, SHAFT, 0.42, (DX - 0.55, DY + 0.22))
        kvis(clod, fs + 19, True)
        kvis(clod, fs + 31, False)

    # ---------------- 268-290  plant the shovel back in the soil
    body(278, 18, 22, 0.87, -16, 22, twist=12); arms(278, -16, -34, -36, -58, rzl=20, rzr=-14)
    aim_tip_z(sho_h, 278, SHAFT, 0.02, (DX + 0.55, DY + 0.10))
    kvis(sho_h, 279, False); kvis(sho_g, 279, True)
    body(290, 6, 10, 0.92, -4, 6); arms(290, -8, -20, -9, -21)

    # ---------------- 290-342  squat, put the seedling in the hole, pat the soil
    ks(seedling, 1, 0.001); kvis(seedling, 1, False)
    body(306, 52, 30, 0.56, -66, 92); arms(306, -35, -45, -35, -45, rzl=16, rzr=-16)
    kvis(seedling, 312, True); ks(seedling, 312, 0.001)
    body(320, 65, 34, 0.52, -70, 96); arms(320, -45, -55, -45, -55, rzl=16, rzr=-16)
    ks(seedling, 322, 0.34)
    for fp in (326, 334):
        body(fp, 68, 36, 0.52, -70, 96); arms(fp, -50, -62, -50, -62, rzl=16, rzr=-16)
        body(fp + 4, 62, 32, 0.53, -69, 94); arms(fp + 4, -42, -52, -42, -52, rzl=16, rzr=-16)

    # ---------------- 342-366  stand up, pick the can back up
    body(348, 42, 26, 0.78, -46, 66); arms(348, -8, -16, -3, -7, rzl=14, rzr=-40)
    aim_dir(can_h, 348, DOWN, DOWN)
    kvis(can_g, 349, False); kvis(can_h, 349, True)
    body(366, 8, 10, 0.91, -8, 12); arms(366, -8, -20, -18, -34)
    aim_dir(can_h, 366, DOWN, DOWN)

    # ---------------- 366-436  water the new flower
    body(384, 26, 30, 0.88, -16, 24); arms(384, -16, -34, -55, -80, rzr=-12)
    aim_at(can_h, 384, SPOUT, (DX, DY, 0.30))
    body(398, 27, 31, 0.88, -16, 24); arms(398, -17, -35, -57, -82, rzr=-12)
    aim_at(can_h, 398, SPOUT, (DX, DY, 0.26))
    body(412, 26, 30, 0.88, -16, 24); arms(412, -18, -36, -58, -84, rzr=-12)
    aim_at(can_h, 412, SPOUT, (DX, DY, 0.30))
    body(424, 14, 20, 0.91, -8, 12); arms(424, -12, -26, -26, -40)
    aim_dir(can_h, 424, DOWN, (0, -0.35, -1))
    body(436, 6, 12, 0.92, -4, 6); arms(436, -8, -20, -12, -26)
    aim_dir(can_h, 436, DOWN, DOWN)
    ks(seedling, 374, 0.36)
    ks(seedling, 416, 1.06)
    ks(seedling, 426, 0.97)
    ks(seedling, 438, 1.0)
    for k, f in enumerate(range(428, 486, 12)):          # it sways in the breeze once it is up
        kr(seedling, f, 3.5 * (1 if k % 2 else -1), 0, 2.0 * (1 if k % 2 else -1))

    # ---------------- 436-480  can down, step back, wipe the brow, look at it
    body(446, 42, 26, 0.78, -46, 66); arms(446, -8, -16, -3, -7, rzl=14, rzr=-40)
    aim_dir(can_h, 446, DOWN, DOWN)
    kvis(can_h, 447, False); kvis(can_g, 447, True)
    pose(J, 458, root=(WORK[0] - 0.08, WORK[1] + 0.40, 0.0), rz=-5)
    body(458, 8, 8, 0.92, 10, 14); arms(458, -8, -20, -9, -21)
    pose(J, 468, root=(WORK[0] - 0.12, WORK[1] + 0.50, 0.0), rz=-8)
    body(468, 2, -8, 0.925, -2, 4); arms(468, -8, -20, -100, -185, rzr=-18)
    pose(J, 480, root=(WORK[0] - 0.12, WORK[1] + 0.50, 0.0), rz=-8)
    body(480, 3, 16, 0.92, -2, 4); arms(480, -10, -24, -14, -30)

    # ---------------- butterflies from frame 410
    for i, (core, wings) in enumerate(bflies):
        r, cz, ph = 0.55 + 0.22 * i, 0.72 + 0.20 * i, i * 2.1
        kvis(core, 1, False)
        for w in wings:
            kvis(w, 1, False)
        kvis(core, 410 + i * 14, True)
        for w in wings:
            kvis(w, 410 + i * 14, True)
        for f in range(410 + i * 14, 486, 6):
            a = ph + (f - 410) * 0.055
            kl(core, f, DX + r * math.cos(a), DY + r * 0.8 * math.sin(a),
               cz + 0.12 * math.sin(a * 2.3), interp="BEZIER")
            kr(core, f, 0, 0, math.degrees(a) + 90)
        for f in range(410 + i * 14, 486, 2):
            up = (f // 2) % 2 == 0
            for si, w in enumerate(wings):
                kr(w, f, 0, (62 if up else 8) * (1 if si == 0 else -1), 0, interp="BEZIER")

    # ---------------- water droplets: spawned at the real spout tip of that very frame
    target = Vector((DX, DY, 0.20))
    sc = bpy.context.scene
    for i, d in enumerate(drops):
        kvis(d, 1, False)
        span, t0 = 13, 374 + i * 3
        while t0 < 420:
            sc.frame_set(t0)
            bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            tip = can_h.evaluated_get(dg).matrix_world @ Vector(SPOUT)
            f0, f1 = t0, t0 + span
            jx = (i % 3 - 1) * 0.035
            jy = ((i // 3) % 3 - 1) * 0.030
            kvis(d, f0, True)
            kl(d, f0, tip.x + jx, tip.y + jy, tip.z, interp="LINEAR")
            ks(d, f0, 0.85)
            kl(d, f1, target.x + jx * 2.4, target.y + jy * 2.4, target.z, interp="LINEAR")
            ks(d, f1 - 1, 0.85)
            ks(d, f1, 0.22)
            kvis(d, f1, False)
            t0 += span + 4


# --------------------------------------------------------------------------- assembly

def build():
    global P
    lpm.reset()
    P = lpm.Palette(PALETTE)
    build_env()
    J = build_gardener()

    # watering can: one in the right hand, one standing where he puts it down
    can = build_can()
    can_h = can
    can_h.name = "PR_Can_Hand"
    can_g = _dup(can, "PR_Can_Ground")
    can_h.location = Vector((-0.265, -0.045, 0.775))
    can_h.rotation_euler = Euler((0, 0, math.radians(-8)), "XYZ")
    set_parent(can_h, J["foreR"])

    # shovel: one in the right hand, one standing in the soil
    sho = build_shovel()
    sho_h = sho
    sho_h.name = "PR_Shovel_Hand"
    sho_g = _dup(sho, "PR_Shovel_Ground")
    sho_h.location = Vector((-0.255, -0.030, 0.800))
    sho_h.rotation_euler = Euler((math.radians(-40), 0, math.radians(-6)), "XYZ")
    set_parent(sho_h, J["foreR"])
    sho_g.location = Vector(SHOVEL_GND)
    sho_g.rotation_euler = Euler((math.radians(-18), 0, math.radians(-14)), "XYZ")

    # a clod of soil riding on the blade during the lift
    cl = lpm.lathe("pr_clod", [(0.085, 0), (0.095, 0.03), (0.055, 0.07), (0, 0.09)], segments=6,
                   at=(0, 0, 0), color=P["soil_dark"])
    clod = group("PR_Clod", [cl], (0, 0, 0))
    clod.location = Vector((0.0, -0.03, -0.72))
    set_parent(clod, sho_h)

    seedling = build_flower("FL_New", "yellow", scale=1.38, petals=8, at=HOLE)
    drops = build_water()
    bflies = [build_butterfly("BFLY_0"), build_butterfly("BFLY_1")]

    build_world_and_light()
    build_cameras()
    props = dict(can_h=can_h, can_g=can_g, sho_h=sho_h, sho_g=sho_g, clod=clod,
                 seedling=seedling, drops=drops, bflies=bflies)
    animate(J, props)

    # the put-down copies inherit the exact world transform the hand had at the swap frame,
    # so nothing jumps; the can is additionally dropped onto the soil surface.
    sc = bpy.context.scene
    for src, dst, f, floor, foot in ((can_h, can_g, 142, 0.16, Vector((0, 0, -0.37))),
                                     (sho_h, sho_g, 278, None, None)):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        m = src.evaluated_get(dg).matrix_world.copy()
        if floor is not None:
            m.translation.z += floor - (m @ foot).z
        dst.matrix_world = m
        print(f"[place] {dst.name} <- {src.name}@{f} loc={tuple(round(v, 3) for v in m.translation)}", flush=True)

    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, DUR
    return J, props


def setup_render(samples=24, res=960, threads=0):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 2
    sc.cycles.volume_bounces = 0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    try:
        sc.cycles.use_denoising = True
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
        sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    except Exception as e:
        print("[render] denoiser unavailable:", e)
        sc.cycles.use_denoising = False
    sc.render.resolution_x = res
    sc.render.resolution_y = int(round(res * 9 / 16))
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.compression = 20
    sc.view_settings.view_transform = "Standard"
    sc.render.filter_size = 1.4
    if threads:
        sc.render.threads_mode = "FIXED"
        sc.render.threads = threads


def render_frames(frames, out_dir, skip_existing=True):
    import time
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    for f in frames:
        path = os.path.join(out_dir, f"f_{f:04d}.png")
        if skip_existing and os.path.exists(path) and os.path.getsize(path) > 2000:
            continue
        t0 = time.time()
        sc.frame_set(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"[render] frame {f} -> {os.path.basename(path)}  {time.time() - t0:.1f}s", flush=True)


def probe(J, props, frames):
    """Numbers before opinions: where do the hands, the blade and the spout actually end up?"""
    sc = bpy.context.scene
    out = {}
    for f in frames:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()

        def w(ob, v=(0, 0, 0)):
            return [round(c, 3) for c in (ob.evaluated_get(dg).matrix_world @ Vector(v))]

        out[f] = {"hand_R": w(J["foreR"], (0, -0.005, -0.355)),
                  "hand_L": w(J["foreL"], (0, -0.005, -0.355)),
                  "head_top": w(J["head"], (0, 0, 0.36)),
                  "blade_tip": w(props["sho_h"], (0, 0, -0.825)),
                  "spout_tip": w(props["can_h"], (0, -0.487, -0.072)),
                  "can_base": w(props["can_h"], (0, 0, -0.37))}
    print("##PROBE##" + json.dumps(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save")
    ap.add_argument("--out", default="frames")
    ap.add_argument("--frames", help="comma list, e.g. 1,120,300")
    ap.add_argument("--range", nargs=2, type=int)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--res", type=int, default=960)
    ap.add_argument("--threads", type=int, default=0)
    ap.add_argument("--probe")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args(sys.argv[1:])

    J, props = build()
    if a.stats:
        tot, rows = 0, []
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            t = lpm.tri_count(ob)
            tot += t
            rows.append((ob.name, t))
        rows.sort(key=lambda r: -r[1])
        print("##STATS##" + json.dumps({"total_tris": tot, "objects": len(rows), "top": rows[:14]}))
    if a.probe:
        probe(J, props, [int(x) for x in a.probe.split(",")])
    if a.save:
        print("[saved]", lpm.save(a.save))
    setup_render(a.samples, a.res, a.threads)
    frames = []
    if a.frames:
        frames = [int(x) for x in a.frames.split(",")]
    elif a.range:
        frames = list(range(a.range[0] + a.offset, a.range[1] + 1, a.step))
    if frames:
        render_frames(frames, a.out)


if __name__ == "__main__":
    main()
