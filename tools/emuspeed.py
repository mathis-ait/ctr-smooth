"""Vitesse d'emulation reelle : ticks systeme 3DS emules (268 111 856 Hz) ecoules par
seconde reelle, lus dans l'objet de mesure de temps de la boucle (gestionnaire+0x20,
dernier GetSystemTick en +0x08), plus les compteurs du runtime.
  emuspeed.py [--secs 4] [--mgr 0x08C650B4]"""
import argparse, os, struct, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp
TICKS = 268111856.0
ap = argparse.ArgumentParser(); ap.add_argument('--secs', type=float, default=4.0); ap.add_argument('--mgr', type=lambda s: int(s, 0), default=0x08C650B4)
a = ap.parse_args()
g = Rsp(timeout=5); g.cmd('?')
tm = struct.unpack('<I', g.read(a.mgr + 0x20, 4))[0]
def sample():
    t = struct.unpack('<Q', g.read(tm + 8, 8))[0]
    fr = struct.unpack('<I', g.read(0x006AE640 + 0x20, 4))[0]
    return t, fr
t0, f0 = sample(); w0 = time.time()
g.send('c'); time.sleep(a.secs); g.s.sendall(b'\x03'); g._recv_packet()
t1, f1 = sample(); dt = time.time() - w0
emu = (t1 - t0) / TICKS
print('temps emule %.2f s pour %.2f s reelles : vitesse %.0f %% ; %.1f images par seconde emulee, %.1f par seconde reelle' % (
    emu, dt, 100 * emu / dt, (f1 - f0) / emu if emu else 0, (f1 - f0) / dt))
g.send('c')
