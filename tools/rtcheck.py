"""Pour chaque image : la zone de rendu VRAM a-t-elle change depuis l'image
precedente ? Lit un echantillon du tampon de couleur a chaque entree de
runEachFrame (pas a pas fiable), lissage actif et desactive.
  rtcheck.py [--addr 0x1F0A0000] [--len 0x8000] [-n 14]"""
import argparse, os, struct, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp
import gdbtrace
ap = argparse.ArgumentParser()
ap.add_argument('--addr', type=lambda s: int(s, 0), default=0x1F0A0000)
ap.add_argument('--len', type=lambda s: int(s, 0), default=0x8000)
ap.add_argument('-n', type=int, default=14)
a = ap.parse_args()
gdbtrace.load_code()
g = Rsp(timeout=5); g.cmd('?')
for en in (0, 1):
    g.write(0x006AE644, struct.pack('<I', en))
    rows = []; prev = None
    for k in range(a.n):
        if gdbtrace.wait_hit(g, 0x10E354) is None: break
        fr, = struct.unpack('<I', g.read(0x006AE660, 4))
        upd = struct.unpack('<I', g.read(0x006AE640 + 0x90, 4))[0]
        cur = np.frombuffer(g.read(a.addr, a.len), dtype=np.uint8).astype(np.int16)
        d = float(np.abs(cur - prev).mean()) if prev is not None else 0.0
        rows.append('%d%s:%.2f' % (fr, 'u' if upd else '', d)); prev = cur
    changes = sum(1 for r in rows[1:] if float(r.split(':')[1]) > 0.05)
    print('lissage %d : %d changements sur %d images | %s' % (en, changes, len(rows) - 1, ' '.join(rows[1:])))
g.send('c')
