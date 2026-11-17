* untitled-1: an evolution sliding puzzle for the CoCo 3.
*
* The board is 4x4 squares in 320x192 with 16 colours. The arrow keys slide
* the creatures, and two equal creatures merge into the next one. The game
* starts with two microbes, and a microbe appears after every move. The game
* is won when the human appears, and lost when no move can change the board.
* Then the squares change colour, and Space starts a new game.
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
*     5-9: Up, Down, Left, Right, Space are row PA3, columns PB3 to PB7.
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
TOP     equ 11                      the last creature: it wins the game
WINCODE equ $12                     square colour code after a win (green)
LOSECODE equ $07                    square colour code after a loss (red)
SPACE   equ 16                      the held bit of Space

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
* Every square is drawn first: $FF is not a level.
        ldx #shown
init    lda #$FF
        sta ,x+
        cmpx #shown+16
        blo init
        ifdef LAYOUT
* For the check only: start from a fixed layout.
        ldx #opening
        ldu #cells
lay     lda ,x+
        sta ,u+
        cmpu #cells+16
        blo lay
        else
        lbsr newgame
        endc
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
        ifndef NO_SCAN_STEP
* NO_SCAN_STEP is a fault for the check only.
        lbsr rand
        endc
        lbsr update
        lbsr board
        bra ready

* pause: about 96000 cycles, 6 fields at the normal clock.
pause   ldx #12000
pwait   leax -1,x
        bne pwait
        rts

* sample: the keys into held. Up 1, Down 2, Left 4, Right 8, Space 16.
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
        cmpx #columns+5
        blo scan
        lda #$FF
        sta $FF02
        rts

* update: in play, one move for a new press of one arrow. A move needs
* exactly one arrow held, and that arrow was not held at the previous
* sample. After the end of a game, a new press of Space starts a new game.
update  ldb previous
        comb
        andb held                   B: the keys pressed since last time
        lda held
        sta previous
        ifdef HELD_REPEAT
* A fault for the check only: a held arrow moves at every sample.
        tfr a,b
        endc
        tst phase
        beq uplay
        bitb #SPACE
        beq uend
        lbsr newgame
uend    rts
uplay   anda #15
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
        ifndef SPAWN_ALWAYS
* SPAWN_ALWAYS is a fault for the check only.
        tst moved
        beq unew                    nothing changed: not a move
        endc
        lbsr spawn
        ifndef NO_JUDGE
* NO_JUDGE is a fault for the check only.
        lbsr judge
        endc
unew    rts

* newgame: an empty board with two microbes, in the colours of play.
newgame clr phase
        lda c01_palette+1
        sta $FFB1
        ldx #cells
ngclr   clr ,x+
        cmpx #cells+16
        blo ngclr
        lbsr spawn
        lbsr spawn
        rts

* spawn: a microbe in an empty square. Step the generator, then take its low
* byte modulo the number of empty squares: k. Use the k-th empty square,
* counted from 0 in cell order.
spawn   lbsr rand
        ldx #cells
        clr empty
spcount tst ,x+
        bne spnext
        inc empty
spnext  cmpx #cells+16
        blo spcount
        tst empty
        beq spdone
        lda seed+1
        ifdef FIRST_EMPTY
* For the check only: always the first empty square.
        clra
        endc
spmod   cmpa empty
        blo spfind
        suba empty
        bra spmod
spfind  ldx #cells
spf1    tst ,x+
        bne spf1
        deca
        bpl spf1
        lda #1
        sta -1,x
spdone  rts

* judge: after a move, a human wins. Otherwise the game goes on while a
* square is empty or two neighbours are equal. If not, the game is lost.
judge   ldx #cells
jwin    lda ,x+
        cmpa #TOP
        beq won
        cmpx #cells+16
        blo jwin
        ldx #cells
jempty  tst ,x+
        beq jplay
        cmpx #cells+16
        blo jempty
        ldx #cells
        ldy #pairs
jpair   ldb ,y+
        lda b,x
        ldb ,y+
        cmpa b,x
        beq jplay
        cmpy #pairs+48
        blo jpair
        lda #2
        sta phase
        lda #LOSECODE
        sta $FFB1
jplay   rts
won     lda #1
        sta phase
        lda #WINCODE
        sta $FFB1
        rts

* rand: one step of a 16-bit xorshift generator, shifts 7, 9 and 8.
* seed = seed XOR (seed << 7); seed = seed XOR (seed >> 9);
* seed = seed XOR (seed << 8). Our choice of generator.
rand    ldd seed
        ldx #7
rshift  lslb
        rola
        leax -1,x
        bne rshift
        eora seed
        eorb seed+1
        std seed
        lsra                        A: the high byte >> 1
        eora seed+1
        sta seed+1                  low = low XOR (high >> 1)
        eora seed
        sta seed                    high = high XOR new low
        rts

* slide: move every line toward the edge of direction B. Each line is four
* cell numbers from "lines", the edge first. Creatures close up; two equal
* neighbours merge into the next level. A merged creature does not merge
* again in the same move.
slide   clr moved
        lda #16
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
        cmpa b,y
        beq ssame
        inc moved
        sta b,y
ssame
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

* For the check only: fixed layouts, row by row; 0 is empty.
        ifdef RULES
* One rule in each row: four equal, a merged creature next to an equal one,
* gaps, and three equal.
opening fcb 1,1,1,1
        fcb 1,1,2,0
        fcb 0,3,0,3
        fcb 0,2,2,2
        endc
        ifdef WIN
* Two primates: one move makes the human.
opening fcb 0,0,0,0
        fcb 0,0,0,0
        fcb 0,0,0,0
        fcb 10,10,0,0
        endc
        ifdef LOSE
* One move to the right, then the new microbe fills the board.
opening fcb 1,2,1,2
        fcb 2,1,2,1
        fcb 3,4,3,4
        fcb 3,1,3,0
        endc

* The 24 pairs of neighbouring cells: 12 across, then 12 down.
pairs   fcb 0,1,1,2,2,3,4,5,5,6,6,7,8,9,9,10,10,11,12,13,13,14,14,15
        fcb 0,4,4,8,8,12,1,5,5,9,9,13,2,6,6,10,10,14,3,7,7,11,11,15

* Cell numbers of each line, the edge of the move first: up, down, left,
* right. A cell number is row * 4 + column.
lines   fcb 0,4,8,12,1,5,9,13,2,6,10,14,3,7,11,15
        fcb 12,8,4,0,13,9,5,1,14,10,6,2,15,11,7,3
        fcb 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        fcb 3,2,1,0,7,6,5,4,11,10,9,8,15,14,13,12
* The held bit of each arrow, and the column strobe ($FF02) of each key:
* Up, Down, Left, Right and Space.
arrows  fcb 1,2,4,8
columns
        ifdef WRONG_COLUMN
        fcb $FB                     a fault for the check only: Up on PB2
        else
        fcb $F7
        endc
        fcb $EF,$DF,$BF,$7F

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
phase   fcb 0                       0 play, 1 won, 2 lost
moved   fcb 0                       squares changed by the last slide
empty   fcb 0
seed    fdb $7A35                   the generator's state: never 0
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
