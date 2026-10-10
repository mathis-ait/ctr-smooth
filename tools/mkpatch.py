"""Fabrique un `code.ips` a partir de correctifs « adresse=octets », en fusionnant
les enregistrements d'un IPS existant (par ex. le taux de shiny ecrit par Kaleido).

Usage :
  mkpatch.py [--base 0x100000] [--merge ancien.ips] -o code.ips 0x10E53C=00f020e3 ...
  mkpatch.py --dump code.ips

Les adresses sont des adresses memoire ARM ; l'IPS stocke des positions dans
code.bin (decompresse). Azahar et Luma appliquent l'IPS sur le code decompresse.
"""
import argparse


def read_ips(path):
    d = open(path, 'rb').read()
    if d[:5] != b'PATCH':
        raise SystemExit('%s : pas un IPS' % path)
    i, recs = 5, []
    while d[i:i + 3] != b'EOF':
        off = int.from_bytes(d[i:i + 3], 'big')
        size = int.from_bytes(d[i + 3:i + 5], 'big')
        i += 5
        if size == 0:  # enregistrement RLE
            n = int.from_bytes(d[i:i + 2], 'big')
            recs.append((off, bytes([d[i + 2]]) * n))
            i += 3
        else:
            recs.append((off, d[i:i + size]))
            i += size
    return recs


def write_ips(path, recs):
    out = bytearray(b'PATCH')
    for off, data in sorted(recs):
        if off >= 1 << 24 or len(data) >= 1 << 16:
            raise SystemExit('enregistrement trop grand')
        out += off.to_bytes(3, 'big') + len(data).to_bytes(2, 'big') + data
    out += b'EOF'
    open(path, 'wb').write(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', type=lambda s: int(s, 0), default=0x100000)
    ap.add_argument('--merge', action='append', default=[])
    ap.add_argument('--dump')
    ap.add_argument('-o')
    ap.add_argument('patches', nargs='*')
    a = ap.parse_args()
    if a.dump:
        for off, data in read_ips(a.dump):
            print('  code.bin+%06x (0x%08x) : %s' % (off, off + a.base, data.hex()))
        return
    recs = []
    for m in a.merge:
        recs += read_ips(m)
    for p in a.patches:
        addr, hx = p.split('=')
        recs.append((int(addr, 0) - a.base, bytes.fromhex(hx)))
    write_ips(a.o, recs)
    for off, data in sorted(recs):
        print('  code.bin+%06x (0x%08x) <- %s' % (off, off + a.base, data.hex()))


if __name__ == '__main__':
    main()
