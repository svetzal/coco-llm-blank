* Play a tone on the DAC from the main loop (CoCo 1/2, cooperative sound).
*
* The main loop writes every sample. After each block of 256 samples it
* has one slot for frame work, then it starts the next block.
*
* The example is in four parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The context shows a 256x192 screen and moves a
* marker one byte after each block. The marker stands for a game's frame
* work. A project does not need the context.
*
* Sources:
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 13: $FF01 bit 3 = SEL 1, $FF03 bit 3 = SEL 2 (audio mux select).
*     PDF 14: $FF20 bits 2..7 = the 6-bit DAC, bit 1 = RS-232 out,
*       bit 0 = cassette in. $FF21 bit 2 = 0 selects the direction
*       register. $FF23 bit 3 = six-bit sound enable.
*     PDF 26: the CPU clock is 14.31818 MHz / 16.
*     PDF 38, Table 4: SNDEN 1, SEL 1 = 0, SEL 2 = 0 select the DAC.
*   Tandy, Color Computer 2 NTSC Service Manual, PDF 37-38: Sel A and
*     Sel B 00 select the DAC; SNDEN must be high.
*   Leventhal, 6809 Assembly Language Programming, Appendix C,
*     PDF 553-555: the cycle count of each instruction in the sample loop.

        org $3000
* >>> EXAMPLE 1 of 4: Mask interrupts so that nothing delays a sample.
* The sample rate comes from the cycles of the loop. BASIC's interrupt
* handler would add a gap at unknown times.
start   orcc #$50
* <<< END EXAMPLE

* --- CONTEXT: clear the screen and the state, then show the screen.
* The screen setup is the RG6 setup of examples/first-screen.
        clra
        ldx #$0400
clear   sta ,x+
        cmpx #$1C00
        blo clear
        ldx #state
reset   sta ,x+
        cmpx #state_end
        blo reset
        lda #$FF
        sta $1000
        ldd #LOW
        std step
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
        lda $FF22
        anda #7
        ora #$F0
        sta $FF22

* >>> EXAMPLE 2 of 4: Make $FF20 bits 7..2 outputs for the DAC.
* Clear $FF21 bit 2 to select the direction register. Set bits 7..2.
* Keep bits 1..0 and the other control bits. Then select the data
* register again. Keep the current value of bits 1..0 for each sample.
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
* <<< END EXAMPLE

* >>> EXAMPLE 3 of 4: Select the DAC in the audio mux and enable sound.
* Clear SEL 1 ($FF01 bit 3) and SEL 2 ($FF03 bit 3). Set SNDEN
* ($FF23 bit 3). Keep the other control bits.
        lda $FF01
        anda #$F7
        sta $FF01
        lda $FF03
        anda #$F7
        sta $FF03
        lda $FF23
        ora #8
        sta $FF23
* <<< END EXAMPLE

* >>> EXAMPLE 4 of 4: Write one sample on each pass of the loop.
* A 16-bit phase advances by the step on each sample. The high byte of
* the phase is the waveform. The tone is
*   894,886.25 Hz / 41 cycles * step / 65,536.
* The loop takes 41 cycles: LDD 6, ADDD 7, STD 6, ANDA 2, ORA 5, STA 5,
* DEC 7, BNE 3 (Leventhal PDF 553-555).
* LOW is about 682 Hz and HIGH is about 1364 Hz.
LOW     equ $0800
HIGH    equ $1000
        ifdef SQUARE
* Square wave: phase bit 7 only. DAC values 0 and 32.
WAVE    equ $80
        else
* Sawtooth: phase bits 7..2. All 64 DAC values.
WAVE    equ $FC
        endc
tick    ldd phase
        addd step
        std phase
        anda #WAVE
        ora low_bits
sample  sta $FF20
        dec divider
        bne tick
* The slot after each block of 256 samples. Keep its work short: it
* delays one sample. Choose the step for the next block here. Each note
* lasts 16 blocks: LOW, then HIGH, then LOW again.
        inc blocks
        lda blocks
        bita #16
        beq low_note
        ldd #HIGH
        bra set_step
low_note
        ldd #LOW
set_step
        std step
* <<< END EXAMPLE

* --- CONTEXT: the frame work. Move the marker one byte along row 96.
        ldx #$1000
        ldb position
        clr b,x
        incb
        andb #31
        stb position
        lda #$FF
        sta b,x
* The check takes its snapshot here, after each block.
frame_ready
        bra tick

* --- CONTEXT: the state. The context above clears it.
state
phase   rmb 2
step    rmb 2
blocks  rmb 1
position rmb 1
low_bits rmb 1
divider rmb 1
state_end
        end start
