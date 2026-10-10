"""Partie scriptee sans aucune pause GDB : le script, l'image d'instantane et
l'etat actif/desactive sont compiles dans l'IPS (build.py --script). On lance le
jeu, on attend, puis on lit une seule fois l'instantane et la trace.

  replay_static.py --ips code-script-on.ips --out t.bin [--wait 70] [--snap 1700]
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
from replay import STATE, OFF, MT_LEN, rd  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ips', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--wait', type=float, default=70)
    ap.add_argument('--snap', type=int, default=800, help='image relative a l ancre')
    a = ap.parse_args()
    for attempt in range(3):
        subprocess.run(['bash', os.path.join(HERE, 'sandbox.sh'), 'start', a.ips], check=True, capture_output=True)
        time.sleep(a.wait)
        try:
            g = Rsp(timeout=5)
            break
        except OSError:
            print('stub GDB injoignable, nouveau lancement')
    else:
        sys.exit('stub GDB injoignable')
    g.cmd('?')
    for _ in range(30):
        if rd(g, 'magic') == 0x48544D53 and rd(g, 'snap_done'):
            break
        g.send('c')
        time.sleep(5)
        g.s.sendall(b'\x03')
        g._recv_packet()
    else:
        sys.exit('instantane non atteint (image %d)' % rd(g, 'frame'))
    tab = rd(g, 'tab')
    snap = g.read(tab + 0x40000, MT_LEN + 0x30)
    open(a.out, 'wb').write(snap)
    open(os.path.splitext(a.out)[0] + '.trace', 'wb').write(g.read(tab + 0x41000, 8 * (a.snap + 1)))
    open(os.path.splitext(a.out)[0] + '.anchor', 'w').write(str(rd(g, 'anchor')))
    st = {k: rd(g, k) for k in ('enabled', 'anchor', 'frame', 'n_interp', 'n_swap', 'n_jump', 'n_cut', 'n_skip', 'n_fade')}
    g.send('c')
    view = struct.unpack_from('<12f', snap, MT_LEN)
    print('instantane ancre+%d : MT index %d, camera t=(%.2f, %.2f, %.2f) ; %s' % (
        a.snap, struct.unpack_from('<I', snap, 0)[0], view[3], view[7], view[11],
        ' '.join('%s=%d' % kv for kv in st.items())))


if __name__ == '__main__':
    main()
