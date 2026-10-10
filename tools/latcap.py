"""Latence entree -> image (bac a sable) : arrete le jeu a chaque VBlank, capture la
fenetre, appuie sur une direction a l'image --press, et mesure le nombre d'images
jusqu'au premier changement visible de l'ecran du haut. Mesure faite lissage actif
et coupe (State.enabled), en alternant les directions.

  latcap.py [--runs 6] [--dirs LEFT,RIGHT] [--crop 8,64,408,304]
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


def one(g, hwnd, button, crop, pre=4, post=16, settle=0.12):
    x0, y0, x1, y1 = crop
    imgs, upds = [], []
    for k in range(pre + post):
        if k == pre:
            g.write(VPAD, struct.pack('<I', mask_of(button)))
        if gdbtrace.wait_hit(g, RUN_EACH_FRAME) is None:
            break
        upds.append(struct.unpack('<I', g.read(0x006AEFF0, 4))[0])
        time.sleep(settle)
        imgs.append(capture(hwnd)[y0:y1, x0:x1].astype(np.int16))
    g.write(VPAD, struct.pack('<I', 0))
    base = imgs[pre - 1]
    noise = max(float(np.abs(imgs[i] - imgs[i - 1]).mean()) for i in range(1, pre))
    first = None
    for k in range(pre, len(imgs)):
        if float(np.abs(imgs[k] - base).mean()) > max(0.05, 3 * noise):
            first = k - pre
            break
    upd_at_press = upds[pre] - upds[pre - 1]
    series = ' '.join('%.2f%s' % (float(np.abs(imgs[k] - base).mean()), 'u' if upds[k] != upds[k - 1] else '') for k in range(pre, len(imgs)))
    print('   ecarts / image avant appui (u = image d update) :', series)
    return first, upd_at_press


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', type=int, default=6)
    ap.add_argument('--dirs', default='LEFT,RIGHT')
    ap.add_argument('--crop', default='8,64,408,304')
    a = ap.parse_args()
    crop = list(map(int, a.crop.split(',')))
    gdbtrace.load_code()
    hwnd = find_window()
    g = Rsp(timeout=5)
    g.cmd('?')
    dirs = a.dirs.split(',')
    res = {1: [], 0: []}
    n = 0
    for r in range(a.runs):
        for en in ((1, 0) if r % 2 == 0 else (0, 1)):
            g.write(STATE + 4, struct.pack('<I', en))
            g.send('c'); time.sleep(0.5); g.s.sendall(b'\x03'); g._recv_packet()
            d = dirs[n % len(dirs)]
            n += 1
            first, up = one(g, hwnd, d, crop)
            res[en].append(first)
            print('lissage %s  %-5s  premiere image changee : %s (update a l appui : %d)' % ('actif ' if en else 'coupe ', d, first, up))
            g.send('c'); time.sleep(0.4); g.s.sendall(b'\x03'); g._recv_packet()
    g.write(STATE + 4, struct.pack('<I', 1))
    g.send('c')
    for en in (1, 0):
        v = [x for x in res[en] if x is not None]
        print('%s : %s, moyenne %.2f images' % ('actif' if en else 'coupe', res[en], sum(v) / len(v) if v else -1))


if __name__ == '__main__':
    main()
