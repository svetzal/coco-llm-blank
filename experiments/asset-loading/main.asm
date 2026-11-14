* Original prepared-asset consumer. Hardware source notes in README.md.
* $0400-$1BFF framebuffer; $3000+ code/data; $7E00-$7EFF stack.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        clr completed
        lda #$A5
        sta $03FF
        sta $1C00
* Poison the whole allocation, then clear it: untouched RAM cannot pass.
        ldx #$0400
poison  sta ,x+
        cmpx #$1C00
        blo poison
        ldx #$0400
clear   clr ,x+
        cmpx #$1C00
        blo clear
* SAM F=2, V=110, page zero, R1:R0=00 (normal clock).
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
        clr cell_row
rows    clr cell_column
columns lda cell_row
        ldb #8
        mul
        addb cell_column
        ldx #room
        lda d,x
        lsla
        ldx #terrain_pointers
        ldu a,x
        lda cell_row
        adda #4
        ldb cell_column
        tfr d,x
        ldb #8
pixels  lda ,u+
        ifdef WRONG_BITS
        coma
        endc
        sta ,x
        leax 32,x
        decb
        bne pixels
        inc cell_column
        lda cell_column
        cmpa #8
        blo columns
        inc cell_row
        lda cell_row
        cmpa #6
        blo rows
        ifdef OVERFLOW
        clr $1C00
        endc
        lda #$5A
        sta completed
ready   bra ready
cell_row fcb 0
cell_column fcb 0
completed fcb 0
        include "assets.inc"
program_end
        end start
