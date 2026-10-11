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
# Profils par version (SHA-256 du code.bin décompressé). Adresses relocalisées par re/reloc2.py
# et vérifiées instruction par instruction (octets d'origine contrôlés plus bas).
OR10 = dict(
    name='Rubis Oméga EUR 1.0',
    gate=0x0010E530, end=0x0010E61C, fade_call=0x0010E5AC, fade_fn=0x0011CB60, lytanim=0x0014D618,
    camera=0x00375EA8, h3d=0x0039B338, nwmesh=0x002EC354, setview=0x00392FB4, hid=0x0036FB34,
    touch=0x0036FB40, cnt3d=0x0038CEA4, transmgr=0x0062F830, cam_vt=0x005DBAB8, skel_vt=0x005DB47C,
    text=(0x00579610, 0x0057A000), ro=(0x005EBA20, 0x005EC000), dead=None, dead_sections=[],
    test_head=0x004FBF20)
# Saphir Alpha EUR 1.0 : mêmes adresses que Rubis Oméga pour tout ce que touche le runtime (le
# code ne décale de 8 octets qu'à partir de 0x3E8000, hors crochets) : même patch.
AS10 = dict(OR10, name='Saphir Alpha EUR 1.0', test_head=0x004FBF18)
# Rubis Oméga 1.4 (mise à jour 0004000E0011C400) : la marge de .text n'a plus que 2 036 octets.
# smooth() et find() restent en ARM (VFP), le reste du runtime est compilé en Thumb (split=True).
# Aucune fonction du jeu n'est réutilisée : re/deadfn.py montre que l'analyse statique ne suffit
# pas (0x0046DCA0 semblait inutilisée, DllBag.cro l'appelle par import anonyme).
OR14 = dict(
    name='Rubis Oméga 1.4',
    gate=0x0010E528, end=0x0010E614, fade_call=0x0010E5A4, fade_fn=0x0011CC40, lytanim=0x0014D650,
    camera=0x00376134, h3d=0x0039B5C4, nwmesh=0x002EC540, setview=0x00393240, hid=0x0036FDC0,
    touch=0x0036FDCC, cnt3d=None, transmgr=0x0062F830, cam_vt=0x005DBCA8, skel_vt=0x005DB66C,
    text=(0x00579810, 0x0057A000), ro=(0x005EBC30, 0x005EC000), dead=None, dead_sections=[],
    split=True, test_head=None)
# Saphir Alpha 1.4 (0004000E0011C500) : mêmes adresses que Rubis Oméga 1.4 pour tout ce que touche
# le runtime (sa .text finit 8 octets plus tôt, avant 0x00579810) : même patch.
AS14 = dict(OR14, name='Saphir Alpha 1.4')
GAMES = {
    'd587c98ac5c4dedacf9be4baf2d6b7d10169e6a63f8bc35b132002cc27bc1a37': OR10,
    'b7f9ce60361f3709ed0ce879658afe10a712f7db060640fa72bba826301b7c16': AS10,
    'ff2ce8f4e95ce7dd0448629be43a8e6524df8ed81a848f52bddc5da06ffd7e80': OR14,
    'd0e00228973241650f05a0dd01e4a2f798b23b58426521ea14195ce01caf938e': AS14,
}
BASE = 0x00100000
DEAD_FN_HEAD = 'f04f2de9b80f9fe5'  # début de la fonction morte : push {r4-r11,lr} ; ldr r0,[pc,#0xFB8] (fonction morte)


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
    ap.add_argument('--inject', action='store_true', help='build distribue + boutons injectes (S.vpad), sans code d essai')
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
    G = GAMES.get(hashlib.sha256(code).hexdigest())
    if not G:
        sys.exit('code.bin inattendu (profils : %s)' % ', '.join(g['name'] for g in GAMES.values()))
    if (a.test_input or a.count3d) and not G['test_head']:
        sys.exit('builds de test indisponibles pour %s : utiliser --inject' % G['name'])
    addr_defs = ['-DADDR_%s=0x%08x' % (k.upper(), G[k]) for k in
                 ('transmgr', 'fade_fn', 'cam_vt', 'skel_vt', 'camera', 'h3d', 'lytanim', 'nwmesh')]
    addr_defs += ['-DADDR_CNT3D=0x%08x' % (G['cnt3d'] or 0)]

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
    variant = [*defines, *addr_defs, *(['-DCOUNT3D'] if a.count3d else []), *(['-DSTATS'] if a.test_input or a.count3d else [])]
    if G.get('split'):
        thumb = ['-mthumb', '-mthumb-interwork', '-mcpu=mpcore', '-mfloat-abi=soft'] + cflags[4:]
        run(tool('gcc'), *thumb, *variant, '-DPART_REST', '-c', os.path.join(HERE, 'smooth.c'), '-o', os.path.join(out, 'smooth.o'))
        run(tool('gcc'), *cflags, '-mthumb-interwork', *variant, '-DPART_CORE', '-c', os.path.join(HERE, 'smooth.c'), '-o', os.path.join(out, 'smooth_core.o'))
    else:
        run(tool('gcc'), *cflags, *variant, '-c', os.path.join(HERE, 'smooth.c'), '-o', os.path.join(out, 'smooth.o'))
    run(tool('gcc'), *cflags, *addr_defs, '-c', os.path.join(HERE, 'hooks.S'), '-o', os.path.join(out, 'hooks.o'))
    objs = [os.path.join(out, 'hooks.o'), os.path.join(out, 'smooth.o')] + ([os.path.join(out, 'smooth_core.o')] if G.get('split') else [])
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
    # build distribué : le runtime suit les crochets dans la marge de .text ; essais : ancienne zone
    testbuild = bool(a.test_input or a.count3d)
    dead = G['dead'] or (G['text'][0], G['text'][0])
    subst = {'RTEXT_REGION': 'CAVE_FN' if testbuild else 'CAVE_TEXT',
             '@TEXT_ORIGIN@': '0x%08x' % G['text'][0], '@TEXT_LENGTH@': '0x%x' % (G['text'][1] - G['text'][0]),
             '@RO_ORIGIN@': '0x%08x' % G['ro'][0], '@RO_LENGTH@': '0x%x' % (G['ro'][1] - G['ro'][0]),
             '@DEAD_ORIGIN@': '0x%08x' % dead[0], '@DEAD_LENGTH@': '0x%x' % (dead[1] - dead[0]),
             '@DEAD_SECTIONS@': ' '.join('*smooth.o(%s)' % x for x in G['dead_sections'])}
    script = open(os.path.join(HERE, 'link.ld'), encoding='utf-8').read()
    for k, v in subst.items():
        script = script.replace(k, v)
    open(os.path.join(out, 'link.ld'), 'w', encoding='utf-8').write(script)
    run(tool('ld'), '-T', os.path.join(out, 'link.ld'), '--gc-sections', *(['--use-blx'] if G.get('split') else []), '-e', 'hook_gate',
        '-u', 'hook_camera', '-u', 'hook_h3d', '-u', 'hook_nwmesh', '-u', 'smooth_end', '-u', 'smooth_fade', '-u', 'hook_lytanim', '-u', 'hook_setview', *(['-u', 'hook_hidv', '-u', 'hook_gatev'] if a.inject else ['-u', 'hook_hid']), '-u', 'S',
        *(['-u', 'hook_pad', '-u', 'hook_touch'] if a.test_input else []), *(['-u', 'hook_cnt3d'] if a.count3d else []),
        *[x for i in range(len(a.probe[:8])) for x in ('-u', 'probe_%d' % i)],
        '--no-warn-mismatch', *objs, '-o', elf)
    run(tool('objcopy'), '-O', 'binary', '-j', '.text', elf, os.path.join(out, 'text.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.testro', elf, os.path.join(out, 'testro.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.testtext', elf, os.path.join(out, 'testtext.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.rtext', elf, os.path.join(out, 'rtext.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.hidv', elf, os.path.join(out, 'hidv.bin'))
    run(tool('objcopy'), '-O', 'binary', '-j', '.rdead', elf, os.path.join(out, 'rdead.bin'))
    syms, thumb_syms = {}, set()
    for line in run(tool('nm'), elf).splitlines():
        p = line.split()
        if len(p) == 3:
            syms[p[2]] = int(p[0], 16)
    for line in run(tool('readelf'), '-sW', elf).splitlines():
        p = line.split()
        if len(p) >= 8 and p[3] == 'FUNC' and int(p[1], 16) & 1:
            thumb_syms.add(p[7])

    def call(src, name):
        # appel depuis le code ARM du jeu : BLX vers une fonction Thumb, BL sinon
        dst = syms[name]
        if name not in thumb_syms:
            return branch(src, dst, True)
        off = dst - (src + 8)
        return struct.pack('<I', 0xFA000000 | ((off >> 1) & 1) << 24 | (off >> 2) & 0xFFFFFF)
    text = open(os.path.join(out, 'text.bin'), 'rb').read()
    rtext = open(os.path.join(out, 'rtext.bin'), 'rb').read()
    t0, rt0 = syms['__text_start'], syms['__rtext_start']
    if t0 + len(text) > G['text'][1]:
        sys.exit('runtime trop gros pour la marge de .text : %d octets / %d' % (t0 + len(text) - G['text'][0], G['text'][1] - G['text'][0]))
    if not (0x006AE620 <= syms['S'] and syms['S'] + 0x40 <= 0x006AEFF0):
        sys.exit('etat hors de la marge du .bss')

    def orig(addr, n=4):
        return code[addr - BASE:addr - BASE + n]

    # Instructions remplacées et leur valeur d'origine (contrôle anti-mauvaise version).
    hid_target = syms['hook_pad' if a.test_input else 'hook_hidv' if a.inject else 'hook_hid']
    hooks = [
        (G['gate'], 'ldrb r0,[r4,#0xd]', bytes.fromhex('0d00d4e5'), branch(G['gate'], syms['hook_gatev' if a.inject else 'hook_gate'], True)),
        (G['gate'] + 4, 'rsb r1,r6,#0', bytes.fromhex('001066e2'), bytes.fromhex('000050e3')),  # cmp r0,#0
        (G['gate'] + 8, 'tst r0,r1', bytes.fromhex('010010e1'), bytes.fromhex('00f020e3')),     # nop
        (G['end'], 'nop', bytes.fromhex('00f020e3'), call(G['end'], 'smooth_end')),
        (G['fade_call'], 'bl fondus', branch(G['fade_call'], G['fade_fn'], True), call(G['fade_call'], 'smooth_fade')),
        (G['lytanim'], 'push {r4-r12,lr}', bytes.fromhex('f05f2de9'), branch(G['lytanim'], syms['hook_lytanim'])),
        (G['camera'], 'push {r0-r11,lr}', bytes.fromhex('ff4f2de9'), branch(G['camera'], syms['hook_camera'])),
        (G['h3d'], 'push {r3-r11,lr}', bytes.fromhex('f84f2de9'), branch(G['h3d'], syms['hook_h3d'])),
        (G['nwmesh'], 'push {r4-r8,lr}', bytes.fromhex('f0412de9'), branch(G['nwmesh'], syms['hook_nwmesh'])),
        (G['setview'], 'add r4,r0,#0x148', bytes.fromhex('524f80e2'), branch(G['setview'], syms['hook_setview'], True)),
        # boutons tenus : interrupteur en jeu (release) ou entrées injectées (essais)
        (G['hid'], 'add r1,r4,#0x98', bytes.fromhex('981084e2'), branch(G['hid'], hid_target, True)),
    ]
    if a.test_input:
        hooks.append((G['touch'], 'mov r0,r4', bytes.fromhex('0400a0e1'), branch(G['touch'], syms['hook_touch'], True)))
        if a.count3d:
            hooks.append((G['cnt3d'], 'push {r3-r7,lr}', bytes.fromhex('f8402de9'), branch(G['cnt3d'], syms['hook_cnt3d'])))
    # données lues par le runtime : vtables (premier mot = pointeur dans .text), gestionnaire
    for k in ('cam_vt', 'skel_vt'):
        v = struct.unpack('<I', orig(G[k]))[0]
        if not (BASE <= v < G['text'][0]):
            sys.exit('%s 0x%08x : ce n est pas une vtable (%08x)' % (k, G[k], v))
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
    FN0, FN1 = 0x004FBF20, 0x004FE788  # zone des essais (initialisation statique écrasée)
    if testbuild:
        if orig(G['test_head'], 8) != bytes.fromhex(DEAD_FN_HEAD):
            sys.exit('zone des essais 0x%08x : octets inattendus (autre version ?)' % FN0)
    elif rt0 != G['text'][0] or any(orig(rt0, len(rtext))):
        sys.exit('runtime hors de la marge de .text')
    recs.append((rt0 - BASE, rtext))
    rdead = open(os.path.join(out, 'rdead.bin'), 'rb').read() if os.path.exists(os.path.join(out, 'rdead.bin')) else b''
    if rdead:
        d0 = syms['__rdead_start']
        if not G['dead'] or d0 != G['dead'][0] or d0 + len(rdead) > G['dead'][1]:
            sys.exit('partie du runtime hors de la fonction inutilisée')
        recs.append((d0 - BASE, rdead))
    hidv = open(os.path.join(out, 'hidv.bin'), 'rb').read() if os.path.exists(os.path.join(out, 'hidv.bin')) else b''
    if hidv:
        if not a.inject or any(orig(G['ro'][0], len(hidv))):
            sys.exit('variante de mesure : code hors de sa zone')
        recs.append((G['ro'][0] - BASE, hidv))
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
    if testbuild and FN0 + len(rtext) + len(testtext) > FN1:
        sys.exit('essais trop gros pour leur zone : %d / %d' % (len(rtext) + len(testtext), FN1 - FN0))
    print('%s : runtime %d octets en 0x%08x%s, crochets %d octets en 0x%08x, marge de .text restante %d ; etat a 0x%08x%s' % (
        G['name'], len(rtext), rt0, (' + %d octets en 0x%08x' % (len(rdead), syms['__rdead_start'])) if rdead else '',
        len(text), t0, G['text'][1] - t0 - len(text), syms['S'], ' (build de test)' if testbuild else ''))
    for k in ('hook_gate', 'hook_camera', 'hook_h3d', 'hook_nwmesh', 'smooth_gate', 'smooth_end', 'S') + (('hook_pad',) if a.test_input else ()):
        print('  %-14s 0x%08x' % (k, syms[k]))
    print('->', a.o)


if __name__ == '__main__':
    main()
