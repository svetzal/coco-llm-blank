# A small room with persistent map state

This original demo implements the fixed-room adaptation in
[Build a room from tiles](../../guidance/techniques/tile-maps.md).
It is an adaptation of that guide's design, not a historical reproduction or
a PacDude port. All code, map data, and byte-aligned artwork here are original.

The actor follows a finite script through an asymmetric room. Walls block
movement. Collecting the diamond changes its map entry to floor.

Walking away and returning does not restore the diamond. The exit is a
distinct passable picture. It has no victory rule. There is no keyboard system.

## Run and check

Run these commands from the repository root, with the existing native tools
and verified firmware:

```sh
uv run python scripts/coco.py check examples/tile-room
uv run python scripts/coco.py run examples/tile-room --target coco1
```

`check` covers both targets declared in [coco.toml](coco.toml) and keeps a
result file for each target. Add `--target coco2` to check one target.
Frame N of the check shows the room after N - 1 moves.

At each frame, `check` compares screen memory and also XRoar's rendered picture, so it uses the
instrumented XRoar.

`check` runs headlessly. `run` opens XRoar, moves through the script once,
and holds the final picture. Close XRoar to stop it.

There is no return to BASIC. This is direct DECB auto-run, not disk-loading
evidence. `--help` and invalid arguments do not build or launch anything.

A check removes the previous success record of the target before it builds.
The independent model and its specifications are [expected.py](expected.py)
and [tile_room_spec.py](tile_room_spec.py):

```sh
COVERAGE_FILE=build/tile-room/.coverage \
  uv run pytest examples/tile-room \
  --basetemp=build/tile-room/pytest --cov=examples/tile-room --cov-report=term-missing
```

Generated binaries, symbols, snapshots, logs, and success records stay under
ignored `build/tile-room/`. No firmware or downloaded source is distributed.

## Target and layout

The task specifies CoCo 1 and CoCo 2, NTSC, 32 KiB, a normal-clock 6809,
and a non-T1 MC6847. Both checks use XRoar's `cocous` architecture with explicit
`-vdg-type 6847`, `-machine-cpu 6809`, `-tv-type ntsc`, and `-ram 32`.
`scripts/coco.py` passes `-no-c` to exclude user configuration.

CoCo 1 uses verified `bas11.rom`. CoCo 2 uses verified `bas12.rom`. Neither
target loads Extended BASIC. These are defined emulator configurations, not
evidence for every board revision.

The display is RG6, 256×192, one bit per pixel, with 32 bytes per row and
6,144 bytes total. CSS is zero (black/green).

The 8×6 room occupies the upper left 64×48 pixels. The program clears the rest
of the screen. This deliberately small room keeps the map, drawing, and
movement rules easy to inspect.

| Allocation | Address interval |
| --- | --- |
| Framebuffer | `$0400–$1BFF` |
| Framebuffer guards | `$03FF`, `$1C00` |
| Code, art, script and state | `$3000` to `program_end - 1` |
| Map | `room` through `room + 47`, with adjacent guards |
| Stack reservation | `$7E00–$7EFF`, initial S=`$7F00` |

The build rejects incorrect placement or overlap with the stack reservation.
The program masks IRQ/FIRQ and initializes its state even with nonzero RAM.
PIA setup selects the data register and preserves the low three shared bits.

SAM strobes select base `$0400`, mode `110`, page zero, and normal clock.
The program calls no ROM routines after entry.

## Separate the map, movement and picture

The map uses one byte per cell, with an eight-byte row stride. Tile IDs are
floor 0, wall 1, collectible 2, and exit 3.

The actor image is 4 but is never stored in the map. A separate property table
says which scenery permits travel.

```text
..#.....
.*#..#..
..#.....
....##..
.#......
......E.
```

The actor starts at column 0, row 0. Each move proposes an adjacent cell.
The program rejects unsigned underflow and upper limits before it indexes the
map.

Then the tile's property permits or rejects the move. An accepted collectible
becomes floor in the map before rendering.

Each tile is eight bytes: one byte for each of eight pixel rows. For cell
column `c` and row `r`, map offset is `r * 8 + c`.

## Prepare the pictures from a drawing

The five pictures are the cells of [tiles.png](tiles.png), left to right:
floor, wall, collectible, exit and actor. Each cell is 8×8 source pixels, one
source pixel for each RG6 pixel.

Before each build, [prepare.py](prepare.py)
deletes the old output and converts the drawing with `scripts/graphics.py`.
The result is `tiles.asm` in the build folder, with the labels `tiles_r0c0` to
`tiles_r0c4`. The [assets guide](../../guidance/techniques/assets.md) gives
the method.

The `pictures` table in `main.asm` gives the picture label for each image ID.
The assembly stops in these conditions:

- The table names a picture that the drawing does not have.
- A picture is not eight rows of one byte. The program tests the `_bpr` and
  `_rows` values that `graphics.py` writes.
- The conversion failed. Then there is no `tiles.asm`.

The first display byte is `$0400 + r * 256 + c`. The image rows after the
first are 32 bytes apart. The lower-right cell starts at `$0907`, with its
final row at `$09E7`.

These address calculations are derived. The complete framebuffer oracle checks
them independently.

Every checkpoint redraws the entire framebuffer from current map state. It
then draws the actor. No saved background can reintroduce a collected item.

This approach is simple but does more work than dirty-cell drawing. It does
not synchronize to vertical blanking. This README makes no claim about
smoothness or frame rate.

## Source facts and provenance

The following hardware page images were read before implementation. Their
facts support the display setup. The room and movement rules are our design.

SHA-256 values identify the exact PDFs that were examined locally.

- Tandy, [Color Computer Technical Reference Manual][technical].
  - PDF 14 (printed 7): `$FF22` video fields and `$FF23` data-register
    selection.
  - PDF 15 (printed 8): SAM display-offset, video-mode, page and CPU-rate
    strobes.
  - PDF 31 (printed 24): 256×192 uses SAM `110` and PIA bits 7–4 `1111`.
  - SHA-256 `8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64`.

- Tandy, [Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)][service],
  PDF/printed 31: MC6847 video, SAM addressing, and PIA-controlled mode inputs.
  SHA-256 `7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447`.

- Don Inman, Kurt Inman with Dymax,
  [Assembly Language Graphics for the TRS-80 Color Computer][graphics],
  PDF 107 (printed 98).
  - Eight graphic elements per byte and black/green color set zero.
  - SHA-256 `c1259497b7d1505e6908fd3c8a250d47e0c4b549140e308bdc6bf8e345b6ce01`.

- Motorola, [MC6847 datasheet][vdg], PDF/printed 19, Table 3.
  - RG6 is 256×192 and 6,144 bytes.
  - Pixel order runs L7 through L0 across the byte.
  - SHA-256 `2d4586d2fd3c82c60071bbe4cc3930e561c00dce1e43245b0c7ffd5e081fe88c`.

The guide's reading of the PacDude source gave the separation of map
addressing, display addressing and movement rules. This example does not
copy its renderer or its diagonal-path collision. The guide lists the
[archive sources](../../guidance/techniques/tile-maps.md#sources).

## Evidence and limits

`coco.py check` compares all 42 checkpoints on each defined target. The
specifications in `tile_room_spec.py` test the model and the conversion. The
full starter suite runs them with `uv run pytest`.

The two result files record the same binary SHA-256 and each target's
checkpoint list.

The independent host oracle walks a graph of passable cells. It then composes
pixels from text drawings. To derive its expectations, it does not read the
assembly map, art, script, or captured RAM.

The specifications also assert literal positions at selected checkpoints. They
do not trust the oracle alone.

All 42 checkpoints cover every scripted move and the initial picture:

- Left and top boundary rejection at steps 1 and 2, right at 20, bottom at 26.
- Walls approached from left, below, above and right at steps 4, 9, 17 and 35.
- Collection at 5, departure at 6, return at 39, departure at 40 and return
  at 41.
- Exit traversal at 27, departure at 28, and return at 29.
- At every checkpoint on both targets:
  - every map byte
  - all 6,144 framebuffer bytes
  - four guards
  - actor coordinates
  - acceptance flag
  - script step

The check starts with nonzero RAM and needs a completed-frame PC trap.
A data-address trap must never fire.

Negative controls corrupt the screen, map, guards and state, and deliberately
select missing or unexpected traps. Firmware tests cover missing, partial and
corrupt installations. Help and argument tests intercept process execution to
prevent accidental launches.

Initial CoCo 1 checking reached step 34 but missed 35 under a budget of
ten seconds of emulated time. Raising that budget to 60 allowed the complete
script. The host still limits each capture to 30 seconds.

The failed check did not write a success record. This was a correction to the
test budget, not a speed claim.

Assembly and emulator RAM evidence are distinct from rendered-display evidence.

Later, the pictures moved from hand-written bytes to `tiles.png` and
`prepare.py`, and the check started to compare XRoar's rendered picture.

With the pinned XRoar, all 42 frames on both targets match `expected_frame`
in all 98,304 samples. The art in `expected.py` is text drawings, not the
drawing or the converted bytes. Integration tests in `scripts/coco_spec.py`
make sure that these changes fail:

- One changed pixel in `tiles.png` (7 screen bytes differ at frame 1).
- A clear loop that writes one byte past the screen (a damaged guard).
- A drawing without the actor's cell (the assembler stops).
- Pictures converted at 16×16 (the assembler stops).

These items remain untested:

- appearance on a television or monitor
- real keyboard input
- physical hardware
- PAL
- T1
- CoCo 3
- audio
- performance

[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf>
[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf>
[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf>
[vdg]: <https://people.ece.cornell.edu/land/courses/ece4760/ideas/mc6847.pdf>
