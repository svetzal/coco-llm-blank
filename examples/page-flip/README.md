# Show only finished frames on CoCo 1 and CoCo 2

This example uses two screens to show only finished frames. This is a page
flip.

The program draws each frame into the screen that the display does not show.
When the frame is complete, one SAM write shows that screen. Then the program
draws the next frame into the other screen.

If a program draws into the screen that the display shows, the display can
show a frame that is not complete. Correct screen memory does not prove a
correct picture.

The example does not use an interrupt handler. It does not read input, play
sound or keep a constant frame rate. It does not redraw only the parts that
changed. The program does not return to BASIC.

For the CoCo 3 graphics of the GIME, read
[page flip on CoCo 3](../page-flip-coco3/README.md).

## Choose the two screens

The SAM display offset is the screen address divided by 512, in bits F6 to F0.
[Tandy, PDF 15][tandy-15] Put the two screens at addresses that differ in one
offset bit. Then one write to that bit shows the other screen.

The table gives one pair for each screen size, with the first screen at
`$0400`. We derived the pairs from the offset bits and the screen sizes.

| Screen bytes | Modes | Bit | Clear, set | Second screen | Both screens |
| --- | --- | --- | --- | --- | --- |
| 6144 | CG6, RG6 | F4 | `$FFCE`, `$FFCF` | `$2400` | 12,288 bytes |
| 3072 | CG3, RG3 | F3 | `$FFCC`, `$FFCD` | `$1400` | 6,144 bytes |
| 2048 or less | CG2, RG2, CG1, RG1 | F2 | `$FFCA`, `$FFCB` | `$0C00` | 4,096 bytes |

- The second screen must start after the end of the first screen.
- The first screen at `$0400` has F1 set, because `$0400` / 512 = 2. Do not
  use F1 or F0 for a screen at `$0400`. F1 gives `$0000`, and F0 gives a
  screen that overlaps the first.
- The example uses RG6, the first row. The steps are the same in CG6.
- The screen sizes come from the MC6847 datasheet. [MC6847, PDF 19][mc6847-19]

The program must know when the display starts a new field. This example polls
the field-sync (FS) flag in the PIA at `$FF03`, with the PIA interrupt off.

Other ways that this example does not show:

- An IRQ handler for field sync. The handler reads `$FF02` and does the
  flip. The main program then must not read `$FF02`.
- Three screens. The program can start the next frame before the display
  uses the new screen.

## Flip the screens

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm):

1. `SCREEN_A` and `SCREEN_B`: the two screens, `$0400` and `$2400`. They
   differ only in F4. [Tandy, PDF 15][tandy-15]
2. After `start`, set up the FS flag in `$FF03`. [Tandy, PDF 13][tandy-13]
   - Clear bit 0 to turn off the PIA interrupt. Then no interrupt handler
     reads `$FF02` and clears the flag.
   - Clear bit 1. The flag then sets at the falling edge of FS. FS goes low
     at the end of the active display. [MC6847, PDF 22][mc6847-22]
   - Set bit 2 to select the data register at `$FF02`.

   Then set `drawing` to `SCREEN_B`, the screen that is not shown.
3. After `drawn`, show the finished frame and change screens:
   1. Read `$FF02` to clear an old flag. A read of the data register clears
      the flag. [MC6821, PDF 10][mc6821]
   2. Wait until bit 7 of `$FF03` is set.
   3. Write `$FFCF` to show `$2400`, or `$FFCE` to show `$0400`. The
      `published` label follows this write.
   4. Set bit 1 of `$FF03`, clear the flag and wait for the rising edge of
      FS. Then clear bit 1 again.
   5. Change `drawing` to the other screen.

Step 3.4 waits before the program draws into the old screen. The sources that
we read do not give the instant at which the SAM uses a new offset. In the
pinned XRoar, the SAM uses it at the rising edge of FS.

The
[animation guide](../../guidance/techniques/animation.md#what-the-sources-do-not-settle)
records what is not known.

A frame can take more than one field to draw. That does not matter, because
the display does not show the screen that the program draws into.

The `--- CONTEXT` blocks are not part of the practice:

- They set up RG6 at `$0400` with colour set 0, as in
  [first-screen](../first-screen/README.md).
- They draw an 8x8 checker background. The background inverts every 64
  frames.
- They draw two 16x8 rectangles. Rectangle A has green pixels, and
  rectangle B has black pixels. They move one step each frame and reverse at the edges of the screen.
  The layer order changes every 32 frames.

The program keeps the CPU interrupt mask, the stack, the direct page and the
CPU clock that BASIC sets. The `state` label is data. The check fails if the
CPU runs it.

## See and check the page flip

Open a terminal in the starter folder. Paste this line to see the page flip in
XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/page-flip    # RG6 page flip
```

To check the page flip, paste this line:

```sh
uv run python scripts/coco.py check examples/page-flip
```

The `[capture]` table in [coco.toml](coco.toml) turns on the rendered check,
so `check` needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check takes a snapshot at `published` after frames 1 to 4, 32, 33, 64 and
65. It compares these items with [expected.py](expected.py):

- The screen that the display shows holds the new frame, all 6144 bytes.
- The other screen still holds the frame before it.
- XRoar's rendered picture is the new frame, complete.

The model in `expected.py` draws each frame pixel by pixel from the scene
description above. It does not read the assembly.

A negative control in `scripts/coco_spec.py` changes `eora #$20` to `eora #0`.
The program then draws into the screen that the display shows. The memory
check still passes at frame 1. The rendered check fails.

The check uses the CoCo 1 target: NTSC, 32 KiB, the non-T1 MC6847 and Color
BASIC 1.1. It sees one rendered frame for each checkpoint, not every field. It
does not prove the result on a television, a physical CoCo, PAL or the
MC6847T1.

## Sources

Read these pages before you change the screens or the wait. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Tandy, *Color Computer Technical Reference Manual*, PDF 13: in `$FF03`,
  bit 0 enables the FS interrupt. Bit 1 selects the edge (0 is falling). Bit
  2 selects the data register. Bit 7 is the FS flag. [Link][tandy-13]

- The same manual, PDF 15: the SAM display offset, F6 to F0, in 512-byte
  units. F4 is `$FFCE` (clear) and `$FFCF` (set). [Link][tandy-15]

- The same manual, PDF 14 and 31: the `$FF22` bits. RG6 is SAM V=`110` and
  `$FF22` bits 7 to 4 `1111`.
- Motorola, *MC6821 Peripheral Interface Adapter*, PDF 10, Figure 18: a read
  of the data register clears the flag. [Link][mc6821]
- Motorola, *MC6847 Video Display Generator* datasheet, PDF 19, Table 3: the
  size of each mode. In RG6, bit 7 is the leftmost pixel. [Link][mc6847-19]

- The same datasheet, PDF 22: FS goes low at the end of the display window,
  for 32 scan lines. [Link][mc6847-22]

[tandy-13]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[tandy-15]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=15>
[mc6821]: <https://sowerbutts.com/replica1-serial/6821.pdf#page=10>
[mc6847-19]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=19>
[mc6847-22]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>
