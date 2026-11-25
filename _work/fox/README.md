# Renard low poly — animation 12 s

Court métrage 3D low poly (288 images @ 24 fps) dans une clairière d'automne. Même pipeline que
[le jardinier](../gardener/README.md) : primitives du skill `blender-lpm-skill`, à-plats, une palette par objet,
échelle réelle. Les helpers de rig communs sont dans [`../lpm_anim.py`](../lpm_anim.py).

## Le plan (12 s)

| Temps | Images | Plan | Action |
| --- | --- | --- | --- |
| 0–4,9 s | 1–118 | A, latéral suiveur | Il traverse la clairière au trot (diagonales, cycle de 16 images) |
| 4,9–6,1 s | 118–146 | A | Il ralentit et se cale sur ses quatre pattes |
| 6,1–8 s | 146–192 | B, trois quarts | Il renifle le sol, oreilles en avant, petits à-coups de tête |
| 8–9 s | 192–216 | B | Il relève la tête et suit une feuille qui tombe |
| 9–10,5 s | 216–252 | C, rapproché | Il se couche, pattes repliées, queue qui s'enroule |
| 10,5–12 s | 252–288 | C | Couché : il regarde l'objectif, oreille qui tressaille, bout de queue qui bat |

## Ce qui a demandé du travail

* **Les pattes sont résolues, pas devinées.** `solve_lower()` calcule l'angle du segment bas pour que la patte
  touche exactement le sol, en tenant compte de la hauteur courante de l'échine — sans ce terme, dès que le
  renard baisse l'échine (reniflement, coucher) les pattes traversaient le sol de 7 cm. Vérifié au `--probe` :
  les quatre pattes tiennent à ±2 cm pendant tout le trot.
* **Le trot** est un cycle diagonal (antérieur gauche + postérieur droit en phase) : appui résolu au sol,
  suspension avec flexion du genou pour dégager la patte.
* **Pas d'assise.** Une patte à deux segments ne peut pas se replier en position assise sans un troisième
  segment (jarret) ; le plan final est donc un coucher, qui lui est franc.
* **Plaques d'herbe décalées en hauteur.** Deux plaques coplanaires qui se chevauchent s'auto-ombrent : le rayon
  d'ombre part d'une face et touche immédiatement l'autre, et la zone rend **noire**. Chaque plaque a sa propre
  altitude (4 mm + 1,6 mm par plaque).

## Refaire le rendu

```bash
python fox_scene.py --save fox.blend --stats
python fox_scene.py --probe 96,170,252          # hauteur des pattes, museau, échine
python fox_scene.py --range 1 288 --step 4 --offset 0 --threads 1 --out frames   # x4 en parallèle
ffmpeg -framerate 24 -i frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 renard.mp4
```
