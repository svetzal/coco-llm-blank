* Original masked-object experiment. Sources and memory contract: README.md.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        sta scene
        lda #$A5
        sta $03FF
        sta $1C00
* SAM base $0400, page 0, normal clock, V=110.
        sta $FFC6
        sta $FFC9
        sta $FFCA
        sta $FFCC
        sta $FFCE
        sta $FFD0
        sta $FFD2
        sta $FFD4
        sta $FFD6
        sta $FFD8
        sta $FFC0
        sta $FFC3
        sta $FFC5
        lda $FF23
        ora #4
        sta $FF23
        lda $FF22
        anda #7
        ora #$F0
        sta $FF22
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
frame_ready
* Finite scene sequence repeats for the interactive demo.
        ldy #$FFFF
pause   leay -1,y
        bne pause
        inc scene
        lda scene
        cmpa #12
        blo next_scene
        clr scene
        bra next_scene
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
object_a
        ldx current
        ldd ,x
        ldu #shape_a
        bra place
object_b
        ldx current
        ldd 2,x
        ldu #shape_b
place
* A = byte column (0..30); B = row (0..182). No clipping contract.
        sta column
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
masked_row
* Each source row: preserve mask (16 bits), then ink (16 bits).
* Ink bits under preserve bits are zero. Transparent bits retain destination.
        ldd ,x
        anda ,u+
        andb ,u+
        ora ,u+
        orb ,u+
        std ,x
        leax 32,x
        dec rows_left
        bne masked_row
        rts
* Data must never execute: the negative-control trap uses this label.
state
scene   fcb 0
current fdb 0
row     fcb 0
column  fcb 0
rows_left fcb 0
* Ax-byte, Ay, Bx-byte, By, invert background, order (0 none,1 AB,2 BA).
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
* Hollow rings: transparent outer rows, opaque top/bottom, transparent centre.
* A has green top/left and black bottom/right; B has the opposite colours.
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
program_end
        end start
