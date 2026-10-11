"""Relocalisation par motif masqué (même jeu, autre version) : les mots ARM B/BL et les
chargements relatifs à PC (littéraux) changent quand le code bouge ; on les ignore et on
compare le reste d'une fenêtre autour de l'adresse. Pour les données (littéraux), on suit
un mot chargé par une instruction de référence relocalisée.

  reloc2.py source.bin cible.bin code ADDR [ADDR ...]
  reloc2.py source.bin cible.bin lit ADDR_INSTR   (valeur du littéral chargé par cette
                                                   instruction dans les deux versions)
"""
import struct
import sys

import numpy as np

BASE = 0x00100000


def words(b):
    return np.frombuffer(b[:len(b) // 4 * 4], dtype='<u4')


def mask_of(w):
    m = np.full(w.shape, 0xFFFFFFFF, dtype=np.uint32)
    br = (w & 0x0E000000) == 0x0A000000           # B / BL (toutes conditions)
    m[br] = 0xFF000000
    ldrpc = (w & 0x0F7F0000) == 0x051F0000        # LDR rX, [pc, #imm]
    m[ldrpc] = 0xFFFFF000
    vldr = (w & 0x0F3F0E00) == 0x0D1F0A00         # VLDR sX/dX, [pc, #imm]
    m[vldr] = 0xFFFFFF00
    return m


def locate(src_w, dst_w, idx, before=8, after=24):
    for b, a in ((before, after), (16, 48), (32, 96), (4, 12)):
        lo = max(0, idx - b)
        pat = src_w[lo:idx + a]
        m = mask_of(pat)
        pm = pat & m
        n = len(pat)
        # recherche vectorisée : candidats sur le premier mot non masqué complètement
        first = int(np.argmax(m == 0xFFFFFFFF))
        cand = np.nonzero((dst_w & m[first]) == pm[first])[0] - first
        hits = []
        for c in cand:
            if c < 0 or c + n > len(dst_w):
                continue
            if np.array_equal(dst_w[c:c + n] & m, pm):
                hits.append(c)
                if len(hits) > 1:
                    break
        if len(hits) == 1:
            return hits[0] + (idx - lo), b + a
    return None, None


def literal(code_w, idx):
    w = int(code_w[idx])
    imm = w & 0xFFF
    off = imm if w & 0x00800000 else -imm
    return int(code_w[(idx * 4 + 8 + off) // 4])


def main():
    src, dst = open(sys.argv[1], 'rb').read(), open(sys.argv[2], 'rb').read()
    sw, dw = words(src), words(dst)
    mode, addrs = sys.argv[3], [int(a, 16) for a in sys.argv[4:]]
    for a in addrs:
        new, w = locate(sw, dw, (a - BASE) // 4)
        if new is None:
            print('%08x -> introuvable' % a)
            continue
        na = new * 4 + BASE
        if mode == 'lit':
            print('%08x -> %08x : litteral %08x -> %08x' % (a, na, literal(sw, (a - BASE) // 4), literal(dw, new)))
        else:
            print('%08x -> %08x (%+d, fenetre %d mots)' % (a, na, na - a, w))


if __name__ == '__main__':
    main()
