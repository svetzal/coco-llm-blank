* Original display-address probe. CoCo 3, NTSC, normal-clock 6809.
* FF9D_HIGH is one of $18, $19, $D8, $D9; build with -DFF9D_HIGH=...
* See README.md for source citations, instrumentation, and evidence limits.
        org $3000
start   orcc #$50
        lds #$7F00
        sta $FFD8
* Native display, enabled MMU, executive task, RAM vectors, all RAM.
        lda #$4E
        sta $FF90
        clr $FF91
        sta $FFDF
        clr $FF92
        clr $FF93
* Map physical $0C000-$0DFFF into CPU $6000-$7FFF.
* Stack is unused while this mapping is active.
        lda #6
        sta $FFA3
        ldx #$6000
        ldd #$4141
low0    std ,x++
        cmpx #$6800
        blo low0
        ldd #$4242
low1    std ,x++
        cmpx #$7000
        blo low1
* Map physical $6C000-$6DFFF into the same CPU window, write second.
* On 128 KiB the earlier low-address contents alias and are overwritten.
        lda #$36
        sta $FFA3
        ldx #$6000
        ldd #$4343
high0   std ,x++
        cmpx #$6800
        blo high0
        ldd #$4444
high1   std ,x++
        cmpx #$7000
        blo high1
* Restore executive window, then select 40-column attributed text.
        lda #$3B
        sta $FFA3
        lda #3
        sta $FF98
        lda #5
        sta $FF99
        clr $FF9C
        lda #FF9D_HIGH
        sta $FF9D
        clr $FF9E
        clr $FF9F
ready   bra ready
        end start
