* Arena Blaster: an original arena shooter for the CoCo 1.
* Increment 1: the arena, the player, movement and shots. README.md has the
* contract, the rules for each frame and the memory map.
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
*     PDF 75: keyboard matrix. Row PA0: E=PB5, F=PB6, C=PB3.
*       Row PA1: I=PB1, J=PB2, L=PB4. Row PA2: S=PB3. Row PA5: comma=PB4.
*   Motorola MC6847 datasheet, PDF 19-21 (through the graphics guide):
*     CG6 = 2 bits for each pixel, leftmost pixel in bits 7-6, 32 bytes for
*     each row. Colour set 0: 0 green, 1 yellow, 2 blue, 3 red.
*   Motorola MC6821 datasheet, PDF 10: a read of the data register clears
*     the interrupt flag (through the animation guide).
*   The Rainbow, October 1986, PDF 119: PMODE 3 is graphics mode 6C.

SCREEN_A equ $0400
SCREEN_B equ $2400
STATE   equ $1C00
LIST_A  equ $1D00               ; erase list of screen A, 4 bytes each
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
SHOT_DELAY equ 5                ; frames between two shots is SHOT_DELAY+1

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
D_SIZE  equ 10

* Fields of a shot slot.
S_ON    equ 0                   ; 0 = free
S_X     equ 1
S_Y     equ 2
S_VX    equ 3
S_VY    equ 4
S_SPR   equ 5                   ; 2 bytes
S_MAXX  equ 7
S_MAXY  equ 8
S_SIZE  equ 9

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
        lda #START_X
        sta <px
        lda #START_Y
        sta <py
        ldd #LIST_A
        std <end_a
        ldd #LIST_B
        std <end_b

frame   jsr scan
        jsr move_player
        jsr move_shots
        jsr fire
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
* Column PB1: I (row PA1) shoots up.
        lda #%11111101
        sta $FF02
        lda $FF00
        bita #%00000010
        bne scan_pb2
        lda <fire_keys
        ora #UP
        sta <fire_keys
* Column PB2: J (row PA1) shoots left.
scan_pb2
        lda #%11111011
        sta $FF02
        lda $FF00
        bita #%00000010
        bne scan_pb3
        lda <fire_keys
        ora #LEFT
        sta <fire_keys
* Column PB3: C (row PA0) moves down, S (row PA2) moves left.
scan_pb3
        lda #%11110111
        sta $FF02
        ldb $FF00
        bitb #%00000001
        bne scan_s
        lda <move_keys
        ora #DOWN
        sta <move_keys
scan_s  bitb #%00000100
        bne scan_pb4
        lda <move_keys
        ora #LEFT
        sta <move_keys
* Column PB4: L (row PA1) shoots right, comma (row PA5) shoots down.
scan_pb4
        lda #%11101111
        sta $FF02
        ldb $FF00
        bitb #%00000010
        bne scan_comma
        lda <fire_keys
        ora #RIGHT
        sta <fire_keys
scan_comma
        bitb #%00100000
        bne scan_pb5
        lda <fire_keys
        ora #DOWN
        sta <fire_keys
* Column PB5: E (row PA0) moves up.
scan_pb5
        lda #%11011111
        sta $FF02
        lda $FF00
        bita #%00000001
        bne scan_pb6
        lda <move_keys
        ora #UP
        sta <move_keys
* Column PB6: F (row PA0) moves right.
scan_pb6
        lda #%10111111
        sta $FF02
        lda $FF00
        bita #%00000001
        bne scan_done
        lda <move_keys
        ora #RIGHT
        sta <move_keys
scan_done
        lda #$FF
        sta $FF02
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
        lda #SHOT_DELAY
        sta <delay
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
        ldx ,y
        lda 2,y
        sta <rows
er_row  ldb 3,y
        lda #FLOOR
er_byte sta ,x+
        decb
        bne er_byte
        ldb #32
        subb 3,y
        abx
        dec <rows
        bne er_row
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
        lda <px
        ldb <py
        ldu #player
        bsr draw_sprite
        ldd <next
        std [end_ptr]
        rts

* --- Draw sprite U at pixel x = A, row y = B in the hidden screen.
* screen = (screen AND mask) OR picture, for each byte.
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
        lda ,u
        sta <rows
        lda 1,u
        sta <width
        ldb <temp
        andb #3
        lslb
        addb #2
        ldu b,u                 ; the copy for shift x % 4
        ldy <next
        stx ,y
        lda <rows
        sta 2,y
        lda <width
        sta 3,y
        leay 4,y
        sty <next
ds_row  ldb <width
ds_byte lda ,x
        anda ,u+
        ora ,u+
        sta ,x+
        decb
        bne ds_byte
        ldb #32
        subb <width
        abx
        dec <rows
        bne ds_row
        rts

* --- Show the finished screen at the end of the picture, as in the
* page-flip example. Then select the other screen for drawing.
show    lda $FF02               ; clear an old flag
show_wait
        lda $FF03
        bpl show_wait           ; wait for the falling edge of FS
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
show_new
        lda $FF03
        bpl show_new
        lda $FF03
        anda #%11111101         ; falling edge again
        sta $FF03
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

* --- Tables.
* Direction number for each combination of key bits (UP=1, DOWN=2,
* LEFT=4, RIGHT=8). Number = (dy + 1) * 3 + (dx + 1), so 4 is no
* direction. Opposite keys cancel.
directions
        fcb 4,1,7,4,3,0,6,3,5,2,8,5,4,1,7,4

* One record for each direction number, D_SIZE bytes.
* A shot starts in the middle of the player: ((6 - w) / 2, (10 - h) / 2).
* The largest position is END - size: x <= 124 - w, y <= 187 - h.
*            MDX MDY VX VY  sprite           OX OY MAXX MAXY
dir_table
        fcb -1,-2,-3,-6
        fdb shot_back
        fcb 1,2,121,181         ; 0: up and left   (3x6)
        fcb 0,-2,0,-6
        fdb shot_vertical
        fcb 2,2,123,181         ; 1: up            (1x6)
        fcb 1,-2,3,-6
        fdb shot_forward
        fcb 1,2,121,181         ; 2: up and right  (3x6)
        fcb -1,0,-3,0
        fdb shot_horizontal
        fcb 1,4,120,186         ; 3: left          (4x1)
        fcb 0,0,0,0
        fdb 0
        fcb 0,0,0,0             ; 4: none
        fcb 1,0,3,0
        fdb shot_horizontal
        fcb 1,4,120,186         ; 5: right         (4x1)
        fcb -1,2,-3,6
        fdb shot_forward
        fcb 1,2,121,181         ; 6: down and left (3x6)
        fcb 0,2,0,6
        fdb shot_vertical
        fcb 2,2,123,181         ; 7: down          (1x6)
        fcb 1,2,3,6
        fdb shot_back
        fcb 1,2,121,181         ; 8: down and right (3x6)

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
rows    rmb 1
width   rmb 1
temp    rmb 2
next    rmb 2                   ; next free erase-list entry
end_ptr rmb 2                   ; address of end_a or end_b
end_a   rmb 2                   ; end of the erase list of screen A
end_b   rmb 2
shots   rmb SHOTS*S_SIZE
shots_end
state_end
        end start
