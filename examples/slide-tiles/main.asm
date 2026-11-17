* Slide tiles between the squares of a board, with two screens.
*
* A move takes N steps of a fixed duration. At step k, each moving tile is
* k/N of the way from its start square to its end square. A tile that does
* not move is never drawn again. One step on the screen that is not shown:
*   1. Erase the trail of each moving tile: the part of its rectangle on
*      this screen (where this screen last showed it) that the new rectangle
*      does not cover. Paint it with the empty board.
*   2. Draw each moving tile at its new place, in list order.
*   3. Show the screen (page flip).
* After step N, the program draws step N on the other screen too, so both
* screens show the end of the move.
*
* Two builds:
*   Main build (CoCo 1, CoCo 2 and CoCo 3): CG6, 128x192, 4 colours, 32
*     bytes per row. Screens at CPU $0400 and $2400, flipped with SAM F4,
*     as in examples/page-flip. The 6809 copies with LDA/STA.
*   GIME16 define (variant "gime16", a CoCo 3 with a 6309 and 512 KiB):
*     GIME 320x192, 16 colours, 160 bytes per row. Screens at physical
*     $00000 and $08000, flipped with $FF9D, as in examples/page-flip. The
*     6309 copies with TFM. CPU $6000-$9FFF is a window to two pages of a
*     screen.
*   STEPS8 define (variant "steps8"): 8 steps instead of 4.
*
* The example is in four parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up the screens, paints
* the board, draws the tiles and flips the screens. It plays two moves, Left
* and Down, again and again. A project does not need the context.
*
* Sources:
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 13: $FF03 bit 0 = FS IRQ enable, bit 1 = FS edge, bit 2 = data
*       register, bit 7 = FS flag.
*     PDF 14 and 31 Table 1: CG6 is SAM V=110 and $FF22 bits 7..4 1110.
*     PDF 15: SAM display offset in 1/2K units; F4 is $FFCE and $FFCF.
*   Motorola, MC6847 datasheet, PDF 19 Table 3: the leftmost pixel is in
*     the high bits. PDF 21: colour set 0 is green, yellow, blue, red.
*   Motorola, MC6821 PIA datasheet, PDF 10: a read of the data register
*     clears the flag.
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90; $FF92 bit 3 = VBORD. PDF 12: $FF98, $FF99.
*     PDF 13: $FF9D = physical address bits 18..11, $FF9E = bits 10..3.
*     PDF 15-16: MMU $FFA0-$FFA7; $FFA3 maps CPU $6000-$7FFF, $FFA4 maps
*       $8000-$9FFF; a value is physical address bits 18..13.
*     PDF 17: palette registers $FFB0-$FFBF.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 38-39: in 16-colour modes a byte holds two pixels, the leftmost
*       in the high bits; a pixel value selects a palette register.
*     PDF 41-42 Table 4-10: HRES 111, CRES 10 is 320 pixels, 16 colours.
*     PDF 50: an $FF92 bit sets only if $FF90 enables IRQ (IEN); a read of
*       $FF92 clears it.
*   HD63B09EP Technical Reference Guide, PDF 34: TFM takes 6+3n cycles.
*   The 6309 Book (Burke & Burke), PDF 225: TFM moves W bytes; PDF 231:
*     TFM r0,r1+ repeats one source byte.

        ifdef STEPS8
N       equ 8                       steps in a move
NSHIFT  equ 3                       N = 2^NSHIFT
        else
N       equ 4
NSHIFT  equ 2
        endc
SQH     equ 48                      rows in a square
TY      equ 4                       the tile starts 4 rows into its square
TH      equ 40                      tile rows
TREC    equ 9                       bytes in a tile record

        ifdef GIME16
        ifndef H6309
        error "The gime16 build uses TFM: build it for a 6309 target"
        endc
BPR     equ 160
BX      equ 24                      the board starts at byte 24 (pixel 48)
SQW     equ 28                      a square is 28 bytes (56 pixels)
TX      equ 2                       the tile starts 2 bytes into its square
TW      equ 24                      tile bytes (48 pixels)
* Two pixels of one palette register in each byte.
GUT     equ $00                     register 0: the gaps and the margins
CELL    equ $11                     register 1: an empty square
YEL     equ $22                     register 2
RED     equ $33                     register 3
WINDOW  equ $6000
MMUWIN  equ $FFA3
VIEW_A  equ $00                     physical $00000 / 2048
VIEW_B  equ $10                     physical $08000 / 2048
        else
BPR     equ 32
BX      equ 0
SQW     equ 8                       a square is 8 bytes (32 pixels)
TX      equ 2
TW      equ 4                       tile bytes (16 pixels)
* Four pixels of one colour code in each byte, colour set 0.
GUT     equ $AA                     code 2: blue
CELL    equ $00                     code 0: green
YEL     equ $55                     code 1: yellow
RED     equ $FF                     code 3: red
SCREEN_A equ $0400                  SAM offset 2: F4 = 0
SCREEN_B equ $2400                  SAM offset 18: F4 = 1
        endc

        org $4400
* --- CONTEXT: show the screen mode. Screen A is shown, B is drawn first.
start
        ifdef GIME16
* Mask IRQ: the VBORD flag also requests an IRQ, and BASIC's handler must
* not read $FF92. The window also maps over CPU $8000-$9FFF, where BASIC
* keeps its code, and BASIC's stack can be in $6000-$7FFF. So use an own
* stack.
        lds #stacktop
        orcc #%00010000
        ldx #codes
        ldu #$FFB0
pal     lda ,x+
        sta ,u+
        cmpu #$FFB4
        blo pal
        clr $FF9A                   border: colour code 0
        lda #$6E                    native video, MMU, IEN (as page-flip)
        sta $FF90
        lda #%00001000              VBORD only
        sta $FF92
        lda #%10000000              graphics, one line for each row
        sta $FF98
        lda #%00011110              192 rows, HRES 111, CRES 10
        sta $FF99
        clr $FF9C
        lda #VIEW_A
        sta $FF9D
        clr $FF9E
        clr $FF9F
        else
* CG6 with colour set 0 from SCREEN_A: SAM offset 2, SAM mode V=110.
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
        lda $FF22
        anda #%00000111
        ora #%11100000
        sta $FF22
* No FS IRQ, so no handler takes the flag. Falling edge. Data register.
        lda $FF03
        anda #%11111100
        ora #%00000100
        sta $FF03
        endc
        lda #1
        sta back
        lbsr tables

* --- CONTEXT: play the moves again and again.
again   ldx #moves
nextmv  ldy ,x++
        beq again
        pshs x
        tfr y,x
        lbsr move
        puls x
        bra nextmv

* >>> EXAMPLE 1 of 4: a move. Show the start on both screens. Then N steps,
* then step N on the other screen too.
* X: the move: tile, start square, end square for each tile; $FF ends it.
move    stx mptr
        lbsr board                  the start, on the screen not shown
        lbsr flip
        lbsr board                  and on the other screen
        lbsr records
        lda #1
        sta k
mstep   lbsr step
        lbsr flip
        lda k
        cmpa #N
        beq mend
        inc k
        bra mstep
mend    lbsr step                   step N again, on the other screen
        lbra flip

* records: one record for each tile: kind, start x and y, end x and y,
* then the x and y where screen A and screen B last showed it.
records ldx mptr
        ldu #tiles
        clr ntiles
rc1     lda ,x+
        cmpa #$FF
        beq rc2
        sta ,u
        lda ,x+
        lbsr place                  B: byte column, A: row
        stb 1,u
        sta 2,u
        stb 5,u
        stb 6,u
        sta 7,u
        sta 8,u
        lda ,x+
        lbsr place
        stb 3,u
        sta 4,u
        leau TREC,u
        inc ntiles
        bra rc1
rc2     rts
* <<< END EXAMPLE

* >>> EXAMPLE 2 of 4: one step on the screen that is not shown. Erase every
* trail first, then draw every moving tile. A tile drawn later covers a
* tile drawn before it, so a merge pair overlaps in list order.
step    ldu #tiles
        lda ntiles
        sta tcount
st1     lbsr moves1
        beq st2
        lbsr where
        lbsr trail
st2     leau TREC,u
        dec tcount
        bne st1
        ldu #tiles
        lda ntiles
        sta tcount
st3     lbsr moves1
        beq st4
        lbsr where
        lda nx
        sta rx
        lda ny
        sta ry
        lda ,u
        lbsr tile
        ldb back                    this screen now shows the tile here
        leay 5,u
        lda nx
        sta b,y
        leay 7,u
        lda ny
        sta b,y
st4     leau TREC,u
        dec tcount
        bne st3
        rts

* moves1: Z clear if the tile at U moves in this move.
moves1  lda 1,u
        cmpa 3,u
        bne mv1
        lda 2,u
        cmpa 4,u
mv1     rts

* where: nx = start x + (end x - start x) * k / N, and ny likewise. The
* division rounds toward the start.
where   lda 1,u
        ldb 3,u
        bsr lerp
        sta nx
        lda 2,u
        ldb 4,u
        bsr lerp
        sta ny
        rts
* lerp: A from, B to: A + (B - A) * k / N, on unsigned bytes.
lerp    pshs a
        cmpb ,s
        bhs lup
        lda ,s                      to < from: from - (from - to) * k / N
        pshs b
        suba ,s+
        ldb k
        mul
        bsr divn
        lda ,s+
        pshs b
        suba ,s+
        rts
lup     subb ,s                     to >= from: from + (to - from) * k / N
        lda k
        mul
        bsr divn
        addb ,s+
        tfr b,a
        rts
divn    ldx #NSHIFT
dv1     lsra
        rorb
        leax -1,x
        bne dv1
        rts
* <<< END EXAMPLE

* >>> EXAMPLE 3 of 4: the trail of the tile at U on this screen: its old
* rectangle (ox, oy) minus its new one (nx, ny). A tile moves along one
* axis, so the trail is one strip at the back of the tile. Paint it with
* the empty board. When the tile moved more than its size, the strip also
* covers the empty board between the two rectangles, which does no harm.
trail   ldb back
        leay 5,u
        lda b,y
        sta ox
        leay 7,u
        lda b,y
        sta oy
        lda nx
        cmpa ox
        beq tvert
        blo tleft
        lda ox                      moving right: ox .. nx - 1
        sta rx
        lda nx
        suba ox
        bra thoriz
tleft   lda nx                      moving left: nx + TW .. ox + TW - 1
        adda #TW
        sta rx
        lda ox
        suba nx
thoriz  sta rw
        lda oy
        sta ry
        lda #TH
        sta rh
        lbra paint
tvert   lda ny
        cmpa oy
        beq tnone
        blo tup
        lda oy                      moving down: oy .. ny - 1
        sta ry
        lda ny
        suba oy
        bra tvert2
tup     lda ny                      moving up: ny + TH .. oy + TH - 1
        adda #TH
        sta ry
        lda oy
        suba ny
tvert2  sta rh
        lda ox
        sta rx
        lda #TW
        sta rw
        lbra paint
tnone   rts
* <<< END EXAMPLE

* >>> EXAMPLE 4 of 4: paint the empty board in rh rows of rw bytes from byte
* rx of row ry. Rows 0, 1, 46 and 47 of each square row are gaps; the other
* rows copy the same row of the board, "bgrow".
paint   lbsr rowat
        lda ry
pm1     cmpa #SQH
        blo pm2
        suba #SQH
        bra pm1
pm2     sta m
pt1     ldy #gutrow
        lda m
        cmpa #2
        blo pt2
        cmpa #SQH-2
        bhs pt2
        ldy #bgrow
pt2     tfr y,d                     Y = the row + rx (unsigned)
        addb rx
        adca #0
        tfr d,y
        pshs x
        ldb rw
        lbsr copyb
        puls x
        lbsr down
        inc m
        lda m
        cmpa #SQH
        blo pt3
        clr m
pt3     dec rh
        bne pt1
        rts
* <<< END EXAMPLE

* --- CONTEXT: copyb copies B bytes from Y to X; fillb writes B bytes of A
* to X. Both advance X.
copyb
        ifdef GIME16
        clra
        tfr d,w
        tfm y+,x+
        else
cb1     lda ,y+
        sta ,x+
        decb
        bne cb1
        endc
        rts
fillb
        ifdef GIME16
        sta fillv
        clra
        tfr d,w
        ldy #fillv
        tfm y,x+
        else
fb1     sta ,x+
        decb
        bne fb1
        endc
        rts

* --- CONTEXT: a tile of kind A (1 or 2) at byte rx, row ry. Four rows and
* one byte at each side are its edge. Kind 1: red edge, yellow inside.
* Kind 2: yellow edge, red inside.
tile    ldb #RED
        stb edge
        ldb #YEL
        stb inside
        cmpa #1
        beq tl0
        ldb #YEL
        stb edge
        ldb #RED
        stb inside
tl0     lbsr rowat
        clr count
tl1     pshs x
        lda count
        cmpa #4
        blo tl2
        cmpa #TH-4
        bhs tl2
        lda edge
        ldb #1
        bsr fillb
        lda inside
        ldb #TW-2
        bsr fillb
        lda edge
        ldb #1
        bsr fillb
        bra tl3
tl2     lda edge
        ldb #TW
        bsr fillb
tl3     puls x
        lbsr down
        inc count
        lda count
        cmpa #TH
        blo tl1
        rts

* --- CONTEXT: board: the empty board on the screen not shown, then each
* tile of the move at its start square.
board   clr rx
        clr ry
        lda #BPR
        sta rw
        lda #192
        sta rh
        lbsr paint
        ldx mptr
bd1     lda ,x+
        cmpa #$FF
        beq bd2
        pshs a
        lda ,x+
        leax 1,x
        lbsr place
        stb rx
        sta ry
        puls a
        pshs x
        lbsr tile
        puls x
        bra bd1
bd2     rts

* --- CONTEXT: place: square A (0-15, row by row) -> B: the byte column of
* its tile, A: the row of its tile.
place   pshs a
        anda #3
        ldb #SQW
        mul
        addb #BX+TX
        puls a
        pshs b
        lsra
        lsra
        ldb #SQH
        mul
        addb #TY
        tfr b,a
        puls b,pc

* --- CONTEXT: rowat: X = byte rx of row ry on the screen not shown.
* down: X to the same byte one row lower.
        ifdef GIME16
rowat   lda back                    screen A: pages 0-3; screen B: pages 4-7
        lsla
        lsla
        sta bpage
        lda ry
        ldb #BPR
        mul
        addb rx
        adca #0
        pshs b
        tfr a,b                     page = offset / $2000
        lsrb
        lsrb
        lsrb
        lsrb
        lsrb
        addb bpage
        stb page
        bsr mapwin
        anda #$1F
        adda #WINDOW/256
        puls b
        tfr d,x
        rts
* mapwin: the page at CPU $6000 and the next page at $8000, so that a row
* is never split.
mapwin  pshs b
        ldb page
        stb MMUWIN
        incb
        stb MMUWIN+1
        puls b,pc
down    leax BPR,x
        cmpx #WINDOW+$2000
        blo dn1
        leax -$2000,x
        inc page
        bsr mapwin
dn1     rts
        else
rowat   lda ry
        ldb #BPR
        mul
        addb rx
        adca #0
        tst back
        bne ra1
        addd #SCREEN_A
        bra ra2
ra1     addd #SCREEN_B
ra2     tfr d,x
        rts
down    leax BPR,x
        rts
        endc

* --- CONTEXT: flip: show the screen that was just drawn after the end of
* the active display. Then wait one more field before the program draws into
* the other screen. Read examples/page-flip.
flip
        ifdef GIME16
        lda $FF92
fw1     lda $FF92
        bita #%00001000
        beq fw1
        lda #VIEW_A
        tst back
        beq fw2
        lda #VIEW_B
fw2     sta $FF9D
* For the check only: the check takes a snapshot each time the program
* reaches this label.
published
        lda $FF92
fw3     lda $FF92
        bita #%00001000
        beq fw3
        else
        lda $FF02
fw1     lda $FF03
        bpl fw1
        tst back
        bne fw2
        sta $FFCE
        bra published
fw2     sta $FFCF
* For the check only: the check takes a snapshot each time the program
* reaches this label.
published
        lda $FF03
        ora #%00000010
        sta $FF03
        lda $FF02
fw3     lda $FF03
        bpl fw3
        lda $FF03
        anda #%11111101
        sta $FF03
        endc
        lda back
        eora #1
        sta back
        rts

* --- CONTEXT: tables: bgrow is one row of the empty board through the
* squares; gutrow is one row of gaps.
tables  ldx #gutrow
        ldb #BPR
        lda #GUT
        lbsr fillb
        ldx #bgrow
        ldb #BPR
        lda #GUT
        lbsr fillb
        ldx #bgrow+BX+1
        lda #4
        sta count
tb1     lda #CELL
        ldb #SQW-2
        lbsr fillb
        leax 2,x
        dec count
        bne tb1
        rts

* --- CONTEXT: the moves: kind, start square, end square.
* Left: 1 at 1 -> 0; 2 at 3 -> 1; 1 at 4 stays; 1 at 5 -> 4 (a merge pair);
* 2 at 6 -> 5 and 2 at 7 -> 5 (a merge pair); 2 at 11 -> 8; 1 at 12 stays;
* 1 at 14 -> 12 (a merge pair).
move1   fcb 1,1,0,2,3,1,1,4,4,1,5,4,2,6,5,2,7,5,2,11,8,1,12,12,1,14,12,$FF
* Down: 1 at 0 -> 12; 2 at 1 -> 13 and 2 at 5 -> 13 (a merge pair);
* 1 at 2 -> 10; 2 at 10 -> 14; 1 at 3 -> 7; 2 at 7 -> 11; 1 at 15 stays.
move2   fcb 1,0,12,2,1,13,2,5,13,1,2,10,2,10,14,1,3,7,2,7,11,1,15,15,$FF
moves   fdb move1,move2,0
        ifdef GIME16
* Colour codes for palette registers 0-3: black, green, yellow, red.
codes   fcb $00,$12,$24,$16
        endc

* --- CONTEXT: program state. This is a data label: the check fails if the
* CPU executes it.
state
mptr    rmb 2
tiles   rmb TREC*16
ntiles  rmb 1
tcount  rmb 1
k       rmb 1
nx      rmb 1
ny      rmb 1
ox      rmb 1
oy      rmb 1
m       rmb 1
back    rmb 1                       the screen not shown: 0 A, 1 B
bpage   rmb 1
page    rmb 1
count   rmb 1
edge    rmb 1
inside  rmb 1
fillv   rmb 1
rx      rmb 1
ry      rmb 1
rw      rmb 1
rh      rmb 1
gutrow  rmb BPR
bgrow   rmb BPR
        ifdef GIME16
stack   rmb 128
stacktop
        endc
last    rmb 1
        end start
