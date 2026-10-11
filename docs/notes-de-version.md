# Brouillon : notes de version du « 60 fps natif »

À reprendre dans les notes de la release qui l'embarquera (version à fixer au moment de la release).

---

# (prochaine version) : mises à jour 1.4

## 60 fps natif
- Rubis Oméga et Saphir Alpha **avec la mise à jour 1.4** installée dans Azahar : Kaleido lit le programme de la mise à jour et pose le patch qui lui correspond. La version de la cartouche (1.0) reste couverte.
- Si tu installes ou retires la mise à jour 1.4 après avoir activé le 60 fps natif, l'entrée le signale : clique sur Mettre à jour pour refaire le patch pour la nouvelle version, ou sur Retirer.
- Avec la mise à jour 1.4, le taux de chromatiques du Randomizer ne peut pas s'ajouter : il est calculé pour la version de la cartouche.

---

# Kaleido 0.9.0 : Rubis Oméga en 60 fps natif (voir aussi 0.10.1 : Saphir Alpha et correctif)

## 60 fps natif (expérimental)
- Nouvelle entrée « 60 fps natif » dans **Mods et réglages** de Pokémon Rubis Oméga (catégorie Fluidité). Le jeu affiche 60 images par seconde au lieu de 30 : caméra, personnages et Pokémon bougent entre deux images, en exploration, en intérieur, en combat, en Envol, en Surf, pendant les Méga-Évolutions, les Concours et Pokémon-Amie.
- La vitesse du jeu ne change pas : la logique tourne toujours à 30 images par seconde, donc la musique, les événements, les durées et le hasard restent ceux d'origine (vérifié sur des parties rejouées à l'identique). Ce n'est pas un code « 60 FPS » qui accélère tout le jeu.
- Les menus, textes et effets en 2D restent à 30 images par seconde.
- **L + Select**, tenus une seconde en jeu, coupent ou rétablissent le lissage.
- Se combine avec le taux de chromatiques du Randomizer : Kaleido fusionne les deux dans un seul patch. Retirer le 60 fps natif garde le taux de chromatiques.

## À savoir
- Version couverte : Rubis Oméga **européen, version de la cartouche (1.0), sans la mise à jour 1.4**. Kaleido vérifie la ROM et bloque l'option si une mise à jour du jeu est installée dans Azahar. Saphir Alpha et la 1.4 viendront ensuite.
- L'ordinateur dessine deux fois plus d'images : préfère **Vulkan** dans Azahar. Le Super Entraînement est lourd en résolution ×6, même sans le 60 fps natif : ×3 suffit.
- Les codes de triche « 60 FPS » doivent rester désactivés (Kaleido refuse d'installer tant que l'un d'eux est actif).
- Relancer un mod depuis le Randomizer remplace le dossier du jeu dans Azahar : réactive alors le 60 fps natif.
- Pas de 60 fps sur une vraie console : ce mode est fait pour Azahar.
