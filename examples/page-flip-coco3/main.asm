* Show only finished frames on a CoCo 3: draw into a hidden buffer, then
* show it with one GIME write (a page flip).
*
* The GIME shows the buffer at physical address $FF9D * 2048 + $FF9E * 8.
* Two buffers, at physical $04000 and $06000, have the same $FF9E (0), so
* one write to $FF9D shows the other buffer. The program draws each scene
* into the buffer that is not shown. After the vertical border (VBORD) flag,
* it writes $FF9D. Then it waits for the next VBORD before it draws into the
* other buffer.
*
* The example is in four parts, each between ">>> EXAMPLE" and
* "<<< END EXAMPLE". The rest is context: it sets up a 256x192 two-colour
* screen and draws five scenes, an outline and a square that moves right.
* A project does not need the context.
*
* Sources:
*   Tandy, Color Computer 3 Service Manual:
*     PDF 11: $FF90 bits (COCO, M/P, IEN, ROM map); $FF92 bit 3 = VBORD.
*     PDF 12: $FF98 (BP, LPR) and $FF99 (LPF, HRES, CRES).
*     PDF 13: $FF9D = Y18..Y11, $FF9E = Y10..Y3; $FF9A, $FF9C.
*     PDF 14: $FF9F bit 7 = HVEN.
*     PDF 15-16: MMU registers $FFA0-$FFAF, write only; $FFA2 maps CPU
*       $4000-$5FFF and $FFA3 maps $6000-$7FFF in task set 0.
*     PDF 17-18: palette values and the HRES/CRES table.
*   Laurence A. Tepolt, Assembly Language Programming for the CoCo3:
*     PDF 50: an $FF92 bit sets only if Init0 ($FF90) enables IRQ; a read
*       of $FF92 clears the request.
*     PDF 29: a 128K CoCo 3 has the same RAM in each group of 128K.

* >>> EXAMPLE 1 of 4: two buffers that differ only in $FF9D.
* Physical $04000 = $08 * 2048 and $06000 = $0C * 2048. The MMU puts
* physical page 2 ($04000) at CPU $4000 and page 3 ($06000) at CPU $6000.
BUFFER_A equ $4000
BUFFER_B equ $6000
* <<< END EXAMPLE

        org $3000
* >>> EXAMPLE 2 of 4: map the buffers and turn on the VBORD flag.
* The MMU registers are write only, so set the two pages that hold the
* buffers. BASIC uses task set 0.
start   lda #2
        sta $FFA2
        inca
        sta $FFA3
* $FF92 bit 3: the VBORD flag. The flag sets only when $FF90 bit 5 (IEN)
* is on, and then the GIME also sends an IRQ to the CPU. Mask IRQ so that
* no interrupt handler reads $FF92 and takes the flag.
        orcc #%00010000
* $FF90 = $6E: native video (COCO 0), MMU on, IEN on, FEN off,
* MC3 and MC2 on, 32K internal ROM.
        lda #$6E
        sta $FF90
        lda #%00001000
        sta $FF92
* <<< END EXAMPLE

* --- CONTEXT: 256x192, one bit for each pixel, black border and pixels 0,
* white pixels 1. $FF9E = 0 for both buffers.
        clr $FF9A
        clr $FF9C
        clr $FF9F
        clr $FFB0
        lda #$3F
        sta $FFB1
        lda #$80
        sta $FF98
        lda #8
        sta $FF99
        clr $FF9E
* --- CONTEXT: draw scene 0 into buffer B first.
        clr scene
        ldu #BUFFER_B
        stu back

next    jsr render

* >>> EXAMPLE 3 of 4: show the finished buffer, then draw into the other.
* Wait for a new VBORD, then write $FF9D: $08 for A, $0C for B.
        jsr waitvb
        lda back
        lsra
        lsra
        lsra
        sta $FF9D
* The check takes a snapshot each time the program reaches this label.
published
* Wait for one more VBORD before the program draws into the old buffer.
        jsr waitvb
        ldu #BUFFER_A
        lda back
        cmpa #BUFFER_B/256
        beq chosen
        ldu #BUFFER_B
chosen  stu back
* <<< END EXAMPLE

* --- CONTEXT: the next of five scenes.
        lda scene
        inca
        cmpa #5
        blo keep
        clra
keep    sta scene
        bra next

* >>> EXAMPLE 4 of 4: wait for a new VBORD.
* Read $FF92 to clear an old request. Then wait until bit 3 is set.
waitvb  lda $FF92
poll    lda $FF92
        bita #%00001000
        beq poll
        rts
* <<< END EXAMPLE

* --- CONTEXT: clear the buffer, draw a one-pixel outline, then an 8x8
* square at pixel (32 + 16 * scene, 80).
render  ldx back
        ldy #6144
        clra
clear   sta ,x+
        leay -1,y
        bne clear
        ldx back
        ldb #32
        lda #$FF
edges   sta ,x
        sta 6112,x
        leax 1,x
        decb
        bne edges
        ldx back
        ldy #190
        leax 32,x
sides   lda #$80
        sta ,x
        lda #1
        sta 31,x
        leax 32,x
        leay -1,y
        bne sides
        ldx back
        leax 2564,x
        ldb scene
        lslb
        abx
        ldb #8
        lda #$FF
object  sta ,x
        leax 32,x
        decb
        bne object
        rts

* --- CONTEXT: program state. This is a data label: the check fails if the
* CPU executes it.
state
scene   rmb 1
back    rmb 2
        end start
