"""Relocalise des adresses d'un code.bin vers un autre (même jeu, autre version) par
signatures d'octets : pour chaque adresse, on cherche dans la cible la fenêtre d'octets
qui l'entoure (les branchements relatifs restent identiques tant que l'appelant et la
cible bougent ensemble). Affiche aussi la carte des décalages sur tout .text.

  reloc.py source.bin cible.bin [ADDR ...]
"""
import sys

BASE = 0x00100000


def find_all(hay, needle, limit=4):
    out, i = [], hay.find(needle)
    while i >= 0 and len(out) < limit:
        out.append(i)
        i = hay.find(needle, i + 4)
    return out


def locate(src, dst, addr, windows=(32, 48, 64, 96, 128)):
    off = addr - BASE
    for w in windows:
        for lead in (0, w // 2, w):
            a = max(0, off - lead)
            needle = src[a:a + w]
            hits = find_all(dst, needle)
            if len(hits) == 1:
                return hits[0] + (off - a) + BASE, w
    return None, None


def main():
    src = open(sys.argv[1], 'rb').read()
    dst = open(sys.argv[2], 'rb').read()
    addrs = [int(a, 16) for a in sys.argv[3:]]
    if not addrs:
        # carte des décalages : un point tous les 64 Kio de .text/.rodata/.data
        last = None
        for addr in range(BASE, BASE + len(src), 0x8000):
            new, _ = locate(src, dst, addr)
            d = None if new is None else new - addr
            if d != last:
                print('%08x  decalage %s' % (addr, 'introuvable' if d is None else '%+d' % d))
                last = d
        return
    for a in addrs:
        new, w = locate(src, dst, a)
        print('%08x -> %s' % (a, 'introuvable' if new is None else '%08x (%+d, fenetre %d)' % (new, new - a, w)))


if __name__ == '__main__':
    main()
