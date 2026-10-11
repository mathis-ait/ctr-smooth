"""Adresses de code.bin référencées par les modules CRO sans passer par les exports nommés de
static.crs : imports anonymes (cible = position dans un segment de « static »). Indispensable
pour savoir si une fonction de code.bin est vraiment inutilisée (re/deadfn.py --cro).

  cro_static_refs.py static.crs dossier_des_cro [ADDR_DEBUT ADDR_FIN]
"""
import os
import struct
import sys


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def cstr(d, o):
    return d[o:d.index(b'\0', o)].decode('ascii', 'replace')


def static_segments(path):
    d = open(path, 'rb').read()
    return [struct.unpack_from('<III', d, u32(d, 0xC8) + 12 * i) for i in range(u32(d, 0xCC))]


def refs(cro_dir, segs):
    out = {}
    for name in sorted(os.listdir(cro_dir)):
        if not name.lower().endswith('.cro'):
            continue
        d = open(os.path.join(cro_dir, name), 'rb').read()
        if d[0x80:0x84] != b'CRO0':
            continue
        mods, nmods = u32(d, 0xF0), u32(d, 0xF4)
        for i in range(nmods):
            e = mods + 20 * i
            mname = cstr(d, u32(d, e))
            if mname.strip('|') != 'static':
                continue
            anon, nanon = u32(d, e + 12), u32(d, e + 16)
            for k in range(nanon):
                so = u32(d, anon + 8 * k)
                seg = segs[so & 0xF]
                out.setdefault(seg[0] + (so >> 4), []).append(name)
    return out


def main():
    segs = static_segments(sys.argv[1])
    r = refs(sys.argv[2], segs)
    print('%d adresses de static référencées par import anonyme' % len(r))
    if len(sys.argv) > 4:
        a0, a1 = int(sys.argv[3], 16), int(sys.argv[4], 16)
        hits = {a: m for a, m in r.items() if a0 <= a < a1}
        print('dans %08x-%08x :' % (a0, a1), {('%08x' % a): sorted(set(m)) for a, m in hits.items()} or 'aucune')


if __name__ == '__main__':
    main()
