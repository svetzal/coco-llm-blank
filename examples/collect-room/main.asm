* Original Collect room. Contract, hardware citations and memory map: README.md.
        org $3000
start   orcc #$50
        lds #$7f00
        clra
        tfr a,dp
        ldx #state
zero    clr ,x+
        cmpx #state_end
        blo zero
        ldx #$0400
blank   clr ,x+
        cmpx #$1c00
        blo blank
        lda #$a5
        sta $03ff
        sta $1c00
        sta $7e00
        sta map_guard_before
        sta map_guard_after
        jsr reset_room
* RG6, offset 2, page zero, stock rate. Preserve shared PIA low bits.
        sta $ffc6
        sta $ffc9
        sta $ffca
        sta $ffcc
        sta $ffce
        sta $ffd0
        sta $ffd2
        sta $ffd4
        sta $ffd6
        sta $ffd8
        sta $ffc0
        sta $ffc3
        sta $ffc5
        lda $ff23
        ora #4
        sta $ff23
        lda $ff22
        anda #7
        ora #$f0
        sta $ff22
* Configure keyboard and DAC routing. CPU interrupts stay masked.
        lda $ff01
        anda #$f3
        sta $ff01
        clr $ff00
        ora #4
        sta $ff01
        lda $ff03
        anda #$f3
        sta $ff03
        ldb #$ff
        stb $ff02
        ora #4
        sta $ff03
        stb $ff02
        lda $ff21
        anda #$fb
        sta $ff21
        lda $ff20
        ora #$fc
        sta $ff20
        lda $ff21
        ora #4
        sta $ff21
        lda $ff20
        anda #3
        sta low_bits
        sta $ff20
        lda $ff23
        ora #8
        sta $ff23
* Startup sample seeds Space history, so a held key cannot start accidentally.
        jsr sample
        lda held
        sta previous
        jsr render
frame_ready
        ldx #12000
pause   leax -1,x
        bne pause
        jsr sample
        jsr update
        tst dirty
        beq frame_ready
        jsr render
        bra frame_ready

reset_room
        clr xpos
        clr ypos
        lda #2
        sta remaining
        ldx #initial_map
        ldy #room
        ldb #48
copy_map lda ,x+
        sta ,y+
        decb
        bne copy_map
        inc dirty
        rts

* Keys U,D,L,R,Space => bits 1,2,4,8,16. Only PA3 matters.
sample  clr held
        ldx #columns
        ldb #1
scan    lda ,x+
        sta $ff02
        lda $ff00
        bita #8
        bne released
        pshs b
        orb held
        stb held
        puls b
released
        lslb
        cmpx #columns_end
        blo scan
        lda #$ff
        sta $ff02
        rts

update  clr accepted
        clr dirty
        lda held
        bita #16
        beq movement
        ifndef HELD_SPACE
        ldb previous
        bitb #16
        bne movement
        endc
        lda phase
        cmpa #1
        beq movement
        jsr reset_room
        lda #1
        sta phase
        inc starts
        jsr effect
        bra history
movement
        lda phase
        cmpa #1
        bne history
        lda held
        anda #15
        ldx #directions
        ldb #4
choose  cmpa ,x
        beq chosen
        leax 3,x
        decb
        bne choose
        bra history
chosen  lda xpos
        adda 1,x
        cmpa #8
        bhs rejected
        sta candidate_x
        lda ypos
        adda 2,x
        cmpa #6
        bhs rejected
        sta candidate_y
        ldb #8
        mul
        addb candidate_x
        ldx #room
        leax d,x
        lda ,x
        cmpa #1
        beq rejected
        cmpa #3
        bne pickup
        tst remaining
        bne rejected
        lda #2
        sta phase
        lda #3
        jsr effect
        bra accept
pickup  cmpa #2
        bne accept
        clr ,x
        dec remaining
        lda #2
        jsr effect
accept  lda candidate_x
        sta xpos
        lda candidate_y
        sta ypos
        inc accepted
        inc dirty
history lda held
        sta previous
        rts
rejected
        ifdef STALE_HISTORY
        rts
        else
        bra history
        endc

* Finite square-wave effect. A=1 start,2 pickup,3 win. Preserve game pointers.
effect  pshs d,x,y,u
        sta last_effect
        inc effects
        ldx #delays
        deca
        lda a,x
        sta sound_delay
        lda low_bits
wave    eora #$fc
        ifdef SILENT
        anda #3
        endc
dac_write
        sta $ff20
        inc sample_count+1
        bne no_carry
        inc sample_count
no_carry
        pshs a
        lda sound_delay
        tfr a,b
wait_sound
        decb
        bne wait_sound
        puls a
* Use a separate counter because B was the delay counter.
        inc sound_count
        ldb sound_count
        cmpb #32
        blo wave
        clr sound_count
        lda low_bits
        sta $ff20
        puls d,x,y,u,pc

* Prepared headers, room and actor. No full-screen erase during movement.
render  lda phase
        ldb #0
        ldx #headers
        leax d,x
        ldy #$0600
header  lda ,x+
        sta ,y+
        cmpy #$0700
        blo header
        clr tile_row
rows    clr tile_column
cols    lda tile_row
        ldb #8
        mul
        addb tile_column
        ldx #room
        lda d,x
        jsr tile
        inc tile_column
        lda tile_column
        cmpa #8
        blo cols
        inc tile_row
        lda tile_row
        cmpa #6
        blo rows
        lda xpos
        sta tile_column
        lda ypos
        sta tile_row
        lda #4
        jsr tile
        clr dirty
        rts
* Tile A, expanded 16x16, two bytes/row, room origin pixel (64,48).
tile    ldb #32
        mul
        ldu #art
        leau d,u
        lda tile_row
        lsla
        adda #10
        ldb tile_column
        lslb
        addb #8
        tfr d,x
        ldy #16
pixels  ldd ,u++
        std ,x
        leax 32,x
        leay -1,y
        bne pixels
        rts
columns
        ifdef WRONG_COLUMN
        fcb $ef,$ef,$df,$bf,$7f
        else
        fcb $f7,$ef,$df,$bf,$7f
        endc
columns_end
directions fcb 1,0,-1,2,0,1,4,-1,0,8,1,0
delays  fcb 80,40,120
initial_map
        fcb 0,0,1,0,0,0,0,0
        fcb 0,2,1,0,0,1,0,0
        fcb 0,0,1,0,0,0,0,0
        fcb 0,0,0,0,1,1,0,0
        fcb 0,1,0,0,0,2,0,0
        fcb 0,0,0,0,0,0,3,0
        include "assets.inc"
state
phase   rmb 1
xpos    rmb 1
ypos    rmb 1
remaining rmb 1
held    rmb 1
previous rmb 1
accepted rmb 1
starts  rmb 1
effects rmb 1
last_effect rmb 1
sample_count rmb 2
candidate_x rmb 1
candidate_y rmb 1
dirty   rmb 1
tile_row rmb 1
tile_column rmb 1
low_bits rmb 1
sound_delay rmb 1
sound_count rmb 1
map_guard_before rmb 1
room    rmb 48
map_guard_after rmb 1
state_end
program_end
        end start
