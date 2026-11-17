* Print a message with the Color BASIC ROM, then return to BASIC.
*
* CHROUT ($A002) holds the address of the routine that sends the character
* in A to the device in DEVNUM ($6F). DEVNUM 0 is the screen. The routine
* keeps A, B and X.
* BASIC's main loop in direct mode starts at $AC73. It prints OK and waits for
* a command. XRoar starts the program with a jump, not a call, so the program
* cannot return with RTS. It jumps to the main loop.
*
* Source: Color Basic Unravelled II (Color BASIC 1.2):
*   PDF 18: DEVNUM. PDF 27: CHROUT. PDF 30-31: the screen output.
*   PDF 46: the main loop at $AC73.
* The bytes at $A002 and $AC73 are the same in bas11.rom (CoCo 1 target).
CHROUT  equ $A002
BASIC   equ $AC73

        org $3000
start   leax message,pcr
next    lda ,x+
        beq done
        jsr [CHROUT]
        bra next
done    jmp BASIC

message fcc "HELLO, WORLD!"
        fcb 13,0
        end start
