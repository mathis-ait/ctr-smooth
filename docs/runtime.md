# Runtime ctr-smooth (phase 2 et suite) — Rubis Oméga EUR v1.0

## Principe retenu

La logique (`update()`) n'est jamais modifiée. Le jeu dessine désormais à chaque VBlank, et chaque
matrice lue par le rendu est suivie individuellement (clé = son adresse) :

- `C` = dernière valeur lue, apparue à l'image `tc` ;
- `P` = valeur distincte précédente, apparue à l'image `tp` ;
- `T = tc - tp` = cadence propre de la matrice (2 pour un objet mis à jour à chaque tick de 30 Hz,
  4 pour un contenu à 15 Hz ; un changement isolé après une longue pause compte pour 2).

À l'image `f`, si `k = f - tc + 1 < T`, la matrice est remplacée le temps du dessin par
`P + (C - P) × k / T`, puis restaurée à `C` en fin d'image.

| Contenu | Image de l'update (k = 1) | Images suivantes |
| --- | --- | --- |
| 30 Hz (terrain, personnages) | 50 % | `C` (dessin d'origine) |
| 15 Hz | 25 % | 50 %, 75 %, puis `C` |
| 60 Hz (menus en mode 60 Hz du jeu) | `C` | `C` |

Le terrain n'a **aucune latence ajoutée** : le mélange (n-1, n) est dessiné dès l'image où le tick n
est calculé. Un contenu à 15 Hz atteint `C` deux images (33 ms) plus tard que l'original.
La logique ne voit jamais une valeur mélangée : toute matrice remplacée est restaurée avant la fin
de l'image.

## Points d'interception

| Adresse | Instruction d'origine | Rôle |
| --- | --- | --- |
| 0x0010E530 | `ldrb r0,[r4,#0xd]` → `bl hook_gate` | décision « dessiner ? » : `smooth_gate(mgr, r6)` |
| 0x0010E534 | `rsb r1,r6,#0` → `cmp r0,#0` | |
| 0x0010E538 | `tst r0,r1` → `nop` | `bne 0x10E554` (inchangé) saute le dessin si r0 ≠ 0 |
| 0x0010E61C | `nop` → `bl smooth_end` | fin du dessin : restauration |
| 0x00375EA8 | `push {r0-r11,lr}` → `b hook_camera` | copie de la vue avant la file de rendu ; caméra = `[sp+0xC]` (`nw::gfx::Camera`) |
| 0x0039B338 | `push {r3-r11,lr}` → `b hook_h3d` | rendu d'un maillage H3D ; `r0` = modèle |
| 0x002EC354 | `push {r4-r8,lr}` → `b hook_nwmesh` | `nw::gfx` MeshRenderer ; `r2` = modèle |
| 0x0036FB34 | `add r1,r4,#0x98` → `bl hook_hid` | boutons tenus copiés dans `S.pad` (interrupteur L + Select) ; **builds de test** : `hook_pad` (entrées injectées) |
| 0x0038CEA4 | `push {r3-r7,lr}` → `b hook_cnt3d` | **builds de test** (`--count3d`) : passes de scène 3D |
| 0x0010E5AC | `bl 0x0011CB60` → `bl smooth_fade` | transitions : avance figée et rappel neutralisé sur le dessin ajouté |
| 0x0014D618 | `push {r4-r12,lr}` → `b hook_lytanim` | animations d interface : retour immédiat sur le dessin ajouté |
| 0x00392FB4 | `add r4,r0,#0x148` → `bl hook_setview` | `SetViewMatrix` : retient les caméras des yeux (3D stéréoscopique, intérieurs) |

Matrices lissées (3×4) :

- `nw::gfx::Camera` : vue `+0x148`, inverse de la vue `+0x178` (position caméra).
- Modèles H3D (personnages, Pokémon, décors animés) : matrices **monde** des os,
  `*(modèle+0x4C)[0 .. *(modèle+0x40)[` : déplacement et animation squelettique ensemble.
- Modèles `nw::gfx` : matrice monde `+0x8C`.
- **Phase 2** : `nw::gfx::SkeletalModel` (vtable 0x005DB47C), `StandardSkeleton` en `+0x220` :
  pose monde `+0x3C` et pose de skinning `+0x4C`, chacune { allocateur, matrices, fin, nombre }
  (accesseurs virtuels 0x002FD054 et 0x002FD064, consommées par 0x002EC45C).

- **Suite (lot A)** : caméras des yeux gauche et droit (`nw::gfx::Camera`), voir plus bas.

Un modèle étant rendu maillage par maillage, un tableau d'os n'est traité qu'une fois par image
(garde `seen` sur sa première matrice) : 7 fois moins d'appels en combat.

## Caméras stéréoscopiques (intérieurs)

Rubis Oméga n'active la 3D qu'en intérieur (bâtiments, grottes), pas dans le monde extérieur. En
intérieur, le décor est rendu avec deux caméras d'yeux, pas avec la caméra de base :

- le module de terrain (CRO, appel depuis 0x0076D054) appelle **pendant `update()`** la mise à jour
  stéréo 0x00377984 : caméra de base `[obj+0x94]`, yeux `[obj+0x98]` et `[obj+0x9C]` ; projections
  `+0x1A8` et vues `+0x148` calculées par 0x002DBEF4 (ou copiées de la base, 0x0015EB38 / 0x00144CA8,
  quand l'écart des yeux est nul) ;
- `SetViewMatrix` 0x00392F90 recopie la vue dans chaque œil et recalcule l'inverse `+0x178`
  (0x00195DD0) ;
- les yeux ne passent jamais par `hook_camera` : avant ce correctif, la pièce restait figée sur le
  dessin ajouté (écarts image à image alternant environ 6 et 0,25 dans la boutique de Rosyères), seul
  le joueur bougeait.

Correctif : `hook_setview` retient chaque caméra dont la vue est posée (4 emplacements,
`eye`/`eye_f`), et `smooth_gate` lisse leurs vue et inverse au début de chaque dessin lissé. Une
caméra n'est utilisée que si sa vue a été posée au tick courant ou au précédent
(`frame - eye_f <= 2`) et si sa vtable est celle de `nw::gfx::Camera` (0x005DBAB8) : une caméra
libérée au changement de carte n'est jamais touchée.

Mesures (boutique de Rosyères, marche) : 39 images distinctes sur 39 avec des écarts réguliers
(4,9 à 5,25) contre une alternance 6 / 0,25 avant ; aucun tirage pendant les dessins ajoutés
(`tools/rngcheck.py`) ; `tools/drawdiff.py` (`proto/replay/drawdiff-interieur.txt`) ne montre que
des valeurs recalculées à chaque dessin et un drapeau « premier dessin après le tick »
(0x086FBB28, bit 0x80, et un pointeur voisin) posé une fois par tick, comme dans le jeu d'origine.

## Changements de carte (lot B)

Deux protections, vérifiées en entrant et en sortant de la boutique de Rosyères (capture image par
image, comparée au jeu d'origine) :

- **Pas de dessin ajouté sur un tick où une transition change d'état.** Les fondus et balayages
  affichent une image capturée que le jeu renouvelle lors de son propre dessin, au tick suivant le
  changement d'état. Un dessin ajouté sur ce tick montrait l'ancienne capture : une image blanche en
  entrant (le balayage d'entrée commence), l'extérieur pendant une image en sortant. La signature
  d'un contexte (`*(0x0062F830)` + 0x38 / + 0x3C) combine l'état `+0x0C`, les drapeaux `+0x44`
  (deux octets bas) et `+0x48` : le fondu de sortie change l'état (6 → 0xC), le balayage d'entrée
  ne change que `+0x45` et `+0x48`. Coût : une image répétée au début et à la fin d'une transition
  (`n_tskip`), pendant laquelle le jeu d'origine est de toute façon à 30 images/s.
- **Une matrice non lue depuis plus de 4 images repart sans mélange** : après un fondu ou un
  changement de carte, une adresse peut appartenir à un autre objet.

Les fondus restent à la cadence du jeu (avance figée sur le dessin ajouté, phase 2).

## Azahar ralenti (lot B)

Limite de vitesse à 50 % dans le bac à sable : 29,3 dessins et 14,7 ticks par seconde réelle (le
rapport 2 pour 1 est conservé), aucun dessin sauté par le jeu, marche et changement de carte sans
plantage. Le jeu mesure son temps en ticks **émulés** (`svcGetSystemTick`) : un hôte lent ne
déclenche pas le saut d'image du jeu, il ralentit simplement tout. Un repli automatique « hôte trop
lent » n'est donc pas détectable depuis le jeu ; l'interrupteur L + Select en tient lieu.

## Interrupteur en jeu

**L + Select tenus 60 images (une seconde)** coupent ou rétablissent le lissage (`S.enabled`).
Lissage coupé, la boucle retrouve exactement le comportement d'origine (un dessin sur deux). Au
rétablissement, la table est vidée : aucune valeur d'avant la coupure n'est mélangée. Les boutons
viennent de `gfl::ui::CTR_DeviceManager` (`[r4+0x78]` juste après `nn::hid::PadReader::ReadLatest`).
Vérifié dans le bac à sable (dans les deux sens, aucun menu ouvert par la combinaison).

## Latence (mesure)

`tools/latcap.py` arrête le jeu à chaque VBlank, appuie sur une direction et suit l'écart de chaque
image à l'image d'avant l'appui. Boutique de Rosyères, 6 paires : la réaction (le personnage se
tourne) apparaît à l'image 0 ou 1 dans les deux modes, et le défilement du décor démarre vers
l'image 9 ou 10 lissage actif contre 13 lissage coupé : le premier demi-pas est montré plus tôt,
le lissage n'ajoute aucune latence côté jeu émulé. Une latence ressentie viendrait de l'hôte
(60 présentations par seconde au lieu de 30 : file d'images de la VSync, présentation asynchrone,
3DS à 59,83 Hz contre un écran à 60 Hz).

## Seuils (coupures, apparitions)

Pour chaque changement de `C`, avec `mag` = plus grande coordonnée de translation :

- translation : refus si l'écart dépasse `min(jump_t, jump_rel × mag + jump_min)`
  (48 ; 0,25 ; 0,5). Le terrain est en milliers d'unités (plafond 48, environ 2,5 cases), les
  objets proches de l'origine en unités (seuil de 0,5 à quelques unités) ;
- rotation/échelle : refus si un coefficient varie de plus de `jump_r` (0,7) pour un objet, de
  `jump_rcam` (0,25, environ 14°) pour une caméra : une coupure de plan est comptée dans `n_cut`.

Un refus fait reprendre directement `C` (pas de glissement). Une matrice vue pour la première
fois n'est pas mélangée.

## Mémoire

| Zone | Adresse | Contenu |
| --- | --- | --- |
| Crochets | 0x00579610–0x0057A000 (marge de fin de `.text`) | trampolines de `hooks.S`, 176 octets |
| Runtime | 0x004FBF20–0x004FE790 (fonction morte de 10 Ko : aucune référence, aucun littéral, non exportée par `static.crs`) | corps de `smooth.c`, 2,4 Ko, puis code des essais ; `build.py` vérifie ses premiers octets |
| Données des essais | 0x005EBA20–0x005EC000 (marge de fin de `.rodata`) | script d'entrées compilé |
| État `State` | 0x006AE640 (marge de fin de `.bss`, hors fichier) | initialisé au premier appel (magic `SMTH`) |
| Table | 0x0A000000, 288 Ko, `svcControlMemory` | 2 048 entrées de 120 octets (0x3C000) ; instantané en +0x3C000, trace en +0x3D000 (tests) |

Le `.bss` suit `.data` sans alignement : 0x0062F9F4 + 0x7EC2C = **0x006AE620**. Azahar n'applique
pas d'`exheader.bin` de remplacement : le `.bss` ne peut pas grandir, d'où l'allocation au
démarrage. Si elle échoue, `failed` ≠ 0 et le jeu garde son comportement d'origine.

## Structure `State` (0x006AE640, mots de 32 bits)

| Off. | Champ | | Off. | Champ |
| --- | --- | --- | --- | --- |
| 0x00 | magic `SMTH` | | 0x40 | vpad (tests) |
| 0x04 | **enabled** (0 = original, à chaud) | | 0x44 | n_skip |
| 0x08 | jump_t (f32) | | 0x48–0x6B | script et instantané (tests) |
| 0x0C | jump_r (f32) | | 0x6C | cam (dernière caméra) |
| 0x10 | tab_addr | | 0x70, 0x74 | trace, trace_n (tests) |
| 0x14 | tab_size | | 0x78, 0x7C | seen, anchor (tests) |
| 0x18 | tab | | 0x80 | jump_rel (f32) |
| 0x1C | failed | | 0x84 | jump_min (f32) |
| 0x20 | frame | | 0x88 | jump_rcam (f32) |
| 0x24 | interp | | 0x8C | n_cut |
| 0x28 | lastrec | | 0x90 | upd |
| 0x2C | n_interp | | 0x94, 0x98 | c3d_u, c3d_n (tests) |
| 0x30–0x3C | n_swap, n_jump, n_miss, n_rec | | 0x9C, 0xA0 | extra, n_fade |
| | | | 0xA4–0xB3 | eye[4] (caméras des yeux) |
| | | | 0xB4–0xC3 | eye_f[4] (image de la pose) |
| | | | 0xC4 | n_eye (vues d'yeux lissées) |
| | | | 0xC8, 0xCC | pad (boutons tenus), combo_f |
| | | | 0xD0, 0xD4 | tstate[2] (état des contextes de transition) |
| | | | 0xD8 | n_tskip (dessins ajoutés supprimés aux changements d'état) |

`tools/smstat.py` lit et modifie cette structure via le stub GDB (`set enabled 0`, `set jump_rcam 0.3`).

## Systèmes animés au dessin (phase 2)

Dessiner deux fois par tick ne doit rien faire avancer. Deux systèmes du jeu avancent pourtant
dans le bloc de dessin de `runEachFrame`, et sont neutralisés sur le dessin ajouté
(`S.extra` = image d'update, mode 30 Hz, lissage actif) :

| Système | Où | Effet sans correctif | Correctif |
| --- | --- | --- | --- |
| Transitions et fondus | 0x0011CB60 → 0x0012AF04, gestionnaire `*(0x0062F830)`, contextes `+0x38`/`+0x3C`, avance dans 0x0014BF90 | fondus deux fois plus rapides ; le rappel de changement de scène (`+0x40`) appelé deux fois plus souvent : le combat démarrait **84 images (1,4 s) plus tôt**, mesuré par la trace du RNG | crochet en 0x0010E5AC : octet `+0x46` posé (avance figée, dessin conservé) et rappel neutralisé le temps de l'appel |
| Animations de l'interface 2D | 0x0014D618 (temps d'animation + vitesse, rappel de fin), appelée par le dessin des mises en page 0x0012ABC4 | animations d'interface deux fois plus rapides, fins d'animation anticipées | crochet d'entrée : retour immédiat sur le dessin ajouté |

Méthode de détection : parties scriptées actives et désactivées, comparaison de l'index MT image
par image (une rafale de tirages décalée signale un événement décalé), puis `tools/drawdiff.py`
(mots du tas modifiés par un dessin ajouté) : sur le terrain et en combat, il ne reste que des
valeurs recalculées à chaque dessin.

Vérification finale (scène du rival, 4 000 images, `proto/replay/h-*`) : 3 parties actives et
3 désactivées identiques (rythme du RNG et état MT19937 final), une fois les générateurs MT19937
(0x08C55E64) et TinyMT (0x08C55E24) réinitialisés à l'ancre dans les builds de test.

## Combat (lot C) : 60 images, la « mi-cadence » était un artefact de mesure

La phase 2 concluait que le combat ne renouvelait l'image qu'un dessin sur deux (15 images/s
d'origine, 30 avec le lissage). **C'était faux** : la mesure (`tools/framecap.py`) arrête le jeu à
chaque VBlank par le stub GDB et capture la fenêtre ; en combat, scène lourde, l'image capturée
n'était pas celle du dernier dessin.

Mesure sans aucune pause (builds `--probe`, `tools/cadence.py`) : à chaque appel de la décision de
dessin, le runtime lit l'index du tampon affiché de l'écran du haut dans la mémoire partagée GSP
(`0x10002200`, tampons LCD en VRAM `0x1F300000` / `0x1F346600`), compte ses changements et prend
une empreinte de l'image présentée (un mot sur 97) pour compter les images identiques.

| Combat du rival (bac à sable, Vulkan ×6) | Ticks / s | Images présentées / s | Images identiques à la précédente |
| --- | --- | --- | --- |
| Lissage coupé | 29,5 | 29,2 | 0 sur 117 |
| Lissage actif, menu | 29,2 | 58,2 | 1 sur 233 |
| Lissage actif, attaque | 28,9 | 57,7 | 1 sur 347 |

Le combat utilise aussi les caméras des yeux (mise à jour stéréo 0x00377984 appelée par
`DllBattle`, puis `SetViewMatrix`) : le correctif du lot A les lisse aussi en combat ; il est
probable que c'est ce qui manquait au combat lors du premier essai réel (non mesuré avec
l'ancien patch).

Coût hôte en combat : en OpenGL ×6, Azahar tombe à 89 % de vitesse lissage actif (le jeu ralentit,
environ 51 images/s réelles) ; en Vulkan ×6, 96 à 106 %. Vulkan est à conseiller.

## Coût

| Scène | Vitesse d'émulation, lissage désactivé | actif |
| --- | --- | --- |
| Terrain (Route 103) | 100 % | 100 % (Vulkan), 87 % (OpenGL, bac à sable) |
| Combat | 102 % | 89 % (OpenGL ×6), 96 à 106 % (Vulkan ×6), bac à sable |

La 3DS émulée garde sa cadence (60 images par seconde **émulée** dans les deux cas) : c'est
l'ordinateur hôte qui doit rendre deux fois plus d'images. Le jeu n'est donc pas ralenti en temps
émulé, mais il peut l'être en temps réel sur une machine limite ou en résolution interne élevée.

## Construire

```bash
python runtime/build.py                      # release : runtime/build/code.ips
python runtime/build.py --counters --test-input [--count3d] -o runtime/build/code-test.ips
python runtime/build.py --counters --script proto/replay/rival.txt --snap 4000 --enabled 1 -o ...
python runtime/build.py --merge kaleido-shiny.ips   # fusion avec un autre code.ips
```

Script d'essai : `N BOUTONS` (image absolue), `@N BOUTONS` (relative à l'ancre = apparition du
joueur), `BOUTONS/40x6` = appui de 6 images toutes les 40. `build.py` refuse un `code.bin` dont le
SHA-256 diffère du profil et vérifie chaque instruction remplacée.
