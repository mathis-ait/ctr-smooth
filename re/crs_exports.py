"""Exports de static.crs (symboles de code.bin utilises par les modules CRO).
  crs_exports.py static.crs [orphans.txt code.bin]
Sans les deux derniers arguments : liste des exports. Avec : candidats « code mort »
(fonctions sans reference, sans litteral, non exportees)."""
import struct, sys
d = open(sys.argv[1], 'rb').read()
u = lambda o: struct.unpack_from('<I', d, o)[0]
assert d[0x80:0x84] == b'CRO0', d[0x80:0x84]
seg_off, seg_n = u(0xC8), u(0xCC)
segs = [struct.unpack_from('<III', d, seg_off + 12 * i) for i in range(seg_n)]
def addr(so):
    return segs[so & 0xF][0] + (so >> 4)
named = [(u(u(0xD0) + 8 * i), u(u(0xD0) + 8 * i + 4)) for i in range(u(0xD4))]
indexed = [u(u(0xD8) + 4 * i) for i in range(u(0xDC))]
exports = set()
for name_off, so in named:
    exports.add(addr(so))
for so in indexed:
    exports.add(addr(so))
if len(sys.argv) < 4:
    print('segments :', ['%08x+%x type %d' % s for s in segs])
    print('%d exports nommes, %d indexes' % (len(named), len(indexed)))
    for a in sorted(exports)[:20]:
        print('  %08x' % a)
    sys.exit()
code = open(sys.argv[3], 'rb').read()
words = set(struct.unpack_from('<%dI' % (len(code) // 4), code))
print('segments :', ['%08x+%x type %d' % s for s in segs], ' exports :', len(exports))
n = 0
for line in open(sys.argv[2]):
    a, size, name = line.split(None, 2)
    a, size = int(a, 16), int(size)
    if size < 512:
        break
    if a in words or (a | 1) in words or a in exports or (a | 1) in exports:
        continue
    print('%08x %5d' % (a, size)); n += 1
    if n >= 12:
        break
