@ Trampolines ctr-smooth (ARM, ARMv6K). Chaque crochet d'entrée remplace la
@ première instruction (un push, indépendant de la position) de la fonction
@ visée par « b hook_xxx » ; le trampoline appelle le C en préservant r0-r3, r12,
@ lr et d0-d7 (paramètres flottants possibles en ABI hard-float), rejoue
@ l'instruction déplacée puis revient à l'instruction suivante.

    .syntax unified
    .arm
    .section .text.hooks, "ax"

@ 0x0010E530 « ldrb r0,[r4,#0xd] » devient « bl hook_gate » ; r4 = gestionnaire
@ d'images, r6 = 1 si update() a tourné sur cette image. Retour : r0 = sauter.
    .global hook_gate
hook_gate:
    mov     r0, r4
    mov     r1, r6
    b       smooth_gate

@ 0x00375EA8 (copie de la vue avant le parcours de la file de rendu) :
@ la caméra est le 4e argument de pile, [sp+0xC] à l'entrée.
    .global hook_camera
hook_camera:
    push    {r0-r3, r12, lr}
    vpush   {d0-d7}
    ldr     r0, [sp, #(24 + 64 + 0xC)]
    bl      smooth_camera
    vpop    {d0-d7}
    pop     {r0-r3, r12, lr}
    push    {r0-r11, lr}
    b       0x00375EAC

@ 0x0039B338 (rendu d'un maillage H3D) : r0 = modèle.
    .global hook_h3d
hook_h3d:
    push    {r0-r3, r12, lr}
    vpush   {d0-d7}
    bl      smooth_h3d
    vpop    {d0-d7}
    pop     {r0-r3, r12, lr}
    push    {r3-r11, lr}
    b       0x0039B33C

@ 0x0014D618 (avance des animations de l'interface 2D, appelée au dessin) :
@ « push {r4-r12,lr} » devient « b hook_lytanim ». Sur le dessin ajouté (S.extra),
@ retour immédiat : les animations gardent leur vitesse d'origine.
    .global hook_lytanim
hook_lytanim:
    ldr     r12, =S
    ldr     r12, [r12, #0x9C]
    cmp     r12, #0
    bxne    lr
    push    {r4-r12, lr}
    b       0x0014D61C
    .ltorg

@ 0x002EC354 (nw::gfx MeshRenderer::RenderMesh) : r2 = modèle.
    .global hook_setview
hook_setview:                   @ bl depuis 0x00392FB4 (add r4,r0,#0x148) ; r0 = nw::gfx::Camera
    push    {r0-r3, r12, lr}
    bl      smooth_setview
    pop     {r0-r3, r12, lr}
    add     r4, r0, #0x148
    bx      lr

@ 0x0036FB34, juste après nn::hid::PadReader::ReadLatest dans gfl::ui::CTR_DeviceManager::Main :
@ « bl hook_hid ». Copie les boutons tenus ([r4+0x78]) dans S.pad (interrupteur en jeu).
@ Les builds de test remplacent ce crochet par hook_pad (entrées injectées).
    .global hook_hid
hook_hid:
    ldr     r12, =S
    ldr     r0, [r4, #0x78]
    str     r0, [r12, #0xC8]
    add     r1, r4, #0x98
    bx      lr

@ Variante de mesure (build.py --inject) : comme hook_hid, plus les boutons injectés par le stub
@ GDB (S.vpad). Sans code d'essai : utilisable avec le build distribué, dans les deux jeux.
    .section .text.hidv, "ax"
    .global hook_hidv
hook_hidv:
    ldr     r12, =S
    ldr     r0, [r4, #0x78]
    ldr     r1, [r12, #0x40]
    orr     r0, r0, r1
    str     r0, [r4, #0x78]
    str     r0, [r12, #0xC8]
    add     r1, r4, #0x98
    bx      lr
    .ltorg
    .section .text.hooks, "ax"

    .global hook_nwmesh
hook_nwmesh:
    push    {r0-r3, r12, lr}
    vpush   {d0-d7}
    mov     r0, r2
    bl      smooth_nwmodel
    vpop    {d0-d7}
    pop     {r0-r3, r12, lr}
    push    {r4-r8, lr}
    b       0x002EC358

@ Builds de test uniquement (build.py --test-input) : 0x0036FB34, juste après
@ nn::hid::PadReader::ReadLatest dans gfl::ui::CTR_DeviceManager::Main, devient
@ « bl hook_pad ». r4 = gestionnaire, mot « boutons tenus » en [r4+0x78].
@ Ajoute S.vpad (écrit par le stub GDB) puis rejoue « add r1, r4, #0x98 ».
    .section .text.testpad, "ax"
@ Builds de test (--count3d) : 0x0038CEA4 (passe de scène 3D) « push {r3-r7,lr} » -> compteur.
    .section .text.testcnt, "ax"
    .global hook_cnt3d
hook_cnt3d:
    push    {r0-r3, r12, lr}
    bl      smooth_cnt3d
    pop     {r0-r3, r12, lr}
    push    {r3-r7, lr}
    b       0x0038CEA8

    .section .text.testpad, "ax"
    .global hook_pad
hook_pad:
    push    {r4, lr}
    ldr     r0, [r4, #0x78]
    mov     r1, r4
    blx     smooth_pad
    str     r0, [r4, #0x78]
    add     r1, r4, #0x98
    pop     {r4, pc}

@ Builds de test : 0x0036FB40 (« mov r0, r4 », juste après TouchPanelReader::ReadLatest)
@ devient « bl hook_touch » : écran tactile injecté en [r4+0x98] (x, y, appui).
    .global hook_touch
hook_touch:
    push    {r0-r3, r12, lr}
    mov     r0, r4
    blx     smooth_touch
    pop     {r0-r3, r12, lr}
    mov     r0, r4
    bx      lr
