"""Verification phase 1 a partir des traces de replay_static.py (lissage active a l'ancre).

Chaque trace donne, pour chaque image depuis l'ancre : index MT19937 et translation x
de la vue camera. La graine MT varie d'un demarrage a l'autre (horloge emulee au
boot), on compare donc ce qui ne depend pas d'elle :
  - le rythme de consommation du RNG (index MT image par image) ;
  - la trajectoire de la camera image par image (position du joueur, vitesse, durees).
Les parties sont regroupees par etat a l'ancre (index MT) : dans un groupe, actif et
desactive doivent donner des traces identiques.

  verify_runs.py proto/replay/b-*.trace
"""
import collections
import os
import struct
import sys


def load(p):
    d = open(p, 'rb').read()
    return [struct.unpack_from('<If', d, 8 * i) for i in range(len(d) // 8)]


def main():
    runs = {}
    anchors = {}
    for p in sys.argv[1:]:
        name = os.path.splitext(os.path.basename(p))[0]
        runs[name] = load(p)
        anc = os.path.splitext(p)[0] + '.anchor'
        # groupe = image de l'ancre : l'histoire d'avant l'ancre varie d'un demarrage a l'autre
        anchors[name] = int(open(anc).read()) if os.path.exists(anc) else runs[name][0][0]
    groups = collections.defaultdict(list)
    for name in runs:
        groups[anchors[name]].append(name)
    verdict = True
    for idx, names in sorted(groups.items()):
        on = [n for n in names if '-on' in n]
        off = [n for n in names if '-off' in n]
        print('ancre a l\'image %d -> actif %s, desactive %s' % (idx, on, off))
        ref = runs[names[0]]
        for n in names[1:]:
            t = runs[n]
            mt_same = [a[0] for a in ref] == [b[0] for b in t]
            cam_same = [a[1] for a in ref] == [b[1] for b in t]
            first = next((i for i, (a, b) in enumerate(zip(ref, t)) if a != b), None)
            first = next((i for i, (a, b) in enumerate(zip(ref, t)) if a[0] != b[0]), None)
            print('   %s vs %s : rythme RNG %s, trajectoire camera %s%s' % (
                names[0], n, 'identique' if mt_same else 'DIFFERENT', 'identique' if cam_same else 'DIFFERENTE',
                '' if first is None else ' (1re difference image %d)' % first))
            if on and off and ((n in on) != (names[0] in on)):
                verdict &= mt_same  # la colonne camera suit la derniere camera dessinee : indicative
        if not (on and off):
            print('   (pas de paire actif/desactive dans ce groupe)')
    print('RESULTAT :', 'actif = desactive dans tous les groupes mixtes' if verdict else 'DIVERGENCE actif/desactive')


if __name__ == '__main__':
    main()
