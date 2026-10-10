/* Placement dans les marges de code.bin (Rubis Oméga et Saphir Alpha EUR 1.0) :
 * runtime et crochets : fin de .text 0x00579610 .. 0x0057A000 (build distribué : smooth.c puis
 *            hooks.S, 2 544 octets au plus) ;
 * builds de test : smooth.c et le code des essais dans 0x004FBF20 .. 0x004FE788 (RTEXT_REGION
 *            = CAVE_FN). ATTENTION : cette « fonction morte » est une initialisation statique
 *            appelée au démarrage ; l'écraser casse l'initialisation d'un tableau (0x0062FC34)
 *            et fait exécuter le runtime au démarrage. Réservé au bac à sable.
 * état  : fin de .bss    0x006AE620 .. 0x006AF000 (inscriptible, hors fichier :
 *         le .bss suit .data sans alignement, 0x0062F9F4 + 0x7EC2C = 0x006AE620 ;
 *         0x006AEFF0.. est réservé aux compteurs de trace) */
MEMORY
{
    CAVE_TEXT (rx) : ORIGIN = 0x00579610, LENGTH = 0x9F0
    CAVE_DATA (rw) : ORIGIN = 0x006AE640, LENGTH = 0x980
    CAVE_RO   (r)  : ORIGIN = 0x005EBA20, LENGTH = 0x5E0
    /* builds de test uniquement (voir plus haut) */
    CAVE_FN   (rx) : ORIGIN = 0x004FBF20, LENGTH = 0x2868
}

SECTIONS
{
    .rtext : {
        __rtext_start = .;
        *smooth.o(.text .text.*)
        *smooth.o(.rodata .rodata.[!t]*)
    } > RTEXT_REGION

    .testtext : {
        *(.text.testpad)
        *(.text.testcnt)
        *test.o(.text .text.*)
    } > CAVE_FN

    .text : {
        __text_start = .;
        *(.text.hooks)
        *(.text .text.*)
        *(.rodata .rodata.[!t]*)
    } > CAVE_TEXT

    .testro : {
        *(.rodata.testdata)
    } > CAVE_RO

    .data (NOLOAD) : {
        *(.state)
        *(.data .data.*)
        *(.bss .bss.* COMMON)
    } > CAVE_DATA

    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.attributes) *(.comment) *(.note*) }
}
