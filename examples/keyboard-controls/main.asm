* Read held keys and single presses in five example parts.
* Context moves a position, counts actions and records 16 updates in RAM.
* Code and state $3000..program_end; records $4000..$406F.
* --- CONTEXT: Initialize the state for the bounded demonstration.
        org $3000
start   ldx #state
clear   clr ,x+
        cmpx #state_end
        blo clear
        lda #2
        sta position
* >>> EXAMPLE 1 of 5: Set rows as inputs and columns as outputs
* Tandy, Color Computer Technical Reference Manual, PDF 13: control bit 2.
* Motorola, MC6821 PIA datasheet, PDF 7-8: DDR 0=input, 1=output.
* CoCo 3 Service Manual, PDF 9: the same PIA registers and control bit 2.
* Keep the other control bits while selecting DDR, then data registers.
* The control_*_before copies exist only for the check.
* All conditional fault defines exist only for the negative controls.
        lda $ff01
        sta control_a_before
        anda #$fb
        sta $ff01
        clr $ff00
        ora #4
        sta $ff01
        lda $ff03
        sta control_b_before
* Mask IRQ while $FF03 bit 2 selects DDRB. Extended BASIC leaves the
* field-sync IRQ on ($FF03 bit 0; Color Basic Unravelled II, PDF 23-24).
* Its handler at $894C (IRQ vector, the same book, PDF 20) reads $FF02 to
* clear the flag. With DDRB selected that read does not clear it: only a
* data-register read does (MC6821 datasheet, PDF 7). The flag stays set
* and the handler runs again forever. Restore BASIC's mask afterwards.
        pshs cc
        orcc #$10
        anda #$fb
        sta $ff03
        ldb #$ff
        stb $ff02
        ora #4
        sta $ff03
        puls cc
        stb $ff02
        ifdef WRONG_SELECT
* The mask stops a hang, so the fault shows in the update records.
        orcc #$10
        anda #$fb
        sta $ff03
        endc
* <<< END EXAMPLE
* --- CONTEXT: Point to the update records used by the check.
        ldu #$4000
* >>> EXAMPLE 2 of 5: Seed history from the startup sample
* Our policy: a Space held at startup does not count as a new press.
        jsr sample
        lda held
        sta previous
* <<< END EXAMPLE
* --- CONTEXT: Apply controls and record all 16 updates for the check.
loop    jsr sample
        jsr update
        ldx #raw_left
        ldb #7
record  lda ,x+
        sta ,u+
        decb
        bne record
        inc count
        lda count
        cmpa #16
        blo loop
        lda $ff01
        sta control_a_after
        lda $ff03
        sta control_b_after
        lda $ff02
        sta columns_after
* This loop exists only for the check, after all 16 records are written.
finished bra finished

* >>> EXAMPLE 3 of 5: Sample all three controls before choosing actions
* Tandy, Color Computer Technical Reference Manual, PDF 40: low selects.
* The same manual, PDF 75, and CoCo 2 NTSC Service Manual, PDF 36:
* Left, Right and Space are PA3 at PB5, PB6 and PB7.
* CoCo 3 Service Manual, PDF 40, figure 5-9: the same positions.
* Derived strobes: $DF, $BF, $7F. Test PA3 only; leave all columns high.
* The raw row copies exist only for the check.
* A key script takes effect at each sample entry.
sample  clr held
        lda #$df
        ifdef WRONG_COLUMN
        lda #$ef
        endc
        sta $ff02
        lda $ff00
        sta raw_left
        bita #8
        bne right
        inc held
right   lda #$bf
        sta $ff02
        lda $ff00
        sta raw_right
        bita #8
        bne fire
        lda held
        ora #2
        sta held
fire    lda #$7f
        sta $ff02
        lda $ff00
        sta raw_fire
        bita #8
        bne scan_done
        lda held
        ora #4
        sta held
scan_done
        lda #$ff
        sta $ff02
        rts

* <<< END EXAMPLE

* >>> EXAMPLE 4 of 5: Count an action only on a new Space press
* Logical bits: Left=1, Right=2, Space=4. This policy is our adaptation.
update  lda held
        bita #4
        beq movement
        ifndef HELD_FIRE
        ldb previous
        bitb #4
        bne movement
        endc
        inc shots
* <<< END EXAMPLE
* --- CONTEXT: Move within positions 0 to 4; opposite arrows cancel.
movement
        anda #3
        cmpa #1
        beq go_left
        cmpa #2
        bne history
        lda position
        cmpa #4
        beq rejected
        inc position
        bra history
go_left tst position
        beq rejected
        dec position
* >>> EXAMPLE 5 of 5: Save history even after a rejected move
history lda held
        sta previous
        rts
* <<< END EXAMPLE
* --- CONTEXT: Return from a rejected move through the history update.
rejected
        ifdef STALE_HISTORY
        rts
        else
        bra history
        endc
* --- CONTEXT: Store raw rows, controls and demonstration state.
* The seven record fields must stay adjacent for the check.
state
raw_left rmb 1
raw_right rmb 1
raw_fire rmb 1
held    rmb 1
position rmb 1
shots   rmb 1
previous rmb 1
count   rmb 1
control_a_before rmb 1
control_b_before rmb 1
control_a_after rmb 1
control_b_after rmb 1
columns_after rmb 1
state_end
program_end
        end start
