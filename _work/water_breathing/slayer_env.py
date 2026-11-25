# slayer_env.py — cinematic night environment, drawn in layers with parallax so the camera
# can push in and orbit. Every layer takes px (pan, in world px) and scales its own shift.
import math
import numpy as np
import skia
from engine import *

E = dict(
    sky0='#0C1026', sky1='#172544', sky2='#27425F', sky3='#3E6B7E',
    moon='#F6F2DE', moonG='#BFE2E8',
    far='#2A3C5C', mid='#1E2C49', near='#141D37', grove='#0F1628',
    rock='#28334C', rockLt='#38455F', rockDk='#1A2235',
    pool='#2A5473', poolLt='#4E89A6', poolDk='#17374F',
    mist='#9CC2D2', petal='#E7B2C2', petalDk='#C98598',
    fire='#F7D98A', star='#E8F2FF',
)

# ---------------------------------------------------------------- sky
def sky(t, px=0.0, zoom=1.0, dawn=0.0):
    c = CTX.canvas
    cols = [mix(E['sky0'], '#1A2142', dawn), mix(E['sky1'], '#2C3A5E', dawn),
            mix(E['sky2'], '#4A5E78', dawn), mix(E['sky3'], '#79909A', dawn)]
    grad_rect(-200, -200, W + 400, H + 400, cols, [0, .42, .76, 1.0])
    # stars
    r = np.random.default_rng(21)
    for i in range(70):
        sx = (r.random() * (W + 600) - 300 - px * .04) % (W + 600) - 300
        sy = r.random() * H * .62
        tw = .45 + .55 * abs(math.sin(t * (.7 + r.random() * 1.6) + i))
        rr = 1.1 + r.random() * 2.0
        glow(sx, sy, rr * 3.4, E['star'], .30 * tw)
        wash(ell(sx, sy, rr, rr, 8), E['star'], key=f'st{i}', a=int(190 * tw))
    # moon
    mx, my = W * .765 - px * .055, H * .155
    glow(mx, my, 300, E['moonG'], .22)
    glow(mx, my, 150, E['moon'], .34)
    fill(ell(mx, my, 76, 76, 40), E['moon'], key='moon', tex=.18, edge=.12, amp=1.0)
    for (dx, dy, rr) in ((-22, -14, 15), (18, 10, 20), (-6, 26, 10), (30, -24, 8)):
        wash(ell(mx + dx, my + dy, rr, rr * .9, 14), '#E2DCC2', key=f'mc{dx}', a=90)
    # thin cloud bands across the moon
    for i in range(4):
        y0 = H * (.13 + i * .075)
        dx = (t * (7 + i * 4) - px * .07) % (W + 1200) - 600
        Q = [(dx - 420, y0), (dx - 150, y0 - 16 - i * 4), (dx + 160, y0 + 10), (dx + 440, y0 - 6)]
        D = catmull(np.array(Q), False, 10)
        CTX.canvas.drawPath(ribbon(D, 24 + i * 7, 16 + i * 5, key=f'cl{i}', var=.3),
                            skia.Paint(AntiAlias=True, Color=hexc(mix(E['sky2'], '#8FB0BE', .35), 60)))

# ---------------------------------------------------------------- mountains
def _ridge(seed, ybase, amp, col, px, par, key, n=16, spikes=1.0):
    """rolling asymmetric ridge from layered sines plus a few sharper peaks"""
    r = np.random.default_rng(seed)
    m = 110
    xs = np.linspace(-700, W + 700, m)
    span = float(xs[-1] - xs[0])
    ph = r.random(5) * 6.283
    prof = np.zeros(m)
    for k, (f, wgt) in enumerate(((0.55, 1.0), (1.3, .55), (2.7, .30), (5.1, .16))):
        prof += np.sin(xs / span * 6.283 * f + ph[k]) * wgt
    prof = (prof - prof.min()) / max(1e-6, float(np.ptp(prof)))
    for k in range(3):
        c0 = r.random() * span + xs[0]
        wd = 180 + r.random() * 320
        prof = prof + np.exp(-((xs - c0) / wd) ** 2) * (.45 + r.random() * .75) * spikes
    prof = prof / max(1e-6, prof.max())
    ys = ybase - prof * amp
    Q = np.stack([xs - px * par, ys], 1)
    D = catmull(Q, False, 3)
    P2 = np.vstack([D, [[W + 900 - px * par, H + 400], [-900 - px * par, H + 400]]])
    fill(P2, col, key=key, tex=.26, edge=.28, amp=1.6)

def ridges(t, px=0.0, dawn=0.0):
    _ridge(3, H * .60, 150, mix(E['far'], '#546C80', dawn), px, .10, 'rg0', 15, 1.0)
    _ridge(9, H * .66, 120, mix(E['mid'], '#3E5168', dawn), px, .20, 'rg1', 13, 1.2)
    _ridge(17, H * .72, 95, mix(E['near'], '#2A3850', dawn), px, .34, 'rg2', 11, 1.1)
    # mist band between ridges
    for i in range(3):
        y0 = H * (.60 + i * .045)
        a = 44 - i * 8
        dx = (t * (5 + i * 3) - px * .16) % 900 - 450
        for j in range(5):
            xx = dx + j * 480 - 300
            shade(ell(xx, y0, 330, 34 + i * 10, 24), E['mist'], a, key=f'mb{i}{j}', blur=22)

def grove(t, px=0.0, side='both', a=1.0):
    """bamboo/pine silhouettes framing the frame"""
    r = np.random.default_rng(5)
    stalks = []
    if side in ('both', 'left'):
        stalks += [(-160 + i * 78, .9 + r.random() * .5, i) for i in range(5)]
    if side in ('both', 'right'):
        stalks += [(W + 150 - i * 84, .9 + r.random() * .5, 20 + i) for i in range(5)]
    for (bx, sc, i) in stalks:
        par = .62 + (i % 3) * .07
        X = bx - px * par
        sway = math.sin(t * .8 + i) * 16 + math.sin(t * 1.9 + i * 2.1) * 6
        top = H * (-.12 - .05 * (i % 3))
        Q = catmull([(X, H + 120), (X + sway * .3, H * .55), (X + sway, top)], False, 12)
        D = boil(densify(Q, False, 8), f'bam{i}', 1.6, False)
        CTX.canvas.drawPath(ribbon(D, 30 * sc, 15 * sc, key=f'bamr{i}', var=.16),
                            skia.Paint(AntiAlias=True, Color=hexc(E['grove'], int(255 * a))))
        # leaf clusters
        for j in range(4):
            f = .28 + j * .19
            lx = X + sway * (1 - f) * 1.0
            ly = lerp(H + 120, top, 1 - f * .92)
            for k2 in range(5):
                ang = -1.9 + k2 * .55 + math.sin(t * 1.3 + j + k2) * .12
                L = 86 * sc * (.6 + .3 * ((k2 * 7 + j * 3) % 5) / 4)
                Q2 = catmull([(lx, ly), (lx + math.cos(ang) * L * .5, ly + math.sin(ang) * L * .5 - 10),
                              (lx + math.cos(ang) * L, ly + math.sin(ang) * L)], False, 7)
                CTX.canvas.drawPath(ribbon(Q2, 11 * sc, 1.6, key=f'lf{i}{j}{k2}', var=.2),
                                    skia.Paint(AntiAlias=True, Color=hexc(E['grove'], int(255 * a))))

# ---------------------------------------------------------------- ground
GY = H * .80       # world ground line (at zoom 1, cam centred)
def ground(t, px=0.0, gy=None, pool=True):
    gy = GY if gy is None else gy
    c = CTX.canvas
    # rock plateau
    xs = np.linspace(-800, W + 800, 22)
    r = np.random.default_rng(31)
    ys = gy + np.sin(xs * .004 + 1.2) * 9 + r.normal(0, 4.5, len(xs))
    Q = np.stack([xs - px * .9, ys], 1)
    D = catmull(Q, False, 6)
    fill(np.vstack([D, [[W + 900, H + 300], [-900, H + 300]]]), E['rock'], key='gnd', tex=.30, edge=.34, amp=2.0)
    # slabs / cracks
    for i in range(11):
        sx = -400 + i * 230 - px * .9
        sy = gy + 26 + (i % 3) * 48
        Q2 = [(sx, sy), (sx + 90, sy + 10 + (i % 2) * 8), (sx + 190, sy - 6)]
        ink(catmull(np.array(Q2), False, 8), 2.6, E['rockDk'], key=f'cr{i}', closed=False, amp=2.0, a=150)
    # lit top edge of the plateau
    ink(D, 3.4, E['rockLt'], key='gedge', closed=False, amp=1.2, a=130)
    if not pool: return
    # shallow pools reflecting the sky
    for i, (ox, w2, h2) in enumerate(((-260, 300, 30), (240, 390, 36), (760, 300, 26), (1290, 420, 34), (1860, 300, 28))):
        cxp = ox - px * .9
        Q3 = ell(cxp, gy + 60 + (i % 2) * 42, w2, h2, 26)
        fill(Q3, E['pool'], key=f'pl{i}', tex=.18, edge=.30, amp=2.2)
        wash(ell(cxp - w2 * .2, gy + 54 + (i % 2) * 42, w2 * .5, h2 * .34, 18), E['poolLt'], key=f'plh{i}', a=120)
        # moon glints wobbling on the surface
        for j in range(3):
            gx2 = cxp + (j - 1) * w2 * .40
            gy2 = gy + 60 + (i % 2) * 42 + math.sin(t * 2.2 + i + j) * 3
            wash(ell(gx2, gy2, w2 * .16, 2.6, 10), '#CFEAF2', key=f'plg{i}{j}', a=int(120 + 60 * math.sin(t * 3 + j)))

def petals(t, px=0.0, n=16, key='pt', a=1.0, speed=1.0):
    r = np.random.default_rng(13)
    for i in range(n):
        ph = r.random(); sp = .5 + r.random()
        yy = ((t * 26 * sp * speed + ph * H * 1.5) % (H + 300)) - 120
        xx = (r.random() * (W + 500) - 250 + math.sin(t * .9 * sp + i) * 70 - px * .5) % (W + 500) - 250
        s = 7 + r.random() * 7
        rot = t * (1.2 + sp) + i
        Q = np.array([(xx - s, yy), (xx, yy - s * .62), (xx + s, yy), (xx, yy + s * .62)])
        Q = np.stack([xx + (Q[:, 0] - xx) * math.cos(rot) - (Q[:, 1] - yy) * math.sin(rot) * .5,
                      yy + (Q[:, 0] - xx) * math.sin(rot) * .5 + (Q[:, 1] - yy) * math.cos(rot)], 1)
        col = E['petal'] if i % 3 else E['petalDk']
        fill(Q, col, key=f'{key}{i}', tex=.1, edge=.2, amp=.5, a=int(210 * a))

def fireflies(t, px=0.0, n=14, key='ff', a=1.0):
    r = np.random.default_rng(77)
    for i in range(n):
        sp = .4 + r.random() * .8
        xx = (r.random() * W + math.sin(t * sp + i * 2.1) * 120 - px * .55) % (W + 300) - 150
        yy = H * (.42 + r.random() * .46) + math.sin(t * sp * 1.7 + i) * 40
        k = .45 + .55 * abs(math.sin(t * (1.1 + sp) + i * 1.7))
        glow(xx, yy, 26 * k, E['fire'], .5 * k * a)
        wash(ell(xx, yy, 2.6, 2.6, 8), '#FFF6CE', key=f'{key}{i}', a=int(230 * k * a))

def vignette(k=.55, col='#070A16'):
    """cinematic corner darkening (screen space)"""
    c = CTX.canvas
    p = skia.Paint(AntiAlias=True)
    cc = hexc(col)
    p.setShader(skia.GradientShader.MakeRadial(
        (W / 2, H * .52), W * .78,
        [skia.ColorSetA(cc, 0), skia.ColorSetA(cc, int(70 * k)), skia.ColorSetA(cc, int(225 * k))], [0, .62, 1.0]))
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, H), p)

def letterbox(h=0.0, col='#05070E'):
    if h <= 0: return
    c = CTX.canvas
    p = skia.Paint(Color=hexc(col))
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, H * h), p)
    c.drawRect(skia.Rect.MakeXYWH(0, H * (1 - h), W, H * h), p)

def moonlight(k=1.0, col='#9FD4E6'):
    """cool rim light wash from the upper right (screen space, additive)"""
    if k <= 0: return
    c = CTX.canvas
    p = skia.Paint(AntiAlias=True)
    cc = hexc(col)
    p.setShader(skia.GradientShader.MakeLinear(
        [(W * 1.02, 0), (W * .18, H)],
        [skia.ColorSetA(cc, int(44 * k)), skia.ColorSetA(cc, int(12 * k)), skia.ColorSetA(cc, 0)], [0, .45, 1]))
    p.setBlendMode(skia.BlendMode.kPlus)
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W, H), p)
