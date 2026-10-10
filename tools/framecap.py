"""Capture image par image d'Azahar (bac a sable) pendant un deplacement, pour
verifier « 60 images distinctes » : le stub GDB arrete le jeu a chaque entree de
runEachFrame (1 arret = 1 VBlank), on capture la fenetre (PrintWindow) puis on
compare chaque image a la precedente.

  framecap.py [-n 40] [--hold LEFT] [--out dossier] [--crop x0,y0,x1,y1]

Sortie : pour chaque image, l'ecart moyen avec la precedente (0 = doublon) et un
resume : images distinctes / images capturees.
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os

import struct
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp  # noqa: E402
import gdbtrace  # noqa: E402

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
RUN_EACH_FRAME = 0x0010E354


def find_window():
    import subprocess
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "(Get-Process azahar | Where-Object { $_.Path -like '*azahar-sandbox*' -and $_.MainWindowHandle -ne 0 }).MainWindowHandle"],
                         capture_output=True, text=True).stdout.strip().splitlines()
    return int(out[0])


def capture(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)

    class BMI(ctypes.Structure):
        _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG), ('biPlanes', wt.WORD),
                    ('biBitCount', wt.WORD), ('biCompression', wt.DWORD), ('biSizeImage', wt.DWORD),
                    ('biXPelsPerMeter', wt.LONG), ('biYPelsPerMeter', wt.LONG), ('biClrUsed', wt.DWORD),
                    ('biClrImportant', wt.DWORD)]
    bmi = BMI(ctypes.sizeof(BMI), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    return np.frombuffer(buf.raw, dtype=np.uint8).reshape(h, w, 4)[:, :, 2::-1]


VPAD = 0x006AE640 + 0x40  # State.vpad (builds --test-input)
BUTTONS = {'A': 1, 'B': 2, 'SELECT': 4, 'START': 8, 'RIGHT': 0x10, 'LEFT': 0x20, 'UP': 0x40, 'DOWN': 0x80,
           'R': 0x100, 'L': 0x200, 'X': 0x400, 'Y': 0x800}


def mask_of(spec):
    m = 0
    for b in spec.upper().split('+'):
        if b:
            m |= BUTTONS[b]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', type=int, default=40)
    ap.add_argument('--hold', default='LEFT')
    ap.add_argument('--out')
    ap.add_argument('--crop', default='')
    ap.add_argument('--settle', type=float, default=0.12)
    ap.add_argument('--stats', action='store_true', help='compteurs du runtime image par image')
    a = ap.parse_args()
    gdbtrace.load_code()
    hwnd = find_window()
    g = Rsp(timeout=5)
    g.cmd('?')
    if a.hold:
        g.write(VPAD, struct.pack('<I', mask_of(a.hold)))
    g.send('c')
    time.sleep(0.6)  # le personnage se met en mouvement
    g.s.sendall(b'\x03')
    g._recv_packet()
    frames = []
    stats = []
    for k in range(a.n):
        if gdbtrace.wait_hit(g, RUN_EACH_FRAME) is None:
            break
        st = struct.unpack('<16I', g.read(0x006AE640, 64))
        upd = struct.unpack('<I', g.read(0x006AEFF0, 4))[0]
        stats.append((st[8], upd, st[12], st[15]))
        time.sleep(a.settle)
        img = capture(hwnd)
        if a.crop:
            x0, y0, x1, y1 = map(int, a.crop.split(','))
            img = img[y0:y1, x0:x1]
        frames.append(img)
    g.write(VPAD, struct.pack('<I', 0))
    g.send('c')
    diffs = [float(np.abs(frames[i].astype(np.int16) - frames[i - 1].astype(np.int16)).mean()) for i in range(1, len(frames))]
    distinct = sum(d > 0.05 for d in diffs)
    print('ecarts image/image :', ' '.join('%.2f' % d for d in diffs))
    print('%d images distinctes sur %d transitions' % (distinct, len(diffs)))
    if a.stats:
        for i in range(1, len(stats)):
            f, u, sw, rc = stats[i]
            f0, u0, sw0, rc0 = stats[i - 1]
            print('  image %d : update %d, changees %d, melangees %d, ecart %.2f' % (f0, u - u0, rc - rc0, sw - sw0, diffs[i - 1]))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        for i, f in enumerate(frames):
            Image.fromarray(f).save(os.path.join(a.out, '%03d.png' % i))


if __name__ == '__main__':
    main()
