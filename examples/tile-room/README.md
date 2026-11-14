# A small room with persistent map state

This original demo implements the fixed-room proposal in
[Build a room from tiles](../../guidance/techniques/tile-maps.md). It is an adaptation of
that guide's design, not a historical reproduction or a PacDude port.
All code, map data, and byte-aligned artwork here are original.

The actor follows a finite script through an asymmetric room. Walls block
movement. Collecting the diamond changes its map entry to floor. Walking away
and returning does not restore the diamond. The exit is a distinct passable
picture; it has no victory rule. There is no keyboard system.

## Run and check

From the repository root, with the existing native tools and verified firmware:

```sh
uv run python scripts/tile_room.py check --target coco1
uv run python scripts/tile_room.py check --target coco2
uv run python scripts/tile_room.py run --target coco1
```

`check` runs headlessly. `run` opens XRoar, moves through the script once,
and holds the final picture. Close XRoar to stop it. There is no return to
BASIC. This is direct DECB auto-run, not disk-loading evidence.
`--help` and invalid arguments do not build or launch anything.

A fresh build invalidates previous snapshots and success records before invoking
LWASM. To retain both targets' results from one binary, run the scoped specs:

```sh
COVERAGE_FILE=build/tile-room/.coverage \
  uv run pytest scripts/tile_room_spec.py \
  --basetemp=build/tile-room/pytest --cov=tile_room --cov-report=term-missing
```

Generated binaries, symbols, snapshots, logs, and success records stay under
ignored `build/tile-room/`. No firmware or downloaded source is distributed.

## Target and layout

The task specifies CoCo 1 and CoCo 2, NTSC, 32 KiB, a normal-clock 6809,
and a non-T1 MC6847. Both checks use XRoar's `cocous` architecture with explicit
`-vdg-type 6847`, `-machine-cpu 6809`, `-tv-type ntsc`, and `-ram 32`.
The runner uses `-c /dev/null` to exclude user configuration. CoCo 1 uses verified
`bas11.rom` and `extbas10.rom`; CoCo 2 uses verified `bas12.rom` and
`extbas11.rom`. These are defined emulator configurations, not evidence for
every board revision. The scoped local contract is
`local/research/tile-room/contract.txt`; shared project notes are untouched.

The display is RG6, 256×192, one bit per pixel, with 32 bytes per row and
6,144 bytes total. CSS is zero (black/green). The 8×6 room occupies the upper
left 64×48 pixels; the rest of the screen is cleared. This deliberately small
room keeps the map, drawing, and movement rules easy to inspect.

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
No ROM routines are called after entry.

## Separate the map, movement and picture

The map uses one byte per cell, with an eight-byte row stride. Tile IDs are
floor 0, wall 1, collectible 2, and exit 3. The actor image is 4 but is never
stored in the map. A separate property table says which scenery permits travel.

```text
..#.....
.*#..#..
..#.....
....##..
.#......
......E.
```

The actor starts at column 0, row 0. Each move proposes an adjacent cell.
Unsigned underflow and upper limits are rejected before indexing the map.
Then the tile's property permits or rejects the move. An accepted collectible
becomes floor in the map before rendering.

Each tile is eight bytes: one byte for each of eight pixel rows. For cell
column `c` and row `r`, map offset is `r * 8 + c`. The first display byte is
`$0400 + r * 256 + c`; subsequent image rows are 32 bytes apart.
The lower-right cell starts at `$0907`, with its final row at `$09E7`.
These are derived address calculations, independently checked through the
complete framebuffer oracle.

Every checkpoint redraws the entire framebuffer from current map state and
then draws the actor. No saved background can reintroduce a collected item.
This approach is simple but does more work than dirty-cell drawing. It does
not synchronize to vertical blanking; no smoothness or frame-rate claim is made.

## Source facts and provenance

The following hardware page images were read before implementation. Their
facts support the display setup; the room and movement rules are our design.
SHA-256 values identify the exact locally examined PDFs.

- Tandy, [Color Computer Technical Reference Manual][technical], PDF 14
  (printed 7): `$FF22` video fields and `$FF23` data-register selection.
  PDF 15 (printed 8): SAM display-offset, video-mode, page and CPU-rate strobes.
  PDF 31 (printed 24): 256×192 uses SAM `110` and PIA bits 7–4 `1111`.
  SHA-256 `8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64`.
- Tandy, [Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)][service],
  PDF/printed 31: MC6847 video, SAM addressing, and PIA-controlled mode inputs.
  SHA-256 `7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447`.
- Don Inman, Kurt Inman with Dymax, [Assembly Language Graphics for the TRS-80
  Color Computer][graphics], PDF 107 (printed 98): eight graphic elements per
  byte and black/green color set zero.
  SHA-256 `c1259497b7d1505e6908fd3c8a250d47e0c4b549140e308bdc6bf8e345b6ce01`.
- Motorola, [MC6847 datasheet][vdg], PDF/printed 19, Table 3: RG6 is
  256×192, 6,144 bytes, and pixel order runs L7 through L0 across the byte.
  SHA-256 `2d4586d2fd3c82c60071bbe4cc3930e561c00dce1e43245b0c7ffd5e081fe88c`.

The guide's PacDude source reading motivated the separation of map addressing,
display addressing and movement rules. This example does not reimplement its
renderer or diagonal-path collision. Its archive citations remain in the
[guide's reading record](../../guidance/techniques/tile-maps.md#source-and-reading-record).

## Evidence and limits

The scoped run passed all 12 specs, including all 42 checkpoints on each
defined target. Combined statement and branch coverage of `tile_room.py` was
98.67%. Ruff lint/format and scoped Markdown lint passed. The two result files
record the same binary SHA-256 and each target's checkpoint list.

The independent host oracle walks a graph of passable cells, then composes
pixels from text drawings. It does not read the assembly map, art, script,
or captured RAM to derive its expectations. The specs also assert literal
positions at selected checkpoints, rather than trusting the oracle alone.

All 42 checkpoints cover every scripted move and the initial picture:

- Left and top boundary rejection at steps 1 and 2, right at 20, bottom at 26.
- Walls approached from left, below, above and right at steps 4, 9, 17 and 35.
- Collection at 5, departure at 6, return at 39, departure at 40 and return at 41.
- Exit traversal at 27, departure at 28, and return at 29.
- Every map byte, all 6,144 framebuffer bytes, four guards, actor coordinates,
  acceptance flag and script step at every checkpoint on both targets.

The runner starts with nonzero RAM and requires a completed-frame PC trap.
A data-address trap must never fire. Negative controls corrupt the screen,
map, guards and state, and deliberately select missing or unexpected traps.
Firmware tests cover missing, partial and corrupt installations. Help and
argument tests intercept process execution to prevent accidental launches.

Initial CoCo 1 checking reached step 34 but missed 35 under a ten-second
emulated-time budget. Raising that budget to 60 allowed the complete script;
the host still limits each capture to 30 seconds. The failed attempt did not
write a success record. This was a test-budget correction, not a speed claim.

Assembly and emulator RAM evidence are distinct from rendered-display evidence.
No GUI was launched for this task. Display appearance, real keyboard input,
physical hardware, PAL, T1, CoCo 3, audio and performance remain untested.
The full starter suite is intentionally outside this worker's scope.

[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf>
[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf>
[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf>
[vdg]: <https://people.ece.cornell.edu/land/courses/ece4760/ideas/mc6847.pdf>
