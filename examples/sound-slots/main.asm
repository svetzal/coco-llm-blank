* Original cooperative sound experiment. CoCo 1 NTSC, 32 KiB, stock clock.
* Read README.md for hardware sources and the deliberately uneven sample timing.
* Screen $0400-$1BFF, code/state $3000+, stack $7E00-$7EFF.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        ldx #$0400
clear   sta ,x+
        cmpx #$1C00
        blo clear
        ldx #state
reset   sta ,x+
        cmpx #state_end
        blo reset
        lda #$A5
        sta $03FF
        sta $1C00
        lda #$FF
        sta $1000
        ldd #$0800
        std pitch
* Same sourced 256x192 display setup as first-screen.
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
* DAC output bits, preserving the serial/cassette bits and PIA control fields.
        lda $FF21
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
        sta low_bits
* Select DAC in the shared audio/joystick mux. Select keyboard data registers.
        lda $FF01
        anda #$F3
        sta $FF01
        clr $FF00
        ora #4
        sta $FF01
        lda $FF03
        anda #$F3
        sta $FF03
        ldb #$FF
        stb $FF02
        ora #4
        sta $FF03
        lda #$FF
        sta $FF02
        lda $FF23
        ora #8
        sta $FF23
* Sawtooth phase accumulator. Every 256 samples, service input and graphics.
tick    ldd phase
        addd pitch
        std phase
        anda #$FC
        ora low_bits
sample  sta $FF20
        ldd samples
        addd #1
        std samples
        dec divider
        bne tick
        lda $FF00
        anda #1
        ifdef SCRIPTED
* Test-only input substitution AFTER the real PIA read. Never physical-input proof.
        lda frames+1
        anda #16
        lsra
        lsra
        lsra
        lsra
        eora #1
        endc
        sta button
        ldd #$0800
        tst button
        bne set_pitch
        ldd #$1000
set_pitch
        std pitch
        ldx #$1000
        ldb position
        clr b,x
        incb
        andb #31
        stb position
        lda #$FF
        sta b,x
        ldd frames
        addd #1
        std frames
frame_ready
        bra tick
state
phase   rmb 2
pitch   rmb 2
samples rmb 2
frames  rmb 2
position rmb 1
button  rmb 1
low_bits rmb 1
divider rmb 1
state_end
        end start
