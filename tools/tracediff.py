"""Compare des traces par image de replay.py (index MT19937, translation x de la vue).
  tracediff.py a.trace b.trace [c.trace ...]
Pour chaque paire (a, x) : premiere image divergente, et decalage d'images qui rend
les traces identiques sur la phase de jeu (si la divergence vient du temps de chargement).
"""
import struct
import sys


def load(p):
    d = open(p, 'rb').read()
    return [struct.unpack_from('<IIf', d + b'\0' * 4, 8 * i)[:1] + struct.unpack_from('<f', d, 8 * i + 4) for i in range(len(d) // 8)]


def first_diff(a, b, start=0):
    for i in range(start, min(len(a), len(b))):
        if a[i] != b[i]:
            return i
    return None


def best_shift(a, b, lo=1000, hi=None, maxs=30):
    hi = hi or min(len(a), len(b)) - maxs
    best = None
    for s in range(-maxs, maxs + 1):
        bad = sum(1 for i in range(lo, hi) if 0 <= i + s < len(b) and a[i] != b[i + s])
        if best is None or bad < best[1]:
            best = (s, bad)
    return best


def main():
    ref = load(sys.argv[1])
    name = sys.argv[1].split('/')[-1]
    for p in sys.argv[2:]:
        t = load(p)
        fd = first_diff(ref, t)
        s, bad = best_shift(ref, t)
        if fd is None:
            print('%s vs %s : identiques sur %d images' % (name, p.split('/')[-1], min(len(ref), len(t))))
        else:
            print('%s vs %s : 1re divergence image %d (ref %s / %s) ; meilleur decalage %+d -> %d images differentes sur 1000..fin' % (
                name, p.split('/')[-1], fd, ref[fd], t[fd], s, bad))


if __name__ == '__main__':
    main()
