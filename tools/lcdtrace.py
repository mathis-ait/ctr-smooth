"""Ecran du haut image par image (bac a sable) : a chaque VBlank, index du tampon
affiche dans la memoire partagee GSP (0x10002200) et empreinte des deux tampons LCD
en VRAM. Montre si chaque dessin ecrit une image neuve et si l'ecran bascule.
  lcdtrace.py [-n 16]"""
import argparse, hashlib, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp  # noqa: E402
import gdbtrace  # noqa: E402
from framecap import RUN_EACH_FRAME  # noqa: E402
STATE = 0x006AE640
GSP_TOP = 0x10002200


def h(g, addr):
    d = b''.join(g.read(addr + o, 0x1000) for o in range(0x10000, 0x30000, 0x8000))
    return hashlib.md5(d).hexdigest()[:6]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('-n', type=int, default=16); a = ap.parse_args()
    gdbtrace.load_code()
    g = Rsp(timeout=5); g.cmd('?')
    hdr = g.read(GSP_TOP, 0x40)
    fb = [struct.unpack_from('<I', hdr, 4 + 0x1c * i + 4)[0] for i in range(2)]
    print('tampons haut : %08x %08x' % tuple(fb))
    for k in range(a.n):
        if gdbtrace.wait_hit(g, RUN_EACH_FRAME) is None:
            break
        hdr = g.read(GSP_TOP, 4)
        f, = struct.unpack('<I', g.read(STATE + 0x20, 4)); up, = struct.unpack('<I', g.read(STATE + 0x90, 4))
        c = struct.unpack('<3I', g.read(0x006AEFF0, 12))
        print('frame %d upd %d draws %d  index %d upd_flag %d   A %s  B %s' % (f, up, c[2], hdr[0], hdr[1], h(g, fb[0]), h(g, fb[1])))
    g.send('c')


if __name__ == '__main__':
    main()
