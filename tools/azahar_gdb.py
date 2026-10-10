"""Client GDB (Remote Serial Protocol) minimal pour le stub GDB d'Azahar.

Usage :
  azahar_gdb.py count [--secs 5] ADDR[=nom] ...   compte les passages par adresse
  azahar_gdb.py read  ADDR LEN                     lit la memoire (hex)
  azahar_gdb.py write ADDR HEXBYTES                ecrit en memoire
  azahar_gdb.py regs                               registres a l'arret courant

Azahar doit tourner avec « use_gdbstub=true » (section [Debugging] de
qt-config.ini) ; il attend la connexion au demarrage du jeu. Port : 24689.
"""
import argparse
import socket
import struct
import time


class Rsp:
    def __init__(self, host='127.0.0.1', port=24689, timeout=3.0):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.s.settimeout(timeout)
        self.buf = b''
        self.noack = False
        if self.cmd('QStartNoAckMode') == 'OK':
            self.noack = True

    def _recv_packet(self):
        while True:
            i = self.buf.find(b'$')
            if i >= 0:
                j = self.buf.find(b'#', i)
                if j >= 0 and len(self.buf) >= j + 3:
                    pkt = self.buf[i + 1:j]
                    self.buf = self.buf[j + 3:]
                    if not self.noack:
                        self.s.sendall(b'+')
                    return pkt.decode('latin1')
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError('stub ferme')
            self.buf += chunk

    def send(self, payload):
        data = payload.encode('latin1')
        self.s.sendall(b'$' + data + b'#' + b'%02x' % (sum(data) & 0xFF))

    def cmd(self, payload):
        self.send(payload)
        if not self.noack:
            while b'+' not in self.buf and b'-' not in self.buf:
                self.buf += self.s.recv(65536)
            k = self.buf.find(b'+')
            self.buf = self.buf[k + 1:]
        return self._recv_packet()

    def read(self, addr, n):
        out = b''
        while n:
            k = min(n, 0x1000)
            r = self.cmd('m%x,%x' % (addr, k))
            if r.startswith('E') or not r:
                raise RuntimeError('lecture %#x : %r' % (addr, r))
            out += bytes.fromhex(r)
            addr += k
            n -= k
        return out

    def write(self, addr, data):
        r = self.cmd('M%x,%x:%s' % (addr, len(data), data.hex()))
        if r != 'OK':
            raise RuntimeError('ecriture %#x : %r' % (addr, r))

    def regs(self):
        r = self.cmd('g')
        return [struct.unpack('<I', bytes.fromhex(r[i:i + 8]))[0] for i in range(0, min(len(r), 16 * 8), 8)]

    def set_bp(self, addr, kind=4):
        r = self.cmd('Z0,%x,%d' % (addr, kind))
        if r != 'OK':
            raise RuntimeError("point d'arret %#x : %r" % (addr, r))

    def clear_bp(self, addr, kind=4):
        self.cmd('z0,%x,%d' % (addr, kind))

    def cont(self):
        """Continue et attend le prochain arret ; renvoie le paquet T05."""
        self.send('c')
        return self._recv_packet()

    @staticmethod
    def stop_pc(stop):
        for part in stop[3:].split(';'):
            if ':' in part:
                k, v = part.split(':', 1)
                if k.lower() in ('0f', 'pc', '15') and len(v) >= 8:
                    try:
                        return struct.unpack('<I', bytes.fromhex(v[:8]))[0]
                    except ValueError:
                        return None
        return None


def parse_addr(s):
    name = None
    if '=' in s:
        s, name = s.split('=', 1)
    a = int(s, 16)
    return a, name or ('%#x' % a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=24689)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('count')
    c.add_argument('--secs', type=float, default=5.0)
    c.add_argument('addrs', nargs='+')
    r = sub.add_parser('read')
    r.add_argument('addr')
    r.add_argument('len')
    w = sub.add_parser('write')
    w.add_argument('addr')
    w.add_argument('hex')
    sub.add_parser('regs')
    wt = sub.add_parser('watch')
    wt.add_argument('--secs', type=float, default=5.0)
    wt.add_argument('addr')
    wt.add_argument('words', type=int)
    a = ap.parse_args()

    g = Rsp(port=a.port)
    print('connecte ; etat :', g.cmd('?'))
    if a.cmd == 'read':
        base = int(a.addr, 16)
        d = g.read(base, int(a.len, 0))
        for i in range(0, len(d), 16):
            print('%08x  %s' % (base + i, d[i:i + 16].hex(' ')))
        g.send('c')
    elif a.cmd == 'write':
        g.write(int(a.addr, 16), bytes.fromhex(a.hex))
        print('OK')
        g.send('c')
    elif a.cmd == 'regs':
        for i, v in enumerate(g.regs()):
            print('r%-2d = %08x' % (i, v))
        g.send('c')
    elif a.cmd == 'watch':
        base = int(a.addr, 16)
        before = struct.unpack('<%dI' % a.words, g.read(base, 4 * a.words))
        g.send('c')
        t0 = time.time()
        time.sleep(a.secs)
        g.s.sendall(b'')
        g._recv_packet()
        dt = time.time() - t0
        after = struct.unpack('<%dI' % a.words, g.read(base, 4 * a.words))
        for i, (x, y) in enumerate(zip(before, after)):
            print('  %08x : %10u -> %10u  delta %6u = %6.1f/s' % (base + 4 * i, x, y, y - x, (y - x) / dt))
        g.send('c')
    elif a.cmd == 'count':
        # Le stub d'Azahar n'honore qu'un point d'arret a la fois : on mesure chaque
        # adresse l'une apres l'autre. Un silence du stub est rattrape par une
        # interruption (0x03) puis reprise.
        for s in a.addrs:
            addr, name = parse_addr(s)
            g.set_bp(addr)
            n = 0
            lost = 0
            t0 = time.time()
            while time.time() - t0 < a.secs:
                try:
                    g.cont()
                    n += 1
                except socket.timeout:
                    lost += 1
                    g.s.sendall(b'')
                    try:
                        g._recv_packet()
                    except socket.timeout:
                        print('  stub muet : abandon')
                        break
            dt = time.time() - t0
            g.clear_bp(addr)
            print('  %-14s %#010x : %5d passages en %.1f s = %6.1f/s%s' % (name, addr, n, dt, n / dt, ('  (%d reprises)' % lost) if lost else ''))
        g.send('c')

if __name__ == '__main__':
    main()
