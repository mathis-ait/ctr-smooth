import sys, struct
from capstone import *
code = open(sys.argv[1], 'rb').read(); BASE = 0x100000
start, end = int(sys.argv[2], 16), int(sys.argv[3], 16)
md = Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN); md.detail = False
def rd(a):
    o = a - BASE
    return struct.unpack_from('<I', code, o)[0] if 0 <= o < len(code)-3 else None
for i in md.disasm(code[start-BASE:end-BASE], start):
    note = ''
    if i.mnemonic.startswith('ldr') and '[pc, #' in i.op_str:
        imm = int(i.op_str.split('#')[1].rstrip(']'), 0)
        v = rd((i.address + 8 + imm) & ~3)
        if v is not None: note = f'   ; =0x{v:08x}'
    print(f'{i.address:08x}  {code[i.address-BASE:i.address-BASE+4].hex()}  {i.mnemonic:8s} {i.op_str}{note}')
