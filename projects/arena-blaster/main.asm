* Arena Blaster: an original arena shooter for the CoCo 1.
* Increment 11a: a demo that starts when the title is idle for 10 seconds.
* Increment 10: jinxes, pickups that hurt, and the names of the gift and
* the jinx in the band.
* Increment 9: things to collect: points, power-ups and bombs.
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
*   Disk Basic Unravelled II (Spectral Associates; revised by W. K. Zydhek,
*     1999), PDF 15: $FF40 bits. PDF 20: Disk BASIC RAM starts at $600.
*     PDF 70: the IRQ handler turns the drive motors off.

SCREEN_A equ $0400
SCREEN_B equ $2400
STATE   equ $1C00
LIST_A  equ $1D00               ; erase list of screen A: first byte, erase routine
LIST_B  equ $1E00               ; erase list of screen B
EXTRA   equ $1F00               ; more state, not in the direct page
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

SHOTS   equ 10                  ; shot slots
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
BULLET_H equ 4
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
*   FIXED_PICKUP=N a level starts with a pickup of type N at x 60, y 60.
*   DROP_EVERY, FIRST_POWER, POWER_TIME  other values for the pickups.
*   FIRST_JINX, JINX_TIME  a jinx at the start of a game, and its time.
*   FIRST_DROP   the first place in drop_order.
*   DEMO_SOON    the demo starts after 30 idle frames on the title, not 300.
*   FIRST_PART=N the first demo part.
*   FIRST_SCENE=N the first demo after power-on starts at scene N.
*   FIRST_LEVEL, FIRST_LIVES, FIRST_SCORE  other start values.

* Things to collect (README.md "Things to collect"). Pickup types:
PK_POINTS equ 1                 ; 100 points
PK_DOUBLE equ 2                 ; shots in 2 directions: also the power
PK_SPREAD equ 3                 ; shots in 4 directions
PK_STAR equ 4                   ; shots in 8 directions
PK_BOMB equ 5                   ; clears the enemies near the player
PK_SLOW equ 6                   ; jinx: half the fire speed
PK_HEAVY equ 7                  ; jinx: half the move speed
PK_BLITZ equ 8                  ; jinx: hunters come in at once
DROP_TYPES equ 11               ; entries in drop_order
PICKUP_W equ 6
PICKUP_H equ 7
PICKUP_LEVEL equ 4              ; the first level with pickups
BOMB_LEVEL equ 6                ; the first level with bombs
JINX_LEVEL equ 8                ; the first level with jinxes
BLITZ_HUNTERS equ 3             ; hunters that a blitz tries to place
BLITZ_FRAMES equ 60             ; the band shows BLITZ for 2 seconds
PICKUP_FRAMES equ 150           ; a pickup stays 5 seconds
BLINK_FRAMES equ 60             ; it blinks in its last 2 seconds
BOMB_X  equ 40                  ; a bomb clears enemies less than 40
BOMB_Y  equ 60                  ; pixels across and 60 rows away
        ifndef DROP_EVERY
DROP_EVERY equ 6                ; each 6th enemy that a shot removes
        endc
        ifndef POWER_TIME
POWER_TIME equ 300              ; a power lasts 10 seconds
        endc
        ifndef FIRST_POWER
FIRST_POWER equ 0               ; the power at the start of a game
        endc
        ifndef JINX_TIME
JINX_TIME equ 150               ; a jinx lasts 5 seconds
        endc
        ifndef FIRST_JINX
FIRST_JINX equ 0                ; the jinx at the start of a game
        endc
        ifndef FIRST_DROP
FIRST_DROP equ 0                ; the first place in drop_order
        endc
NAME_GIFT equ 8                 ; byte columns of the names in the band
NAME_JINX equ 17
BAR_ROW equ 9                   ; the timer bars: rows 9-10, 6 bytes
BAR_BYTES equ 6
GIFT_STEP equ 50                ; frames for each byte of a bar
JINX_STEP equ 25

* The demo (README.md "Demo"). A part is a list of scenes. After a part,
* the title shows again, and the next idle time starts the next part.
        ifdef DEMO_SOON
IDLE_FRAMES equ 30
        else
IDLE_FRAMES equ 300             ; 10 seconds of the title with no key
        endc
        ifndef FIRST_PART
FIRST_PART equ 0
        endc
PROMPT_COL equ 9                ; the byte column of the demo prompt
        ifndef FIRST_SCENE
FIRST_SCENE equ 0               ; check only: the first demo starts here
        endc
SC_CAPTION equ 0                ; scene record: the banner text list
SC_X    equ 2                   ; the player's start
SC_Y    equ 3
SC_FIRE equ 4                   ; frames between two bullets, 0 = none
SC_FIRST equ 5                  ; frames until the first hunter, 2 bytes
SC_WAIT equ 7                   ; frames between two hunters, 0 = none
SC_SEED equ 9                   ; the random sequence, 2 bytes
SC_PICKUP equ 11                ; pickup type (0 = none), x, y
SC_POWER equ 14
SC_JINX equ 15
SC_SCRIPT equ 16                ; the keys: pairs of keys and frames, 0 ends
SC_ENEMIES equ 18               ; type, x, y for each enemy; 0 ends

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
TEACH_LEVELS equ 6              ; levels with their own row in teach_table
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
P_PICKUP equ 4
P_JINX  equ 4
P_BOMB  equ 5
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
* Disk BASIC turns the drive motor off in its IRQ handler, which no longer
* runs. So turn the motors off here: $FF40 is a write-only latch, bit 3 = 1
* motors on (Disk Basic Unravelled II, PDF 15). 0 also clears the drive
* selects and the halt flag. The Disk BASIC IRQ handler stores the same
* way (PDF 70).
        clr $FF40
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
        lda #FIRST_PART
        sta <part
        lda #2*FIRST_SCENE
        sta <skip
        ifdef SKIP_TITLE        ; check only: a game at once
        lda #PLAY
        sta <phase
        jsr new_game
        jsr resync
        else
        jsr setup_title         ; phase = TITLE (0): the title screen
        lda #SCREEN_A/256       ; at power-on, both screens at once
        jsr title_screen
        clr <fresh
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
        beq frame_game
        cmpa #ENTRY
        lbeq frame_entry
* Title: a shoot key that was not held in the last frame starts a game.
* Any other game key starts the idle count again. After IDLE_FRAMES
* frames with no key, the next part of the demo starts.
        lda <fire_new
        bne frame_start
        lda <move_keys
        ora <fire_keys
        beq frame_idle
        ldd #0
        std <idle
        lbra frame_still
frame_idle
        ldd <idle
        addd #1
        std <idle
        cmpd #IDLE_FRAMES
        lbne frame_still
        jsr start_demo
        lbra frame_draw
* In the demo, a new shoot key starts a game.
frame_game
        tst <demo
        beq frame_over
        lda <fire_new
        beq frame_over
frame_start
        jsr begin_game
        lbra frame_draw
* After game over: wait. Then the initials for a high score, or the title.
frame_over
        lda <over
        beq frame_dying
        dec <over
        lbne frame_draw
        jsr game_end
        lbra frame_still
* After a death: wait. Then take a life, and start the level again or
* end the game.
frame_dying
        lda <dying
        beq frame_ready
        dec <dying
        lbne frame_draw
        dec <lives
        bne frame_again
        ldx #fx_over
        lda #P_OVER
        jsr start_sound
        lda #OVER_FRAMES
        sta <over
        bra frame_draw
frame_again
        clr <power              ; a death ends the power and the jinx
        clr <jinx
        jsr start_level         ; the same level again
        bra frame_draw
* The banner at the start of a level: wait.
frame_ready
        lda <ready
        beq frame_play
        dec <ready
        bra frame_draw
* In the demo, the scene script gives the keys. At its end, the next scene
* of the part starts. After the last scene, the title shows again.
frame_play
        tst <demo
        beq frame_move
        jsr demo_keys
        bcc frame_move
        ldx <scene_ptr
        leax 2,x
        stx <scene_ptr
        ldd ,x
        beq frame_title
        jsr start_scene
        bra frame_draw
frame_title
        jsr setup_title
        lbra frame_still
frame_move
        jsr move_player
        jsr move_shots
        jsr move_bullets
        jsr fire
        jsr move_enemies
        jsr spawn_hunter
        jsr enemy_fire
        jsr hit_enemies
        jsr update_pickup
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
        tst <demo               ; the end of a scene is the end of its keys
        bne frame_draw
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
        jsr fresh_screen
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
        jsr fresh_screen
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
        lda D_MDX,x
        ldb <jinx
        cmpb #PK_HEAVY
        bne mp_x
        asra                    ; heavy: half the step
mp_x    adda <px
        cmpa #MIN_X
        bhs mp_right
        lda #MIN_X
mp_right
        cmpa #END_X-PLAYER_W
        bls mp_store_x
        lda #END_X-PLAYER_W
mp_store_x
        sta <px
        lda D_MDY,x
        ldb <jinx
        cmpb #PK_HEAVY
        bne mp_y
        asra
mp_y    adda <py
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
fire    lda <power                ; a power counts down its time
        beq fire_jinx
        ldd <power_timer
        subd #1
        std <power_timer
        bne fire_jinx
        clr <power
fire_jinx
        lda <jinx               ; so does a jinx
        beq fire_delay
        dec <jinx_timer
        bne fire_delay
        clr <jinx
fire_delay
        lda <delay
        beq fire_ready
        deca
        sta <delay
        rts
* The shoot keys give a direction. Its place in 'ring' (the 8 directions in
* turn) is the first shot. A power adds shots at even steps around the
* ring: 2 shots each 4 places, 4 shots each 2 places, 8 shots each place.
fire_ready
        ldb <fire_keys
        ldx #directions
        ldb b,x                 ; direction number 0-8
        cmpb #4
        beq fire_done           ; no direction
        ldx #ring_pos
        lda b,x
        sta <fpos
        ldb <power
        ldx #power_count
        lda b,x
        sta <fcount
        ldx #power_step
        lda b,x
        sta <fstep
        clr <fired
fire_dir
        lda <fpos
        anda #7
        ldx #ring
        ldb a,x                 ; the direction of this shot
        lda #D_SIZE
        mul
        ldx #dir_table
        leax d,x
        bsr fire_one
        lda <fpos
        adda <fstep
        sta <fpos
        dec <fcount
        bne fire_dir
        tst <fired
        beq fire_done           ; no free slot
        lda #SHOT_DELAY
        ldb <jinx
        cmpb #PK_SLOW
        bne fire_wait_store
        lda #2*SHOT_DELAY+1     ; slow: half as many shots
fire_wait_store
        sta <delay
        ldx #fx_shot
        lda #P_SHOT
        jmp start_sound
fire_done
        rts

* X = a direction record: start a shot in the first free slot, if any.
fire_one
        ldu #shots
fo_slot tst S_ON,u
        beq fo_start
        leau S_SIZE,u
        cmpu #shots_end
        blo fo_slot
        rts
fo_start
        inc <fired
        ldd D_SPR,x
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
        rts

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
        lda <pk_type            ; the pickup: it blinks near its end
        beq df_no_pickup
        ldb <pk_timer
        cmpb #BLINK_FRAMES
        bhs df_pickup
        bitb #4
        bne df_no_pickup
df_pickup
        lsla
        ldu #pickup_sprites
        ldu a,u
        lda <pk_x
        ldb <pk_y
        lbsr draw_sprite
df_no_pickup
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
        tst <demo               ; the demo: the caption of the scene
        beq db_level
        ldx <scene
        ldu SC_CAPTION,x
        bra db_hint
db_level
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
        bhi db_jinx
        deca
        ldb #T_SIZE
        mul
        addd #teach_table
        tfr d,x
        ldu T_HINT,x
        bra db_hint
db_jinx cmpa #JINX_LEVEL        ; the first level with jinxes has a hint
        bne db_erase
        ldu #hint_jinx
db_hint lda <drawing
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
        tst <demo               ; the demo: SHOOT TO START flashes in the band
        beq dh_score
        ldd #HUD_ROW*32+PROMPT_COL
        adda <drawing
        tfr d,y
        clr <tcolour            ; yellow
        ldu #shoot_on
        lda <frames+1
        bita #16
        beq dh_prompt
        ldu #shoot_off
dh_prompt
        jsr text_at
        bra dh_lives
dh_score
        lda <drawing
        ldb #HUD_ROW*32+1
        tfr d,y                 ; the first digit
        ldx #score
dh_byte lda ,x
        lsra
        lsra
        lsra
        lsra
        lbsr dh_glyph_digit     ; high digit
        lda ,x+
        anda #$0F
        lbsr dh_glyph_digit     ; low digit
        cmpx #score+3
        blo dh_byte
dh_lives
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
        lbsr dh_glyph
        leay -2,y               ; dh_glyph moved Y on by 1
        dec <count
        bne dh_icon
        tst <demo               ; the prompt has the place of the names
        lbne dh_done
* The names of the gift (the power) and the jinx, at byte columns
* NAME_GIFT and NAME_JINX. A name changes rarely, so each screen keeps
* the types that it shows in hud_seen, and a name is drawn only when its
* type differs. Under each name, a bar of the time that is left.
        ldx #hud_seen
        lda <drawing
        cmpa #SCREEN_A/256
        beq dh_seen
        leax 2,x
dh_seen lda <power
        ldb #NAME_GIFT
        bsr dh_name
        leax 1,x
        lda <jinx
        ldb #NAME_JINX
        bsr dh_name
        lda #CURSOR             ; the gift bar: yellow
        sta <tbits
        ldd #GIFT_STEP
        std <temp
        ldd #0
        tst <power
        beq dh_gift_bar
        ldd <power_timer
dh_gift_bar
        pshs d
        ldd #BAR_ROW*32+NAME_GIFT
        adda <drawing
        tfr d,y
        puls d
        bsr dh_bar
        lda #WALL               ; the jinx bar: red
        sta <tbits
        ldd #JINX_STEP
        std <temp
        clra
        ldb <jinx
        beq dh_jinx_bar
        ldb <jinx_timer
dh_jinx_bar
        pshs d
        ldd #BAR_ROW*32+NAME_JINX
        adda <drawing
        tfr d,y
        puls d
* D = frames left, temp = frames for each byte, tbits = the bar byte,
* Y = the first byte. (D + temp - 1) / temp bytes of bar on 2 rows, then
* the floor, BAR_BYTES bytes in all.
dh_bar  clr <rows
br_count
        cmpd #0
        ble br_draw
        inc <rows
        subd <temp
        bra br_count
br_draw ldb #BAR_BYTES
br_byte lda #FLOOR
        tst <rows
        beq br_store
        dec <rows
        lda <tbits
br_store
        sta ,y
        sta 32,y
        leay 1,y
        decb
        bne br_byte
dh_done rts

* A = a pickup type (0 = none), B = a byte column, X = the type that the
* hidden screen shows there. If they differ, draw the name of type A in
* the band (a jinx in red) and keep A at X.
dh_name cmpa ,x
        beq dn_done
        sta ,x
        pshs b
        ldb #7
        mul
        addd #names
        tfr d,u
        puls b
        lda ,x
        cmpa #PK_SLOW
        lda #YELLOW_TEXT        ; LDA keeps the carry
        blo dn_colour
        lda #RED_TEXT
dn_colour
        sta <tcolour
        lda <drawing
        addd #HUD_ROW*32
        tfr d,y
        jmp text_at
dn_done rts

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
        clr <demo
        bsr arena_screens
        jsr new_game
        bra resync

* --- The arena in both screens, for a game or the demo.
arena_screens
        lda #PLAY
        sta <phase
        lda <drawing
        clrb
        tfr d,x
        jsr prepare_screen
        jsr other_fresh
        ldd #LIST_A             ; nothing to erase
        std <end_a
        ldd #LIST_B
        std <end_b
        ldd #0                  ; both screens show no names
        std <hud_seen
        std <hud_seen+2
        rts

* --- From the idle title: the next part of the demo. The demo player has
* one life and cannot die. It plays at level 1, so no enemy leaves a
* pickup.
start_demo
        lda #1
        sta <demo
        bsr arena_screens
        lda #1
        sta <lives
        sta <level
        ldd #0
        std <score
        sta <score+2
        clr <next_extra
        ldd #EXTRA_EVERY*256
        std <next_extra+1
        ldx #parts
        lda <part
        lsla
        ldx a,x                 ; the scene list of the part
        ldb <skip               ; check only: skip scenes, one time
        abx
        clr <skip
        stx <scene_ptr
        lda <part               ; the next part, in a ring
        inca
        cmpa #PARTS
        blo sd_part
        clra
sd_part sta <part
        bsr start_scene
        bra resync

* --- The scene at scene_ptr: the player, the enemies, the pickup, the
* waits, the random sequence, the power and the jinx, from its record.
* The caption shows in the banner.
start_scene
        ldx [scene_ptr]
        stx <scene
        ldd SC_X,x
        std <px                 ; px and py
        jsr clear_arena
        ldx <scene
        lda SC_FIRE,x
        sta <fire_wait
        sta <fire_timer
        ldd SC_FIRST,x
        std <hunter_timer
        ldd SC_WAIT,x
        std <hunter_wait
        ldd SC_SEED,x
        std <seed
        lda SC_PICKUP,x
        sta <pk_type
        ldd SC_PICKUP+1,x
        std <pk_x               ; pk_x and pk_y
        lda #PICKUP_FRAMES
        sta <pk_timer
        lda SC_POWER,x
        sta <power
        ldd #POWER_TIME
        std <power_timer
        lda SC_JINX,x
        sta <jinx
        lda #JINX_TIME
        sta <jinx_timer
        ldd SC_SCRIPT,x
        std <dptr
        clr <dcount
        lda #READY_FRAMES
        sta <ready
        leax SC_ENEMIES,x
        ldu #enemies
        ldy #periods
sc_enemy
        lda ,x+
        beq sc_done
        sta E_TYPE,u
        ldb a,y
        stb E_TICK,u
        ldd ,x++
        std E_X,u
        leau E_SIZE,u
        bra sc_enemy
sc_done rts

* --- The keys of the demo player for this frame, from the script: pairs
* of a key byte (move keys in bits 3-0, shoot keys in bits 7-4) and a
* count of frames. Carry set at the end of the script.
demo_keys
        lda <dcount
        bne dk_keys
        ldx <dptr
        ldd ,x++
        tstb
        beq dk_end
        stx <dptr
        sta <dkeys
        stb <dcount
dk_keys dec <dcount
        lda <dkeys
        tfr a,b
        anda #$0F
        sta <move_keys
        lsrb
        lsrb
        lsrb
        lsrb
        stb <fire_keys
        andcc #$FE
        rts
dk_end  orcc #$01
        rts

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
        clr <demo
        ldd #0
        std <idle
        lda <drawing
        bsr title_screen
        bsr other_fresh
        lbra resync

* --- A new screen goes only into the hidden screen, so that the shown
* screen does not change while the VDG shows it. 'fresh' keeps the other
* screen. The first frame that draws into it draws the new screen first.
other_fresh
        lda <drawing
        eora #(SCREEN_A^SCREEN_B)/256
        sta <fresh
        rts

* At the start of drawing a frame: the new screen of the phase, if the
* hidden screen does not have it yet.
fresh_screen
        lda <fresh
        cmpa <drawing
        bne fh_done
        clr <fresh
        ldb <phase
        cmpb #ENTRY
        lbeq entry_screen       ; A = the screen
        cmpb #PLAY
        beq fh_arena
        bra title_screen
fh_arena
        clrb
        tfr d,x
        jmp prepare_screen
fh_done rts

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
        lda <drawing
        bsr entry_screen
        lbsr other_fresh
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
        bsr clear_arena
        ifdef FIXED_PICKUP      ; check only: a pickup above the player
        lda #FIXED_PICKUP
        sta <pk_type
        ldd #60*256+60          ; x 60, y 60
        std <pk_x
        lda #PICKUP_FRAMES
        sta <pk_timer
        endc
        lbra sl_ready

* --- No shots, enemies, bullets or pickup.
clear_arena
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
        clr <pk_type            ; no pickup
        rts
* The banner "LEVEL N" first: nothing moves for READY_FRAMES frames.
sl_ready
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
sh_try  bsr new_hunter
        bcc sh_done
        ldd <hunter_wait
        std <hunter_timer
        ldx #fx_hunter
        lda #P_HUNTER
        jmp start_sound
sh_done rts

* --- A hunter in the first free slot, at a random place on a random edge,
* but not near the player. Carry set if a hunter came in.
new_hunter
        ldu #enemies
sh_slot tst E_TYPE,u
        beq sh_free
        leau E_SIZE,u
        cmpu #enemies_end
        blo sh_slot
nh_none andcc #$FE              ; carry clear: no hunter
        rts
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
        blo nh_none
sh_place
        lda #HUNTER
        sta E_TYPE,u
        lda #HUNTER_PERIOD
        sta E_TICK,u
        orcc #$01               ; carry set: a hunter came in
        rts

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

* --- An enemy at U was removed by a shot. From PICKUP_LEVEL, each
* DROP_EVERY-th such enemy leaves a pickup at its place, if no pickup is
* there. The types come in the order of drop_order. Before BOMB_LEVEL, a
* bomb is points. Before JINX_LEVEL, a jinx is skipped. The pickup x is a multiple of 4, so assets.py makes only
* one draw routine for each pickup.
drop_pickup
        lda <level
        cmpa #PICKUP_LEVEL
        blo dp_done
        dec <drop_count
        bne dp_done
        lda #DROP_EVERY
        sta <drop_count
        tst <pk_type
        bne dp_done
dp_next ldb <pk_next            ; the next place in drop_order, in a ring
        tfr b,a
        inca
        cmpa #DROP_TYPES
        blo dp_ring
        clra
dp_ring sta <pk_next
        ldx #drop_order
        lda b,x
        cmpa #PK_SLOW
        blo dp_gift
        ldb <level
        cmpb #JINX_LEVEL
        blo dp_next             ; a jinx before JINX_LEVEL: the next place
dp_gift cmpa #PK_BOMB
        bne dp_type
        ldb <level
        cmpb #BOMB_LEVEL
        bhs dp_type
        lda #PK_POINTS
dp_type sta <pk_type
        lda E_X,u
        anda #$FC               ; a multiple of 4: one byte column
        sta <pk_x
        lda E_Y,u
        adda #(ENEMY_H-PICKUP_H)/2
        sta <pk_y
        lda #PICKUP_FRAMES
        sta <pk_timer
dp_done rts

* --- If the player overlaps the pickup, collect it. If not, count down
* its time.
update_pickup
        lda <pk_type
        beq up_done
        lda <pk_x
        adda #PICKUP_W
        cmpa <px                ; pickup right > player left
        bls up_time
        lda <px
        adda #PLAYER_W
        cmpa <pk_x
        bls up_time
        lda <pk_y
        adda #PICKUP_H
        cmpa <py
        bls up_time
        lda <py
        adda #PLAYER_H
        cmpa <pk_y
        bhi up_collect
up_time dec <pk_timer
        bne up_done
        clr <pk_type            ; time is up
up_done rts
up_collect
        lda <pk_type
        clr <pk_type
        cmpa #PK_POINTS
        bne up_power
        lda #$50                ; 100 points: two adds of BCD 50
        jsr add_score
        lda #$50
        jsr add_score
        bra up_sound
up_power
        cmpa #PK_BOMB
        beq bomb
        cmpa #PK_SLOW
        bhs up_jinx
        sta <power              ; PK_DOUBLE, PK_SPREAD or PK_STAR
        ldd #POWER_TIME
        std <power_timer
up_sound
        ldx #fx_pickup
        lda #P_PICKUP
        jmp start_sound
* A jinx takes the place of the jinx before it. A blitz shows its name for
* BLITZ_FRAMES, and tries to bring in BLITZ_HUNTERS hunters at once.
up_jinx sta <jinx
        ldb #JINX_TIME
        stb <jinx_timer
        cmpa #PK_BLITZ
        bne up_jinx_sound
        ldb #BLITZ_FRAMES
        stb <jinx_timer
        lda #BLITZ_HUNTERS
        sta <count
up_blitz
        jsr new_hunter
        dec <count
        bne up_blitz
up_jinx_sound
        ldx #fx_jinx
        lda #P_JINX
        jmp start_sound

* --- A bomb removes each enemy less than BOMB_X pixels across and BOMB_Y
* rows from the player, and adds its points. It removes all bullets.
bomb    ldu #enemies
bm_slot lda E_TYPE,u
        beq bm_next
        lda E_X,u
        suba <px
        bhs bm_dx
        nega
bm_dx   cmpa #BOMB_X
        bhs bm_next
        lda E_Y,u
        suba <py
        bhs bm_dy
        nega
bm_dy   cmpa #BOMB_Y
        bhs bm_next
        ldx #points
        lda E_TYPE,u
        lda a,x
        clr E_TYPE,u
        pshs u
        jsr add_score
        puls u
bm_next leau E_SIZE,u
        cmpu #enemies_end
        blo bm_slot
        ldx #bullets
bm_bullet
        clr B_ON,x
        leax B_SIZE,x
        cmpx #bullets_end
        blo bm_bullet
        ldx #fx_bomb
        lda #P_BOMB
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
        jsr drop_pickup         ; U = the enemy
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
        tst <demo               ; the demo player cannot die
        beq hp_enemies
        andcc #$FE
        rts
hp_enemies
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
        lda #DROP_EVERY
        sta <drop_count
        lda #FIRST_DROP
        sta <pk_next
        lda #FIRST_POWER
        sta <power
        ldd #POWER_TIME
        std <power_timer
        lda #FIRST_JINX
        sta <jinx
        lda #JINX_TIME
        sta <jinx_timer
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

* Pickup: a fast rising C-E-G. Periods 31, 23, 16 are about 796, 1050 and
* 1467 Hz.
fx_pickup
        fcb 0,31,26,2,0,23,26,2,0,16,26,3,0,16,14,2,FX_END
* Jinx: a slow falling G-E-C, the pickup sound in reverse, and lower.
fx_jinx fcb 0,16,26,3,0,23,26,3,0,31,26,3,0,40,26,4,0,40,14,2,FX_END
* Bomb: a long, loud noise that falls.
fx_bomb fcb NOISE,1,62,2,NOISE,1,58,2,NOISE,2,54,2,NOISE,2,50,2
        fcb NOISE,3,44,2,NOISE,4,38,2,NOISE,5,32,2,NOISE,6,26,2
        fcb NOISE,8,20,2,NOISE,10,14,2,NOISE,12,8,2,FX_END

* --- Shots of a power. ring: the 8 direction numbers in turn, from up,
* clockwise. ring_pos: the place of each direction number in ring. For
* each power (0 none, PK_DOUBLE, PK_SPREAD, PK_STAR): the number of shots
* and the step around the ring.
ring    fcb 1,2,5,8,7,6,3,0
ring_pos fcb 7,0,1,6,0,2,5,4,3
power_count fcb 1,1,2,4,8
power_step fcb 8,8,4,2,1
* The order of the pickup types that enemies leave: DROP_TYPES entries.
* Without the jinxes, it is the order of increment 9.
drop_order
        fcb PK_POINTS,PK_DOUBLE,PK_SLOW,PK_BOMB,PK_SPREAD,PK_HEAVY
        fcb PK_POINTS,PK_STAR,PK_BOMB,PK_BLITZ,PK_DOUBLE
pickup_sprites
        fdb 0,pk_points,pk_double,pk_spread,pk_star,pk_bomb
        fdb pk_slow,pk_heavy,pk_blitz
* The name of each pickup type in the band: 6 characters and 0. Points
* and the bomb have no time, so they have no name.
names   fcc "      "
        fcb 0
        fcc "      "
        fcb 0
        fcc "DOUBLE"
        fcb 0
        fcc "SPREAD"
        fcb 0
        fcc "STAR  "
        fcb 0
        fcc "      "
        fcb 0
        fcc "SLOW  "
        fcb 0
        fcc "HEAVY "
        fcb 0
        fcc "BLITZ "
        fcb 0

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

* --- The demo. parts: the scene list of each part. A scene list ends
* with 0. Keys in a script: move keys in bits 3-0, shoot keys in bits 7-4.
PARTS   equ 3
parts   fdb part_a,part_b,part_c
part_a  fdb scene_grunt,scene_hunter,scene_shooter,0
part_b  fdb scene_points,scene_double,scene_spread,0
part_c  fdb scene_star,scene_bomb,0

scene_grunt
        fdb cap_grunt
        fcb 61,150              ; the player
        fcb 0                   ; no bullets
        fdb 0,0                 ; no hunters
        fdb SEED
        fcb 0,0,0               ; no pickup
        fcb 0,0                 ; no power, no jinx
        fdb keys_grunt
        fcb GRUNT,61,30
        fcb GRUNT,21,50
        fcb GRUNT,101,50
        fcb 0
keys_grunt
        fcb 0,4
        fcb UP*16,8             ; shoot up: the middle grunt
        fcb LEFT,10             ; walk left
        fcb UP*16,8             ; the left grunt
        fcb RIGHT,18            ; walk right
        fcb UP*16,8             ; the right grunt
        fcb 0,16
        fcb 0,0
* Two hunters come from the edges, one from the right and one from the left.
scene_hunter
        fdb cap_hunter
        fcb 61,95
        fcb 0
        fdb 10,50               ; the first hunter after 10 frames, then each 50
        fdb $1234               ; this start gives the right side, then the left
        fcb 0,0,0
        fcb 0,0
        fdb keys_hunter
        fcb 0
keys_hunter
        fcb 0,18
        fcb RIGHT*16,6          ; shoot right: the first hunter
        fcb 0,50
        fcb LEFT*16,8           ; shoot left: the second hunter
        fcb 0,16
        fcb 0,0
* A shooter fires down at the player, who steps aside and back, and shoots.
scene_shooter
        fdb cap_shooter
        fcb 61,150
        fcb 20                  ; a bullet each 20 frames
        fdb 0,0
        fdb SEED
        fcb 0,0,0
        fcb 0,0
        fdb keys_shooter
        fcb SHOOTER,61,30
        fcb 0
keys_shooter
        fcb 0,12
        fcb RIGHT,8             ; step aside before the bullet comes
        fcb 0,14
        fcb LEFT,8              ; step back
        fcb UP*16,10            ; shoot up
        fcb 0,16
        fcb 0,0
cap_hunter
        fdb BANNER_ROW*32+10
        fcb BIG+YELLOW_TEXT
        fcc "HUNTER"
        fcb 0
        fdb 76*32+8
        fcb GREEN_TEXT
        fcc "FAST  50 POINTS"
        fcb 0
        fdb $FFFF
cap_shooter
        fdb BANNER_ROW*32+9
        fcb BIG+YELLOW_TEXT
        fcc "SHOOTER"
        fcb 0
        fdb 76*32+5
        fcb GREEN_TEXT
        fcc "FIRES BACK  30 POINTS"
        fcb 0
        fdb $FFFF
* The player walks right onto a coin.
scene_points
        fdb cap_points
        fcb 40,92
        fcb 0
        fdb 0,0
        fdb SEED
        fcb PK_POINTS,80,94
        fcb 0,0
        fdb keys_points
        fcb 0
keys_points
        fcb 0,6
        fcb RIGHT,22
        fcb 0,14
        fcb 0,0
* The player takes the double, then one shot right hits both grunts.
scene_double
        fdb cap_double
        fcb 52,95
        fcb 0
        fdb 0,0
        fdb SEED
        fcb PK_DOUBLE,64,96
        fcb 0,0
        fdb keys_double
        fcb GRUNT,8,95
        fcb GRUNT,114,95
        fcb 0
keys_double
        fcb 0,4
        fcb RIGHT,4
        fcb 0,10
        fcb RIGHT*16,6
        fcb 0,30
        fcb 0,0
* The player takes the spread, then one shot up hits four grunts.
scene_spread
        fdb cap_spread
        fcb 61,95
        fcb 0
        fdb 0,0
        fdb SEED
        fcb PK_SPREAD,60,108
        fcb 0,0
        fdb keys_spread
        fcb GRUNT,61,20
        fcb GRUNT,61,170
        fcb GRUNT,8,95
        fcb GRUNT,114,95
        fcb 0
keys_spread
        fcb 0,4
        fcb DOWN,4
        fcb 0,10
        fcb UP*16,6
        fcb 0,30
        fcb 0,0
* The player takes the star, then one shot up hits a ring of 8 grunts.
scene_star
        fdb cap_star
        fcb 49,95
        fcb 0
        fdb 0,0
        fdb SEED
        fcb PK_STAR,60,96
        fcb 0,0
        fdb keys_star
        fcb GRUNT,61,15
        fcb GRUNT,61,175
        fcb GRUNT,5,95
        fcb GRUNT,117,95
        fcb GRUNT,23,19
        fcb GRUNT,99,19
        fcb GRUNT,23,171
        fcb GRUNT,99,171
        fcb 0
keys_star
        fcb 0,4
        fcb RIGHT,6
        fcb 0,10
        fcb UP*16,6
        fcb 0,30
        fcb 0,0
* Grunts close in. The player steps onto the bomb, and they all go.
scene_bomb
        fdb cap_bomb
        fcb 61,95
        fcb 0
        fdb 0,0
        fdb SEED
        fcb PK_BOMB,72,96
        fcb 0,0
        fdb keys_bomb
        fcb GRUNT,30,60
        fcb GRUNT,92,60
        fcb GRUNT,30,130
        fcb GRUNT,92,130
        fcb GRUNT,61,50
        fcb GRUNT,61,140
        fcb 0
keys_bomb
        fcb 0,10
        fcb RIGHT,4
        fcb 0,30
        fcb 0,0
cap_points
        fdb BANNER_ROW*32+10
        fcb BIG+YELLOW_TEXT
        fcc "POINTS"
        fcb 0
        fdb 76*32+8
        fcb GREEN_TEXT
        fcc "COLLECT FOR 100"
        fcb 0
        fdb $FFFF
cap_double
        fdb BANNER_ROW*32+10
        fcb BIG+YELLOW_TEXT
        fcc "DOUBLE"
        fcb 0
        fdb 76*32+7
        fcb GREEN_TEXT
        fcc "SHOTS GO TWO WAYS"
        fcb 0
        fdb $FFFF
cap_spread
        fdb BANNER_ROW*32+10
        fcb BIG+YELLOW_TEXT
        fcc "SPREAD"
        fcb 0
        fdb 76*32+7
        fcb GREEN_TEXT
        fcc "SHOTS GO FOUR WAYS"
        fcb 0
        fdb $FFFF
cap_star
        fdb BANNER_ROW*32+12
        fcb BIG+YELLOW_TEXT
        fcc "STAR"
        fcb 0
        fdb 76*32+6
        fcb GREEN_TEXT
        fcc "SHOTS GO EIGHT WAYS"
        fcb 0
        fdb $FFFF
cap_bomb
        fdb BANNER_ROW*32+12
        fcb BIG+YELLOW_TEXT
        fcc "BOMB"
        fcb 0
        fdb 76*32+8
        fcb GREEN_TEXT
        fcc "CLEARS THE AREA"
        fcb 0
        fdb $FFFF
cap_grunt
        fdb BANNER_ROW*32+11
        fcb BIG+YELLOW_TEXT
        fcc "GRUNT"
        fcb 0
        fdb 76*32+8
        fcb GREEN_TEXT
        fcc "SLOW  10 POINTS"
        fcb 0
        fdb $FFFF
shoot_on
        fcc "SHOOT TO START"
        fcb 0
shoot_off
        fcc "              "
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
        fcb 13,3,36
        fdb 150,150,hint_6
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
hint_4  fdb 76*32+5
        fcb GREEN_TEXT
        fcc "COLLECT THE POWER UPS"
        fcb 0
        fdb $FFFF
hint_5  fdb 76*32+7
        fcb GREEN_TEXT
        fcc "SHOOTERS FIRE BACK"
        fcb 0
        fdb $FFFF
hint_6  fdb 76*32+6
        fcb GREEN_TEXT
        fcc "BOMBS CLEAR THE AREA"
        fcb 0
        fdb $FFFF
hint_jinx
        fdb 76*32+8
        fcb GREEN_TEXT
        fcc "SOME GIFTS BITE"
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
pk_type rmb 1                   ; the pickup on the floor, 0 = none
pk_x    rmb 1
pk_y    rmb 1
pk_timer rmb 1                  ; frames until it goes
pk_next rmb 1                   ; the next place in drop_order
drop_count rmb 1                ; enemies until the next pickup
power   rmb 1                   ; 0, PK_DOUBLE, PK_SPREAD or PK_STAR
power_timer rmb 2               ; frames until the power ends
fpos    rmb 1                   ; fire: the place in ring
fstep   rmb 1
fcount  rmb 1
fired   rmb 1                   ; shots that started in this frame
jinx    rmb 1                   ; 0, PK_SLOW, PK_HEAVY or PK_BLITZ
jinx_timer rmb 1                ; frames until the jinx ends
hud_seen rmb 4                  ; the gift and jinx names on screens A, B
idle    rmb 2                   ; title frames with no key
demo    rmb 1                   ; 1 in the demo
part    rmb 1                   ; the next demo part
scene_ptr rmb 2                 ; the place of the scene in its part
scene   rmb 2                   ; the scene record
dptr    rmb 2                   ; the next key pair of the script
dcount  rmb 1                   ; frames left of the current key pair
dkeys   rmb 1
skip    rmb 1                   ; 2 x FIRST_SCENE until the first demo
fresh   rmb 1                   ; the screen that needs the new screen, or 0
state_end

* --- More state after the erase lists, in extended addressing.
        org EXTRA
line    rmb 16                  ; a line of text
shots   rmb SHOTS*S_SIZE
shots_end
bullets rmb BULLETS*B_SIZE
bullets_end
extra_end
        end start
