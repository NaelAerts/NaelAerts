# Jardinier low poly — animation 20 s

Court métrage 3D low poly (480 images @ 24 fps) construit avec le skill
[`blender-lpm-skill`](../../.claude/skills/blender-lpm-skill) : à-plats, une palette unique par objet,
échelle réelle en mètres, Z vers le haut, l'avant en −Y.

## Le plan (20 s)

| Temps | Images | Plan | Action |
| --- | --- | --- | --- |
| 0–3,7 s | 1–88 | A, large | Il arrive par l'allée, l'arrosoir à la main droite (cycle de marche, période 32 images) |
| 3,7–5,4 s | 88–130 | A | Il s'arrête, se tourne vers le massif, avance d'un pas |
| 5,4–6,8 s | 130–164 | A | Il pose l'arrosoir, attrape la bêche plantée dans la terre |
| 7–11,2 s | 166–268 | B, rapproché | Trois coups de bêche (préparation, levée, enfoncement, relevage avec motte, jet) |
| 11,2–14,2 s | 268–342 | B | Il replante la bêche, s'accroupit, met le plant en terre, tasse la terre |
| 14,2–18,2 s | 342–436 | C, face | Il reprend l'arrosoir, arrose : les gouttes tombent, la fleur pousse et s'ouvre |
| 18,2–20 s | 436–480 | C | Il repose l'arrosoir, recule, s'essuie le front ; deux papillons arrivent |

## Ce que contient la scène

4 744 triangles, 46 objets, une palette de 31 teintes (`PALETTE` dans le script).

* **Le jardinier** n'est pas un maillage unique : chaque membre est un objet `lpm` dont l'origine est posée
  sur son articulation (hanche, genou, épaule, coude, cou), parenté en chaîne et animé en rotation d'objet —
  pas d'armature, pas de skinning.
* **Les outils posés** (arrosoir, bêche) existent en double : une copie enfant de l'avant-bras, une copie au
  sol. L'échange se fait sur une image, et la copie au sol hérite de la matrice exacte qu'avait la main au
  moment du lâcher, donc rien ne saute.
* **Les props tenus sont visés, pas devinés** : `aim_dir`, `aim_at` et `aim_tip_z` calculent la rotation locale
  à partir de la vraie matrice du bras évaluée à cette image, pour que la lame tombe à la hauteur voulue et que
  le bec de l'arrosoir pointe sur le plant. C'est nécessaire : les bras sont enfants du torse, donc les angles
  s'additionnent, et un lacet d'épaule casse l'arithmétique naïve.
* **Les gouttes d'eau** naissent à la position réelle du bec, relevée image par image.

## Refaire le rendu

```bash
python gardener_scene.py --save scene.blend                       # juste la scène
python gardener_scene.py --probe 184,320,398                      # positions mains / lame / bec
python gardener_scene.py --frames 1,200,400 --res 640 --samples 12 --out frames
python gardener_scene.py --range 1 480 --step 4 --offset 0 --threads 1 --out frames   # x4 en parallèle
ffmpeg -framerate 24 -i frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 jardinier.mp4
```

Il faut Blender 4.2+ ou le module `bpy` (`pip install bpy`). Rendu Cycles CPU, 16 échantillons + débruitage
OpenImageDenoise, 960×540 — environ 9 s par image sur 4 cœurs.
