* Original CoCo 1 NTSC, 32 KiB, stock 6809 first-screen example.
* Source facts: Tandy Color Computer Technical Reference Manual,
* PDF 14 (PIA), 15 (SAM offsets/clock), 30-31 (mode table).
* Inman, Assembly Language Graphics, PDF 106-108: 256x192, 1 bit/pixel.
* RAM: screen $0400-$1BFF; marker $2FFF; code $3000 onward;
* stack grows down from $7F00 (reserve $7E00-$7EFF).
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
        ldx #$0400
clear   sta ,x+
        cmpx #$1C00
        blo clear
* Top and bottom borders, 32 bytes each.
        ldx #$0400
        ldb #32
        lda #$FF
top     sta ,x+
        decb
        bne top
        ldx #$1BE0
        ldb #32
bottom  sta ,x+
        decb
        bne bottom
* Left and right edges for every row.
        ldx #$0400
        ldb #192
edges   lda #$80
        ora ,x
        sta ,x
        lda #$01
        ora 31,x
        sta 31,x
        leax 32,x
        decb
        bne edges
* Solid central 64x64 square: x=96..159, y=64..127.
        ldx #$0C0C
        ldy #64
square  lda #$FF
        ldb #8
span    sta ,x+
        decb
        bne span
        leax 24,x
        leay -1,y
        bne square
* Set SAM video base to $0400: 512-byte units, F6..F0=0000010.
        sta $FFC6
        sta $FFC9
        sta $FFCA
        sta $FFCC
        sta $FFCE
        sta $FFD0
        sta $FFD2
        sta $FFD4
* Stock clock, SAM display mode V2..V0=110.
        sta $FFD6
        sta $FFD8
        sta $FFC0
        sta $FFC3
        sta $FFC5
* Select PIA data register. Preserve unrelated control and low data bits.
        lda $FF23
        ora #4
        sta $FF23
        lda $FF22
        anda #7
        ora #$F0
        sta $FF22
        lda #$A5
        sta $2FFF
ready   bra ready
        end start
