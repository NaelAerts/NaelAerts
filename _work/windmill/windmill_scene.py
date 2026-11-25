"""
Low-poly windmill - a seamless 6 s loop (144 frames @ 24 fps).

Everything cycles exactly once (or an integer number of times) over 144 frames, so frame 145 would
be frame 1 again: the sails turn a quarter turn (4 blades -> identical), the wheat sways on a full
sine, the flag flutters on two, the birds complete one circle. Rendered 1..144, it loops forever.

    python windmill_scene.py --save mill.blend --stats
    python windmill_scene.py --frames 1,40,80 --res 640 --samples 12 --out frames
    python windmill_scene.py --range 1 144 --step 4 --offset 0 --threads 1 --out frames
"""
import argparse, json, math, os, sys

SKILL = "/home/user/NaelAerts/.claude/skills/blender-lpm-skill/scripts"
sys.path.insert(0, SKILL)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bpy                                            # noqa: E402
from mathutils import Euler, Vector                   # noqa: E402
import lpm                                            # noqa: E402
import lpm_anim as A                                  # noqa: E402

FPS, LOOP = 24, 144

PALETTE_MILL = [
    ("stone",      "#b9b0a0", 0.0, 0.90),
    ("stone_dark", "#938b7d", 0.0, 0.90),
    ("stone_warm", "#cbbfa8", 0.0, 0.90),
    ("wood",       "#8a5f32", 0.0, 0.78),
    ("wood_dark",  "#6b4a2e", 0.0, 0.78),
    ("wood_light", "#b5894e", 0.0, 0.78),
    ("roof",       "#9a4a3c", 0.0, 0.80),
    ("roof_dark",  "#7d3a2f", 0.0, 0.80),
    ("sail",       "#f0e8d6", 0.0, 0.80),
    ("grass",      "#6f9b45", 0.0, 0.85),
    ("grass_dark", "#5a8338", 0.0, 0.85),
    ("wheat",      "#dcbd5e", 0.0, 0.85),
    ("wheat_dark", "#c4a244", 0.0, 0.85),
    ("leaf",       "#4d8a44", 0.0, 0.80),
    ("leaf_dark",  "#3b6f36", 0.0, 0.80),
    ("flag",       "#c8503f", 0.0, 0.75),
    ("metal",      "#b8bcc2", 1.0, 0.40),
    ("bird",       "#3a3630", 0.0, 0.70),
    ("path",       "#c6b48c", 0.0, 0.90),
]
P = None
MILL = (0.0, 3.0)                 # where the mill stands
HUB_Z = 7.35


def build_mill():
    """Tower + cap + turning sails. Returns the sail hub object (the only moving part)."""
    tower = lpm.prism("m_tower", 8, 2.30, 7.10, at=(MILL[0], MILL[1], 0), color=P["stone"], radius_top=1.52)
    lpm.paint(tower, P["stone_warm"], where=lambda c, n, i: i % 3 == 0)
    base = lpm.prism("m_base", 8, 2.52, 0.35, at=(MILL[0], MILL[1], 0), color=P["stone_dark"])
    band = lpm.prism("m_band", 8, 1.92, 0.22, at=(MILL[0], MILL[1], 3.55), color=P["stone_dark"])
    balcony = lpm.prism("m_balc", 8, 2.25, 0.10, at=(MILL[0], MILL[1], 3.77), color=P["wood"])
    rail = []
    for i in range(8):
        a = 2 * math.pi * i / 8 + math.pi / 8
        rail.append(lpm.box(f"m_post{i}", (0.09, 0.09, 0.52), color=P["wood_dark"],
                            at=(MILL[0] + 2.06 * math.cos(a), MILL[1] + 2.06 * math.sin(a), 3.87)))
    hoop = lpm.lathe("m_hoop", [(2.10, 0), (2.16, 0.02), (2.16, 0.09), (2.10, 0.11)], segments=8,
                     at=(MILL[0], MILL[1], 4.30), color=P["wood"])
    cap = lpm.lathe("m_cap", [(1.70, 0), (1.74, 0.18), (1.45, 0.72), (0.85, 1.12), (0, 1.32)], segments=8,
                    at=(MILL[0], MILL[1], 7.10), color=P["roof"])
    eave = lpm.prism("m_eave", 8, 1.80, 0.12, at=(MILL[0], MILL[1], 7.02), color=P["roof_dark"])
    door = lpm.box("m_door", (0.95, 0.12, 1.75), at=(MILL[0], MILL[1] - 2.26, 0.0), color=P["wood_dark"])
    step = lpm.box("m_step", (1.30, 0.45, 0.14), at=(MILL[0], MILL[1] - 2.52, 0.0), color=P["stone_dark"])
    wins = []
    for i, (wx, wy, wz, ws) in enumerate([(-1.25, -1.55, 2.30, 0.55), (1.25, -1.55, 2.30, 0.55),
                                          (0.0, -2.10, 4.95, 0.50), (-1.35, 1.30, 2.60, 0.50)]):
        wins.append(lpm.box(f"m_win{i}", (ws, 0.12, ws * 1.35), at=(MILL[0] + wx, MILL[1] + wy, wz), color=P["wood_dark"]))
        wins.append(lpm.box(f"m_gl{i}", (ws * 0.7, 0.06, ws * 1.0), at=(MILL[0] + wx, MILL[1] + wy - 0.05, wz + ws * 0.18),
                            color=P["stone_dark"]))
    A.group("MILL_Tower", [tower, base, band, balcony, hoop, cap, eave, door, step] + rail + wins)

    # --- sails: a hub on the front of the cap, four blades
    hub_at = (MILL[0], MILL[1] - 1.72, HUB_Z)
    shaft = lpm.prism("s_shaft", 6, 0.16, 0.55, at=(0, 0, 0), color=P["wood_dark"])
    lpm.rotate(shaft, -90, "X", about=(0, 0, 0))
    lpm.move(shaft, hub_at[0], hub_at[1] + 0.30, hub_at[2])
    hubcap = lpm.prism("s_hub", 8, 0.26, 0.18, at=(0, 0, 0), color=P["metal"])
    lpm.rotate(hubcap, -90, "X", about=(0, 0, 0))
    lpm.move(hubcap, hub_at[0], hub_at[1] + 0.02, hub_at[2])
    parts = [shaft, hubcap]
    for i in range(4):
        ang = 90.0 * i
        arm = lpm.box(f"s_arm{i}", (0.16, 0.14, 3.60), at=(0, 0, 0), color=P["wood"])
        slats = []
        for k in range(6):
            z = 0.75 + k * 0.46
            slats.append(lpm.box(f"s_sl{i}{k}", (0.62, 0.05, 0.30), at=(0.39, 0.0, z), color=P["sail"]))
        spar = lpm.box(f"s_spar{i}", (0.07, 0.07, 2.85), at=(0.68, 0, 0.72), color=P["wood_dark"])
        blade = [arm, spar] + slats
        for b in blade:
            lpm.rotate(b, ang, "Y", about=(0, 0, 0))
            lpm.move(b, hub_at[0], hub_at[1] - 0.10, hub_at[2])
        parts += blade
    hub = A.group("MILL_Sails", parts, hub_at)
    return hub


def build_env():
    g, gd = P["grass"], P["grass_dark"]
    ground = lpm.box("e_ground", (70, 70, 0.06), at=(0, 6, -0.06), color=g)
    parts = [ground]
    for i, (px, py, r, col) in enumerate([(-6.0, 1.5, 3.4, gd), (6.5, 4.0, 3.8, gd), (-2.0, 9.0, 4.2, gd),
                                          (9.0, -2.0, 3.0, gd), (-10.0, 6.0, 3.6, gd)]):
        # staggered heights: two coplanar patch tops shadow each other and render black
        parts.append(lpm.prism(f"e_patch{i}", 7, r, 0.010, at=(px, py, 0.004 + i * 0.0016), color=col, rotate=i * 29))
    for i, (hx, hy, hr, hh) in enumerate([(-22, 34, 13.0, 4.6), (14, 40, 15.0, 5.6), (34, 30, 10.0, 3.4)]):
        parts.append(lpm.lathe(f"e_hill{i}", [(hr, 0), (hr * 0.7, hh * 0.45), (hr * 0.35, hh * 0.8), (0, hh)],
                               segments=8, at=(hx, hy, 0.03 + i * 0.002), color=gd))
    path = []
    for i in range(11):
        t = i / 10.0
        px = MILL[0] + 0.25 * math.sin(t * 3.0)
        py = MILL[1] - 3.1 - t * 7.5
        path.append(lpm.prism(f"e_path{i}", 6, 0.62 - 0.02 * i, 0.022, at=(px, py, 0.012 + i * 0.0009),
                              color=P["path"], rotate=i * 31))
    A.group("ENV_Ground", parts + path)

    trees, fence = [], []
    for i, (tx, ty, ts) in enumerate([(-7.5, 8.0, 1.15), (8.5, 9.0, 0.95), (-11.0, 2.0, 0.85), (12.0, 5.5, 1.05)]):
        trees.append(lpm.prism(f"t_tr{i}", 7, 0.26 * ts, 1.9 * ts, at=(tx, ty, 0), color=P["wood_dark"], radius_top=0.20 * ts))
        for k, (cz, cr, ch) in enumerate([(1.55, 1.55, 1.9), (2.75, 1.15, 1.5), (3.70, 0.70, 1.1)]):
            trees.append(lpm.lathe(f"t_c{i}{k}", [(cr * ts, 0), (cr * 0.76 * ts, ch * 0.45 * ts),
                                                  (cr * 0.42 * ts, ch * 0.8 * ts), (0, ch * ts)],
                                   segments=7, at=(tx, ty, cz * ts), color=P["leaf"] if k % 2 else P["leaf_dark"]))
    for i in range(16):
        fx = -11.0 + i * 1.5
        fence.append(lpm.box(f"f_p{i}", (0.10, 0.10, 0.95), at=(fx, 12.0, 0), color=P["wood_dark"], taper=(0.85, 0.85)))
    fence.append(lpm.box("f_rail0", (24.0, 0.05, 0.10), at=(-0.5, 12.03, 0.40), color=P["wood"]))
    fence.append(lpm.box("f_rail1", (24.0, 0.05, 0.10), at=(-0.5, 12.03, 0.70), color=P["wood"]))
    A.group("ENV_Props", trees + fence)


def build_wheat(rows=6, per_row=70):
    """The field in front of the mill, in a few patch objects so each can sway as one."""
    patches = []
    for r in range(rows):
        tufts = []
        for i in range(per_row):
            a = (r * per_row + i) * 2.39996
            rad = 2.2 + ((r * per_row + i) % 7) * 0.55
            tx = MILL[0] + (-7.0 + ((r * per_row + i) * 1.31) % 13.5)
            ty = MILL[1] - 3.6 - r * 1.15 - 0.45 * math.sin(a)
            h = 0.52 + 0.16 * ((i % 4) / 3.0)
            col = P["wheat"] if (i + r) % 3 else P["wheat_dark"]
            tufts.append(lpm.sweep(f"w_{r}_{i}", [(-0.045, 0), (0.045, 0), (0.018, h), (-0.018, h * 0.82)],
                                   depth=0.014, at=(tx, ty, 0.0), color=col))
            if i % 3 == 0:
                tufts.append(lpm.box(f"wh_{r}_{i}", (0.07, 0.03, 0.14), at=(tx, ty, h - 0.02), color=col, taper=(0.4, 0.4)))
        # pivot on the ground at the middle of the row so the whole patch leans
        patches.append(A.group(f"WHEAT_{r}", tufts, (MILL[0], MILL[1] - 3.6 - r * 1.15, 0.0)))
    return patches


def build_flag_and_birds():
    pole = lpm.prism("fg_pole", 5, 0.05, 1.5, at=(MILL[0] + 2.9, MILL[1] + 2.4, 0), color=P["wood_dark"])
    A.group("ENV_Pole", [pole])
    cloth = lpm.sweep("fg_cloth", [(0, 0), (0.62, 0.06), (0.60, 0.30), (0, 0.36)], depth=0.012,
                      at=(MILL[0] + 2.93, MILL[1] + 2.4, 1.12), color=P["flag"])
    flag = A.group("FLAG", [cloth], (MILL[0] + 2.93, MILL[1] + 2.4, 1.12))
    birds = []
    for i in range(3):
        wing = lpm.sweep(f"bd_{i}", [(-0.30, 0.0), (-0.12, 0.07), (0.0, 0.0), (0.12, 0.07), (0.30, 0.0),
                                     (0.12, 0.03), (0.0, -0.04), (-0.12, 0.03)], depth=0.012,
                         at=(0, 0, 0), color=P["bird"], axis="y")
        birds.append(A.group(f"BIRD_{i}", [wing], (0, 0, 0)))
    return flag, birds


def animate(hub, wheat, flag, birds):
    """Every channel closes on itself at frame LOOP+1."""
    for f in (1, LOOP + 1):
        t = (f - 1) / LOOP
        A.kr(hub, f, 0, -90.0 * t, 0, interp="LINEAR")          # a quarter turn: 4 identical blades
    for f in range(1, LOOP + 2, 6):
        t = (f - 1) / LOOP
        w = 2 * math.pi * t
        for r, patch in enumerate(wheat):                        # one full sway, offset per row
            A.kr(patch, f, 3.6 * math.sin(w + r * 0.55), 0, 0.5 * math.sin(w * 2 + r * 0.9))
        A.kr(flag, f, 0, 0, 10.0 * math.sin(2 * w) + 4.0 * math.sin(4 * w))
        for i, b in enumerate(birds):                            # one circuit each, in a loose echelon
            a = w + i * 0.42
            rad = 7.0 + i * 1.1
            A.kl(b, f, MILL[0] + rad * math.cos(a) * 1.25, MILL[1] + 2.0 + rad * math.sin(a),
                 9.2 + i * 0.7 + 0.45 * math.sin(2 * a), interp="BEZIER")
            A.kr(b, f, 8 * math.sin(3 * w + i), 0, math.degrees(a) + 90)


def build():
    global P
    lpm.reset()
    P = A.set_palette(lpm.Palette(PALETTE_MILL))
    build_env()
    hub = build_mill()
    wheat = build_wheat()
    flag, birds = build_flag_and_birds()
    A.sky_and_sun(sun_energy=4.3, sky_strength=1.25, elevation=30, rotation=190,
                  sun_euler=(50, 0, 32), flat=(0.40, 0.62, 0.86),
                  fill={"energy": 110, "size": 9.0, "loc": (-9.0, -14.0, 7.0), "rot": (52, 0, -34)})
    cam, tgt = A.camera("CAM", (-13.5, -21.0, 5.6), (MILL[0] - 0.2, MILL[1] - 0.7, 5.0), lens=39)
    bpy.context.scene.camera = cam
    animate(hub, wheat, flag, birds)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, LOOP
    return hub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save"); ap.add_argument("--out", default="frames")
    ap.add_argument("--frames"); ap.add_argument("--range", nargs=2, type=int)
    ap.add_argument("--step", type=int, default=1); ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--samples", type=int, default=16); ap.add_argument("--res", type=int, default=960)
    ap.add_argument("--threads", type=int, default=0); ap.add_argument("--stats", action="store_true")
    a = ap.parse_args(sys.argv[1:])
    build()
    if a.stats:
        tot, rows = 0, []
        for ob in bpy.data.objects:
            if ob.type != "MESH":
                continue
            t = lpm.tri_count(ob); tot += t; rows.append((ob.name, t))
        rows.sort(key=lambda r: -r[1])
        print("##STATS##" + json.dumps({"total_tris": tot, "objects": len(rows), "top": rows[:10]}))
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
