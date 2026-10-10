#!/bin/bash
# to_save.sh <code.ips> <sauvegarde> : bac a sable -> ecran titre -> Continuer, avec la sauvegarde
# de reference tools-re/<sauvegarde> (sandbox-save-orig, sandbox-save-mart, sandbox-save-fr).
T="$(cd "$(dirname "$0")" && pwd)"
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
SHOT="$TEMP/claude/C--Users-Thisma-Documents-Switch/fd8cf9a4-42f2-46d0-89ba-c6036ffbf612/scratchpad"
dark() { "$PY" -I -c "
from PIL import Image; import sys; im=Image.open(sys.argv[1]).convert('L'); w,h=im.size; im=im.crop((w//2-150,70,w//2+150,280))
print('noir' if sum(im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata())/(300*210) < 8 else 'ok')" "$SHOT/$1.png"; }
for attempt in 1 2 3; do
  SANDBOX_SAVE="$2" bash "$T/sandbox.sh" start "$1" >/dev/null
  sleep 25
  "$PY" -I "$T/smstat.py" press "A 150" "wait 3000" "A 150" "wait 3000" "START 200" "wait 4000" "A 150" "wait 12000" >/dev/null
  bash "$T/shot.sh" ts_field >/dev/null
  # encore sur le menu de l'ecran titre (ecran du bas blanc) : A de plus
  for k in 1 2; do
    w=$("$PY" -I -c "
from PIL import Image; import sys; p=Image.open(sys.argv[1]).convert('RGB').getpixel((200,360)); print('titre' if min(p) > 235 else 'jeu')" "$SHOT/ts_field.png")
    [ "$w" = titre ] || break
    "$PY" -I "$T/smstat.py" press "A 150" "wait 12000" >/dev/null
    bash "$T/shot.sh" ts_field >/dev/null
  done
  [ "$(dark ts_field)" = ok ] && break
done
echo "$SHOT/ts_field.png"
