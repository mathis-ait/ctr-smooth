#!/bin/bash
# shot.sh <nom> : capture la fenetre Azahar dans le scratchpad (ou chemin absolu)
out="$1"; case "$out" in /*|?:*) ;; *) out="$TEMP/claude/C--Users-Thisma-Documents-Switch/fd8cf9a4-42f2-46d0-89ba-c6036ffbf612/scratchpad/$1.png";; esac
powershell -NoProfile -ExecutionPolicy Bypass -File "$(dirname "$0")/azahar_win.ps1" shot "$(cygpath -w "$out" 2>/dev/null || echo "$out")" | tail -1
