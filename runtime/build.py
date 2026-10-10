"""Compile le runtime ctr-smooth et produit le code.ips pour Rubis Oméga EUR v1.0.

  build.py [--code code.bin] [--counters] [--merge autre.ips] [-o sortie.ips]

Étapes : gcc (ARM, VFPv2) → ELF lié dans les marges de code.bin → binaires
.text / .data → enregistrements IPS + crochets. Chaque octet remplacé est
comparé à la valeur attendue dans code.bin d'origine (refus si différent) et
le SHA-256 de code.bin doit être celui du profil.
"""
import argparse
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'proto'))
from mkpatch import read_ips, write_ips  # noqa: E402

GCC = os.environ.get('ARM_GCC_BIN', r'C:\Users\Thisma\Documents\Switch\tools-re\gcc\bin')
CODE = os.environ.get('CTR_SMOOTH_CODE_BIN', r'C:\Users\Thisma\Documents\Switch\tools-re\rosa-or\code.bin')
SHA = 'd587c98ac5c4dedacf9be4baf2d6b7d10169e6a63f8bc35b132002cc27bc1a37'
BASE = 0x00100000
DEAD_FN_HEAD = 'f04f2de9b80f9fe5'  # 0x004FBF20 : push {r4-r11,lr} ; ldr r0,[pc,#0xFB8] (fonction morte)


def tool(name):
    return os.path.join(GCC, 'arm-none-eabi-' + name)


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit('échec : %s\n%s%s' % (' '.join(args), r.stdout, r.stderr))
    return r.stdout


def branch(src, dst, link=False):
    off = ((dst - (src + 8)) >> 2) & 0xFFFFFF
    return struct.pack('<I', (0xEB000000 if link else 0xEA000000) | off)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--code', default=CODE)
    ap.add_argument('--counters', action='store_true', help='ajoute les compteurs de trace de la phase 0')
    ap.add_argument('--test-input', action='store_true', help='injection de boutons via S.vpad (essais automatisés)')
    ap.add_argument('--count3d', action='store_true', help='compteur des passes de scene 3D (0x0038CEA4)')
    ap.add_argument('--probe', action='append', default=[], type=lambda s: int(s, 0),
                    help='essais : compte les appels de la fonction ADDR par parite (8 au plus ; implique --count3d)')
    ap.add_argument('--script', help='partie scriptee compilee (essais deterministes), implique --test-input')
    ap.add_argument('--snap', type=int, default=1700, help='image de l instantane (avec --script)')
    ap.add_argument('--enabled', type=int, default=1, help='lissage actif au demarrage (avec --script)')
    ap.add_argument('--merge', action='append', default=[])
    ap.add_argument('-o', default=os.path.join(HERE, 'build', 'code.ips'))
    a = ap.parse_args()
    if a.probe:
        a.count3d = True

    code = open(a.code, 'rb').read()
    if hashlib.sha256(code).hexdigest() != SHA:
        sys.exit('code.bin inattendu (profil : Rubis Oméga EUR v1.0)')

    out = os.path.join(HERE, 'build')
    os.makedirs(out, exist_ok=True)
    defines = []
    if a.script:
        a.test_input = True
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        from replay import parse_script2
        absolute, relative = parse_script2(a.script)
        lines = ['/* genere par build.py depuis %s */' % os.path.basename(a.script),
                 '__attribute__((section(".rodata.testdata"))) static const u32 test_script[] = {']
        lines += ['    %du, 0x%xu,' % (f, m) for f, m in absolute]
        lines += ['    0xFFFF0000u, 0u, /* ancre : apparition du joueur */']
        lines += ['    %du, 0x%xu,' % (f, m) for f, m in relative]
        lines += ['    0xFFFFFFFFu, 0u,', '};',
                  '#define TEST_SNAP_REL %du' % a.snap,
                  '#define TEST_ENABLED %du' % a.enabled,
                  '#define TEST_SNAP_A 0x08C55E64u /* gfl MT19937 */',
                  '#define TEST_SNAP_ALEN 2500u', '']
        with open(os.path.join(out, 'test_script.h'), 'w', encoding='utf-8', newline='') as h:
            h.write(chr(10).join(lines))
        defines = ['-DTEST_SCRIPT', '-I', HERE]
    cflags = ['-marm', '-mcpu=mpcore', '-mfpu=vfp', '-mfloat-abi=hard', '-Os', '-ffreestanding',
              '-fno-builtin', '-nostdlib', '-fno-unwind-tables', '-fno-asynchronous-unwind-tables',
              '-fomit-frame-pointer', '-ffunction-sections', '-Wall', '-Wextra']
    run(tool('gcc'), *cflags, *defines, *(['-DCOUNT3D'] if a.count3d else []), '-c', os.path.join(HERE, 'smooth.c'), '-o', os.path.join(out, 'smooth.o'))
    run(tool('gcc'), *cflags, '-c', os.path.join(HERE, 'hooks.S'), '-o', os.path.join(out, 'hooks.o'))
    objs = [os.path.join(out, 'hooks.o'), os.path.join(out, 'smooth.o')]
    if a.probe:
        a.count3d = True
        # trampolines : compteur, puis instruction d'origine (push, independante de la position), retour en ADDR+4
        lines = ['    .syntax unified', '    .arm', '    .section .text.testcnt, "ax"']
        for i, addr in enumerate(a.probe[:8]):
            word = struct.unpack('<I', code[addr - BASE:addr - BASE + 4])[0]
            lines += ['    .global probe_%d' % i, 'probe_%d:' % i, '    push {r0-r3, r12, lr}', '    mov r0, #%d' % i,
                      '    blx smooth_probe', '    pop {r0-r3, r12, lr}', '    .word 0x%08x' % word, '    ldr pc, =0x%08x' % (addr + 4), '    .ltorg']
        open(os.path.join(out, 'probes.S'), 'w').write(chr(10).join(lines) + chr(10))
        run(tool('gcc'), '-mcpu=mpcore', '-c', os.path.join(out, 'probes.S'), '-o', os.path.join(out, 'probes.o'))
        objs.append(os.path.join(out, 'probes.o'))
    if a.test_input or a.count3d:
        # code des essais : Thumb (plus compact), sans flottants
        tflags = ['-mthumb', '-mcpu=mpcore', '-mfloat-abi=soft', '-Os', '-ffreestanding', '-fno-builtin', '-nostdlib',
                  '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-fomit-frame-pointer', '-ffunction-sections',
                  '-Wall', '-Wextra']
        run(tool('gcc'), *tflags, *defines, '-c', os.path.join(HERE, 'test.c'), '-o', os.path.join(out, 'test.o'))
        objs.append(os.path.join(out, 'test.o'))
    elf = os.path.join(out, 'ctr-smooth.elf')
    run(tool('ld'), '-T', os.path.join(HERE, 'link.ld'), '--gc-sections', '-e', 'hook_gate',
        '-u', 'hook_camera', '-u', 'hook_h3d', '-u', 'hook_nwmesh', '-u', 'smooth_end', '-u', 'smooth_fade', '-u', 'hook_lytanim', '-u', 'hook_setview', '-u', 'hook_hid', '-u', 'S',
        *(['-u', 'hook_pad', '-u', 'hook_touch'] if a.test_input else []), *(['-u', 'hook_cnt3d'] if a.count3d else []),
        *[x for i in range(len(a.probe[:8])) for x in ('-u', 'probe_%d' % i)],
        '--no-warn-mismatch', *objs, '-o', elf)
    run(tool('objcopy'), '-O', 'binary', '-j', '.text', elf, os.path.join(out, 'text.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.testro', elf, os.path.join(out, 'testro.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.testtext', elf, os.path.join(out, 'testtext.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.rtext', elf, os.path.join(out, 'rtext.bin'))
    syms = {}
    for line in run(tool('nm'), elf).splitlines():
        p = line.split()
        if len(p) == 3:
            syms[p[2]] = int(p[0], 16)
    text = open(os.path.join(out, 'text.bin'), 'rb').read()
    t0 = 0x00579610
    if t0 + len(text) > 0x0057A000:
        sys.exit('runtime trop gros : .text %d / 2544' % len(text))
    if not (0x006AE620 <= syms['S'] and syms['S'] + 0x40 <= 0x006AEFF0):
        sys.exit('etat hors de la marge du .bss')

    def orig(addr, n=4):
        return code[addr - BASE:addr - BASE + n]

    # Instructions remplacées et leur valeur d'origine (contrôle anti-mauvaise version).
    hooks = [
        (0x0010E530, 'ldrb r0,[r4,#0xd]', bytes.fromhex('0d00d4e5'), branch(0x0010E530, syms['hook_gate'], True)),
        (0x0010E534, 'rsb r1,r6,#0', bytes.fromhex('001066e2'), bytes.fromhex('000050e3')),  # cmp r0,#0
        (0x0010E538, 'tst r0,r1', bytes.fromhex('010010e1'), bytes.fromhex('00f020e3')),     # nop
        (0x0010E61C, 'nop', bytes.fromhex('00f020e3'), branch(0x0010E61C, syms['smooth_end'], True)),
        (0x0010E5AC, 'bl 0x0011CB60', bytes.fromhex('6b3900eb'), branch(0x0010E5AC, syms['smooth_fade'], True)),
        (0x0014D618, 'push {r4-r12,lr}', bytes.fromhex('f05f2de9'), branch(0x0014D618, syms['hook_lytanim'])),
        (0x00375EA8, 'push {r0-r11,lr}', bytes.fromhex('ff4f2de9'), branch(0x00375EA8, syms['hook_camera'])),
        (0x0039B338, 'push {r3-r11,lr}', bytes.fromhex('f84f2de9'), branch(0x0039B338, syms['hook_h3d'])),
        (0x002EC354, 'push {r4-r8,lr}', bytes.fromhex('f0412de9'), branch(0x002EC354, syms['hook_nwmesh'])),
        (0x00392FB4, 'add r4,r0,#0x148', bytes.fromhex('524f80e2'), branch(0x00392FB4, syms['hook_setview'], True)),
        # boutons tenus : interrupteur en jeu (release) ou entrées injectées (essais)
        (0x0036FB34, 'add r1,r4,#0x98', bytes.fromhex('981084e2'),
         branch(0x0036FB34, syms['hook_pad' if a.test_input else 'hook_hid'], True)),
    ]
    if a.test_input:
        hooks.append((0x0036FB40, 'mov r0,r4', bytes.fromhex('0400a0e1'), branch(0x0036FB40, syms['hook_touch'], True)))
        if a.count3d:
            hooks.append((0x0038CEA4, 'push {r3-r7,lr}', bytes.fromhex('f8402de9'), branch(0x0038CEA4, syms['hook_cnt3d'])))
    for i, addr in enumerate(a.probe[:8]):
        hooks.append((addr, 'sonde %d' % i, orig(addr), branch(addr, syms['probe_%d' % i])))
    recs = []
    for m in a.merge:
        recs += read_ips(m)
    for addr, what, want, new in hooks:
        if orig(addr) != want:
            sys.exit('0x%08x : %s attendu (%s), trouvé %s' % (addr, what, want.hex(), orig(addr).hex()))
        recs.append((addr - BASE, new))
    if any(orig(t0, len(text))):
        sys.exit('la marge de .text n est pas vide')
    recs.append((t0 - BASE, text))
    # corps du runtime dans la fonction morte 0x004FBF20 (10 Ko), suivi du code des essais
    FN0, FN1 = 0x004FBF20, 0x004FE790
    rtext = open(os.path.join(out, 'rtext.bin'), 'rb').read()
    if orig(FN0, 8) != bytes.fromhex(DEAD_FN_HEAD):
        sys.exit('fonction morte 0x%08x : octets inattendus (autre version ?)' % FN0)
    recs.append((FN0 - BASE, rtext))
    testro = open(os.path.join(out, 'testro.bin'), 'rb').read() if os.path.exists(os.path.join(out, 'testro.bin')) else b''
    if testro:
        if len(testro) > 0x5E0 or any(orig(0x005EBA20, len(testro))):
            sys.exit('donnees de test hors de la marge de .rodata')
        recs.append((0x005EBA20 - BASE, testro))
    testtext = open(os.path.join(out, 'testtext.bin'), 'rb').read() if os.path.exists(os.path.join(out, 'testtext.bin')) else b''
    if testtext:
        if not (a.test_input or a.count3d):
            sys.exit('code de test dans un build distribue')
        t1 = syms.get('hook_pad', syms.get('hook_cnt3d'))
        recs.append((t1 - BASE, testtext))  # après le runtime, builds de test uniquement
        print('code de test : %d octets en 0x%08x' % (len(testtext), t1))
    if a.counters:
        import instrument
        recs += instrument.records(draw60=False)
    os.makedirs(os.path.dirname(os.path.abspath(a.o)), exist_ok=True)
    write_ips(a.o, recs)
    used = len(rtext) + len(testtext)
    if FN0 + used > FN1:
        sys.exit('runtime trop gros pour la fonction morte : %d / %d' % (used, FN1 - FN0))
    print('crochets : %d octets en fin de .text (marge %d) ; runtime : %d octets en 0x%08x (marge %d) ; etat a 0x%08x' % (
        len(text), 0x0057A000 - t0 - len(text), len(rtext), FN0, FN1 - FN0 - used, syms['S']))
    for k in ('hook_gate', 'hook_camera', 'hook_h3d', 'hook_nwmesh', 'smooth_gate', 'smooth_end', 'S') + (('hook_pad',) if a.test_input else ()):
        print('  %-14s 0x%08x' % (k, syms[k]))
    print('->', a.o)


if __name__ == '__main__':
    main()
