# ctr-smooth : 60 fps natif pour Pokémon Rubis Oméga et Saphir Alpha (3DS)

Patch `code.ips` pour l'émulateur Azahar : le jeu affiche 60 images par seconde au lieu de 30,
**sans accélérer le jeu**. La logique reste à 30 Hz (musique, événements, durées et hasard
identiques à l'original) ; le jeu dessine à chaque VBlank et l'image ajoutée est rendue avec les
matrices de la caméra, des personnages et des squelettes interpolées entre les deux derniers ticks.

Ce dépôt est le runtime et l'outillage de rétro-ingénierie extraits de
[Kaleido](https://github.com/mathis-ait/kaleido), qui l'installe en un clic (Mods et réglages →
« 60 fps natif ») et le fusionne avec son taux de chromatiques.

## Utiliser le patch

- Jeux couverts, **version de la cartouche (1.0, Rev 2), sans la mise à jour 1.4** : Pokémon
  Rubis Oméga EUR (Title ID 000400000011C400, SHA-256 du `code.bin` décompressé `d587c98a…1a37`)
  et Saphir Alpha EUR (000400000011C500, `b7f9ce60…7c16`). Le même patch sert aux deux. Sur une
  autre version, il s'appliquerait à des adresses fausses.
- Copier `runtime/build/code.ips` dans `%APPDATA%\Azahar\load\mods\<Title ID>\code.ips`.
- En jeu, **L + Select** tenus une seconde coupent ou rétablissent le lissage.
- Préférer Vulkan : l'ordinateur dessine deux fois plus d'images.

## Ce que le dépôt ne contient pas

Aucune donnée du jeu : ni ROM, ni `code.bin`, ni extrait décompilé ou désassemblé du programme.
Les patchs ne contiennent que le code du runtime (C et assembleur de ce dépôt) et les branchements
vers lui. Pour recompiler ou poursuivre la rétro-ingénierie, il faut son propre `code.bin` extrait
de sa propre cartouche (`CTR_SMOOTH_CODE_BIN`, voir « Mise en place ») ; les décompilations citées
dans `docs/rosa-render-map.md` (`re/out/`) se régénèrent avec `re/ghidra/Dump.java`.

Licence : GPL-3.0 (comme Kaleido).

---

# Journal du projet

Runtime et outillage du PRD « 60 FPS natif : 3DS (ROSA) puis toutes plateformes ». Principe : la
logique du jeu reste à 30 Hz (`update()` jamais modifié), le jeu dessine à chaque VBlank, et l'image
ajoutée est rendue avec des matrices interpolées entre les deux derniers ticks.

Cible : Pokémon Rubis Oméga EUR, code cartouche v1.0 (Rev 2), Azahar 2126.1.2.

## Suite — lot F : Saphir Alpha, et correctif de la 0.9.0 (10 octobre 2026)

- **Saphir Alpha EUR 1.0** (SHA-256 `b7f9ce60…7c16`) : mêmes adresses que Rubis Oméga jusqu'à
  0x3E8000, puis 8 octets plus tôt ; `.rodata` et `.data` aux mêmes adresses (seuls des pointeurs
  vers le code changent). Aucun crochet ni aucune donnée lue par le runtime n'est concerné : **le
  même `code.ips` sert aux deux jeux** (`build.py --code` donne un fichier identique octet pour
  octet). Vérifié en jeu : intérieur 29 images distinctes sur 29, extérieur 27 sur 29 lissage actif
  contre 15 coupé ; Envol en virage 29 sur 29 contre 17 ; combat sauvage 58 images présentées par
  seconde réelle (57 pendant une attaque) contre 29 coupé.
- **Bug de la 0.9.0** : la « fonction morte » qui hébergeait le runtime (0x004FBF20) est une
  initialisation statique appelée au démarrage, sans référence directe (découvert parce que
  Saphir Alpha plantait). Dans Rubis Oméga, le démarrage exécutait le début du runtime, qui
  écrivait à une adresse non mappée, et le tableau qu'elle initialise (0x0062FC34) restait vide.
  Correctif : le runtime distribué tient entièrement dans la marge de fin de `.text` (compteurs de
  statistiques réservés aux builds de test) ; réinstaller depuis Kaleido remet la zone d'origine.
  Test de non-régression dans `crates/core/src/data/fps60_ctr.rs`.
- Mesures avec le build distribué : `build.py --inject` ajoute l'injection de boutons et du stick
  et le compteur des images présentées (code placé dans la marge de `.rodata`, bac à sable
  seulement) : les builds de test classiques plantent Saphir Alpha.

## Suite — lot E : intégration dans Kaleido (10 octobre 2026)

« Mods et réglages » de Rubis Oméga propose l'entrée **60 fps natif** (catégorie Fluidité). Kaleido
lit le programme de la ROM, vérifie son SHA-256 (profil `crates/core/src/data/fps60_ctr.rs`, qui
embarque `runtime/build/code.ips`), puis écrit un seul `code.ips` : le lissage fusionné avec le
`code.ips` déjà présent (taux de chromatiques), refusé s'ils écrivent aux mêmes octets. Le retrait
garde les autres patchs ; une version plus ancienne du runtime est remplacée. Entrée bloquée si une
mise à jour du jeu est installée dans Azahar ; installation refusée si un code de triche « 60 FPS »
est actif. Tests : `crates/core/tests/ctr_fps60_rom.rs` (ROM réelle, avec le taux de chromatiques et
avec le patch de la phase 2).

## Suite — lot D : scènes avec une sauvegarde de fin de jeu (10 octobre 2026)

Sauvegarde fournie (8 badges, Pokédex 721), copiée dans le bac à sable. Vulkan ×6, mesure sans
pause (`tools/cadence.py` : images présentées sur chaque écran et images identiques à la précédente).

| Scène | Images par seconde réelle, lissage actif | Remarque |
| --- | --- | --- |
| Vélo, Surf | 29 transitions distinctes sur 29, écarts réguliers | |
| Envol | 58, aucune image répétée | **corrigé** : la caméra (120 à 400 unités par tick) était refusée par le seuil de translation à chaque tick ; un grand déplacement qui prolonge le mouvement précédent est désormais mélangé |
| Atterrissage, Vol | transitions propres | |
| Méga-Évolution (Lucario) | 58 | aucun glissement, coupures de plan détectées |
| Pokémon-Amie | écran du bas (Pokémon 3D) 59 | écran du haut : fond 2D à 30, attendu |
| Super Entraînement | écran du haut 58 | à ×6, Azahar tombe à 25 % de vitesse **même lissage coupé** ; à ×3, 104 % |
| Concours Live (Poivressel) | 57, aucune image répétée | écran du bas 2D à 30 |
| Bases secrètes, cinématiques des légendaires | non testées | |

Après le changement de seuil, scène du rival rejouée (2 actives, 2 coupées) : état MT19937 final
identique à la phase 2.

## Suite — lot C : combats (9 octobre 2026)

| Combat du rival, Vulkan ×6, mesure sans pause GDB | Lissage coupé | Lissage actif |
| --- | --- | --- |
| Images présentées par seconde réelle | 29,2 | 58,2 (menu), 57,7 (attaque) |
| Images identiques à la précédente | 0 sur 117 | 1 sur 233, 1 sur 347 |
| Vitesse du jeu (ticks par seconde réelle) | 29,5 | 29,2 / 28,9 |

Le combat était déjà à 60 côté jeu : la limite « 15 → 30 » de la phase 2 était un artefact de la
capture sous GDB. Il utilise aussi les caméras des yeux, lissées depuis le lot A. En OpenGL ×6,
Azahar ne suit pas (89 % de vitesse) : Vulkan conseillé. Méthode : `build.py --probe`,
`tools/cadence.py` (index GSP du tampon affiché, empreinte des images).

## Suite — lot B : portes, Azahar ralenti, interrupteur (9 octobre 2026)

| Point | Résultat |
| --- | --- |
| Entrée dans un bâtiment | une image blanche au début du balayage (absente du jeu d'origine) : **corrigé** |
| Sortie d'un bâtiment | l'extérieur visible une image avant le fondu : **corrigé** |
| Azahar limité à 50 % | rapport tick / dessin conservé, aucun dessin sauté, pas de plantage |
| Interrupteur en jeu | **L + Select** tenus une seconde : lissage coupé ou rétabli |
| Place pour le code | ~~runtime déplacé dans une fonction morte~~ : zone erronée, corrigé au lot F (voir plus haut) |

Repli automatique « ordinateur trop lent » : impossible à détecter depuis le jeu (il compte en
temps émulé) ; l'interrupteur en tient lieu. Détails dans [`docs/runtime.md`](docs/runtime.md).

## Suite — lot A : intérieurs (9 octobre 2026)

Plan de la suite : [`docs/prd-suite.html`](docs/prd-suite.html). Premier essai réel : « dans les
bâtiments c'est un peu saccadé ». Cause trouvée : Rubis Oméga n'active la 3D stéréoscopique qu'en
intérieur, et le décor y est rendu avec les **caméras des yeux**, recalculées pendant `update()` et
que le lissage ne voyait pas. La pièce ne bougeait qu'une image sur deux, le joueur à chaque image.

| Mesure (boutique de Rosyères, marche) | Avant | Après |
| --- | --- | --- |
| Écarts image à image | alternance environ 6 / 0,25 | réguliers, 4,9 à 5,25 |
| Images distinctes | 39 sur 39, mais la pièce figée une image sur deux | 39 sur 39 |
| Tirages pendant les dessins ajoutés | | aucun |
| Extérieur (Rosyères) | | inchangé : 39 sur 39, écarts réguliers |

Correctif : crochet sur `SetViewMatrix` (0x00392FB4) qui retient les caméras des yeux, lissées au
début de chaque dessin. Détails dans [`docs/runtime.md`](docs/runtime.md) § Caméras stéréoscopiques.
Non mesuré : Centre Pokémon, maisons de Bourg-en-Vol (même chemin de rendu attendu).

## État de la phase 2 — squelettes, combats, coupures (9 octobre 2026)

Porte du PRD : *matrice de vérification complète au vert*. **Atteinte pour tout ce que la sauvegarde
disponible permet de jouer** (0 badge, 0:29 de jeu) ; le reste est listé plus bas.

Apports :

- **Interpolation à cadence adaptative** par matrice (`T` = intervalle entre deux changements) :
  contenu à 30 Hz comme en phase 1, contenu plus lent réparti sur plusieurs images.
- **Squelettes `nw::gfx`** : poses monde et skinning des `SkeletalModel` (utilisées en combat).
- **Coupures** : seuils relatifs à l'échelle de la scène, seuil de rotation serré pour les caméras
  (`n_cut`) ; 115 coupures détectées dans la scène du rival, sans image mélangée entre deux plans.
- **Systèmes animés au dessin neutralisés sur le dessin ajouté** : transitions et fondus (le combat
  démarrait 1,4 s plus tôt), animations d'interface 2D (deux fois trop rapides).
- **Coût CPU** : un modèle n'est traité qu'une fois par image (7 fois moins d'appels en combat).

| Scénario (PRD) | Mesure | Résultat |
| --- | --- | --- |
| Dialogue et événement scripté (rival, Route 103), coupure de caméra, combat de dresseur | 6 parties scriptées de 4 000 images (3 actives, 3 désactivées), générateurs MT19937 et TinyMT réinitialisés à l'apparition du joueur | **identiques** : rythme du RNG image par image et état MT final octet pour octet |
| Effets de bord du dessin ajouté | vidage du tas avant/après un dessin (`tools/drawdiff.py`) | terrain et combat : seulement des valeurs recalculées à chaque dessin (copies de la vue, pointeurs de tampons, mesure de profilage) |
| Tirages pendant le dessin ajouté | `tools/rngcheck.py` | aucun, en marche et en combat |
| Combat : cadence affichée | capture image par image (méthode fausse en combat, voir lot C) | ~~30 contre 15~~ : 58 contre 29 mesuré sans pause au lot C |

Non vérifiable avec cette sauvegarde : Méga-Évolution, Envol, Surf, Concours, Amie Pokémon,
Super Entraînement, Bases secrètes, cinématiques de légendaires, échanges et combats en ligne.
Changements de carte et Azahar ralenti / console réelle : prévus en phase 3.

~~Limite connue en combat~~ : **corrigé par le lot C** (voir plus haut) : la « mi-cadence » venait
de la méthode de mesure ; le combat s'affiche à 58 images/s avec le lissage.

**Coût hôte** : la 3DS émulée garde sa cadence avec le dessin ajouté ; c'est l'ordinateur qui rend
deux fois plus d'images (combat à 86 % de vitesse en OpenGL ×6 dans le bac à sable). Une résolution
interne plus basse ou Vulkan aident.

## État de la phase 1 — monde extérieur fluide (8 octobre 2026)

Porte du PRD : *Route 103 à 60 images distinctes, durées et RNG identiques à la référence* — **atteinte**.

| Critère | Mesure | Résultat |
| --- | --- | --- |
| 60 images distinctes | capture image par image en marchant sur la Route 103 (`tools/framecap.py`) | lissage actif : 29 transitions distinctes sur 29, écarts réguliers deux à deux ; désactivé : 14 sur 29 (une image sur deux en double) |
| Vitesse du jeu | compteurs dans `runEachFrame` | ticks logiques 28,7/s actif comme désactivé, dessins 57,6/s contre 28,7/s |
| Durées et RNG | 5 parties scriptées déterministes (`tools/replay_static.py`), lissage activé à l'apparition du joueur, instantané 800 images plus tard | 2 parties actives et 2 désactivées **identiques octet pour octet** : état complet du MT19937 (2 500 octets), matrice de vue, et trace image par image (rythme du RNG, trajectoire) |
| Aucun tirage pendant le dessin ajouté | point d'arrêt sur les 9 générateurs du jeu (`tools/rngcheck.py`) | 0 appel pendant un dessin interpolé, en combat et en marche |
| Coupures | seuils de saut (48 unités, 0,7) | environ 3 % des matrices refusées par image interpolée (os masqués par mise à l'échelle, apparitions), aucun glissement visible |
| Désactivation à chaud (F5) | `tools/smstat.py set enabled 0` | dessin d'origine (28,7/s), exactement les octets du jeu dans la boucle |

La cinquième partie scriptée (désactivée) a divergé des autres : c'est la variabilité propre au
démarrage d'Azahar, observée aussi entre deux parties désactivées, jamais liée au lissage.

Ce qui est lissé : caméra (vue et position), modèles H3D (personnages, Pokémon : déplacement **et**
animation squelettique, car leurs os sont en espace monde), modèles `nw::gfx` et, depuis la phase 2,
leurs squelettes. Restent à 30 Hz : particules, effets de texture, interface 2D.

Fonctionnement, adresses, mémoire et seuils : [`docs/runtime.md`](docs/runtime.md).
Cartographie du moteur : [`docs/rosa-render-map.md`](docs/rosa-render-map.md).
Profil : [`profiles/000400000011C400-v1.0.fps60.yaml`](profiles/000400000011C400-v1.0.fps60.yaml).

## Essayer

`runtime/build/code.ips` (lissage seul ; `build.py --merge` le fusionne avec un autre `code.ips`, par exemple
le taux de shiny écrit par Kaleido) se dépose en
`%APPDATA%\Azahar\load\mods\000400000011C400\code.ips`. Rubis Oméga EUR **sans la mise à jour 1.4**
uniquement : sur une autre version, Azahar appliquerait le patch à des adresses fausses.

## Phase 0 (fondations) — rappel

Boucle `runEachFrame` en 0x0010E354 (adresses de Zetta_D sur AS v1.4 décalées de 8), octet `mode` en
gestionnaire+0x0D (0x08C650C1, cible des codes Reshiban), moteur NW4C `nw::gfx` + `gfl::grp::g3d`
H3D, 1 505 classes nommées par le RTTI.

## Arborescence

```
runtime/smooth.c      runtime C (interpolation, table, restauration, essais)
runtime/hooks.S       trampolines ARM des crochets
runtime/link.ld       placement dans les marges de code.bin
runtime/build.py      compilation + IPS vérifié (SHA-256, octets d'origine) ; --test-input, --script
tools/sandbox.sh      Azahar portable isolé (jamais l'Azahar de l'utilisateur), fenêtre discrète
tools/smstat.py       état du runtime via GDB : lecture, set enabled, watch, press (entrées injectées)
tools/gdbtrace.py     traces d'appels (entrée de fonction + adresse de retour), dumps mémoire
tools/framecap.py     capture image par image et comptage des images distinctes
tools/replay_static.py partie scriptée sans pause GDB ; snapdiff.py, verify_runs.py, tracediff.py
tools/drawdiff.py     effets de bord d'un dessin sur le tas du jeu (dessin ajouté / d'origine)
tools/perframe.py, emuspeed.py, rtcap.py, rtcheck.py, encounter.sh   mesures complémentaires
runtime/test.c        code des essais (Thumb, builds de test seulement, voir docs/runtime.md § Mémoire)
tools/rngcheck.py     tirages aléatoires pendant les dessins interpolés
tools/azahar_gdb.py   client GDB RSP ; mkpatch.py : IPS ; ini_set.py / sandbox_config.py : config
proto/replay/         scripts (Route 103, rival), traces des séries de vérification, rapports drawdiff
re/                   outillage Ghidra, désassemblage, RTTI, scans
```

## Mise en place (machine de développement)

Outils hors dépôt dans `C:\Users\Thisma\Documents\Switch\tools-re\` : `jdk\`, `ghidra\`, `gcc\`
(xpack arm-none-eabi 15.2.1), projet Ghidra `ghidra-proj\rosa`, `rosa-or\code.bin`, et
`azahar-sandbox\` (Azahar portable : config, sauvegarde et mods copiés, horloge fixe, rendu OpenGL,
stub GDB actif). Python 3.12 (`%LOCALAPPDATA%\Programs\Python\Python312\python.exe`) avec `capstone`,
`keystone-engine`, `numpy`, `pillow`.

```bash
python runtime/build.py
python runtime/build.py --counters --test-input -o runtime/build/code-test.ips
bash tools/sandbox.sh start runtime/build/code-test.ips && bash tools/sandbox.sh continue
python tools/smstat.py watch 3
```

Pièges : Azahar ne lit la manette qu'avec le focus (d'où l'injection), une fenêtre hors écran ne
reçoit rien, et une fenêtre Vulkan masquée ne se rafraîchit plus quand l'émulation est en pause
(d'où OpenGL dans le bac à sable). Détails dans `docs/rosa-render-map.md` § 5.
