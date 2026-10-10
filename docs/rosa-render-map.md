# ROSA — cartographie boucle principale et chemin de rendu (phase 0)

Cible analysée : **Pokémon Rubis Oméga (EUR), code cartouche v1.0** (`Pokemon Omega Ruby (Europe) (Rev 2).3ds`,
NCCH version 0x0002, ExHeader `sango-1` remaster 3, `code.bin` SHA-256
`d587c98a…bc1a37`, 5 439 488 octets). La mise à jour 1.4 n'est pas installée dans Azahar ;
Zetta_D a travaillé sur Saphir Alpha v1.4, dont la boucle est identique à **+8 octets** près.

Niveaux de confiance : **[V]** vérifié en jeu (compteurs / stub GDB), **[S]** établi en statique
(Ghidra + RTTI), **[H]** hypothèse à confirmer en phase 1.

## 1. Boucle principale `runEachFrame` — 0x0010E354 [V]

Appelée depuis `FUN_00108A48` (appel en 0x00108AD0) à chaque VBlank, ~60 fois par seconde, y compris
en mode 30 fps. Désassemblage complet et décompilation : `re/out/` (générés localement par `re/dis.py` et
`re/ghidra/Dump.java`, non publiés).

Objet « gestionnaire d'images » passé en `r0` (tas, **0x08C650B4** en v1.0) :

| Offset | Taille | Rôle |
| --- | --- | --- |
| +0x0C | u8 | mode demandé (2 = aucun) ; consommé par `FUN_00108A48` qui appelle `FUN_00110F14(gfx, 0/1)` (écrit l'octet +0x14 de chaque cible d'affichage) puis `FUN_00111008(gfx)` (remet +0x18 à 0) et remet la parité à 0 |
| +0x0D | u8 | **`mode`** : 1 = 30 fps (alternance update / draw), 0 = 60 fps (update + draw chaque image). C'est l'octet **0x08C650C1** écrit par les codes Reshiban v1.0 (0x08C690A1 en v1.4) |
| +0x0E | u8 | parité : basculée à chaque appel quand `mode` = 1 |
| +0x10 | f32 | échelle de temps passée à `FUN_0011CE44(gfx, 1.0f × valeur)` dans le chemin draw |
| +0x14 | ptr | processus courant (proc manager) |
| +0x18 | ptr | état « fin de jeu » (`[*+0]` ≠ 0 saute la partie proc) |
| +0x1C | ptr | contexte graphique : +0x1FC check GPU activé, +0x1FD check CPU activé, **+0x1FE `skip`** (saute le prochain draw) |
| +0x2C, +0x30 | ptr | gestionnaires mis à jour par `FUN_00122C6C` / `FUN_0012DDF4` |

Structure (adresses v1.0) :

```
0x10E374  mode == 0 ?  → r6 = 1 (update)                          [mode 0 : update + draw]
0x10E380  sinon parité ^= 1 ; r6 = parité                         [mode 1 : une image sur deux]
0x10E394  r6 = 1 : chemin UPDATE  (0x10E3D0 : FUN_00117ECC, FUN_00122C6C, FUN_0012DDF4, FUN_0011ED7C…)
0x10E3B8  r6 = 0 : chemin SANS update (0x10E4CC : vérification d'état du proc seulement)
0x10E530  jonction : si (mode & -r6) ≠ 0 → retour SANS draw      ← 0x10E53C `bne 0x10E554`
0x10E540  si skip : skip = 0, retour
0x10E568  svc 0x28 (GetSystemTick) ; DRAW :
          FUN_001117A4(gfx, 7)  FUN_0011ECE4?  FUN_0011CB60  FUN_00122BE0  FUN_0012286C
          FUN_00122BE0  FUN_00122810  FUN_00142350(gfx,1)  FUN_0011CE44(gfx, f)  FUN_0011153C(gfx)
0x10E620  svc 0x28 ; delta ; seuil = mode ? 0x8235 (33 333 µs) : 0x411A (16 666 µs)
          si (check GPU && FUN_0011D62C() > seuil) ou (check CPU && delta×3/…>16 666) → skip = 1
```

Le code mort 0x10E398–0x10E3B4 (8 mots : `mov r0,r0 ; nop ; nop ; mov r0,#0 ; cmp ; nop ; bne ; b`)
et 0x10E3B8–0x10E3C8 (5 mots) sont les emplacements utilisés par Zetta_D (AS v1.4 : 0x10E36C–0x10E38C)
et par nos compteurs.

**Mesures Azahar (écran titre, `mode` = 1), compteurs insérés dans le code (`proto/instrument.py`) :**

| Variante | update / s | images sans update / s | draw / s |
| --- | --- | --- | --- |
| Original (+ compteurs) | 29,6 | 29,6 | 29,6 |
| `0x10E53C` → `nop` (draw à chaque image) | 29,6 | 29,6 | **59,2** |

La logique reste strictement à 30 Hz ; le rendu passe à 60 Hz ; l'image est intacte. C'est le
prototype de la porte de phase 0. Sur une image « update », draw() dessine l'état tout juste calculé :
les images sont encore des doublons visuels (c'est la phase 1 qui y mettra des matrices interpolées).

Fonctions appelées par draw() (toutes dans `code.bin`, pas dans les CRO) — décompilation dans
`re/out/draw-callees-decomp.c` :

| Adresse | Rôle probable |
| --- | --- |
| 0x001117A4 | `gfx->BeginFrame(mask 7)` : parcourt les 3 écrans (haut G/D, bas), lie les cibles de rendu (`FUN_0011CDD0`), appelle `FUN_0011CE58` si une image est en attente |
| 0x0011CB60 | boucle sur 2 contextes (`FUN_0014BF90` : machine d'états de transition / fondu) puis libération des listes |
| 0x00122BE0 | lecture d'un champ global (+0x54) |
| 0x0012286C, 0x00122810 | soumission de listes de commandes (`FUN_0012ABC4`, `FUN_0012AA3C`) |
| 0x00142350 | test « temps GPU dépassé » (globals +0x80 / +0x84) |
| 0x0011CE44 | pas de temps du rendu (reçoit `1.0f × [mgr+0x10]`) : **à surveiller** en phase 1 (dessiner deux fois par tick ne doit pas l'avancer deux fois) |
| 0x0011153C | présentation : `FUN_0011D63C` (swap, `GetSystemTick`, compteur +0x2C modulo 2 = double buffer), `FUN_0011D1F4` (transfert vers les LCD, modes 0x400 / 0x410) |

## 2. Moteur de rendu identifié [S]

`code.bin` n'utilise **pas** `gfl2::renderingengine` (c'est Gen 7). Le RTTI Itanium (`re/rtti.py`,
1 505 vtables nommées dans `re/out/rtti-classes.txt`, importées dans le projet Ghidra) montre deux
pipelines :

1. **NintendoWare `nw::gfx` (NW4C)** : `SceneUpdater` (vtable 0x005DB370), `WorldMatrixUpdater`,
   `SkeletonUpdater` (0x005DB5EC), `Skeleton` / `StandardSkeleton`, `TransformNode` (0x005DB4B0),
   `Model` (0x005DBA84), `SkeletalModel` (0x005DB47C), `Camera` (0x005DBAB8) + `*ViewUpdater` /
   `*ProjectionUpdater`, `RenderContext` (0x005DB45C), `MeshRenderer` (0x005DB350),
   `MaterialActivator` (0x005DB714, `Activate` = 0x002FDEFC) et `SimpleMaterialActivator`
   (`Activate` = 0x003085D8), `SceneTraverser` (0x005DB500), files de rendu `BasicRenderQueue`.
   Même bibliothèque que Ocarina of Time 3D / Majora's Mask 3D.
2. **`gfl::grp::g3d` (couche Game Freak)** : `Scene` (0x005DDD50), `SceneSystem`, `RenderSystem`
   (0x005DD89C), `Camera` (0x005DDD6C, 22 virtuelles), `Model` (0x005DDCA8, 40 virtuelles) et le
   chemin **H3D** maison (`H3dModel` 0x005DDE0C, 65 virtuelles, `H3dCommand`, `H3dResSkeletalAnim`…)
   qui envoie ses propres commandes PICA (`FUN_00397CAC` : 2 424 octets d'écritures de registres).

Les modèles Pokémon et une partie du terrain passent par H3D ; le reste (UI 3D, particules, certains
décors) par `nw::gfx`. **Les deux chemins devront être interceptés** (le profil déclarera deux jeux
de hooks).

Points d'écriture GPU repérés (`re/pica_scan.py`, mots de commande PICA en dur) :

| Fonction | Mot | Rôle |
| --- | --- | --- |
| 0x00319CF0 (nw::gfx, appelée par les deux `Activate`) | `804F02C0` | uniformes flottants (textures / matériaux) |
| 0x00397CAC (gfl H3D) | `804F02C0` | uniformes flottants du matériau H3D |
| 0x0014B7B8, 0x0033899C, 0x004F5014 | `000F02C0` | écritures d'uniformes isolées |
| 0x002F01F4, 0x002FC284, 0x002F4240, 0x002F4870 (nw::gfx) | `orr #0x80000000` dynamique | constructeurs d'en-têtes de commandes ; 0x002FC284 alloue deux tampons (double buffer) |

Noms d'uniformes présents : `uModelView`, `uProjection` (0x005E6647 / 0x005E6627, utilisés par
0x00126B38 / 0x00136D04 : rendu 2D/layout bas niveau), `ViewUpdater.*` (propriétés de caméra NW4C).
L'envoi des matrices modèle / vue / os des deux pipelines **n'est pas encore localisé** : c'est la
première tâche de la phase 1 (voir § 4).

## 3. Décision : où intercepter les matrices

Dans NW4C, les matrices monde des `TransformNode` et les poses des squelettes sont calculées par
`SceneUpdater::UpdateAll` → `WorldMatrixUpdater` / `SkeletonUpdater`, c'est-à-dire pendant
**`update()`** (`gfl::grp::g3d::Scene::Calculate`), et `draw()` ne fait que les lire (`RenderContext`,
`MeshRenderer`). Le chemin H3D fait de même (animation échantillonnée côté logique, matrices stockées
dans `H3dModel`). C'est le cas « risque n° 1 » du PRD, et il se traite ainsi :

- **Interception côté consommateur, dans `draw()`**, à l'endroit où chaque pipeline envoie ses
  uniformes (vue, modèle×vue, palette d'os) : un seul point par pipeline, les matrices y arrivent
  déjà finales, et aucune écriture dans l'état du jeu n'est nécessaire (F2, F3).
- **Clé d'appariement** = adresse du nœud (`TransformNode` / `H3dModel`) + index d'os, stable tant
  que l'objet vit (méthode SoH) ; repli sur l'index d'occurrence dans l'image.
- `mtx_ring` enregistre la matrice à chaque **image avec update** (tick n) et la mélange à 50 % avec
  celle du tick n-1 sur l'image **sans update** ; `cam_epoch` compare la vue au tick précédent.
- Les images sans update n'existent que quand `mode` = 1 ; quand le jeu passe lui-même en `mode` = 0
  (menus 60 fps), le hook ne fait rien (`interp = mode && !r6`).

Le hook de la boucle principale se réduit donc à : `0x10E53C → nop` (draw sur l'image d'update) et un
drapeau `interp` posé sur le chemin 0x10E3B8 (image sans update), lu par les hooks de rendu.

## 4. Travail restant pour la phase 1 (ordre proposé)

1. Localiser l'envoi des matrices `nw::gfx` : point d'arrêt sur `MaterialActivator::Activate`
   (0x002FDEFC) pendant draw(), remonter la pile (`lr`) jusqu'à `MeshRenderer::RenderMesh`, puis
   suivre les écritures 0x2C0/0x2C1 ; identifier `RenderContext::SetCameraMatrix` / `SetModelMatrix` et
   l'envoi de la palette d'os de `SkeletalModel`.
2. Même chose pour H3D : à partir de `gfl::grp::g3d::RenderSystem` (0x003767E4) et `H3dModel`
   (vtable 0x005DDE0C), trouver la fonction qui écrit la matrice monde×vue et les os du modèle.
3. Offsets de `nw::gfx::TransformNode` (matrice monde) et de `gfl::grp::g3d::Camera` (vue / projection)
   pour l'appariement par adresse.
4. Vérifier `FUN_0011CE44` (pas de temps du rendu) : s'il avance une animation, le figer sur l'image
   intermédiaire.
5. Port des adresses vers v1.4 (mise à jour à installer dans Azahar) et Saphir Alpha par signature.

## 5. Outillage et pièges rencontrés

- Ghidra 12.1.4 headless, `code.bin` chargé brut à 0x00100000 (`ARM:LE:32:v6`), `.bss` ajouté par
  `re/ghidra/CtrLayout.java` ; dumps par `re/ghidra/Dump.java` ; symboles RTTI importés avec
  `ImportSymbolsScript`. Analyse automatique : 4 min. **Correction phase 1** : le `.bss` commence à
  0x0062F9F4 (juste après `.data`, sans alignement), pas à 0x00630000 ; sa marge libre est
  0x006AE620–0x006AF000.
- Stub GDB d'Azahar 2126.1.2 (**corrigé en phase 1**) : le pas à pas n'existe pas (`s` → `E5F`) et
  reprendre depuis un point d'arrêt le redéclenche aussitôt sans avancer ; les comptages de la
  phase 0 par points d'arrêt étaient donc faux (bornés par l'aller-retour GDB), seuls les compteurs
  insérés dans le code étaient fiables. Méthode correcte (`tools/gdbtrace.py`) : point d'arrêt à
  l'**entrée** d'une fonction, puis, pour enjamber l'appel, point d'arrêt sur son adresse de retour.
  Paquets jusqu'à 9 800 octets (`PacketSize`) : lectures par blocs de 4 Ko.
- Azahar ne lit la manette que si sa fenêtre a le focus, même avec
  `SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS`. Les essais automatisés injectent donc les boutons dans le
  jeu (`hook_pad`, builds de test), sans focus et à l'image près.
- `qt-config.ini` : une clé suivie de `clé\default=true` est ignorée par Azahar ; il faut écrire
  `use_gdbstub\default=false` **et** `use_gdbstub=true`, Azahar fermé (il réécrit le fichier en
  quittant).
- Le mot de la mise à jour 1.4 : Rubis Oméga Rev 2 contient le code v1.0 ; les adresses Zetta_D (AS
  v1.4) se retrouvent à +8 dans cette fonction.
