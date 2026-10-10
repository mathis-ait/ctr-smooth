#!/bin/bash
# to_soar.sh <code.ips> : sauvegarde sandbox-save-fr (labo de Bourg-en-Vol) -> sortie -> Flute Eon -> Envol
T="$(cd "$(dirname "$0")" && pwd)"
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
bash "$T/to_save.sh" "$1" sandbox-save-fr >/dev/null
args=("DOWN 2500" "wait 1000" "DOWN 1500" "wait 4500" "DOWN 600" "wait 300" "X 300" "wait 2000" "DOWN 150" "wait 500" "A 150" "wait 2500" "LEFT 150" "wait 900")
for i in $(seq 1 7); do args+=("DOWN 120" "wait 250"); done
args+=("A 150" "wait 1500" "A 150" "wait 3000" "A 150" "wait 15000")
"$PY" -I "$T/smstat.py" press "${args[@]}" >/dev/null
bash "$T/shot.sh" soar
