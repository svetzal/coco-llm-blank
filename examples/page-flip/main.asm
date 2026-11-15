* Show only finished frames on a CoCo 1/2: draw into a hidden screen, then
* show it with one SAM write (a page flip).
*
* Two RG6 screens, at $0400 and $2400, differ only in SAM display offset
* bit F4. The program draws each frame into the screen that the VDG does not
* show. At the end of the active display, one write to $FFCE or $FFCF shows
* that screen. Then the program waits for the next field before it draws into
* the other screen.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up RG6 and draws a moving
* scene, two rectangles over a checker background. A project does not need
* the context.
*
* Sources:
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 13: $FF03 bit 0 = field-sync (FS) IRQ enable, bit 1 = FS edge
*       (0 = falling), bit 2 = 1 selects the data register $FF02,
*       bit 7 = FS flag.
*     PDF 15: SAM display offset F6..F0 in 1/2K units. F4 is $FFCE (clear)
*       and $FFCF (set).
*     PDF 14 and 31: $FF22 bits; RG6 is SAM V=110 and $FF22 bits 7..4 1111.
*   Motorola, MC6821 PIA datasheet, PDF 10, Figure 18: a read of the data
*     register clears the flag.
*   Motorola, MC6847 datasheet, PDF 22: FS goes low at the end of the
*     display window, for 32 scan lines.

* >>> EXAMPLE 1 of 3: two screens that differ in one SAM offset bit.
* $0400 / 512 = 2 (F4 = 0). $2400 / 512 = 18 (F4 = 1). Each RG6 screen is
* 6144 bytes, so the two screens do not overlap.
SCREEN_A equ $0400
SCREEN_B equ $2400
* <<< END EXAMPLE

        org $4000
* --- CONTEXT: show RG6 at $0400 with colour set 0, as in first-screen.
* SAM offset F=2 ($0400 / 512), then SAM mode V=110. Keep $FF22 bits 2..0.
start   sta $FFC6
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
        ora #%11110000
        sta $FF22

* >>> EXAMPLE 2 of 3: set up the field-sync flag, then start in the hidden
* screen.
* $FF03 bit 0 = 0: no IRQ, so no interrupt handler reads $FF02 and takes the
* flag. Bit 1 = 0: set the flag at the falling edge of FS, the end of the
* active display. Bit 2 = 1: $FF02 is the data register. Keep bits 5..3.
        lda $FF03
        anda #%11111100
        ora #%00000100
        sta $FF03
        ldd #SCREEN_B
        std drawing
* <<< END EXAMPLE

* --- CONTEXT: start the scene at the top-left corner.
        clra
        sta xpos
        sta ypos
        sta frames
        sta frames+1
        inca
        sta xstep
        sta ystep

* --- CONTEXT: draw one complete frame into the screen at 'drawing'.
frame   ldd frames
        addd #1
        std frames
        jsr background
* Change the layer order every 32 frames.
        lda frames+1
        anda #32
        bne reversed
        jsr object_a
        jsr object_b
        bra drawn
reversed
        jsr object_b
        jsr object_a
drawn

* >>> EXAMPLE 3 of 3: show the finished screen, then draw into the other.
* Read $FF02 to clear an old flag. Then wait for a new falling edge of FS.
        lda $FF02
wait_fs lda $FF03
        bpl wait_fs
* One write to F4 shows the screen that was just drawn.
        lda drawing
        cmpa #SCREEN_B/256
        bne show_a
        sta $FFCF
        bra published
show_a  sta $FFCE
* The check takes a snapshot each time the program reaches this label.
published
* The display must use the new screen before the program draws into the old
* one. Select the rising edge of FS, clear the flag and wait for the edge.
* Then select the falling edge again.
        lda $FF03
        ora #%00000010
        sta $FF03
        lda $FF02
wait_new
        lda $FF03
        bpl wait_new
        lda $FF03
        anda #%11111101
        sta $FF03
* Draw the next frame into the screen that is not shown.
* (SCREEN_A XOR SCREEN_B) / 256 = $20.
        lda drawing
        eora #$20
        sta drawing
* <<< END EXAMPLE

        jsr advance
        bra frame

* --- CONTEXT: an 8x8 checker background. Invert it every 64 frames.
background
        ldx drawing
        clr row
bg_row  lda row
        anda #8
        beq bg_zero
        lda #$FF
        bra bg_colour
bg_zero clra
bg_colour
        ldb frames+1
        bitb #64
        beq bg_span
        coma
bg_span ldb #32
bg_byte sta ,x+
        coma
        decb
        bne bg_byte
        inc row
        lda row
        cmpa #192
        blo bg_row
        rts

* --- CONTEXT: two 16x8 rectangles. A is green at column xpos. B is black at
* column 30 - xpos. Both are at row ypos.
object_a
        lda #$FF
        sta ink
        ldb xpos
        bra rectangle
object_b
        clr ink
        ldb #30
        subb xpos
rectangle
        stb column
        lda ypos
        ldb #32
        mul
        addd drawing
        tfr d,x
        clra
        ldb column
        leax d,x
        ldb #8
        lda ink
rectrow sta ,x
        sta 1,x
        leax 32,x
        decb
        bne rectrow
        rts

* --- CONTEXT: move one step. Reverse at each edge: columns 0..30,
* rows 0..184.
advance
        lda xpos
        bne x_right
        ldb #1
        stb xstep
x_right cmpa #30
        bne x_move
        ldb #$FF
        stb xstep
x_move  adda xstep
        sta xpos
        lda ypos
        bne y_bottom
        ldb #1
        stb ystep
y_bottom
        cmpa #184
        bne y_move
        ldb #$FF
        stb ystep
y_move  adda ystep
        sta ypos
        rts

* --- CONTEXT: program state. This is a data label: the check fails if the
* CPU executes it.
state
drawing rmb 2
frames  rmb 2
xpos    rmb 1
ypos    rmb 1
xstep   rmb 1
ystep   rmb 1
row     rmb 1
column  rmb 1
ink     rmb 1
        end start
