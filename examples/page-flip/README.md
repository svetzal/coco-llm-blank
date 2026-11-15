# Show only finished frames

This example uses two screens to show only finished frames. This is a page
flip.

The program draws each frame into the screen that the display does not show.
When the frame is complete, one write shows that screen. Then the program
draws the next frame into the other screen.

If a program draws into the screen that the display shows, the display can
show a frame that is not complete. Correct screen memory does not prove a
correct picture.

The example runs on the CoCo 1, the CoCo 2 (MC6847 or MC6847T1) and the
CoCo 3. It has two builds:

- The main build flips RG6 screens with the SAM and waits for the field-sync
  flag of the PIA. It runs on the CoCo 1, the CoCo 2 and the CoCo 3.
- The `coco3` variant flips screens in the native graphics of the CoCo 3 GIME
  with `$FF9D`. It waits for the vertical border (VBORD) flag of the GIME. It
  runs only on the CoCo 3.

The example does not use an interrupt handler. It does not read input, play
sound or keep a constant frame rate. It does not redraw only the parts that
changed. The program does not return to BASIC.

## Choose the method

| Build | Machines | Graphics modes | Write to show a screen | Wait for |
| --- | --- | --- | --- | --- |
| Main | CoCo 1, CoCo 2 (MC6847 and MC6847T1), CoCo 3 (128 and 512 KiB) | The VDG modes, such as RG6 and CG6 | One SAM offset bit, here F4 | FS flag, `$FF03` bit 7 |
| `coco3` variant | CoCo 3 (128 and 512 KiB) | The GIME native modes | `$FF9D` (and `$FF9E`) | VBORD flag, `$FF92` bit 3 |

- Use the main build in a program that uses the VDG modes. The same code runs
  on the three machines.
- Use the `coco3` variant in a program that uses the GIME native modes. In
  those modes the SAM offset has no effect.
  [Tepolt, PDF 39][tepolt-39]
- Both builds use the same two screens at CPU `$0400` and `$2400` and draw the
  same bytes. Only the mode, the flip and the wait are different.

### Choose the two screens for the SAM

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

On a CoCo 3 the GIME does the work of the SAM and the VDG in these modes.
[Tepolt, PDF 43][tepolt-43] The SAM bits F6 to F0 give the physical address
bits Y15 to Y9. Bits 7 to 5 of `$FF9D` give Y18 to Y16.
[Tepolt, PDF 44][tepolt-44] [Tandy CoCo 3, PDF 13][coco3-13] BASIC loads
`$FF9D` with `$E0`. [Tepolt, PDF 56][tepolt-56] So the same SAM writes flip
the same two screens.

Do not use RG1, RG2 or RG3 on a CoCo 3 before you read the open question in
the [graphics guide](../../guidance/techniques/graphics.md). XRoar shows them
differently on its CoCo 3. RG6, the mode of this example, is the same.

### Choose the two screens for the GIME

The GIME shows the screen at the physical address `$FF9D` x 2048 + `$FF9E` x
8. [Tandy CoCo 3, PDF 13][coco3-13] Give the two screens the same `$FF9E`.
Then one write to `$FF9D` shows the other screen.

| Screen | CPU address | Physical address | `$FF9D` | `$FF9E` |
| --- | --- | --- | --- | --- |
| A | `$0400-$1BFF` | `$70400-$71BFF` | `$E0` | `$80` |
| B | `$2400-$3BFF` | `$72400-$73BFF` | `$E4` | `$80` |

- The display reads physical memory, not CPU addresses.
  [Tepolt, PDF 31][tepolt-31] BASIC maps CPU `$0000-$FFFF` to the physical
  pages `$38` to `$3F`. [Tepolt, PDF 56][tepolt-56] So CPU `$0400` is physical
  `$70400`.
- A 256x192 two-colour screen uses 6144 bytes. A screen with more colours or
  more pixels needs more memory. [Tandy CoCo 3, PDF 18][coco3-18]
- A 128 KiB CoCo 3 does not use the address bits Y18 and Y17. Each group of
  128 KiB holds the same RAM. [Tepolt, PDF 29][tepolt-29] So `$E0` and `$E4`
  show the same screens at 128 and 512 KiB. A 128 KiB machine has the RAM of
  physical `$70400` at `$10400` too.
- A screen outside the BASIC pages needs the MMU to write it, and at 128 KiB
  it shares RAM with another group. This example does not do that.

Other ways that this example does not show:

- An IRQ handler for the FS flag or for VBORD. The handler reads `$FF02` or
  `$FF92` and does the flip. The main program then must not read that
  register.
- Two GIME screens that differ in `$FF9E` too. Then the program writes two
  registers. The sources that we read do not say if the GIME uses both writes
  in the same field.
- Three screens. The program can start the next frame before the display
  uses the new screen.

## Flip the screens

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm). The
`COCO3` define selects the variant code in parts 1 to 3.

1. `SCREEN_A` and `SCREEN_B`: the two screens, `$0400` and `$2400`. They
   differ only in F4. [Tandy, PDF 15][tandy-15] With `COCO3`, `VIEW_A`,
   `VIEW_B` and `VIEW_LO` are the `$FF9D` and `$FF9E` values of the two
   screens.
2. After the mode setup, set up the flag:
   - Main build: in `$FF03`, clear bit 0 to turn off the field-sync
     interrupt. Clear bit 1, so that the flag sets at the falling edge of FS.
     Set bit 2 to select the data register at `$FF02`.
     [Tandy, PDF 13][tandy-13] FS goes low at the end of the active display.
     [MC6847, PDF 22][mc6847-22] Keep bits 7 to 3.
   - `COCO3`: mask IRQ in the CPU. Write `$6E` to `$FF90`: BASIC's `$CE`
     without the CoCo modes and with the GIME IRQ on.
     [Tandy CoCo 3, PDF 11][coco3-11] [Tepolt, PDF 57][tepolt-57] Then
     write `$08` to `$FF92`. VBORD is then the only GIME IRQ source.

   Then set `drawing` to `SCREEN_B`, the screen that is not shown.
3. After `drawn`, show the finished frame and change screens:
   1. Clear an old flag. The main build reads `$FF02`. A read of the data
      register clears the flag. [MC6821, PDF 10][mc6821] `COCO3` reads
      `$FF92`. [Tepolt, PDF 50][tepolt-50]
   2. Wait for the flag: bit 7 of `$FF03`, or bit 3 of `$FF92`.
   3. Show the new screen. The main build writes `$FFCF` to show `$2400`, or
      `$FFCE` to show `$0400`. `COCO3` writes `$E4` or `$E0` to `$FF9D`. The
      `published` label follows this write.
   4. Wait for the next field. The main build sets bit 1 of `$FF03`, clears
      the flag and waits for the rising edge of FS. Then it clears bit 1
      again. `COCO3` waits for one more VBORD.
   5. Change `drawing` to the other screen.

The main build turns off the field-sync interrupt because BASIC turns it on.
On every target, the program starts with `$FF03` bit 0 set and the CPU IRQ
mask clear. `$FF03` holds `$35` at entry, measured in the pinned XRoar.
The [toolchain guide](../../guidance/starter/toolchain.md#target-tables)
records the measurement.
BASIC's IRQ handler then runs at each falling edge of FS and reads `$FF02`.
That read clears the flag. [MC6821, PDF 10][mc6821]

We read this code in the Extended BASIC 1.1 ROM of the CoCo 1 and 2. The cold
start sets bit 0 at `$809E`, and the handler at `$894C` reads `$FF02`.

If the handler reads `$FF02` before the wait loop reads `$FF03`, the loop does
not see that edge. It waits for the next field. The picture stays correct,
but the program loses a field. The check cannot see this. It passes with the
interrupt left on (measured on `coco2b`). With bit 0 clear, the flag still
sets, and only the wait loop reads `$FF02`.

The `$FF92` flag sets only when `$FF90` bit 5 sends the GIME IRQ to the CPU.
[Tepolt, PDF 50][tepolt-50] The variant masks IRQ, so no interrupt handler
reads `$FF92` and takes the flag.

Step 3.4 waits before the program draws into the old screen. The sources that
we read do not give the instant at which the SAM or the GIME uses a new
offset. In the pinned XRoar, the SAM uses it at the rising edge of FS.

The
[animation guide](../../guidance/techniques/animation.md#what-the-sources-do-not-settle)
records what is not known.

A frame can take more than one field to draw. That does not matter, because
the display does not show the screen that the program draws into.

The `--- CONTEXT` blocks are not part of the practice:

- The main build sets up RG6 at `$0400` with colour set 0, as in
  [first-screen](../first-screen/README.md).
- `COCO3` sets up 256x192 with two colours: `$FF98` = `$80` and `$FF99` =
  `$08`. [Tandy CoCo 3, PDF 18][coco3-18] It writes `VIEW_A` and `VIEW_LO` to
  `$FF9D` and `$FF9E`. It keeps the palette, the border and the horizontal
  offset that BASIC sets. [Tepolt, PDF 56 and 57][tepolt-56]
- They draw an 8x8 checker background. The background inverts every 64
  frames.
- They draw two 16x8 rectangles. Rectangle A has pixels 1, and rectangle B
  has pixels 0. They move one step each frame and reverse at the edges of
  the screen. The layer order changes every 32 frames.
- The code starts at `$3C00`, after `SCREEN_B`. On a CoCo 3, BASIC's reset
  runs its own code at `$4000-$436C`. [Tepolt, PDF 56][tepolt-56]

The two builds show different colours:

| Build | Machine | Pixel 0 | Pixel 1 | Palette registers |
| --- | --- | --- | --- | --- |
| Main | CoCo 1, CoCo 2 | Black | Green | None: fixed VDG colours |
| Main | CoCo 3 | Black | Green | 8 and 9 [Tepolt, PDF 46][tepolt-46] |
| `coco3` | CoCo 3 | Green | Yellow | 0 and 1 [Tepolt, PDF 39][tepolt-39] |

BASIC loads the palette registers. [Tepolt, PDF 57][tepolt-57] The program
does not change them.

The main build keeps the CPU interrupt mask, the stack, the direct page and
the CPU clock that BASIC sets. It changes only the field-sync interrupt bit. The variant keeps the stack, the direct page
and the CPU clock. The `state` label is data. The check fails if the CPU runs
it.

## See and check the page flip

Open a terminal in the starter folder. Paste one of these lines to see the
page flip in XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/page-flip                     # SAM flip, CoCo 1
uv run python scripts/coco.py run examples/page-flip --target coco2      # SAM flip, CoCo 2
uv run python scripts/coco.py run examples/page-flip --target coco2b     # SAM flip, CoCo 2 (MC6847T1)
uv run python scripts/coco.py run examples/page-flip --target coco3      # SAM flip, CoCo 3
uv run python scripts/coco.py run examples/page-flip --variant coco3     # GIME flip, CoCo 3
```

To check both builds on every machine, paste this line:

```sh
uv run python scripts/coco.py check examples/page-flip
```

The `[capture]` table in [coco.toml](coco.toml) turns on the rendered check,
so `check` needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check runs the main build on the targets `coco1`, `coco2`, `coco2b`,
`coco3` and `coco3-512`. It runs the `coco3` variant on `coco3` and `coco3-512`. It takes
a snapshot at `published` after frames 1 to 4, 32, 33, 64 and 65. It compares
these items with [expected.py](expected.py):

- The screen that the display shows holds the new frame, all 6144 bytes.
- The other screen still holds the frame before it.
- XRoar's rendered picture is the new frame, complete.

The snapshot holds physical RAM. So `expected.py` adds an offset to the two
CPU addresses for each target:

| Target | Screen A | Screen B |
| --- | --- | --- |
| `coco1`, `coco2`, `coco2b` | `$0400` | `$2400` |
| `coco3` (128 KiB) | `$10400` | `$12400` |
| `coco3-512` | `$70400` | `$72400` |

The model in `expected.py` draws each frame pixel by pixel from the scene
description above. It does not read the assembly. Its RGB values are from
captures of the pinned XRoar, in `scripts/graphics.py`. They are not from a
source or a monitor.

Two negative controls in `scripts/coco_spec.py` make a wrong program that the
memory check accepts. The rendered check fails for each:

- Change `eora #$20` to `eora #0`. The program then draws into the screen
  that the display shows.
- Add 1 to the `$FF9D` value of the variant. The GIME then shows memory 2 KiB
  after the screen.

The check uses NTSC machines with the 6809 and Extended Color BASIC. They are
a CoCo 1, a CoCo 2 with the MC6847, a CoCo 2 with the MC6847T1 and a CoCo 3
with the GIME 1986. The example does not need Extended BASIC. The targets
load it because most machines have it. The check sees one rendered frame for
each checkpoint, not every field. It does not prove the result on a television, a
monitor, a physical CoCo, PAL, the GIME 1987 or the 6309.

On the CoCo 3, the main build uses the field-sync flag of the PIA. The PIA
interrupts stay on the CoCo 3. [Tepolt, PDF 49][tepolt-49] VSYNC is still a
PIA interrupt source. [Tandy CoCo 3, PDF 37][coco3-37] The sources that we
read do not give the timing of FS on the CoCo 3. The check shows that the
flag works in XRoar (measured).

In the XRoar source, FS falls later on the CoCo 3 than on the VDG and stays
low for a shorter time. The
[animation guide](../../guidance/techniques/animation.md#what-the-sources-do-not-settle)
gives the numbers as an open question.

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
- Tandy, *Color Computer 3 Service Manual*, PDF 11: the `$FF90` bits and the
  `$FF92` bits. Bit 3 of `$FF92` is VBORD. [Link][coco3-11]
- The same manual, PDF 13: `$FF9D` holds address bits Y18 to Y11, and
  `$FF9E` holds Y10 to Y3. In the CoCo modes, SAM F6 to F0 give Y15 to Y9.
  [Link][coco3-13]
- The same manual, PDF 18: the table of resolutions. 256 pixels with two
  colours is HRES `010` and CRES `00`. [Link][coco3-18]
- The same manual, PDF 37: on the CoCo 3, VSYNC is still an interrupt source
  of the PIA. [Link][coco3-37]
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 29: a 128 KiB CoCo 3 has the same RAM in each group of pages.
  [Link][tepolt-29]
- The same book, PDF 31 and 39: the GIME reads physical memory. Native
  graphics need `$FF98` bit 7 set and `$FF90` bit 7 clear. In a two-colour
  mode, bit 7 is the leftmost pixel, and each bit selects palette register 0
  or 1. [Link][tepolt-39]
- The same book, PDF 43 and 44: in the CoCo modes, the GIME does the work of
  the SAM and the VDG. Figure 5-1 gives the physical address from `$FF9D`,
  the SAM offset and `$FF9E`. [Link][tepolt-44]
- The same book, PDF 46: in RG modes, a pixel selects palette register 8 or 9
  (colour set 0). [Link][tepolt-46]
- The same book, PDF 49 and 50: the PIA interrupts stay. The `$FF92` flag
  needs `$FF90` bit 5. A read of `$FF92` clears the request.
  [Link][tepolt-50]
- The same book, PDF 56 and 57: BASIC's reset. It maps the physical pages
  `$38` to `$3F`, runs code at `$4000`, loads `$FF9D` with `$E0`, writes
  `$CE` to `$FF90` and loads the palette registers. [Link][tepolt-56]

[tandy-13]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[tandy-15]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=15>
[mc6821]: <https://sowerbutts.com/replica1-serial/6821.pdf#page=10>
[mc6847-19]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=19>
[mc6847-22]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>
[coco3-11]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=11>
[coco3-13]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=13>
[coco3-18]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=18>
[coco3-37]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=37>
[tepolt-29]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=29>
[tepolt-31]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=31>
[tepolt-39]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=39>
[tepolt-43]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=43>
[tepolt-44]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=44>
[tepolt-46]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=46>
[tepolt-49]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=49>
[tepolt-50]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=50>
[tepolt-56]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=56>
[tepolt-57]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=57>
