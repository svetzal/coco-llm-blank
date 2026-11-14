* Original bounded scanner and policy. Contract/provenance in validation guide.
* Code/state $3000..program_end; records $4000..$406f; stack $7e00..$7eff.
        org $3000
start   orcc #$50
        lds #$7f00
        clra
        tfr a,dp
        ldx #state
clear   clr ,x+
        cmpx #state_end
        blo clear
        lda #2
        sta position
* Preserve control bits while selecting DDR, then data registers.
        lda $ff01
        sta control_a_before
        anda #$fb
        sta $ff01
        clr $ff00
        ora #4
        sta $ff01
        lda $ff03
        sta control_b_before
        anda #$fb
        sta $ff03
        ldb #$ff
        stb $ff02
        ora #4
        sta $ff03
        stb $ff02
        ifdef WRONG_SELECT
        anda #$fb
        sta $ff03
        endc
        ldu #$4000
* Startup sample seeds history, suppressing startup-held fire.
        jsr sample
        lda held
        sta previous
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
        lda #$a5
        sta complete
finished bra finished

* Breakpoint on sample injects real XRoar keyboard events before the PIA read.
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

* Logical bits left=1,right=2,fire=4. World [0,5); wall at 5.
* Save history even if motion is rejected. Both directions cancel.
update  lda held
        bita #4
        beq movement
        ifndef HELD_FIRE
        ldb previous
        bitb #4
        bne movement
        endc
        inc shots
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
history lda held
        sta previous
        rts
rejected
        ifdef STALE_HISTORY
        rts
        else
        bra history
        endc
state
raw_left rmb 1
raw_right rmb 1
raw_fire rmb 1
held    rmb 1
position rmb 1
shots   rmb 1
previous rmb 1
count   rmb 1
complete rmb 1
control_a_before rmb 1
control_b_before rmb 1
control_a_after rmb 1
control_b_after rmb 1
columns_after rmb 1
state_end
program_end
        end start
