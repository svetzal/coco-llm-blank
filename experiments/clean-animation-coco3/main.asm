* Original bounded scene. See validation note for register sources.
        org $3000
start   orcc #$50
        clra
        tfr a,dp
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
        lda #$6E
        sta $FF90
        lds #$7F00
        clr $FF93
        lda #8
        sta $FF92
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
        jsr render
        lda #8
        sta front
        sta $FF9D
initial_ready
        jsr waitvb
        jsr waitvb
next    inc scene
        ldu #$6100
        lda front
        cmpa #8
        beq chosen
        ldu #$4100
chosen  stu back
        ifdef UNSAFE
* Deliberately publish BEFORE the long redraw and hold for two fields.
        jsr publish
        jsr waitvb
        jsr waitvb
        endc
        jsr render
        ifndef UNSAFE
        jsr waitvb
        jsr publish
        endc
published
        lda scene
        cmpa #1
        beq pub1
        cmpa #2
        beq pub2
        cmpa #3
        beq pub3
pub4    bra held
pub3    bra held
pub2    bra held
pub1    bra held
held    jsr waitvb
        jsr waitvb
        lda scene
        cmpa #4
        blo next
        lda #$5A
        sta complete
finished bra finished
unreachable bra unreachable

waitvb  lda $FF92
poll    lda $FF92
        bita #8
        beq poll
        rts

publish lda back
        lsra
        lsra
        lsra
        ifdef WRONG_BASE
* Off by one 2 KiB high-register unit, while both RAM scenes stay correct.
        inca
        endc
        sta $FF9D
* Track intended front independently of the deliberately wrong write.
        lda back
        lsra
        lsra
        lsra
        sta front
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
scene   fcb 0
front   fcb 0
back    fdb 0
complete fcb 0
code_end
        end start
