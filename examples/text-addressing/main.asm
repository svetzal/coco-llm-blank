* Set up a CoCo 3 high-resolution text screen at a chosen physical address.
*
* One physical address gives two values. The CPU writes the screen through
* an MMU page, and the GIME shows it from a display address. Calculate both
* from the same physical address. Then the program works on 128 KiB and on
* 512 KiB.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it fills the screen with a test
* card of space characters on black and white backgrounds, and holds it for
* the check. A project does not need the context.
*
* Sources:
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90 bits. PDF 12: $FF98 and $FF99 bits.
*     PDF 13: $FF9C, and $FF9D/$FF9E hold physical address bits 18..3.
*     PDF 15-16: MMU $FFA0-$FFA7, data bits 5..0 = address bits 18..13.
*     PDF 17: palette $FFB0-$FFBF; $00 black, $3F white (RGB).
*     PDF 18: HRES and CRES for 32, 40 and 80 characters.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3 (1987):
*     PDF 29: on 128 KiB, address bits 18 and 17 are not used.
*     PDF 31: the buffer is rows of character pairs, from the upper left.
*     PDF 32-34: $FF99 rows; $FF9C scroll; $FF9F offset; byte 0 is the
*       character code, byte 1 the attribute.
*     PDF 35: attribute colours select palette 8-15 and 0-7.
*     PDF 36 Table 4-8: HRES, CRES and buffer size for 32/40/64/80 columns.
*
* >>> EXAMPLE 1 of 3: the values for each width, and the screen address.
* Select the width with one assembler define. coco.toml has a variant for
* each. $FF99: LPF=00 (24 rows), HRES2..0, CRES1..0 = x1 (attributes).
*   (none) 40 columns  80 bytes/row  1920 bytes  $FF99 = %00000101
*   C32    32 columns  64 bytes/row  1536 bytes  $FF99 = %00000001
*   C64    64 columns 128 bytes/row  3072 bytes  $FF99 = %00010001
*   C80    80 columns 160 bytes/row  3840 bytes  $FF99 = %00010101
        ifdef C32
COLS    equ 32
RES     equ %00000001
WIDTHSET equ 1
        endc
        ifdef C64
COLS    equ 64
RES     equ %00010001
WIDTHSET equ 1
        endc
        ifdef C80
COLS    equ 80
RES     equ %00010101
WIDTHSET equ 1
        endc
        ifndef WIDTHSET
COLS    equ 40
RES     equ %00000101
        endc
ROWS    equ 24
* The physical screen address. It must be a multiple of 8 and the screen
* must not cross an 8 KiB page. An address below $20000 is the same RAM
* on 128 KiB and 512 KiB.
SCREEN  equ $0C000
PAGE    equ SCREEN/$2000            MMU data: address bits 18..13
BASEHI  equ (SCREEN/$800)&$FF       $FF9D: address bits 18..11
BASELO  equ (SCREEN/8)&$FF          $FF9E: address bits 10..3
* The CPU window that shows the page: CPU $4000-$5FFF is MMU entry $FFA2.
WINDOW  equ $4000
CPUSCR  equ WINDOW+(SCREEN&$1FFF)
* Attribute byte: bit 7 blink, bit 6 underline, bits 5..3 foreground
* (palette 8-15), bits 2..0 background (palette 0-7).
BLACK   equ %00000000               foreground palette 8, background 0
WHITE   equ %00000001               foreground palette 8, background 1
* <<< END EXAMPLE

        org $3000
* >>> EXAMPLE 2 of 3: map the screen page into the CPU window.
* The window stays mapped. The program writes the screen at CPUSCR.
start   lda #PAGE
        sta $FFA2
* <<< END EXAMPLE

* --- CONTEXT: a test card. Each cell holds a space. The border cells and
* the cells where column = row have a white background. The others are black.
        ldx #CPUSCR
        clr rowv
row     clr colv
cell    lda #WHITE
        ldb rowv
        beq put
        cmpb #ROWS-1
        beq put
        ldb colv
        beq put
        cmpb #COLS-1
        beq put
        cmpb rowv
        beq put
        lda #BLACK
put     ldb #' '
        stb ,x+                     byte 0: the character code
        sta ,x+                     byte 1: the attribute
        inc colv
        ldb colv
        cmpb #COLS
        blo cell
        inc rowv
        ldb rowv
        cmpb #ROWS
        blo row

* >>> EXAMPLE 3 of 3: show the screen.
* Palette: background 0 black, background 1 white, foreground 8 white.
        clr $FFB0
        lda #$3F
        sta $FFB1
        sta $FFB8
* $FF90: native mode, MMU on, no GIME interrupt outputs, constant RAM at
* $FExx, standard SCS, 32 KiB internal ROM. Write each register in full.
        lda #%01001110
        sta $FF90
* $FF98: BP=0 text, LPR=011 eight lines for each character row.
        lda #%00000011
        sta $FF98
        lda #RES
        sta $FF99
* $FF9C: no vertical scroll.
        clr $FF9C
* $FF9D and $FF9E: the physical display address.
        lda #BASEHI
        sta $FF9D
        lda #BASELO
        sta $FF9E
* $FF9F: normal buffer width (HE=0) and no horizontal offset.
        clr $FF9F
* <<< END EXAMPLE

* --- CONTEXT: hold the screen. The check takes its snapshot at this label.
* A project replaces this loop with its own main loop.
ready   bra ready

* --- CONTEXT: the test card's row and column counters.
rowv    fcb 0
colv    fcb 0
        end start
