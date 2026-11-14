* Original bounded retained-description renderer. See README.md.
* CPU $3000 code/state; $4000-$427F A; $5000-$527F B;
* stack $7E00-$7EFF. No ROM calls or display setup; explicitly select the slow MPU rate.
        org $3000
start   orcc #$50
        lds #$7F00
        clra
        tfr a,dp
* XRoar 1.12.1 tcc1014.c: $FFD8 clears R1 (16 master ticks/cycle).
        sta $FFD8
        clr $FF91
* Set executive mapping explicitly before enabling native MMU.
        ldx #$FFA0
        lda #$38
map     sta ,x+
        inca
        cmpa #$40
        blo map
        lda #$4E
        sta $FF90
        ldx #state
        clra
reset   sta ,x+
        cmpx #state_end
        blo reset
* Nonzero allocation; zero history must not imply valid pixels.
        ldx #$3FFF
        ldy #$4281
        jsr poison
        ldx #$4FFF
        ldy #$5281
        jsr poison
        include "driver.inc"
finished bra finished
poison  lda #$A5
        sta ,x+
        pshs y
        cmpx ,s++
        blo poison
        rts
* Entry X=current two records, Y=history for selected buffer,
* U=destination. Record is valid, top, bottom-exclusive, foreground,
* background. Callers supply valid=1; history starts invalid.
render  stx next_ptr
        sty old_ptr
        stu dest_ptr
        clr region
region_loop
        ldx next_ptr
        ldy old_ptr
        ifdef BROKEN_HISTORY
        ldy #history_a
        lda region
        beq broken_selected
        leay 5,y
broken_selected
        endc
        ifndef FULL_REDRAW
        ldb #5
compare lda ,x+
        cmpa ,y+
        bne changed
        decb
        bne compare
        bra skip
        endc
changed jsr paint
* Publish description only after all writes finish.
        ldx next_ptr
        ldy old_ptr
        ifdef BROKEN_HISTORY
        ldy #history_a
        lda region
        beq broken_save
        leay 5,y
broken_save
        endc
        ldb #5
save    lda ,x+
        sta ,y+
        decb
        bne save
skip    ldd next_ptr
        addd #5
        std next_ptr
        ldd old_ptr
        addd #5
        std old_ptr
        ldd dest_ptr
        addd #8
        std dest_ptr
        inc region
        lda region
        cmpa #2
        blo region_loop
        rts
* Each region covers four bytes on eight 80-byte rows.
paint   ldu dest_ptr
        ldx next_ptr
        clr row
row_loop
        lda row
        cmpa 1,x
        blo background
        cmpa 2,x
        bhs background
        lda 3,x
        bra pack
background
        lda 4,x
pack    ldb #17
        mul
        tfr b,a
        ldb #4
pixels  sta ,u+
        pshs d
        ldd writes
        addd #1
        std writes
        puls d
        decb
        bne pixels
        leau 76,u
        inc row
        lda row
        cmpa #8
        blo row_loop
        rts
state
history_a rmb 10
history_b rmb 10
writes  rmb 2
next_ptr rmb 2
old_ptr rmb 2
dest_ptr rmb 2
region  rmb 1
row     rmb 1
state_end
        end start
