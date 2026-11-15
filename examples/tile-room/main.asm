* Original fixed-room adaptation, not a historical listing. See README.md.
* RG6 $0400-$1BFF, code $3000+, stack $7E00-$7EFF; normal 6809.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        sta step
        sta xpos
        sta ypos
        sta accepted
        lda #$A5
        sta $03FF
        sta $1C00
        sta map_guard_before
        sta map_guard_after
        ldx #initial_map
        ldy #room
        ldb #48
copy    lda ,x+
        sta ,y+
        decb
        bne copy
* SAM base $0400, V=110, page zero, normal clock.
        sta $FFC6
        sta $FFC9
        sta $FFCA
        sta $FFCC
        sta $FFCE
        sta $FFD0
        sta $FFD2
        sta $FFD4
        sta $FFD6
        sta $FFD8
        sta $FFC0
        sta $FFC3
        sta $FFC5
        lda $FF23
        ora #4
        sta $FF23
        lda $FF22
        anda #7
        ora #$F0
        sta $FF22
frame   jsr render
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
        inc step
        bra frame
finished bra finished
* Directions are delta pairs: right, down, left, up. Reject unsigned
* underflow/overflow before calculating any map address.
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
accept  lda candidate_x
        sta xpos
        lda candidate_y
        sta ypos
        lda #1
        sta accepted
        rts
rejected clr accepted
        rts
* Background and actor are rebuilt from current map state, never saved pixels.
render  ldx #$0400
clear   clr ,x+
        cmpx #$1C00
        blo clear
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
        rts
* A is image ID: the pictures table gives its eight byte-aligned rows.
* destination = $0400 + cell_row*256 + cell_column.
tile    lsla
        ldx #pictures
        ldu a,x
        lda tile_row
        adda #4
        ldb tile_column
        tfr d,x
        ldb #8
pixels  lda ,u+
        sta ,x
        leax 32,x
        decb
        bne pixels
        rts
* Image ID to picture: floor, wall, collectible, exit, actor. The labels
* are cells of tiles.png, left to right; prepare.py converts it to tiles.asm.
pictures fdb tiles_r0c0,tiles_r0c1,tiles_r0c2,tiles_r0c3,tiles_r0c4
        include "tiles.asm"
* tile draws 8 rows of 1 byte. Refuse pictures of a different size.
        if tiles_r0c0_bpr-1
        error "tiles.asm: each picture row must be 1 byte"
        endc
        if tiles_r0c0_rows-8
        error "tiles.asm: each picture must be 8 rows"
        endc
passable fcb 1,0,1,1
initial_map
        fcb 0,0,1,0,0,0,0,0
        fcb 0,2,1,0,0,1,0,0
        fcb 0,0,1,0,0,0,0,0
        fcb 0,0,0,0,1,1,0,0
        fcb 0,1,0,0,0,0,0,0
        fcb 0,0,0,0,0,0,3,0
deltas  fcb 1,0,0,1,-1,0,0,-1
moves   fcb 2,3,0,0,1,1,1,0,3,0,3,3,3,3
        fcb 0,0,1,0,0,0,1,1,1,1,1,1,2,0,2
        fcb 2,2,2,2,3,2,3,2,3,3,1,3
moves_end
state
step    fcb 0
xpos    fcb 0
ypos    fcb 0
accepted fcb 0
candidate_x fcb 0
candidate_y fcb 0
tile_row fcb 0
tile_column fcb 0
map_guard_before fcb 0
room    rmb 48
map_guard_after fcb 0
program_end
        end start
