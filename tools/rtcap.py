"""Capture en temps reel (sans pause GDB) de la fenetre Azahar du bac a sable :
PrintWindow en boucle pendant N secondes, puis nombre d'images distinctes par
seconde reelle. Mesure la cadence vue par le joueur.

  rtcap.py [--secs 3] [--crop x0,y0,x1,y1]
"""
import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from framecap import capture, find_window  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--secs', type=float, default=3.0)
    ap.add_argument('--crop', default='8,64,408,304')
    a = ap.parse_args()
    x0, y0, x1, y1 = map(int, a.crop.split(','))
    hwnd = find_window()
    shots = []
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < a.secs:
        shots.append((time.perf_counter(), capture(hwnd)[y0:y1, x0:x1].copy()))
    dt = shots[-1][0] - shots[0][0]
    changes = 0
    for i in range(1, len(shots)):
        if np.abs(shots[i][1].astype(np.int16) - shots[i - 1][1].astype(np.int16)).mean() > 0.05:
            changes += 1
    print('%d captures en %.2f s (%.0f/s) : %d changements d image = %.1f images distinctes par seconde' % (
        len(shots), dt, len(shots) / dt, changes, changes / dt))


if __name__ == '__main__':
    main()
