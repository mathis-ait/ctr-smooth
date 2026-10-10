#!/bin/bash
# encounter.sh : allers-retours dans les hautes herbes (Route 103) jusqu'a un combat.
# Detection : le terrain est surtout vert ; l'ecran de combat ne l'est pas.
T="$(cd "$(dirname "$0")" && pwd)"; PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
SP="$TEMP/claude/C--Users-Thisma-Documents-Switch/fd8cf9a4-42f2-46d0-89ba-c6036ffbf612/scratchpad"
for i in $(seq 1 ${1:-20}); do
  timeout 60 "$PY" -I "$T/smstat.py" press "DOWN 700" "UP 700" >/dev/null
  "$T/shot.sh" enc >/dev/null
  g=$("$PY" -I -c "
from PIL import Image; import numpy as np
im=np.asarray(Image.open(r'$SP/enc.png'))[64:304,8:408,:3].astype(int)
print(int((im[:,:,1]-im[:,:,0]).mean()))")
  echo "essai $i : indice vert $g"
  if [ "$g" -lt 30 ]; then sleep 6; "$T/shot.sh" enc >/dev/null; echo "combat"; exit 0; fi
done
exit 1
