"""Sound for the voxel scale-zoom: ambient bed rising in pitch across the film,
per-level textures, and an 8-bit layer (square blips as blocks snap in, scatter
noise + power-up arpeggio + coin ding on every new scale label)."""
import sys, numpy as np
sys.path.insert(0, "/home/user/NaelAerts/.claude/skills/ai-video-motion-graphics/scripts")
from sfx_kit import Mixer, SR
from scipy.io import wavfile

DUR = 30.0
LV = [(0.0, 'galaxy'), (3.4, 'solar'), (6.7, 'earth'), (10.0, 'coast'), (13.3, 'tree'),
      (16.6, 'hopper'), (19.9, 'cells'), (23.2, 'dna'), (26.5, 'atom')]
mx = Mixer(np.zeros((int(DUR * SR), 2), np.float32), seed=11)
T = lambda d: np.arange(int(d * SR)) / SR

def sq(f, d, duty=.5, dec=14):
    t = T(d)
    return np.sign(np.sin(2 * np.pi * f * t) + (duty - .5) * 2) * np.exp(-t * dec)

def blip(t0, f, g=.055, d=.09, pan=0):
    mx.put(t0, sq(f, d) * np.minimum(1, T(d) / .004), g, pan)

PENT = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
hz = lambda semi, base=440: base * 2 ** (semi / 12)

# ---------------- ambient bed, rising in pitch across the whole film
n = int(DUR * SR); t = np.arange(n) / SR
bed = np.zeros(n)
rise = 2 ** (t / DUR * 1.6)                      # just over an octave from start to end
for k, (f, a) in enumerate([(55, .30), (82.4, .22), (110, .17), (164.8, .10), (220, .07)]):
    bed += a * np.sin(2 * np.pi * f * rise * t + k) * (1 + .22 * np.sin(2 * np.pi * (.07 + k * .013) * t))
air = np.random.default_rng(3).standard_normal(n)
from scipy import signal as sg
air = sg.sosfilt(sg.butter(2, [320, 2100], 'band', fs=SR, output='sos'), air)
bed = bed * .33 + air * .10
bed *= np.clip(np.minimum(t / 1.4, (DUR - t) / 2.2), 0, 1)
mx.beds[:, 0] += bed * .17; mx.beds[:, 1] += np.roll(bed, 240) * .17

# ---------------- per-level textures
def texture(t0, t1, kind):
    rng = np.random.default_rng(abs(hash(kind)) % 9999)
    d = t1 - t0
    if kind == 'galaxy':
        for i in range(26): mx.chime(t0 + rng.random() * d, .012, f=hz(PENT[rng.integers(4, 11)], 1320), pan=rng.random() * 2 - 1)
    elif kind == 'solar':
        x = sg.sosfilt(sg.butter(2, 160, 'low', fs=SR, output='sos'), rng.standard_normal(int(d * SR)))
        mx.put(t0, x * np.minimum(1, T(d) / .5) * .9, .10)
    elif kind == 'earth':
        x = sg.sosfilt(sg.butter(2, [240, 1500], 'band', fs=SR, output='sos'), rng.standard_normal(int(d * SR)))
        mx.put(t0, x * (.5 + .5 * np.sin(2 * np.pi * .7 * T(d))), .035)
    elif kind == 'coast':
        x = sg.sosfilt(sg.butter(2, [180, 3200], 'band', fs=SR, output='sos'), rng.standard_normal(int(d * SR)))
        mx.put(t0, x * (.45 + .55 * np.sin(2 * np.pi * .35 * T(d)) ** 2), .055)
    elif kind == 'tree':
        for i in range(7):
            f = hz(PENT[rng.integers(5, 11)], 1760)
            mx.chime(t0 + .25 + rng.random() * (d - .5), .016, f=f, pan=rng.random() * 2 - 1)
    elif kind == 'hopper':
        for i in range(10):
            tt = t0 + .2 + rng.random() * (d - .4)
            for k in range(3): mx.tick(tt + k * .035, .012, f=3400 + rng.random() * 900)
    elif kind == 'cells':
        for i in range(14):
            tt = t0 + rng.random() * d; dd = .18
            e = np.exp(-T(dd) * 12); f = 300 + rng.random() * 500
            mx.put(tt, np.sin(2 * np.pi * (f * (1 + 2.2 * T(dd))) * T(dd)) * e, .022, rng.random() * 2 - 1)
    elif kind == 'dna':
        for i in range(12): blip(t0 + i * (d / 12), hz(PENT[i % len(PENT)], 660), .030, .14, (i % 3 - 1) * .6)
    elif kind == 'atom':
        f0 = 220
        x = np.sin(2 * np.pi * f0 * T(d) * (1 + .15 * np.sin(2 * np.pi * 5.5 * T(d)))) * np.minimum(1, T(d) / .6)
        mx.put(t0, x * np.exp(-T(d) * .25), .035)
        for i in range(9): mx.sparkle(t0 + .3 + i * (d / 9), .014, pan=(i % 3 - 1) * .7, d=.4)

for i, (t0, name) in enumerate(LV):
    t1 = LV[i + 1][0] if i + 1 < len(LV) else DUR
    texture(t0, t1, name)

# ---------------- 8-bit layer on every scale change
for i, (t0, name) in enumerate(LV):
    if i:                                           # scatter burst + power-up + coin on the boundary
        rng = np.random.default_rng(100 + i)
        d = .26; x = rng.standard_normal(int(d * SR))
        x = np.round(sg.sosfilt(sg.butter(2, [600, 6000], 'band', fs=SR, output='sos'), x) * 6) / 6
        mx.put(t0 - .20, x * np.exp(-T(d) * 9), .045)
        for k, s in enumerate([0, 4, 7, 12]): blip(t0 - .10 + k * .045, hz(s, 523), .05, .07)
        blip(t0 + .06, hz(12, 523), .06, .10); blip(t0 + .13, hz(19, 523), .055, .14)
        mx.put(t0 - .02, np.sin(2 * np.pi * np.linspace(62, 34, int(.5 * SR)) * T(.5)) * np.exp(-T(.5) * 5), .10)
    nb = 11                                          # blocks snapping in
    for k in range(nb):
        blip(t0 + .02 + k * .028 + (k * .013) ** 1.4, hz(PENT[(k + i) % len(PENT)], 880), .030, .07, (k % 5 - 2) * .4)

# title jingle + closing swell
for k, s in enumerate([0, 7, 12, 16, 19]): blip(.12 + k * .085, hz(s, 523), .055, .16, (k % 3 - 1) * .5)
mx.swell(27.2, .055, root=196, d=2.4)
mx.swell(28.4, .05, root=294, d=1.6)

info = mx.write('/home/user/NaelAerts/_work/voxel/voxel_mix.wav', '/home/user/NaelAerts/_work/voxel/voxel_SFX_stem.wav', reverb=.14)
print('sfx written', info)
