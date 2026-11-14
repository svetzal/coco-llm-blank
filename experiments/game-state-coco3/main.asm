* Original rules subset. ABI and citations are in README/validation note.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        sta $FFD8
* Task 0, executive pages. Preserve boot mapping while installing MMU map.
        clr $FF91
        ldx #$FFA0
        lda #$38
map     sta ,x+
        inca
        cmpa #$40
        blo map
        lda #$4E
        sta $FF90
* Poison owned RAM, including result region and stack guards.
        ldx #$4000
        lda #$A5
poison  sta ,x+
        cmpx #$6000
        blo poison
        sta $7DFF
        sta $7F00
        include "driver.inc"
finished bra finished
unreachable bra unreachable

* Command bytes: player, source, destination, count, delay hi, delay lo.
* Result 0=accepted, 1=rejected. No world write before all checks pass.
send    lda #1
        sta status
        ifdef BAD_REJECT
        dec ships
        endc
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
        ldd command+4
        lbeq rejected
        addd turn
        lbcs rejected
        cmpd turn_limit
        lbhi rejected
        std arrival_tmp
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
commit  lda ,y
        suba command+3
        sta ,y
        lda command+2
        sta 1,x
        lda command+3
        sta 2,x
        ldd arrival_tmp
        std 3,x
        lda #1
        sta ,x
        clr status
rejected rts

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

* Record world + status + resolved mask at each operation boundary.
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
code_end

world   equ $4100
turn    equ world
turn_limit equ world+2
phase   equ world+4
ships   equ world+5
queue   equ world+7
queue_end equ world+17
command equ $4200
arrival_tmp equ $4206
status  equ $4208
resolved equ $4209
slot_bit equ $420A
results equ $5000
        end start
