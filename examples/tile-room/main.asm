* Keep a room's state in a tile map, and draw the room from the map (CoCo 1, 2 and 3).
*
* The map holds one tile number for each cell. Drawing and movement both read
* the map: one table gives the picture of each tile number, a second table
* gives its movement rule. To change the room, change the map. The next
* redraw shows the change.
*
* The example is in five parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up RG6, clears the screen,
* includes the pictures that prepare.py converts from tiles.png, and plays a
* script of 41 moves with a pause after each move. A project does not need it.
*
* The variant (coco.toml) replaces part 4, the redraw after a move:
*   (none)  changed  draw the cell that the actor left, then the actor
*   FULL    full     draw every cell of the map, then the actor
*
* Sources:
*   Inman, Inman and Dymax, Assembly Language Graphics for the TRS-80 Color
*     Computer, PDF 106-107: RG6 (6R) is 256x192 at $0400-$1BFF, 6 KiB.
*     Each byte gives eight pixels. Colour set 0: 0 is black, 1 is green.
*   Motorola, MC6847 datasheet, PDF 19 Table 3: RG6 has 256 pixels in each
*     row and uses 6144 bytes. Bit 7 (L7) is the leftmost pixel.
*   Tandy, Color Computer Technical Reference Manual, PDF 14-15 and 31:
*     SAM offset and mode bits, $FF22 bits; RG6 is SAM V=110, $FF22 $F0.
*   Tepolt, Assembly Language Programming for the CoCo3, PDF 46: on a CoCo 3
*     the same SAM and $FF22 values select G6R. A 0 bit selects palette
*     register 8, a 1 bit register 9. PDF 57 step 44: BASIC loads them at
*     reset. The program does not write $FFB0-$FFBF, so it keeps them.

        org $3000
* --- CONTEXT: show RG6 at $0400 with colour set 0, as in first-screen.
* SAM offset F=2 ($0400 / 512), then SAM mode V=110. Keep $FF22 bits 2..0.
start   sta $FFC6
        sta $FFC9
        sta $FFCA
        sta $FFCC
        sta $FFCE
        sta $FFD0
        sta $FFD2
        sta $FFC0
        sta $FFC3
        sta $FFC5
        lda $FF22
        anda #%00000111
        ora #%11110000
        sta $FF22

* --- CONTEXT: clear the screen once. The room covers only its top-left
* corner, 64x48 pixels.
        ldx #$0400
clear   clr ,x+
        cmpx #$1C00
        blo clear

* >>> EXAMPLE 1 of 5: copy the initial map to the room map, then draw it all.
* The room map is in RAM, because a move can change it. The actor starts at
* column 0, row 0.
        ldx #initial_map
        ldy #room
        ldb #48
copy    lda ,x+
        sta ,y+
        decb
        bne copy
        clr xpos
        clr ypos
        jsr draw_room
* <<< END EXAMPLE

* --- CONTEXT: play the script of moves, with a pause after each move.
        clr step
* The check takes one snapshot each time the program reaches this label.
frame_ready
        ldx #12000
pause   leax -1,x
        bne pause
        ldb step
        cmpb #moves_end-moves
        beq finished
        ldx #moves
        lda b,x
        jsr move
        jsr redraw
        inc step
        bra frame_ready
finished bra finished

* >>> EXAMPLE 2 of 5: draw the room, or one cell of it, from the map.
* draw_room draws all 8x6 cells, then the actor.
draw_room
        clr tile_row
room_row
        clr tile_column
room_cell
        jsr draw_cell
        inc tile_column
        lda tile_column
        cmpa #8
        blo room_cell
        inc tile_row
        lda tile_row
        cmpa #6
        blo room_row
* draw_actor draws the actor's picture, 4, at xpos, ypos.
draw_actor
        lda xpos
        sta tile_column
        lda ypos
        sta tile_row
        lda #4
        bra draw_picture
* draw_cell draws the cell at tile_column (0..7), tile_row (0..5).
* Map offset = row * 8 + column.
draw_cell
        lda tile_row
        ldb #8
        mul
        addb tile_column
        ldx #room
        lda d,x
* draw_picture draws picture A at the cell. Screen address = $0400 +
* row * 256 + column: RG6 has 32 bytes in each pixel row, and a cell is
* 8 pixel rows. The 8 rows of a picture are 32 bytes apart.
draw_picture
        lsla
        ldx #pictures
        ldu a,x
        lda tile_row
        adda #4
        ldb tile_column
        tfr d,x
        ldb #8
picture_row
        lda ,u+
        sta ,x
        leax 32,x
        decb
        bne picture_row
        rts
* <<< END EXAMPLE

* >>> EXAMPLE 3 of 5: try a move to the next cell. The map decides.
* A = direction: 0 right, 1 down, 2 left, 3 up. Test the room edge before
* the map address: -1 is $FF, so one unsigned test finds both edges. Then
* test the movement rule of the tile number. A collectible becomes floor in
* the map. Out: accepted is 1 if the actor moved; old_x, old_y is the cell
* that the actor left.
move    lsla
        ldx #deltas
        leax a,x
        lda xpos
        adda ,x
        cmpa #8
        bhs rejected
        sta candidate_x
        ldb ypos
        addb 1,x
        cmpb #6
        bhs rejected
        stb candidate_y
        lda #8
        mul
        addb candidate_x
        ldx #room
        leax d,x
        lda ,x
        ldy #passable
        ldb a,y
        beq rejected
        cmpa #2
        bne accept
        clr ,x
accept  lda xpos
        sta old_x
        lda ypos
        sta old_y
        lda candidate_x
        sta xpos
        lda candidate_y
        sta ypos
        lda #1
        sta accepted
        rts
rejected
        clr accepted
        rts
* <<< END EXAMPLE

* >>> EXAMPLE 4 of 5: redraw after a move.
        ifdef FULL
* Draw every cell from the map, then the actor.
redraw  jmp draw_room
        else
* Draw only the cells that changed: the cell that the actor left, from the
* map, then the actor at its new cell. A rejected move changes nothing.
redraw  tst accepted
        beq redrawn
        lda old_x
        sta tile_column
        lda old_y
        sta tile_row
        jsr draw_cell
        jsr draw_actor
redrawn rts
        endc
* <<< END EXAMPLE

* --- CONTEXT: the pictures. prepare.py converts tiles.png to tiles.asm
* before each build, with labels tiles_r0c0 to tiles_r0c4, left to right.
* draw_picture copies 8 rows of 1 byte, so refuse pictures of another size.
        include "tiles.asm"
        if tiles_r0c0_bpr-1
        error "tiles.asm: each picture row must be 1 byte"
        endc
        if tiles_r0c0_rows-8
        error "tiles.asm: each picture must be 8 rows"
        endc

* >>> EXAMPLE 5 of 5: the tables and the map.
* Tile numbers in the map: floor 0, wall 1, collectible 2, exit 3. The
* actor's picture is 4. It is never in the map.
pictures fdb tiles_r0c0,tiles_r0c1,tiles_r0c2,tiles_r0c3,tiles_r0c4
* The movement rule of each tile number: 1 permits a move onto it.
passable fcb 1,0,1,1
* The change in column, row for each direction: right, down, left, up.
deltas  fcb 1,0,0,1,-1,0,0,-1
* The room at the start: 8 columns, 6 rows, one byte for each cell.
initial_map
        fcb 0,0,1,0,0,0,0,0
        fcb 0,2,1,0,0,1,0,0
        fcb 0,0,1,0,0,0,0,0
        fcb 0,0,0,0,1,1,0,0
        fcb 0,1,0,0,0,0,0,0
        fcb 0,0,0,0,0,0,3,0
* The room map in RAM. Part 1 fills it from initial_map.
room    rmb 48
* <<< END EXAMPLE

* --- CONTEXT: the script of 41 moves, one direction number for each move.
moves   fcb 2,3,0,0,1,1,1,0,3,0,3,3,3,3
        fcb 0,0,1,0,0,0,1,1,1,1,1,1,2,0,2
        fcb 2,2,2,2,3,2,3,2,3,3,1,3
moves_end

* --- CONTEXT: program state. This is a data label: the check fails if the
* CPU executes it.
state
xpos    rmb 1
ypos    rmb 1
old_x   rmb 1
old_y   rmb 1
accepted rmb 1
candidate_x rmb 1
candidate_y rmb 1
tile_row rmb 1
tile_column rmb 1
step    rmb 1
        end start
