* Original CoCo 3 timer/cooperative comparison, NTSC, 128 KiB, slow 6809.
* Read README.md for sources, timer revision, and measurement limits.
* Screen $0400-$1BFF, code/state $3000+, stack $7E00-$7EFF.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
* Keep executive mapping, compatibility display, and fixed FExx vector RAM.
* Tepolt PDF 48-52, 56-57,60; service manual PDF 11-12,18.
        lda #$CE
        sta $FF90
        clr $FF91
        sta $FFDF
        clr $FF92
        clr $FF93
        clr $FF95
        clr $FF94
* Establish known PIA controls with all interrupt sources disabled.
        lda #$34
        sta $FF01
        sta $FF03
        sta $FF21
        sta $FF23
        lda $FF00
        lda $FF02
        lda $FF20
        lda $FF22
        clra
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
* Select DAC in the shared audio/joystick mux.
        lda $FF01
        anda #$F7
        sta $FF01
        lda $FF03
        anda #$F7
        sta $FF03
        lda $FF23
        ora #8
        sta $FF23
* Fixed-step oscillator is shared by both scheduling builds.
        ifdef TIMER
        lda #$7E
        sta $FEF4
        ldd #handler
        std $FEF5
        lda #$DE
        sta $FF90
        lda #$20
        sta $FF91
        sta $FF93
        lda $FF92
        lda $FF93
* Low byte first. MSB write starts the 12-bit timer; 510 is intentional.
        lda #$FE
        sta $FF95
        lda #1
        sta $FF94
        andcc #$BF
        endc
main_loop
        ifndef TIMER
        jsr emit
        endc
        lda samples
        cmpa last_block
        beq main_loop
        sta last_block
* The heavy build clears the framebuffer, representing a costly redraw.
        ifdef HEAVY
        ldx #$0400
        clra
redraw  sta ,x+
        cmpx #$1C00
        blo redraw
        endc
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
        bra main_loop
        ifdef TIMER
handler pshs a,b
        ifdef NO_ACK
        lda #$20
        else
        lda $FF93
        endc
        bita #$20
        beq restore
        jsr emit
restore puls a,b
        rti
        endc
emit    ldd phase
        addd #$0800
        std phase
        anda #$FC
        ora low_bits
sample  sta $FF20
        ldd samples
        addd #1
        std samples
        rts
state
phase   rmb 2
samples rmb 2
frames  rmb 2
position rmb 1
last_block rmb 1
low_bits rmb 1
state_end
        end start
