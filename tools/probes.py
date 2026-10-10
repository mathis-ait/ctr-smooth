"""Lit les sondes des builds --probe (State.pc) : appels par seconde, images d'update / sans.
  probes.py [secs] [nom0 nom1 ...]"""
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp
S = 0x006AE640
PC = S + 0x178
secs = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
names = sys.argv[2:]
g = Rsp(timeout=5); g.cmd('?')
rd = lambda: (struct.unpack('<18I', g.read(PC, 72)), struct.unpack('<3I', g.read(0x006AEFF0, 12)), struct.unpack('<I', g.read(S + 4, 4))[0])
a, ca, en = rd(); g.send('c'); t = time.time(); time.sleep(secs); g.s.sendall(b'\x03'); g._recv_packet(); dt = time.time() - t
b, cb, _ = rd(); g.send('c')
print('lissage %s ; updates %.1f/s, dessins %.1f/s, images presentees (ecran du haut) %.1f/s' % (
    'actif' if en else 'coupe', (cb[0] - ca[0]) / dt, (cb[2] - ca[2]) / dt, (b[17] - a[17]) / dt))
for i in range(8):
    u, n = (b[2 * i] - a[2 * i]) / dt, (b[2 * i + 1] - a[2 * i + 1]) / dt
    if u or n or i < len(names):
        print('  %-14s image d update %6.1f/s   sans update %6.1f/s' % (names[i] if i < len(names) else 'sonde %d' % i, u, n))
