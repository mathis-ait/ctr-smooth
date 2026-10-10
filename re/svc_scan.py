import sys, struct
from capstone import *
code = open(sys.argv[1], 'rb').read()
BASE = 0x100000
md = Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN)
# svc #imm en mode ARM : cond=1110 1111 imm24 -> 0xEF000028 pour GetSystemTick
hits = []
for off in range(0, len(code) - 4, 4):
    w = struct.unpack_from('<I', code, off)[0]
    if w == 0xEF000028:
        hits.append(BASE + off)
print("svc 0x28 (GetSystemTick) sites:", len(hits))
for a in hits:
    print(hex(a))
# Pour chaque site : afficher 12 instructions autour, pour repérer la boucle principale.
for a in hits[:40]:
    off = a - BASE
    print("\n==", hex(a))
    for i in md.disasm(code[off-32:off+32], a-32):
        print(f"  {i.address:08x}  {i.mnemonic:8s} {i.op_str}")
