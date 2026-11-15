* Set up a VDG full-graphics screen on a CoCo 1/2 (MC6847 VDG, MC6883 SAM).
*
* Three steps select a screen. The order does not matter for a still picture.
*   1. SAM display offset F6..F0: the screen start address / 512.
*   2. SAM display mode V2..V0: how the SAM steps through screen memory.
*   3. PIA $FF22 bits 7..3: VDG mode (A/G, GM2, GM1, GM0) and colour set (CSS).
*      Bits 2..0 belong to other hardware. Keep them.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it draws a test picture and holds
* it for the check. A project does not need the context.
*
* Sources:
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 11: SAM control. Write to the even address to clear a bit,
*       to the odd address to set it. $FFC6-$FFD3 is the display offset.
*     PDF 14: $FF22 bit 3 = CSS, bits 4..7 = GM0, GM1, GM2, A/G.
*     PDF 15: SAM bit addresses; offset in 1/2K units; V bits per mode.
*     PDF 30: the size of each mode; pixel width and height in clocks.
*     PDF 31 Table 1: SAM V2..V0 and $FF22 bits for each mode.
*       $FF22 bits 2..0 are "do not change".
*   Motorola, MC6847 datasheet, PDF 18-21: sizes, colours, pixel order.
*
* >>> EXAMPLE 1 of 3: the values for each mode.
* Select the mode with one assembler define. coco.toml has a variant for each.
*   (none) CG6  PMODE 3  128x192  4 colours  32 bytes/row  6144 bytes
*   RG6    RG6  PMODE 4  256x192  2 colours  32 bytes/row  6144 bytes
*   RG3    RG3  PMODE 2  128x192  2 colours  16 bytes/row  3072 bytes
*   CG3    CG3  PMODE 1  128x96   4 colours  32 bytes/row  3072 bytes
*   RG2    RG2  PMODE 0  128x96   2 colours  16 bytes/row  1536 bytes
*   CG2    CG2  -        128x64   4 colours  32 bytes/row  2048 bytes
*   RG1    RG1  -        128x64   2 colours  16 bytes/row  1024 bytes
*   CG1    CG1  -        64x64    4 colours  16 bytes/row  1024 bytes
* PMODE numbers: The Rainbow, October 1986, PDF 119.
*
* SAMV is V2..V0. VDG is $FF22 bits 7..4. BPR is bytes per row. ROWS is the
* number of rows.
        ifdef RG6
SAMV    equ %110
VDG     equ %11110000
BPR     equ 32
ROWS    equ 192
MODESET equ 1
        endc
        ifdef RG3
SAMV    equ %101
VDG     equ %11010000
BPR     equ 16
ROWS    equ 192
MODESET equ 1
        endc
        ifdef CG3
SAMV    equ %100
VDG     equ %11000000
BPR     equ 32
ROWS    equ 96
MODESET equ 1
        endc
        ifdef RG2
SAMV    equ %011
VDG     equ %10110000
BPR     equ 16
ROWS    equ 96
MODESET equ 1
        endc
        ifdef CG2
SAMV    equ %010
VDG     equ %10100000
BPR     equ 32
ROWS    equ 64
MODESET equ 1
        endc
        ifdef RG1
SAMV    equ %001
VDG     equ %10010000
BPR     equ 16
ROWS    equ 64
MODESET equ 1
        endc
        ifdef CG1
SAMV    equ %001
VDG     equ %10000000
BPR     equ 16
ROWS    equ 64
MODESET equ 1
        endc
        ifndef MODESET
SAMV    equ %110
VDG     equ %11100000
BPR     equ 32
ROWS    equ 192
        endc
* Colour set: 0 = green, yellow, blue, red (RG: black, green).
*             %00001000 = buff, cyan, magenta, orange (RG: black, buff).
CSS     equ 0
* Screen start. It must be a multiple of 512. BASIC's text screen is at $0400.
SCREEN  equ $0400
* <<< END EXAMPLE

* --- CONTEXT: the leftmost and rightmost pixel of a byte, in the last colour
* code, for the border. $FF22 bit 4 is GM0. It is 1 in every two-colour mode.
        ifne VDG&%00010000
LEFT    equ %10000000
RIGHT   equ %00000001
        else
LEFT    equ %11000000
RIGHT   equ %00000011
        endc

        org $3000
* --- CONTEXT: draw the picture first, then show it.
* Each row holds four bars of bytes $55, $AA, $FF and $00.
start   ldx #SCREEN
        ldy #ROWS
row     ldu #bars
bar     lda ,u+
        ldb #BPR/4
fill    sta ,x+
        decb
        bne fill
        cmpu #bars+4
        bne bar
        leay -1,y
        bne row
* A border one pixel wide in the last colour code.
        ldx #SCREEN
        bsr line
        ldx #SCREEN+BPR*(ROWS-1)
        bsr line
        ldx #SCREEN
        ldy #ROWS
edges   lda ,x
        ora #LEFT
        sta ,x
        lda BPR-1,x
        ora #RIGHT
        sta BPR-1,x
        leax BPR,x
        leay -1,y
        bne edges
* >>> EXAMPLE 2 of 3: the three steps that select the screen.
* Step 1: SAM display offset.
        lda #SCREEN/512
        ldx #$FFC6
        ldb #7
        bsr samset
* Step 2: SAM display mode.
        lda #SAMV
        ldx #$FFC0
        ldb #3
        bsr samset
* Step 3: VDG mode and colour set. Keep bits 2..0.
        lda $FF22
        anda #%00000111
        ora #VDG+CSS
        sta $FF22
* <<< END EXAMPLE

* --- CONTEXT: hold the picture. The check takes its snapshot at this label.
* A project replaces this loop with its own main loop.
ready   bra ready

* --- CONTEXT: fill one row at X with $FF.
line    lda #$FF
        ldb #BPR
line1   sta ,x+
        decb
        bne line1
        rts

* >>> EXAMPLE 3 of 3: write SAM bits.
* Write the low B bits of A to the SAM, low bit first, from address X.
* Each bit has two addresses: even clears it, odd sets it. The data does not
* matter.
samset  lsra
        bcc samclr
        sta 1,x
        bra samnext
samclr  sta ,x
samnext leax 2,x
        decb
        bne samset
        rts
* <<< END EXAMPLE

* --- CONTEXT: the bytes of the four bars.
bars    fcb $55,$AA,$FF,$00
        end start
