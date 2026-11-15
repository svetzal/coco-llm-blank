* Original turn queue for one player on CoCo 3; NTSC, 128/512 KiB, 6809,
* GIME 1986. Two planets, two journey slots, 16-bit turns and a turn
* limit. A rejected command changes no world byte. Journeys land when
* their turn comes, once each. No display, input, combat or production.
* The script that prepare.py writes from turns.txt drives every case and
* records the world after each operation. See README.md for the layout.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
* Normal low CPU rate, task 0, executive map $38-$3F, MMU on, native mode.
        sta $FFD8
        clr $FF91
        ldx #$FFA0
        lda #$38
map     sta ,x+
        inca
        cmpa #$40
        blo map
        lda #$4E
        sta $FF90
* Fill $4000-$5FFF and the stack guards with $A5 before any world is set.
        ldx #$4000
        lda #$A5
poison  sta ,x+
        cmpx #$6000
        blo poison
        sta $7DFF
        sta $7F00
* Each case: 1, then 17 world bytes, then steps, then 0. A 0 in place of
* the 1 ends the script. A step is 1 (send) with six command bytes,
* 2 (begin_turn) or 3 (end_commands). Each step appends a 19-byte record.
        ldu #results
        ldx #script
case    lda ,x+
        beq done
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
done    lda #$5A
        sta complete
finished bra finished

* Command: player, source, destination, ships, delay high, delay low.
* Status 0 = accepted, 1 = rejected. No world write before every check.
send    lda #1
        sta status
        lda phase
        cmpa #1
        lbne rejected
        lda command
        cmpa #1
        lbne rejected
        ldb command+1
        cmpb #2
        lbhs rejected
        lda command+2
        cmpa #2
        lbhs rejected
        cmpa command+1
        lbeq rejected
        ldy #ships
        leay b,y
        lda command+3
        lbeq rejected
        cmpa ,y
        lbhi rejected
        ifdef BAD_REJECT
        lda ,y
        suba command+3
        sta ,y
        endc
        ldd command+4
        lbeq rejected
        addd turn
        lbcs rejected
        cmpd turn_limit
        lbhi rejected
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
        bra rejected
        endc
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
rejected rts

* Only from the complete phase and below the limit: add one to the turn,
* land every due or overdue journey in slot order, then take commands.
begin_turn
        lda #1
        sta status
        clr resolved
        ifndef BAD_WRAP
        lda phase
        bne rejected
        ldd turn
        cmpd turn_limit
        bhs rejected
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
        rts

* Only from the commands phase: complete, or finished at the turn limit.
end_commands
        lda #1
        sta status
        lda phase
        cmpa #1
        bne rejected
        clr phase
        ldd turn
        cmpd turn_limit
        bne ended
        lda #2
        sta phase
ended   clr status
        rts

* Append the world, the status and the resolved-slot mask at U.
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

script
        include "script.inc"
code_end

world   equ $4100
turn    equ world
turn_limit equ world+2
phase   equ world+4
ships   equ world+5
queue   equ world+7
queue_end equ world+17
command equ $4200
arrival equ $4206
status  equ $4208
resolved equ $4209
slot_bit equ $420A
complete equ $420B
cursor  equ $420C
results equ $5000
        end start
