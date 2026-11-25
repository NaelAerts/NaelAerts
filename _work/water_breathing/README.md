# Water Breathing, Fifth Form — Blessed Rain After the Drought

A 12-second cinematic 2D anime fight animation, rendered entirely in code
(no footage, no AI image generation, no stock assets). 1920x1080, 24 fps, H.264 MP4.

**Output:** `water_breathing_fifth_form.mp4` (12.000 s, 288 frames, H.264 + AAC 48 kHz stereo, 13 MB)
**Audio stem:** `sound/water_breathing_audio.wav` — the full mix on its own, for rebalancing

## Character

An **original character design** built from scratch for this piece — a young water-breathing
swordsman. Art direction as briefed: dark hair warming to burgundy at the tips, a green-and-black
checkered haori over a dark kimono and hakama, a black nichirin-style blade with a crimson spine,
and a determined expression. He is drawn parametrically every frame, so the design stays
identical across all 288 frames.

## Scenes

| Time | Scene | Content |
|------|-------|---------|
| 0.0–3.0 s | Introduction | Wide moonlit plateau; he stands calm, haori and hair moving in the wind; camera pushes slowly in; he opens his eyes. |
| 3.0–5.0 s | Preparation | Cut to the eyes, then the camera falls to the blade as he lifts it; blue water gathers along the steel and spirals up out of the pools. |
| 5.0–9.0 s | Fifth Form | Wind-up, step, and one graceful revolution of the blade — a full circular water trail wrapping around him, spray, splash, motion blur. |
| 9.0–12.0 s | Final shot | The water falls apart into gentle rain; he settles and flicks the blade clean; the camera arcs around him and pulls back. |

## How the motion works

The pose is a **pure function of `t`** (`scenes.pose`). That makes the blade samplable at past
times, so the motion blur and the flowing trails are built from where the sword *actually was*
rather than from a painted-on smear:

- `blade_sweep` fills the quads swept between consecutive blade positions (6 samples, ~85 ms).
- `tip_hist` reconstructs the arc the tip carved over the last 0.55 s and skins it with water.
- The circular trail is depth-split: the far half is drawn **before** the figure and the near
  half **after**, so the ring genuinely wraps around him.
- Arms use 2-bone IK onto the hilt, with the grip derived from the blade angle, so the hands
  really hold the sword through the whole sweep.
- The camera is multiplane: each layer takes a parallax depth, and the final "orbit" keeps him
  centred while the world sweeps past.

## Sound design

Every cue is **synthesised from scratch** in `sound.py` (noise + oscillators + filters) — no
samples, no library audio. Cues are placed against the picture's own beats:

| Time | Cue |
|------|-----|
| 0.18 s | Deep taiko hit opening the film |
| 0.5–2.4 s | Haori snapping in the wind; night air and wind bed |
| 1.95 s | Low swell as he opens his eyes |
| 3.00 s | Whoosh on the cut to the eyes |
| 3.6–4.9 s | Water gathering: upward shimmer and drop pings |
| 4.46 s | Nichirin steel rings (inharmonic partials) as the blade lifts |
| 5.28 s | Rising wind-up whoosh, cloth snap |
| **6.02 s** | **The strike** — water slash panned hard right→left, taiko, splash |
| 6.50 / 7.20 s | The two follow-throughs, panned back across |
| 5.6–9.4 s | The ring of water turning around him |
| 8.1–9.3 s | Shimmer falling, water coming apart into drops |
| 9.64 s | The chiburi flick: sharp whoosh, bright ring, droplet spatter |
| 10.35 s | Closing low hit; rain carries to the end |

Beds: night wind, a sub drone (a tone under the drama, not a melody), pools lapping, and
rain fading in from 8.2 s. The master adds a synthetic hall convolution, a 34 Hz high-pass,
and gentle bus compression; the mix peaks at −1.0 dBFS with −21 dBFS RMS, so it stays dynamic.

The strike at 6.02 s is the loudest 100 ms window in the whole mix, by design.

## Files

- `slayer_char.py` — the character: hair, face, haori/hakama, katana, IK limbs
- `slayer_env.py` — night environment: sky, moon, ridges, bamboo, rock plateau, pools, rain-lit mist
- `slayer_water.py` — water FX: layered sumi-e ribbons with curling crests, droplets, spray, ring arcs, rain
- `scenes.py` — choreography, camera, the four shots, grade
- `sound.py` — the synthesised sound design and the mix

## Rebuild

```bash
SK=.claude/skills/ai-music-video-animation/scripts
for i in 0 1 2 3; do python3 $SK/render_frames.py scenes $i 288 4 out/frames & done; wait
ffmpeg -y -framerate 24 -i out/frames/f%05d.jpg -c:v libx264 -preset slow -b:v 8M \
  -maxrate 10M -bufsize 16M -vf hqdn3d=1.5:1:3:3 -pix_fmt yuv420p -movflags +faststart \
  water_breathing_fifth_form.mp4
```
Then the sound, and mux it in without re-encoding the picture:

```bash
python3 sound.py
ffmpeg -y -i water_breathing_fifth_form.mp4 -i sound/water_breathing_audio.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -movflags +faststart -shortest out.mp4
```

Requires `skia-python`, `opencv-python-headless`, `numpy`, `scipy` and system `libegl1`.
