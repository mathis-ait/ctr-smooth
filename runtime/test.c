/*
 * ctr-smooth — code des essais automatisés (builds --test-input / --script),
 * compilé en Thumb (plus compact) et sans flottants. Jamais dans le build distribué.
 */
#include "state.h"

#define SNAP_OFF 0x40000u
#define TRACE_OFF 0x41000u

#ifdef TEST_SCRIPT
#include "build/test_script.h" /* généré par build.py --script */

/* Paramètres de la partie scriptée, posés après l'allocation de la table. */
void test_setup(u8 *tab)
{
    S.script = test_script;
    S.snap_frame = TEST_SNAP_REL;
    S.snap_a = TEST_SNAP_A;
    S.snap_alen = TEST_SNAP_ALEN;
    S.snap_b = 1u;
    S.snap_blen = 0x30u;
    S.snap_dst = tab + SNAP_OFF;
    S.trace = (u32 *)(tab + TRACE_OFF);
    S.trace_n = TEST_SNAP_REL + 1u;
}

/* Essais (Thumb, section des essais) : ancre, graine fixe, instantané, trace.
 * Renvoie l'état « lissage actif » éventuellement basculé à l'ancre. */
u32 test_frame(u32 did_update, u32 on)
{
    if (S.seen && !S.anchor && did_update) {
        S.anchor = S.frame;
        S.enabled = TEST_ENABLED;
        on = S.enabled && S.tab;
        /* graine MT19937 fixe à l'ancre : la graine du jeu dépend de l'instant du
         * démarrage, ce qui rendrait les rencontres différentes d'une partie à l'autre */
        u32 *mt = (u32 *)TEST_SNAP_A;
        mt[1] = 0x5EED1234u;
        for (u32 i = 1; i < 624u; i++)
            mt[i + 1] = 1812433253u * (mt[i] ^ (mt[i] >> 30)) + i;
        mt[0] = 0;
        /* TinyMT global (0x08C55E24, juste avant le MT), consommé pendant la marche */
        u32 *tiny = (u32 *)0x08C55E24u;
        tiny[0] = 0x8F7011EEu;
        tiny[1] = 0xFC78FF1Fu;
        tiny[2] = 0x3793FDFFu;
        tiny[3] = 0x5EED5678u;
    }
    u32 rel = S.anchor ? S.frame - S.anchor : 0xFFFFFFFFu;
    if (S.snap_frame && rel == S.snap_frame && !S.snap_done && S.snap_dst) {
        u8 *d = S.snap_dst;
        for (u32 i = 0; i < S.snap_alen; i++)
            *d++ = ((const u8 *)S.snap_a)[i];
        /* snap_b == 1 : vue de la dernière caméra du terrain */
        const u8 *b = S.snap_b == 1u ? (S.cam ? S.cam + 0x148 : 0) : (const u8 *)S.snap_b;
        for (u32 i = 0; b && i < S.snap_blen; i++)
            *d++ = b[i];
        S.snap_done = 1u;
    }
    if (S.trace && rel < S.trace_n) {
        S.trace[2 * rel] = S.snap_a ? *(const u32 *)S.snap_a : 0;
        S.trace[2 * rel + 1] = S.cam ? *(const u32 *)(S.cam + 0x148 + 12) : 0;
    }
    return on;
}
#endif

/* Builds de test : compte les passes de scène 3D par type d'image. */
__attribute__((section(".text.testcnt"))) void smooth_cnt3d(void)
{
    if (S.upd)
        S.c3d_u++;
    else
        S.c3d_n++;
}

/* Builds de test : boutons tenus = manette + S.vpad + script. Le script a deux
 * parties : images absolues (menus, jusqu'à l'ancre), séparateur 0xFFFF0000,
 * puis images relatives à l'ancre (apparition du joueur), fin 0xFFFFFFFF. */
u32 smooth_pad(u32 hold, u8 *dev)
{
    const u32 *p = S.script;
    u32 mask = 0;
    if (p) {
        u32 t = S.frame;
        if (S.anchor) {
            while (*p != 0xFFFF0000u)
                p += 2;
            p += 2;
            t = S.frame - S.anchor;
        }
        const u32 *last = 0;
        for (; *p < 0xFFFF0000u && *p <= t; p += 2)
            last = p;
        if (last) {
            mask = last[1];
            /* impulsions : bit 31, boutons (16 bits), période (bits 16-23), durée (24-30) */
            if (mask & 0x80000000u) {
                u32 period = (mask >> 16) & 0xFFu, dur = (mask >> 24) & 0x7Fu, r = t - last[0];
                while (period && r >= period)
                    r -= period; /* pas de division matérielle sur ARM11 */
                mask = period && r < dur ? mask & 0xFFFFu : 0;
            }
        }
    }
    /* stick : nn::hid::PadStatus { hold, trigger, release, stick x, stick y } en dev+0x78 */
    if (S.vstick) {
        *(u32 *)(dev + 0x84) = S.vstick;
    }
    S.pad = hold | S.vpad | mask;
    return S.pad;
}

/* Builds de test (--probe ADDR) : compteur d'appels par sonde et par parité d'image. */
__attribute__((section(".text.testcnt"))) void smooth_probe(u32 i)
{
    S.pc[2u * i + (S.upd ? 0u : 1u)]++;
}

/* Builds de test : écran tactile (nn::hid::TouchPanelStatus { u16 x, u16 y, u8 touch } en dev+0x98). */
void smooth_touch(u8 *dev)
{
    if (S.vtouch & 0x80000000u) {
        *(unsigned short *)(dev + 0x98) = (unsigned short)(S.vtouch & 0x1FFu);
        *(unsigned short *)(dev + 0x9A) = (unsigned short)((S.vtouch >> 16) & 0xFFu);
        dev[0x9C] = 1;
    }
}
