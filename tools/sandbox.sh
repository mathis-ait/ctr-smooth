#!/bin/bash
# Azahar portable (bac a sable) pour les essais ctr-smooth. Jamais l'Azahar de l'utilisateur.
#   sandbox.sh start <code.ips|none>   lance Rubis Omega avec ce patch (fenetre discrete)
#     SANDBOX_SAVE=sandbox-save-mart : autre sauvegarde de reference (tools-re\<nom>)
#   sandbox.sh stop                    ferme l'Azahar portable
#   sandbox.sh continue                intro -> ecran titre -> Continuer (sauvegarde copiee)
# Azahar ne lit la manette que si sa fenetre a le focus : les entrees sont injectees
# dans le jeu par le runtime (builds --test-input, smstat.py press).
S="C:/Users/Thisma/Documents/Switch/tools-re/azahar-sandbox"
# SANDBOX_GAME=as : Saphir Alpha (Title ID 000400000011C500) au lieu de Rubis Oméga
if [ "$SANDBOX_GAME" = as ]; then
  ROM="C:/Users/Thisma/Documents/Switch/Pokemon Alpha Sapphire (Europe) (En,Ja,Fr,De,Es,It,Ko) (Rev 2).3ds"; TLO=0011c500
else
  ROM="C:/Users/Thisma/Documents/NDS & 3DS/Pokemon Omega Ruby (Europe) (En,Ja,Fr,De,Es,It,Ko) (Rev 2).3ds"; TLO=0011c400
fi
PY="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
T="$(cd "$(dirname "$0")" && pwd)"
case "$1" in
  stop)
    powershell -NoProfile -Command "Get-Process azahar -ErrorAction SilentlyContinue | Where-Object { \$_.Path -like '*azahar-sandbox*' } | Stop-Process -Force"
    sleep 2 ;;
  start)
    "$0" stop
    # sauvegarde de reference (Route 103, 0:29:09) recopiee a chaque lancement :
    # une partie scriptee peut sauvegarder (defaite, menus) et fausser les suivantes
    SAVE="$S/user/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/$TLO/data"
    rm -rf "$SAVE"; mkdir -p "$SAVE"; cp -r "C:/Users/Thisma/Documents/Switch/tools-re/${SANDBOX_SAVE:-sandbox-save-orig}/." "$SAVE/"
    M="$S/user/load/mods/00040000${TLO^^}"; mkdir -p "$M"; rm -f "$M/code.ips"
    [ "$2" != none ] && cp "$2" "$M/code.ips"
    cat > "$TEMP/ctr-smooth-launch.ps1" <<PS
\$env:SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS = '1'
\$env:SDL_JOYSTICK_WGI = '0'
Start-Process -FilePath '$S/azahar.exe' -ArgumentList '"$ROM"'
PS
    powershell -NoProfile -ExecutionPolicy Bypass -File "$TEMP/ctr-smooth-launch.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File "$T/offscreen.ps1"
    for i in $(seq 1 30); do netstat -an | grep -q ":24689 .*LISTENING" && break; sleep 1; done
    grep -a "patching\|GDB server" "$S/user/log/azahar_log.txt" | tail -2 | cut -c1-140 ;;
  continue)
    sleep 25
    "$PY" -I "$T/smstat.py" press "A 150" "wait 3000" "A 150" "wait 3000" "START 200" "wait 4000" "A 150" "wait 2500" "A 150" "wait 9000" ;;
esac
