* Palette swatches: CoCo 1 NTSC, 32 KiB, stock 6809, VDG CG6 (128x192, 4 colours).
* Source facts:
* Motorola MC6847 datasheet, PDF 20: CG6 is 128x192, four colours, 6k x 8.
* MC6847 PDF 19 Table 3 and PDF 21 Figure 22: one pair of bits per pixel,
*   leftmost pixel in bits 7-6; PDF 21 colour table: pair 00/01/10/11 is
*   green/yellow/blue/red with CSS=0 and buff/cyan/magenta/orange with CSS=1.
* Tandy Color Computer Technical Reference Manual, PDF 31 Table 1: CG6 is
*   SAM V2..V0=110 and $FF22 bits 7-4=1110, bit 3=CSS, bits 2-0 unchanged.
*   PDF 14-15: PIA data register select and SAM display offset, as first-screen.
* RAM: screen $0400-$1BFF; marker $2FFF; code $3000 onward;
* stack grows down from $7F00 (reserve $7E00-$7EFF).
*   Same table: RG6 shares SAM V2..V0=110; $FF22 bits 7-4=1111.
* Defines: CSS1 selects colour set 1; RG6 shows the same bytes in RG6
* (256x192, two colours, bit 7 leftmost: MC6847 PDF 19 Table 3, PDF 20).
        ifdef RG6
VDGMODE equ $F0
        else
VDGMODE equ $E0
        endc
        ifdef CSS1
CSSBIT  equ $08
        else
CSSBIT  equ $00
        endc
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
* Rows 0-159: four bars of 32 pixels (8 bytes) each, pair values 00, 01, 10, 11.
        ldx #$0400
        ldb #160
bars    pshs b
        ldu #pattern
        ldb #4
bar     lda ,u+
        sta ,x+
        sta ,x+
        sta ,x+
        sta ,x+
        sta ,x+
        sta ,x+
        sta ,x+
        sta ,x+
        decb
        bne bar
        puls b
        decb
        bne bars
* Rows 160-191: every byte $1B, pixels 00 01 10 11 from the left.
        lda #$1B
order   sta ,x+
        cmpx #$1C00
        blo order
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
        ora #VDGMODE+CSSBIT
        sta $FF22
        lda #$A5
        sta $2FFF
ready   bra ready
pattern fcb $00,$55,$AA,$FF
        end start
