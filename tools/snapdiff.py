"""Compare des instantanes de replay.py (etat MT19937 + vue camera) octet a octet.
  snapdiff.py reference.bin autre.bin [autre2.bin ...]
"""
import struct
import sys

MT_LEN = 625 * 4


def describe(d):
    idx = struct.unpack_from('<I', d, 0)[0]
    v = struct.unpack_from('<12f', d, MT_LEN)
    return 'MT index %3d, camera t=(%.3f, %.3f, %.3f)' % (idx, v[3], v[7], v[11])


def main():
    ref = open(sys.argv[1], 'rb').read()
    print('%-28s %s' % (sys.argv[1].split('/')[-1], describe(ref)))
    ok = True
    for p in sys.argv[2:]:
        d = open(p, 'rb').read()
        diff = [i for i in range(min(len(ref), len(d))) if ref[i] != d[i]]
        mt = sum(1 for i in diff if i < MT_LEN)
        cam = sum(1 for i in diff if i >= MT_LEN)
        same = not diff and len(ref) == len(d)
        ok &= same
        print('%-28s %s  -> %s' % (p.split('/')[-1], describe(d),
                                   'IDENTIQUE' if same else 'DIFFERENT (%d octets MT, %d octets camera)' % (mt, cam)))
    print('RESULTAT :', 'identiques octet pour octet' if ok else 'divergence')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
