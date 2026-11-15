* Arena Blaster: an original arena shooter for the CoCo 1.
* Increment 4: compiled sprites from assets.py and a fixed speed of 30
* frames each second. README.md has the contract, the rules for each frame
* and the memory map.
*
* Sources (all read as page images):
*   Tandy, Color Computer Technical Reference Manual:
*     PDF 13: $FF00 bits 0-6 = keyboard rows, $FF02 = keyboard columns.
*       $FF01/$FF03 bit 2 = 1 selects the data register, 0 the DDR.
*       $FF03 bit 0 = FS IRQ enable, bit 1 = FS edge (0 falling),
*       bit 7 = FS flag.
*     PDF 14: $FF22 bits 7-3 = A/G, GM2, GM1, GM0, CSS.
*     PDF 15: SAM V2-V0 at $FFC0-$FFC5, display offset F6-F0 at
*       $FFC6-$FFD3 in 512-byte units (even address clears, odd sets).
*     PDF 31, Table 1: 128x192 colour graphics (CG6) is V = 110 and
*       $FF22 bits 7-4 = 1110.
*     PDF 75: keyboard matrix. Row PA0: A=PB1, D=PB4. Row PA1: K=PB3,
*       L=PB4, O=PB7. Row PA2: S=PB3, W=PB7. Row PA5: semicolon=PB3.
*     PDF 13-14: $FF01/$FF03 bit 3 = SEL 1/SEL 2, $FF20 bits 7-2 = the
*       six-bit DAC, $FF21 bit 2 = 0 selects its direction register,
*       $FF23 bit 3 = sound enable.
*     PDF 26: the CPU clock is 14.31818 MHz / 16 = 0.894886 MHz.
*     PDF 38, Table 4: SNDEN 1, SEL 1 0, SEL 2 0 select the DAC.
*   Leventhal, 6809 Assembly Language Programming, Appendix C, PDF 553-555:
*     the cycles of each instruction in the sound loop.
*   Motorola MC6847 datasheet, PDF 19-21 (through the graphics guide):
*     CG6 = 2 bits for each pixel, leftmost pixel in bits 7-6, 32 bytes for
*     each row. Colour set 0: 0 green, 1 yellow, 2 blue, 3 red.
*   Motorola MC6821 datasheet, PDF 10, Figure 18: the flag sets on the
*     selected edge of CB1 and stays set until a read of the data register
*     (read as a page image).
*   The Rainbow, October 1986, PDF 119: PMODE 3 is graphics mode 6C.

SCREEN_A equ $0400
SCREEN_B equ $2400
STATE   equ $1C00
LIST_A  equ $1D00               ; erase list of screen A: first byte, erase routine
LIST_B  equ $1E00               ; erase list of screen B
STACK   equ $2400

* Screen bytes. Four pixels for each byte, code 2 (blue) is the floor.
FLOOR   equ $AA                 ; blue blue blue blue
WALL    equ $FF                 ; red red red red
LEFT_WALL equ $AB               ; blue blue blue red (pixel 3)
RIGHT_WALL equ $EA              ; red blue blue blue (pixel 124)
WALL_TOP equ 12
WALL_BOTTOM equ 187

* The area inside the wall: pixels 4-123, rows 13-186.
MIN_X   equ 4
END_X   equ 124                 ; first pixel column of the right wall
MIN_Y   equ 13
END_Y   equ 187                 ; first row of the bottom wall
PLAYER_W equ 6
PLAYER_H equ 10
START_X equ 61
START_Y equ 95

SHOTS   equ 6                   ; shot slots
SHOT_DELAY equ 2                ; frames between two shots is SHOT_DELAY+1

* Enemies. All are 6x10 pixels, the same size as the player.
ENEMIES equ 24                  ; enemy slots
ENEMY_W equ 6
ENEMY_H equ 10
GRUNT   equ 1                   ; enemy types; 0 = free slot
HUNTER  equ 2
GRUNT_PERIOD equ 2              ; frames between two grunt steps
HUNTER_PERIOD equ 1             ; frames between two hunter steps
MAX_GRUNTS equ 20               ; 4 + 2 * level, up to this number
MIN_HUNTER_WAIT equ 45          ; 330 - 30 * level, down to this number
SAFE_X  equ 28                  ; no grunt starts this near the player
SAFE_Y  equ 45
SEED    equ $ACE1               ; start value of the random sequence
        ifndef FIRST_LEVEL
FIRST_LEVEL equ 1               ; a test variant can start at another level
        endc
* Test-harness controls, only for the check (README.md lists them):
*   NO_ENEMIES   a level starts with no grunts, and an empty arena is not
*                a clear arena.
*   FIXED_GRUNTS a level starts with two grunts, at x 100, y 90 and at
*                x 100, y 40, and no hunter comes.
*   STILL        enemies do not move.
*   HUNTER_SOON  the hunter wait is 30 frames on every level.
*   NO_DEATH     a touch does not start the level again.

* Sound effects: one record a frame (README.md "Sound").
NOISE   equ $80                 ; record mode: noise; 0 is a square wave
FX_END  equ $FF                 ; record mode: end of the effect
P_SHOT  equ 1                   ; priorities: a new effect replaces the
P_BOOM  equ 2                   ; current one only if its priority is
P_HUNTER equ 3                  ; the same or higher
P_LEVEL equ 4
P_DEATH equ 5

* Key bits. The same bits for movement and for shots.
UP      equ 1
DOWN    equ 2
LEFT    equ 4
RIGHT   equ 8

* Fields of a direction record (dir_table).
D_MDX   equ 0                   ; player step across, pixels
D_MDY   equ 1                   ; player step down, rows
D_VX    equ 2                   ; shot step across, pixels
D_VY    equ 3                   ; shot step down, rows
D_SPR   equ 4                   ; shot sprite, 2 bytes
D_OX    equ 6                   ; shot start, from the player's corner
D_OY    equ 7
D_MAXX  equ 8                   ; largest x that keeps the shot inside
D_MAXY  equ 9                   ; largest y that keeps the shot inside
D_W     equ 10                  ; shot width, pixels
D_H     equ 11                  ; shot height, rows
D_SIZE  equ 12

* Fields of a shot slot.
S_ON    equ 0                   ; 0 = free
S_X     equ 1
S_Y     equ 2
S_VX    equ 3
S_VY    equ 4
S_SPR   equ 5                   ; 2 bytes
S_MAXX  equ 7
S_MAXY  equ 8
S_W     equ 9
S_H     equ 10
S_SIZE  equ 11

* Fields of an enemy slot.
E_TYPE  equ 0                   ; 0 = free, GRUNT or HUNTER
E_X     equ 1
E_Y     equ 2
E_TICK  equ 3                   ; frames until the next step
E_SIZE  equ 4

        org $3C00
start   orcc #$50               ; mask IRQ and FIRQ: no handler runs
        lds #STACK
        lda #STATE/256
        tfr a,dp
        setdp STATE/256

* Clear the state and both erase lists ($1C00-$1FFF).
        ldx #STATE
clear   clr ,x+
        cmpx #STACK-$400
        blo clear

* Keyboard: rows are inputs, columns are outputs. Keep the other control
* bits. This follows the keyboard-controls example.
        lda $FF01
        anda #$FB
        sta $FF01
        clr $FF00
        ora #4
        sta $FF01
        lda $FF03
        anda #$FB
        sta $FF03
        ldb #$FF
        stb $FF02
        ora #4
        sta $FF03
        stb $FF02
* Field sync: no IRQ (bit 0 = 0), flag on the falling edge (bit 1 = 0),
* $FF02 is the data register (bit 2 = 1).
        lda $FF03
        anda #%11111100
        ora #%00000100
        sta $FF03

* Sound: $FF20 bits 7-2 are outputs. Keep bits 1-0 and the other control
* bits. This follows the sound-slots example.
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
        sta <level_out          ; DAC 0, bits 1-0 kept
        sta $FF20
* Select the DAC: SEL 1 = 0, SEL 2 = 0, sound enable = 1.
        lda $FF01
        anda #$F7
        sta $FF01
        lda $FF03
        anda #$F7
        sta $FF03
        lda $FF23
        ora #8
        sta $FF23
        lda #1
        sta <scount
        sta <period
        lda #$5A
        sta <noise

* Draw the floor and the wall into both screens.
        ldx #SCREEN_A
        jsr prepare_screen
        ldx #SCREEN_B
        jsr prepare_screen

* Show screen A in CG6, colour set 0. SAM offset F = $0400 / 512 = 2.
        sta $FFC6               ; F0 = 0
        sta $FFC9               ; F1 = 1
        sta $FFCA               ; F2 = 0
        sta $FFCC               ; F3 = 0
        sta $FFCE               ; F4 = 0
        sta $FFD0               ; F5 = 0
        sta $FFD2               ; F6 = 0
        sta $FFC0               ; V0 = 0
        sta $FFC3               ; V1 = 1
        sta $FFC5               ; V2 = 1
        lda $FF22
        anda #%00000111         ; keep bits 2-0
        ora #%11100000          ; A/G=1 GM2=1 GM1=1 GM0=0 CSS=0
        sta $FF22

* Start state. Frame 1 is drawn into screen B.
        lda #SCREEN_B/256
        sta <drawing
        ldd #LIST_A
        std <end_a
        ldd #LIST_B
        std <end_b
        ldd #SEED
        std <seed
        lda #FIRST_LEVEL
        sta <level
        jsr start_level

frame   jsr rand_step           ; one step of the random sequence a frame
        jsr scan
        jsr move_player
        jsr move_shots
        jsr fire
        jsr move_enemies
        jsr spawn_hunter
        jsr hit_enemies
        jsr hit_player
        bcc frame_clear
        ldx #fx_death
        lda #P_DEATH
        jsr start_sound
        jsr start_level         ; touched: the same level again
        bra frame_draw
frame_clear
        ifdef NO_ENEMIES        ; check only: an empty arena is not clear
        bra frame_draw
        endc
        ldx #enemies
fc_slot tst E_TYPE,x
        bne frame_draw          ; an enemy is left
        leax E_SIZE,x
        cmpx #enemies_end
        blo fc_slot
        ldx #fx_level
        lda #P_LEVEL
        jsr start_sound
        inc <level              ; arena clear: the next level
        jsr start_level
frame_draw
        jsr sound_frame
        jsr draw_frame
        jsr show
        ldd <frames
        addd #1
        std <frames
        bra frame

* --- Read the eight keys. A pressed key reads 0 on its row.
* A key script line takes effect each time the program reaches 'scan'.
scan    clr <move_keys
        clr <fire_keys
* Column PB1: A (row PA0) moves left.
        lda #%11111101
        sta $FF02
        lda $FF00
        bita #%00000001
        bne scan_pb3
        lda #LEFT
        sta <move_keys
* Column PB3: S (row PA2) moves down. K (row PA1) shoots left.
* Semicolon (row PA5) shoots right.
scan_pb3
        lda #%11110111
        sta $FF02
        ldb $FF00
        bitb #%00000100
        bne scan_k
        lda <move_keys
        ora #DOWN
        sta <move_keys
scan_k  bitb #%00000010
        bne scan_semicolon
        lda <fire_keys
        ora #LEFT
        sta <fire_keys
scan_semicolon
        bitb #%00100000
        bne scan_pb4
        lda <fire_keys
        ora #RIGHT
        sta <fire_keys
* Column PB4: D (row PA0) moves right. L (row PA1) shoots down.
scan_pb4
        lda #%11101111
        sta $FF02
        ldb $FF00
        bitb #%00000001
        bne scan_l
        lda <move_keys
        ora #RIGHT
        sta <move_keys
scan_l  bitb #%00000010
        bne scan_pb7
        lda <fire_keys
        ora #DOWN
        sta <fire_keys
* Column PB7: W (row PA2) moves up. O (row PA1) shoots up.
scan_pb7
        lda #%01111111
        sta $FF02
        ldb $FF00
        bitb #%00000100
        bne scan_o
        lda <move_keys
        ora #UP
        sta <move_keys
scan_o  bitb #%00000010
        bne scan_done
        lda <fire_keys
        ora #UP
        sta <fire_keys
scan_done
        lda #$FF
        sta $FF02
* K, O, S and W are the corners of a rectangle in the matrix: rows PA1
* and PA2, columns PB3 and PB7. Three held keys make the fourth read as
* held. So when K and O are held and both W and S read as held, the
* vertical movement cannot be known. Keep the one of the last frame.
        lda <fire_keys
        anda #UP+LEFT
        cmpa #UP+LEFT
        bne scan_vertical
        lda <move_keys
        anda #UP+DOWN
        cmpa #UP+DOWN
        bne scan_vertical
        lda <move_keys
        anda #LEFT+RIGHT
        ora <last_vertical
        sta <move_keys
        rts
scan_vertical
        lda <move_keys
        anda #UP+DOWN
        sta <last_vertical
        rts

* --- X = the direction record for the key bits in B.
direction
        ldx #directions
        ldb b,x
        lda #D_SIZE
        mul
        ldx #dir_table
        leax d,x
        rts

* --- Move the player one step. Stop at the arena edge.
move_player
        ldb <move_keys
        bsr direction
        lda <px
        adda D_MDX,x
        cmpa #MIN_X
        bhs mp_right
        lda #MIN_X
mp_right
        cmpa #END_X-PLAYER_W
        bls mp_store_x
        lda #END_X-PLAYER_W
mp_store_x
        sta <px
        lda <py
        adda D_MDY,x
        cmpa #MIN_Y
        bhs mp_bottom
        lda #MIN_Y
mp_bottom
        cmpa #END_Y-PLAYER_H
        bls mp_store_y
        lda #END_Y-PLAYER_H
mp_store_y
        sta <py
        rts

* --- Move each shot one step. Remove a shot that leaves the arena.
move_shots
        ldx #shots
ms_slot tst S_ON,x
        beq ms_next
        lda S_X,x
        adda S_VX,x
        sta S_X,x
        cmpa #MIN_X
        blo ms_off
        cmpa S_MAXX,x
        bhi ms_off
        lda S_Y,x
        adda S_VY,x
        sta S_Y,x
        cmpa #MIN_Y
        blo ms_off
        cmpa S_MAXY,x
        bls ms_next
ms_off  clr S_ON,x
ms_next leax S_SIZE,x
        cmpx #shots_end
        blo ms_slot
        rts

* --- Start a shot when the delay is 0, a shoot key is held and a slot
* is free.
fire    lda <delay
        beq fire_ready
        deca
        sta <delay
        rts
fire_ready
        ldb <fire_keys
        bsr direction
        ldd D_SPR,x
        beq fire_done           ; no direction: no sprite
        ldu #shots
fire_slot
        tst S_ON,u
        beq fire_start
        leau S_SIZE,u
        cmpu #shots_end
        blo fire_slot
fire_done
        rts
fire_start
        std S_SPR,u
        lda #1
        sta S_ON,u
        lda <px
        adda D_OX,x
        sta S_X,u
        lda <py
        adda D_OY,x
        sta S_Y,u
        ldd D_VX,x
        std S_VX,u              ; S_VX and S_VY
        ldd D_MAXX,x
        std S_MAXX,u            ; S_MAXX and S_MAXY
        ldd D_W,x
        std S_W,u               ; S_W and S_H
        lda #SHOT_DELAY
        sta <delay
        ldx #fx_shot
        lda #P_SHOT
        jmp start_sound

* --- Erase what the hidden screen showed two frames before. Then draw
* the shots and the player, and keep their rectangles for the next erase.
draw_frame
        ldy #LIST_A
        ldx #end_a
        lda <drawing
        cmpa #SCREEN_A/256
        beq df_erase
        ldy #LIST_B
        ldx #end_b
df_erase
        stx <end_ptr
        sty <next
        ldd ,x
        std <temp
er_next cmpy <temp
        beq er_done
        ldx ,y                  ; the first byte
        jsr [2,y]               ; the erase routine keeps Y
        leay 4,y
        bra er_next
er_done
        ldx #shots
df_shot tst S_ON,x
        beq df_skip
        pshs x
        ldu S_SPR,x
        lda S_X,x
        ldb S_Y,x
        bsr draw_sprite
        puls x
df_skip leax S_SIZE,x
        cmpx #shots_end
        blo df_shot
        ldx #enemies
df_enemy
        lda E_TYPE,x
        beq df_enemy_skip
        pshs x
        ldu #grunt
        cmpa #GRUNT
        beq df_enemy_draw
        ldu #hunter
df_enemy_draw
        lda E_X,x
        ldb E_Y,x
        bsr draw_sprite
        puls x
df_enemy_skip
        leax E_SIZE,x
        cmpx #enemies_end
        blo df_enemy
        lda <px
        ldb <py
        ldu #player
        bsr draw_sprite
        ldd <next
        std [end_ptr]
        rts

* --- Draw sprite U at pixel x = A, row y = B in the hidden screen.
* U holds a draw and an erase routine for each shift (assets.py). Keep
* the first byte and the erase routine in the erase list, then jump to
* the draw routine. Its RTS returns to the caller.
draw_sprite
        sta <temp
        lda #32
        mul                     ; D = y * 32
        adda <drawing
        tfr d,x
        lda <temp
        lsra
        lsra
        leax a,x                ; + x / 4
        ldb <temp
        andb #3                 ; shift x % 4
        lslb
        lslb
        leau b,u                ; its routines: draw, then erase
        ldy <next
        stx ,y++
        ldd 2,u
        std ,y++
        sty <next
        jmp [,u]

* --- Show the finished screen after exactly two fields: 30 frames each
* second. The last show cleared the flag at the start of the first field.
* The flag sets at the end of a field and stays set until a read of
* $FF02 (MC6821 PDF 10, Figure 18). So a set flag here tells that the
* work took more than one field. The sound takes its next record at the
* end of the first field, so an effect still has one record a field.
* If the work takes more than two fields, the frame takes three or more.
show    lda $FF03
        bmi show_late           ; the first field ended during the work
        jsr play_until_fs       ; wait for the end of the first field
show_late
        lda $FF02               ; clear the flag
        jsr sound_frame         ; the record of the second field
        jsr play_until_fs       ; wait for the end of the second field
        lda <drawing
        cmpa #SCREEN_B/256
        bne show_a
        sta $FFCF               ; F4 = 1: screen B
        bra published
show_a  sta $FFCE               ; F4 = 0: screen A
* The check takes a snapshot each time the program reaches this label.
published
        lda $FF03
        ora #%00000010          ; rising edge
        sta $FF03
        lda $FF02
        jsr play_until_fs       ; wait for the rising edge of FS
        lda $FF03
        anda #%11111101         ; falling edge again
        sta $FF03
        lda $FF02               ; clear the flag: the first field starts
        lda <drawing
        eora #(SCREEN_A^SCREEN_B)/256
        sta <drawing
        rts

* --- Fill the screen at X with the floor and the wall.
prepare_screen
        clr <temp
ps_row  lda <temp
        cmpa #WALL_TOP
        blo ps_plain
        cmpa #WALL_BOTTOM
        bhi ps_plain
        ldb #LEFT_WALL
        stb ,x+
        ldb #FLOOR
        cmpa #WALL_TOP
        beq ps_wall
        cmpa #WALL_BOTTOM
        bne ps_inside
ps_wall ldb #WALL
ps_inside
        lda #30
ps_inside_byte
        stb ,x+
        deca
        bne ps_inside_byte
        ldb #RIGHT_WALL
        stb ,x+
        bra ps_next
ps_plain
        lda #32
        ldb #FLOOR
ps_plain_byte
        stb ,x+
        deca
        bne ps_plain_byte
ps_next inc <temp
        lda <temp
        cmpa #192
        blo ps_row
        rts

* --- Start the level in 'level': the player in the middle, no shots,
* new grunts, and the hunter wait for this level.
start_level
        lda #START_X
        sta <px
        lda #START_Y
        sta <py
        clr <delay
        ldx #shots
sl_shot clr S_ON,x
        leax S_SIZE,x
        cmpx #shots_end
        blo sl_shot
        ldx #enemies
sl_enemy
        clr E_TYPE,x
        leax E_SIZE,x
        cmpx #enemies_end
        blo sl_enemy
* Hunter wait: 330 - 30 * level frames, but not less than 45.
        lda <level
        cmpa #10
        blo sl_calc
        ldd #MIN_HUNTER_WAIT
        bra sl_wait
sl_calc ldb #30
        mul
        std <temp
        ldd #330
        subd <temp
sl_wait
        ifdef HUNTER_SOON       ; check only: a hunter each 15 frames
        ldd #15
        endc
        ifdef FIXED_GRUNTS      ; check only: no hunter
        ldd #0
        endc
        std <hunter_wait
        std <hunter_timer
        ifdef NO_ENEMIES        ; check only: no grunts
        rts
        endc
        ifdef FIXED_GRUNTS      ; check only: two grunts at fixed places
        ldu #enemies
        lda #GRUNT
        sta E_TYPE,u
        sta E_SIZE+E_TYPE,u
        ldd #100*256+90
        std E_X,u
        ldd #100*256+40
        std E_SIZE+E_X,u
        lda #1
        sta E_TICK,u
        lda #2
        sta E_SIZE+E_TICK,u
        rts
        endc
* Grunts: 4 + 2 * level, but not more than 20.
        lda #MAX_GRUNTS
        ldb <level
        cmpb #(MAX_GRUNTS-4)/2
        bhs sl_count
        lslb
        addb #4
        tfr b,a
sl_count
        sta <count
        ldu #enemies
sl_grunt
        jsr random_x
        stb E_X,u
        jsr random_y
        stb E_Y,u
* Not near the player's start: try again if x is 33-89 and y is 50-140.
        lda E_X,u
        cmpa #START_X-SAFE_X
        blo sl_place
        cmpa #START_X+SAFE_X
        bhi sl_place
        lda E_Y,u
        cmpa #START_Y-SAFE_Y
        blo sl_place
        cmpa #START_Y+SAFE_Y
        bls sl_grunt
sl_place
        lda #GRUNT
        sta E_TYPE,u
* First step after 1-2 frames (slot number AND 1, plus 1), so that the
* grunts do not all step in the same frame.
        tfr u,d
        subd #enemies
        lsrb
        lsrb                    ; slot number (E_SIZE = 4)
        andb #1
        incb
        stb E_TICK,u
        leau E_SIZE,u
        dec <count
        bne sl_grunt
        rts

* --- One step of the 16-bit random sequence: shift right, and if a 1
* bit falls out, exclusive-or with $B400. Our choice of a maximal-length
* Galois shift register. D is changed.
rand_step
        ldd <seed
        lsra
        rorb
        bcc rs_store
        eora #$B4
rs_store
        std <seed
        rts

* --- B = a random byte: eight steps, then the low byte of the sequence.
rand    lda #8
        sta <rcount
rand_loop
        bsr rand_step
        dec <rcount
        bne rand_loop
        ldb <seed+1
        rts

* --- B = a random enemy x, 4-118: 7 random bits, try again above 114.
random_x
        bsr rand
        andb #127
        cmpb #END_X-ENEMY_W-MIN_X
        bhi random_x
        addb #MIN_X
        rts

* --- B = a random enemy y, 13-177: a random byte, try again above 164.
random_y
        bsr rand
        cmpb #END_Y-ENEMY_H-MIN_Y
        bhi random_y
        addb #MIN_Y
        rts

* --- Each enemy counts down its tick. At 0 it steps toward the player:
* 1 pixel across and up to 2 rows down or up.
move_enemies
        ifdef STILL             ; check only: enemies do not move
        rts
        endc
        ldu #enemies
me_slot lda E_TYPE,u
        beq me_next
        dec E_TICK,u
        bne me_next
        ldb #GRUNT_PERIOD
        cmpa #GRUNT
        beq me_tick
        ldb #HUNTER_PERIOD
me_tick stb E_TICK,u
        lda E_X,u
        cmpa <px
        beq me_y
        blo me_right
        deca
        bra me_store_x
me_right
        inca
me_store_x
        sta E_X,u
me_y    lda <py
        suba E_Y,u              ; py - y
        beq me_next
        bhs me_down
        nega                    ; y - py
        cmpa #2
        bls me_up
        lda #2
me_up   sta <temp
        lda E_Y,u
        suba <temp
        sta E_Y,u
        bra me_next
me_down cmpa #2
        bls me_add
        lda #2
me_add  adda E_Y,u
        sta E_Y,u
me_next leau E_SIZE,u
        cmpu #enemies_end
        blo me_slot
        rts

* --- Count down the hunter wait. At 0, put a hunter at a random place on
* a random side of the arena. If no slot is free, or the place is near the
* player, try again in the next frame.
spawn_hunter
        ldd <hunter_wait
        beq sh_done             ; a wait of 0: no hunters (check only)
        ldd <hunter_timer
        beq sh_try
        subd #1
        std <hunter_timer
        bne sh_done
sh_try  ldu #enemies
sh_slot tst E_TYPE,u
        beq sh_free
        leau E_SIZE,u
        cmpu #enemies_end
        blo sh_slot
sh_done rts
sh_free jsr rand
        andb #3                 ; side: 0 top, 1 bottom, 2 left, 3 right
        stb <temp
        cmpb #2
        bhs sh_side
        jsr random_x
        stb E_X,u
        ldb #MIN_Y
        tst <temp
        beq sh_top
        ldb #END_Y-ENEMY_H
sh_top  stb E_Y,u
        bra sh_near
sh_side jsr random_y
        stb E_Y,u
        ldb #MIN_X
        lda <temp
        cmpa #2
        beq sh_left
        ldb #END_X-ENEMY_W
sh_left stb E_X,u
* Near the player: less than 20 pixels across and 30 rows. Then no hunter.
sh_near lda E_X,u
        suba <px
        bhs sh_dx
        nega
sh_dx   cmpa #20
        bhs sh_place
        lda E_Y,u
        suba <py
        bhs sh_dy
        nega
sh_dy   cmpa #30
        blo sh_done
sh_place
        lda #HUNTER
        sta E_TYPE,u
        lda #HUNTER_PERIOD
        sta E_TICK,u
        ldd <hunter_wait
        std <hunter_timer
        ldx #fx_hunter
        lda #P_HUNTER
        jmp start_sound

* --- A shot that overlaps an enemy removes the enemy and the shot. Shots
* in slot order; each shot removes the first enemy in slot order.
hit_enemies
        ldx #shots
he_shot tst S_ON,x
        beq he_next_shot
        lda S_X,x
        adda S_W,x
        sta <right
        lda S_Y,x
        adda S_H,x
        sta <bottom
        ldu #enemies
he_enemy
        tst E_TYPE,u
        beq he_next_enemy
        lda E_X,u
        cmpa <right             ; enemy left < shot right
        bhs he_next_enemy
        adda #ENEMY_W
        cmpa S_X,x              ; enemy right > shot left
        bls he_next_enemy
        lda E_Y,u
        cmpa <bottom
        bhs he_next_enemy
        adda #ENEMY_H
        cmpa S_Y,x
        bls he_next_enemy
        clr E_TYPE,u
        clr S_ON,x
        pshs x,u
        ldx #fx_boom
        lda #P_BOOM
        jsr start_sound
        puls x,u
        bra he_next_shot
he_next_enemy
        leau E_SIZE,u
        cmpu #enemies_end
        blo he_enemy
he_next_shot
        leax S_SIZE,x
        cmpx #shots_end
        blo he_shot
        rts

* --- Carry set if an enemy overlaps the player. Both are 6x10, so they
* overlap when they are less than 6 pixels across and 10 rows apart.
hit_player
        ifdef NO_DEATH          ; check only: no touch
        andcc #$FE
        rts
        endc
        ldu #enemies
hp_slot tst E_TYPE,u
        beq hp_next
        lda E_X,u
        suba <px
        bhs hp_dx
        nega
hp_dx   cmpa #ENEMY_W
        bhs hp_next
        lda E_Y,u
        suba <py
        bhs hp_dy
        nega
hp_dy   cmpa #ENEMY_H
        blo hp_touch
hp_next leau E_SIZE,u
        cmpu #enemies_end
        blo hp_slot
        andcc #$FE              ; carry clear: not touched
        rts
hp_touch
        orcc #$01               ; carry set: touched
        rts

* --- Start effect X with priority A, if A is the same as or higher
* than the priority of the effect that plays now.
start_sound
        cmpa <priority
        blo ss_done
        sta <priority
        stx <effect
ss_done rts

* --- Once a frame: take the next record of the effect. Each record is
* mode, period and volume. Mode 0 is a square wave and NOISE is noise.
* Volume is the DAC step, 0-63, shifted left 2 for $FF20 bits 7-2.
sound_frame
        lda <level_out          ; start each frame at DAC 0
        anda #3
        sta <level_out
        sta $FF20
        ldx <effect
        beq sf_silent
        lda ,x
        cmpa #FX_END
        beq sf_end
        sta <mode
        ldd 1,x
        sta <period
        lslb
        lslb
        stb <volume
        leax 3,x
        stx <effect
        rts
sf_end  ldx #0
        stx <effect
        clr <priority
sf_silent
        clr <volume
        rts

* --- Play the sound until the FS flag ($FF03 bit 7) sets.
* A pass without a change takes 17 cycles: LDA ext 5, BMI 3, DEC dir 6,
* BNE 3. A pass that changes the output takes 52 cycles. So a half wave
* of P passes is 17 x P + 35 cycles, and a square wave is
* 894886 / (2 x (17 x P + 35)) Hz.
play_until_fs
        lda $FF03
        bmi pf_done
        dec <scount
        bne play_until_fs
        ldb <period             ; 4
        stb <scount             ; 4
        lda <mode               ; 4
        bmi pf_noise            ; 3
        lda <level_out          ; 4
        eora <volume            ; 4
        sta <level_out          ; 4
        sta $FF20               ; 5
        bra play_until_fs       ; 3
* Noise: an 8-bit shift register. When a 1 bit falls out, change the
* output. Our choice of taps: exclusive OR with $1D.
pf_noise
        lda <noise
        lsla
        bcc pf_noise_keep
        eora #$1D
        sta <noise
        lda <level_out
        eora <volume
        sta <level_out
        sta $FF20
        bra play_until_fs
pf_noise_keep
        sta <noise
        bra play_until_fs
pf_done rts

* --- Sound effects. Records: mode, period, volume. One record a frame.
* Square-wave pitch: 894886 / (2 x (17 x period + 35)) Hz.
fx_shot fcb 0,8,24,0,10,22,0,13,18,0,17,14,0,22,10,FX_END
fx_boom fcb NOISE,2,44,NOISE,2,40,NOISE,3,34,NOISE,3,28,NOISE,4,22
        fcb NOISE,4,16,NOISE,5,10,NOISE,6,6,FX_END
fx_hunter
        fcb 0,10,26,0,10,26,0,14,26,0,14,26,0,10,26,0,10,26
        fcb 0,14,26,0,14,26,FX_END
fx_level
        fcb 0,30,28,0,30,28,0,30,28,0,22,28,0,22,28,0,22,28
        fcb 0,16,28,0,16,28,0,16,28,0,11,28,0,11,28,0,11,28
        fcb 0,11,20,0,11,12,FX_END
fx_death
        fcb NOISE,1,60,NOISE,1,56,NOISE,2,52,NOISE,2,48,NOISE,3,44
        fcb NOISE,3,40,NOISE,4,36,NOISE,4,32,NOISE,5,28,NOISE,6,24
        fcb NOISE,7,20,NOISE,8,16,NOISE,9,12,NOISE,10,8,FX_END

* --- Tables.
* Direction number for each combination of key bits (UP=1, DOWN=2,
* LEFT=4, RIGHT=8). Number = (dy + 1) * 3 + (dx + 1), so 4 is no
* direction. Opposite keys cancel.
directions
        fcb 4,1,7,4,3,0,6,3,5,2,8,5,4,1,7,4

* One record for each direction number, D_SIZE bytes.
* A shot starts in the middle of the player: ((6 - w) / 2, (10 - h) / 2).
* The largest position is END - size: x <= 124 - w, y <= 187 - h.
* Fields: MDX MDY VX VY, sprite, OX OY MAXX MAXY W H.
dir_table
        fcb -2,-4,-6,-12
        fdb shot_back
        fcb 1,2,121,181,3,6  ; 0: up and left   (3x6)
        fcb 0,-4,0,-12
        fdb shot_vertical
        fcb 2,2,123,181,1,6  ; 1: up            (1x6)
        fcb 2,-4,6,-12
        fdb shot_forward
        fcb 1,2,121,181,3,6  ; 2: up and right  (3x6)
        fcb -2,0,-6,0
        fdb shot_horizontal
        fcb 1,4,120,186,4,1  ; 3: left          (4x1)
        fcb 0,0,0,0
        fdb 0
        fcb 0,0,0,0,0,0  ; 4: none
        fcb 2,0,6,0
        fdb shot_horizontal
        fcb 1,4,120,186,4,1  ; 5: right         (4x1)
        fcb -2,4,-6,12
        fdb shot_forward
        fcb 1,2,121,181,3,6  ; 6: down and left (3x6)
        fcb 0,4,0,12
        fdb shot_vertical
        fcb 2,2,123,181,1,6  ; 7: down          (1x6)
        fcb 2,4,6,12
        fdb shot_back
        fcb 1,2,121,181,3,6  ; 8: down and right (3x6)

* Sprites, made from sprites.txt by assets.py at each build.
        include "assets.inc"
program_end

* --- Game state in the direct page. These labels are data: the check
* fails if the CPU executes 'state'.
        org STATE
state
drawing rmb 1                   ; high byte of the hidden screen
px      rmb 1
py      rmb 1
move_keys rmb 1
fire_keys rmb 1
delay   rmb 1
frames  rmb 2
temp    rmb 2
next    rmb 2                   ; next free erase-list entry
end_ptr rmb 2                   ; address of end_a or end_b
end_a   rmb 2                   ; end of the erase list of screen A
end_b   rmb 2
shots   rmb SHOTS*S_SIZE
shots_end
level   rmb 1
seed    rmb 2
rcount  rmb 1
count   rmb 1
right   rmb 1
bottom  rmb 1
hunter_wait rmb 2               ; frames between two hunters on this level
hunter_timer rmb 2              ; frames until the next hunter
enemies rmb ENEMIES*E_SIZE
enemies_end
last_vertical rmb 1             ; UP, DOWN or both, from the last frame
effect  rmb 2                   ; next record, or 0 for no effect
priority rmb 1
mode    rmb 1
period  rmb 1
volume  rmb 1                   ; the DAC step, shifted left 2
level_out rmb 1                 ; the value in $FF20
scount  rmb 1                   ; passes until the next change
noise   rmb 1
state_end
        end start
