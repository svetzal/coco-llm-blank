* Select a colour set on a CoCo 1/2 graphics screen (MC6847 VDG). The same
* code runs on a CoCo 3 in its VDG-compatible modes.
*
* $FF22 bit 3 is the colour-set select (CSS). It selects one of two sets of
* colours for the full screen. Each colour code in a screen byte then shows
* one colour of that set. On a CoCo 3, each code selects a palette register
* instead, and the program keeps the colours that BASIC loads into them.
*
* The example is in two parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it draws bars of each colour code
* and a band that shows the pixel order, sets up the screen at $0400 as in
* first-screen, and holds the picture for the check. A project does not need
* the context.
*
* Variants (coco.toml) select the colour set and the mode:
*   (none)    CG6  CSS=0  green, yellow, blue, red
*   css1      CG6  CSS=1  buff, cyan, magenta, orange
*   rg6       RG6  CSS=0  black, green
*   rg6-css1  RG6  CSS=1  black, buff
*
* Sources:
*   Motorola, MC6847 datasheet:
*     PDF 20: CG6 is 128x192 with four colours, RG6 is 256x192 with two.
*       Both use 6K bytes. CSS selects the colour and the border.
*     PDF 21 Figure 22(c): the colour of each code for each colour set.
*     PDF 19 Table 3: the leftmost pixel is in the high bits of a byte.
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 14: $FF22 bit 3 = CSS, bits 4..7 = GM0, GM1, GM2, A/G.
*     PDF 31 Table 1: CG6 and RG6 are SAM V2..V0 = 110, $FF22 bits 7..4 =
*       1110 and 1111. $FF22 bits 2..0 are "do not change".
*     PDF 11 and 15: SAM bits. The even address clears a bit, the odd
*       address sets it. F6..F0 is the screen start / 512.
*   Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 46: the same $FF22 and SAM values select G6C and G6R on a CoCo 3.
*       A G6C code selects palette register 0-3 (CSS=0) or 4-7 (CSS=1). A
*       G6R bit selects register 8-9 (CSS=0) or 10-11 (CSS=1).
*     PDF 57 step 44: BASIC loads registers 0-15 with 12,24,0B,07,3F,1F,09,
*       26,00,12,00,3F,00,12,00,26 (hex). This program does not change them.

* >>> EXAMPLE 1 of 2: the colour set and the mode.
* CSS is $FF22 bit 3: 0 selects colour set 0, %00001000 selects colour set 1.
*   Code  CG CSS=0  CG CSS=1  RG CSS=0  RG CSS=1
*   00/0  green     buff      black     black
*   01/1  yellow    cyan      green     buff
*   10    blue      magenta
*   11    red       orange
* VDG is $FF22 bits 7..4: %1110 for CG6, %1111 for RG6.
        ifdef CSS1
CSS     equ %00001000
        else
CSS     equ 0
        endc
        ifdef RG6
VDG     equ %11110000
        else
VDG     equ %11100000
        endc
* <<< END EXAMPLE

        org $3000
* --- CONTEXT: draw the picture. Rows 0-159 hold four bars, 8 bytes each,
* of $00, $55, $AA and $FF. In CG6 each bar is one colour code: 0, 1, 2, 3.
start   ldx #$0400
        ldy #160
row     ldu #bars
bar     lda ,u+
        ldb #8
fill    sta ,x+
        decb
        bne fill
        cmpu #bars+4
        bne bar
        leay -1,y
        bne row
* Rows 160-191: every byte is $1B, codes 0, 1, 2, 3 from the left in CG6.
        lda #$1B
order   sta ,x+
        cmpx #$1C00
        blo order
* --- CONTEXT: show the screen at $0400 in CG6 or RG6, as in first-screen.
* SAM offset F6..F0 = 0000010 ($0400 / 512), then SAM mode V2..V0 = 110.
        sta $FFC6
        sta $FFC9
        sta $FFCA
        sta $FFCC
        sta $FFCE
        sta $FFD0
        sta $FFD2
        sta $FFC0
        sta $FFC3
        sta $FFC5
* >>> EXAMPLE 2 of 2: write the mode and the colour set to $FF22.
* Keep bits 2..0. Other hardware uses them.
        lda $FF22
        anda #%00000111
        ora #VDG+CSS
        sta $FF22
* <<< END EXAMPLE

* --- CONTEXT: hold the picture. The check takes its snapshot at this label.
* A project replaces this loop with its own main loop.
ready   bra ready

* --- CONTEXT: the bytes of the four bars.
bars    fcb $00,$55,$AA,$FF
        end start
