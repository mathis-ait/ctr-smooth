#!/bin/bash
# to_amie.sh <code.ips> : sauvegarde sandbox-save-fr -> Navi-Fun -> Poke Recre (Pokemon-Amie) avec Gardevoir
T="$(cd "$(dirname "$0")" && pwd)"
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
bash "$T/to_save.sh" "$1" sandbox-save-fr >/dev/null
t() { "$PY" -I "$T/smstat.py" touch "$1" "$2" 250 >/dev/null; "$PY" -I "$T/smstat.py" press "wait $3" >/dev/null; }
t 284 105 8000      # Navi-Fun
t 105 100 10000     # Jouer avec un Pokemon
t 160 170 12000     # lecture
for i in 1 2 3 4; do t 308 10 1500; done
t 305 220 8000      # fin du tutoriel
t 157 122 10000     # Gardevoir
t 157 180 16000     # Jouer
bash "$T/shot.sh" amie
