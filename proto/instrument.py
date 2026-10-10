"""Prototype phase 0 (OR EUR v1.0) : compteurs de trace + « draw() a chaque image ».

Produit deux IPS a partir des octets d'origine de runEachFrame (0x0010E354) :
  - or-eur-v1.0-counters.ips        compteurs seuls (reference 30 fps)
  - or-eur-v1.0-counters-draw60.ips compteurs + dessin a chaque VBlank

Compteurs (mots 32 bits, zone de remplissage inutilisee en fin de .bss, lisibles
par le stub GDB) :
  0x006AEFF0  nombre de passages dans update()      (chemin r6 = 1)
  0x006AEFF4  nombre d'images sans update()         (chemin r6 = 0)
  0x006AEFF8  nombre d'appels a draw()
Le .bss commence a 0x00630000 (taille 0x7EC2C) : la page 0x006AE000-0x006AF000 est
mappee, les octets au-dela de 0x006AEC2C ne sont references par rien.

Usage : instrument.py [--merge kaleido.ips] [-o dossier]
"""
import argparse
import os
import sys

from keystone import Ks, KS_ARCH_ARM, KS_MODE_ARM, KS_MODE_LITTLE_ENDIAN

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
from mkpatch import read_ips, write_ips  # noqa: E402

BASE = 0x100000
COUNTERS = 0x006AEFF0
LITERAL = 0x0010E3B0  # mot mort reutilise comme litteral (adresse des compteurs)

ks = Ks(KS_ARCH_ARM, KS_MODE_ARM | KS_MODE_LITTLE_ENDIAN)


def asm(addr, code):
    enc, _ = ks.asm(code, addr)
    return addr, bytes(enc)


def records(draw60):
    recs = []
    # Chemin update (r6 = 1) : 0x10E398..0x10E3B4 est du code mort (mov r0,r0 ; nop ; nop ;
    # mov r0,#0 ; cmp r0,#0 ; nop ; bne ; b 0x10E3D0). r0/r1 sont redefinis avant usage en 0x10E3D0.
    recs.append(asm(0x0010E398, '''
        ldr r0, [pc, #0x10]      @ 0x10E3B0 -> COUNTERS
        ldr r1, [r0]
        add r1, r1, #1
        str r1, [r0]
        b #0x0010E3D0
        nop
    '''))
    recs.append((LITERAL, COUNTERS.to_bytes(4, 'little')))
    recs.append(asm(0x0010E3B4, 'nop'))
    # Chemin sans update (r6 = 0) : 0x10E3B8..0x10E3C8 (nop ; mov r0,#0 ; cmp ; nop ; bne jamais pris).
    recs.append(asm(0x0010E3B8, '''
        ldr r0, [pc, #-0x10]     @ 0x10E3B0
        ldr r1, [r0, #4]
        add r1, r1, #1
        str r1, [r0, #4]
        nop
    '''))
    # draw() : deux nops en 0x10E5A4/0x10E5A8 et 0x10E5B0/0x10E5B4 autour de bl 0x11CB60 ;
    # sl/fp (r10/r11) ne sont pas vivants avant 0x10E6A4.
    recs.append(asm(0x0010E5A4, '''
        ldr r10, [pc, #-0x1FC]   @ 0x10E3B0
        ldr r11, [r10, #8]
    '''))
    recs.append(asm(0x0010E5B0, '''
        add r11, r11, #1
        str r11, [r10, #8]
    '''))
    if draw60:
        # 0x10E53C : bne 0x10E554 (« image d'update : pas de draw ») -> nop
        recs.append(asm(0x0010E53C, 'nop'))
    return [(a - BASE, d) for a, d in recs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--merge', action='append', default=[])
    ap.add_argument('-o', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    base = []
    for m in a.merge:
        base += read_ips(m)
    for name, draw60 in (('or-eur-v1.0-counters.ips', False), ('or-eur-v1.0-counters-draw60.ips', True)):
        recs = base + records(draw60)
        path = os.path.join(a.o, name)
        write_ips(path, recs)
        print(path)
        for off, d in sorted(recs):
            print('  0x%08x <- %s' % (off + BASE, d.hex()))


if __name__ == '__main__':
    main()
