"""Fonctions vraiment inutilisées d'un code.bin, assez grandes pour héberger le runtime.

Une fonction (début = « push {..., lr} », fin = début suivant) est retenue si aucune
adresse de son intervalle n'est :
  - la cible d'un B/BL/BLX hors de la fonction ;
  - un mot absolu n'importe où dans code.bin (vtables, littéraux, tables de pointeurs) ;
  - la cible d'un mot relatif (init_array d'armcc : valeur = cible - adresse du mot) ;
  - exportée par static.crs (seule porte d'entrée des modules CRO) ;
  - calculée par ADD/SUB rX, pc, #imm hors de la fonction ;
  - importée par un module CRO (imports anonymes vers « |static| », re/cro_static_refs.py) :
    c'est ainsi que DllBag.cro appelle 0x0046DCA0 (1.4), invisible sans ce contrôle.
Leçon de la 0.9.0 : le contrôle relatif est indispensable (constructeurs statiques).

  deadfn.py code.bin static.crs dossier_des_cro [taille_min]
"""
import struct
import sys

import numpy as np

BASE = 0x00100000


def crs_exports(path):
    d = open(path, 'rb').read()
    u = lambda o: struct.unpack_from('<I', d, o)[0]
    segs = [struct.unpack_from('<III', d, u(0xC8) + 12 * i) for i in range(u(0xCC))]
    addr = lambda so: segs[so & 0xF][0] + (so >> 4)
    named = [u(u(0xD0) + 8 * i + 4) for i in range(u(0xD4))]
    indexed = [u(u(0xD8) + 4 * i) for i in range(u(0xDC))]
    return {addr(s) for s in named + indexed}


def main():
    code = open(sys.argv[1], 'rb').read()
    exports = crs_exports(sys.argv[2])
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cro_static_refs
    exports |= set(cro_static_refs.refs(sys.argv[3], cro_static_refs.static_segments(sys.argv[2])))
    minsize = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0x800
    w = np.frombuffer(code[:len(code) // 4 * 4], dtype='<u4')
    n = len(w)
    addr = np.arange(n, dtype=np.int64) * 4 + BASE
    text_end = BASE + struct.unpack_from('<I', code, 0)[0] if False else None
    # fin de .text : dernier mot non nul avant la première page de .rodata (0x57A000)
    text_n = (0x0057A000 - BASE) // 4
    tw = w[:text_n]
    # débuts de fonction : STMDB sp!, {..., lr}
    starts = np.nonzero((tw & 0xFFFF4000) == 0xE92D4000)[0]
    marks = np.zeros(n + 1, dtype=np.int32)

    def mark(targets):
        t = np.asarray(targets, dtype=np.int64)
        t = t[(t >= BASE) & (t < BASE + n * 4)]
        np.add.at(marks, (t - BASE) // 4, 1)

    # 1. branchements
    br = np.nonzero((tw & 0x0E000000) == 0x0A000000)[0]
    imm = (tw[br] & 0x00FFFFFF).astype(np.int64)
    imm = np.where(imm & 0x800000, imm - 0x1000000, imm)
    tgt = addr[br] + 8 + imm * 4
    # 2. mots absolus (tout le fichier)
    ab = w.astype(np.int64)
    # 3. mots relatifs (signés)
    sw = np.where(ab >= 2**31, ab - 2**32, ab)
    rel = addr + sw
    # 4. adresses calculées : ADD/SUB rX, pc, #imm (ADR)
    adr = np.nonzero(((tw & 0x0FFF0000) == 0x028F0000) | ((tw & 0x0FFF0000) == 0x024F0000))[0]
    rot = ((tw[adr] >> 8) & 0xF).astype(np.int64) * 2
    v8 = (tw[adr] & 0xFF).astype(np.int64)
    val = ((v8 >> rot) | (v8 << (32 - rot))) & 0xFFFFFFFF
    val = np.where(rot == 0, v8, val)
    adrt = np.where((tw[adr] & 0x00F00000) == 0x00800000, addr[adr] + 8 + val, addr[adr] + 8 - val)
    # 5. exports
    ex = np.array(sorted(exports), dtype=np.int64)
    found = []
    ends = np.append(starts[1:], text_n)
    # cible -> fonction, en retirant les branchements internes
    for s, e in zip(starts, ends):
        size = (e - s) * 4
        if size < minsize:
            continue
        a0, a1 = BASE + s * 4, BASE + e * 4
        inside = (tgt >= a0) & (tgt < a1)
        from_out = inside & ~((addr[br] >= a0) & (addr[br] < a1))
        if from_out.any():
            continue
        if ((ab >= a0) & (ab < a1)).any() or (((ab & ~1) >= a0) & ((ab & ~1) < a1)).any():
            continue
        if ((rel >= a0) & (rel < a1)).any():
            continue
        if ((ex >= a0) & (ex < a1)).any():
            continue
        if ((adrt >= a0) & (adrt < a1) & ~((addr[adr] >= a0) & (addr[adr] < a1))).any():
            continue
        found.append((a0, a1, size))
    for a0, a1, size in sorted(found, key=lambda x: -x[2])[:15]:
        print('%08x-%08x  %6d octets' % (a0, a1, size))
    print('%d candidates (>= %d octets)' % (len(found), minsize))


if __name__ == '__main__':
    main()
