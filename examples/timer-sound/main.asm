* Write DAC samples from the CoCo 3 GIME timer interrupt (FIRQ).
*
* The timer interrupts the main loop at a fixed rate. The handler writes
* one sample. The main loop is free to draw, and the sound continues.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The context shows a 256x192 screen, sets up the DAC,
* and moves a marker after each block of 256 samples. The HEAVY build
* also clears the full screen before each move. The COOPERATIVE builds
* write the samples from the main loop instead, for comparison.
*
* Sources:
*   Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 47: FIRQ pushes only CC and PC.
*     PDF 48: the FIRQ vector leads to the jump table entry at $FEF4.
*     PDF 49-51: Init0 bit 4 enables GIME FIRQ. Init1 bit 5 selects the
*       fast timer input. FIRQEN bit 5 is the timer. A read of FIRQEN
*       releases the request. The timer reloads itself.
*     PDF 52-53: mask interrupts, turn off the PIA sources, bleed off the
*       flags, set the jump table, then unmask. The handler reads the
*       enable register to release the request.
*     PDF 55: BASIC runs with the executive task registers.
*     PDF 57: at reset, BASIC puts the jump table in RAM at
*       $FEEE-$FEFF, selects all-RAM mode and sets Init0 to $CE.
*   Leventhal, 6809 Assembly Language Programming, PDF 554: JMP
*     extended is $7E.
*   Tandy, Color Computer 3 Service Manual:
*     PDF 10: $FF21 bit 0 and $FF23 bit 0 enable the PIA FIRQ sources.
*     PDF 11: $FF90 bits (COCO, M/P, IEN, FEN, MC3, MC2, MC1, MC0),
*       $FF91 bit 5 = TINS, $FF93 bit 5 = timer FIRQ.
*     PDF 12: a write to $FF94 starts the 12-bit timer. It reloads
*       when it passes zero.
*   Kowalski, GIME register reference, $FF91 and $FF94-$FF95: with the
*     fast input, one count is 279.365 ns. A period is the reload value
*     plus 2 counts (1986 GIME) or plus 1 (1987 GIME). Read the timer
*     clock conflict in guidance/techniques/sound.md.

        org $3000
* >>> EXAMPLE 1 of 3: Mask interrupts while you set them up.
* ORCC #$50 sets both I (IRQ) and F (FIRQ). IRQ stays masked.
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

* --- CONTEXT: set up the DAC as in examples/sound-slots.
* $FF20 bits 7..2 are outputs. Keep bits 1..0. Select the DAC in the
* audio mux and enable sound.
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
        lda $FF01
        anda #$F7
        sta $FF01
        lda $FF03
        anda #$F7
        sta $FF03
        lda $FF23
        ora #8
        sta $FF23

        ifndef COOPERATIVE
* >>> EXAMPLE 2 of 3: Start the timer interrupt.
* Turn off the PIA FIRQ sources: CD ($FF21 bit 0) and the cartridge
* ($FF23 bit 0). Read the data registers to clear their flags.
        lda $FF21
        anda #$FE
        sta $FF21
        lda $FF23
        anda #$FE
        sta $FF23
        lda $FF20
        lda $FF22
* Put JMP handler ($7E is JMP extended) in the jump table at $FEF4.
        lda #$7E
        sta $FEF4
        ldd #handler
        std $FEF5
* $FF90: BASIC's $CE with FEN (bit 4) set. $FF91: fast timer input,
* executive task. $FF93: the timer is the only FIRQ source. Then read
* $FF93 to release a request that waits.
        lda #$DE
        sta $FF90
        lda #$20
        sta $FF91
        sta $FF93
        lda $FF93
* Reload value 510: low byte first. The high-byte write starts the timer.
        lda #$FE
        sta $FF95
        lda #1
        sta $FF94
* Unmask FIRQ only.
        andcc #$BF
* <<< END EXAMPLE
        endc

* --- CONTEXT: the main loop. Redraw after each block of 256 samples.
* The COOPERATIVE builds write one sample on each pass instead.
main_loop
        ifdef COOPERATIVE
        jsr emit
        endc
        lda samples
        cmpa last_block
        beq main_loop
        sta last_block
* The HEAVY builds clear the full screen first: a costly redraw.
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
* The check takes its snapshot here, after each redraw.
frame_ready
        bra main_loop

        ifndef COOPERATIVE
* >>> EXAMPLE 3 of 3: The FIRQ handler.
* FIRQ saves only CC and PC, so save A and B. Read $FF93 to release the
* request. Write a sample only for the timer flag. RTI restores CC and PC.
handler pshs a,b
        lda $FF93
        bita #$20
        beq restore
        jsr emit
restore puls a,b
        rti
* <<< END EXAMPLE
        endc

* --- CONTEXT: write one sample. A 16-bit phase advances by $0800.
* Its high byte, bits 7..2, goes to the DAC with the saved low bits.
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

* --- CONTEXT: the state. The context above clears it.
state
phase   rmb 2
samples rmb 2
position rmb 1
last_block rmb 1
low_bits rmb 1
state_end
        end start
