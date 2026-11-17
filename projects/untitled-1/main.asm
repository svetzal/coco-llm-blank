* untitled-1: an evolution sliding puzzle for the CoCo 3.
*
* This step draws the 4x4 board in 320x192 with 16 colours, with a fixed
* showcase layout of all eleven creatures, and holds it at "ready".
* Input and the game rules come in the next step.
*
* Sources (read before changing a value):
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90. PDF 12: $FF98, $FF99. PDF 13: $FF9D, $FF9E.
*     PDF 15-16: MMU $FFA0-$FFA7; $FFA3 maps CPU $6000-$7FFF; data bits
*       5..0 are physical address bits 18..13.
*     PDF 17: palette registers $FFB0-$FFBF.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 38-39: byte formats, leftmost pixel in the high bits.
*     PDF 41-42 Table 4-10: HRES 111, CRES 10 is 320 pixels, 16 colours.
*   examples/gime-graphics: the same display setup, checked in XRoar.
*
* Memory (CPU addresses, BASIC's MMU map):
*   $2000-$5FFF  this program, its sprites and its own stack
*   $6000-$7FFF  the window that shows one 8 KiB page of the screen
*   physical $00000-$077FF  the screen, 160 bytes x 192 rows

WINDOW  equ $6000
MMUWIN  equ $FFA3                   MMU task 0 entry for CPU $6000-$7FFF
BPR     equ 160                     bytes in one screen row
ROWS    equ 192
* Board geometry, in bytes (two pixels each) and rows.
BOARDX  equ 24                      48 pixels from the left: centred
SQW     equ 28                      a square is 56 pixels: square on screen
SQH     equ 48
CELLX   equ 1                       grey cell: 2 pixels in from the square
CELLY   equ 2
CELLW   equ 26
CELLH   equ 44
SPRX    equ 2                       creature: 4 pixels in from the square
SPRY    equ 4
GREY    equ $11                     two pixels of register 1 (dark grey $10)

        org $2000
* Set our own stack. BASIC's stack could be in CPU $6000-$7FFF, which this
* program maps to the screen.
start   lds #stacktop
        clr rval                    clear the screen to register 0
        clr rx
        clr ry
        lda #BPR
        sta rw
        lda #ROWS
        sta rh
        lbsr fill
        lbsr board

* Set the palette and show the screen (as examples/gime-graphics).
        ldx #c01_palette
        ldu #$FFB0
pal     lda ,x+
        sta ,u+
        cmpu #$FFC0
        blo pal
        clr $FF9A                   border: colour code 0
        lda #%01001110              CoCo 3 mode, MMU on, 32K internal ROM
        sta $FF90
        lda #%10000000              graphics, one line for each row
        sta $FF98
        lda #%00011110              192 rows, HRES 111, CRES 10
        sta $FF99
        clr $FF9C
        clr $FF9D                   display at physical $00000
        clr $FF9E
        clr $FF9F
* For the check: hold the picture. The game loop replaces this.
ready   bra ready

* Draw the 16 squares from "cells", row by row.
board   clr square
bsq     lda square
        anda #3
        ldb #SQW
        mul
        addb #BOARDX
        stb sqx
        lda square
        lsra
        lsra
        ldb #SQH
        mul
        stb sqy
        lda sqx                     the grey cell
        adda #CELLX
        sta rx
        lda sqy
        adda #CELLY
        sta ry
        lda #CELLW
        sta rw
        lda #CELLH
        sta rh
        lda #GREY
        sta rval
        lbsr fill
        ldx #cells                  the creature, if the square has one
        lda square
        lda a,x
        beq bnext
        deca
        lsla
        ldx #sprites
        ldu a,x
        lda sqx
        adda #SPRX
        sta rx
        lda sqy
        adda #SPRY
        sta ry
        lda #c01_bpr
        sta rw
        lda #c01_rows
        sta rh
        lbsr blit
bnext   inc square
        lda square
        cmpa #16
        blo bsq
        rts

* fill: rh rows of rw bytes of rval, from byte rx of row ry.
fill    lda rh
        sta count
frow    lbsr rowat
        ldb rw
fbyte   lda rval
        bsr put
        decb
        bne fbyte
        inc ry
        dec count
        bne frow
        rts

* blit: rh rows of rw bytes from U, to byte rx of row ry.
blit    lda rh
        sta count
brow    lbsr rowat
        ldb rw
bbyte   lda ,u+
        bsr put
        decb
        bne bbyte
        inc ry
        dec count
        bne brow
        rts

* rowat: map the page that holds byte rx of row ry; X = its CPU address.
rowat   lda ry
        ldb #BPR
        mul
        addb rx
        adca #0
        pshs b
        tfr a,b                     page = offset / $2000 = high byte / 32
        lsrb
        lsrb
        lsrb
        lsrb
        lsrb
        stb page
        stb MMUWIN
        anda #$1F
        adda #WINDOW/256
        puls b
        tfr d,x
        rts

* put: store A at X and advance. At the end of the window, map the next page.
put     sta ,x+
        cmpx #WINDOW+$2000
        blo put1
        pshs a
        inc page
        lda page
        sta MMUWIN
        puls a
        ldx #WINDOW
put1    rts

* The creature level in each square, row by row; 0 is empty.
* A fixed showcase of all eleven creatures, until the game rules exist.
cells   fcb 1,2,3,4
        fcb 5,6,7,8
        fcb 9,10,11,0
        fcb 0,0,0,0

sprites fdb c01,c02,c03,c04,c05,c06,c07,c08,c09,c10,c11
        include "c01.asm"
        include "c02.asm"
        include "c03.asm"
        include "c04.asm"
        include "c05.asm"
        include "c06.asm"
        include "c07.asm"
        include "c08.asm"
        include "c09.asm"
        include "c10.asm"
        include "c11.asm"
        include "c01-palette.asm"
        if c01_bpr-24
        error "c01.asm: a sprite row must be 24 bytes"
        endc
        if c01_rows-40
        error "c01.asm: a sprite must be 40 rows"
        endc

rx      fcb 0
ry      fcb 0
rw      fcb 0
rh      fcb 0
rval    fcb 0
count   fcb 0
page    fcb 0
square  fcb 0
sqx     fcb 0
sqy     fcb 0
stack   rmb 256
stacktop
ends    fcb 0
        end start
