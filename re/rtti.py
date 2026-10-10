"""Recupere les noms de classes GFL2 depuis le RTTI Itanium C++ de code.bin.

Un objet type_info = { vtable* (__class_type_info...), const char* nom, [bases...] }.
Un vtable = { offset_to_top, type_info*, fonctions... } ; les objets pointent sur
vtable+8. On en deduit : nom de classe -> adresse du vtable -> fonctions virtuelles.

Usage : rtti.py code.bin [--base 0x100000] [--filter gfl2] [-o symbols.txt]
Sortie : une ligne par fonction virtuelle « Classe::vfn_N  adresse », importable
dans Ghidra (ImportSymbolsScript : nom adresse f).
"""
import argparse
import re
import struct


def demangle_name(s):
    # Nom mangle de type_info sans le 'Z' initial : N3gfl2ui6ButtonE -> gfl2::ui::Button
    if s.startswith('N') and s.endswith('E'):
        body, parts, i = s[1:-1], [], 0
        while i < len(body):
            m = re.match(r'\d+', body[i:])
            if not m:
                parts.append(body[i:])
                break
            n = int(m.group()); i += len(m.group())
            parts.append(body[i:i + n]); i += n
        return '::'.join(parts)
    m = re.match(r'^(\d+)(.*)$', s)
    if m and len(m.group(2)) == int(m.group(1)):
        return m.group(2)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('code')
    ap.add_argument('--base', type=lambda s: int(s, 0), default=0x100000)
    ap.add_argument('--filter', default='')
    ap.add_argument('-o')
    a = ap.parse_args()
    d = open(a.code, 'rb').read()
    base = a.base

    # 1. Chaines de noms mangles (type_info::__name) : [N0-9]...E\0
    names = {}
    for m in re.finditer(rb'(?<=\x00)(N(?:\d+[A-Za-z_0-9]+)+E|\d+[A-Za-z_][A-Za-z_0-9]*)\x00', d):
        names[base + m.start(1)] = m.group(1).decode()

    # 2. Pointeurs vers ces chaines = champ nom des type_info (mot a l'offset +4)
    words = {}
    for off in range(0, len(d) - 3, 4):
        words.setdefault(struct.unpack_from('<I', d, off)[0], []).append(base + off)
    typeinfos = {}
    for addr, s in names.items():
        for ref in words.get(addr, []):
            ti = ref - 4
            typeinfos[ti] = demangle_name(s)

    # 3. Vtables : mot = type_info* precede de offset_to_top (0 pour la base primaire)
    vtables = []
    for ti, name in typeinfos.items():
        for ref in words.get(ti, []):
            if ref in typeinfos:  # c'est un autre type_info (classe de base), pas un vtable
                continue
            top = struct.unpack_from('<I', d, ref - 4 - base)[0]
            if top > 0x1000 and top < 0xFFFF0000:
                continue
            vt = ref + 4
            fns = []
            o = vt - base
            while o + 4 <= len(d):
                f = struct.unpack_from('<I', d, o)[0]
                if not (base <= f < base + 0x47A000) or f & 3:
                    break
                fns.append(f); o += 4
            if fns:
                vtables.append((name, vt, top, fns))

    flt = re.compile(a.filter) if a.filter else None
    lines = []
    for name, vt, top, fns in sorted(vtables, key=lambda v: (v[0], v[1])):
        if flt and not flt.search(name):
            continue
        suffix = '' if top == 0 else '@%d' % (-(top - (1 << 32)) if top >= 1 << 31 else top)
        lines.append('# %s%s vtable 0x%08x (%d fonctions)' % (name, suffix, vt, len(fns)))
        for i, f in enumerate(fns):
            lines.append('%s%s::vfn_%02d 0x%08x f' % (name, suffix.replace('@', '_sub'), i, f))
    text = '\n'.join(lines) + '\n'
    if a.o:
        open(a.o, 'w', encoding='utf-8', newline='\n').write(text)
    print('%d noms, %d type_info, %d vtables' % (len(names), len(typeinfos), len(vtables)))
    if not a.o:
        print(text)


if __name__ == '__main__':
    main()
