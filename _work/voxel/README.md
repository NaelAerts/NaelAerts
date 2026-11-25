# Powers of Ten voxel — animation 3D, 30 s

Un plongé continu à travers les échelles, de la Voie lactée à l'atome, entièrement construit en cubes :
900 images @ 30 fps, 1920×1080, rendu **Three.js en Chromium headless** image par image, puis encodé avec
une bande-son synthétisée. Fait avec le skill `ai-video-motion-graphics` (mode G, voxel scale-zoom).

## Les neuf niveaux

| t | échelle | niveau |
| --- | --- | --- |
| 0,0 s | 10²¹ m | Voie lactée — bras spiraux, cœur incandescent |
| 3,4 s | 10¹² m | Système solaire — soleil, orbites, planètes |
| 6,7 s | 10⁷ m | Terre — continents, calottes, nuages translucides |
| 10,0 s | 10⁴ m | Littoral — mer, plage, champs, falaise |
| 13,3 s | 10¹ m | Chêne sur la falaise |
| 16,6 s | 10⁻¹ m | Sauterelle sur une feuille |
| 19,9 s | 10⁻⁴ m | Cellules de la feuille |
| 23,2 s | 10⁻⁸ m | ADN |
| 26,5 s | 10⁻¹⁰ m | Atome de carbone (la caméra remonte en fin de plan) |

## Comment ça marche

* **Moteur voxel** (`site/vox.js`, repris du skill) : un seul `InstancedBufferGeometry` par objet, avec
  `iPos/iScl/iCol/iGlow/iRnd` par cube. Toute l'animation est dans le vertex shader — assemblage décalé
  depuis une dispersion aléatoire (`uAsm`), explosion radiale au départ du niveau (`uOut`), onde de pulsation.
* **Caméra** : `logPos` + `zoomU` donnent un zoom logarithmique à vitesse d'échelle constante — le plan arrive
  avec l'élan du précédent, dérive lentement le temps qu'on lise le monde, puis accélère dans la plongée et
  garde cette vitesse pendant le fondu. Jamais d'arrêt net.
* **Transitions** : fondu de 0,36 s centré sur la frontière ; les cubes sortants partent en gerbe pendant que
  les entrants s'assemblent, avec un léger flou de zoom et une aberration chromatique poussée sur le fondu.
* **Post** : mix des deux cibles de rendu → UnrealBloom → tonemap ACES → étalonnage (saturation, vignette, grain).
* **Son** (`vox_sfx.py`) : nappe ambiante dont la hauteur monte d'une octave sur les 30 s, texture par niveau
  (carillons, grondement solaire, vent, stridulations, bulles, pizzicati, bourdon atomique) et couche 8-bit —
  bips carrés pentatoniques quand les blocs s'emboîtent, bruit écrêté + arpège power-up + pièce à chaque
  changement d'échelle.

## Deux correctifs trouvés en route

* Le dôme de ciel était mis à l'échelle dans `onBeforeRender`, donc **après** le calcul de sa matrice monde :
  il ne couvrait jamais l'image et tous les fonds sortaient noirs.
* Les nuages posés sur une grille de Fibonacci dessinaient des **stries en spirale** au lieu de nuages ;
  ils sont maintenant tirés aléatoirement sur la sphère.

## Refaire le rendu

```bash
npm install                                   # three.js
cd site && python3 -m http.server 8731 &      # servir la page
node shoot.cjs --from 0 --to 899 --fps 30 --w 1920 --out frames
python3 vox_sfx.py
ffmpeg -framerate 30 -i frames/f_%05d.png -i voxel_mix.wav -c:v libx264 -crf 18 \
       -pix_fmt yuv420p -af "volume=2.8" -shortest voxel_30s.mp4
```
