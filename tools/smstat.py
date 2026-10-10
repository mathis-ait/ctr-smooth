"""Lit l'etat du runtime ctr-smooth (structure State a 0x006AE640) via le stub GDB.
  smstat.py            affiche l'etat
  smstat.py set enabled 0|1   active / desactive a chaud
  smstat.py watch 3    deltas sur 3 s (+ compteurs de trace 0x006AEFF0 si presents)
  smstat.py press "A 150" "wait 2000" "LEFT 800" ...   (builds --test-input) appuis injectes"""
BUTTONS = {'A': 1, 'B': 2, 'SELECT': 4, 'START': 8, 'RIGHT': 0x10, 'LEFT': 0x20, 'UP': 0x40, 'DOWN': 0x80,
           'R': 0x100, 'L': 0x200, 'X': 0x400, 'Y': 0x800}
import os, struct, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp
ADDR = 0x006AE640
F = ['magic', 'enabled', 'jump_t', 'jump_r', 'tab_addr', 'tab_size', 'tab', 'failed', 'frame', 'interp',
     'lastrec', 'n_interp', 'n_swap', 'n_jump', 'n_miss', 'n_rec', 'vpad', 'n_skip', 'script', 'script_pos', 'snap_frame', 'snap_a', 'snap_alen', 'snap_b', 'snap_blen',
     'snap_dst', 'snap_done', 'cam', 'trace', 'trace_n', 'seen', 'anchor', 'jump_rel', 'jump_min', 'jump_rcam', 'n_cut', 'upd', 'c3d_u', 'c3d_n', 'extra', 'n_fade',
     'eye0', 'eye1', 'eye2', 'eye3', 'eyef0', 'eyef1', 'eyef2', 'eyef3', 'n_eye',
     'pad', 'combo_f', 'tstate0', 'tstate1', 'n_tskip', 'cam_u', 'cam_n', 'h3d_u', 'h3d_n', 'nw_u', 'nw_n']
# champs suivants (après tlog, pc, lcd) : adresses fixes calculées par offset_of() plus bas
FLOATS = {'jump_t', 'jump_r', 'jump_rel', 'jump_min', 'jump_rcam'}
def read(g):
    raw = g.read(ADDR, 4 * len(F))
    vals = {}
    for i, k in enumerate(F):
        vals[k] = struct.unpack_from('<f' if k in FLOATS else '<I', raw, 4 * i)[0]
    return vals
TEST = {'script', 'script_pos', 'snap_frame', 'snap_a', 'snap_alen', 'snap_b', 'snap_blen', 'snap_dst',
        'snap_done', 'trace', 'trace_n', 'seen', 'tab_addr', 'tab_size', 'lastrec', 'interp',
        'eye0', 'eye1', 'eye2', 'eye3', 'eyef0', 'eyef1', 'eyef2', 'eyef3', 'combo_f'}
def show(v):
    return '  '.join(('%s=%.2f' % (k, v[k])) if k in FLOATS else ('%s=%#x' % (k, v[k]) if k in ('magic', 'tab', 'tab_addr', 'tab_size', 'vpad') else '%s=%d' % (k, v[k])) for k in F if k not in TEST)
g = Rsp(timeout=5); g.cmd('?')
if len(sys.argv) > 1 and sys.argv[1] == 'set':
    k, val = sys.argv[2], sys.argv[3]
    i = F.index(k)
    g.write(ADDR + 4 * i, struct.pack('<f' if k in FLOATS else '<I', float(val) if k in FLOATS else int(val, 0)))
    print(show(read(g)))
elif len(sys.argv) > 1 and sys.argv[1] == 'press':
    VP = ADDR + 4 * F.index('vpad')
    for step in sys.argv[2:]:
        p = step.split()
        if p[0].upper() == 'WAIT':
            mask, ms = 0, int(p[1])
        else:
            mask = 0
            for b in p[0].upper().split('+'):
                mask |= BUTTONS[b]
            ms = int(p[1]) if len(p) > 1 else 150
        g.write(VP, struct.pack('<I', mask))
        g.send('c'); time.sleep(ms / 1000); g.s.sendall(b''); g._recv_packet()
    g.write(VP, struct.pack('<I', 0))
    print('ok')
elif len(sys.argv) > 1 and sys.argv[1] in ('stick', 'touch'):
    # stick X Y [ms] (valeurs signees, environ +-150) ; touch X Y [ms] (ecran du bas 320 x 240) ; ms absent = laisse en place, « off » = relache
    from stateoff import off
    k = 'vstick' if sys.argv[1] == 'stick' else 'vtouch'
    if sys.argv[2] == 'off':
        val = 0
    else:
        x, y = int(sys.argv[2]), int(sys.argv[3])
        val = (x & 0xFFFF) | (y & 0xFFFF) << 16 if k == 'vstick' else x | y << 16 | 0x80000000
    g.write(ADDR + off(k), struct.pack('<I', val))
    if len(sys.argv) > 4:
        g.send('c'); time.sleep(int(sys.argv[4]) / 1000); g.s.sendall(b''); g._recv_packet()
        g.write(ADDR + off(k), struct.pack('<I', 0))
    print('ok')
elif len(sys.argv) > 1 and sys.argv[1] == 'watch':
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
    a = read(g); c0 = struct.unpack('<3I', g.read(0x006AEFF0, 12))
    g.send('c'); t = time.time(); time.sleep(secs); g.s.sendall(b'\x03'); g._recv_packet(); dt = time.time() - t
    b = read(g); c1 = struct.unpack('<3I', g.read(0x006AEFF0, 12))
    print(show(b))
    for k in ('frame', 'n_interp', 'n_swap', 'n_jump', 'n_cut', 'n_miss', 'n_rec', 'n_skip', 'c3d_u', 'c3d_n', 'n_fade', 'n_eye', 'n_tskip', 'cam_u', 'cam_n', 'h3d_u', 'h3d_n', 'nw_u', 'nw_n'):
        print('  %-9s %8.1f/s' % (k, (b[k] - a[k]) / dt))
    for name, x, y in zip(('update', 'sans update', 'draw'), c0, c1):
        print('  %-11s %6.1f/s' % (name, (y - x) / dt))
else:
    print(show(read(g)))
    r = g.cmd('g'); pc = struct.unpack('<I', bytes.fromhex(r[15*8:16*8]))[0]; print('pc=%08x' % pc)
g.send('c')
