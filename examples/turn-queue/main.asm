* Keep turn-based game state in a journey queue (CoCo 1, 2 and 3; RAM only).
*
* A command changes the world only after every check passes. A turn lands
* each due journey once, in slot order. A phase byte and a turn limit decide
* which routine may run. The rules are our design; README.md states them.
*
* The example is in four parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE": the world layout, send, begin_turn and end_commands.
* The rest is context: a runner reads the script that prepare.py writes from
* turns.txt, loads each case's start world, calls the routines and appends
* the world, the status and the landed slots to a record after each step.
* A project does not need the context.
*
* The program keeps the interrupts, stack, direct page, CPU rate and memory
* map that BASIC sets. No routine writes a hardware register.
*
* The BAD_* defines are faults for the negative controls in
* scripts/coco_spec.py only. A project does not need them.
*
* Sources:
*   Leventhal, 6809 Assembly Language Programming, PDF 537: ADDD and CMPD
*     take a 16-bit value with its high byte at the lower address; ADDD
*     sets C.
*   The same book, PDF 543: BHI branches when C and Z are both 0, BHS when
*     C is 0.
*   Color Computer Technical Reference Manual, PDF 12: a 32K machine has RAM
*     at $0000-$7FFF. Code at $3000, the world at $4100 and the records at
*     $5000-$5343 fit in it.
*   Color Basic Unravelled II, PDF 27 (Color BASIC 1.2): at a cold start
*     BASIC puts its stack 200 bytes below the top of RAM, above the records.

        org $3000
* --- CONTEXT: run each case of the script and record each step.
* Each case: 1, then 17 world bytes, then steps, then 0. A 0 in place of the
* 1 ends the script. A step is 1 (send) with six command bytes, 2
* (begin_turn) or 3 (end_commands).
start   ldu #results
        ldx #script
case    lda ,x+
        beq finished
        ldy #world
        ldb #17
reset   lda ,x+
        sta ,y+
        decb
        bne reset
step    lda ,x+
        beq case
        clr resolved
        cmpa #1
        bne other
        ldy #command
        ldb #6
load    lda ,x+
        sta ,y+
        decb
        bne load
        stx cursor
        jsr send
        bra kept
other   stx cursor
        cmpa #2
        bne close
        jsr begin_turn
        bra kept
close   jsr end_commands
kept    jsr record
        ldx cursor
        bra step
* This loop exists only for the check, after the last record is written.
finished bra finished

* >>> EXAMPLE 2 of 4: send. Check everything, then commit in one place.
* Command: player, source, destination, ships, delay (16 bits, high first).
* Status 0 = accepted, 1 = rejected. No world byte changes before commit.
send    lda #1
        sta status
        lda phase
        cmpa #1
        lbne send_done
        lda command
        cmpa #1
        lbne send_done
        ldb command+1
        cmpb #2
        lbhs send_done
        lda command+2
        cmpa #2
        lbhs send_done
        cmpa command+1
        lbeq send_done
        ldy #ships
        leay b,y
        lda command+3
        lbeq send_done
        cmpa ,y
        lbhi send_done
        ifdef BAD_REJECT
        lda ,y
        suba command+3
        sta ,y
        endc
* Unsigned: C set means the arrival turn does not fit in 16 bits.
        ldd command+4
        lbeq send_done
        addd turn
        lbcs send_done
        cmpd turn_limit
        lbhi send_done
        std arrival
        ldx #queue
find    tst ,x
        beq commit
        leax 5,x
        cmpx #queue_end
        blo find
        ifdef BAD_FULL
        ldx #queue
        bra commit
        else
        bra send_done
        endc
* The commit: take the ships and fill the free slot.
commit
        ifndef BAD_REJECT
        lda ,y
        suba command+3
        sta ,y
        endc
        lda command+2
        sta 1,x
        lda command+3
        sta 2,x
        ldd arrival
        std 3,x
        lda #1
        sta ,x
        clr status
send_done
        rts
* <<< END EXAMPLE

* >>> EXAMPLE 3 of 4: begin_turn. Only from the complete phase and below the
* limit: add one to the turn, land each due or overdue journey in slot order,
* free its slot, then take commands.
begin_turn
        lda #1
        sta status
        clr resolved
        ifndef BAD_WRAP
        lda phase
        bne begin_done
        ldd turn
        cmpd turn_limit
        bhs begin_done
        endc
        ldd turn
        addd #1
        std turn
        ldx #queue
        lda #1
        sta slot_bit
scan    tst ,x
        beq next
        ldd 3,x
        cmpd turn
        bhi next
        ldy #ships
        ldb 1,x
        leay b,y
        lda ,y
        adda 2,x
        bcc landed
        lda #255
landed  sta ,y
        lda resolved
        ora slot_bit
        sta resolved
        ifndef BAD_REPEAT
        clr ,x
        clr 1,x
        clr 2,x
        clr 3,x
        clr 4,x
        endc
next    asl slot_bit
        leax 5,x
        ifdef BAD_LAST
        cmpx #queue+5
        else
        cmpx #queue_end
        endc
        blo scan
        lda #1
        sta phase
        clr status
begin_done
        rts
* <<< END EXAMPLE

* >>> EXAMPLE 4 of 4: end_commands. Only from the commands phase: finished at
* the turn limit, else complete.
end_commands
        lda #1
        sta status
        lda phase
        cmpa #1
        bne end_done
        clr phase
        ldd turn
        cmpd turn_limit
        bne accepted
        lda #2
        sta phase
accepted
        clr status
end_done
        rts
* <<< END EXAMPLE

* --- CONTEXT: append the world, the status and the landed-slot mask at U.
record  ldx #world
        ldb #17
copy    lda ,x+
        sta ,u+
        decb
        bne copy
        lda status
        sta ,u+
        lda resolved
        sta ,u+
        rts

* --- CONTEXT: the script from turns.txt. This is a data label: the check
* fails if the CPU executes it.
script
        include "script.inc"
code_end

* >>> EXAMPLE 1 of 4: the world, 17 bytes. 16-bit values are high byte first.
world   equ $4100
turn    equ world               2 bytes
turn_limit equ world+2          2 bytes
phase   equ world+4             0 complete, 1 commands, 2 finished
ships   equ world+5             planets 0 and 1, 0 to 255 ships each
queue   equ world+7             two slots of 5 bytes: used, destination,
queue_end equ world+17          ships, arrival turn (2 bytes)
* <<< END EXAMPLE

* --- CONTEXT: the command, scratch bytes, the runner's cursor and records.
command equ $4200
arrival equ $4206
status  equ $4208
resolved equ $4209
slot_bit equ $420A
cursor  equ $420B
results equ $5000
        end start
