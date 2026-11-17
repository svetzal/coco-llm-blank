* Set up a CoCo 3 GIME graphics screen at a chosen physical address.
*
* The example is in three parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it draws a test card, a border of
* the last colour around one vertical bar of each colour, and holds it for
* the check. A project does not need the context.
*
* Sources:
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90 bits. PDF 12: $FF98 and $FF99 bits, lines per field.
*     PDF 13: $FF9D/$FF9E hold physical address bits 18..3.
*     PDF 15-16: MMU $FFA0-$FFA7, data bits 5..0 = address bits 18..13.
*     PDF 17: palette $FFB0-$FFBF, six bits each.
*     PDF 18: HRES and CRES of ten graphics modes.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3 (1987):
*     PDF 29: on 128 KiB, address bits 18 and 17 are not used.
*     PDF 32: $FF99 bits 6..5: 192, 200 or 225 rows.
*     PDF 38-39: byte formats: the leftmost pixel is in the high bits; a
*       pixel's value selects a palette register; HRES0 set gives the full
*       screen width.
*     PDF 41-42 Table 4-10: HRES and CRES of every graphics mode.
*   John Kowalski, Sock's GIME register reference,
*     http://users.axess.com/twilight/sock/gime.html (Wayback Machine
*     20211201002932): the sixteen commonly used graphics modes.
*
* >>> EXAMPLE 1 of 3: the values for each mode, and the screen address.
* Select the mode with one assembler define. coco.toml has a variant for
* each. $FF99 = LPF (bits 6..5), HRES (bits 4..2), CRES (bits 1..0).
*   Define   Pixels   Colours  HRES  CRES  Bytes/row  Width
*   (none)   320       16      111   10    160        full
*   G256X16  256       16      110   10    128        short
*   G160X16  160       16      101   10     80        full
*   G128X16  128       16      100   10     64        short
*   G640X4   640        4      111   01    160        full
*   G512X4   512        4      110   01    128        short
*   G320X4   320        4      101   01     80        full
*   G256X4   256        4      100   01     64        short
*   G160X4   160        4      011   01     40        full
*   G128X4   128        4      010   01     32        short
*   G640X2   640        2      101   00     80        full
*   G512X2   512        2      100   00     64        short
*   G320X2   320        2      011   00     40        full
*   G256X2   256        2      010   00     32        short
*   G160X2   160        2      001   00     20        full
*   G128X2   128        2      000   00     16        short
* Tepolt's Table 4-10 adds four low-resolution modes:
*   G80X16    80       16      011   10     40        full
*   G64X16    64       16      010   10     32        short
*   G80X4     80        4      001   01     20        full
*   G64X4     64        4      000   01     16        short
* HRES 110 or 111 with CRES 00 uses two bytes for each pixel (Tepolt's
* format X). The example does not draw it. CRES 11 blanks the screen.
* L200 or L225 selects 200 or 225 rows (LPF 01 or 11); the default is 192.
        ifdef G256X16
WIDTH   equ 256
BPP     equ 4
HRES    equ %110
        endc
        ifdef G160X16
WIDTH   equ 160
BPP     equ 4
HRES    equ %101
        endc
        ifdef G128X16
WIDTH   equ 128
BPP     equ 4
HRES    equ %100
        endc
        ifdef G640X4
WIDTH   equ 640
BPP     equ 2
HRES    equ %111
        endc
        ifdef G512X4
WIDTH   equ 512
BPP     equ 2
HRES    equ %110
        endc
        ifdef G320X4
WIDTH   equ 320
BPP     equ 2
HRES    equ %101
        endc
        ifdef G256X4
WIDTH   equ 256
BPP     equ 2
HRES    equ %100
        endc
        ifdef G160X4
WIDTH   equ 160
BPP     equ 2
HRES    equ %011
        endc
        ifdef G128X4
WIDTH   equ 128
BPP     equ 2
HRES    equ %010
        endc
        ifdef G640X2
WIDTH   equ 640
BPP     equ 1
HRES    equ %101
        endc
        ifdef G512X2
WIDTH   equ 512
BPP     equ 1
HRES    equ %100
        endc
        ifdef G320X2
WIDTH   equ 320
BPP     equ 1
HRES    equ %011
        endc
        ifdef G256X2
WIDTH   equ 256
BPP     equ 1
HRES    equ %010
        endc
        ifdef G160X2
WIDTH   equ 160
BPP     equ 1
HRES    equ %001
        endc
        ifdef G128X2
WIDTH   equ 128
BPP     equ 1
HRES    equ %000
        endc
        ifdef G80X16
WIDTH   equ 80
BPP     equ 4
HRES    equ %011
        endc
        ifdef G64X16
WIDTH   equ 64
BPP     equ 4
HRES    equ %010
        endc
        ifdef G80X4
WIDTH   equ 80
BPP     equ 2
HRES    equ %001
        endc
        ifdef G64X4
WIDTH   equ 64
BPP     equ 2
HRES    equ %000
        endc
        ifndef WIDTH
WIDTH   equ 320
BPP     equ 4
HRES    equ %111
        endc
        ifdef L200
ROWS    equ 200
LPF     equ %01
        endc
        ifdef L225
ROWS    equ 225
LPF     equ %11
        endc
        ifndef ROWS
ROWS    equ 192
LPF     equ %00
        endc
COLOURS equ 1<<BPP
CRES    equ BPP/2                   1 bit: 00, 2 bits: 01, 4 bits: 10
RES     equ (LPF*32)+(HRES*4)+CRES
BYTES   equ WIDTH*BPP/8             bytes in one row of pixels
* The physical screen address. It must be a multiple of 8. An address below
* $20000 is the same RAM on 128 KiB and 512 KiB. The largest screen,
* 160 bytes x 225 rows, is 36000 bytes: five 8 KiB pages from $00000.
SCREEN  equ $00000
PAGE    equ SCREEN/$2000            MMU data: address bits 18..13
BASEHI  equ (SCREEN/$800)&$FF       $FF9D: address bits 18..11
BASELO  equ (SCREEN/8)&$FF          $FF9E: address bits 10..3
* The CPU window that shows one page: CPU $4000-$5FFF is MMU entry $FFA2.
WINDOW  equ $4000
* <<< END EXAMPLE

        org $3000
* >>> EXAMPLE 2 of 3: write the screen through the CPU window.
* "put" stores the byte in A at the next screen address. At the end of the
* window it maps the next 8 KiB page. Call "first" before the first byte.
first   lda #PAGE
        sta page
        sta $FFA2
        ldx #WINDOW+(SCREEN&$1FFF)
        rts
put     sta ,x+
        cmpx #WINDOW+$2000
        blo put1
        inc page
        lda page
        sta $FFA2
        ldx #WINDOW
put1    rts
* <<< END EXAMPLE

* --- CONTEXT: a test card. Pixels on the outer rows and columns use the last
* colour. Inside, the picture is one vertical bar of each colour, from colour
* 0 at the left. Every 16 rows, each bar takes the next colour, so a wrong
* number of rows moves a visible line. Pixels go into each byte from the high
* bits.
start   bsr first
        clr row
nextrow ldd #0
        std column
        clr bar
        clr bits
        clr acc
nextbar ldd #WIDTH/COLOURS
        std left
pixel   ldb row
        beq edge
        cmpb #ROWS-1
        beq edge
        ldd column
        beq edge
        cmpd #WIDTH-1
        beq edge
        ldb row                     every 16 rows, each bar takes the next colour
        lsrb
        lsrb
        lsrb
        lsrb
        addb bar
        andb #COLOURS-1
        tfr b,a
        bra colour
edge    lda #COLOURS-1
colour  sta value
        ldb acc
        lda #BPP
shift   lslb
        deca
        bne shift
        orb value
        stb acc
        lda bits
        adda #BPP
        sta bits
        cmpa #8
        blo moved
        lda acc
        bsr put
        clr bits
        clr acc
moved   ldd column
        addd #1
        std column
        ldd left
        subd #1
        std left
        bne pixel
        inc bar
        lda bar
        cmpa #COLOURS
        blo nextbar
        inc row
        lda row
        cmpa #ROWS
        lblo nextrow

* >>> EXAMPLE 3 of 3: set the palette and show the screen.
* Palette register n holds the colour of pixel value n. Write all 16: a
* 2- or 4-colour mode uses only the first 2 or 4.
        ldx #palette
        ldu #$FFB0
pal     lda ,x+
        sta ,u+
        cmpu #$FFC0
        blo pal
* $FF9A: the border colour, a colour code, not a palette register.
        clr $FF9A
* $FF90: CoCo 3 modes (bit 7 clear), MMU on, no GIME interrupt outputs,
* constant RAM at $FExx, standard SCS, 32 KiB internal ROM.
        lda #%01001110
        sta $FF90
* $FF98: BP=1 graphics, LPR=000 one line for each row of pixels.
        lda #%10000000
        sta $FF98
        lda #RES
        sta $FF99
* $FF9C: no vertical scroll.
        clr $FF9C
* $FF9D and $FF9E: the physical display address.
        lda #BASEHI
        sta $FF9D
        lda #BASELO
        sta $FF9E
* $FF9F: normal buffer width (HE=0) and no horizontal offset.
        clr $FF9F
* <<< END EXAMPLE

* --- CONTEXT: hold the screen. The check takes its snapshot at this label.
* A project replaces this loop with its own main loop.
ready   bra ready

* --- CONTEXT: the colour codes that the test card uses, and its counters.
* Each code is a six-bit colour (Service Manual PDF 17). These sixteen look
* different from each other on the check's composite picture.
palette fcb $00,$30,$12,$24,$0B,$16,$1C,$34
        fcb $07,$21,$2D,$05,$19,$3C,$0E,$26
page    fcb 0
row     fcb 0
column  fdb 0
left    fdb 0
bar     fcb 0
bits    fcb 0
acc     fcb 0
value   fcb 0
        end start
