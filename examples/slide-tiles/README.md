# Slide tiles between squares

This example slides tiles from their start squares to their end squares on a
4×4 board. The display shows each step of the slide. The program draws each
step into the screen that the display does not show, then shows that screen
(a page flip).

A move has a fixed number of steps, N. At step k, each moving tile is k/N of
the way to its end square. A tile that does not move is not drawn again. In
each step, the program erases the trail of each moving tile, then draws each
moving tile at its new place.

The example does not read keys, apply game rules, merge tiles, time the
steps or play sound. The tiles are opaque rectangles. The flip is the method
of the [page flip](../page-flip/README.md) example.

The main build runs on a CoCo 1, a CoCo 2 and a CoCo 3, in CG6. The `gime16`
variant runs on a CoCo 3 with a 6309 and 512 KiB, in the GIME's 320×192
mode with 16 colours.

## Choose a redraw method

The trail erase is the default. It writes the fewest bytes when the
background has a pattern, and the tiles keep their own pictures.

| Method | Bytes in each step, for each moving tile | Notes |
| --- | --- | --- |
| Trail erase | The tile, and a strip as wide as two steps of travel | The default. One routine for each axis of travel. |
| Redraw the line | The board strip of the line (row or column), and each tile in it | Simple. In the GIME mode, one 112×48-byte strip is 5,376 bytes. |
| Full redraw | The whole screen, and each tile | 6,144 bytes in CG6 and 30,720 bytes in the GIME mode. |

Each screen shows every second step. Thus the trail on a screen is the
travel of two steps. A tile can move more than its own size in two steps.
Then the strip also covers some empty board between the two places. This
does no harm.

Select the number of steps:

| Steps | Variant | Notes |
| --- | --- | --- |
| 4 | (none) | The default. A short slide with larger jumps. |
| 8 | `steps8` | Smaller jumps. Each tile is drawn twice as many times. |

The [slide tiles guide](../../guidance/techniques/slide-tiles.md) gives
measured times for each choice on the CoCo 3.

Other ways that this example does not show:

- A fixed speed, not a fixed duration. Then a short move ends earlier, and a
  tile behind another tile can reach it before the end.
- A third screen. Then the program can draw while the display still shows
  the old screen. The trail becomes three steps of travel.
- Transparent tiles, drawn with a mask, as in the
  [masked objects](../masked-objects/README.md) example. They cost more.

## Slide one move

The example is the four `>>> EXAMPLE` parts of [main.asm](main.asm):

1. `move` shows the start of the move on both screens. Then it does steps 1
   to N. After step N, it does step N again on the other screen, so that both
   screens show the end. `records` makes one record for each tile: its kind,
   its start place, its end place and the place where each screen last
   showed it.
2. `step` erases the trail of each moving tile first. Then it draws each
   moving tile in list order. A tile drawn later covers a tile drawn before
   it, so the two tiles of a merge pair overlap. `where` calculates the place
   at step k. The division rounds toward the start.
3. `trail` finds the trail: the part of the old rectangle on this screen
   that the new rectangle does not cover. A tile moves on one axis, so the
   trail is one strip.
4. `paint` paints the empty board into a rectangle. Each row copies a part
   of one board row, `bgrow`, or of one row of gaps, `gutrow`.

The order is important. If the program draws one tile before it erases the
trail of another tile, the erase can remove part of the new tile.

A tile that does not move is safe. The trail of a moving tile is behind it,
and a tile that stays is ahead of it or at its end square.

The `--- CONTEXT` blocks are not part of the practice:

- They set up CG6 at `$0400` with colour set 0, or the GIME's 320×192 mode
  with 16 colours. They set palette registers 0 to 3 in the GIME mode.
- They flip the screens as the [page flip](../page-flip/README.md) does.
- They paint the board and draw the tiles. A tile is a 40-row rectangle with
  an edge of 4 rows and 1 byte. Kind 1 has a red edge, kind 2 a yellow
  edge.
- They play two moves, Left and Down, again and again.

The `gime16` build masks IRQ. The VBORD flag also requests an IRQ, and
BASIC's handler must not read `$FF92`. That build also maps two screen pages
at CPU `$6000-$9FFF`, over BASIC's code. Thus it sets its own stack. It copies
with the 6309 instruction `TFM`. The main build keeps BASIC's interrupts and
stack, and turns off the field-sync IRQ as the page flip does.

The program starts at `$4400` and ends below `$6000`. The `state` label is
data. The check fails if the CPU runs it.

## See and check each build

Open a terminal in the starter folder. Copy one line and paste it to see that
build in XRoar. The moves repeat until you close the window.

```sh
uv run python scripts/coco.py run examples/slide-tiles                       # CG6, 4 steps
uv run python scripts/coco.py run examples/slide-tiles --variant steps8      # CG6, 8 steps
uv run python scripts/coco.py run examples/slide-tiles --variant gime16      # GIME 320x192x16, 6309
```

Add `--target coco2`, `--target coco2b` or `--target coco3` to see the CG6
builds on another machine.

To check all builds on all targets, paste this line:

```sh
uv run python scripts/coco.py check examples/slide-tiles
```

The check stops at each flip, at 24 flips. It compares both screens with
[expected.py](expected.py). The shown screen must hold the picture of this
flip. The other screen must hold the picture of the flip before it. It also
compares XRoar's rendered picture of the shown screen.

The model calculates each place from the slide rule. It draws the tiles that
stay, then the moving tiles in list order, on the empty board. It does not
model the erase. A correct erase leaves no trace of the old places on
either screen.

A program without the trail erase fails the check at flip 2.

The check runs on these targets in [coco.toml](coco.toml), each with NTSC:

- `coco1`, `coco2` and `coco2b`: the standard targets, with a 6809 and
  32 KiB.
- `coco3`: a CoCo 3 with a 6809, 128 KiB and the 1986 GIME.
- `coco3-6309`: a CoCo 3 with a 6309, 512 KiB and the 1986 GIME. The `gime16`
  variant runs only here. The main build also runs here.

On the CoCo 3 in CG6, each colour code selects a palette register that BASIC
loads (Tepolt PDF 46 and 57). The model uses the `xroar-coco3` palette of
`scripts/graphics.py`.

## Sources

- Tandy, *Color Computer Technical Reference Manual*: PDF 13 (`$FF03`), PDF
  14 and 31 (CG6 is SAM V=110 and `$FF22` bits 7..4 `1110`), PDF 15 (SAM
  display offset, F4).
- Motorola, *MC6847* datasheet: PDF 19 Table 3 (the leftmost pixel is in the
  high bits), PDF 21 (colour set 0).
- Motorola, *MC6821* datasheet: PDF 10 (a read of the data register clears
  the flag).
- Tandy, *Color Computer 3 Service Manual*: PDF 11 (`$FF90`, `$FF92`), PDF
  12 (`$FF98`, `$FF99`), PDF 13 (`$FF9D`), PDF 15-16 (MMU), PDF 17
  (palette registers).
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*: PDF
  38-39 and 41-42 Table 4-10 (320 pixels with 16 colours, two pixels in a
  byte), PDF 50 (`$FF92` and IEN).
- *HD63B09EP Technical Reference Guide*: PDF 34 (`TFM` takes 6+3n cycles).
- Burke & Burke, *The 6309 Book*: PDF 225 and 231 (`TFM`).

Only the check establishes these facts:

- The rendered colours of the GIME codes `$00`, `$12`, `$24` and `$16`, as
  in [GIME graphics](../gime-graphics/README.md).
- In the GIME mode, the capture starts at sample 64 of the 640-sample line.
  XRoar centres the 512-sample capture on the line (`update_viewport` in
  `src/vo_render.c` of XRoar 1.13.1). With sample 62, the rendered check
  fails.

An emulator check is not a television or a physical CoCo.
