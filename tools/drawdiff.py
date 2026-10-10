"""Effets de bord du dessin : quels mots du tas du jeu un dessin modifie-t-il ?

Arrete le jeu au debut d'un dessin (0x0010E564, apres la decision de dessin) puis a
sa fin (0x0010E61C, avant la restauration du runtime), vide le tas a chaque fois et
compare. Les matrices remplacees par le runtime (entrees de la table avec swp =
image courante) sont exclues. Fait la mesure pour un dessin ajoute (image d'update)
et pour un dessin d'origine (image sans update) : un etat qui avance dans les deux
est un systeme anime au dessin, que le dessin ajoute ferait avancer deux fois.

  drawdiff.py [--base 0x08000000] [--len 0xDF0000] [-o rapport.txt]
"""
import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp  # noqa: E402
import gdbtrace  # noqa: E402

STATE = 0x006AE640
DRAW_BEGIN, DRAW_END = 0x0010E564, 0x0010E61C
ENTRY = 128
TAB_N = 2048


def st(g, off):
    return struct.unpack('<I', g.read(STATE + off, 4))[0]


def run_to(g, addr):
    g.set_bp(addr)
    g.cont()
    g.clear_bp(addr)


def swapped(g, frame):
    tab = st(g, 0x18)
    raw = g.read(tab, TAB_N * ENTRY)
    out = set()
    for i in range(TAB_N):
        key, obs, swp = struct.unpack_from('<III', raw, i * ENTRY)
        if key and swp == frame:
            out.update(range(key, key + 48, 4))
    return out


def measure(g, want_extra, base, length):
    # avancer jusqu'a un debut de dessin du type voulu
    for _ in range(8):
        run_to(g, DRAW_BEGIN)
        if st(g, 0x9C) == want_extra:
            break
        run_to(g, DRAW_END)
    frame = st(g, 0x20)
    a = np.frombuffer(g.read(base, length), dtype='<u4')
    run_to(g, DRAW_END)
    b = np.frombuffer(g.read(base, length), dtype='<u4')
    excl = swapped(g, frame) if want_extra else set()
    idx = np.nonzero(a != b)[0]
    rows = []
    for i in idx:
        addr = base + 4 * int(i)
        if addr in excl:
            continue
        rows.append((addr, int(a[i]), int(b[i])))
    return frame, rows


def describe(addr, x, y):
    fx, fy = struct.unpack('<ff', struct.pack('<II', x, y))
    s = '%08x : %08x -> %08x' % (addr, x, y)
    if 1e-6 < abs(fx) < 1e7 and 1e-6 < abs(fy) < 1e7:
        s += '   (%.4f -> %.4f, %+.4f)' % (fx, fy, fy - fx)
    elif abs(y - x) < 1000:
        s += '   (entier %+d)' % (y - x)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', type=lambda s: int(s, 0), default=0x08000000)
    ap.add_argument('--len', type=lambda s: int(s, 0), default=0xDF0000)
    ap.add_argument('-o', default='drawdiff.txt')
    a = ap.parse_args()
    gdbtrace.load_code()
    g = Rsp(timeout=30)
    g.cmd('?')
    fe, extra = measure(g, 1, a.base, a.len)
    fn, normal = measure(g, 0, a.base, a.len)
    g.send('c')
    ne = {r[0] for r in normal}
    both = [r for r in extra if r[0] in ne]
    only_extra = [r for r in extra if r[0] not in ne]
    with open(a.o, 'w', encoding='utf-8') as f:
        f.write('dessin ajoute (image %d) : %d mots modifies hors matrices lissees\n' % (fe, len(extra)))
        f.write('dessin d origine (image %d) : %d mots modifies\n' % (fn, len(normal)))
        f.write('\n== modifies par les deux dessins (etat qui avance a chaque dessin) : %d\n' % len(both))
        for r in both:
            f.write(describe(*r) + '\n')
        f.write('\n== modifies seulement par le dessin ajoute : %d\n' % len(only_extra))
        for r in only_extra:
            f.write(describe(*r) + '\n')
    print('dessin ajoute : %d mots, dessin d origine : %d mots, communs : %d -> %s' % (len(extra), len(normal), len(both), a.o))


if __name__ == '__main__':
    main()
