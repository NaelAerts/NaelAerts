# slayer_water.py — Water Breathing effects in the Japanese woodblock idiom: layered translucent
# ribbons (dark base -> mid -> light -> foam), curling crests, round droplets, and real motion-blur
# sweeps built from the blade's own past positions.
import math
import numpy as np
import skia
from engine import *

WC = dict(
    dk='#11456E', md='#2287C0', lt='#5CC8E6', pale='#A8E8F6', foam='#EAFAFF',
    glow='#7FD9F2', deep='#0B2C4C', aqua='#39B6D6',
)

def _rib(D, w0, w1, col, key, a=255, var=.14):
    CTX.canvas.drawPath(ribbon(D, w0, w1, key=key, var=var),
                        skia.Paint(AntiAlias=True, Color=hexc(col, a)))

def _nrm(D):
    d = np.gradient(np.asarray(D, np.float64), axis=0)
    n = np.stack([-d[:, 1], d[:, 0]], 1)
    return n / np.maximum(np.hypot(n[:, 0], n[:, 1]), 1e-6)[:, None]

# ---------------------------------------------------------------- the core water ribbon
def wave(pts, w0, w1=None, key='wv', a=1.0, glowk=.5, curl=0.0, foam=1.0, side=1.0, boilamp=1.6):
    """A flowing band of water along pts. Layers inward so it reads translucent and lit.
    curl>0 spawns hooked crests along the upper edge (the Hokusai claw)."""
    pts = np.asarray(pts, np.float64)
    if len(pts) < 3: return
    w1 = w0 * .35 if w1 is None else w1
    D = densify(catmull(pts, False, 8), False, 7)
    D = boil(D, key + 'b', boilamp, False)
    A = int(255 * clamp(a))
    if A <= 2: return
    nrm = _nrm(D)
    if glowk > 0:
        step = max(1, len(D) // 16)
        for i in range(0, len(D), step):
            f = i / max(1, len(D) - 1)
            glow(float(D[i, 0]), float(D[i, 1]), lerp(w0, w1, f) * 2.1, WC['glow'], .30 * glowk * a)
    _rib(D, w0 * 1.08, w1 * 1.08, WC['deep'], key + 'o', int(A * .50))
    _rib(D, w0, w1, WC['dk'], key + 'd', int(A * .80))
    _rib(D + nrm * (w0 * .10 * side), w0 * .74, w1 * .74, WC['md'], key + 'm', int(A * .88))
    _rib(D + nrm * (w0 * .20 * side), w0 * .44, w1 * .44, WC['lt'], key + 'l', int(A * .92))
    _rib(D + nrm * (w0 * .28 * side), w0 * .18, w1 * .18, WC['pale'], key + 'p', int(A * .95))
    if foam > 0:
        E = D + nrm * (w0 * .40 * side)
        _rib(E[1:-1], w0 * .085 * foam, w1 * .07 * foam, WC['foam'], key + 'f', int(A * .92))
        F = D - nrm * (w0 * .44 * side)
        _rib(F[2:-2], w0 * .055 * foam, w1 * .045 * foam, WC['pale'], key + 'f2', int(A * .62))
    if curl > 0:
        n = max(2, int(curl * 7))
        for i in range(n):
            f = .10 + .80 * (i / max(1, n - 1.0))
            j = int(f * (len(D) - 1))
            wj = lerp(w0, w1, f)
            px, py = nrm[j]
            bx, by = D[j, 0] + px * wj * .44 * side, D[j, 1] + py * wj * .44 * side
            dx, dy = (D[min(j + 2, len(D) - 1)] - D[max(j - 2, 0)])
            dl = math.hypot(dx, dy) + 1e-6
            dx, dy = dx / dl, dy / dl
            R = wj * (.52 + .34 * math.sin(i * 2.3 + CTX.t * 3.1))
            Q = []
            for k2 in range(11):
                aa = k2 / 10.0
                ang = aa * math.pi * 1.55
                rr = R * (1 - aa * .62)
                Q.append((bx + dx * rr * math.cos(ang) + px * side * rr * math.sin(ang) * 1.15,
                          by + dy * rr * math.cos(ang) + py * side * rr * math.sin(ang) * 1.15))
            Q = np.array(Q)
            Dc = boil(densify(catmull(Q, False, 6), False, 5), f'{key}c{i}', 1.0, False)
            _rib(Dc, wj * .30, wj * .045, WC['lt'], f'{key}cl{i}', int(A * .88))
            _rib(Dc, wj * .14, wj * .02, WC['foam'], f'{key}cf{i}', int(A * .92))

# ---------------------------------------------------------------- droplets & spray
def drops(key, pts, n=14, s0=5.0, s1=16.0, a=1.0, spread=26.0, seed=0, t=None):
    """round droplets scattered along a path, each with a highlight"""
    pts = np.asarray(pts, np.float64)
    if len(pts) < 2: return
    t = CTX.t if t is None else t
    r = np.random.default_rng(zlib_seed(key, seed))
    for i in range(n):
        f = r.random()
        j = min(len(pts) - 1, int(f * (len(pts) - 1)))
        nx, ny = _nrm(pts)[j] if len(pts) > 2 else (0, -1)
        off = (r.random() - .5) * 2 * spread
        rr = lerp(s0, s1, r.random())
        x = pts[j, 0] + nx * off + (r.random() - .5) * spread * .7
        y = pts[j, 1] + ny * off + (r.random() - .5) * spread * .7
        Q = ell(x, y, rr, rr * (1.0 + .28 * math.sin(t * 6 + i)), 14, r.random() * 3)
        A = int(235 * clamp(a))
        fill(Q, WC['lt'], key=f'{key}d{i}', tex=.1, edge=.25, amp=.6, a=A)
        wash(ell(x - rr * .3, y - rr * .34, rr * .40, rr * .30, 10), WC['foam'], key=f'{key}dh{i}', a=int(A * .9))

def zlib_seed(*a):
    import zlib
    return zlib.crc32(('|'.join(map(str, a))).encode()) & 0x7fffffff

def spray(x, y, k, n=22, key='sp', R=240.0, a=1.0, ang0=-math.pi, ang1=0.0, s=1.0):
    """burst of droplets + streaks flying outward; k = 0..1 life"""
    if k <= 0 or k >= 1.4: return
    r = np.random.default_rng(zlib_seed(key))
    for i in range(n):
        ang = lerp(ang0, ang1, r.random())
        v = (.45 + r.random()) * R * s
        d = v * easeOut(min(1, k * 1.25))
        px, py = x + math.cos(ang) * d, y + math.sin(ang) * d + (k ** 2) * 190 * s
        al = clamp(1 - k) * a
        rr = (4 + r.random() * 9) * s * (1 - k * .35)
        if al <= .02: continue
        # an elongated droplet instead of a pin: stretched along its own motion
        st = 1.0 + 0.8 * clamp(v / (R * s + 1e-6))
        fill(ell(px, py, rr * st, rr, 14, ang), WC['lt'], key=f'{key}s{i}', tex=.08, edge=.22,
             amp=.5, a=int(215 * al))
        wash(ell(px - math.cos(ang) * rr * .25, py - math.sin(ang) * rr * .25, rr * .5, rr * .40, 10),
             WC['pale'], key=f'{key}p{i}', a=int(225 * al))
        if i % 3 == 0:
            glow(px, py, rr * 3.2, WC['glow'], .35 * al)

# ---------------------------------------------------------------- blade motion blur
def blade_sweep(spines, key='sw', a=1.0, glowk=.8, water=1.0):
    """spines: list of blade spine arrays, newest FIRST. Fills the quads swept between
    consecutive blade positions -> genuine motion blur, then skins it with water."""
    if len(spines) < 2: return
    n = len(spines)
    for i in range(n - 1, 0, -1):
        f = 1.0 - i / float(n)          # 0 = oldest, 1 = newest
        A = clamp(a * (f ** 1.5))
        if A <= .015: continue
        s0, s1 = spines[i], spines[i - 1]
        m = min(len(s0), len(s1))
        quad = np.vstack([s0[:m], s1[:m][::-1]])
        col = mix(WC['md'], WC['lt'], f)
        wash(quad, col, key=f'{key}q{i}', a=int(26 * A * water))
        if f > .62:
            wash(np.vstack([s0[:m] * .35 + s1[:m] * .65, s1[:m][::-1]]), WC['pale'],
                 key=f'{key}h{i}', a=int(18 * A))
    # bright leading edge along the newest blade
    lead = spines[0]
    _rib(densify(lead, False, 7), 11 * water, 3.0, WC['foam'], key + 'le', int(235 * clamp(a)))
    if glowk > 0:
        for i in range(0, len(lead), 4):
            glow(float(lead[i, 0]), float(lead[i, 1]), 46 * glowk, WC['glow'], .40 * glowk * a)

def trail_ribbon(hist, w0=56.0, key='tr', a=1.0, curl=.6):
    """water ribbon along a point history (newest first) — the arc the tip has carved"""
    hist = np.asarray(hist, np.float64)
    if len(hist) < 3: return
    wave(hist[::-1], w0 * .30, w0, key=key, a=a, glowk=.8, curl=curl, foam=1.0, side=1.0)

# ---------------------------------------------------------------- circular water trails
def ring_arc(cx, cy, rx, ry, a0, a1, w, key='ra', t=None, a=1.0, curl=.7, tilt=0.0, phase=0.0):
    """Elliptical water arc (perspective circle) from a0 to a1 radians. The scene draws the far
    half before the character and the near half after, so the ring truly wraps around him."""
    t = CTX.t if t is None else t
    n = max(8, int(abs(a1 - a0) * 13))
    ang = np.linspace(a0, a1, n)
    wob = 1.0 + .055 * np.sin(ang * 3.0 + t * 5.0 + phase) + .035 * np.sin(ang * 5.0 - t * 3.4)
    X = cx + np.cos(ang) * rx * wob
    Y = cy + np.sin(ang) * ry * wob
    if tilt:
        ct, stt = math.cos(tilt), math.sin(tilt)
        dx, dy = X - cx, Y - cy
        X, Y = cx + dx * ct - dy * stt, cy + dx * stt + dy * ct
    Q = np.stack([X, Y], 1)
    # width swells through the middle of the arc
    s = np.linspace(0, 1, n)
    env = np.sin(s * math.pi) ** .55
    wave(Q, w * float(env[max(1, n // 6)]) * .55 + 3, w, key=key, a=a, glowk=.75, curl=curl, foam=1.0)
    return Q

def ripple(x, y, r, k, key='rp', a=1.0, ry=.28):
    """expanding flat ring on the ground"""
    if k <= 0 or k >= 1: return
    rr = r * easeOut(k)
    al = clamp(1 - k) * a
    Q = ell(x, y, rr, rr * ry, 40)
    D = boil(densify(Q, True, 8), key, 2.0, True)
    _rib(np.vstack([D, D[:1]]), 9 * (1 - k * .5), 5 * (1 - k * .5), WC['lt'], key + 'r', int(190 * al))
    _rib(np.vstack([D, D[:1]]), 3.4 * (1 - k * .5), 2.0, WC['foam'], key + 'f', int(210 * al))

def splash_crown(x, y, k, s=1.0, key='sc', a=1.0, n=9):
    """water thrown up in a crown — rises then falls"""
    if k <= 0 or k >= 1.25: return
    up = math.sin(min(1, k) * math.pi * .92)
    for i in range(n):
        f = i / (n - 1.0)
        ang = lerp(-2.75, -0.40, f)
        L = (120 + 150 * math.sin(f * math.pi)) * s
        bx, by = x + math.cos(ang) * 26 * s, y
        tx = bx + math.cos(ang) * L * (.5 + .9 * up)
        ty = by + math.sin(ang) * L * (.55 + .85 * up) + (k ** 2) * 150 * s
        Q = np.array([(bx, by), ((bx + tx) / 2 + math.cos(ang) * 14, (by + ty) / 2 - 18 * up), (tx, ty)])
        al = clamp(1.15 - k) * a
        wave(Q, 25 * s * up + 4, 5 * s, key=f'{key}{i}', a=al * .95, glowk=.5, curl=.25 if i % 2 else 0, foam=1.0)
    drops(key + 'dr', np.array([(x - 150 * s, y - 120 * s * up), (x, y - 190 * s * up), (x + 150 * s, y - 120 * s * up)]),
          n=int(12 * s + 6), s0=4, s1=13 * s, a=clamp(1.1 - k) * a, spread=70 * s)

# ---------------------------------------------------------------- gentle rain (the "blessed rain")
def rain(t, n=150, key='rn', a=1.0, speed=1.0, px=0.0, wind=.18, L=46.0, cols=None):
    """soft falling rain streaks, drifting with the wind"""
    if a <= .01: return
    r = np.random.default_rng(zlib_seed(key))
    c = CTX.canvas
    for i in range(n):
        sp = .7 + r.random() * .8
        ph = r.random()
        y0 = ((t * 620 * sp * speed + ph * (H + 500)) % (H + 500)) - 250
        x0 = (r.random() * (W + 700) - 350 + y0 * wind - px * .35) % (W + 700) - 350
        ln = L * (.6 + r.random() * .9) * sp
        al = int(170 * a * (.45 + .55 * r.random()))
        p = skia.Paint(AntiAlias=True, Color=hexc(WC['pale'], al), StrokeWidth=1.1 + r.random() * 1.9)
        p.setStyle(skia.Paint.kStroke_Style)
        c.drawLine(x0, y0, x0 + ln * wind * 1.5, y0 + ln, p)
    # a few bright foreground streaks
    for i in range(max(3, n // 14)):
        sp = 1.3 + r.random() * .7
        y0 = ((t * 980 * sp * speed + r.random() * H * 2) % (H + 700)) - 350
        x0 = (r.random() * (W + 400) - 200 - px * .5) % (W + 400) - 200
        ln = 150 * sp
        p = skia.Paint(AntiAlias=True, Color=hexc(WC['foam'], int(120 * a)), StrokeWidth=3.4)
        p.setStyle(skia.Paint.kStroke_Style)
        c.drawLine(x0, y0, x0 + ln * wind * 1.6, y0 + ln, p)

def rain_impacts(t, gy, n=18, key='ri', a=1.0, x0=-200, x1=None):
    """little rings and ticks where rain meets the ground"""
    x1 = (W + 200) if x1 is None else x1
    r = np.random.default_rng(zlib_seed(key))
    for i in range(n):
        ph = r.random() * 2.2
        k = ((t * 1.7 + ph) % 1.0)
        xx = lerp(x0, x1, r.random())
        yy = gy + r.random() * 86
        ripple(xx, yy, 26 + r.random() * 30, k, key=f'{key}{i}', a=a * .8)

# ---------------------------------------------------------------- misc
def aura(x, y, r, k=1.0, key='au', col=None, n=5):
    """swirling water aura around a point (gathering energy)"""
    col = col or WC['lt']
    if k <= 0: return
    t = CTX.t
    glow(x, y, r * 1.5 * k, WC['glow'], .30 * k)
    for i in range(n):
        f = i / float(n)
        a0 = t * (1.5 + f * 1.4) + f * 6.283
        rr = r * (.52 + .46 * f) * (0.92 + .08 * math.sin(t * 4 + i))
        Q = []
        for j in range(12):
            aa = a0 + j * .30
            rj = rr * (1 - j * .018)
            Q.append((x + math.cos(aa) * rj, y + math.sin(aa) * rj * .52))
        wave(np.array(Q), r * .10 * k + 2, r * .028 * k + 1, key=f'{key}{i}',
             a=k * (.55 + .4 * f), glowk=.4, curl=0, foam=1.0)

def mist_veil(y, k=1.0, key='mv', col=None, n=7, amp=1.0):
    """low-lying water vapour drifting across the ground"""
    col = col or WC['pale']
    t = CTX.t
    for i in range(n):
        dx = ((t * (16 + i * 9)) % (W + 1000)) - 500
        yy = y + (i % 3) * 42 - 20
        shade(ell(dx, yy, 300 * amp, 42 * amp, 24), col, int(34 * k), key=f'{key}{i}', blur=26)
