* Show only finished frames: draw into a hidden screen, then show it with
* one write (a page flip).
*
* Two 256x192 two-colour screens, at CPU $0400 and $2400, hold 6144 bytes
* each. The program draws each frame into the screen that the display does
* not show. At the end of the active display, one write shows that screen.
* Then the program waits for the next field before it draws into the other
* screen.
*
* Two builds:
*   Main build (CoCo 1, CoCo 2 and CoCo 3): RG6. The screens differ only in
*     SAM display offset bit F4. One write to $FFCE or $FFCF flips them. The
*     wait uses the field-sync (FS) flag of the PIA at $FF03.
*   COCO3 define (variant "coco3", CoCo 3 only): the GIME's native 256x192
*     two-colour graphics. The screens differ only in $FF9D. One write to
*     $FF9D flips them. The wait uses the vertical border (VBORD) flag at
*     $FF92.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up the graphics mode and
* draws a moving scene, two rectangles over a checker background. A project
* does not need the context.
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
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90 bits (COCO, MMU, IEN, MC3, MC2, ROM map); $FF92 bit 3 =
*       VBORD.
*     PDF 13: $FF9D = Y18..Y11, $FF9E = Y10..Y3. In CoCo mode, SAM F6..F0
*       give Y15..Y9 and Y18..Y16 are 1.
*     PDF 18: 256 pixels, 2 colours is HRES 010, CRES 00.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 29: a 128K CoCo 3 ignores Y18 and Y17, so each group of 128K
*       holds the same RAM.
*     PDF 44, Fig. 5-1: in the CoCo modes, $FF9D bits 7..5, SAM F6..F0 and
*       $FF9E bits 5..0 give the physical buffer address.
*     PDF 39: native graphics need BP ($FF98 bit 7) set and $FF90 bit 7
*       clear. In 2-colour modes bit 7 is the leftmost pixel, and a bit
*       selects palette register 0 or 1.
*     PDF 49: the PIA interrupts stay; the GIME interrupts are in addition.
*     PDF 50: an $FF92 bit sets only if Init0 ($FF90) enables IRQ; a read
*       of $FF92 clears the request.
*     PDF 56-57: BASIC's reset maps CPU pages to physical $38-$3F, loads
*       $FF9C = $0F, $FF9D = $E0 and the other $FF98-$FF9F with 0, writes
*       $CE to $FF90 and loads the palette registers.

* >>> EXAMPLE 1 of 3: two screens that differ in one address bit.
* $0400 / 512 = 2 (F4 = 0). $2400 / 512 = 18 (F4 = 1). Each screen is
* 6144 bytes, so the two screens do not overlap.
SCREEN_A equ $0400
SCREEN_B equ $2400
        ifdef COCO3
* BASIC's map puts CPU $0400 at physical $70400 and $2400 at $72400.
* Physical address = $FF9D * 2048 + $FF9E * 8:
* $70400 = $E0 * 2048 + $80 * 8 and $72400 = $E4 * 2048 + $80 * 8.
VIEW_A  equ $E0
VIEW_B  equ $E4
VIEW_LO equ $80
        endc
* <<< END EXAMPLE

* The code follows SCREEN_B. On a CoCo 3, BASIC's reset runs its own code
* at $4000-$436C (Tepolt PDF 56, step 8).
        org $3C00
        ifdef COCO3
* --- CONTEXT: show native 256x192 graphics, two colours, from SCREEN_A.
* $FF98 = $80: BP on, one scan line for each row. $FF99 = $08: 192 rows,
* HRES 010, CRES 00. Keep BASIC's palette, border and horizontal offset.
start   lda #$80
        sta $FF98
        lda #$08
        sta $FF99
        lda #VIEW_A
        sta $FF9D
        lda #VIEW_LO
        sta $FF9E
        else
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
        endc

* >>> EXAMPLE 2 of 3: set up the field flag, then start in the hidden
* screen.
        ifdef COCO3
* $FF92 bit 3: the VBORD flag. The flag sets only when $FF90 bit 5 (IEN)
* is on, and then the GIME also sends an IRQ to the CPU. Mask IRQ so that
* no interrupt handler reads $FF92 and takes the flag.
        orcc #%00010000
* $FF90 = $6E: BASIC's $CE with COCO (bit 7) off for native video and IEN
* (bit 5) on.
        lda #$6E
        sta $FF90
        lda #%00001000
        sta $FF92
        else
* $FF03 bit 0 = 0: no IRQ, so no interrupt handler reads $FF02 and takes the
* flag. Bit 1 = 0: set the flag at the falling edge of FS, the end of the
* active display. Bit 2 = 1: $FF02 is the data register. Keep bits 5..3.
        lda $FF03
        anda #%11111100
        ora #%00000100
        sta $FF03
        endc
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
        ifdef COCO3
* Read $FF92 to clear an old request. Then wait for a new VBORD.
        lda $FF92
wait_vb lda $FF92
        bita #%00001000
        beq wait_vb
* One write to $FF9D shows the screen that was just drawn.
        lda drawing
        cmpa #SCREEN_B/256
        bne show_a
        lda #VIEW_B
        bra show
show_a  lda #VIEW_A
show    sta $FF9D
        else
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
        endc
* The check takes a snapshot each time the program reaches this label.
published
* The display must use the new screen before the program draws into the old
* one.
        ifdef COCO3
* Wait for one more VBORD.
        lda $FF92
wait_new
        lda $FF92
        bita #%00001000
        beq wait_new
        else
* Select the rising edge of FS, clear the flag and wait for the edge. Then
* select the falling edge again.
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
        endc
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

* --- CONTEXT: two 16x8 rectangles. A has pixels 1 at column xpos. B has
* pixels 0 at column 30 - xpos. Both are at row ypos.
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
