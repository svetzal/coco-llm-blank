* Evolve: an evolution sliding puzzle for the CoCo 3.
*
* The title screen shows the eleven creatures. Space starts a game. The
* board is 4x4 squares in 320x192 with 16 colours. The arrow keys slide
* the creatures, and two equal creatures merge into the next one. The game
* starts with two microbes, and a microbe appears after every move. The game
* is won when the human appears, and lost when no move can change the board.
* Then the squares change colour, a banner shows the result, and Space
* starts a new game.
*
* Two screens: the program draws into the screen that is not shown, then
* shows it in the vertical blank. Thus a change appears all at once.
*
* Sources (read before changing a value):
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90. PDF 12: $FF98, $FF99. PDF 13: $FF9D, $FF9E.
*     PDF 15-16: MMU $FFA0-$FFA7; $FFA3 maps CPU $6000-$7FFF; data bits
*       5..0 are physical address bits 18..13.
*     PDF 17: palette registers $FFB0-$FFBF.
*     PDF 11: $FF92 bit 3 = VBORD.
*   Tepolt, PDF 50: an $FF92 bit sets only if $FF90 enables IRQ (IEN); a
*     read of $FF92 clears it.
*   The 6309 Book (Burke & Burke): PDF 225: TFM moves W bytes between two
*     of X, Y, U, S, D; W is 0 after it. PDF 231: TFM r0,r1+ repeats one
*     source byte (a fill). HD63B09EP Technical Reference Guide, PDF 34:
*     each TFM form takes 6+3n cycles.
*   guidance/techniques/animation.md, "Flip pages in the GIME native modes",
*     and examples/page-flip: write $FF9D after a new VBORD, then wait for
*     one more VBORD before drawing into the old screen.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 38-39: byte formats, leftmost pixel in the high bits.
*     PDF 41-42 Table 4-10: HRES 111, CRES 10 is 320 pixels, 16 colours.
*   examples/gime-graphics: the same display setup, checked in XRoar.
*   Keyboard matrix: Tandy, Color Computer 3 Service Manual, PDF 40, figure
*     5-9: Up, Down, Left, Right, Space are row PA3, columns PB3 to PB7.
*     PDF 9: the PIA registers and control bit 2. A pressed key reads 0.
*     guidance/techniques/controls-and-collision.md and
*     examples/keyboard-controls and collect-room use the same scan.
*   Sound (as examples/timer-sound; guidance/techniques/sound.md):
*     Tepolt, PDF 47-53: FIRQ saves CC and PC; the jump table entry $FEF4;
*     $FF90 bit 4 (FEN), $FF91 bit 5 (fast timer input), $FF93 bit 5
*     (timer FIRQ); a read of $FF93 releases the request. Service Manual,
*     PDF 9-10: the DAC in $FF20 bits 7-2, the mux select in $FF01 and
*     $FF03 bit 3, sound enable $FF23 bit 3, the PIA FIRQ enables. PDF 12:
*     the write to $FF94 starts the 12-bit timer, which reloads itself.
*     Kowalski, GIME register reference: one count is 279.365 ns, and a
*     period is the reload value plus 2 counts on the 1986 GIME.
*     TFM and interrupts: the HD63B09EP Technical Reference Guide, PDF 12,
*     says an interrupt can stop a TFM; the 6309 Book, PDF 230, says not.
*
* Memory (CPU addresses, BASIC's MMU map):
*   $0E00-$5FFF  this program, its sprites, its words and its own stack
*   $6000-$9FFF  the window that shows two 8 KiB pages of a screen, so a
*                row is never split ($FFA3 and $FFA4). BASIC is not used.
*   physical $00000-$077FF  screen A, 160 bytes x 192 rows (pages 0-3)
*   physical $08000-$0F7FF  screen B (pages 4-7)

WINDOW  equ $6000
MMUWIN  equ $FFA3                   MMU task 0 entries for CPU $6000-$9FFF
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
* $FF9D = physical address bits 18..11; $FF9E = bits 10..3 stays 0.
VIEWA   equ $00                     $00000 / 2048
VIEWB   equ $10                     $08000 / 2048
* Phases.
PLAY    equ 0
WON     equ 1
LOST    equ 2
TITLE   equ 3
* What a screen holds: its scene, its banner, the level in each square,
* then the score and the best score that it shows (3 BCD bytes each).
NOSCENE equ 0
TSCENE  equ 1
BSCENE  equ 2
DSCORE  equ 18
DBEST   equ 21
DSIZE   equ 24
* The scores, in the black margins beside the board: byte column and row.
SCOREX  equ 2                       5 digits: pixels 4-43
BESTX   equ 138                     5 digits: pixels 276-315
DIGITY  equ 20
LABELY  equ 8

        ifndef H6309
        error "Evolve uses 6309 instructions (TFM): build for a 6309 target"
        endc
        org $0E00
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
        lbsr sound
* Both screens are black, and neither holds a scene.
        lda #4
        sta bpage
        lbsr clear
        clr bpage
        lbsr clear
        clr desc
        clr desc+DSIZE
        ifdef LAYOUT
* For the check only: start a game from a fixed layout.
        ldx #opening
        ldu #cells
lay     lda ,x+
        sta ,u+
        cmpu #cells+16
        blo lay
        clr phase
        lbsr seen
        else
        lda #TITLE
        sta phase
        endc

* Set the palette and show screen A (as examples/gime-graphics).
        ldx #c01_palette
        ldu #$FFB0
pal     lda ,x+
        sta ,u+
        cmpu #$FFC0
        blo pal
        clr $FF9A                   border: colour code 0
* CoCo 3 mode, MMU on, IEN on (the VBORD flag), FEN on (the sound timer),
* 32K internal ROM. IRQ is masked in the CPU, so no handler reads $FF92.
        ifdef SILENT
        lda #%01101110              a fault for the check only: no FIRQ
        else
        lda #%01111110              FEN on: the GIME timer FIRQ
        endc
        sta $FF90
        lda #%00001000              VBORD only
        sta $FF92
        lda #%10000000              graphics, one line for each row
        sta $FF98
        lda #%00011110              192 rows, HRES 111, CRES 10
        sta $FF99
        clr $FF9C
        lda #VIEWA
        sta $FF9D                   display at physical $00000
        clr $FF9E
        clr $FF9F
        lda #1                      screen B is not shown
        sta back
        lbsr render
        lbsr flip

* Let a few fields pass in the new mode before the first snapshot. XRoar
* sets its picture window once for each field, from the mode at the end of
* vertical sync (src/tcc1014/tcc1014.c), so a field that starts in BASIC's
* text mode has the window of that mode.
        lbsr pause
* An arrow held at the start is not a new press.
        lbsr sample
        lda held
        sta previous
* The game loop. "ready" is where the check takes each snapshot. The pause
* keeps the picture still for the capture and sets the scan rate.
ready   lbsr field
        lbsr sample
        ifndef NO_SCAN_STEP
* NO_SCAN_STEP is a fault for the check only.
        lbsr rand
        endc
        lbsr update
        tst dirty
        beq ready
        clr dirty
        lbsr render
        lbsr flip
        bra ready

* pause: about 96000 cycles, 6 fields at the normal clock.
pause   ldx #12000
pwait   leax -1,x
        bne pwait
        rts

* field: wait for a new VBORD, so the keys are scanned once in each field.
field   lda $FF92
fwait   lda $FF92
        bita #%00001000
        beq fwait
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
        bitb #SPACE                 title, won or lost: Space starts a game
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
        ifndef NO_BEST
* NO_BEST is a fault for the check only.
        lbsr record
        endc
        lbsr chime
        inc dirty
unew    rts

* record: the best score is the highest score since the program started.
record  ldd score
        cmpd best
        bhi rnew
        blo rkeep
        lda score+2
        cmpa best+2
        bls rkeep
rnew    ldd score
        std best
        lda score+2
        sta best+2
rkeep   rts

* newgame: an empty board with two microbes.
newgame clr phase
        inc dirty
        clr score
        clr score+1
        clr score+2
        ldx #cells
ngclr   clr ,x+
        cmpx #cells+16
        blo ngclr
        lbsr spawn
        lbsr spawn
        lbra seen

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
        lda #LOST
        sta phase
jplay   rts
won     lda #WON
        sta phase
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
        clr mtop
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
        cmpa mtop
        bls smax
        sta mtop                    the highest new level of this move
smax    lbsr addpts
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

* seen: topseen is the highest level on the board.
seen    clr topseen
        ldx #cells
seloop  lda ,x+
        cmpa topseen
        bls senext
        sta topseen
senext  cmpx #cells+16
        blo seloop
        rts

* chime: after a move, choose a sound. A loss or a win has its own sound.
* Otherwise a merge to a level not seen in this game plays three rising
* notes, and other merges play one note. A move without a merge is silent.
chime   ldx #losesnd
        lda phase
        cmpa #LOST
        beq cplay
        ldx #winsnd
        cmpa #WON
        beq cplay
        lda mtop
        beq cdone
        ifdef FLAT
        suba #1                     a fault for the check only: wrong note
        else
        suba #2                     A: the note, 0 for level 2
        endc
        ldb mtop
        ifndef NO_FIND
* NO_FIND is a fault for the check only.
        cmpb topseen
        bls cblip
        stb topseen
        ldb #16
        mul
        ldx #finds
        abx
        bra cplay
        endc
cblip   ldb #8
        mul
        ldx #blips
        abx
* Start the sound at X. It replaces a sound that plays. Mask FIRQ while
* the timer and the note change. Enable the timer FIRQ, then read $FF93
* to release a request that waits.
cplay   orcc #$40
        lbsr load
        lda #$20
        sta $FF93
        lda $FF93
        andcc #$BF
cdone   rts

* load: start the note at X. Write the reload value low byte first: the
* write to $FF94 starts the timer. At the end of the sound, turn off the
* timer FIRQ.
load    ldd 2,x
        beq lstop
        std edges
        ldd ,x
        stb $FF95
        sta $FF94
        leax 4,x
        stx snote
        rts
lstop   clr $FF93
        rts

* firq: the GIME timer FIRQ. FIRQ saves only CC and PC, so save A, B and
* X. Read $FF93 to release the request. Change the DAC level: one edge of
* the square wave. After the last edge of the note, start the next note.
firq    pshs a,b,x
        lda $FF93
        lda dacval
        eora #$40
        sta dacval
        ora lowbits
        sta $FF20
        ldd edges
        subd #1
        std edges
        bne fdone
        ldx snote
        bsr load
fdone   puls a,b,x
        rti

* sound: the DAC as in examples/timer-sound, and the timer FIRQ. The
* timer FIRQ is enabled for each sound (chime).
sound   lda $FF21                   $FF20 bits 7-2 are outputs
        anda #$FB
        sta $FF21
        lda $FF20
        ora #$FC
        sta $FF20
        lda $FF21
        ora #4
        sta $FF21
        lda $FF20
        anda #3
        sta lowbits
        ora dacval
        sta $FF20                   the DAC at rest
        lda $FF01                   the audio mux selects the DAC
        anda #$F7
        sta $FF01
        lda $FF03
        anda #$F7
        sta $FF03
        lda $FF23                   sound on
        ora #8
        sta $FF23
        lda $FF21                   no PIA FIRQ: CD and cartridge off
        anda #$FE
        sta $FF21
        lda $FF23
        anda #$FE
        sta $FF23
        lda $FF20                   clear their flags
        lda $FF22
        lda #$7E                    JMP firq in the FIRQ jump table entry
        sta $FEF4
        ldd #firq
        std $FEF5
        lda #$20                    fast timer input, executive task
        sta $FF91
        clr $FF93                   no FIRQ source until a sound starts
        lda $FF93
        andcc #$BF                  unmask FIRQ; IRQ stays masked
        rts

* render: make the screen that is not shown hold the picture of the phase.
* Draw only what differs from what that screen holds (its record at dptr).
render  lda back
        ldb #DSIZE
        mul
        addd #desc
        std dptr
        lda back
        lsla
        lsla
        sta bpage                   screen A: pages 0-3; screen B: pages 4-7
        ldx dptr
        lda phase
        cmpa #TITLE
        bne rboard
        lda ,x
        cmpa #TSCENE
        beq rdone
        lbsr clear
        lbsr title
        ldx dptr
        lda #TSCENE
        sta ,x
        clr 1,x
rdone   rts
rboard  lda ,x
        cmpa #BSCENE
        beq rbanner
        lbsr clear                  a new scene: every square must be drawn
        ldx dptr
        lda #BSCENE
        sta ,x
        clr 1,x
        leay 2,x
        lbsr forget                 Y: the scores of the record
        ldb #6
        lbsr forget8
        lbsr labels
        ldx dptr
rbanner lda 1,x                     a banner that must go: make its area
        beq rsq                     black, then draw squares 4-11 again
        cmpa phase
        beq rsq
        clr 1,x
        leay 6,x
        ldb #8
        lbsr forget8
        ifndef KEEP_FRAME
* KEEP_FRAME is a fault for the check only.
        ldd #28*256+72
        std rx
        ldd #104*256+48
        std rw
        clr rval
        lbsr fill
        endc
rsq     lbsr board
        lbsr scores
        ldx dptr
        lda phase
        beq rdone
        cmpa 1,x
        beq rdone
        sta 1,x
        lbra banner

* addpts: add the points of a merge to the score: 2 to the power of the new
* level A, from the table "points" (3 BCD bytes for each level).
addpts  pshs a,b,x
        ldb #3
        mul
        ldx #points
        abx
        lda score+2
        adda 2,x
        ifndef NO_DAA
* NO_DAA is a fault for the check only: binary, not decimal, addition.
        daa
        endc
        sta score+2
        lda score+1
        adca 1,x
        daa
        sta score+1
        lda score
        adca ,x
        daa
        sta score
        puls a,b,x,pc

* labels: "SCORE" and "BEST" above the two numbers.
labels  ldu #t_score
        ldd #SCOREX*256+LABELY
        std rx
        ldd #t_score_bpr*256+t_score_rows
        std rw
        lbsr blit
        ldu #t_best
        ldd #(BESTX+2)*256+LABELY
        std rx
        ldd #t_best_bpr*256+t_best_rows
        std rw
        lbra blit

* scores: draw the score and the best score where they differ from what
* the screen shows.
scores  ldy dptr
        leay DSCORE,y
        ldu #score
        lda #SCOREX
        bsr number
        ldy dptr
        leay DBEST,y
        ldu #best
        lda #BESTX
* number: if the 3 BCD bytes at U differ from the record at Y, copy them
* there and draw their 5 low digits from byte column A.
number  sta nx
        ldd ,u
        cmpd ,y
        bne ndraw
        lda 2,u
        cmpa 2,y
        beq ndone
ndraw   ldd ,u
        std ,y
        lda 2,u
        sta 2,y
        lda ,u+                     the first byte: its low digit only
        stu nptr
        anda #$0F
        bsr digit
        lda #2
        sta ncount
ndigit  lda [nptr]
        lsra
        lsra
        lsra
        lsra
        bsr digit
        ldu nptr
        lda ,u+
        stu nptr
        anda #$0F
        bsr digit
        dec ncount
        bne ndigit
ndone   rts

* digit: draw digit A at byte column nx, row DIGITY; nx moves on 4 bytes.
digit   ldb #32
        mul
        addd #digits
        tfr d,u
        lda nx
        sta rx
        adda #4
        sta nx
        lda #DIGITY
        sta ry
        ldd #4*256+8
        std rw
        lbra blit

* forget: mark 16 squares from Y as unknown ($FF is not a level).
* forget8: mark B squares from Y.
forget  ldb #16
forget8 lda #$FF
fgt     sta ,y+
        decb
        bne fgt
        rts

* flip: show the screen that was just drawn, in the vertical blank. Set the
* square colour of the phase at the same time. Then wait one more VBORD,
* so that the old screen is no longer shown before it is drawn.
flip    lda $FF92                   clear an old VBORD
fwait1  lda $FF92
        bita #%00001000
        beq fwait1
        lda #VIEWA
        tst back
        beq fshow
        lda #VIEWB
fshow   sta $FF9D
        ldx #squarecode
        ldb phase
        lda b,x
        sta $FFB1
        lda $FF92
fwait2  lda $FF92
        bita #%00001000
        beq fwait2
        ifndef ONE_SCREEN
* ONE_SCREEN is a fault for the check only: it draws on the shown screen.
        lda back
        eora #1
        sta back
        endc
        rts

* clear: make the four pages of the screen at bpage black.
clear   lda bpage
        sta page
cpage   lbsr mapwin
        ldx #WINDOW
* Clear in blocks of 256 bytes (774 cycles, 0.87 ms). Sources disagree
* whether an interrupt can stop a TFM, so no TFM is long enough to delay
* the next sound edge by much.
cblock  ldy #zero
        ldw #256
        tfm y,x+
        cmpx #WINDOW+$2000
        blo cblock
        inc page
        lda page
        suba bpage
        cmpa #4
        blo cpage
        rts

* title: the name, the eleven creatures as a family photo on a grey
* backdrop, and "PRESS SPACE".
title   ldd #4*256+44
        std rx
        ldd #152*256+104
        std rw
        lda #GREY
        sta rval
        lbsr fill
        clr square
tpose   ldb square
        lslb
        ldx #photo
        abx
        lda ,x
        sta rx
        lda 1,x
        sta ry
        ldx #sprites
        ldb square
        lslb
        ldu b,x
        lda #c01_bpr
        sta rw
        lda #c01_rows
        sta rh
        lbsr blit
        inc square
        lda square
        cmpa #11
        blo tpose
        ldu #t_evolve
        ldd #(80-t_evolve_bpr/2)*256+12
        std rx
        ldd #t_evolve_bpr*256+t_evolve_rows
        std rw
        lbsr blit
        ldu #t_press
        ldd #(80-t_press_bpr/2)*256+164
        std rx
        ldd #t_press_bpr*256+t_press_rows
        std rw
        lbra blit

* banner: a white frame and a black box over the middle of the board, with
* the result and "PRESS SPACE".
banner  ldd #28*256+72
        std rx
        ldd #104*256+48
        std rw
        lda #$33                    two pixels of register 3, white
        sta rval
        lbsr fill
        ldd #29*256+74
        std rx
        ldd #102*256+44
        std rw
        clr rval
        lbsr fill
        lda phase
        cmpa #WON
        bne bover
        ldu #t_win
        ldd #(80-t_win_bpr/2)*256+80
        std rx
        ldd #t_win_bpr*256+t_win_rows
        std rw
        bra bword
bover   ldu #t_over
        ldd #(80-t_over_bpr/2)*256+80
        std rx
        ldd #t_over_bpr*256+t_over_rows
        std rw
bword   lbsr blit
        ldu #t_press
        ldd #(80-t_press_bpr/2)*256+104
        std rx
        ldd #t_press_bpr*256+t_press_rows
        std rw
        lbra blit

* board: draw each square whose level differs from the screen's record.
board   clr square
bsq     ldx #cells
        ldb square
        lda b,x
        ldx dptr
        leax 2,x
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
        lda #GREY
        sta rval
        ldx #cells                  the creature, if the square has one
        lda square
        lda a,x
        bne bsprite
        lda #CELLH                  an empty square: all grey
        sta rh
        lbsr fill
        bra bnext
* A creature: 2 grey rows, 40 rows of grey byte, creature, grey byte, then
* 2 grey rows. The creature is SPRX-CELLX = 1 byte and SPRY-CELLY = 2 rows
* into the cell, and 24 + 2 = CELLW bytes wide.
bsprite deca
        lsla
        ldx #sprites
        ldu a,x
        lda #SPRY-CELLY
        sta rh
        lbsr fill                   X: the row below, mapped
        lda #c01_rows
        sta count
bsrow   pshs x
        lda #GREY
        sta ,x+
        ldw #c01_bpr
        tfm u+,x+
        sta ,x
        puls x
        lbsr down
        dec count
        bne bsrow
        lda #CELLH-(SPRY-CELLY)-c01_rows
        sta rh
        lbsr fillx
bnext   inc square
        lda square
        cmpa #16
        lblo bsq
        rts

* fill: rh rows of rw bytes of rval, from byte rx of row ry. Returns X at
* the same byte of the row below, with its pages mapped.
* fillx: the same from X.
fill    lbsr rowat
fillx   lda rh
        sta count
frow    pshs x
        clra
        ldb rw
        tfr d,w
        ldy #rval
        tfm y,x+
        puls x
        bsr down
        dec count
        bne frow
        rts

* blit: rh rows of rw bytes from U, to byte rx of row ry.
blit    lbsr rowat
        lda rh
        sta count
brow    pshs x
        clra
        ldb rw
        tfr d,w
        tfm u+,x+
        puls x
        bsr down
        dec count
        bne brow
        rts

* rowat: map the pages that hold byte rx of row ry; X = its CPU address.
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
        addb bpage
        stb page
        bsr mapwin
        anda #$1F
        adda #WINDOW/256
        puls b
        tfr d,x
        rts

* mapwin: page at CPU $6000, the next page at $8000. Changes B only.
mapwin  ldb page
        stb MMUWIN
        incb
        stb MMUWIN+1
        rts

* down: X to the same byte one row lower. A row starts below $8000, so it
* ends below $A000. When X passes $8000, map the next page at $6000.
down    leax BPR,x
        ifndef NO_PAGE_STEP
* NO_PAGE_STEP is a fault for the check only.
        cmpx #WINDOW+$2000
        blo down1
        leax -$2000,x
        inc page
        pshs b
        bsr mapwin
        puls b
        endc
down1   rts

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

* Register 1 (the squares) in each phase: play, won, lost, title.
squarecode fcb $10,WINCODE,LOSECODE,$10

* The family photo: byte column and row of each creature, levels 1 to 11.
* Levels 1-5 stand in front, levels 6-11 behind them.
photo   fcb 20,100,44,100,68,100,92,100,116,100
        fcb 8,52,32,52,56,52,80,52,104,52,128,52

* The points of a merge, by the new level: 2 to that power, as 3 BCD bytes.
points  fcb 0,0,0,0,0,0                    levels 0 and 1: no merge makes them
        fcb $00,$00,$04,$00,$00,$08         levels 2, 3: 4, 8
        fcb $00,$00,$16,$00,$00,$32         levels 4, 5: 16, 32
        fcb $00,$00,$64,$00,$01,$28         levels 6, 7: 64, 128
        fcb $00,$02,$56,$00,$05,$12         levels 8, 9: 256, 512
        fcb $00,$10,$24,$00,$20,$48         levels 10, 11: 1024, 2048

* note: one square-wave note of \1 Hz for \2 ms. The first word is the
* timer reload value. A period of the timer is the reload value plus 2
* counts of 279.365 ns, and each period is half a wave:
* reload = 14318180 / 8 / f - 2. The second word is the number of DAC
* edges: 2 * f * t / 1000. A sound ends with two zero words.
note    macro
        fdb 1789773/\1-2,\1*\2/500
        endm

* The C major scale from C5 (523 Hz) to B6 (1976 Hz). A merge to level L
* uses note L-2: level 2 is C5 and level 11 is E6.
* blips: one short note for a merge. 8 bytes for each level.
blips   note 523,40
        fdb 0,0
        note 587,40
        fdb 0,0
        note 659,40
        fdb 0,0
        note 698,40
        fdb 0,0
        note 784,40
        fdb 0,0
        note 880,40
        fdb 0,0
        note 988,40
        fdb 0,0
        note 1047,40
        fdb 0,0
        note 1175,40
        fdb 0,0
        note 1319,40
        fdb 0,0
* finds: a creature seen for the first time in this game. Three rising
* notes of the scale: L-2, L and L+2. 16 bytes for each level.
finds   note 523,40
        note 659,40
        note 784,80
        fdb 0,0
        note 587,40
        note 698,40
        note 880,80
        fdb 0,0
        note 659,40
        note 784,40
        note 988,80
        fdb 0,0
        note 698,40
        note 880,40
        note 1047,80
        fdb 0,0
        note 784,40
        note 988,40
        note 1175,80
        fdb 0,0
        note 880,40
        note 1047,40
        note 1319,80
        fdb 0,0
        note 988,40
        note 1175,40
        note 1397,80
        fdb 0,0
        note 1047,40
        note 1319,40
        note 1568,80
        fdb 0,0
        note 1175,40
        note 1397,40
        note 1760,80
        fdb 0,0
        note 1319,40
        note 1568,40
        note 1976,80
        fdb 0,0
* The win: C6 E6 G6, then a long C7. The loss: G5 E5, then a long C5.
winsnd  note 1047,80
        note 1319,80
        note 1568,80
        note 2093,240
        fdb 0,0
losesnd note 784,150
        note 659,150
        note 523,300
        fdb 0,0

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
        include "text.asm"
        if c01_bpr-24
        error "c01.asm: a sprite row must be 24 bytes"
        endc
        if c01_rows-40
        error "c01.asm: a sprite must be 40 rows"
        endc

zero    fcb 0                       a zero byte for the clear
mtop    fcb 0                       the highest level made by this move
topseen fcb 0                       the highest level seen in this game
snote   fdb 0                       the next note of the sound
edges   fdb 0                       DAC edges left in this note
dacval  fcb $80                     DAC bits 7-2 now
lowbits fcb 0                       $FF20 bits 1-0, kept as they were
score   fcb 0,0,0                   BCD, most significant byte first
best    fcb 0,0,0
nx      fcb 0
nptr    fdb 0
ncount  fcb 0
cells   rmb 16                      the level in each square; 0 is empty
* The record of each screen: scene, banner (a phase), then 16 levels.
desc    rmb DSIZE*2
dptr    fdb 0                       the record of the screen being drawn
back    fcb 0                       the screen not shown: 0 A, 1 B
bpage   fcb 0                       its first page: 0 or 4
dirty   fcb 0                       the picture must change
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
