"""Traces ponctuelles via le stub GDB d'Azahar (un point d'arret a la fois, pose a
l'ENTREE d'une fonction : c'est le seul cas fiable avec le JIT d'Azahar).

  gdbtrace.py hits ADDR [-n 8] [--mem REG:OFF:LEN ...]
      N arrets successifs : r0-r3, lr, pile d'appels heuristique (mots de pile
      pointant juste apres un BL/BLX dans .text), dumps memoire optionnels
      (ex. --mem r0:0:0x40 lit 0x40 octets a r0+0).
  gdbtrace.py rate ADDR... [--secs 2]    appels par seconde de chaque fonction
  gdbtrace.py dump ADDR LEN FICHIER      lit une zone memoire vers un fichier
"""
import argparse
import os
import socket
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from azahar_gdb import Rsp  # noqa: E402

TEXT = (0x00100000, 0x00579604)
CODE = None


def load_code():
    global CODE
    p = os.environ.get('ROSA_CODE', r'C:\Users\Thisma\Documents\Switch\tools-re\rosa-or\code.bin')
    if os.path.exists(p):
        CODE = open(p, 'rb').read()


def is_return_addr(a):
    if not (TEXT[0] + 4 <= a < TEXT[1]) or a & 3 or CODE is None:
        return False
    w = struct.unpack_from('<I', CODE, a - 4 - TEXT[0])[0]
    return (w & 0x0F000000) == 0x0B000000 or (w & 0x0FFFFFF0) == 0x012FFF30  # BL / BLX reg


def stop_regs(g):
    r = g.cmd('g')
    return [struct.unpack('<I', bytes.fromhex(r[i:i + 8]))[0] for i in range(0, 16 * 8, 8)]


def _cont(g, timeout):
    g.s.settimeout(timeout)
    try:
        return g.cont()
    except socket.timeout:
        g.s.sendall(b'\x03')
        g.s.settimeout(3)
        g._recv_packet()
        return None


def wait_hit(g, addr, timeout=5.0, state={}):
    """Prochain appel de la fonction `addr`. Le stub d'Azahar ne sait pas faire de pas
    a pas (« s » -> E5F) et re-declenche le meme point d'arret a la reprise : on
    enjambe l'appel precedent en posant un point d'arret sur son adresse de retour."""
    lr = state.pop(addr, None)
    if lr is not None:
        g.set_bp(lr)
        hit = _cont(g, timeout)
        g.clear_bp(lr)
        if hit is None:
            return None
    g.set_bp(addr)
    hit = _cont(g, timeout)
    g.clear_bp(addr)
    if hit is not None:
        state[addr] = stop_regs(g)[14]
    return hit


def backtrace(g, sp, depth=0x200):
    try:
        st = g.read(sp, depth)
    except RuntimeError:
        return []
    out = []
    for i in range(0, len(st), 4):
        v = struct.unpack_from('<I', st, i)[0]
        if is_return_addr(v):
            out.append((sp + i, v))
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    h = sub.add_parser('hits')
    h.add_argument('addr')
    h.add_argument('-n', type=int, default=8)
    h.add_argument('--mem', action='append', default=[])
    h.add_argument('--bt', type=lambda s: int(s, 0), default=0x180)
    r = sub.add_parser('rate')
    r.add_argument('addrs', nargs='+')
    r.add_argument('--secs', type=float, default=2.0)
    d = sub.add_parser('dump')
    d.add_argument('addr')
    d.add_argument('len')
    d.add_argument('out')
    a = ap.parse_args()
    load_code()
    g = Rsp(timeout=5)
    g.cmd('?')
    if a.cmd == 'hits':
        addr = int(a.addr, 16)
        for k in range(a.n):
            if wait_hit(g, addr) is None:
                print('  (pas d\'appel en 5 s)')
                break
            regs = stop_regs(g)
            print('#%d pc=%08x r0=%08x r1=%08x r2=%08x r3=%08x lr=%08x sp=%08x' % (
                k, regs[15], regs[0], regs[1], regs[2], regs[3], regs[14], regs[13]))
            if a.bt:
                bt = backtrace(g, regs[13], a.bt)
                print('    pile : ' + ' '.join('%08x' % v for _, v in bt[:14]))
            for spec in a.mem:
                reg, off, ln = spec.split(':')
                base = regs[int(reg[1:])] + int(off, 0)
                try:
                    data = g.read(base, int(ln, 0))
                    for i in range(0, len(data), 16):
                        row = data[i:i + 16]
                        fl = ' '.join('%9.3f' % f for f in struct.unpack('<%df' % (len(row) // 4), row[:len(row) // 4 * 4]))
                        print('    %08x  %-47s  %s' % (base + i, row.hex(' '), fl))
                except RuntimeError as e:
                    print('    lecture impossible', e)
        g.send('c')
    elif a.cmd == 'rate':
        for s in a.addrs:
            addr = int(s, 16)
            n, t0 = 0, time.time()
            while time.time() - t0 < a.secs:
                if wait_hit(g, addr, timeout=a.secs) is None:
                    break
                n += 1
            dt = time.time() - t0
            print('  %08x : %7.1f appels/s (borne basse : 2 allers-retours GDB par appel)' % (addr, n / dt))
        g.send('c')
    elif a.cmd == 'dump':
        base, ln = int(a.addr, 16), int(a.len, 0)
        t0 = time.time()
        data = g.read(base, ln)
        open(a.out, 'wb').write(data)
        g.send('c')
        print('%d octets en %.1f s' % (len(data), time.time() - t0))


if __name__ == '__main__':
    main()
