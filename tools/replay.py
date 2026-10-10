"""Partie scriptee deterministe dans l'Azahar portable (horloge fixe), pour comparer
lissage actif / desactive a l'image pres (PRD : durees, RNG, position identiques).

  replay.py --ips code-test.ips --enabled 1|0 --script script.txt --snap FRAME --out snap.bin
            [--shots 400,800,...] [--timeout 600]

script.txt : une ligne par plage « image_debut boutons » (ex. « 1200 A », « 1206 - »),
             le masque s'applique jusqu'a la ligne suivante ; « - » = rien.
Instantane a l'image FRAME : etat MT19937 (0x08C55E64, 625 mots) + vue de la camera du terrain.
"""
import argparse
import os
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from azahar_gdb import Rsp  # noqa: E402

STATE = 0x006AE640
F = ['magic', 'enabled', 'jump_t', 'jump_r', 'tab_addr', 'tab_size', 'tab', 'failed', 'frame', 'interp',
     'lastrec', 'n_interp', 'n_swap', 'n_jump', 'n_miss', 'n_rec', 'vpad', 'n_skip',
     'script', 'script_pos', 'snap_frame', 'snap_a', 'snap_alen', 'snap_b', 'snap_blen', 'snap_dst', 'snap_done', 'cam', 'trace', 'trace_n', 'seen', 'anchor',
     'jump_rel', 'jump_min', 'jump_rcam', 'n_cut', 'upd', 'c3d_u', 'c3d_n', 'extra', 'n_fade']
OFF = {k: 4 * i for i, k in enumerate(F)}
BUTTONS = {'A': 1, 'B': 2, 'SELECT': 4, 'START': 8, 'RIGHT': 0x10, 'LEFT': 0x20, 'UP': 0x40, 'DOWN': 0x80,
           'R': 0x100, 'L': 0x200, 'X': 0x400, 'Y': 0x800}
MT = 0x08C55E64
MT_LEN = 625 * 4
CAMERA_VIEW = 1  # le runtime prend la derniere camera vue (+0x148)


def parse_script(path):
    pairs = []
    for line in open(path, encoding='utf-8'):
        line = line.split('#')[0].strip()
        if not line:
            continue
        f, b = line.split()[:2]
        m = 0
        if b != '-':
            for x in b.upper().split('+'):
                m |= BUTTONS[x]
        pairs.append((int(f), m))
    pairs.sort()
    return pairs


def parse_script2(path):
    """Lignes « N BOUTONS » (image absolue) et « @N BOUTONS » (relative a l'ancre)."""
    absolute, relative = [], []
    for line in open(path, encoding='utf-8'):
        line = line.split('#')[0].strip()
        if not line:
            continue
        f, b = line.split()[:2]
        m = 0
        pulse = None
        if '/' in b:                       # « A/40x6 » : A pendant 6 images toutes les 40
            b, spec = b.split('/')
            period, dur = spec.lower().split('x')
            pulse = (int(period), int(dur))
        if b != '-':
            for x in b.upper().split('+'):
                m |= BUTTONS[x]
        if pulse:
            m |= 0x80000000 | (pulse[0] << 16) | (pulse[1] << 24)
        (relative if f.startswith('@') else absolute).append((int(f.lstrip('@')), m))
    return sorted(absolute), sorted(relative)


def rd(g, k):
    return struct.unpack('<I', g.read(STATE + OFF[k], 4))[0]


def wr(g, k, v):
    g.write(STATE + OFF[k], struct.pack('<I', v))


def pause(g):
    g.s.sendall(b'\x03')
    g._recv_packet()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ips', required=True)
    ap.add_argument('--enabled', type=int, default=1)
    ap.add_argument('--script', required=True)
    ap.add_argument('--snap', type=int, required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--shots', default='')
    ap.add_argument('--timeout', type=float, default=900)
    ap.add_argument('--poll', type=float, default=5.0, help='secondes entre deux pauses GDB')
    a = ap.parse_args()
    pairs = parse_script(a.script)
    subprocess.run(['bash', os.path.join(HERE, 'sandbox.sh'), 'start', a.ips], check=True)
    g = None
    for _ in range(60):
        try:
            g = Rsp(timeout=5)
            break
        except OSError:
            time.sleep(0.5)
    g.cmd('?')
    # attendre l'initialisation du runtime (premiere decision de dessin)
    t0 = time.time()
    while True:
        if rd(g, 'magic') == 0x48544D53 and rd(g, 'tab'):
            break
        g.send('c')
        time.sleep(0.05)
        pause(g)
        if time.time() - t0 > 60:
            sys.exit('runtime non initialise')
    wr(g, 'enabled', a.enabled)
    frame0 = rd(g, 'frame')
    tab = rd(g, 'tab')
    sc = tab + 0x36000
    flat = b''.join(struct.pack('<II', f, m) for f, m in pairs) + struct.pack('<II', 0xFFFFFFFF, 0)
    if pairs and pairs[0][0] <= frame0:
        sys.exit('script trop tot : image courante %d' % frame0)
    g.write(sc, flat)
    wr(g, 'script_pos', 0)
    g.write(STATE + OFF['script'], struct.pack('<I', sc))
    for k, v in (('snap_a', MT), ('snap_alen', MT_LEN), ('snap_b', CAMERA_VIEW), ('snap_blen', 0x30),
                 ('snap_dst', tab + 0x38000), ('snap_done', 0), ('snap_frame', a.snap),
                 ('trace', tab + 0x39000), ('trace_n', min(a.snap + 1, 3000))):
        wr(g, k, v)
    print('runtime pret a l\'image %d (lissage %s), %d entrees de script' % (frame0, 'actif' if a.enabled else 'desactive', len(pairs)))
    shots = sorted(int(x) for x in a.shots.split(',') if x)
    t0 = time.time()
    while True:
        g.send('c')
        time.sleep(a.poll)
        pause(g)
        fr = rd(g, 'frame')
        while shots and fr >= shots[0]:
            s = shots.pop(0)
            g.send('c')
            subprocess.run(['bash', os.path.join(HERE, 'shot.sh'), '%s-f%d' % (os.path.splitext(a.out)[0], fr)],
                           capture_output=True)
            pause(g)
        if rd(g, 'snap_done'):
            break
        if time.time() - t0 > a.timeout:
            sys.exit('instantane non atteint (image %d)' % fr)
    snap = g.read(tab + 0x38000, MT_LEN + 0x30)
    open(a.out, 'wb').write(snap)
    n = min(a.snap + 1, 3000)
    open(os.path.splitext(a.out)[0] + '.trace', 'wb').write(g.read(tab + 0x39000, 8 * n))
    st = {k: rd(g, k) for k in ('frame', 'n_interp', 'n_swap', 'n_jump', 'n_skip')}
    g.send('c')
    idx = struct.unpack_from('<I', snap, 0)[0]
    view = struct.unpack_from('<12f', snap, MT_LEN)
    print('instantane image %d : MT index %d, camera t=(%.2f, %.2f, %.2f) ; %s' % (
        a.snap, idx, view[3], view[7], view[11], ' '.join('%s=%d' % kv for kv in st.items())))


if __name__ == '__main__':
    main()
