* Original hidden-screen adaptation of moving-objects; baseline is unchanged.
* Sources, memory map and isolated target contract: README.md.
* IRQ/FIRQ masked; no ROM calls. Markers $3F00-$3F03 measure emulated cost.
        org $4000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        sta xpos
        sta ypos
        sta frames
        sta frames+1
        lda #1
        sta xstep
        sta ystep
        lda #$A5
        sta $03FF
        sta $1C00
        sta $23FF
        sta $3C00
        ldd #$2400
        std drawing
* Preserve PIA mux bits; select data, falling FS, disable its IRQ output.
        lda $FF03
        anda #$FC
        ora #4
        sta $FF03
* Same sourced RG6 setup as first-screen. Base $0400, V=110, slow clock.
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
frame   sta $3F00
        ldd frames
        addd #1
        std frames
        jsr background
* Change layer order every 32 frames, so both overlap orders get exercised.
        lda frames+1
        anda #32
        bne reversed
        jsr object_a
        jsr object_b
        bra frame_ready
reversed
        jsr object_b
        jsr object_a
frame_ready
* The hidden scene is complete. Discard a stale FS flag after drawing.
        sta $3F01
        lda $FF02
wait_fs lda $FF03
        bpl wait_fs
* One F4 strobe selects $0400 or $2400 before the next FS rising edge.
        lda drawing
        cmpa #$24
        bne show_low
        sta $FFCF
        bra published
show_low
        sta $FFCE
published
        sta $3F02
* XRoar reloads SAM at FS rise. Retain the old front until that event.
* This establishes emulator adoption, not an exact silicon latch contract.
        lda $FF03
        ora #2
        sta $FF03
        lda $FF02
wait_adopt
        lda $FF03
        bpl wait_adopt
        sta $3F03
        lda $FF03
        anda #$FD
        sta $FF03
        lda drawing
        eora #$20
        sta drawing
        jsr advance
        bra frame
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
* Invert scenery every 64 frames, including beneath the objects.
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
advance
* Reverse before an out-of-bounds move; do not dwell on the boundary.
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
* The following data address is never an instruction checkpoint.
state
drawing fdb 0
frames  fdb 0
xpos    fcb 0
ypos    fcb 0
xstep   fcb 0
ystep   fcb 0
row     fcb 0
column  fcb 0
ink     fcb 0
program_end
        end start
