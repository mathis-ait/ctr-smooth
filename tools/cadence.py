"""Cadence sans pause GDB sur une meme fenetre : temps emule (GetSystemTick du jeu),
ticks logiques, dessins, images presentees (builds --probe : S.n_flip) et sauts.
Ramene a la seconde emulee (ce que verrait une console) et a la seconde reelle.
  cadence.py [secs]"""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp
S = 0x006AE640
TICKS = 268111856.0
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
g = Rsp(timeout=5); g.cmd('?')
tm, = struct.unpack('<I', g.read(0x08C650B4 + 0x20, 4))
def rd():
    t, = struct.unpack('<Q', g.read(tm + 8, 8))
    c = struct.unpack('<3I', g.read(0x006AEFF0, 12))
    flip, _, dup, _, flip2, _, dup2 = struct.unpack('<7I', g.read(S + 0x1BC, 28))
    skip, = struct.unpack('<I', g.read(S + 0x44, 4))
    en, = struct.unpack('<I', g.read(S + 4, 4))
    return t, c, flip, skip, en, dup, flip2, dup2
a = rd(); w = time.time(); g.send('c'); time.sleep(secs); g.s.sendall(b'\x03'); g._recv_packet(); dt = time.time() - w; b = rd(); g.send('c')
emu = (b[0] - a[0]) / TICKS
up, dr, fl, sk = b[1][0] - a[1][0], b[1][2] - a[1][2], b[2] - a[2], b[3] - a[3]
print('  images identiques a la precedente : haut %d sur %d ; bas %d sur %d (bas : %.1f images/s reelle)' % (
    b[5] - a[5], fl, b[7] - a[7], b[6] - a[6], (b[6] - a[6]) / dt))
print('lissage %s : vitesse %3.0f %% | par seconde emulee : %4.1f ticks, %4.1f dessins, %4.1f images affichees, %3.1f sauts | par seconde reelle : %4.1f ticks, %4.1f images' % (
    'actif' if a[4] else 'coupe', 100 * emu / dt, up / emu, dr / emu, fl / emu, sk / emu, up / dt, fl / dt))
