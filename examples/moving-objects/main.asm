* Move objects over scenery without holes in it (CoCo 1/2, RG6).
*
* Each frame first puts back the scenery where the objects were. Then it draws
* the objects at their new places, the bottom layer first. The default method
* keeps a second copy of the scenery in RAM, the scenery buffer, and copies
* the old rectangles back from it. When the scenery changes, the program
* draws the new scenery into the buffer and shows all of it.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up RG6, draws an 8x8 checker
* scenery that inverts every 64 frames, moves two opaque 16x8 rectangles that
* bounce off the edges, and swaps their layer order every 32 frames. A project
* does not need the context.
*
* Variants (coco.toml) select another way to put back the scenery:
*   (none)  buffer  copy the old rectangles from a 6 KiB scenery buffer
*   SAVE    save    keep the screen bytes under each object, put them back
*                   in the reverse of the draw order
*   REDRAW  redraw  draw all of the scenery again in each frame
*
* Sources:
*   Inman, Inman and Dymax, Assembly Language Graphics for the TRS-80 Color
*     Computer, PDF 106-107: RG6 (6R) is 256x192 at $0400-$1BFF, 8 pixels
*     per byte. Colour set 0: 0 is black, 1 is green. PDF 162: the book
*     erases the old shape with CLR, which also erases scenery.
*   Motorola, MC6847 datasheet, PDF 19 Table 3: bit 7 is the leftmost pixel.
*   Tandy, Color Computer Technical Reference Manual, PDF 14-15 and 31:
*     SAM offset and mode bits, $FF22 bits; RG6 is SAM V=110, $FF22 $F0.

SCREEN  equ $0400               the RG6 screen, 32 bytes x 192 rows
SCENERY equ $4400               buffer method: the scenery, SCREEN + $4000
        ifdef SAVE
SLOT    equ 18                  screen address, then 8 rows of 2 bytes
        else
SLOT    equ 2                   screen address only
        endc
        ifndef SAVE
        ifndef REDRAW
BUFFER  equ 1                   the default method
        endc
        endc

        org $3000
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
        clra
        clrb
        std frames
        std xpos                xpos and ypos
        lda #1
        sta xstep
        sta ystep

* --- CONTEXT: count the frame. The scenery is new in frame 1, and it
* changes in each 64th frame.
frame   ldd frames
        addd #1
        std frames
        cmpd #1
        beq new_scenery
        andb #63
        beq new_scenery

* >>> EXAMPLE 1 of 3: put back the scenery where the objects were.
* Do this for all the objects before you draw any object.
        ifdef REDRAW
        bra new_scenery         redraw: all of the scenery, in each frame
        else
        ifdef SAVE
        ldu #slots+SLOT         the object drawn last goes back first
        bsr put_back
        ldu #slots
        bsr put_back
        else
        ldx slots               the buffer: any order is correct
        bsr copy_back
        ldx slots+SLOT
        bsr copy_back
        endc
        bra draw_objects
        endc

        ifdef SAVE
* U = a slot. Write its 16 saved bytes back to the screen.
put_back
        ldx ,u++
        ldb #8
pb_row  ldy ,u++
        sty ,x
        leax 32,x
        decb
        bne pb_row
        rts
        endc
        ifdef BUFFER
* X = the screen address of an old rectangle. Copy it from the buffer.
copy_back
        ldb #8
cb_row  ldy SCENERY-SCREEN,x
        sty ,x
        leax 32,x
        decb
        bne cb_row
        rts
        endc
* <<< END EXAMPLE

* >>> EXAMPLE 2 of 3: when the scenery changes, show all of the new scenery.
* This also removes the old objects.
new_scenery
        ifdef BUFFER
        ldx #SCENERY            change the buffer first
        jsr scenery
        ldx #SCREEN             then copy all of it to the screen
show_all
        ldd SCENERY-SCREEN,x
        std ,x++
        cmpx #SCREEN+6144
        blo show_all
        else
        ldx #SCREEN             save, redraw: draw it on the screen
        jsr scenery
        endc
* <<< END EXAMPLE

* >>> EXAMPLE 3 of 3: draw the objects at their new places, bottom layer
* first. Each object records where it is, for the next frame.
draw_objects
        ldu #slots              slot 0 is the object drawn first
        lda frames+1
        anda #32                context: swap the layers every 32 frames
        bne b_first
        bsr object_a
        bsr object_b
        bra frame_ready
b_first bsr object_b
        bsr object_a
        bra frame_ready

* X = the screen address of the top-left byte, A = the ink, U = the next slot.
* Draw one opaque 16x8 rectangle.
rectangle
        stx ,u++
        ifdef SAVE
        pshs a,x                keep the screen bytes under the rectangle
        ldb #8
save_row
        ldy ,x
        sty ,u++
        leax 32,x
        decb
        bne save_row
        puls a,x
        endc
        ldb #8
draw_row
        sta ,x
        sta 1,x
        leax 32,x
        decb
        bne draw_row
        rts
* <<< END EXAMPLE

* --- CONTEXT: the check takes one snapshot each time the program reaches
* this label. The pause keeps the picture still for the check's capture of
* the rendered frame, and slows the motion for a person.
frame_ready
        ldx #4096
pause   leax -1,x
        bne pause
        bsr advance
        jmp frame

* --- CONTEXT: object A is green and object B is black. Both are at pixel
* row ypos. A is at byte column xpos. B is at byte column 30 - xpos.
object_a
        ldb xpos
        lda #$FF
        bra place
object_b
        ldb #30
        subb xpos
        clra
place   sta ink
        stb column
        lda ypos
        ldb #32
        mul
        addd #SCREEN
        addb column
        adca #0
        tfr d,x
        lda ink
        bra rectangle

* --- CONTEXT: move one byte column and one pixel row in each frame. Reverse
* at an edge, so that the full rectangle stays on the screen.
advance lda xpos
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

* --- CONTEXT: X = the destination. Fill 6144 bytes with 8x8 checker
* squares. Bit 6 of the frame count inverts them.
scenery clr row
sc_row  lda row
        anda #8
        beq sc_even
        lda #$FF
        bra sc_invert
sc_even clra
sc_invert
        ldb frames+1
        bitb #64
        beq sc_span
        coma
sc_span ldb #32
sc_byte sta ,x+
        coma
        decb
        bne sc_byte
        inc row
        lda row
        cmpa #192
        blo sc_row
        rts

* --- CONTEXT: program state. This is a data label: the check fails if the
* CPU executes it.
state
frames  rmb 2
xpos    rmb 1
ypos    rmb 1
xstep   rmb 1
ystep   rmb 1
row     rmb 1
column  rmb 1
ink     rmb 1
slots   rmb 2*SLOT
* The build fails if the program reaches the scenery buffer (coco.toml).
program_end
        end start
