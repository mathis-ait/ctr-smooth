"""Etat du gestionnaire de transitions image par image autour d'un passage de porte
(bac a sable) : capture la fenetre et vide *(0x0062F830) (0x60 octets) et ses
contextes +0x38 / +0x3C (0x60 octets) a chaque VBlank, repere l'image parasite
(pic d'ecart isole) et affiche les mots qui changent autour.

  transtrace.py --hold DOWN [-n 60]
"""
import argparse
import os
import struct
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp  # noqa: E402
import gdbtrace  # noqa: E402
from framecap import RUN_EACH_FRAME, VPAD, capture, find_window, mask_of  # noqa: E402

STATE = 0x006AE640


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hold', default='DOWN')
    ap.add_argument('-n', type=int, default=60)
    a = ap.parse_args()
    gdbtrace.load_code()
    hwnd = find_window()
    g = Rsp(timeout=5)
    g.cmd('?')
    g.write(VPAD, struct.pack('<I', mask_of(a.hold)))
    rows = []
    for k in range(a.n):
        if gdbtrace.wait_hit(g, RUN_EACH_FRAME) is None:
            break
        tm, = struct.unpack('<I', g.read(0x0062F830, 4))
        m = g.read(tm, 0x60) if tm else b''
        c0, c1 = struct.unpack_from('<II', m, 0x38) if m else (0, 0)
        d0 = g.read(c0, 0x60) if c0 else b''
        d1 = g.read(c1, 0x60) if c1 else b''
        upd, = struct.unpack('<I', g.read(0x006AEFF0, 4))
        time.sleep(0.08)
        img = capture(hwnd)[64:304, 8:408].astype(np.int16)
        rows.append((upd, m, d0, d1, img))
    g.write(VPAD, struct.pack('<I', 0))
    g.send('c')
    diffs = [0.0] + [float(np.abs(rows[i][4] - rows[i - 1][4]).mean()) for i in range(1, len(rows))]
    # image parasite : ecart avec la precedente ET la suivante, alors que precedente ~ suivante
    flash = None
    for i in range(1, len(rows) - 1):
        if diffs[i] > 15 and diffs[i + 1] > 15:
            flash = i
            break
    print('ecarts :', ' '.join('%.1f' % d for d in diffs))
    print('image parasite :', flash)
    lo = max(1, (flash or 10) - 6)
    hi = min(len(rows), (flash or 10) + 4)
    for name, idx in (('gest', 1), ('ctx0', 2), ('ctx1', 3)):
        for off in range(0, 0x60, 4):
            vals = [struct.unpack_from('<I', rows[i][idx], off)[0] if len(rows[i][idx]) > off else None for i in range(lo, hi)]
            if len(set(vals)) > 1:
                print('%s+%02x' % (name, off), ' '.join('%08x' % v if v is not None else '--------' for v in vals))
    print('update      ', ' '.join('%8d' % (rows[i][0] - rows[i - 1][0]) for i in range(lo, hi)))
    print('images      ', ' '.join('%8d' % i for i in range(lo, hi)))


if __name__ == '__main__':
    main()
