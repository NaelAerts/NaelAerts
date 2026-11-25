# Moulin low poly — boucle parfaite de 6 s

144 images @ 24 fps, pensées comme une **boucle** : l'image 145 serait exactement l'image 1, donc la vidéo
tourne en continu sans raccord visible.

| Élément | Cycle sur 144 images |
| --- | --- |
| Ailes | un quart de tour exactement — les 4 ailes sont identiques, donc 90° ≡ 0° |
| Blé (6 rangées) | une sinusoïde complète, décalée par rangée (effet de vague) |
| Drapeau | deux sinusoïdes |
| Oiseaux | un tour de cercle chacun |

Le reste est fixe (caméra, lumière), ce qui est la condition d'une boucle propre.

Construit avec les primitives du skill `blender-lpm-skill` et les helpers de
[`../lpm_anim.py`](../lpm_anim.py). 9 072 triangles, 15 objets.

Deux points de méthode repris des scènes précédentes : les plaques d'herbe ont chacune leur altitude (deux faces
coplanaires qui se chevauchent s'auto-ombrent et rendent **noir**), et le ciel est un aplat plutôt qu'une texture
de ciel, qui saturait l'horizon en blanc pur.

```bash
python windmill_scene.py --save mill.blend --stats
python windmill_scene.py --range 1 144 --step 4 --offset 0 --threads 1 --out frames   # x4 en parallèle
ffmpeg -framerate 24 -i frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 moulin.mp4
# pour une vidéo qui boucle 5 fois :
ffmpeg -stream_loop 4 -i moulin.mp4 -c copy moulin_x5.mp4
```
