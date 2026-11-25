# sound.py — sound design for "Water Breathing, Fifth Form", synthesised from scratch.
# Every cue is built from noise and oscillators (no samples, no library audio), then placed
# against the animation's own beats: the cut at 3.00, the blade lift at 4.45, the strike at
# 6.02 with its two follow-throughs, the flick at 9.64, and the rain that takes over from 8.2.
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 12.0
N = int(DUR * SR)
RNG = np.random.default_rng(1973)

# ---------------------------------------------------------------- primitives
def nz(n):            return RNG.standard_normal(int(n)).astype(np.float64)
def T(n):             return np.arange(int(n)) / SR
def hump(n, p=2.0):   return np.sin(np.pi * np.arange(int(n)) / int(n)) ** p
def env(n, a, d, p=1.0):
    t = T(n); return np.minimum(1.0, t / max(a, 1e-5)) * np.exp(-t * d) ** p

def _sos(kind, f, q=0.707, order=2):
    f = np.atleast_1d(f).astype(float)
    f = np.clip(f, 20.0, SR / 2 - 100.0)
    return signal.butter(order, f if len(f) > 1 else f[0], kind, fs=SR, output='sos')
def lp(x, f, order=2):  return signal.sosfilt(_sos('low', f, order=order), x)
def hp(x, f, order=2):  return signal.sosfilt(_sos('high', f, order=order), x)
def bp(x, lo, hi, order=2):
    lo, hi = max(20.0, lo), min(SR / 2 - 100.0, hi)
    if hi <= lo * 1.05: hi = lo * 1.3
    return signal.sosfilt(signal.butter(order, [lo, hi], 'band', fs=SR, output='sos'), x)

def sweep_bp(x, f0, f1, q=0.55, curve=1.0, chunk=512):
    """band-pass whose centre glides f0 -> f1 across the buffer (the whoosh engine)"""
    n = len(x); out = np.zeros(n)
    for s in range(0, n, chunk):
        k = (s / max(1, n)) ** curve
        c = f0 * (f1 / f0) ** k
        out[s:s + chunk] = bp(x[s:s + chunk], c * (1 - q), c * (1 + q))
    return out

def fm_sine(n, f_curve, phase=0.0):
    return np.sin(2 * np.pi * np.cumsum(np.asarray(f_curve, float)) / SR + phase)

# ---------------------------------------------------------------- voices
def wind(d, lo=90, hi=950, gust=0.55, seed=0):
    """night wind over the plateau: low-passed noise with slow gusting"""
    n = int(d * SR); x = bp(nz(n), lo, hi, order=2)
    t = T(n)
    g = (1 - gust) + gust * (0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t + seed)) * \
        (0.6 + 0.4 * np.sin(2 * np.pi * 0.41 * t + seed * 2.1))
    # slow timbral movement so it never sits still
    x = x * g
    return x + 0.35 * lp(nz(n), 160)

def water_rush(d, lo=380, hi=5200, mod=0.45, seed=0):
    """the body of moving water — bright noise with rolling amplitude"""
    n = int(d * SR); t = T(n)
    x = bp(nz(n), lo, hi, order=2)
    m = (1 - mod) + mod * (0.5 + 0.5 * np.sin(2 * np.pi * 2.3 * t + seed)) * \
        (0.55 + 0.45 * np.sin(2 * np.pi * 5.7 * t + seed * 1.7))
    return x * m

def rain_bed(d, density=0.55, seed=3):
    """steady rain: hiss plus a scatter of individual drop transients"""
    n = int(d * SR)
    r = np.random.default_rng(100 + seed)
    hiss = hp(r.standard_normal(n), 1800, order=2) * 0.45
    hiss += bp(r.standard_normal(n), 400, 1400, order=2) * 0.22
    # discrete droplets ticking on stone
    ticks = np.zeros(n)
    k = int(900 * density * d)
    idx = r.integers(0, n - 2000, k)
    for i in idx:
        dd = int(r.uniform(0.004, 0.016) * SR)
        f = r.uniform(1800, 7000)
        ticks[i:i + dd] += np.sin(2 * np.pi * f * T(dd)) * np.exp(-T(dd) * 320) * r.uniform(.2, 1.0)
    return hiss + ticks * 0.5

def droplet(f0=2600, f1=900, d=0.16, bright=1.0):
    """a single water drop: resonant ping falling in pitch"""
    n = int(d * SR); t = T(n)
    f = f1 + (f0 - f1) * np.exp(-t * 26)
    s = fm_sine(n, f) * np.exp(-t * 24)
    s += bp(nz(n), 2500, 9000) * np.exp(-t * 90) * 0.25 * bright
    return s * np.minimum(1, t / 0.0012)

def air_whoosh(d=0.42, f0=260, f1=4200, curve=1.0, q=0.6, p=1.6):
    """blade cutting air"""
    n = int(d * SR)
    return sweep_bp(nz(n), f0, f1, q=q, curve=curve) * hump(n, p)

def water_slash(d=0.6, f0=500, f1=6000):
    """air whoosh fused with a sheet of water torn off the arc"""
    n = int(d * SR); t = T(n)
    a = sweep_bp(nz(n), f0, f1, q=0.62, curve=0.8) * hump(n, 1.4)
    w = bp(nz(n), 700, 7000) * np.exp(-t * 7) * 0.9
    sub = fm_sine(n, 120 * np.exp(-t * 9) + 46) * np.exp(-t * 8) * 0.55
    return a + w + sub

def splash(d=0.75, size=1.0):
    """water thrown up and falling back"""
    n = int(d * SR); t = T(n)
    body = bp(nz(n), 260 / size, 3800 * size) * np.exp(-t * 5.5)
    fizz = hp(nz(n), 3500) * np.exp(-t * 3.2) * 0.5
    s = body + fizz
    for k in range(int(10 * size)):
        i = int(RNG.uniform(0.04, 0.7) * n)
        g = droplet(RNG.uniform(1800, 3600), RNG.uniform(700, 1300), 0.12) * RNG.uniform(.15, .45)
        s[i:i + len(g)] += g[:max(0, n - i)]
    return s

def shing(d=1.1, f=2150, metal=1.0):
    """nichirin steel: inharmonic partials ringing out"""
    n = int(d * SR); t = T(n)
    s = np.zeros(n)
    for m, a, k in ((1.0, 1.0, 3.4), (2.03, .55, 4.6), (3.11, .32, 6.2),
                    (4.37, .20, 8.0), (5.81, .12, 10.5), (7.42, .07, 13.0)):
        s += a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * k)
    s += bp(nz(n), 4000, 12000) * np.exp(-t * 70) * 0.35 * metal   # strike transient
    return s * np.minimum(1, t / 0.0015) / 2.2

def taiko(d=1.4, f0=105, f1=44, body=1.0):
    """deep drum: pitch-dropping sine with a skin transient"""
    n = int(d * SR); t = T(n)
    f = f1 + (f0 - f1) * np.exp(-t * 7.5)
    s = fm_sine(n, f) * np.exp(-t * 3.4) * body
    s += fm_sine(n, f * 2.02) * np.exp(-t * 7.0) * 0.28
    s += bp(nz(n), 180, 2600) * np.exp(-t * 34) * 0.5
    return s * np.minimum(1, t / 0.0012)

def cloth(d=0.33):
    """haori snapping in the wind"""
    n = int(d * SR); t = T(n)
    s = bp(nz(n), 420, 4200) * np.exp(-t * 11)
    return s * (0.5 + 0.5 * np.sin(2 * np.pi * 15 * t))

def drone(d, f=48.0, fifth=True):
    """sub bed under the drama — a tone, not a melody"""
    n = int(d * SR); t = T(n)
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2 * t + 1.1)
    if fifth: s += 0.3 * np.sin(2 * np.pi * f * 1.5 * t + .4)
    return s * 0.5

def shimmer(d, f0=900, f1=6400, up=True):
    """water energy gathering: noise sweeping upward with a glassy edge"""
    n = int(d * SR); t = T(n)
    a, b = (f0, f1) if up else (f1, f0)
    s = sweep_bp(nz(n), a, b, q=0.5, curve=0.75)
    ring = sum(np.sin(2 * np.pi * fq * t) * np.exp(-np.maximum(t - .1, 0) * 1.5)
               for fq in (1570, 2350, 3140)) * 0.04
    return s * np.minimum(1, t / 0.05) + ring * hump(n, 1.2)

# ---------------------------------------------------------------- mixing
class Mix:
    def __init__(self):
        self.b = np.zeros((N, 2))
    def put(self, t0, s, g=1.0, pan=0.0, pan_to=None):
        i = int(t0 * SR)
        if i >= N: return
        s = np.asarray(s, float)
        n = min(len(s), N - i)
        if n <= 0: return
        s = s[:n]
        if pan_to is None:
            a = (np.clip(pan, -1, 1) + 1) * np.pi / 4
            l, r = np.cos(a), np.sin(a)
        else:
            pp = np.linspace(pan, pan_to, n)
            a = (np.clip(pp, -1, 1) + 1) * np.pi / 4
            l, r = np.cos(a), np.sin(a)
        if i < 0:
            s = s[-i:]; l = l if np.isscalar(l) else l[-i:]; r = r if np.isscalar(r) else r[-i:]; n = len(s); i = 0
        self.b[i:i + n, 0] += s * g * l
        self.b[i:i + n, 1] += s * g * r
    def put_st(self, t0, left, right, g=1.0):
        i = int(t0 * SR); n = min(len(left), N - i)
        if n <= 0: return
        self.b[i:i + n, 0] += left[:n] * g
        self.b[i:i + n, 1] += right[:n] * g

def ramp(t0, t1, v0, v1, n=None):
    """sample-rate gain ramp over the whole timeline"""
    g = np.zeros(N)
    i0, i1 = int(t0 * SR), int(t1 * SR)
    g[:i0] = v0; g[i1:] = v1
    if i1 > i0: g[i0:i1] = np.linspace(v0, v1, i1 - i0)
    return g

def curve(points):
    """piecewise-linear automation from [(t, v), ...]"""
    ts = np.array([p[0] for p in points]) * SR
    vs = np.array([p[1] for p in points], float)
    return np.interp(np.arange(N), ts, vs)

def reverb(x, rt=1.5, mix=0.22, pre=0.02):
    """synthetic hall: exponentially decaying noise impulse, slight stereo decorrelation"""
    L = int(rt * SR)
    out = np.zeros_like(x)
    for ch in (0, 1):
        ir = np.random.default_rng(40 + ch).standard_normal(L) * np.exp(-T(L) * (5.0 / rt))
        ir = lp(ir, 5200)
        ir /= np.sqrt((ir ** 2).sum())
        wet = signal.fftconvolve(x[:, ch], ir)[:N]
        d = int(pre * SR)
        wet = np.concatenate([np.zeros(d), wet[:-d]]) if d else wet
        out[:, ch] = x[:, ch] * (1 - mix) + wet * mix
    return out

# ---------------------------------------------------------------- the cue sheet
def build():
    m = Mix()

    # ---- beds -------------------------------------------------------------
    # night wind, rising through the form, settling under the rain
    wl, wr = wind(DUR, 110, 1700, .55, 0), wind(DUR, 100, 1550, .55, 3.3)
    wg = curve([(0, .30), (2.0, .34), (5.0, .40), (6.1, .72), (7.4, .52), (9.0, .34), (12, .30)])
    m.put_st(0, wl * wg, wr * wg, 0.150)
    # high night air so the quiet shots still have texture
    ag = curve([(0, .55), (3.0, .5), (6.0, .7), (9.0, .35), (12, .3)])
    m.put_st(0, hp(nz(N), 2600) * ag, hp(nz(N), 2800) * ag, 0.016)

    # sub drone: swells into the strike, resolves under the rain
    dg = curve([(0, .22), (1.2, .30), (3.0, .26), (4.6, .42), (5.5, .55),
                (6.02, .95), (7.2, .55), (9.0, .34), (10.6, .26), (12, .20)])
    d1 = drone(DUR, 46.0)
    m.put(0, d1 * dg, 0.052, pan=0.0)
    m.put(0, drone(DUR, 69.0, fifth=False) * dg * 0.45, 0.026, pan=0.0)

    # pools lapping before the technique
    pg = curve([(0, .20), (4.0, .26), (5.6, .40), (8.0, .22), (9.2, .08), (12, .05)])
    m.put_st(0, water_rush(DUR, 300, 2600, .5, 0.0) * pg,
             water_rush(DUR, 320, 2800, .5, 2.4) * pg, 0.046)

    # rain takes over from the dissolving water
    rg = curve([(0, 0), (8.2, 0), (9.0, .45), (9.8, .95), (10.6, 1.0), (12, 1.0)])
    m.put_st(0, rain_bed(DUR, .55, 1) * rg, rain_bed(DUR, .55, 9) * rg, 0.100)

    # ---- scene 1: introduction -------------------------------------------
    m.put(0.18, taiko(2.0, 96, 40), 0.185, pan=0.0)                 # the opening hit
    m.put(0.55, cloth(0.40), 0.085, pan=-0.35)                     # haori in the wind
    m.put(1.40, cloth(0.34), 0.065, pan=0.30)
    m.put(2.35, cloth(0.42), 0.075, pan=-0.25)
    m.put(1.88, shimmer(1.3, 700, 2600, up=True), 0.030, pan=0.0)  # he opens his eyes
    m.put(1.95, taiko(1.6, 74, 38), 0.085, pan=0.0)

    # ---- scene 2: preparation --------------------------------------------
    m.put(2.96, air_whoosh(0.30, 700, 3600, curve=.7, p=2.4), 0.085, pan=0.5, pan_to=-0.2)  # the cut
    m.put(3.00, taiko(1.1, 80, 36), 0.070)
    # water gathering on the steel
    m.put(3.62, shimmer(1.6, 800, 5200, up=True), 0.055, pan=-0.15)
    for tt, f0, pn in ((3.95, 2700, -.4), (4.18, 2200, .35), (4.36, 3100, -.15),
                       (4.62, 2450, .45), (4.86, 2900, -.3)):
        m.put(tt, droplet(f0, 900, 0.17), 0.085, pan=pn)
    m.put(4.40, air_whoosh(0.34, 400, 3000, curve=.8), 0.075, pan=0.35, pan_to=0.0)  # lifting it
    m.put(4.46, shing(1.5, 2180), 0.115, pan=0.12)                 # steel rings
    m.put(4.60, shimmer(1.5, 1100, 6200, up=True), 0.055, pan=0.2)
    m.put(4.90, drone(1.4, 55.0) * np.linspace(0, 1, int(1.4 * SR)) ** 2, 0.050)

    # ---- scene 3: the fifth form -----------------------------------------
    # water lifting out of the pools
    m.put(5.05, water_rush(2.2, 260, 4200, .5, 1.3) * hump(int(2.2 * SR), .7), 0.055, pan=-0.3)
    m.put(5.28, air_whoosh(0.50, 220, 1500, curve=1.5, p=2.2), 0.075, pan=0.45)   # wind-up
    m.put(5.46, cloth(0.30), 0.090, pan=0.3)

    # the strike
    m.put(5.88, water_slash(0.78, 440, 6600), 0.185, pan=0.75, pan_to=-0.55)
    m.put(6.02, taiko(2.0, 118, 42, body=1.15), 0.255)
    m.put(6.06, splash(0.95, 1.15), 0.115, pan=-0.3)
    m.put(6.02, shing(1.3, 1960, metal=.8), 0.075, pan=-0.1)

    # follow-throughs
    m.put(6.34, water_slash(0.62, 520, 5600), 0.115, pan=-0.6, pan_to=0.45)
    m.put(6.50, taiko(1.5, 96, 40), 0.115)
    m.put(6.54, splash(0.8, .95), 0.085, pan=0.35)
    m.put(7.06, water_slash(0.66, 480, 5200), 0.105, pan=0.5, pan_to=-0.35)
    m.put(7.20, taiko(1.4, 88, 38), 0.100)
    m.put(7.24, splash(0.85, 1.0), 0.080, pan=-0.2)

    # the ring of water turning around him
    rr = curve([(0, 0), (5.6, 0), (6.1, 1.0), (7.5, .85), (8.4, .45), (9.4, .10), (10.2, 0), (12, 0)])
    m.put_st(0, water_rush(DUR, 420, 6200, .55, 4.1) * rr,
             water_rush(DUR, 440, 6600, .55, 8.8) * rr, 0.068)

    # water coming apart into rain
    m.put(8.10, shimmer(2.0, 5200, 900, up=False), 0.050, pan=0.1)
    for tt, f0, pn in ((8.30, 2500, .4), (8.62, 1900, -.35), (8.95, 2800, .2), (9.30, 2100, -.45)):
        m.put(tt, droplet(f0, 820, 0.19), 0.070, pan=pn)

    # ---- scene 4: the final shot -----------------------------------------
    m.put(9.58, air_whoosh(0.26, 900, 5200, curve=.6, p=2.6), 0.105, pan=-0.1, pan_to=0.45)  # chiburi
    m.put(9.64, shing(1.6, 2640, metal=1.1), 0.125, pan=0.25)
    m.put(9.70, splash(0.55, .7), 0.070, pan=0.4)
    for tt, f0, pn in ((9.78, 3100, .5), (9.92, 2400, .3), (10.08, 2800, .55), (10.26, 2050, .35)):
        m.put(tt, droplet(f0, 950, 0.15), 0.065, pan=pn)
    m.put(10.35, taiko(2.2, 70, 34), 0.110)                          # the closing weight
    m.put(10.9, cloth(0.42), 0.060, pan=-0.3)
    m.put(11.25, shimmer(1.5, 2600, 800, up=False), 0.030, pan=0.15)

    # ---- master ----------------------------------------------------------
    x = m.b
    x = reverb(x, rt=1.6, mix=0.20, pre=0.018)                      # the valley around him
    x = hp(x.T, 34, order=2).T                                      # clear the sub-rumble
    # gentle bus compression so the strike sits with the beds
    e = np.abs(x).max(axis=1)
    e = lp(e, 8.0)
    gain = 1.0 / (1.0 + np.maximum(0.0, e - 0.42) * 2.6)
    x = x * gain[:, None]
    # fade in / out matched to the picture
    fi = int(0.35 * SR); x[:fi] *= np.linspace(0, 1, fi)[:, None]
    fo_a, fo_b = int(11.70 * SR), N
    x[fo_a:fo_b] *= np.linspace(1, 0, fo_b - fo_a)[:, None]
    pk = np.abs(x).max()
    if pk > 0: x = x / pk * 0.89                                    # ~ -1 dBFS
    return x

if __name__ == '__main__':
    import sys
    x = build()
    wavfile.write('sound/water_breathing_audio.wav', SR, (x * 32767).astype(np.int16))
    rms = np.sqrt((x ** 2).mean())
    print('wrote sound/water_breathing_audio.wav')
    print('samples %d  dur %.3fs  peak %.3f (%.1f dBFS)  rms %.4f (%.1f dBFS)'
          % (len(x), len(x) / SR, np.abs(x).max(), 20 * np.log10(np.abs(x).max() + 1e-9),
             rms, 20 * np.log10(rms + 1e-9)))
