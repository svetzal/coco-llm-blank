# Keep the room in a tile map, and draw it from the map

This example keeps the state of a room in a map of tile numbers. Drawing and
movement both read the map. One table gives the picture of each tile number. A
second table gives its movement rule: the program refuses a move onto a wall.

To change the room, the program changes the map. When the actor moves onto
the collectible, the program writes floor to its cell in the map. The next
redraw of that cell shows floor.

The example does not read the keyboard, scroll, animate or time the frames.
It has no victory rule: the exit is only a different picture. It does not
draw a tile at a pixel position inside a byte or with transparent pixels.

The context plays a fixed script of 41 moves. The
[tile-map guide](../../guidance/techniques/tile-maps.md) gives the method and
its sources.

The same program runs on a CoCo 1, two CoCo 2 models and a CoCo 3. The
CoCo 3 shows RG6 in its VDG-compatible mode. [Machines](#machines) tells what is
different.

## Choose how to redraw after a move

Redraw only the changed cells. This is the default. It suits most games: the
work for each move does not increase with the size of the room.

| Method | Variant | Cells drawn after a move | Bytes copied | Shows a map change at |
| --- | --- | --- | --- | --- |
| Changed cells | (none) | 2: the cell that the actor left, then the actor | 16 | The cells that you draw |
| Full | `full` | 49: all 48 cells, then the actor | 392 | Every cell |

- After a refused move, the changed-cells method draws nothing. The full
  method draws all 49 cells again.
- With changed cells, draw each cell whose map entry changes. In this
  example, only the cell under the actor changes, so the cell that the actor
  left is enough. A door that opens away from the actor needs its own
  draw.
- Use the full method when many cells change at a time, or to find a bug in
  a changed-cells redraw.

Both methods must show the same picture after each move. The check uses the
same model for both.

The map uses one byte for each cell. The tile numbers are:

| Number | Tile | Picture | Movement rule |
| --- | --- | --- | --- |
| 0 | Floor | Blank | Permit |
| 1 | Wall | Brick | Refuse |
| 2 | Collectible | Diamond | Permit, then becomes floor |
| 3 | Exit | Box | Permit |
| 4 | Actor | Figure | Not in the map |

Other ways that this example does not show:

- Keep the movement rule in bits of the tile number, not in a table.
- Use wider pictures, such as 16×16 pixels, with two or more bytes for each
  picture row.
- Keep a copy of the screen cells, and draw only the cells that differ from
  the map.

## Keep the room in the map

The example is the five `>>> EXAMPLE` parts of [main.asm](main.asm):

1. At `start`, after the screen setup, copy `initial_map` to `room`. Then
   draw the full room. The room map is in RAM, because a move changes it.

2. At `draw_room`, `draw_cell` and `draw_picture`, draw from the map:
   1. Read the tile number at `room + row × 8 + column`.
   2. Find its picture in the `pictures` table.
   3. Find the screen address of the cell: `$0400 + row × 256 + column`.
      RG6 has 32 bytes in each pixel row, and a cell is 8 pixel rows.
   4. Copy the 8 rows of the picture, 32 bytes apart.

   `draw_actor` draws picture 4 at the actor's cell.

3. At `move`, try a move to the next cell:
   1. Refuse a move past the room edge before you calculate a map address.
      One unsigned test finds both edges, because -1 is `$FF`.
   2. Read the tile number of the new cell. Refuse the move if its entry in
      `passable` is 0.
   3. If the tile is the collectible, write floor to the map.
   4. Keep the old cell in `old_x` and `old_y`. Set `accepted` to 1.

4. At `redraw`, show the move. The plain build draws the cell that the actor
   left, from the map, then the actor. The `full` variant calls `draw_room`.

5. At `pictures`, `passable`, `deltas`, `initial_map` and `room`, keep the
   tables and the map.

The `--- CONTEXT` blocks are not part of the practice:

- They set up RG6 at `$0400` with colour set 0, as in
  [first-screen](../first-screen/README.md). They clear the screen once.
- They include `tiles.asm`, which [prepare.py](prepare.py) converts from
  [tiles.png](tiles.png) before each build.

  The drawing has five cells. From left to right, they are floor, wall,
  collectible, exit and actor. The
  [assets guide](../../guidance/techniques/assets.md#convert-the-pictures-at-each-build)
  gives this method.
- They play the 41 moves in `moves`, with a pause after each move.

The program keeps the interrupts, stack, direct page and CPU clock that BASIC
sets. On each target, Extended BASIC turns on the field-sync interrupt, and
its handler runs once in each field. The program does not wait for field sync
and does not write the PIA. The pause is a counted loop, so the interrupt only
makes the pause a little longer. The `state` label is data. The check fails
if the CPU runs it.

## Machines

The program, the map, the screen bytes and the picture are the same on each
machine. Only the RGB values of the colours are different.

- CoCo 1 and the two CoCo 2 models: the VDG gives each colour a fixed value. With colour
  set 0, a 0 bit is black and a 1 bit is green.
- CoCo 3: the same `$FF22` and SAM writes select RG6. A 0 bit selects palette
  register 8 and a 1 bit selects register 9. BASIC loads these registers at
  reset (Tepolt, *Assembly Language Programming for the CoCo3*, PDF 46 and
  57). The program does not write `$FFB0` to `$FFBF`, so it keeps those
  values.

The CoCo 3 needs no other setup. The screen is at `$0400` on each machine.
The CoCo 3 snapshot is physical memory, so the check reads the screen at
`$10400` there. Tepolt PDF 58 puts BASIC's 32 KiB at physical `$70000`, and
the 128 KiB starts at `$60000`. The offset `$10400` is our arithmetic from
these values.

In XRoar, black and green are (0, 31, 0) and (46, 188, 36) on the CoCo 1 and
on both CoCo 2 models, with the MC6847 and with the MC6847T1.
On the CoCo 3 they are (20, 20, 20) and (71, 145, 5). These values are
measured in XRoar, in [palette-swatches](../palette-swatches/README.md). They
are not the colours of a monitor or a physical CoCo.

## See and check each method

Open a terminal in the starter folder. Copy one line and paste it to see that
method in XRoar. The actor plays the script once and stops. Close the window
to stop XRoar.

```sh
uv run python scripts/coco.py run examples/tile-room                 # changed cells
uv run python scripts/coco.py run examples/tile-room --variant full  # full
```

To see a method on another machine, add `--target coco2`,
`--target coco2b` or `--target coco3`:

```sh
uv run python scripts/coco.py run examples/tile-room --target coco3                 # changed cells
uv run python scripts/coco.py run examples/tile-room --target coco3 --variant full  # full
```

To check both methods on all four targets, paste this line:

```sh
uv run python scripts/coco.py check examples/tile-room --video
```

The `--video` option needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check takes a snapshot at the start and after each of the 41 moves. It
compares all 6,144 screen bytes and XRoar's rendered picture with
[expected.py](expected.py).

The model in `expected.py` walks the room from a text drawing of the map and
the move script. It draws each picture from a text drawing. It does not read
`main.asm`, `tiles.png` or the converted bytes.

The moves include these cases:

- A move past each of the four room edges.
- A move into a wall from each of the four sides.
- A move onto the collectible, away from it, and back onto its cell.
- A move onto the exit, away from it, and back.

The check runs both methods on each target in [coco.toml](coco.toml). Each
target has NTSC and a normal-clock 6809:

| Target | Machine | RAM | Video | Firmware |
| --- | --- | --- | --- | --- |
| `coco1` | CoCo 1 | 32 KiB | MC6847 | Color BASIC 1.1, Extended Color BASIC 1.1 |
| `coco2` | CoCo 2 | 32 KiB | MC6847 | Color BASIC 1.2, Extended Color BASIC 1.1 |
| `coco2b` | CoCo 2 | 32 KiB | MC6847T1 | Color BASIC 1.3, Extended Color BASIC 1.1 |
| `coco3` | CoCo 3 | 128 KiB | GIME 1986 | Super Extended Color BASIC |

The program does not use Extended BASIC. The targets load it because most
machines had it.

The model uses the `xroar` palette for the CoCo 1 and both CoCo 2 targets,
and the `xroar-coco3` palette for the CoCo 3. The check does not prove the
result on a television, a physical CoCo or PAL.

The program draws into the screen that the VDG shows, with no vertical sync.
The check does not measure the time of a redraw.

## Sources

Read these pages before you change the screen setup, the bit order or the
screen address of a cell. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Inman, Inman and Dymax, *Assembly Language Graphics for the TRS-80 Color
  Computer*, PDF 106–107: mode 6R is 256×192 at `$0400`–`$1BFF` and uses
  6 KiB. Each byte gives eight pixels. With colour set 0, a 0 bit shows black
  and a 1 bit shows green.

- Motorola, *MC6847 Video Display Generator* datasheet, PDF 19, Table 3: RG6
  has 256 pixels in each row and uses 6,144 bytes. Bit 7 is the leftmost
  pixel of a byte.

- Tandy, *Color Computer Technical Reference Manual*, PDF 14–15: the `$FF22`
  bits, and the SAM offset and mode bits. PDF 31: RG6 uses SAM V=`110` and
  `$FF22` bits 7 to 4 `1111`.

- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*, PDF 46:
  on a CoCo 3, the same `$FF22` and SAM values select G6R. With colour set 0,
  a 0 bit selects palette register 8 and a 1 bit selects register 9. PDF 57,
  step 44: BASIC loads the palette registers at reset. PDF 58: the CoCo 3
  memory map. BASIC's 32 KiB is at physical `$70000`.

The cell address is our arithmetic from these values. The map, the tables,
the pictures and the moves are our own design.

The
[tile-map guide](../../guidance/techniques/tile-maps.md#sources) gives the
historical sources that we read, such as *PacDude Monster Maze*. This example
does not copy their code.
