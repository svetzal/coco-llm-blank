* Let each game phase accept only its own input (CoCo 1, 2 and 3).
*
* The game has three phases: title (0), play (1) and won (2).
*   Title  Space starts play.         Arrows do nothing.
*   Play   Arrows move one tile.      Space does nothing.
*   Won    Space restarts play.       Arrows do nothing.
* Space acts only on a new press. A Space held at startup does not start.
* Each start restores the room, so a restart is the same game again.
*
* The example is in six parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: a small game with an RG6 room,
* keyboard scan, blocking DAC effects and lettering. A project does not need
* the context.
*
* Sources for the context:
*   Inman, Inman and Dymax, Assembly Language Graphics for the TRS-80 Color
*     Computer, PDF 106: mode 6R (RG6) is 256x192 at $0400-$1BFF.
*   Motorola, MC6847 datasheet, PDF 19 Table 3: RG6 bit order.
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 13: $FF00 rows, $FF02 columns, control bit 2 selects the DDR,
*       $FF01 bit 3 = SEL 1 and $FF03 bit 3 = SEL 2.
*     PDF 14: $FF20 bits 7..2 = 6-bit DAC, $FF23 bit 3 = sound enable.
*     PDF 31 Table 1: RG6 is SAM V=110 and $FF22 bits 7..3 = 1111 CSS.
*     PDF 38 Table 4: SNDEN 1, SEL 1 = 0 and SEL 2 = 0 select the DAC.
*   Motorola, MC6821 PIA datasheet, PDF 10, Figure 18: control bit 2 = 0
*     selects the DDR; only a read of the output register clears the flag.
*   Color Basic Unravelled II, PDF 42: Color BASIC's IRQ handler reads
*     $FF02 to reset the field-sync flag. On every target that IRQ is on
*     when the program starts: TIMER ($0112) counts in each snapshot, and
*     without the mask below a delay in the DDR window stops the program
*     (both measured in the pinned XRoar).
*   Tandy, Color Computer 2 NTSC Service Manual, PDF 36 figure 4-10:
*     Up, Down, Left, Right and Space are row PA3, columns PB3 to PB7.
*   The CoCo 3 needs no other setup:
*   Tandy, Color Computer 3 Service Manual:
*     PDF 9-10: the same $FF00-$FF03 and $FF20-$FF23 bits as above.
*     PDF 40 figure 5-9: the same row PA3 and columns PB3 to PB7.
*     PDF 43: Sel B 0 and Sel A 0 select the DAC; SNDEN high enables it.
*   Tepolt, Assembly Language Programming for the CoCo3, PDF 46: in the
*     VDG modes each colour code selects a GIME palette register. PDF 57
*     step 44: BASIC loads them. This program keeps them.
*
* All conditional fault defines exist only for the negative controls.

        org $3000
* --- CONTEXT: clear the game state and the screen.
start   ldx #state
zero    clr ,x+
        cmpx #state_end
        blo zero
        ldx #$0400
blank   clr ,x+
        cmpx #$1c00
        blo blank
* The guard bytes exist only for the check.
        lda #$a5
        sta $03ff
        sta $1c00
        sta map_guard_before
        sta map_guard_after
        jsr reset_room
* --- CONTEXT: show RG6 at $0400 with colour set 0, as in first-screen.
* SAM offset F=2 ($0400 / 512), then SAM mode V=110. Keep $FF22 bits 2..0.
        sta $ffc6
        sta $ffc9
        sta $ffca
        sta $ffcc
        sta $ffce
        sta $ffd0
        sta $ffd2
        sta $ffc0
        sta $ffc3
        sta $ffc5
        lda $ff22
        anda #7
        ora #$f0
        sta $ff22
* --- CONTEXT: keyboard directions as in keyboard-controls, then DAC routing.
* Mux select 00 and sound enable route the DAC to the sound output.
        lda $ff01
        anda #$f3
        sta $ff01
        clr $ff00
        ora #4
        sta $ff01
* BASIC's IRQ handler reads $FF02 to clear the field-sync flag; with the DDR
* selected it reads DDRB, so the flag stays set and the handler runs forever.
* So mask IRQ only while $FF03 selects DDRB. A field sync in that window
* runs the handler after PULS CC, when $FF02 is the data register again.
* PULS CC restores BASIC's mask.
        lda $ff03
        pshs cc
        orcc #$10
        anda #$f3
        sta $ff03
        ldb #$ff
        stb $ff02
        ora #4
        sta $ff03
        puls cc
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
* >>> EXAMPLE 1 of 6: Seed the history from a startup sample
* Our policy: a Space held at startup is not a new press, so it cannot start.
        jsr sample
        lda held
        sta previous
* <<< END EXAMPLE
* --- CONTEXT: draw, then wait, sample and update. Redraw after a change.
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

* >>> EXAMPLE 2 of 6: Restore the room at each start
* Put the actor at (0, 0), set two stars to collect and copy the initial map.
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
* <<< END EXAMPLE

* --- CONTEXT: scan Up, Down, Left, Right and Space into held bits
* 1, 2, 4, 8 and 16. Test row PA3 only. Leave all columns high.
* A key script takes effect at each sample entry.
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

* >>> EXAMPLE 3 of 6: Space starts play only from title or won
* A new press is Space held now and released at the previous sample.
* In play, Space does nothing and the arrows are read below.
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
* The starts counter exists only for the check.
        inc starts
        jsr effect
        bra history
* <<< END EXAMPLE
* >>> EXAMPLE 4 of 6: Read the arrows only in play
* In title and won, the update ends here, so the arrows do nothing.
movement
        lda phase
        cmpa #1
        bne history
* <<< END EXAMPLE
* --- CONTEXT: one arrow chooses a step; more than one cancels.
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
* --- CONTEXT: reject the room edges and walls.
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
* >>> EXAMPLE 5 of 6: Keep the exit locked until no star remains
* Entering the open exit changes the phase to won.
        cmpa #3
        bne pickup
        tst remaining
        bne rejected
        lda #2
        sta phase
        lda #3
        jsr effect
        bra accept
* <<< END EXAMPLE
* --- CONTEXT: collect a star, then move.
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
* The accepted counter exists only for the check.
        inc accepted
        inc dirty
* >>> EXAMPLE 6 of 6: Save the history after every update
* Every phase and every rejected move must reach this step. Otherwise a
* Space held across a phase change can count as a new press.
history lda held
        sta previous
        rts
* <<< END EXAMPLE
* --- CONTEXT: return from a rejected move through the history update.
rejected
        ifdef STALE_HISTORY
        rts
        else
        bra history
        endc

* --- CONTEXT: a blocking square-wave effect of 32 DAC writes.
* A=1 start, 2 pickup, 3 win. The game reads no keys during an effect.
effect  pshs d,x,y,u
* The last_effect, effects and sample_count values exist only for the check.
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
        inc sound_count
        ldb sound_count
        cmpb #32
        blo wave
        clr sound_count
        lda low_bits
        sta $ff20
        puls d,x,y,u,pc

* --- CONTEXT: draw the phase message, the room and the actor.
* No full-screen erase during movement.
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
* Tile A, 16x16 pixels, two bytes a row, room origin at pixel (64,48).
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

* --- CONTEXT: tables, the initial map, the art and the game state.
* Column strobes for Up, Down, Left, Right and Space.
columns
        ifdef WRONG_COLUMN
        fcb $ef,$ef,$df,$bf,$7f
        else
        fcb $f7,$ef,$df,$bf,$7f
        endc
columns_end
* Held bits, then the x and y step.
directions fcb 1,0,-1,2,0,1,4,-1,0,8,1,0
delays  fcb 80,40,120
* 0 floor, 1 wall, 2 star, 3 exit.
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
        end start
