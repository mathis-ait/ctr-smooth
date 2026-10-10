"""Pour chaque image, la fonction ADDR est-elle appelee ? (fiable avec le stub d'Azahar)
Point d'arret sur ADDR ; a l'arret, on note l'image puis on saute au debut de l'image
suivante (runEachFrame) avant de reposer le point d'arret.
  perframe.py ADDR [-n 16]"""
import argparse, os, socket, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp
FRAME = 0x0010E354
ap = argparse.ArgumentParser(); ap.add_argument('addr'); ap.add_argument('-n', type=int, default=16)
a = ap.parse_args(); addr = int(a.addr, 16)
g = Rsp(timeout=5); g.cmd('?')
def cont(bp):
    g.set_bp(bp); g.s.settimeout(3)
    try:
        g.cont(); ok = True
    except socket.timeout:
        g.s.sendall(b'\x03'); g._recv_packet(); ok = False
    g.clear_bp(bp); return ok
frames = []
# on part d'un debut d'image
cont(FRAME)
for k in range(a.n):
    f0 = struct.unpack('<I', g.read(0x006AE640 + 0x20, 4))[0]   # valeur avant la decision de cette image
    if not cont(addr):
        frames.append((f0 + 1, None)); cont(FRAME); continue
    fr, interp = struct.unpack('<II', g.read(0x006AE640 + 0x20, 8))
    frames.append((fr, interp))
    cont(FRAME)
g.send('c')
print(' '.join('%d%s' % (f, '' if i is None else ('*' if i else '')) if i is not None else '%d:-' % f for f, i in frames))
print('(* = image interpolee ; :- = pas d appel)')
