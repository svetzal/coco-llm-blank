* Arena Blaster: an original arena shooter for the CoCo 1.
* Increment 8: shooters, enemies that fire bullets at the player.
* Increment 7: first levels that teach the game, and a "LEVEL N" banner.
* Increment 6: title screen, high-score table and initials. Increment 5:
* score, lives and game over. Increment 4: compiled sprites and a fixed
* speed of 30 frames each second. README.md has the contract,
* the rules for each frame and the memory map.
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
line    equ $1F00               ; a line of text, 16 bytes
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
SHOOTER equ 3
SHOOTER_PERIOD equ 3            ; frames between two shooter steps
MAX_SHOOTERS equ 4              ; level - 3, up to this number
MIN_FIRE_WAIT equ 24            ; 84 - 8 * level, down to this number
BULLETS equ 4                   ; enemy bullet slots
BULLET_W equ 3
BULLET_H equ 3
BULLET_VX equ 3                 ; pixels across each frame
BULLET_VY equ 6                 ; rows down or up each frame
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
        ifndef FIRST_LIVES
FIRST_LIVES equ 3               ; lives at the start of a game
        endc
        ifndef FIRST_SCORE
FIRST_SCORE equ $0000           ; BCD, the low four digits of the score
        endc
* Test-harness controls, only for the check (README.md lists them):
*   NO_ENEMIES   a level starts with no grunts, and an empty arena is not
*                a clear arena.
*   FIXED_ENEMIES a level starts with a grunt at x 100, y 90 and a hunter
*                at x 100, y 40, and no other hunter comes.
*   STILL        enemies do not move.
*   HUNTER_SOON  the hunter wait is 15 frames on every level.
*   NO_DEATH     a touch does not kill the player.
*   SKIP_TITLE   at power-on a game starts at once, with no title screen.
*   NO_READY     a level starts with no banner: play starts at once.
*   ONE_SHOOTER  a level starts with one shooter at x 61, y 30, which
*                fires each 20 frames, and no other enemies.
*   FIRST_LEVEL, FIRST_LIVES, FIRST_SCORE  other start values.

* Score, lives and pauses (README.md "Score and lives").
EXTRA_EVERY equ $10             ; BCD hundreds: an extra life each 1000
DYING_FRAMES equ 45             ; the pause after a death
OVER_FRAMES equ 90              ; the pause after game over
HUD_ROW equ 3                   ; the first row of the digits and icons
ICONS   equ 6                   ; places for reserve lives

* Phases of the program (README.md "Title and high scores").
TITLE   equ 0                   ; the title screen and the table
PLAY    equ 1                   ; a game
ENTRY   equ 2                   ; the initials for a new high score
PLACES  equ 10                  ; entries in the high-score table
P_ENTRY_SIZE equ 6              ; an entry: 3 BCD score bytes, 3 letters
REPEAT_FIRST equ 12             ; frames before a held W or S repeats
REPEAT_NEXT equ 4               ; frames between two repeats
* Text colours (font.txt is yellow on blue) and the big-text flag.
YELLOW_TEXT equ 0
RED_TEXT equ 1
GREEN_TEXT equ 2
BIG     equ $80                 ; each pixel shows as 2x2 pixels
CURSOR  equ $55                 ; four yellow pixels

* The first levels and the banner (README.md "Levels and enemies").
TEACH_LEVELS equ 5              ; levels with their own row in teach_table
READY_FRAMES equ 60             ; the banner: 2 seconds
BANNER_ROW equ 60               ; "LEVEL N" in big text: rows 60-69
BANNER_ROWS equ 21              ; the hint is on rows 76-80
BANNER_COL equ 2                ; the banner is in byte columns 2-29
* Fields of a teach_table row.
T_GRUNTS equ 0
T_SHOOTERS equ 1
T_FIRE  equ 2                   ; frames between two bullets, 0 = none
T_FIRST equ 3                   ; frames until the first hunter, 0 = none
T_WAIT  equ 5                   ; frames between two hunters, 0 = none
T_HINT  equ 7                   ; the hint: a list of text records
T_SIZE  equ 9

* Sound effects: records of mode, period, volume and fields (README.md
* "Sound").
NOISE   equ $80                 ; record mode: noise; 0 is a square wave
FX_END  equ $FF                 ; record mode: end of the effect
P_SHOT  equ 1                   ; priorities: a new effect replaces the
P_ZAP   equ 1
P_BOOM  equ 2                   ; current one only if its priority is
P_HUNTER equ 3                  ; the same or higher
P_LEVEL equ 4
P_EXTRA equ 4
P_DEATH equ 5
P_OVER  equ 6
P_START equ 6

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

* Fields of an enemy bullet slot.
B_ON    equ 0                   ; 0 = free
B_X     equ 1
B_Y     equ 2
B_VX    equ 3
B_VY    equ 4
B_SIZE  equ 5

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
        lda #$FF
        sta <new_rank           ; no entry of the table is new
        ifdef SKIP_TITLE        ; check only: a game at once
        lda #PLAY
        sta <phase
        jsr new_game
        jsr resync
        else
        jsr setup_title         ; phase = TITLE (0): the title screen
        endc

frame   jsr rand_step           ; one step of the random sequence a frame
        jsr scan
        lda <old_fire           ; shoot keys held now, but not in the last frame
        coma
        anda <fire_keys
        sta <fire_new
        lda <fire_keys
        sta <old_fire
        lda <phase
        cmpa #PLAY
        beq frame_over
        cmpa #ENTRY
        lbeq frame_entry
* Title: a shoot key that was not held in the last frame starts a game.
        lda <fire_new
        lbeq frame_still
        jsr begin_game
        bra frame_draw
* After game over: wait. Then the initials for a high score, or the title.
frame_over
        lda <over
        beq frame_dying
        dec <over
        bne frame_draw
        jsr game_end
        lbra frame_still
* After a death: wait. Then take a life, and start the level again or
* end the game.
frame_dying
        lda <dying
        beq frame_ready
        dec <dying
        bne frame_draw
        dec <lives
        bne frame_again
        ldx #fx_over
        lda #P_OVER
        jsr start_sound
        lda #OVER_FRAMES
        sta <over
        bra frame_draw
frame_again
        jsr start_level         ; the same level again
        bra frame_draw
* The banner at the start of a level: wait.
frame_ready
        lda <ready
        beq frame_play
        dec <ready
        bra frame_draw
frame_play
        jsr move_player
        jsr move_shots
        jsr move_bullets
        jsr fire
        jsr move_enemies
        jsr spawn_hunter
        jsr enemy_fire
        jsr hit_enemies
        jsr hit_player
        bcc frame_clear
        ldx #fx_death
        lda #P_DEATH
        jsr start_sound
        lda #DYING_FRAMES       ; touched: everything stops for a moment
        sta <dying
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
frame_show
        jsr show
        ldd <frames
        addd #1
        std <frames
        jmp frame
* Title and initials: the screens stay, and only one part changes.
frame_still
        jsr sound_frame
        lda <phase
        cmpa #ENTRY
        beq fs_entry
        jsr draw_prompt
        bra frame_show
fs_entry
        jsr draw_entry
        bra frame_show

* --- Initials. W or S changes the letter at the cursor: at once, then
* after REPEAT_FIRST frames, then each REPEAT_NEXT frames. A new shoot key
* moves the cursor on. After the third letter, the entry goes into the
* table and the title screen comes.
frame_entry
        lda <move_keys
        anda #UP+DOWN
        beq fe_none             ; W and S are not held
        cmpa #UP+DOWN
        beq fe_none             ; both are held
        ldb <rpt
        bne fe_held
        ldb #REPEAT_FIRST       ; a new press
        bra fe_change
fe_held decb
        stb <rpt
        bne fe_fire
        ldb #REPEAT_NEXT
fe_change
        stb <rpt
        ldx #initials
        ldb <pos
        abx
        ldb ,x
        cmpa #UP
        bne fe_down
        incb                    ; W: the next letter, after Z comes A
        cmpb #'Z
        bls fe_store
        ldb #'A
        bra fe_store
fe_down decb                    ; S: the letter before, before A comes Z
        cmpb #'A
        bhs fe_store
        ldb #'Z
fe_store
        stb ,x
        ldx #fx_shot
        lda #P_SHOT
        jsr start_sound
        bra fe_fire
fe_none clr <rpt
fe_fire lda <fire_new
        beq fe_done
        inc <pos
        lda <pos
        cmpa #3
        beq fe_last
        ldx #fx_shot
        lda #P_SHOT
        jsr start_sound
fe_done jmp frame_still
fe_last jsr insert
        lda <rank
        sta <new_rank
        ldx #fx_level
        lda #P_LEVEL
        jsr start_sound
        jsr setup_title
        jmp frame_still

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
        lbsr draw_sprite
        puls x
df_skip leax S_SIZE,x
        cmpx #shots_end
        blo df_shot
        ldx #bullets
df_bullet
        tst B_ON,x
        beq df_bullet_skip
        pshs x
        ldu #bullet
        lda B_X,x
        ldb B_Y,x
        lbsr draw_sprite
        puls x
df_bullet_skip
        leax B_SIZE,x
        cmpx #bullets_end
        blo df_bullet
        ldx #enemies
df_enemy
        lda E_TYPE,x
        beq df_enemy_skip
        pshs x
        lsla
        ldu #enemy_sprites
        ldu a,u                 ; the sprite of this enemy type
        lda E_X,x
        ldb E_Y,x
        lbsr draw_sprite
        puls x
df_enemy_skip
        leax E_SIZE,x
        cmpx #enemies_end
        blo df_enemy
        lda <px
        ldb <py
        ldu #player
        lbsr draw_sprite
        lda <ready
        beq df_end
        jsr draw_banner
df_end  ldd <next
        std [end_ptr]
        jmp draw_hud

* --- The banner: "LEVEL N" in big text, and the hint of a first level
* under it. An erase-list entry clears the banner area.
draw_banner
        ldd #BANNER_ROW*32+9
        adda <drawing
        tfr d,y
        lda #BIG+YELLOW_TEXT
        sta <tcolour
        ldu #level_text
        jsr text_at             ; Y moves on after the text
        ldx #line               ; the level number in decimal
        lda <level
        ldb #'0
db_tens cmpa #10
        blo db_ones
        suba #10
        incb
        bra db_tens
db_ones cmpb #'0
        beq db_one              ; no tens digit
        stb ,x+
db_one  adda #'0
        clrb
        std ,x
        ldu #line
        jsr text_at
        lda <level
        cmpa #TEACH_LEVELS
        bhi db_erase
        deca
        ldb #T_SIZE
        mul
        addd #teach_table
        tfr d,x
        ldu T_HINT,x
        lda <drawing
        sta <target
        jsr texts
db_erase
        ldd #BANNER_ROW*32+BANNER_COL
        adda <drawing
        ldy <next
        std ,y++
        ldd #erase_banner
        std ,y++
        sty <next
        rts

* Erase routine of the banner: X = its first byte. The floor in 28 bytes
* of BANNER_ROWS rows. Keeps Y, as each erase routine does.
erase_banner
        ldb #BANNER_ROWS
        ldu #FLOOR*257
eb_row  stu ,x
        stu 2,x
        stu 4,x
        stu 6,x
        stu 8,x
        stu 10,x
        stu 12,x
        stu 14,x
        stu 16,x
        stu 18,x
        stu 20,x
        stu 22,x
        stu 24,x
        stu 26,x
        leax 32,x
        decb
        bne eb_row
        rts

* --- The score and the reserve lives, in the blue band above the arena
* (rows HUD_ROW to HUD_ROW+4). Each glyph is one byte for each row
* (font.txt). The score is at byte columns 1-6. Reserve lives are from
* byte column 30 to the left; empty places get the floor.
draw_hud
        lda <drawing
        ldb #HUD_ROW*32+1
        tfr d,y                 ; the first digit
        ldx #score
dh_byte lda ,x
        lsra
        lsra
        lsra
        lsra
        bsr dh_glyph_digit      ; high digit
        lda ,x+
        anda #$0F
        bsr dh_glyph_digit      ; low digit
        cmpx #score+3
        blo dh_byte
        lda <drawing
        ldb #HUD_ROW*32+30
        tfr d,y                 ; the first reserve life
        ldb <lives
        decb                    ; reserves: lives - 1, but not less than 0
        bpl dh_reserves
        clrb
dh_reserves
        lda #ICONS
        sta <count
dh_icon ldu #life_icon
        tstb
        bne dh_icon_draw
        ldu #no_icon
        incb
dh_icon_draw
        decb
        bsr dh_glyph
        leay -2,y               ; dh_glyph moved Y on by 1
        dec <count
        bne dh_icon
        rts

* A = a digit 0-9: its glyph from digits, 5 bytes each.
dh_glyph_digit
        ldb #5
        mul
        ldu #digits
        leau d,u
* Store the 5 bytes at U down the column at Y. Then Y moves on by 1.
dh_glyph
        lda ,u+
        sta ,y
        lda ,u+
        sta 32,y
        lda ,u+
        sta 64,y
        lda ,u+
        sta 96,y
        lda ,u
        sta 128,y
        leay 1,y
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
        bsr field_start
        lda <drawing
        eora #(SCREEN_A^SCREEN_B)/256
        sta <drawing
        rts

* --- Wait for the rising edge of FS: the start of a field. Then select
* the falling edge again and clear the flag.
field_start
        lda $FF03
        ora #%00000010          ; rising edge
        sta $FF03
        lda $FF02
        jsr play_until_fs       ; wait for the rising edge of FS
        lda $FF03
        anda #%11111101         ; falling edge again
        sta $FF03
        lda $FF02               ; clear the flag: the first field starts
        rts

* --- After long work, such as a new screen: wait for the end of a field,
* then start the frame at the start of the next field.
resync  lda $FF02
        jsr play_until_fs
        bra field_start

* --- From the title: a new game in the arena.
begin_game
        lda #PLAY
        sta <phase
        ldx #SCREEN_A
        jsr prepare_screen
        ldx #SCREEN_B
        jsr prepare_screen
        ldd #LIST_A             ; nothing to erase
        std <end_a
        ldd #LIST_B
        std <end_b
        jsr new_game
        bra resync

* --- After the pause of game over: the initials if the score gets a
* place in the table, if not the title.
game_end
        lda #$FF
        sta <new_rank
        bsr find_rank
        lda <rank
        cmpa #PLACES
        lbhs setup_title
        lbra setup_entry

* --- rank = the first entry with a lower score than 'score', or PLACES
* if none. A score the same as an entry goes below that entry.
find_rank
        ldx #table
        clr <rank
fr_entry
        ldd <score
        cmpd ,x
        bne fr_test
        lda <score+2
        cmpa 2,x
fr_test bhi fr_done             ; score > entry
        leax P_ENTRY_SIZE,x
        inc <rank
        lda <rank
        cmpa #PLACES
        blo fr_entry
fr_done rts

* --- Put the score and the initials into the table at 'rank'. Each
* lower entry moves down one place. The last entry goes out.
insert  lda <rank
        ldb #P_ENTRY_SIZE
        mul
        addd #table
        tfr d,y                 ; the new entry
        leau P_ENTRY_SIZE,y
        stu <temp               ; the lowest byte that gets a copy
        ldx #table+PLACES*P_ENTRY_SIZE-1
ins_move
        cmpx <temp
        blo ins_put
        lda -P_ENTRY_SIZE,x
        sta ,x
        leax -1,x
        bra ins_move
ins_put ldd <score
        std ,y
        lda <score+2
        sta 2,y
        ldd <initials
        std 3,y
        lda <initials+2
        sta 5,y
        rts

* --- The title screen in both screens.
setup_title
        clr <phase              ; TITLE
        lda #SCREEN_A/256
        bsr title_screen
        lda #SCREEN_B/256
        bsr title_screen
        lbra resync

* A = the screen. The name, the table, the enemies and their points, and
* the keys. The prompt is drawn each frame (draw_prompt).
title_screen
        sta <target
        lbsr blank
        ldu #title_texts
        lbsr texts
        bsr draw_table
        lda <drawing            ; draw_sprite draws into 'drawing'
        pshs a
        lda <target
        sta <drawing
        ldd #LIST_A             ; a place for the erase entries, not used
        std <next
        ldd #20*256+136
        ldu #grunt
        lbsr draw_sprite
        ldd #52*256+136
        ldu #hunter
        lbsr draw_sprite
        ldd #84*256+136
        ldu #shooter
        lbsr draw_sprite
        puls a
        sta <drawing
        rts

* --- The table: one line for each entry, "NN ABC 012345", from row 40,
* each 9 rows, at byte column 9. A new entry is green.
draw_table
        clr <trow
        ldx #table
dt_line ldy #line
        lda <trow
        inca                    ; place 1-10
        cmpa #PLACES
        bne dt_one
        ldd #'1*256+'0
        bra dt_place
dt_one  adda #'0
        tfr a,b
        lda #32                 ; a space
dt_place
        std ,y++
        lda #32
        sta ,y+
        lda 3,x
        sta ,y+
        lda 4,x
        sta ,y+
        lda 5,x
        sta ,y+
        lda #32
        sta ,y+
        tfr x,u
        bsr bcd_text
        clr ,y
        lda #YELLOW_TEXT
        ldb <trow
        cmpb <new_rank
        bne dt_colour
        lda #GREEN_TEXT
dt_colour
        sta <tcolour
        lda <trow
        ldb #9
        mul
        addb #40                ; the row: 40 + 9 x place
        lda #32
        mul
        addd #9
        adda <target
        tfr d,y
        pshs x
        ldu #line
        lbsr text_at
        puls x
        leax P_ENTRY_SIZE,x
        inc <trow
        lda <trow
        cmpa #PLACES
        blo dt_line
        rts

* --- The 3 BCD bytes at U as 6 characters at Y. Y moves on.
bcd_text
        lda #3
        sta <count
bt_byte lda ,u
        lsra
        lsra
        lsra
        lsra
        adda #'0
        sta ,y+
        lda ,u+
        anda #$0F
        adda #'0
        sta ,y+
        dec <count
        bne bt_byte
        rts

* --- The initials screen in both screens.
setup_entry
        lda #ENTRY
        sta <phase
        clr <pos
        clr <rpt
        lda #'A
        sta <initials
        sta <initials+1
        sta <initials+2
        lda #SCREEN_A/256
        bsr entry_screen
        lda #SCREEN_B/256
        bsr entry_screen
        lbra resync

* A = the screen. The texts and the score. The letters and the cursor are
* drawn each frame (draw_entry).
entry_screen
        sta <target
        bsr blank
        ldu #entry_texts
        lbsr texts
        ldy #line
        ldu #score
        bsr bcd_text
        clr ,y
        ldd #40*32+13
        adda <target
        tfr d,y
        clr <tcolour            ; yellow
        ldu #line
        lbra text_at

* --- Each frame on the title: the prompt shows for 16 frames, then a
* space for 16 frames.
draw_prompt
        ldd #156*32+9
        adda <drawing
        tfr d,y
        clr <tcolour            ; yellow
        ldu #prompt_on
        lda <frames+1
        bita #16
        beq text_at
        ldu #prompt_off
        bra text_at

* --- Each frame of the initials: the three letters in big text at row 80,
* byte columns 12, 16 and 20. Under the letter at 'pos', a yellow bar on
* rows 92-93.
draw_entry
        ldx #line
        lda <initials
        ldb #32
        std ,x++
        lda <initials+1
        std ,x++
        lda <initials+2
        clrb
        std ,x
        ldd #80*32+12
        adda <drawing
        tfr d,y
        lda #BIG+YELLOW_TEXT
        sta <tcolour
        ldu #line
        bsr text_at
        ldd #92*32+12
        adda <drawing
        tfr d,x
        clr <trow
de_bar  ldu #FLOOR*257
        lda <trow
        cmpa <pos
        bne de_put
        ldu #CURSOR*257
de_put  stu ,x
        stu 32,x
        leax 4,x
        inc <trow
        lda <trow
        cmpa #3
        blo de_bar
        rts

* --- Fill the screen in 'target' with the floor.
blank   lda <target
        clrb
        tfr d,x
        adda #6144/256
        std <temp
        ldd #FLOOR*257
bl_word std ,x++
        cmpx <temp
        blo bl_word
        rts

* --- Draw the text records at U into the screen in 'target'. A record is
* the byte offset (2 bytes), the colour, the characters and 0. $FFFF ends
* the list.
texts   ldd ,u++
        cmpd #$FFFF
        beq tl_done
        adda <target
        tfr d,y
        lda ,u+
        sta <tcolour
        bsr text_at
        bra texts
tl_done rts

* --- Draw the characters at U, up to a 0, at screen byte Y in the colour
* 'tcolour'. A normal character is 1 byte wide and 5 rows high. A big
* character is 2 bytes wide and 10 rows high. U moves past the 0.
text_at lda ,u+
        beq tx_done
        pshs u
        suba #32
        ldb #5
        mul
        ldu #font
        leau d,u
        tst <tcolour
        bmi tx_big
        bsr glyph
        bra tx_next
tx_big  bsr big_glyph
tx_next puls u
        bra text_at
tx_done rts

* Glyph U (5 bytes) at Y in 'tcolour'. Then Y moves on by 1.
glyph   lda #5
        sta <rows
gl_row  lda ,u+
        bsr paint
        sta ,y
        leay 32,y
        dec <rows
        bne gl_row
        leay -5*32+1,y
        rts

* Glyph U at Y, each pixel two times across and down. Then Y moves on by 2.
big_glyph
        lda #5
        sta <rows
        ldx #double
bg_row  lda ,u+
        bsr paint
        pshs a
        lsra
        lsra
        lsra
        lsra
        lda a,x                 ; the left two pixels, doubled
        sta ,y
        sta 32,y
        puls a
        anda #$0F
        lda a,x                 ; the right two pixels, doubled
        sta 1,y
        sta 33,y
        leay 64,y
        dec <rows
        bne bg_row
        leay -10*32+2,y
        rts

* A = a glyph byte, yellow (01) on blue (10). Change yellow to the colour
* in 'tcolour'. Red (11) = byte OR (yellow bits shifted left). Green (00) =
* byte AND $AA.
paint   ldb <tcolour
        andb #$7F
        beq pt_done             ; yellow
        decb
        bne pt_green
        tfr a,b
        andb #$55
        lslb
        stb <tbits
        ora <tbits
        rts
pt_green
        anda #$AA
pt_done rts

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
        ldx #bullets
sl_bullet
        clr B_ON,x
        leax B_SIZE,x
        cmpx #bullets_end
        blo sl_bullet
        lda #$FF                ; the first shooter to fire is the first in
        sta <shooter_turn          ; slot order
* The banner "LEVEL N" first: nothing moves for READY_FRAMES frames.
        ifndef NO_READY         ; check only: no banner
        lda #READY_FRAMES
        sta <ready
        endc
* Levels 1 to TEACH_LEVELS take the enemies and the waits from
* teach_table. After them: level - 3 shooters, but not more than 4. 4 + 2 *
* level enemies, but not more than 20: the shooters, and grunts for the
* rest. A bullet each 84 - 8 * level frames, but not less than 24. A hunter
* each 330 - 30 * level frames, but not less than 45.
        lda <level
        cmpa #TEACH_LEVELS
        bhi sl_formula
        deca
        ldb #T_SIZE
        mul
        addd #teach_table
        tfr d,x
        lda T_GRUNTS,x
        sta <grunts
        adda T_SHOOTERS,x
        sta <count              ; grunts and shooters
        lda T_FIRE,x
        sta <fire_wait
        sta <fire_timer
        ldd T_WAIT,x
        std <hunter_wait
        ldd T_FIRST,x
        std <hunter_timer
        bra sl_controls
sl_formula
        lda #MAX_GRUNTS
        ldb <level
        cmpb #(MAX_GRUNTS-4)/2
        bhs sl_count
        lslb
        addb #4
        tfr b,a
sl_count
        sta <count              ; all enemies at the start
        ldb <level
        subb #3
        cmpb #MAX_SHOOTERS
        bls sl_shooters
        ldb #MAX_SHOOTERS
sl_shooters
        stb <temp
        suba <temp
        sta <grunts             ; the rest are grunts
        lda <level
        cmpa #(84-MIN_FIRE_WAIT)/8+1  ; level 8 and up
        blo sl_fire_calc
        lda #MIN_FIRE_WAIT
        bra sl_fire
sl_fire_calc
        lsla
        lsla
        lsla                    ; 8 * level
        nega
        adda #84
sl_fire sta <fire_wait
        sta <fire_timer
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
sl_wait std <hunter_wait
        std <hunter_timer
sl_controls
        ifdef HUNTER_SOON       ; check only: a hunter each 15 frames
        ldd #15
        std <hunter_wait
        std <hunter_timer
        endc
        ifdef FIXED_ENEMIES     ; check only: no hunter and no bullets
        ldd #0
        std <hunter_wait
        std <hunter_timer
        clr <fire_wait
        endc
        ifdef ONE_SHOOTER       ; check only: one shooter, no hunter
        ldd #0
        std <hunter_wait
        std <hunter_timer
        lda #20
        sta <fire_wait
        sta <fire_timer
        ldu #enemies
        lda #SHOOTER
        sta E_TYPE,u
        ldd #START_X*256+30
        std E_X,u
        lda #SHOOTER_PERIOD
        sta E_TICK,u
        rts
        endc
        ifdef NO_ENEMIES        ; check only: no grunts and no bullets
        clr <fire_wait
        rts
        endc
        ifdef FIXED_ENEMIES     ; check only: a grunt and a hunter
        ldu #enemies
        lda #GRUNT
        sta E_TYPE,u
        lda #HUNTER
        sta E_SIZE+E_TYPE,u
        ldd #100*256+90
        std E_X,u
        ldd #100*256+40
        std E_SIZE+E_X,u
        lda #1
        sta E_TICK,u
        lda #HUNTER_PERIOD
        sta E_SIZE+E_TICK,u
        rts
        endc
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
        lda #GRUNT              ; the first 'grunts' enemies are grunts,
        tst <grunts             ; the rest are shooters
        beq sl_shooter
        dec <grunts
        bra sl_type
sl_shooter
        lda #SHOOTER
sl_type sta E_TYPE,u
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
        ldx #periods
        ldb a,x                 ; the period of this enemy type
        stb E_TICK,u
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

* --- Move each enemy bullet one step. Remove a bullet that leaves the
* arena.
move_bullets
        ldx #bullets
mb_slot tst B_ON,x
        beq mb_next
        lda B_X,x
        adda B_VX,x
        sta B_X,x
        cmpa #MIN_X
        blo mb_off
        cmpa #END_X-BULLET_W
        bhi mb_off
        lda B_Y,x
        adda B_VY,x
        sta B_Y,x
        cmpa #MIN_Y
        blo mb_off
        cmpa #END_Y-BULLET_H
        bls mb_next
mb_off  clr B_ON,x
mb_next leax B_SIZE,x
        cmpx #bullets_end
        blo mb_slot
        rts

* --- Count down the fire wait. At 0, the next shooter in slot order, after
* the one that fired last, fires a bullet at the player if a bullet slot is
* free.
enemy_fire
        lda <fire_wait
        beq ef_done             ; no bullets on this level
        dec <fire_timer
        bne ef_done
        sta <fire_timer
        lda #ENEMIES
        sta <count
ef_scan ldb <shooter_turn
        incb
        cmpb #ENEMIES
        blo ef_wrap
        clrb
ef_wrap stb <shooter_turn
        lslb
        lslb                    ; E_SIZE = 4
        ldu #enemies
        leau b,u
        lda E_TYPE,u
        cmpa #SHOOTER
        beq ef_found
        dec <count
        bne ef_scan
ef_done rts                     ; no shooter is left
ef_found
        ldx #bullets
ef_free tst B_ON,x
        beq ef_aim
        leax B_SIZE,x
        cmpx #bullets_end
        blo ef_free
        rts                     ; no free slot: this shooter does not fire
* The bullet starts in the middle of the shooter. AX = the pixels across
* to the player, AY = the rows down or up. A pixel is about two rows wide.
* If AX > AY, the bullet goes only across. If AY / 4 > AX, it goes only
* down or up. If not, it goes on a diagonal.
ef_aim  lda E_X,u
        adda #(ENEMY_W-BULLET_W)/2
        sta B_X,x
        lda E_Y,u
        adda #(ENEMY_H-BULLET_H)/2
        sta B_Y,x
        ldb #BULLET_VX
        lda <px
        suba E_X,u
        bhs ef_ax
        nega
        negb                    ; the player is to the left
ef_ax   sta <right              ; AX
        stb B_VX,x
        ldb #BULLET_VY
        lda <py
        suba E_Y,u
        bhs ef_ay
        nega
        negb                    ; the player is above
ef_ay   sta <bottom             ; AY
        stb B_VY,x
        lda <right
        cmpa <bottom
        bls ef_steep
        clr B_VY,x              ; AX > AY: only across
        bra ef_on
ef_steep
        lda <bottom
        lsra
        lsra
        cmpa <right
        bls ef_on
        clr B_VX,x              ; AY / 4 > AX: only down or up
ef_on   lda #1
        sta B_ON,x
        ldx #fx_zap
        lda #P_ZAP
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
        pshs x
        ldx #points
        lda E_TYPE,u
        ldb a,x                 ; the points of this enemy type
        puls x
        clr E_TYPE,u
        clr S_ON,x
        pshs x,u
        pshs b
        ldx #fx_boom
        lda #P_BOOM
        jsr start_sound
        puls a
        jsr add_score
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
* A bullet hits when it overlaps the player.
        ldu #bullets
hp_bullet
        tst B_ON,u
        beq hp_bullet_next
        lda B_X,u
        adda #BULLET_W
        cmpa <px                ; bullet right > player left
        bls hp_bullet_next
        lda <px
        adda #PLAYER_W
        cmpa B_X,u              ; player right > bullet left
        bls hp_bullet_next
        lda B_Y,u
        adda #BULLET_H
        cmpa <py
        bls hp_bullet_next
        lda <py
        adda #PLAYER_H
        cmpa B_Y,u
        bhi hp_touch
hp_bullet_next
        leau B_SIZE,u
        cmpu #bullets_end
        blo hp_bullet
        andcc #$FE              ; carry clear: not touched
        rts
hp_touch
        orcc #$01               ; carry set: touched
        rts

* --- Start effect X with priority A, if A is the same as or higher
* than the priority of the effect that plays now.
* --- Start a game: score, lives and level, the start sound, the level.
new_game
        clr <score
        ldd #FIRST_SCORE
        std <score+1
        clr <next_extra
        ldd #EXTRA_EVERY*256    ; 1000: BCD 00 10 00
        std <next_extra+1
        lda #FIRST_LIVES
        sta <lives
        lda #FIRST_LEVEL
        sta <level
        ldx #fx_start
        lda #P_START
        jsr start_sound
        jmp start_level

* --- Add A (BCD, 00-99) to the 6-digit BCD score. DAA after ADDA or
* ADCA corrects A to BCD and sets the carry for the next byte
* (Leventhal PDF 488). At the next 1000, give an extra life.
add_score
        adda <score+2
        daa
        sta <score+2
        lda <score+1
        adca #0
        daa
        sta <score+1
        lda <score
        adca #0
        daa
        sta <score
        ldd <score              ; score < next_extra: no extra life
        cmpd <next_extra
        blo as_done
        bhi as_extra
        lda <score+2
        cmpa <next_extra+2
        blo as_done
as_extra
        inc <lives
        lda <next_extra+1
        adda #EXTRA_EVERY
        daa
        sta <next_extra+1
        lda <next_extra
        adca #0
        daa
        sta <next_extra
        ldx #fx_extra
        lda #P_EXTRA
        jsr start_sound
as_done rts

start_sound
        cmpa <priority
        blo ss_done
        sta <priority
        stx <effect
        clr <hold               ; the first record plays at the next field
ss_done rts

* --- Once a frame: take the next record of the effect. Each record is
* mode, period and volume. Mode 0 is a square wave and NOISE is noise.
* Volume is the DAC step, 0-63, shifted left 2 for $FF20 bits 7-2.
sound_frame
        lda <level_out          ; start each frame at DAC 0
        anda #3
        sta <level_out
        sta $FF20
        lda <hold               ; keep the record for its fields
        cmpa #1
        bls sf_next
        deca
        sta <hold
        rts
sf_next ldx <effect
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
        lda 3,x
        sta <hold
        leax 4,x
        stx <effect
        rts
sf_end  ldx #0
        stx <effect
        clr <priority
        clr <hold
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
fx_shot fcb 0,8,24,1,0,10,22,1,0,13,18,1,0,17,14,1,0,22,10,1,FX_END
fx_boom fcb NOISE,2,44,1,NOISE,2,40,1,NOISE,3,34,1,NOISE,3,28,1
        fcb NOISE,4,22,1,NOISE,4,16,1,NOISE,5,10,1,NOISE,6,6,1,FX_END
fx_hunter
        fcb 0,10,26,2,0,14,26,2,0,10,26,2,0,14,26,2,FX_END
fx_level
        fcb 0,30,28,3,0,22,28,3,0,16,28,3,0,11,28,3,0,11,20,1,0,11,12,1
        fcb FX_END
fx_death
        fcb NOISE,1,60,1,NOISE,1,56,1,NOISE,2,52,1,NOISE,2,48,1
        fcb NOISE,3,44,1,NOISE,3,40,1,NOISE,4,36,1,NOISE,4,32,1
        fcb NOISE,5,28,1,NOISE,6,24,1,NOISE,7,20,1,NOISE,8,16,1
        fcb NOISE,9,12,1,NOISE,10,8,1,FX_END
* Extra life: a fast high trill.
fx_extra
        fcb 0,15,30,2,0,10,30,2,0,15,30,2,0,10,30,2,0,15,30,2,0,10,30,2
        fcb 0,10,20,2,FX_END
* Start: a rising C-E-G-C, then G-C. Periods 48, 38, 31, 23 are about
* 526, 657, 796 and 1050 Hz.
fx_start
        fcb 0,48,28,4,0,38,28,4,0,31,28,4,0,23,28,6,0,31,28,3,0,23,28,12
        fcb 0,23,18,4,0,23,10,4,FX_END
* Game over: a slow falling G-E flat-D-C. Periods 32, 40, 43, 48 are
* about 773, 626, 584 and 526 Hz.
fx_over fcb 0,32,28,20,0,40,28,20,0,43,28,20,0,48,28,30,0,48,20,15
        fcb 0,48,12,15,FX_END
no_icon fcb FLOOR,FLOOR,FLOOR,FLOOR,FLOOR
* Enemy bullet: a short falling note. Periods 12, 16, 20 are about 1897,
* 1449 and 1172 Hz.
fx_zap  fcb 0,12,22,1,0,16,18,1,0,20,14,1,FX_END

* For each enemy type (0, GRUNT, HUNTER, SHOOTER): the frames between two
* steps, the points (BCD) and the sprite.
periods fcb 0,GRUNT_PERIOD,HUNTER_PERIOD,SHOOTER_PERIOD
points  fcb 0,$10,$50,$30
enemy_sprites
        fdb 0,grunt,hunter,shooter

* --- Text records: the byte offset in the screen (row x 32 + byte
* column), the colour, the characters, 0. $FFFF ends a list.
title_texts
        fdb 10*32+3
        fcb BIG+YELLOW_TEXT
        fcc "ARENA BLASTER"
        fcb 0
        fdb 28*32+10
        fcb YELLOW_TEXT
        fcc "HIGH SCORES"
        fcb 0
        fdb 138*32+7            ; beside the grunt at pixel 20, row 136
        fcb YELLOW_TEXT
        fcc "10"
        fcb 0
        fdb 138*32+15           ; beside the hunter at pixel 52, row 136
        fcb YELLOW_TEXT
        fcc "50"
        fcb 0
        fdb 138*32+23           ; beside the shooter at pixel 84, row 136
        fcb YELLOW_TEXT
        fcc "30"
        fcb 0
        fdb 172*32+5
        fcb GREEN_TEXT
        fcc "MOVE WASD  SHOOT OKL;"
        fcb 0
        fdb $FFFF
entry_texts
        fdb 20*32+2
        fcb BIG+YELLOW_TEXT
        fcc "NEW HIGH SCORE"
        fcb 0
        fdb 60*32+6
        fcb YELLOW_TEXT
        fcc "ENTER YOUR INITIALS"
        fcb 0
        fdb 120*32+3
        fcb GREEN_TEXT
        fcc "W AND S CHANGE THE LETTER"
        fcb 0
        fdb 130*32+3
        fcb GREEN_TEXT
        fcc "SHOOT FOR THE NEXT LETTER"
        fcb 0
        fdb $FFFF
level_text
        fcc "LEVEL "
        fcb 0

* --- The first levels: grunts, the first hunter wait, the hunter wait and
* the hint. The hint is a text list, centred on row 76, in green.
* Each row: grunts, shooters, the fire wait, then the first hunter wait,
* the hunter wait and the hint.
teach_table
        fcb 4,0,0
        fdb 0,0,hint_1
        fcb 8,0,0
        fdb 0,0,hint_2
        fcb 6,0,0
        fdb 60,240,hint_3
        fcb 10,0,0
        fdb 210,210,hint_4
        fcb 12,2,60
        fdb 180,180,hint_5
hint_1  fdb 76*32+8
        fcb GREEN_TEXT
        fcc "SHOOT THE GRUNTS"
        fcb 0
        fdb $FFFF
hint_2  fdb 76*32+2
        fcb GREEN_TEXT
        fcc "HOLD TWO KEYS FOR DIAGONALS"
        fcb 0
        fdb $FFFF
hint_3  fdb 76*32+8
        fcb GREEN_TEXT
        fcc "HUNTERS ARE FAST"
        fcb 0
        fdb $FFFF
hint_4  fdb 76*32+7
        fcb GREEN_TEXT
        fcc "MORE OF EVERYTHING"
        fcb 0
        fdb $FFFF
hint_5  fdb 76*32+7
        fcb GREEN_TEXT
        fcc "SHOOTERS FIRE BACK"
        fcb 0
        fdb $FFFF
prompt_on
        fcc "SHOOT TO START"
        fcb 0
prompt_off
        fcc "              "
        fcb 0

* --- The high-score table: PLACES entries of 3 BCD score bytes and 3
* letters, the highest first. It is in RAM, so it keeps new entries while
* the machine is on. Made-up start entries, 10000 down to 1000.
table   fcb $01,$00,$00
        fcc "ZAP"
        fcb $00,$90,$00
        fcc "ACE"
        fcb $00,$80,$00
        fcc "MAX"
        fcb $00,$70,$00
        fcc "JET"
        fcb $00,$60,$00
        fcc "SKY"
        fcb $00,$50,$00
        fcc "REX"
        fcb $00,$40,$00
        fcc "ION"
        fcb $00,$30,$00
        fcc "VOX"
        fcb $00,$20,$00
        fcc "KIT"
        fcb $00,$10,$00
        fcc "DOT"

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
hold    rmb 1                   ; fields left of the current record
score   rmb 3                   ; BCD, 6 digits, most significant first
next_extra rmb 3                ; BCD: the score for the next extra life
lives   rmb 1                   ; lives left, with the one in play
dying   rmb 1                   ; frames left of the pause after a death
over    rmb 1                   ; frames left of the pause after game over
phase   rmb 1                   ; TITLE, PLAY or ENTRY
old_fire rmb 1                  ; the shoot keys of the last frame
fire_new rmb 1                  ; shoot keys held now, not in the last frame
target  rmb 1                   ; high byte of the screen for a new picture
tcolour rmb 1                   ; text colour, and BIG
tbits   rmb 1
rows    rmb 1
trow    rmb 1
rank    rmb 1                   ; the place for the score, or PLACES
new_rank rmb 1                  ; the place of the last new entry, or $FF
pos     rmb 1                   ; the letter at the cursor, 0-2
rpt     rmb 1                   ; frames until a held W or S repeats
initials rmb 3
ready   rmb 1                   ; frames left of the banner
grunts  rmb 1                   ; grunts left to place in start_level
fire_wait rmb 1                 ; frames between two bullets, 0 = none
fire_timer rmb 1                ; frames until the next bullet
shooter_turn rmb 1              ; the slot of the shooter that fired last
bullets rmb BULLETS*B_SIZE
bullets_end
state_end
        end start
