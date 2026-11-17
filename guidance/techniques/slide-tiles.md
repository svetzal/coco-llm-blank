# Slide tiles between squares

Read this when board tiles must slide to their new squares, as in a
merging puzzle. It tells how to redraw only what
changes, how many steps to use, and what a slide costs on a CoCo 3.

The method works on the CoCo 1, 2 and 3. The measured times are for a CoCo
3 in the GIME's 320×192 mode with 16 colours, in XRoar. Read
[Plan animation and redraw](animation.md) first. A slide uses its page flip.

## The method

**Our adaptation.** The [slide tiles](../../examples/slide-tiles/README.md)
example does these steps:

1. Give the move a fixed number of steps, N. At step k, each moving tile is
   k/N of the way from its start square to its end square. Round toward the
   start.
2. Keep, for each tile, the place where each screen last showed it.
3. On the screen that is not shown, erase the trail of each moving tile: its
   old rectangle on this screen, less its new rectangle. Paint the empty
   board there.
4. Then draw each moving tile at its new place, in list order.
5. Flip the screens. After step N, draw step N on the other screen too.

Erase all trails before you draw any tile. If you draw one tile before you
erase the trail of another tile, the erase can remove part of the new tile.

A tile that does not move is not drawn again. The trail of a moving tile is
behind it, so it never touches a tile that stays.

**Derived.** With a fixed duration, two tiles in a line keep their order. The
gap between them goes from its start value to its end value in a straight
line. Both values are at least one square, so the tiles do not overlap. Only
the two tiles of a merge pair meet, at the end. The tile drawn later covers
the other. With a fixed speed instead, a short move ends first, and a tile
behind can reach a tile that has stopped.

**Derived.** Each screen shows every second step. Thus a trail on one screen
is the travel of two steps.

**Derived.** In the 16-colour GIME modes, a byte holds two pixels, the
leftmost in the high bits. [Tepolt, PDF 38-39][tepolt-38] A tile that moves by
an even number of pixels thus needs no bit shift. In CG6, a byte holds four
pixels, so a move by four pixels needs no shift.

The example's check compares both screens and the rendered picture at 24
flips on the CoCo 1, 2, 2B and 3, in CG6 with 4 and 8 steps. It also checks
the 320×192 16-colour mode on a CoCo 3 with a 6309. The model draws each step
complete, and the program only erases trails. A program without the trail
erase fails at flip 2.

## Choose the redraw

| Method | Bytes in each step, for each moving tile |
| --- | --- |
| Trail erase (the example) | The tile, and a strip of two steps of travel |
| Redraw the line | The board strip of its row or column, and each tile in it |
| Full redraw | The whole screen, and each tile |

In the 320×192 16-colour mode, a 112-byte by 48-row line strip is 5,376
bytes. A 24-byte by 40-row tile is 960 bytes.

Draw only the picture of a tile, not the empty square around it. The trail
erase then paints the edge of the square. This removed 15% of the draw time
in the measurement below.

## What a slide costs on the CoCo 3

**Published explanation.** A write to `$FFD8` selects the normal CPU rate. A
write to `$FFD9` selects the high rate, at which the CPU runs instructions
twice as fast. Some BASIC routines, such as serial and cassette I/O, do not
work at the high rate. [Tepolt, PDF 62][tepolt-62] and [PDF 67][tepolt-67]

**Published explanation.** `TFM` takes 6+3n cycles for n bytes.
[HD63B09EP Technical Reference Guide, PDF 34][tfm] The 6309 starts in
emulation mode. `LDMD #1` selects native mode. Read the passage before you
use native mode with interrupts. [The 6309 Book, PDF 209][book]

**Measured result.** Tile cost. A program drew 16 tiles of 26 bytes by 44
rows at the squares of a 4×4 board in the 320×192 16-colour mode. A routine
called for each row moved down a row and stepped the MMU window. Each time
is for one tile, or for one strip of 112 bytes by 48 rows:

| Work | 6309 normal rate | 6309 high rate | 6809 normal rate | 6809 high rate |
| --- | --- | --- | --- | --- |
| One tile, `TFM` for each row | 7.20 ms | 3.60 ms | - | - |
| One tile, `LDD`/`STD` | 12.66 ms | 6.33 ms | 12.66 ms | 6.33 ms |
| One strip, `TFM` (6309) or a `STD` loop (6809) | 21.85 ms | 10.93 ms | 51.5 ms | 25.8 ms |

A field is 16.68 ms. So the 6309 at the high rate draws about 4.6 tiles in
each field with `TFM`. The bytes of a tile take 3,432 of about 6,440 cycles.
The rest is the work for each row.

**Measured result.** A slide. The same mode on a 6309 at the high rate. A
move had 7 moving tiles and 1 tile that stays, with 4 steps. The step period
includes the flip:

| Version | Draw of one step | Step period |
| --- | --- | --- |
| 26×44 tile, a general erase loop, emulation mode | 53.9 ms | 84 ms, 5 fields |
| The same, native mode | 49.8 ms | 67 ms, 4 fields |
| Short loops for each axis, native mode | 42.7 ms | 67 ms |
| Short loops, emulation mode | 45.7 ms | 67 ms |
| 24×40 tile picture only, native mode | 37.6 ms | 67 ms |

With the last version, the slide took about 250 ms with 4 steps (15 pictures
each second). With 8 steps, it took about 410 ms (about 20 pictures each
second). The first step draws less, because it has less trail to erase.

**Derived.** The flip waits for VBORD, then for one more VBORD. Thus a step
takes the draw, rounded up to a field, and one field more. A draw below two
fields (33.4 ms) gives a step of three fields. A move with fewer moving tiles
draws faster, so its steps are shorter. The time of a slide depends on the
number of moving tiles.

**Method.** These times are emulated time in XRoar. The program reached a
checkpoint label before and after the work. `coco.py snapshot --audio --frame
N` records the mixer sound from power-on to hit N. The length of the WAV file
is the emulated time at that hit. A control loop of 96,000 cycles (`LEAX
-1,X` and `BNE`, 12,000 times) measured 107.30 ms at the normal rate and
53.67 ms at the high rate. To repeat a result, make the same program and the
same checkpoints, and compare the WAV lengths.

These are emulator results. They are not measured on a physical CoCo 3.

## Faster slides that are not tested

- A third screen. The program can then draw while the display can still
  show the old screen, so the extra field after each flip goes. Each trail
  becomes three steps of travel.
- A shorter wait after the flip. The instant at which the GIME loads `$FF9D`
  is an open question. Read
  [what the sources do not settle](animation.md#what-the-sources-do-not-settle).
- Fewer steps for a move with many moving tiles.

## Sources

- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 38-39 (pixel packing), PDF 62 ("Lo/Hi MPU Speed"), PDF 67 (table of
  dedicated addresses). Resource `tepolt-coco3`.
- Chet Simpson, with additions by Alan DeKok, *HD63B09EP Technical Reference
  Guide*, PDF 34 (instruction timing). Resource `6309-technical-reference`.
- Burke & Burke, *The 6309 Book*, PDF 209 (processor modes and `LDMD`).
  Resource `6309-book`.
- The [slide tiles](../../examples/slide-tiles/README.md) example and its
  check.

[tepolt-38]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=38>
[tepolt-62]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=62>
[tepolt-67]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=67>
[tfm]: <https://colorcomputerarchive.com/repo/Documents/Microprocessors/HD6309/HD63B09EP%20Technical%20Reference%20Guide.pdf#page=34>
[book]: <https://colorcomputerarchive.com/repo/Documents/Books/The%206309%20Book%20%28Burke%20%26%20Burke%29.pdf#page=209>
