/*
 * ctr-smooth — runtime d'interpolation de rendu (Pokémon Rubis Oméga EUR v1.0).
 *
 * Principe (PRD option B) : la logique tourne à 30 Hz sans aucune modification ;
 * le jeu dessine à chaque VBlank. Chaque matrice consommée par le rendu est suivie
 * (clé = adresse) : ses deux dernières valeurs distinctes P et C, et les images tp
 * et tc où elles sont apparues. Tant que l'image courante f vérifie f - tc + 1 < T
 * (T = tc - tp, cadence propre de la matrice), elle est remplacée le temps du
 * dessin par P + (C - P) * (f - tc + 1) / T, puis restaurée (C).
 *   - contenu à 30 Hz (terrain, T = 2) : 50 % sur l'image de l'update, puis C ;
 *   - contenu à 15 Hz (scène de combat, T = 4) : 25 %, 50 %, 75 %, puis C.
 * Le terrain n'a aucune latence ajoutée ; un contenu à 15 Hz atteint C deux
 * images (33 ms) plus tard que le jeu d'origine. L'état du jeu est intact entre
 * deux dessins.
 *
 * Le runtime n'écrit que dans sa table (mémoire allouée au démarrage) et, le
 * temps d'un dessin, dans les matrices qu'il restaure avant la fin de l'image.
 *
 * Contraintes : ARMv6K (ARM11 MPCore, pas de Thumb-2), VFPv2, pas de libc ;
 * le code tient dans la marge de fin de .text (2,5 Ko), l'état dans la marge
 * de fin de .bss (page 0x006AE620-0x006AF000, hors fichier : initialisé au
 * premier appel), la table dans un bloc alloué par svcControlMemory, les
 * données des essais dans la marge de fin de .rodata.
 */
#include "state.h"

#define TAB_BITS 11u
#define TAB_N (1u << TAB_BITS)
#define TAB_PROBES 16u
#define STALE_FRAMES 120u

/* Zones de la mémoire allouée (0x40000 octets) */
#define TAB_BYTES (TAB_N * sizeof(Entry)) /* 0x40000 */
#define SNAP_OFF 0x40000u
#define TRACE_OFF 0x41000u
#define MAX_PERIOD 8u   /* au-delà : changement isolé, mélangé sur un tick (T = 2) */
#define UNSEEN_FRAMES 4u
#define PAD_COMBO 0x204u /* L (0x200) + Select (0x4) ; sans R : L + R + Start redémarre le jeu */

struct Entry {
    u32 key;        /* adresse de la matrice dans la mémoire du jeu (0 = libre) */
    u32 obs;        /* dernière image où la matrice a été lue (0 = entrée neuve) */
    u32 swp;        /* image où la matrice a été remplacée par le mélange */
    u32 seen;       /* image où l'objet dont c'est la 1re matrice a été traité */
    u32 tc, tp;     /* images d'apparition de cur et de prev (tp = 0 : inconnue) */
    float prev[12]; /* avant-dernière valeur distincte (P) */
    float cur[12];  /* dernière valeur lue (C), restaurée en fin d'image */
    float dlast;    /* écart de translation du dernier changement (même refusé) */
    u32 rsv;
};
_Static_assert(sizeof(Entry) == 128, "Entry : 128 octets (table 0x40000)");



__attribute__((section(".state"), used)) State S;

/* hooks.S lit S.extra à cet offset */
_Static_assert(__builtin_offsetof(State, extra) == 0x9C, "State.extra doit rester en 0x9C");
/* hooks.S (hook_hid) écrit S.pad à cet offset */
_Static_assert(__builtin_offsetof(State, pad) == 0xC8, "State.pad doit rester en 0xC8");

#ifdef TEST_SCRIPT
u32 test_frame(u32 did_update, u32 on); /* test.c (Thumb) */
void test_setup(u8 *tab);
#endif

static u32 svc_alloc(u32 addr, u32 size, u32 *out)
{
    register u32 r0 __asm__("r0") = 3u;  /* MEMOP_ALLOC */
    register u32 r1 __asm__("r1") = addr;
    register u32 r2 __asm__("r2") = 0u;
    register u32 r3 __asm__("r3") = size;
    register u32 r4 __asm__("r4") = 3u;  /* MEMPERM_READ | MEMPERM_WRITE */
    __asm__ volatile("svc 0x01" : "+r"(r0), "+r"(r1), "+r"(r2), "+r"(r3) : "r"(r4) : "memory", "r12", "lr");
    *out = r1;
    return r0;
}

static Entry *find(u32 key)
{
    Entry *t = S.tab, *cand = 0;
    u32 h = (key * 2654435761u) >> (32u - TAB_BITS);
    for (u32 i = 0; i < TAB_PROBES; i++) {
        Entry *e = &t[(h + i) & (TAB_N - 1u)];
        if (e->key == key)
            return e;
        if (!cand && (e->key == 0 || S.frame - e->obs > STALE_FRAMES))
            cand = e;
        if (e->key == 0)
            break;
    }
    if (cand) {
        cand->key = key;
        cand->obs = 0;
        cand->swp = 0;
        cand->seen = 0;
    } else {
        S.n_miss++;
    }
    return cand;
}

static inline float fabs_(float x) { return x < 0.0f ? -x : x; }

/* Point d'interception commun : `m` est une matrice 3x4 que le rendu va lire.
 * camera = 1 : seuil de rotation serré, une coupure est comptée à part. */
static void smooth(float *m, u32 camera)
{
    if (!S.interp)
        return;
    Entry *e = find((u32)m);
    if (!e || e->obs == S.frame)
        return;
    u32 f = S.frame;
    /* Pas lue depuis plus de UNSEEN_FRAMES images (fondu, changement de carte, objet
     * masqué) : son adresse peut appartenir à un autre objet, on repart sans mélange. */
    if (e->obs == 0 || f - e->obs > UNSEEN_FRAMES) {
        for (u32 i = 0; i < 12; i++)
            e->prev[i] = e->cur[i] = m[i];
        e->obs = e->tc = f;
        e->tp = 0;
        e->dlast = 0.0f;
        S.n_rec++;
        return;
    }
    e->obs = f;
    u32 changed = 0;
    for (u32 i = 0; i < 12; i++)
        if (m[i] != e->cur[i])
            changed = 1;
    if (changed) {
        /* Seuils : la translation est jugée à l'échelle de la scène (le terrain est
         * en milliers d'unités), plafonnée par jump_t ; rotation/échelle à part. */
        float mag = 0.0f, dt = 0.0f, dr = 0.0f;
        for (u32 i = 0; i < 12; i++) {
            float d = fabs_(m[i] - e->cur[i]);
            if ((i & 3u) == 3u) {
                float a = fabs_(m[i]);
                if (a > mag)
                    mag = a;
                if (d > dt)
                    dt = d;
            } else if (d > dr) {
                dr = d;
            }
        }
        float lim_t = S.jump_rel * mag + S.jump_min;
        if (lim_t > S.jump_t)
            lim_t = S.jump_t;
        /* Un grand déplacement qui prolonge le mouvement du changement précédent (Envol,
         * vélo, caméra qui suit) est mélangé ; un saut surgi d'un coup (téléportation,
         * réapparition, coupure) ne l'est pas. */
        u32 tjump = dt > lim_t && dt > 2.0f * e->dlast + lim_t;
        e->dlast = dt;
        u32 jump = tjump || dr > (camera ? S.jump_rcam : S.jump_r);
        for (u32 i = 0; i < 12; i++) {
            e->prev[i] = jump ? m[i] : e->cur[i];
            e->cur[i] = m[i];
        }
        e->tp = e->tc;
        e->tc = f;
        S.n_rec++;
        if (jump) {
            S.n_jump++;
            if (camera)
                S.n_cut++;
            return;
        }
    }
    u32 period = e->tc - e->tp;
    if (e->tp == 0 || period > MAX_PERIOD)
        period = 2u;
    u32 k = f - e->tc + 1u;
    if (k >= period)
        return;
    float a = (float)k / (float)period;
    for (u32 i = 0; i < 12; i++)
        m[i] = e->prev[i] + (e->cur[i] - e->prev[i]) * a;
    e->swp = f;
    S.n_swap++;
}

/* Lisse un tableau de n matrices 3x4 une seule fois par image (un même modèle est
 * rendu maillage par maillage : sans cette garde, ses os seraient revus à chaque fois). */
static void smooth_array(float *mats, u32 n)
{
    if (!S.interp || !mats || n == 0 || n > 256u)
        return;
    Entry *e0 = find((u32)mats);
    if (!e0 || e0->seen == S.frame)
        return;
    for (u32 i = 0; i < n; i++)
        smooth(mats + i * 12u, 0);
    e0->seen = S.frame;
}

/* Caméras des yeux (3D stéréoscopique, active en intérieur) : le module de terrain
 * les recalcule pendant update() à partir de la caméra de base (0x00377984, puis
 * SetViewMatrix 0x00392F90 sur chaque œil) ; le rendu les lit telles quelles, sans
 * passer par hook_camera. Leurs vues sont lissées au début de chaque dessin.
 * Une caméra n'est retenue que si sa vue a été posée au tick courant ou au précédent
 * (frame - eye_f <= 2) : une caméra libérée entre-temps n'est jamais touchée. */
#define NW_CAMERA_VT 0x005DBAB8u
static void smooth_eyes(void)
{
    for (u32 i = 0; i < 4u; i++) {
        u8 *c = S.eye[i];
        if (c && S.frame - S.eye_f[i] <= 2u && *(u32 *)c == NW_CAMERA_VT) {
            smooth((float *)(c + 0x148), 1);
            smooth((float *)(c + 0x178), 1);
            S.n_eye++;
        }
    }
}

/* SetViewMatrix (0x00392FB4, r0 = nw::gfx::Camera) : retient la caméra. */
void smooth_setview(u8 *cam)
{
    if (S.magic != MAGIC || !cam)
        return;
    u32 slot = 0, oldest = 0xFFFFFFFFu;
    for (u32 i = 0; i < 4u; i++) {
        if (S.eye[i] == cam) {
            slot = i;
            break;
        }
        if (S.eye_f[i] < oldest)
            oldest = S.eye_f[i], slot = i;
    }
    S.eye[slot] = cam;
    S.eye_f[slot] = S.frame;
}

#ifdef COUNT3D
/* Essais : images réellement présentées sur un écran (GSP, framebuffer info : index puis
 * deux entrées de 0x1C octets, adresse du tampon gauche en +4) ; c[0] index, c[1] images,
 * c[2] empreinte, c[3] images identiques à la précédente. */
static void lcd_probe(const volatile u8 *info, u32 *c)
{
    u32 idx = info[0];
    if (idx != c[0] && idx < 2u) {
        const volatile u32 *fb = *(const volatile u32 *const volatile *)(info + 8u + 0x1Cu * idx);
        u32 hsh = 2166136261u;
        for (u32 k = 0; k < 0x38400u / 4u; k += 97u) /* 320 x 240 x 3 : couvre les deux écrans */
            hsh = (hsh ^ fb[k]) * 16777619u;
        c[1]++;
        if (hsh == c[2])
            c[3]++;
        c[2] = hsh;
    }
    c[0] = idx;
}
#endif

/* Remplace la décision « dessiner ? » de runEachFrame (0x0010E530).
 * Renvoie 1 pour sauter le dessin (comportement d'origine), 0 pour dessiner. */
u32 smooth_gate(const u8 *mgr, u32 did_update)
{
    u32 mode = mgr[0x0D];
    if (S.magic != MAGIC) {
        u32 *w = (u32 *)&S;
        for (u32 i = 0; i < sizeof(S) / 4u; i++)
            w[i] = 0;
        S.magic = MAGIC;
        S.enabled = 1u;
        S.jump_t = 48.0f;
        S.jump_r = 0.7f;
        S.jump_rel = 0.25f;
        S.jump_min = 0.5f;
        S.jump_rcam = 0.25f;
        S.tab_addr = 0x0A000000u;
        S.tab_size = 0x4A000u; /* table 0x40000 + essais (instantané, trace de 4 000 images) */
#ifdef TEST_SCRIPT
        S.enabled = 0u; /* le mode testé s'applique à partir de l'ancre */
#endif
    }
    if (!S.tab && !S.failed) {
        u32 addr = 0, rc = svc_alloc(S.tab_addr, S.tab_size, &addr);
        if (rc == 0 && addr) {
            S.tab = (Entry *)addr;
#ifdef TEST_SCRIPT
            test_setup((u8 *)addr);
#endif
        } else {
            S.failed = rc ? rc : 1u;
        }
    }
    /* L + Select tenus une seconde (60 images) : lissage coupé ou rétabli. La table
     * est vidée au rétablissement : aucune valeur d'avant la coupure n'est mélangée. */
    if ((S.pad & PAD_COMBO) == PAD_COMBO) {
        if (!S.combo_f)
            S.combo_f = S.frame + 1u;
        else if (S.frame + 1u - S.combo_f == 60u) {
            S.enabled ^= 1u;
            if (S.enabled && S.tab)
                for (u32 i = 0; i < TAB_N; i++)
                    S.tab[i].key = 0;
        }
    } else {
        S.combo_f = 0;
    }
    u32 on = S.enabled && S.tab;
    /* Transition qui change d'état à ce tick (contextes *(0x0062F830) + 0x38 / + 0x3C :
     * état +0x0C, drapeaux +0x44 (deux octets bas) et +0x48 ; par exemple 6 -> 0xC au
     * début du fondu de sortie, +0x45 et +0x48 à 1 au début du balayage d'entrée) : le jeu
     * renouvelle l'image capturée qu'affiche la transition lors de son propre dessin,
     * au tick suivant. Un dessin ajouté montrerait l'ancienne capture (image blanche en
     * entrant dans un bâtiment, extérieur une image en sortant) : pas de dessin ajouté. */
    const u8 *tm = *(const u8 *const *)0x0062F830u;
    u32 tchg = 0;
    for (u32 i = 0; i < 2u; i++) {
        const u8 *c = tm ? *(const u8 *const *)(tm + 0x38u + 4u * i) : 0;
        u32 st = c ? *(const u32 *)(c + 0x0C) ^ (*(const u32 *)(c + 0x44) & 0xFFFFu) << 8 ^
                         *(const u32 *)(c + 0x48) << 24 : 0xFFFFFFFFu;
        if (st != S.tstate[i])
            tchg = 1;
        S.tstate[i] = st;
    }
    if (on && mode && did_update && tchg)
        S.n_tskip++;
    u32 skip = (mode && did_update) && (!on || tchg);
    /* Le jeu saute lui-même le prochain dessin après une image trop lente
     * ([[mgr+0x1C]+0x1FE], testé juste après cette fonction) : pas d'interpolation. */
    const u8 *gfx = *(const u8 *const *)(mgr + 0x1C);
    if (!skip && gfx && gfx[0x1FE])
        S.n_skip++, skip = 2u;
    S.frame++;
    S.upd = did_update;
#ifdef COUNT3D
    lcd_probe((const volatile u8 *)0x10002200u, &S.lcd_idx);
    lcd_probe((const volatile u8 *)0x10002240u, &S.lcd2_idx);
#endif
#ifdef TEST_SCRIPT
    on = test_frame(did_update, on);
#endif
    /* interp : ce dessin passe par le lissage (toutes les images dessinées quand
     * le lissage est actif ; le jeu en mode 60 Hz donne naturellement T = 1). */
    S.interp = on && !skip;
    S.extra = on && mode && did_update && !skip;
    if (on && mode && did_update && !skip)
        S.n_interp++;
    if (S.interp)
        smooth_eyes();
    return skip == 1u;
}

/* Fin du dessin (0x0010E61C) : restaure les matrices remplacées (valeur C). */
void smooth_end(void)
{
    if (!S.tab || !S.interp)
        return;
    Entry *e = S.tab;
    for (u32 i = 0; i < TAB_N; i++, e++) {
        if (e->swp == S.frame) {
            float *m = (float *)e->key;
            for (u32 k = 0; k < 12; k++)
                m[k] = e->cur[k];
        }
    }
    S.lastrec = S.frame;
    S.interp = 0;
    S.extra = 0;
}

/* Transitions et fondus (0x0011CB60, gestionnaire *(0x0062F830)) : ils avancent au
 * dessin, pas à l'update. Sur le dessin ajouté, on fige l'avance de chaque contexte
 * (octet +0x46, testé par 0x0014BF90 qui dessine quand même) et on neutralise le rappel
 * de changement de scène (+0x40, appelé à chaque dessin pendant une transition) :
 * fondus et chargements gardent leur durée d'origine. */
typedef void (*Fn0)(void);
void smooth_fade(void)
{
    u8 *mgr = *(u8 **)0x0062F830u;
    if (!S.extra || !mgr) {
        ((Fn0)0x0011CB60u)();
        return;
    }
    u8 *c0 = *(u8 **)(mgr + 0x38), *c1 = *(u8 **)(mgr + 0x3C);
    u8 p0 = c0 ? c0[0x46] : 0, p1 = c1 ? c1[0x46] : 0;
    u32 cb = *(u32 *)(mgr + 0x40);
    if (c0)
        c0[0x46] = 1;
    if (c1)
        c1[0x46] = 1;
    *(u32 *)(mgr + 0x40) = 0;
    ((Fn0)0x0011CB60u)();
    if (c0)
        c0[0x46] = p0;
    if (c1)
        c1[0x46] = p1;
    if (*(u32 *)(mgr + 0x40) == 0)
        *(u32 *)(mgr + 0x40) = cb;
    if (cb)
        S.n_fade++;
}

/* nw::gfx::Camera : vue (+0x148) et son inverse (+0x178). */
#ifdef COUNT3D
#define TCOUNT(k) (S.tc[2u * (k) + (S.upd ? 0u : 1u)]++)
#else
#define TCOUNT(k) ((void)0)
#endif

void smooth_camera(u8 *cam)
{
    TCOUNT(0);
#ifdef COUNT3D
    {
        u32 i = S.tlog_i++ & 15u;
        S.tlog[2u * i] = S.frame << 1 | S.upd;
        S.tlog[2u * i + 1u] = (u32)cam;
    }
#endif
    if (!S.tab || !cam)
        return;
    S.cam = cam;
    smooth((float *)(cam + 0x148), 1);
    smooth((float *)(cam + 0x178), 1);
}

/* Modèle H3D (gfl::grp::g3d) : matrices monde des os, *(+0x4C)[0 .. *(+0x40)[. */
void smooth_h3d(u8 *model)
{
    TCOUNT(1);
    if (!S.tab || !model)
        return;
    u32 n = *(u32 *)(model + 0x40);
#ifdef TEST_SCRIPT
    /* ancre des essais : le joueur sur le terrain (squelette de 50 os, coordonnees de
     * terrain > 1000 ; la cinematique d ouverture a aussi des squelettes de 50 os) */
    float *b2 = *(float **)(model + 0x4C);
    if (n == 50u && b2 && (b2[27] > 1000.0f || b2[27] < -1000.0f))
        S.seen = 1u;
#endif
    smooth_array(*(float **)(model + 0x4C), n);
}

/* Modèle nw::gfx : matrice monde (+0x8C) ; pour un nw::gfx::SkeletalModel
 * (vtable 0x005DB47C), les poses du StandardSkeleton (*(+0x220)) : monde (+0x3C)
 * et skinning (+0x4C), chacune { allocateur, matrices, ?, nombre }. */
void smooth_nwmodel(u8 *model)
{
    TCOUNT(2);
    if (!S.tab || !model)
        return;
    smooth((float *)(model + 0x8C), 0);
    if (*(u32 *)model == 0x005DB47Cu) {
        u8 *sk = *(u8 **)(model + 0x220);
        if (sk) {
            smooth_array(*(float **)(sk + 0x40), *(u32 *)(sk + 0x48));
            smooth_array(*(float **)(sk + 0x50), *(u32 *)(sk + 0x58));
        }
    }
}

