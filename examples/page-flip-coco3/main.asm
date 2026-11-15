* Original native CoCo 3 page flip; NTSC, 128/512 KiB, 6809, GIME 1986.
* A white outline and an 8x8 square at five positions on a black
* 256x192 two-colour bitmap. Each scene is drawn into the buffer that is
* not shown; after the next VBORD one write to $FF9D shows it.
* CPU $4100-$58FF is buffer A (physical $04100, MMU page 2) and
* $6100-$78FF is buffer B (physical $06100, page 3). Guards $40FF/$5900/
* $60FF/$7900/$7DFF/$7F00; code/state $3000-$3FFF; stack $7E00-$7EFF.
* IRQ/FIRQ masked; no ROM calls; no return to BASIC.
        org $3000
start   orcc #$50
        clra
        tfr a,dp
* Normal low CPU rate, task 0, executive map $38-$3F, then pages 2/3.
        sta $FFD8
        clr $FF91
        ldx #$FFA0
        lda #$38
map     sta ,x+
        inca
        cmpa #$40
        blo map
        lda #2
        sta $FFA2
        lda #3
        sta $FFA3
* Native video and MMU; GIME IRQ source VBORD only, no GIME FIRQ.
        lda #$6E
        sta $FF90
        lds #$7F00
        clr $FF93
        lda #8
        sta $FF92
* Border and palette 0 black, palette 1 white; 256x192, one bit per pixel.
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
* Both bases have low offset byte $20; only $FF9D changes at a flip.
        lda #$20
        sta $FF9E
        lda #$A5
        sta $40FF
        sta $5900
        sta $60FF
        sta $7900
        sta $7DFF
        sta $7F00
        clr scene
        ldu #$4100
        stu back
next    jsr render
* The hidden scene is complete. Show it after the next VBORD.
        jsr waitvb
        jsr publish
published
* Keep drawing out of the shown buffer until the next VBORD; XRoar loads
* the new base before it.
        jsr waitvb
        lda scene
        inca
        cmpa #5
        blo keep
        clra
keep    sta scene
        ldu #$6100
        lda back
        cmpa #$41
        beq chosen
        ldu #$4100
chosen  stu back
        bra next

* Read $FF92 to discard an old VBORD, then wait for a new one.
waitvb  lda $FF92
poll    lda $FF92
        bita #8
        beq poll
        rts

* Display base = $FF9D * 2048 + $FF9E * 8.
publish lda back
        lsra
        lsra
        lsra
        sta $FF9D
        rts

* Full clear, rectangular outline, then 8x8 object at (32+16*scene,80).
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
* The following data address is never an instruction checkpoint.
state
scene   fcb 0
back    fdb 0
state_end
        end start
