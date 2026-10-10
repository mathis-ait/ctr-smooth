#!/bin/bash
# to_training.sh <code.ips> : sauvegarde sandbox-save-fr -> Navi-Fun -> SPV -> test contre Lepidonille
T="$(cd "$(dirname "$0")" && pwd)"
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
bash "$T/to_save.sh" "$1" sandbox-save-fr >/dev/null
t() { "$PY" -I "$T/smstat.py" touch "$1" "$2" 250 >/dev/null; "$PY" -I "$T/smstat.py" press "wait $3" >/dev/null; }
t 284 105 8000; t 105 155 14000; t 160 170 14000
for i in 1 2 3; do t 308 10 2000; done
t 305 220 10000
"$PY" -I "$T/smstat.py" press "A 150" "wait 1500" "A 150" "wait 1500" >/dev/null
for i in 1 2 3 4 5; do t 160 50 1500; done
t 22 188 9000; t 160 50 1500; t 160 50 1500; t 160 130 3000; t 160 130 16000
bash "$T/shot.sh" training
