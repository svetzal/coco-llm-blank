* Draw a byte-aligned object over scenery with a software mask (CoCo 1-3).
*
* Each screen byte under the object becomes (screen AND mask) OR ink.
* A mask bit of 1 keeps the scenery pixel. A mask bit of 0 replaces it with
* the ink bit. Ink is 0 under each mask bit of 1, so opaque black is not
* transparent.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up RG6, redraws a checker
* background for each of 12 scenes, then draws two objects in the scene's
* order. A project does not need the context.
*
* Variants (coco.toml) replace part 2 with the other two draw methods:
*   (none)  mask    (screen AND mask) OR ink
*   OPAQUE  opaque  ink only: the full 16x10 box replaces the scenery
*   XOR     xor     screen XOR ink: lit ink inverts, black ink does nothing
*
* Sources:
*   Inman, Inman and Dymax, Assembly Language Graphics for the TRS-80 Color
*     Computer, PDF 106-107: RG6 (6R) is 256x192, 8 pixels per byte, 6 KiB.
*     Colour set 0: 0 is black, 1 is green.
*   Motorola, MC6847 datasheet, PDF 19 Table 3: bit 7 is the leftmost pixel.
*   Tandy, Color Computer Technical Reference Manual, PDF 14-15 and 31:
*     SAM offset and mode bits, $FF22 bits; RG6 is SAM V=110, $FF22 $F0.
*   Tepolt, Assembly Language Programming for the CoCo3, PDF 46: on a CoCo 3
*     the same $FF22 and SAM values select G6R (RG6); each bit selects
*     palette register 8 or 9 (colour set 0), which BASIC loads (PDF 57).

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
        clr scene

* --- CONTEXT: redraw the background, then draw the objects in scene order.
next_scene
        lda scene
        ldb #6
        mul
        ldx #scenes
        leax d,x
        stx current
        jsr background
        ldx current
        lda 5,x
        beq frame_ready
        cmpa #2
        beq reverse
        jsr object_a
        jsr object_b
        bra frame_ready
reverse jsr object_b
        jsr object_a
* The check takes one snapshot each time the program reaches this label.
frame_ready
* Wait so that a person can see each scene in `run`. A project removes it.
        ldy #$FFFF
pause   leay -1,y
        bne pause
        inc scene
        lda scene
        cmpa #12
        blo next_scene
        clr scene
        bra next_scene

* --- CONTEXT: fill the screen with 8x8 checker squares, inverted on request.
background
        ldx #$0400
        clr row
bg_row  lda row
        anda #8
        beq bg_zero
        lda #$FF
        bra bg_invert
bg_zero clra
bg_invert
        ldy current
        tst 4,y
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

* --- CONTEXT: pick the origin and shape of object A or B for this scene.
object_a
        ldx current
        ldd ,x
        ldu #shape_a
        bra place
object_b
        ldx current
        ldd 2,x
        ldu #shape_b

* >>> EXAMPLE 1 of 3: find the screen byte of the object's top-left corner.
* A = byte column (0..30). B = pixel row (0..182). The object must fit on the
* screen: there is no clipping. Address = $0400 + 32 * row + column.
place   sta column
        tfr b,a
        ldb #32
        mul
        addd #$0400
        tfr d,x
        clra
        ldb column
        leax d,x
        lda #10
        sta rows_left
* <<< END EXAMPLE

* >>> EXAMPLE 2 of 3: draw one row of two bytes, then step to the next row.
* U points to the row's mask word, then its ink word.
draw_row
        ifdef OPAQUE
        leau 2,u
        ldd ,u++
        else
        ifdef XOR
        leau 2,u
        ldd ,x
        eora ,u+
        eorb ,u+
        else
        ldd ,x
        anda ,u+
        andb ,u+
        ora ,u+
        orb ,u+
        endc
        endc
        std ,x
        leax 32,x
        dec rows_left
        bne draw_row
        rts
* <<< END EXAMPLE

* --- CONTEXT: program state. This is a data label: the check fails if the
* CPU executes it.
state
scene   rmb 1
current rmb 2
row     rmb 1
column  rmb 1
rows_left rmb 1
* --- CONTEXT: six bytes for each scene: A column, A row, B column, B row,
* inverted background (0 or 1), draw order (0 none, 1 A then B, 2 B then A).
scenes  fcb 0,0,30,182,0,1
        fcb 30,0,0,182,0,1
        fcb 14,88,15,88,0,1
        fcb 14,88,15,88,0,2
        fcb 14,88,14,88,0,1
        fcb 14,88,14,88,0,2
        fcb 2,20,27,160,0,1
        fcb 2,20,27,160,0,0
        fcb 14,88,15,88,1,1
        fcb 14,88,15,88,1,2
        fcb 14,88,15,88,1,0
        fcb 0,182,30,0,1,1

* >>> EXAMPLE 3 of 3: the shape data, 16x10 pixels.
* Each row is a 16-bit mask, then 16-bit ink. Bit 15 is the leftmost pixel.
* Ink must be 0 wherever the mask is 1.
* Rows 0 and 9 and the centre are transparent. A has a green top and left
* edge and a black bottom and right edge. B has the opposite colours.
shape_a fdb $FFFF,$0000
        fdb $0000,$FFFF
        fdb $7FFE,$8000
        fdb $7FFE,$8000
        fdb $7FFE,$8000
        fdb $7FFE,$8000
        fdb $7FFE,$8000
        fdb $7FFE,$8000
        fdb $0000,$0000
        fdb $FFFF,$0000
shape_b fdb $FFFF,$0000
        fdb $0000,$0000
        fdb $7FFE,$0001
        fdb $7FFE,$0001
        fdb $7FFE,$0001
        fdb $7FFE,$0001
        fdb $7FFE,$0001
        fdb $7FFE,$0001
        fdb $0000,$FFFF
        fdb $FFFF,$0000
* <<< END EXAMPLE
        end start
