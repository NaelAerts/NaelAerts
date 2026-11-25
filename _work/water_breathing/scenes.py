# scenes.py — "Water Breathing, Fifth Form: Blessed Rain After the Drought"  12.0 s @ 24 fps, 1920x1080
#
# S1  0.00-3.00  INTRODUCTION   wide moonlit plateau; he stands calm, haori and hair in the wind;
#                               camera pushes slowly in toward his face; he opens his eyes.      [fade in]
# S2  3.00-5.00  PREPARATION    cut to the eyes, then the camera falls to the blade as he lifts it;
#                               blue water gathers along the steel and spirals up from the pools. [whip blur]
# S3  5.00-9.00  FIFTH FORM     wind-up, step, and one graceful revolution of the blade: a full
#                               circular water trail wrapping around him, spray, splash, motion blur.
# S4  9.00-12.00 FINAL SHOT     the water falls apart into gentle rain; he settles, flicks the blade;
#                               the camera arcs around him and pulls back to the final composition.
#
# The pose is a PURE function of t, so the blade can be sampled at past times to build real
# motion blur and flowing trails instead of a static smear.
import math
import numpy as np
import skia
from engine import *
import slayer_env as EV
import slayer_water as WA
from slayer_char import slayer, katana_pts, P as CP

FPS_ = 24
DURATION = 12.0

WX, WGY = W / 2.0, 880.0      # character's world ground point
U = 46.0                      # body unit -> figure ~14.2u = 653 px tall at zoom 1

# ================================================================ camera
def camera(t):
    """returns (cx, cy, zoom, rot). cx stays on the character so panning him = orbiting him."""
    ox = orbit(t)
    if t < 3.0:        # push in
        k = ease(seg(t, 0.0, 3.0))
        cx = lerp(WX - 30, WX + 18, k)
        cy = lerp(615, 360, k)
        z = lerp(0.93, 1.72, k)
        rot = lerp(-1.6, -0.5, k)
    elif t < 3.95:     # eyes
        k = seg(t, 3.0, 3.95)
        cx = WX + 24 + 14 * ease(k)
        cy = 300 + 8 * k
        z = lerp(2.95, 3.25, ease(k))
        rot = lerp(2.2, 1.1, k)
    elif t < 4.45:     # fall to the blade
        k = ease(seg(t, 3.95, 4.45))
        cx = lerp(WX + 38, WX + 118, k)
        cy = lerp(308, 470, k)
        z = lerp(3.25, 2.35, k)
        rot = lerp(1.1, -2.6, k)
    elif t < 5.0:      # settle into the stance
        k = ease(seg(t, 4.45, 5.0))
        cx = lerp(WX + 118, WX + 10, k)
        cy = lerp(470, 430, k)
        z = lerp(2.45, 1.52, k)
        rot = lerp(-2.6, -0.8, k)
    elif t < 9.0:      # the form
        k = seg(t, 5.0, 9.0)
        cx = WX + ox + kf(t, [(5.0, 10.0), (5.6, -34.0), (6.3, 46.0), (7.2, 10.0), (8.2, -18.0), (9.0, 0.0)])
        cy = kf(t, [(5.0, 430.0), (5.6, 404.0), (6.3, 452.0), (7.4, 470.0), (9.0, 500.0)])
        z = kf(t, [(5.0, 1.52), (5.55, 1.66), (5.95, 1.30), (6.5, 1.40), (7.3, 1.48), (8.3, 1.38), (9.0, 1.30)])
        rot = kf(t, [(5.0, -0.8), (5.6, 2.6), (6.1, -3.4), (6.8, 1.8), (7.6, -1.0), (9.0, 0.6)])
    else:              # arc around him and pull back
        k = ease(seg(t, 9.0, 12.0))
        cx = WX + ox
        cy = lerp(500, 540, k)
        z = lerp(1.30, 1.16, k)
        rot = lerp(0.6, -1.4, k)
    sx, sy = 0.0, 0.0
    for (ts, am) in ((6.08, 15.0), (6.52, 9.0), (7.22, 7.0)):
        s = shake(t, ts, am, .34); sx += s[0]; sy += s[1]
    return (cx + sx, cy + sy, z, rot)

def orbit(t):
    """lateral travel of the camera around him (he is kept centred, so the world sweeps past)"""
    if t < 5.0: return 0.0
    if t < 9.0:
        return kf(t, [(5.0, 0.0), (6.3, 26.0), (7.4, -22.0), (9.0, 0.0)])
    return 580.0 * ease(seg(t, 9.0, 12.0)) - 34.0 * math.sin(seg(t, 9.0, 12.0) * math.pi)

def lbegin(cam, p, zp=None, orb=0.0):
    """multiplane layer: p = parallax depth (0 = sky, 1 = character plane)"""
    cx, cy, z, rot = cam
    zp = p if zp is None else zp
    ze = 1.0 + (z - 1.0) * zp
    c = CTX.canvas; c.save()
    c.translate(W / 2, H / 2); c.rotate(rot * (0.35 + .65 * p)); c.scale(ze, ze)
    c.translate(-(W / 2 + (cx - W / 2) * p), -(H / 2 + (cy - H / 2) * p))
    CTX.cam = (W / 2 + (cx - W / 2) * p, H / 2 + (cy - H / 2) * p, ze, rot * (0.35 + .65 * p))

def lend():
    CTX.canvas.restore(); CTX.cam = (W / 2, H / 2, 1, 0)

# ================================================================ pose (pure function of t)
def pose(t):
    """Everything about the body at time t. No drawing — so it can be sampled in the past."""
    x = WX + orbit(t)
    y = WGY
    # --- sword: blade angle first; the grip is then derived so the arms stay extended
    swAng = kf(t, [(0.0, 1.12), (2.40, 1.12), (3.00, 1.10), (3.90, 0.96),
                   (4.45, -0.30), (5.00, -0.58),
                   (5.55, -1.86),                      # wind-up, blade high behind
                   (5.95, -0.95), (6.35, 0.75), (6.80, 2.35), (7.25, 3.70),
                   (7.75, 4.75), (8.40, 5.55), (9.00, 5.95),
                   (9.45, 5.82), (9.64, 7.02), (9.95, 6.92),
                   (10.60, 6.80), (12.0, 6.78)], fn=ease)
    # the strike itself gets a sharper ease so the blade snaps through the middle of the arc
    if 5.55 <= t <= 7.25:
        k = seg(t, 5.55, 7.25)
        kk = clamp(0.5 - 0.5 * math.cos(math.pi * (k ** 0.74)))
        swAng = lerp(-1.86, 3.70, kk)
    # hands ride a circle around the chest, leading the blade -> arms never fold into the body
    R = kf(t, [(4.45, 1.20), (5.55, 1.35), (6.25, 1.62), (7.10, 1.48), (8.20, 1.30), (12.0, 1.22)])
    bcx, bcy = -0.15, -9.70
    gf = (bcx + R * math.cos(swAng + 1.25), bcy + R * math.sin(swAng + 1.25))
    # keep the hands a workable distance from the sword shoulder: no folded or over-stretched arms
    shx0, shy0 = 1.70, -11.50
    dgx, dgy = gf[0] - shx0, gf[1] - shy0
    dg = math.hypot(dgx, dgy) or 1e-6
    dc = min(4.05, max(1.15, dg))
    gf = (shx0 + dgx / dg * dc, shy0 + dgy / dg * dc)
    rest = (1.75, -7.30)
    if t < 4.30:
        grip = kf(t, [(0.0, rest), (3.0, (1.78, -7.34)), (3.90, (1.70, -7.50)), (4.30, (1.82, -8.00))])
    elif t < 4.72:
        k = ease(seg(t, 4.30, 4.72))
        grip = (lerp(1.82, gf[0], k), lerp(-8.00, gf[1], k))
    else:
        grip = gf
    # --- body
    o = {}
    o['key'] = 'TJ'
    o['u'] = U
    o['grip'] = grip
    o['swAng'] = swAng
    o['bend'] = kf(t, [(0.0, 0.06), (2.4, 0.04), (3.9, 0.02), (5.0, 0.10),
                       (5.55, -0.26), (5.95, 0.30), (6.35, 0.44), (6.9, 0.16),
                       (7.6, -0.06), (8.6, 0.02), (12.0, 0.05)])
    o['lean'] = kf(t, [(0.0, 0.0), (5.0, 0.0), (5.55, -0.28), (6.0, 0.34), (6.5, 0.40),
                       (7.3, 0.10), (8.4, 0.0), (12.0, 0.0)])
    o['sq'] = kf(t, [(0.0, 0.0), (5.0, 0.02), (5.5, 0.10), (5.95, -0.03), (6.4, 0.06),
                     (7.2, 0.03), (8.4, 0.01), (12.0, 0.0)])
    o['stance'] = kf(t, [(0.0, (-1.05, 0.0, 1.10, 0.0)), (4.9, (-1.05, 0.0, 1.10, 0.0)),
                         (5.5, (-0.70, 0.0, 1.55, 0.0)), (6.1, (-2.05, 0.0, 1.05, 0.0)),
                         (6.9, (-2.25, 0.0, 1.00, 0.0)), (8.6, (-1.85, 0.0, 1.15, 0.0)),
                         (12.0, (-1.60, 0.0, 1.20, 0.0))])
    # head turn: follows the blade through the form, then turns to camera as the camera arcs
    o['head'] = kf(t, [(0.0, 0.085), (1.9, 0.075), (2.5, 0.015), (3.9, 0.012),
                       (4.5, 0.055), (5.0, 0.030), (5.55, 0.115), (6.1, -0.055),
                       (6.7, -0.085), (7.5, -0.030), (8.6, 0.015),
                       (9.6, 0.105), (10.8, 0.055), (12.0, -0.015)])
    o['tilt'] = kf(t, [(0.0, 0.03), (2.5, 0.01), (5.0, 0.0), (5.55, -0.11), (6.2, 0.14),
                       (7.0, 0.05), (8.4, 0.0), (12.0, 0.02)])
    o['lookX'] = kf(t, [(0.0, -0.5), (2.3, -0.35), (2.7, 0.0), (5.0, 0.0), (5.55, 0.5),
                        (6.2, -0.6), (7.2, -0.3), (8.6, 0.0), (12.0, 0.1)])
    o['lookY'] = kf(t, [(0.0, 0.1), (5.4, 0.0), (5.9, -0.35), (6.5, 0.3), (7.4, 0.0), (12.0, 0.0)])
    o['hairWind'] = 0.30 + 0.16 * math.sin(t * 1.35) + 0.08 * math.sin(t * 2.7 + 1.1) \
        + kf(t, [(5.3, 0.0), (5.9, 0.55), (6.6, 0.30), (7.6, 0.10), (12.0, 0.04)])
    o['haoriWind'] = 0.34 + 0.15 * math.sin(t * 1.15 + .6) + 0.07 * math.sin(t * 2.3) \
        + kf(t, [(5.3, 0.0), (6.0, 0.72), (6.8, 0.40), (7.8, 0.12), (12.0, 0.05)])
    o['hairFlick'] = kf(t, [(5.5, 0.0), (6.05, 0.30), (6.9, 0.10), (12.0, 0.0)])
    # --- face
    blink = 0.0
    for bt in (1.15, 4.92, 8.95, 11.3):
        if bt - .10 < t < bt + .12:
            blink = math.sin(clamp((t - (bt - .10)) / .22) * math.pi) ** .7
    o['blink'] = blink
    o['eyes'] = 'closed' if t < 1.95 else 'det'
    o['squint'] = kf(t, [(1.95, 0.55), (2.6, 0.12), (3.2, 0.06), (5.4, 0.10),
                         (5.95, 0.0), (6.5, 0.0), (7.6, 0.18), (9.2, 0.30), (12.0, 0.26)])
    o['browAng'] = kf(t, [(0.0, 0.02), (2.2, 0.16), (5.5, 0.22), (6.4, 0.26), (8.0, 0.16), (12.0, 0.12)])
    o['browUp'] = kf(t, [(0.0, 0.0), (2.2, 0.10), (6.2, 0.16), (9.0, 0.04), (12.0, 0.02)])
    o['mouth'] = 'grit' if 5.7 < t < 7.0 else 'flat'
    o['mouthOpen'] = kf(t, [(5.75, 0.0), (5.95, 0.26), (6.6, 0.13), (7.0, 0.0)]) if 5.7 < t < 7.05 else 0.0
    # one-handed at rest; both hands on the hilt from the preparation onward
    o['onehand'] = t < 4.30
    o['handRest'] = kf(t, [(0.0, (-1.85, -7.25)), (3.0, (-1.82, -7.32)), (4.30, (-1.40, -8.30))])
    # water sheen on the steel
    o['glow'] = kf(t, [(0.0, 0.0), (3.55, 0.0), (4.1, 0.45), (4.9, 0.80), (5.5, 1.0),
                       (7.4, 1.0), (8.6, 0.55), (10.2, 0.22), (12.0, 0.12)])
    return dict(x=x, y=y, u=U, o=o, grip=grip, swAng=swAng)

def blade_at(t):
    p = pose(t)
    gx = p['x'] + p['grip'][0] * p['u']
    gy = p['y'] + p['grip'][1] * p['u']
    return katana_pts(gx, gy, p['swAng'], p['u'])

def tip_hist(t, span=0.52, n=22):
    """blade-tip positions over the last `span` seconds (newest first)"""
    out = []
    for i in range(n):
        tt = t - span * (i / (n - 1.0))
        if tt < 5.30: break
        out.append(blade_at(tt)['tip'])
    return np.array(out) if len(out) > 2 else None

def blade_speed(t):
    a0 = pose(max(0.0, t - 1 / 48.0))['swAng']; a1 = pose(t + 1 / 48.0)['swAng']
    return abs(a1 - a0) * 24.0

def head_pos(t):
    p = pose(t); o = p['o']
    sq = o['sq']
    shY = p['y'] - 11.5 * p['u'] * (1 - sq * .22)
    shx = p['x'] + o['bend'] * p['u'] * 2.0 + o['lean'] * p['u'] * 1.2
    return (shx + o['bend'] * p['u'] * .5, shY - 1.70 * p['u'] * 1.02)

# ================================================================ screen-space helpers
def dip(k, col='#04060E'):
    if k <= 0: return
    p = skia.Paint(Color=hexc(col, int(255 * clamp(k))))
    CTX.canvas.drawRect(skia.Rect.MakeXYWH(0, 0, W, H), p)

def speed_lines(t, cx, cy, k, n=30, key='sl', col=None, r0=320, r1=1500):
    """radial anime speed lines during the fastest part of the swing"""
    if k <= 0: return
    col = col or WA.WC['pale']
    c = CTX.canvas
    r = np.random.default_rng(WA.zlib_seed(key, int(t * 12)))
    for i in range(n):
        a = r.random() * 6.283
        rr0 = r0 * (.5 + r.random() * .9)
        rr1 = rr0 + (r1 - r0) * (.3 + r.random())
        w = (2.0 + r.random() * 5.0) * k
        p = skia.Paint(AntiAlias=True, Color=hexc(col, int(120 * k * (.4 + .6 * r.random()))),
                       StrokeWidth=w)
        p.setStyle(skia.Paint.kStroke_Style)
        c.drawLine(cx + math.cos(a) * rr0, cy + math.sin(a) * rr0,
                   cx + math.cos(a) * rr1, cy + math.sin(a) * rr1, p)

def whip(k, key='wh', col=None):
    """horizontal smear across the frame — used to soften the one hard cut"""
    if k <= 0: return
    col = col or '#BFE4F2'
    c = CTX.canvas
    r = np.random.default_rng(WA.zlib_seed(key))
    for i in range(34):
        y = r.random() * H
        h = 5 + r.random() * 46
        a = int(85 * k * (.25 + .75 * r.random()))
        p = skia.Paint(Color=hexc(col, a))
        c.drawRect(skia.Rect.MakeXYWH(-200, y, W + 400, h), p)

# ================================================================ world drawing
def world_bg(t, cam, dawn=0.0, grove_a=1.0):
    lbegin(cam, 0.045, 0.12); EV.sky(t, 0.0, dawn=dawn); lend()
    lbegin(cam, 0.11, 0.16); EV._ridge(3, H * .60, 150, mix(EV.E['far'], '#546C80', dawn), 0, 0, 'rg0', 15, 1.0); lend()
    lbegin(cam, 0.20, 0.26); EV._ridge(9, H * .66, 120, mix(EV.E['mid'], '#3E5168', dawn), 0, 0, 'rg1', 13, 1.2); lend()
    lbegin(cam, 0.33, 0.40)
    EV._ridge(17, H * .72, 95, mix(EV.E['near'], '#2A3850', dawn), 0, 0, 'rg2', 11, 1.1)
    for i in range(3):
        y0 = H * (.60 + i * .045)
        for j in range(5):
            shade(ell((t * (5 + i * 3)) % 900 - 450 + j * 480 - 300, y0, 330, 34 + i * 10, 24),
                  EV.E['mist'], 44 - i * 8, key=f'mb{i}{j}', blur=22)
    lend()
    if grove_a > 0.02:
        lbegin(cam, 0.70, 0.76); EV.grove(t, 0.0, a=grove_a); lend()

def world_ground(t, cam, pool=True):
    lbegin(cam, 1.0)
    EV.ground(t, 0.0, gy=WGY, pool=pool)
    lend()

# ================================================================ the four scenes
def draw(t):
    cam = camera(t)
    p = pose(t)
    o = dict(p['o'])
    glowk = o['glow']
    spd = blade_speed(t)

    # ---------------- background
    world_bg(t, cam, dawn=0.0, grove_a=1.0 if t < 4.0 or t > 8.4 else lerp(1.0, .45, seg(t, 4.0, 5.2)))
    world_ground(t, cam)

    # ---------------- water that lives behind him
    lbegin(cam, 1.0)
    # mist / vapour over the ground
    WA.mist_veil(WGY + 30, k=kf(t, [(0.0, .55), (4.5, .8), (6.0, 1.0), (9.0, .9), (12.0, .7)]), key='mv', amp=1.3)

    # pools answer the technique: water lifts out of them, then rains back
    rise = kf(t, [(4.3, 0.0), (5.2, 0.45), (5.9, 1.0), (7.4, 0.85), (8.6, 0.30), (9.6, 0.05), (12.0, 0.0)])
    if rise > .02:
        for i, px0 in enumerate((-300, 260, 820, 1420, 1960)):
            xx = px0 + orbit(t) * 0.9
            ph = i * .37
            k = ((t * .62 + ph) % 1.0)
            WA.splash_crown(xx, WGY + 62 + (i % 2) * 40, k, s=0.55 + .25 * (i % 3) * rise,
                            key=f'pc{i}', a=rise * .9)
            WA.ripple(xx, WGY + 62 + (i % 2) * 40, 130, ((t * .9 + ph) % 1.0), key=f'pr{i}', a=rise)

    # the great circular trail — far half (behind him)
    ring = kf(t, [(5.5, 0.0), (6.1, 0.55), (6.6, 1.0), (7.6, 1.0), (8.4, 0.72), (9.2, 0.30), (10.0, 0.0)])
    if ring > .02:
        rx = U * (4.6 + 2.2 * ease(seg(t, 6.0, 9.2)))
        ry = rx * 0.40
        cy0 = p['y'] - U * 5.6
        ph = t * 2.0
        for b in range(2):
            WA.ring_arc(p['x'], cy0 + b * U * 1.5, rx * (1 - b * .12), ry * (1 - b * .2),
                        -math.pi + b * .3, 0.0 - b * .25, U * (.62 - b * .18) * ring,
                        key=f'rbk{b}', a=ring, curl=.7, tilt=-0.06 + b * .03, phase=ph + b)
    lend()

    # ---------------- the figure (+ its sword, drawn inside)
    lbegin(cam, 1.0)
    # water that clings to the blade while it gathers
    if 3.9 < t < 5.6 and glowk > .05:
        K0 = blade_at(t)
        WA.aura(K0['spine'][len(K0['spine']) // 2][0], K0['spine'][len(K0['spine']) // 2][1],
                U * 2.3, k=glowk * .85, key='bau')
    slayer(p['x'], p['y'], p['u'], o)
    lend()

    # ---------------- water in front of him
    lbegin(cam, 1.0)
    # blade motion blur + the carved water trail
    if t > 5.35 and spd > 0.9:
        n = 6
        dt = 1 / 74.0
        spines = [blade_at(max(5.30, t - i * dt))['spine'] for i in range(n)]
        WA.blade_sweep(spines, key='bsw', a=clamp(spd / 7.0), glowk=.9, water=1.0)
    TH = tip_hist(t, span=0.55, n=20)
    if TH is not None and len(TH) > 3:
        a = clamp(spd / 5.5) * kf(t, [(5.3, 0.0), (5.7, .9), (7.4, 1.0), (8.4, .7), (9.4, .25), (10.2, 0.0)])
        if a > .03:
            WA.trail_ribbon(TH, w0=U * 1.30, key='tip', a=a, curl=.8)
            WA.drops('tipd', TH[:10], n=9, s0=3.5, s1=11, a=a * .85, spread=38)
    # near half of the ring (in front of him)
    if ring > .02:
        rx = U * (4.6 + 2.2 * ease(seg(t, 6.0, 9.2)))
        ry = rx * 0.40
        cy0 = p['y'] - U * 5.6
        ph = t * 2.0
        for b in range(2):
            WA.ring_arc(p['x'], cy0 + b * U * 1.5, rx * (1 - b * .12), ry * (1 - b * .2),
                        0.0 + b * .25, math.pi - b * .3, U * (.70 - b * .2) * ring,
                        key=f'rfr{b}', a=ring * .96, curl=.8, tilt=-0.06 + b * .03, phase=ph + b + 2)
    # spray off the strike
    for (ts, sx0, sy0, rr, a0, a1, sc) in ((6.02, 0.2, -5.6, 330, -2.9, -0.2, 1.15),
                                           (6.46, -0.9, -4.2, 300, -2.6, 0.4, 1.0),
                                           (7.18, 1.1, -6.2, 260, -3.2, -0.6, .85)):
        if ts < t < ts + 1.05:
            WA.spray(p['x'] + sx0 * U, p['y'] + sy0 * U, (t - ts) / 1.05, n=15,
                     key=f'spy{ts}', R=rr, a=1.0, ang0=a0, ang1=a1, s=sc)
    # water flung off the blade by the finishing flick
    if 9.62 < t < 10.60:
        ft = blade_at(9.64)['tip']
        WA.spray(ft[0], ft[1], (t - 9.62) / .98, n=16, key='flick', R=300, a=1.0,
                 ang0=-1.45, ang1=1.25, s=.85)
    # impact ripples under him
    for ts in (6.06, 6.50, 7.20):
        if ts < t < ts + 0.9:
            WA.ripple(p['x'] - U * .6, p['y'] + 16, 420, (t - ts) / .9, key=f'imp{ts}', a=.9)
    lend()

    # ---------------- gentle rain: the blessing after the drought
    ra = kf(t, [(7.3, 0.0), (8.2, 0.35), (9.2, 0.95), (10.4, 1.0), (12.0, 0.95)])
    if ra > .02:
        lbegin(cam, 0.55, 0.5); WA.rain(t, n=120, key='rnB', a=ra * .55, speed=.85, wind=.16, L=40); lend()
        lbegin(cam, 1.0); WA.rain_impacts(t, WGY + 40, n=16, key='rnI', a=ra * .8); lend()

    # ---------------- foreground: petals, fireflies, rain
    lbegin(cam, 1.15, 1.0)
    EV.petals(t, 0.0, n=14, key='pt', a=0.85, speed=1.0)
    lend()
    if t < 5.6:
        lbegin(cam, 0.9, .8); EV.fireflies(t, 0.0, n=12, a=clamp(1 - seg(t, 4.6, 5.6))); lend()
    if ra > .02:
        WA.rain(t, n=70, key='rnF', a=ra * .8, speed=1.35, wind=.2, L=120)

    # ---------------- grade & screen-space finish
    EV.moonlight(kf(t, [(0.0, .9), (5.0, 1.0), (6.3, 1.25), (9.0, 1.0), (12.0, .85)]))
    # a cool wash of water light during the form
    wl = kf(t, [(5.3, 0.0), (6.2, 1.0), (7.6, .75), (9.4, .35), (12.0, .2)])
    if wl > .02:
        pnt = skia.Paint(Color=hexc('#2E86B8', int(34 * wl)))
        pnt.setBlendMode(skia.BlendMode.kPlus)
        CTX.canvas.drawRect(skia.Rect.MakeXYWH(0, 0, W, H), pnt)
    # speed lines at the peak of the swing
    sl = clamp((spd - 3.2) / 4.2) * (1.0 if 5.8 < t < 7.3 else 0.0)
    if sl > .02:
        hp = to_screen_pt(cam, *head_pos(t))
        speed_lines(t, hp[0], hp[1], sl * .85, n=26, key='slz')
    EV.vignette(kf(t, [(0.0, .62), (3.0, .5), (3.95, .42), (6.2, .40), (9.0, .52), (12.0, .66)]))
    # flashes on the strikes
    flash(kf(t, [(5.92, 0.0), (6.02, .18), (6.20, 0.0)]) if 5.9 < t < 6.22 else 0.0, '#DFF4FF')
    flash(kf(t, [(7.10, 0.0), (7.18, .12), (7.32, 0.0)]) if 7.08 < t < 7.34 else 0.0, '#E8F8FF')
    # the one hard cut, softened with a whip smear
    if 2.95 < t < 3.10:
        whip((1 - seg(t, 2.97, 3.10)) * .55, key='wh1')
    # fade in / out
    dip(1 - ease(seg(t, 0.0, 0.55)))
    dip(ease(seg(t, 11.76, 12.0)) * 0.88)

def to_screen_pt(cam, x, y):
    cx, cy, z, rot = cam
    a = math.radians(rot)
    dx, dy = (x - cx) * z, (y - cy) * z
    return (W / 2 + dx * math.cos(a) - dy * math.sin(a), H / 2 + dx * math.sin(a) + dy * math.cos(a))

# ================================================================ render
def render(t):
    CTX.t = t; CTX.bi = int(t * BOIL)
    s = skia.Surface(W, H); c = s.getCanvas(); CTX.canvas = c
    CTX.cam = (W / 2, H / 2, 1, 0)
    c.clear(hexc('#0B1024'))
    draw(t)
    return finish(s.makeImageSnapshot().toarray())
