* untitled-1: an evolution sliding puzzle for the CoCo 3.
*
* The board is 4x4 squares in 320x192 with 16 colours. The arrow keys slide
* the creatures, and two equal creatures merge into the next one. In this
* step the game starts from a fixed layout, and no new creatures appear.
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
*   Keyboard matrix: Tandy, Color Computer 3 Service Manual, PDF 40, figure
*     5-9: Up, Down, Left, Right are row PA3, columns PB3, PB4, PB5, PB6.
*     PDF 9: the PIA registers and control bit 2. A pressed key reads 0.
*     guidance/techniques/controls-and-collision.md and
*     examples/keyboard-controls and collect-room use the same scan.
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
TOP     equ 11                      the last creature: it does not merge

        org $2000
* Set our own stack. BASIC's stack could be in CPU $6000-$7FFF, which this
* program maps to the screen.
start   lds #stacktop
* Mask IRQ and FIRQ. Nothing of BASIC runs after this point, so its IRQ
* handler cannot read the PIA while the direction register is selected.
        orcc #$50
* Rows (port A) are inputs and columns (port B) are outputs. Control bit 2
* clear selects the direction register; set selects the data register.
        lda $FF01
        anda #$FB
        sta $FF01
        clr $FF00
        ora #4
        sta $FF01
        lda $FF03
        anda #$FB
        sta $FF03
        ldb #$FF
        stb $FF02
        ora #4
        sta $FF03
        stb $FF02
* The game starts from the fixed layout. Nothing is on the screen yet.
        ldx #opening
        ldu #cells
        ldy #shown
init    lda ,x+
        sta ,u+
        lda #$FF                    not a level: every square is drawn
        sta ,y+
        cmpu #cells+16
        blo init
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

* Let a few fields pass in the new mode before the first snapshot. XRoar
* sets its picture window once for each field, from the mode at the end of
* vertical sync (src/tcc1014/tcc1014.c), so the first field still has the
* window of BASIC's text mode.
        lbsr pause
* An arrow held at the start is not a new press.
        lbsr sample
        lda held
        sta previous
* The game loop. "ready" is where the check takes each snapshot. The pause
* keeps the picture still for the capture and sets the scan rate.
ready   lbsr pause
        lbsr sample
        lbsr update
        lbsr board
        bra ready

* pause: about 96000 cycles, 6 fields at the normal clock.
pause   ldx #12000
pwait   leax -1,x
        bne pwait
        rts

* sample: the arrows into held. Up 1, Down 2, Left 4, Right 8.
* Strobe one column low, test row PA3 (bit 3). Leave all columns high.
* A key script takes effect at each entry of sample.
sample  clr held
        ldx #columns
        ldb #1
scan    lda ,x+
        sta $FF02
        lda $FF00
        bita #8
        bne up
        pshs b
        orb held
        stb held
        puls b
up      lslb
        cmpx #columns+4
        blo scan
        lda #$FF
        sta $FF02
        rts

* update: one move for a new press of one arrow. A move needs exactly one
* arrow held, and that arrow was not held at the previous sample.
update  ldb previous
        comb
        andb held                   B: the arrows pressed since last time
        lda held
        sta previous
        ifdef HELD_REPEAT
* A fault for the check only: a held arrow moves at every sample.
        tfr a,b
        endc
        ldx #arrows
udir    cmpa ,x
        beq ufound
        leax 1,x
        cmpx #arrows+4
        blo udir
        rts                         no arrow, or more than one
ufound  andb ,x
        beq unew
        tfr x,d
        subd #arrows                B: 0 up, 1 down, 2 left, 3 right
        lbsr slide
unew    rts

* slide: move every line toward the edge of direction B. Each line is four
* cell numbers from "lines", the edge first. Creatures close up; two equal
* neighbours merge into the next level. A merged creature does not merge
* again in the same move. The last creature does not merge.
slide   lda #16
        mul
        ldx #lines
        abx
        lda #4
        sta lcount
sline   stx lptr
        ldu #cells
        ldy #vin
        ldb #4
sread   lda ,x+
        lda a,u
        sta ,y+
        decb
        bne sread
        ldy #vout
        clr ,y
        clr 1,y
        clr 2,y
        clr 3,y
        clr last
        ldu #vin
        ldb #4
smerge  lda ,u+
        beq snext
        cmpa last
        bne sput
        cmpa #TOP
        beq sput
        inca
        sta -1,y
        clr last
        ifdef REMERGE
* A fault for the check only: the merged creature can merge again.
        sta last
        endc
        bra snext
sput    sta ,y+
        sta last
snext   decb
        bne smerge
        ldx lptr
        ldu #vout
        ldy #cells
        lda #4
        sta count
swrite  ldb ,x+
        lda ,u+
        sta b,y
        dec count
        bne swrite
        dec lcount
        bne sline
        rts

* Draw each square whose level differs from "shown", row by row.
board   clr square
bsq     ldx #cells
        ldb square
        lda b,x
        ldx #shown
        cmpa b,x
        lbeq bnext
        sta b,x
        lda square
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
        lblo bsq
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

* The opening layout, row by row; 0 is empty. Each row tests a rule.
* New creatures do not appear yet, so this layout is the whole game.
opening fcb 1,1,1,1
        fcb 1,1,2,0
        fcb 0,3,0,3
        fcb 11,11,10,10

* Cell numbers of each line, the edge of the move first: up, down, left,
* right. A cell number is row * 4 + column.
lines   fcb 0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15
        fcb 12,8,4,0,13,9,5,1,14,10,6,2,15,11,7,3
        fcb 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        fcb 3,2,1,0,7,6,5,4,11,10,9,8,15,14,13,12
* The held bit of each arrow, and its column strobe ($FF02), in that order.
arrows  fcb 1,2,4,8
columns
        ifdef WRONG_COLUMN
        fcb $FB                     a fault for the check only: Up on PB2
        else
        fcb $F7
        endc
        fcb $EF,$DF,$BF

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

cells   rmb 16                      the level in each square; 0 is empty
shown   rmb 16                      the level drawn in each square
vin     rmb 4                       one line before the move
vout    rmb 4                       one line after the move
lptr    fdb 0
lcount  fcb 0
last    fcb 0
held    fcb 0
previous fcb 0
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
