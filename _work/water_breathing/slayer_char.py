# slayer_char.py — code-drawn anime swordsman (original design, Demon-Slayer-inspired).
# Everything is parametric and redrawn every frame: fill() washes + ink() outlines that boil,
# so the figure has hand-inked anime line quality rather than flat vector shapes.
#
# Proportions (units of u, measured up from the ground point):
#   foot 0 | knee 3.6 | hip 7.0 | obi 8.3 | chest 10.4 | shoulder 11.5 | chin 12.1 | head c 13.15 | top 14.2
# ~7 heads tall = anime hero proportion.
import math
import numpy as np
import skia
from engine import *

# ---------------------------------------------------------------- palette
P = dict(
    skin='#F0C6A0', skinSh='#D79C75', skinDp='#BE7F5E',
    hair='#241A20', hairSh='#120C12', hairBur='#6E2130', hairTip='#8E2C33', hairHi='#4A3038',
    haoG='#2F5B40', haoGSh='#1E3E2C', haoK='#221D26', haoKSh='#141017',
    kimo='#2B2630', kimoSh='#1A1620', hak='#3A3240', hakSh='#241F2B',
    obi='#6B4A3E', obiSh='#4A3029',
    blade='#2A2430', bladeEdge='#D7E4F0', bladeRed='#7E2630', hamon='#9FB6CC',
    tsuka='#262B36', tsukaW='#C7B189', tsuba='#B09A5E',
    eyeIris='#8E3029', eyeDk='#2A1C20', white='#FFFCF4',
    scar='#9C4030', ear='#F6ECD8', earRed='#B8303A',
    belt='#4A3F46',
)
INKC = '#1E1820'

# ---------------------------------------------------------------- small helpers
def _rot(Q, a, ox=0.0, oy=0.0):
    Q = np.asarray(Q, np.float64); c, s = math.cos(a), math.sin(a)
    x, y = Q[:, 0] - ox, Q[:, 1] - oy
    return np.stack([ox + x * c - y * s, oy + x * s + y * c], 1)

def ik(sx, sy, hx, hy, L1, L2, side=1.0):
    """2-bone IK -> elbow/knee point"""
    dx, dy = hx - sx, hy - sy
    d = math.hypot(dx, dy)
    d = min(d, (L1 + L2) * .995)
    d = max(d, abs(L1 - L2) * 1.02 + 1e-4)
    a = math.atan2(dy, dx)
    ca = clamp((d * d + L1 * L1 - L2 * L2) / (2 * d * L1), -1, 1)
    A = math.acos(ca)
    ea = a + A * side
    return (sx + math.cos(ea) * L1, sy + math.sin(ea) * L1)

def limb(pts, w0, w1, col, sh, key, ow=None, n=10):
    """tapered limb: ink outline ribbon + colour ribbon + shadow tone on one side"""
    c = CTX.canvas
    D = catmull(np.asarray(pts, np.float64), False, n)
    D = boil(densify(D, False, 5), key, max(.5, w0 * .035), False)
    ow = ow if ow is not None else max(2.4, w0 * .22)
    c.drawPath(ribbon(D, w0 + ow, w1 + ow * .85, key=key + 'o', var=.08), skia.Paint(AntiAlias=True, Color=hexc(INKC)))
    c.drawPath(ribbon(D, w0, w1, key=key + 'c', var=.07), skia.Paint(AntiAlias=True, Color=hexc(col)))
    # shadow tone: thinner ribbon pushed to the lower-right side
    d = np.gradient(D, axis=0)
    nrm = np.stack([-d[:, 1], d[:, 0]], 1); nrm /= np.maximum(np.hypot(nrm[:, 0], nrm[:, 1]), 1e-6)[:, None]
    S = D + nrm * (w0 * .26)
    pa = skia.Paint(AntiAlias=True, Color=hexc(sh))
    c.drawPath(ribbon(S, w0 * .42, w1 * .40, key=key + 's', var=.06), pa)

def hand(x, y, r, key, col=None, sh=None, a=0.0, grip=1.0):
    col = col or P['skin']; sh = sh or P['skinSh']
    Q = ell(x, y, r * (1.0 - .12 * grip), r * 1.08, 16, a)
    fill(Q, col, key=key, tex=.18, edge=.30, amp=.5, outline=max(2.0, r * .30), ocol=INKC)
    wash(ell(x + r * .22, y + r * .26, r * .46, r * .40, 12, a), sh, key=key + 's', a=190)

# ---------------------------------------------------------------- katana
def katana_pts(gx, gy, ang, u):
    """Geometry only (no drawing). grip point (gx,gy) = front hand; ang rad, blade runs toward +ang.
    Returns spine (guard->tip), tip, guard, butt and the edge-side offset normal."""
    ca, sa = math.cos(ang), math.sin(ang)
    px, py = -sa, ca                      # left normal of the blade direction
    gl = 0.55 * u                          # guard sits just ahead of the grip
    bx, by = gx + ca * gl, gy + sa * gl    # guard
    L = 6.3 * u
    n = 26
    s = np.linspace(0, 1, n)
    curve = -0.30 * u * np.sin(s * math.pi * .78)   # gentle shinogi curve, edge side
    sx = bx + ca * (L * s) + px * curve
    sy = by + sa * (L * s) + py * curve
    spine = np.stack([sx, sy], 1)
    butt = (gx - ca * 1.85 * u, gy - sa * 1.85 * u)
    return dict(spine=spine, tip=(float(sx[-1]), float(sy[-1])), guard=(bx, by),
                butt=butt, dir=(ca, sa), nrm=(px, py), u=u, ang=ang, L=L)

def katana(K, key='kat', glow_k=0.0, gcol='#7FD9F2'):
    """Draw the sword from katana_pts geometry. glow_k adds a water-light sheen on the blade."""
    c = CTX.canvas
    u = K['u']; ca, sa = K['dir']; px, py = K['nrm']
    sp = K['spine']; bx, by = K['guard']
    gx, gy = bx - ca * .55 * u, by - sa * .55 * u
    w = .30 * u   # blade half-width at the guard
    # blade body: spine side (back) and edge side
    s01 = np.linspace(0, 1, len(sp))
    nb = np.array([-px, -py]) * w * .92
    ne = np.array([px, py]) * w
    back = sp + np.outer(1 - .18 * s01, nb)
    edge = sp + np.outer(1 - .55 * s01 ** 2.2, ne)
    # taper to the point (kissaki)
    back[-1] = sp[-1]; edge[-1] = sp[-1]
    body = np.vstack([back, edge[::-1]])
    if glow_k > 0:
        for i in range(0, len(sp), 3):
            glow(float(sp[i, 0]), float(sp[i, 1]), u * (1.5 + 1.4 * glow_k), gcol, .34 * glow_k)
    fill(body, P['blade'], key=key + 'b', tex=.20, edge=.34, amp=.35, outline=max(2.2, u * .13), ocol=INKC)
    # crimson sheen along the spine (black nichirin blade)
    rs = sp + np.array([-px, -py]) * w * .48
    ink(rs[1:-1], max(1.6, u * .085), P['bladeRed'], key=key + 'r', closed=False, amp=.25, a=215)
    # bright edge line + hamon
    es = sp + np.outer(1 - .5 * s01 ** 2, np.array([px, py]) * w * .74)
    ink(es[:-1], max(1.5, u * .075), P['bladeEdge'], key=key + 'e', closed=False, amp=.2, a=235)
    hm = sp + np.array([px, py]) * w * .30
    ink(hm[2:-2], max(1.0, u * .045), P['hamon'], key=key + 'h', closed=False, amp=.5, a=120)
    if glow_k > 0:
        ink(es[:-1], max(1.8, u * .10), gcol, key=key + 'g', closed=False, amp=.3, a=int(190 * clamp(glow_k)))
    # tsuba (guard)
    fill(ell(bx, by, u * .62, u * .30, 16, math.atan2(py, px)), P['tsuba'], key=key + 't',
         tex=.2, edge=.35, amp=.4, outline=max(2.0, u * .12), ocol=INKC)
    # tsuka (handle) with ito wrap diamonds
    bu = K['butt']
    hp = np.array([[gx + px * u * .19, gy + py * u * .19], [bu[0] + px * u * .17, bu[1] + py * u * .17],
                   [bu[0] - px * u * .17, bu[1] - py * u * .17], [gx - px * u * .19, gy - py * u * .19]])
    fill(hp, P['tsuka'], key=key + 'k', tex=.22, edge=.35, amp=.35, outline=max(2.0, u * .12), ocol=INKC)
    for i in range(5):
        k = .12 + i * .19
        mx, my = gx + (bu[0] - gx) * k, gy + (bu[1] - gy) * k
        ink([(mx + px * u * .17, my + py * u * .17), (mx - px * u * .17, my - py * u * .17)],
            max(1.2, u * .055), P['tsukaW'], key=f'{key}w{i}', closed=False, amp=.2, a=170)

# ---------------------------------------------------------------- head
def _anime_eye(x, y, s, key, kind='det', lookX=0.0, lookY=0.0, blink=0.0, flip=1, squint=0.0):
    """large anime eye: ellipse sclera, iris with gradient, heavy upper lash line"""
    c = CTX.canvas
    ow = max(1.6, s * .19)
    bl = clamp(blink)
    if kind == 'closed' or bl > .9:
        Q = [(x - s * .66, y - s * .05), (x, y + s * .15), (x + s * .66, y - s * .02)]
        ink(catmull(Q, False, 8), ow * 1.7, INKC, key=key + 'c', closed=False, amp=.3)
        ink([(x + s * .66 * flip, y - s * .02), (x + s * .84 * flip, y - s * .20)], ow * 1.1, INKC,
            key=key + 'cl', closed=False, amp=.2)
        return
    hh = s * (.76 - .32 * squint) * (1 - bl * .85)
    hw = s * .60
    fill(ell(x, y, hw, hh, 26), P['white'], key=key + 'w', tex=.08, edge=.14, amp=.35)
    ix, iy = x + lookX * s * .20, y + lookY * s * .14
    ir = min(s * .44, hh * .95)
    fill(ell(ix, iy, ir, min(ir * 1.10, hh * .98), 22), P['eyeIris'], key=key + 'i', tex=.12, edge=.28, amp=.3)
    wash(ell(ix, iy + ir * .36, ir * .84, min(ir * .50, hh * .5), 16), '#C4584A', key=key + 'ib', a=160)
    fill(ell(ix, iy - ir * .04, ir * .42, min(ir * .50, hh * .6), 16), P['eyeDk'], key=key + 'p',
         tex=0, edge=0, amp=.25)
    wash(ell(ix - ir * .40 * flip, iy - ir * .44, ir * .32, ir * .24, 12), P['white'], key=key + 'h1')
    wash(ell(ix + ir * .34 * flip, iy + ir * .40, ir * .14, ir * .11, 10), P['white'], key=key + 'h2', a=200)
    # heavy upper lash line
    up = np.array([(x - hw * 1.10, y - hh * .34), (x - hw * .45, y - hh * 1.00),
                   (x + hw * .45, y - hh * 1.02), (x + hw * 1.10, y - hh * .40)])
    if flip < 0: up[:, 0] = 2 * x - up[:, 0]
    U = catmull(up, False, 10)
    c.drawPath(ribbon(boil(densify(U, False, 4), key + 'u', .45, False), s * .19, s * .09,
                      key=key + 'ur', var=.1), skia.Paint(AntiAlias=True, Color=hexc(INKC)))
    lo = np.array([(x - hw * .92, y + hh * .50), (x, y + hh * .96), (x + hw * .88, y + hh * .54)])
    if flip < 0: lo[:, 0] = 2 * x - lo[:, 0]
    ink(catmull(lo, False, 8), ow * .80, INKC, key=key + 'l', closed=False, amp=.3, a=195)
    tipx = x + hw * 1.10 * flip
    ink([(tipx, y - hh * .40), (tipx + s * .24 * flip, y - hh * .78)], ow * 1.2, INKC,
        key=key + 'f', closed=False, amp=.2)

# ---------------------------------------------------------------- hair (original design)
def _hair_back(cx, cy, u, o, key):
    """mass behind the head + a gathered tail at the nape"""
    t = CTX.t
    wind = o.get('hairWind', 0.0)
    sd = o.get('_side', 0.0)
    bx = cx + sd * u * .34
    Q = ell(bx, cy + u * .02, u * 1.00, u * 1.10, 28)
    fill(Q, P['hairSh'], key=key + 'm', tex=.28, edge=.40, amp=1.0, outline=max(2.2, u * .11), ocol=INKC)
    # nape tail: three heavy locks falling behind the shoulder, swinging with the wind
    for i in range(3):
        f = i / 2.0
        sx = bx + (f - .5) * u * .74 - sd * u * .18
        sy = cy + u * .50
        L = u * (0.80 + .22 * math.sin(i * 2.0))
        sw = wind * (.70 + .35 * f) + .14 * math.sin(t * 2.0 + i * 1.3)
        mid = (sx - u * .10 + sw * L * .34, sy + L * .52)
        tip = (sx - u * .24 + sw * L * .95, sy + L)
        D = boil(densify(catmull([(sx, sy), mid, tip], False, 9), False, 5), f'{key}t{i}', .9, False)
        CTX.canvas.drawPath(ribbon(D, u * .30, u * .045, key=f'{key}to{i}', var=.12),
                            skia.Paint(AntiAlias=True, Color=hexc(INKC)))
        CTX.canvas.drawPath(ribbon(D, u * .21, u * .025, key=f'{key}ti{i}', var=.11),
                            skia.Paint(AntiAlias=True, Color=hexc(P['hairSh'])))
        T = D[int(len(D) * .68):]
        CTX.canvas.drawPath(ribbon(T, u * .20, u * .02, key=f'{key}tb{i}', var=.12),
                            skia.Paint(AntiAlias=True, Color=hexc(P['hairBur'])))

def _hair_front(cx, cy, u, o, key):
    """One inked shape: skull volume whose lower edge breaks into bang points, plus side locks."""
    t = CTX.t
    wind = o.get('hairWind', 0.0)
    flick = o.get('hairFlick', 0.0)
    sd = o.get('_side', 0.0)
    cxh = cx + sd * u * .20
    sw = (wind * .55 + flick * .5) * u
    # outline: up the left side, over the crown, down the right side, then the bang fringe back
    top = [(cxh - u * 1.00, cy + u * .20), (cxh - u * 1.10, cy - u * .46),
           (cxh - u * .80, cy - u * 1.08), (cxh - u * .12, cy - u * 1.30),
           (cxh + u * .66, cy - u * 1.14), (cxh + u * 1.06, cy - u * .52),
           (cxh + u * 1.02, cy + u * .16)]
    # jagged fringe: alternating low tips and high notches, swept by the wind
    fr = []
    tips = [(.78, -.40), (.34, -.52), (-.10, -.42), (-.54, -.50), (-.90, -.34)]
    for j, (fx, fy) in enumerate(tips):
        nx = cxh + fx * u * 1.02 + sw * (.30 + .22 * j)
        fr.append((nx, cy + fy * u - u * .02))
        if j < len(tips) - 1:
            mx = cxh + (fx + tips[j + 1][0]) * .5 * u * 1.02 + sw * (.26 + .2 * j)
            fr.append((mx, cy - u * .90))
    Q = np.array(top + fr)
    fill(catmull(Q, True, 6), P['hair'], key=key + 'f', tex=.28, edge=.42, amp=1.0,
         outline=max(2.4, u * .12), ocol=INKC)
    # burgundy warmth low in the fringe
    for j, (fx, fy) in enumerate(tips):
        nx = cxh + fx * u * 1.02 + sw * (.30 + .22 * j)
        D = boil(densify(np.array([(nx - u * .04, cy - u * .86), (nx, cy + fy * u + u * .03)]), False, 5),
                 f'{key}bt{j}', .7, False)
        CTX.canvas.drawPath(ribbon(D, u * .17, u * .02, key=f'{key}br{j}', var=.14),
                            skia.Paint(AntiAlias=True, Color=hexc(P['hairBur'], 225)))
    # anime shine band across the crown
    hl = catmull([(cxh - u * .70, cy - u * .66), (cxh - u * .12, cy - u * .92),
                  (cxh + u * .56, cy - u * .70)], False, 9)
    D = boil(densify(hl, False, 5), key + 'hl', .6, False)
    CTX.canvas.drawPath(ribbon(D, u * .17, u * .05, key=key + 'hlr', var=.22),
                        skia.Paint(AntiAlias=True, Color=hexc(P['hairHi'], 165)))
    # side locks framing the face
    for side in (-1, 1):
        bx = cxh + side * u * 1.00
        by = cy - u * .40
        L = u * (1.16 if side * (1 if sd >= 0 else -1) > 0 else 0.98)
        s2 = sw * (.55 + .25 * side)
        mid = (bx + side * u * .10 + s2 * .4, by + L * .52)
        tip = (bx + side * u * .16 + s2, by + L)
        D = boil(densify(catmull([(bx, by - u * .18), mid, tip], False, 9), False, 5), f'{key}s{side}', .8, False)
        CTX.canvas.drawPath(ribbon(D, u * .23, u * .035, key=f'{key}so{side}', var=.13),
                            skia.Paint(AntiAlias=True, Color=hexc(INKC)))
        CTX.canvas.drawPath(ribbon(D, u * .15, u * .02, key=f'{key}si{side}', var=.12),
                            skia.Paint(AntiAlias=True, Color=hexc(P['hair'])))
        T = D[int(len(D) * .62):]
        CTX.canvas.drawPath(ribbon(T, u * .10, u * .015, key=f'{key}sb{side}', var=.13),
                            skia.Paint(AntiAlias=True, Color=hexc(P['hairBur'])))

def head(cx, cy, u, o, key='H'):
    """u = head unit: head height ~2.2u. o carries expression + heading."""
    t = CTX.t
    hd = o.get('head', 0.0)
    fr = math.cos(hd * 2 * math.pi); sd = math.sin(hd * 2 * math.pi)
    o = dict(o); o['_front'] = fr; o['_side'] = sd
    tilt = o.get('tilt', 0.0)
    blink = o.get('blink', 0.0)
    squint = o.get('squint', 0.0)
    c = CTX.canvas
    c.save(); c.translate(cx, cy); c.rotate(math.degrees(tilt)); c.translate(-cx, -cy)
    _hair_back(cx, cy, u, o, key + 'hb')
    # ---- ear on the far side
    if abs(sd) > .05:
        ex = cx - sd * u * .82
        fill(ell(ex, cy + u * .18, u * .16, u * .25, 14, -sd * .3), P['skin'], key=key + 'ear',
             tex=.2, edge=.3, amp=.4, outline=max(1.8, u * .10), ocol=INKC)
    # ---- face
    fw = u * .84 * (0.82 + .18 * abs(fr))
    fcx = cx + sd * u * .22
    face = np.array([
        (fcx - fw, cy - u * .40), (fcx - fw * .98, cy + u * .14), (fcx - fw * .82, cy + u * .56),
        (fcx - fw * .42, cy + u * .92), (fcx + sd * u * .12, cy + u * 1.06),
        (fcx + fw * .46, cy + u * .90), (fcx + fw * .84, cy + u * .54),
        (fcx + fw * .99, cy + u * .12), (fcx + fw, cy - u * .42),
        (fcx + fw * .70, cy - u * .84), (fcx, cy - u * .98), (fcx - fw * .72, cy - u * .82)])
    fill(catmull(face, True, 7), P['skin'], key=key + 'f', tex=.14, edge=.24, amp=.7,
         outline=max(2.2, u * .11), ocol=INKC)
    shade(ell(fcx + sd * u * .1, cy + u * .66, fw * .70, u * .32, 18), P['skinSh'], 62, key=key + 'js', blur=5)
    shade(ell(fcx - fw * .64 * (1 if sd >= 0 else -1), cy + u * .14, fw * .32, u * .40, 16),
          P['skinSh'], 44, key=key + 'cs', blur=6)
    # ---- brows
    bw = fw * .42
    for side in (-1, 1):
        bx = fcx + side * fw * .50 + sd * u * .10
        by = cy - u * .50 - o.get('browUp', 0.0) * u * .12
        inn = (bx - side * bw * .58, by + u * .09 + o.get('browAng', .10) * u)
        out = (bx + side * bw * .62, by - u * .05)
        Q = catmull([inn, ((inn[0] + out[0]) / 2, (inn[1] + out[1]) / 2 - u * .05), out], False, 7)
        D = boil(densify(Q, False, 4), f'{key}br{side}', .5, False)
        c.drawPath(ribbon(D, u * .125, u * .045, key=f'{key}brr{side}', var=.12),
                   skia.Paint(AntiAlias=True, Color=hexc(P['hairSh'])))
    # ---- eyes (large, anime)
    es = u * .42
    for side, flip in ((-1, -1), (1, 1)):
        ex = fcx + side * fw * .48 + sd * u * .13
        comp = 1.0 if (side * sd) >= 0 else lerp(1.0, .52, abs(sd))
        if comp < .60 and abs(sd) > .55: continue
        c.save(); c.translate(ex, cy); c.scale(comp, 1.0); c.translate(-ex, -cy)
        _anime_eye(ex, cy - u * .04, es, f'{key}e{side}', kind=o.get('eyes', 'det'),
                   lookX=o.get('lookX', 0.0), lookY=o.get('lookY', 0.0), blink=blink, flip=flip, squint=squint)
        c.restore()
    # ---- nose + mouth
    nx = fcx + sd * u * .32
    ink([(nx - u * .01, cy + u * .32), (nx + u * .09 + sd * u * .06, cy + u * .45), (nx - u * .05, cy + u * .48)],
        max(1.4, u * .07), P['skinDp'], key=key + 'n', closed=False, amp=.3, a=165)
    mk = o.get('mouth', 'flat'); mo = o.get('mouthOpen', 0.0)
    mx, my = fcx + sd * u * .26, cy + u * .74
    if mo > .06:
        k = mo
        Q = ell(mx, my + u * .03 * k, u * .17 * (1 + .22 * k), u * (.04 + .15 * k), 18)
        fill(Q, '#6E2630', key=key + 'm', tex=0, edge=.2, amp=.3, outline=max(1.6, u * .075), ocol=INKC)
        wash(ell(mx, my - u * .01 - u * .05 * k, u * .14, u * .03, 12), P['white'], key=key + 'mt', a=215)
    elif mk == 'grit':
        Q = rrect(mx - u * .21, my - u * .06, u * .42, u * .13, u * .03)
        fill(Q, '#5E2028', key=key + 'm', tex=0, edge=.2, amp=.4, outline=max(1.6, u * .075), ocol=INKC)
        wash(rect(mx - u * .19, my - u * .05, u * .38, u * .055), P['white'], key=key + 'mt', a=225)
    else:
        ink([(mx - u * .15, my), (mx, my + u * .045), (mx + u * .15, my - u * .01)],
            max(1.5, u * .075), INKC, key=key + 'm', closed=False, amp=.3, a=205)
    # ---- near ear
    if sd <= .25:
        ex = fcx + fw * .99
        fill(ell(ex, cy + u * .24, u * .14, u * .22, 14, .2), P['skin'], key=key + 'ear2',
             tex=.2, edge=.3, amp=.4, outline=max(1.8, u * .09), ocol=INKC)
    _hair_front(cx, cy, u, o, key + 'hf')
    c.restore()

# ---------------------------------------------------------------- cloth pattern
def _checker(path, x0, y0, s, key, ang=0.0, colB=None):
    """green/black checkerboard clipped to a cloth panel"""
    colB = colB or P['haoK']
    c = CTX.canvas
    b = path.getBounds()
    if b.width() < 2 or b.height() < 2: return
    c.save(); c.clipPath(path, skia.ClipOp.kIntersect, True)
    c.translate(x0, y0); c.rotate(math.degrees(ang)); c.translate(-x0, -y0)
    nx = int(b.width() / s) + 4; ny = int(b.height() / s) + 4
    i0 = int((b.left() - x0) / s) - 2; j0 = int((b.top() - y0) / s) - 2
    pa = skia.Paint(AntiAlias=True, Color=hexc(colB))
    for i in range(i0, i0 + nx + 4):
        for j in range(j0, j0 + ny + 4):
            if (i + j) % 2: continue
            c.drawRect(skia.Rect.MakeXYWH(x0 + i * s, y0 + j * s, s, s), pa)
    c.restore()

# ---------------------------------------------------------------- the figure
def slayer(x, y, u, o=None):
    """(x,y) = ground point between the feet; u = body unit (figure ~14.2u tall)."""
    o = o or {}
    t = CTX.t
    key = o.get('key', 'T')
    c = CTX.canvas
    hu = u * 1.18
    bend = o.get('bend', 0.0); lean = o.get('lean', 0.0); sq = o.get('sq', 0.0)
    hd = o.get('head', 0.0)
    fr = math.cos(hd * 2 * math.pi); sd = math.sin(hd * 2 * math.pi)
    lift = o.get('lift', 0.0) * u
    hw = o.get('haoriWind', 0.4)

    if not o.get('noShadow'):
        shade(ell(x, y + u * .10, u * 2.3 * (1 - min(.45, lift / (u * 9))), u * .40, 26),
              '#241F36', int(76 * (1 - min(.5, lift / (u * 10)))), key=key + 'sh', blur=8)
    y -= lift

    hipY = y - 7.0 * u * (1 - sq * .35)
    obiY = y - 8.3 * u * (1 - sq * .30)
    chY = y - 10.4 * u * (1 - sq * .25)
    shY = y - 11.5 * u * (1 - sq * .22)
    kneeY = y - 3.6 * u * (1 - sq * .40)
    hx = x + lean * u * .5
    cxx = x + bend * u * 1.1 + lean * u * .9
    shx = x + bend * u * 2.0 + lean * u * 1.2
    shHalf = u * 1.70
    sL = (shx - shHalf * (0.55 + .45 * abs(fr)) - sd * u * .25, shY + u * .12)
    sR = (shx + shHalf * (0.55 + .45 * abs(fr)) - sd * u * .25, shY + u * .12)
    headY = shY - 1.70 * hu
    headX = shx + bend * u * .5 + o.get('headDx', 0.0) * u

    # ---------------- haori back panel (behind everything)
    bp = np.array([(shx - shHalf * .95 - sd * u * .2, shY - u * .20), (shx + shHalf * .95 - sd * u * .2, shY - u * .20),
                   (shx + shHalf * 1.15 + hw * u * .6, obiY + u * .4), (hx + u * 1.5, hipY - u * .2),
                   (hx - u * 1.5, hipY - u * .2), (shx - shHalf * 1.15 + hw * u * .4, obiY + u * .4)])
    pth = fill(catmull(bp, True, 6), P['haoG'], key=key + 'bk', tex=.26, edge=.38, amp=1.0,
               outline=max(2.4, u * .12), ocol=INKC)
    _checker(pth, shx, shY, u * .60, key + 'bkc', ang=bend * .10)
    shade(catmull(bp, True, 6), P['haoGSh'], 70, key=key + 'bks', blur=10)

    # ---------------- legs
    st = o.get('stance', (-1.05, 0.0, 1.10, 0.0))
    fL = (x + st[0] * u, y + st[1] * u)
    fR = (x + st[2] * u, y + st[3] * u)
    hipL = (hx - u * .66, hipY + u * .16)
    hipR = (hx + u * .66, hipY + u * .16)
    kn = {}
    for (hp, ft, k2) in ((hipL, fL, 'L'), (hipR, fR, 'R')):
        kn[k2] = ik(hp[0], hp[1], ft[0], ft[1] - u * .30, 3.4 * u, 3.6 * u, side=1.0)
    for k2, ft in (('L', fL), ('R', fR)):
        e = kn[k2]
        # shin wrapped dark, from the knee to the foot
        limb([(e[0], e[1] - u * .25), ((e[0] + ft[0]) / 2, (e[1] + ft[1]) / 2), (ft[0], ft[1] - u * .24)],
             u * .50, u * .38, P['hak'], P['hakSh'], key + 'shin' + k2)
        fp = np.array([(ft[0] - u * .44, ft[1] - u * .30), (ft[0] + u * .52, ft[1] - u * .33),
                       (ft[0] + u * .60, ft[1] - u * .02), (ft[0] - u * .50, ft[1])])
        fill(fp, '#E3D8C0', key=key + 'ft' + k2, tex=.2, edge=.30, amp=.5, outline=max(2.0, u * .11), ocol=INKC)
        ink([(ft[0] + u * .08, ft[1] - u * .31), (ft[0] + u * .12, ft[1] - u * .03)], max(1.3, u * .05),
            P['skinSh'], key=key + 'ftl' + k2, closed=False, amp=.2, a=140)
    # ---------------- hakama (baggy, pleated, knee length)
    hemL = min(kn['L'][0], fL[0]) - u * .86
    hemR = max(kn['R'][0], fR[0]) + u * .86
    hak = np.array([(hx - u * 1.30, obiY - u * .05), (hx + u * 1.30, obiY - u * .05),
                    (hx + u * 1.62, lerp(obiY, kneeY, .55)), (hemR, kneeY + u * .22),
                    (lerp(hemL, hemR, .68), kneeY + u * .52), (lerp(hemL, hemR, .34), kneeY + u * .46),
                    (hemL, kneeY + u * .20), (hx - u * 1.60, lerp(obiY, kneeY, .55))])
    fill(catmull(hak, True, 6), P['hak'], key=key + 'hk', tex=.26, edge=.36, amp=1.2,
         outline=max(2.4, u * .12), ocol=INKC)
    for i in (-2, -1, 0, 1, 2):
        ink([(hx + i * u * .50, obiY + u * .18), (hx + i * u * .66, kneeY + u * .20)],
            max(1.3, u * .055), P['hakSh'], key=f'{key}pl{i}', closed=False, amp=1.0, a=120)
    shade(catmull(hak, True, 6), P['hakSh'], 46, key=key + 'hks', blur=9)

    # ---------------- torso + obi
    tw = u * 1.46
    torso = np.array([
        (shx - shHalf * .86 - sd * u * .2, shY), (shx + shHalf * .86 - sd * u * .2, shY),
        (cxx + tw, chY), (hx + u * 1.14, obiY), (hx + u * 1.20, hipY + u * .3),
        (hx - u * 1.18, hipY + u * .3), (hx - u * 1.12, obiY), (cxx - tw, chY)])
    fill(catmull(torso, True, 6), P['kimo'], key=key + 'to', tex=.24, edge=.36, amp=.9,
         outline=max(2.4, u * .12), ocol=INKC)
    col = np.array([(shx - u * .76 - sd * u * .2, shY - u * .14), (cxx + sd * u * .22, chY + u * .72),
                    (shx + u * .76 - sd * u * .2, shY - u * .16)])
    D = catmull(col, False, 9)
    c.drawPath(ribbon(boil(densify(D, False, 5), key + 'cv', .8, False), u * .26, u * .20, key=key + 'cvr', var=.1),
               skia.Paint(AntiAlias=True, Color=hexc('#CFC4AE')))
    ink(D, max(1.8, u * .09), INKC, key=key + 'cvo', closed=False, amp=.5, a=190)
    shade(catmull(torso, True, 6), P['kimoSh'], 50, key=key + 'tos', blur=9)
    ob = rrect(hx - u * 1.20, obiY - u * .38, u * 2.40, u * .84, u * .18)
    fill(ob, P['obi'], key=key + 'ob', tex=.24, edge=.36, amp=.6, outline=max(2.2, u * .11), ocol=INKC)
    shade(ob, P['obiSh'], 64, key=key + 'obs', blur=4)

    # ---------------- haori front panels
    def panel(side, zkey):
        sx0 = shx + side * shHalf * (0.78 + .2 * abs(fr)) - sd * u * .2
        top = shY - u * .22
        L = 5.4 * u
        outer, inner = [(sx0 + side * u * .30, top)], []
        n = 6
        for i in range(1, n + 1):
            f = i / n
            fl = (hw * (.50 + .85 * f) + .09 * math.sin(t * 2.1 + side * 1.3 + f * 3.4)) * u * (1.2 + f)
            outer.append((sx0 + side * u * (.44 + .62 * f) + fl + bend * u * f * -1.1,
                          top + L * f + .20 * u * math.sin(f * 4.2 + t * 2.6 + side)))
        for i in range(n, 0, -1):
            f = i / n
            fl = (hw * (.38 + .62 * f) + .07 * math.sin(t * 2.3 + side * 1.1 + f * 3.0)) * u * (.9 + f)
            inner.append((sx0 + side * u * (-.26 + .10 * f) + fl * .70 + bend * u * f * -.95,
                          top + L * f * .94 + .16 * u * math.sin(f * 3.6 + t * 2.2)))
        Q = np.array(outer + inner)
        pth = fill(catmull(Q, True, 6), P['haoG'], key=key + zkey, tex=.26, edge=.38, amp=1.1,
                   outline=max(2.4, u * .12), ocol=INKC)
        _checker(pth, sx0 + side * u * .2, top + u * .4, u * .60, key + zkey + 'c',
                 ang=0.09 * side + bend * .12)
        shade(catmull(Q, True, 6), P['haoGSh'], 40, key=key + zkey + 's', blur=10)

    panel(-1, 'hpL'); panel(1, 'hpR')

    # ---------------- arms + sword
    gu = o.get('grip', None)
    swAng = o.get('swAng', -0.9)
    K = None
    if gu is not None:
        K = katana_pts(x + gu[0] * u, y + gu[1] * u, swAng, u)

    def arm(sh, target, side, k2):
        el = ik(sh[0], sh[1], target[0], target[1], 2.25 * u, 2.15 * u, side=side)
        # haori sleeve over the upper arm, with a hanging flare
        d = math.atan2(el[1] - sh[1], el[0] - sh[0])
        nx2, ny2 = -math.sin(d), math.cos(d)
        fl = (hw * .5 + .08 * math.sin(t * 2.4 + side)) * u
        Q = np.array([(sh[0] + nx2 * u * .64, sh[1] + ny2 * u * .64),
                      (el[0] + nx2 * u * .76 + nx2 * fl, el[1] + ny2 * u * .76 + ny2 * fl + u * .30),
                      (el[0] + math.cos(d) * u * .30, el[1] + math.sin(d) * u * .30),
                      (el[0] - nx2 * u * .70, el[1] - ny2 * u * .70),
                      (sh[0] - nx2 * u * .66, sh[1] - ny2 * u * .66)])
        pth = fill(catmull(Q, True, 6), P['haoG'], key=key + 'sv' + k2, tex=.24, edge=.36, amp=.8,
                   outline=max(2.2, u * .11), ocol=INKC)
        _checker(pth, sh[0], sh[1], u * .50, key + 'svc' + k2, ang=d)
        shade(catmull(Q, True, 6), P['haoGSh'], 46, key=key + 'svs' + k2, blur=6)
        # forearm
        limb([(el[0], el[1]), ((el[0] + target[0]) / 2, (el[1] + target[1]) / 2), target],
             u * .40, u * .34, P['skin'], P['skinSh'], key + 'fa' + k2)
        return el

    if K is not None:
        gx = K['guard'][0] - K['dir'][0] * .55 * u
        gy = K['guard'][1] - K['dir'][1] * .55 * u
        bu = K['butt']
        h2 = (lerp(gx, bu[0], .62), lerp(gy, bu[1], .62))
        far, near = (sL, sR) if sd >= 0 else (sR, sL)
        if o.get('onehand'):
            rest = o.get('handRest', (-1.9, -8.4))
            arm(far, (x + rest[0] * u, y + rest[1] * u), 1.0, 'F')
            hand(x + rest[0] * u, y + rest[1] * u, u * .40, key + 'hR2')
            katana(K, key=key + 'kat', glow_k=o.get('glow', 0.0), gcol=o.get('gcol', '#7FD9F2'))
            arm(near, (gx, gy), -1.0, 'N')
            hand(gx, gy, u * .42, key + 'h1', a=K['ang'])
        else:
            arm(far, h2, 1.0, 'F')
            katana(K, key=key + 'kat', glow_k=o.get('glow', 0.0), gcol=o.get('gcol', '#7FD9F2'))
            hand(h2[0], h2[1], u * .40, key + 'h2', a=K['ang'])
            arm(near, (gx, gy), -1.0, 'N')
            hand(gx, gy, u * .42, key + 'h1', a=K['ang'])
    else:
        aL = o.get('handL', (-2.1, -9.0)); aR = o.get('handR', (2.1, -9.0))
        arm(sL, (x + aL[0] * u, y + aL[1] * u), 1.0, 'F')
        arm(sR, (x + aR[0] * u, y + aR[1] * u), -1.0, 'N')
        hand(x + aL[0] * u, y + aL[1] * u, u * .40, key + 'hL')
        hand(x + aR[0] * u, y + aR[1] * u, u * .40, key + 'hR')

    # ---------------- neck + head
    nk = np.array([(shx - u * .42 - sd * u * .15, shY + u * .14), (shx + u * .42 - sd * u * .15, shY + u * .14),
                   (headX + u * .36, headY + hu * .86), (headX - u * .36, headY + hu * .86)])
    fill(nk, P['skin'], key=key + 'nk', tex=.14, edge=.24, amp=.5, outline=max(2.0, u * .11), ocol=INKC)
    shade(nk, P['skinSh'], 80, key=key + 'nks', blur=5)
    head(headX, headY, hu, o, key=key + 'hd')
    return K
