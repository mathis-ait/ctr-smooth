"""Mises à jour installées dans l'Azahar du bac à sable (jamais celui de l'utilisateur).

  sandbox_update.py stash NOM        range la mise à jour installée (title/0004000e) sous NOM
  sandbox_update.py use NOM|none     installe la mise à jour rangée NOM, ou aucune

Les mises à jour rangées vivent dans tools-re/sandbox-updates/NOM (installées une fois avec
« azahar.exe -i fichier.cia » dans le bac à sable, puis rangées).
"""
import os
import shutil
import sys

TOOLS = r'C:\Users\Thisma\Documents\Switch\tools-re'
SDMC = os.path.join(TOOLS, 'azahar-sandbox', 'user', 'sdmc', 'Nintendo 3DS', '0' * 32, '0' * 32, 'title')
UPD = os.path.join(SDMC, '0004000e')
STORE = os.path.join(TOOLS, 'sandbox-updates')


def main():
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == 'stash':
        dst = os.path.join(STORE, name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.move(UPD, dst)
        print('rangée :', dst)
    elif cmd == 'use':
        if os.path.isdir(UPD):
            shutil.rmtree(UPD)
        if name != 'none':
            shutil.copytree(os.path.join(STORE, name), UPD)
        print('mise à jour du bac à sable :', name)


if __name__ == '__main__':
    main()
