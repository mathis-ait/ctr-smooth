/* Placement dans les marges de code.bin de Rubis Oméga EUR v1.0 :
 * crochets : fin de .text 0x00579604 .. 0x0057A000 (trampolines de hooks.S)
 * runtime  : fonction morte 0x004FBF20 .. 0x004FE790 (smooth.c, puis code des essais)
 * état  : fin de .bss    0x006AE620 .. 0x006AF000 (inscriptible, hors fichier :
 *         le .bss suit .data sans alignement, 0x0062F9F4 + 0x7EC2C = 0x006AE620 ;
 *         0x006AEFF0.. est réservé aux compteurs de trace) */
MEMORY
{
    CAVE_TEXT (rx) : ORIGIN = 0x00579610, LENGTH = 0x9F0
    CAVE_DATA (rw) : ORIGIN = 0x006AE640, LENGTH = 0x980
    CAVE_RO   (r)  : ORIGIN = 0x005EBA20, LENGTH = 0x5E0
    /* fonction morte de 10 Ko (aucune reference, aucun litteral, non exportee par
     * static.crs) : corps du runtime (smooth.c), puis code des builds de test */
    CAVE_FN   (rx) : ORIGIN = 0x004FBF20, LENGTH = 0x2870
}

SECTIONS
{
    .rtext : {
        *smooth.o(.text .text.*)
        *smooth.o(.rodata .rodata.[!t]*)
    } > CAVE_FN

    .testtext : {
        *(.text.testpad)
        *(.text.testcnt)
        *test.o(.text .text.*)
    } > CAVE_FN

    .text : {
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
