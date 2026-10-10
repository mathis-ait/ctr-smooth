#!/bin/bash
# to_battle.sh <code.ips> : bac a sable -> sauvegarde Route 103 -> combat du rival (ecran de choix).
# Verifie chaque etape par une capture (la sequence d'ecran titre echoue parfois).
T="$(cd "$(dirname "$0")" && pwd)"
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
SHOT="$TEMP/claude/C--Users-Thisma-Documents-Switch/fd8cf9a4-42f2-46d0-89ba-c6036ffbf612/scratchpad"
dark() { "$PY" -I -c "
from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert('L').crop((8,64,408,304))
print('noir' if sum(im.getdata())/(400*240) < 8 else 'ok')" "$SHOT/$1.png"; }
for attempt in 1 2 3; do
  bash "$T/sandbox.sh" start "$1" >/dev/null
  sleep 25
  "$PY" -I "$T/smstat.py" press "A 150" "wait 3000" "A 150" "wait 3000" "START 200" "wait 4000" "A 150" "wait 12000" >/dev/null
  bash "$T/shot.sh" tb_field >/dev/null
  [ "$(dark tb_field)" = ok ] && break
done
args=("LEFT 2500" "wait 1000"); for i in $(seq 1 45); do args+=("A 120" "wait 900"); done
args+=("wait 3000" "A 120" "wait 1500" "A 120" "wait 16000")
"$PY" -I "$T/smstat.py" press "${args[@]}" >/dev/null
bash "$T/shot.sh" battle
