"""Verifie qu'aucun generateur aleatoire du jeu n'est appele pendant un dessin
interpole (promesse O3/O4 : RNG identique). A chaque appel d'une fonction de
tirage, on lit State.interp du runtime : 1 = l'appel a lieu dans le dessin ajoute.

  rngcheck.py [--secs 4] [ADDR ...]
Par defaut : les generateurs reperes dans code.bin OR EUR v1.0 (TinyMT, MT19937,
LCG 32 et 64 bits).
"""
import argparse
import os
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp  # noqa: E402
import gdbtrace  # noqa: E402

STATE = 0x006AE640
INTERP = STATE + 0x24
DEFAULT = {
    0x0011A204: 'TinyMT next',
    0x00164798: 'TinyMT (2)',
    0x00168AC8: 'LCG 41C64E6D (1)',
    0x00175F68: 'LCG 41C64E6D (2)',
    0x0018592C: 'MT19937 (1)',
    0x002DAE74: 'LCG64 (init)',
    0x002DBB04: 'LCG64 / TinyMT',
    0x004FE798: 'MT19937 (2)',
    0x00507C18: 'LCG 41C64E6D (3)',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--secs', type=float, default=4.0)
    ap.add_argument('addrs', nargs='*')
    a = ap.parse_args()
    funcs = {int(x, 16): x for x in a.addrs} if a.addrs else DEFAULT
    gdbtrace.load_code()
    g = Rsp(timeout=5)
    g.cmd('?')
    total_bad = 0
    for addr, name in funcs.items():
        n = bad = 0
        stacks = set()
        t0 = time.time()
        while time.time() - t0 < a.secs:
            if gdbtrace.wait_hit(g, addr, timeout=a.secs) is None:
                break
            n += 1
            interp = struct.unpack('<I', g.read(INTERP, 4))[0]
            if interp:
                bad += 1
                regs = gdbtrace.stop_regs(g)
                stacks.add('%08x' % regs[14])
        total_bad += bad
        print('  %08x %-18s appels %4d   pendant un dessin interpole : %d %s' % (
            addr, name, n, bad, ('lr=' + ','.join(sorted(stacks))) if stacks else ''))
    g.send('c')
    print('RESULTAT :', 'aucun tirage pendant les dessins interpoles' if total_bad == 0 else '%d tirages pendant des dessins interpoles' % total_bad)


if __name__ == '__main__':
    main()
