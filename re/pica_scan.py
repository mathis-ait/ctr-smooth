import re, struct, bisect, sys
code = open('rosa-or/code.bin','rb').read(); BASE=0x100000
funcs = []
for line in open('out/funcs.txt', encoding='utf-8'):
    a, size, name = line.split(); funcs.append((int(a,16), int(size), name))
funcs.sort(); starts = [f[0] for f in funcs]
def fn(addr):
    i = bisect.bisect_right(starts, addr) - 1
    if i >= 0 and starts[i] <= addr < starts[i] + funcs[i][1]: return funcs[i][2]
    return '?'
# mots de commande PICA : registre dans les 16 bits bas, masque dans 16-19, taille 20-27, bit 31 = consecutif
hits = {}
for off in range(0, 0x47A000, 4):
    w = struct.unpack_from('<I', code, off)[0]
    reg = w & 0xFFFF
    if reg in (0x02C0, 0x02C1, 0x02B0, 0x02B1, 0x02B2) and (w >> 16) & 0xF in (0xF, 0x1, 0x3, 0x7) :
        hits.setdefault(fn(BASE + off), []).append((BASE + off, w))
for f, l in sorted(hits.items(), key=lambda kv: -len(kv[1])):
    print('%-16s %3d  %s' % (f, len(l), ' '.join('%08x:%08x' % x for x in l[:6])))
print('---- chaines de fichiers source')
for m in re.finditer(rb'[A-Za-z0-9_/\.\-]+\.(?:cpp|h|c)\x00', code):
    s = m.group().rstrip(b'\0').decode()
    if 'gfx' in s.lower() or 'grp' in s.lower() or 'g3d' in s.lower() or 'nw' in s.lower() or 'scene' in s.lower() or 'render' in s.lower() or 'mtx' in s.lower() or 'math' in s.lower():
        print('%08x %s' % (BASE + m.start(), s))
