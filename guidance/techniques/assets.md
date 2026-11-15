# Prepare assets before the drawing loop

Read this when you decide how artwork becomes data for the drawing loop. This
guide covers picture IDs, descriptors, where the bytes live and how a build
makes them. The [graphics guide](graphics.md) covers modes, pixel packing and
the converter, `scripts/graphics.py`. Use [moving objects](moving-objects.md)
for drawing over scenery and [animation](animation.md) for frame storage.

We measured the method on CoCo 1 and CoCo 2 in RG6, in the tile-room and
collect-room examples. The two magazine sources are CoCo 3 articles. We read
them but did not run them.

## Keep art, pictures and scene state apart

Diego Barizo's "Mine Sweeper! The Mission" draws its pictures once during
setup, captures each one with HGET and selects them when it shows the map.
Read the graphics setup, lines 4500–4960, on PDF 17–18, and the map display,
lines 5000–5070, on PDF 18. It is a BASIC workflow on the CoCo 3, not a
binary asset format. Its random marks (`RND` on PDF 17) do not make a
repeatable picture. [Barizo, *CoCoNutz!* 2:2, PDF 12–19][barizo]

Our adaptation, which the examples use:

1. Keep the source art in the project: a drawing, or a deterministic recipe.
2. Convert each picture before the program runs. Record its size and colour
   set.
3. Give each picture an ID. Keep map and actor state in their own tables.
   Translate a map value to a picture ID through an explicit table.
4. Let the drawing loop use only the converted bytes. Keep conversion and file
   parsing out of the loop.

Picture pixels, transparency, collision shape and map rules are different
data. Do not let one stand in for another. The
[controls guide](controls-and-collision.md) keeps collision separate.

## Convert the pictures at each build

This is the method of [tile-room](../../examples/tile-room/README.md):

1. Draw all pictures in one PNG, one equal cell for each picture, with no
   gaps. For pixel art, draw one source pixel for each mode pixel.
2. In `coco.toml`, set `prepare = "prepare.py"`. `scripts/coco.py` runs
   `prepare(output)` before each build.
3. In `prepare(output)`, delete the old output first. Then run
   `graphics.py sheet` with `--fit stretch --resample nearest`. Those options
   keep every source column and copy each pixel. Stop on any error.
4. Include the generated `.asm` file in `main.asm`. Give the drawing routine a
   table of picture labels, in image-ID order.
5. Test the `_bpr` and `_rows` equates of the include with `if` and `error`,
   so that a picture of a different size stops the assembly.
6. In `expected.py`, write the pictures again as text drawings. Do not read
   the PNG or the converted bytes there.

An original fragment of tile-room's `main.asm`:

```text
pictures fdb tiles_r0c0,tiles_r0c1,tiles_r0c2,tiles_r0c3,tiles_r0c4
        include "tiles.asm"
        if tiles_r0c0_bpr-1
        error "tiles.asm: each picture row must be 1 byte"
        endc
```

Each failure then stops at the earliest step that can see it:

| Fault | Where it stops |
| --- | --- |
| The conversion fails | `prepare.py` stops, and no old include stays |
| The table names a picture that the drawing does not have | The assembler: undefined label |
| Two includes use the same label | The assembler: multiply defined symbol |
| A picture has a different size | The assembler: the `error` line |
| A pixel of the drawing changes | `coco.py check`: screen bytes differ |

`coco.py` runs the conversion at each build, so an old include cannot stay in
use. Do not commit converted bytes beside the drawing. That copy can get
stale.

Collect-room uses a different step. Its `assets.py` converts `terrain.png`,
enlarges each picture to 16×16 and writes its own include. It compares the
converted bytes with `expected.py` before it writes the include.

## Give each picture an ID and a descriptor

Barizo's text says that the map numbers are the HGET buffer numbers
(PDF 12). Line 5050 draws buffer `M(X,Y)+1` (PDF 18). His cursor uses
offset `-18` (line 215, PDF 13) and his terrain uses `-24` (line 5050). These
are reasons to write the ID translation and each anchor as data. Do not copy
the prose into a contract.

For each kind of picture, record these items:

- Width in bytes and height in rows. `graphics.py` writes them as
  `<label>_bpr` and `<label>_rows`.
- Mode and colour set. The header comment of the include gives them. The
  colour set applies to the whole screen ([graphics](graphics.md#know-the-colours)).
- The anchor: the pixel of the picture that the position refers to.
  `graphics.py` does not write it. Keep it in the program, one for each kind
  of object.
- The row stride of the destination, which is the screen width in bytes.

Use an asymmetric test picture, so that a check can see a picture that is
upside down or mirrored. Use the same rule for bounds everywhere: inclusive or
exclusive.

Give each data section its own start and length. Barizo's introduction reads
text DATA before palette DATA. Its skip path must read to the `X` sentinel
(line 7160), or the palette load fails (PDF 12). Then text and palette are
coupled. A separate start for the palette removes that coupling.

Barizo sets colours for an RGB monitor and tells TV users to change line 7260
(PDF 12). That is not evidence that the two displays look the same. Select
the display with the [colour guide](colour.md).

## Know where the bytes live

In tile-room, the pictures are part of the DECB program. They are at `$3000`
and up, with the code, below the stack at `$7E00`. The `[memory]` table in
`coco.toml` makes the build fail on an overlap. Five 8×8 RG6 pictures use
40 bytes, and the table uses 10 bytes.

Collect-room stores each picture enlarged to 32 bytes, so its draw loop does
no scaling. That costs memory and saves work at draw time. Neither example
loads assets from disk or tape. `coco.py` loads the program into XRoar.

## Keep banked storage separate from the window

Robert Gault's "Special Backup Utility for a Coco3 Using Full 512K RAM" is a
disk copier for a 512K CoCo 3, not a game loader. Its `MMU` routine writes a
block number to `$FFA2` and uses the window at `$4000–$5FFF` (PDF 41).
`RDWRDK` changes the block between tracks (PDF 44–46). `COLD` restores one
BASIC mapping (PDF 40–41). [Gault, *CoCoNutz!* 2:3, PDF 38–46][gault]

A pointer into such a window is correct only with its mapping. This is our
proposal, which we did not test:

1. Record a block and an offset in the descriptor, not only a CPU address.
2. Reserve blocks for assets, code, state, stack and screen separately.
3. Copy assets into a stable buffer while a level loads, or map them for each
   short access. Copies cost RAM. Mapping needs control of each user of the
   window.
4. Keep code, stack and interrupt data in view during the access. Read the
   MMU and interrupt pages of the target's manual first.
5. Restore the caller's mapping on success and on failure.

Gault's restore constant is not a general save and restore. A game with sound
needs more evidence. His interrupt handling does not show that a frame loop
and a sound handler can share the window.

## Get evidence before you add compression

Neither article gives a compressed format or a timed table of frames. HGET
capture is not compression. Start with uncompressed pictures. Count headers,
masks, palette data, work buffers and shifted copies.

For a later codec, store the encoded and the decoded length. Refuse truncated
input and output overflow. Measure the worst decode time on the target. A
small file can need a large work buffer. These are our requirements, not
results from the articles.

## What the examples check

`uv run python scripts/coco.py check examples/tile-room --video` converts
`tiles.png`, assembles, and runs 41 moves on CoCo 1 with the pinned
instrumented XRoar. At the start and after each move, it compares all 6,144
screen bytes and the rendered frame with the model in `expected.py`.
Integration tests in `scripts/coco_spec.py` cause a changed pixel, a missing
cell and 16×16 pictures. Each one must fail.

Collect-room's check runs its converted terrain through a key journey on
CoCo 1 and CoCo 2B. Neither check shows a television or a physical CoCo.

**Earlier lab results, not rerun.** A host converter wrote four 8×8 RG6
pictures and a room into a JSON bundle. 33 cases passed. They rejected
missing, duplicate and unknown IDs, wrong sizes, pixels out of range, damaged
or stale output, and a source file used as its output. A 6809 consumer then
drew 48 cells through a pointer table on CoCo 1 and CoCo 2 with XRoar 1.12.1.
In 35 tests, it matched all 6,144 framebuffer bytes with literal expectations.
Complemented pictures gave 384 differing bytes, and a store past the screen
damaged a guard.

Tile-room now does that check with `graphics.py`, so we removed the converter
and the consumer.

## Open questions

Nothing checks text and palette sections in one file, banked storage, mapping
restore after an error, disk or tape loading, or compression. Nothing checks
CoCo 3 pictures, PAL, T1 VDGs or physical hardware.

## Sources

- Diego Barizo, "Mine Sweeper! The Mission", *CoCoNutz! E-Zine* volume 2,
  issue 2, July 2006, PDF 12–19. SHA-256
  `fbacbeee8205063bf49dc52f4468c4e808c124b0ba4d2f9caa498485b25a7a7d`.
- Robert Gault, "Special Backup Utility for a Coco3 Using Full 512K RAM",
  *CoCoNutz! E-Zine* volume 2, issue 3, October 2006, PDF 38–46. SHA-256
  `6027e4d0708d62442c2e9e83e9f49ec66f6dba6fe53a90142586f181e3cf0c0c`.

These are direct archive citations, with no resource IDs in the manifest. The
article pages have no printed page numbers. We read both complete listings.
A search of the next issue found no correction. We found no redistribution licence,
and Gault's listing shows a copyright (PDF 40). The examples use original art
and code.

[barizo]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Coco%20Nutz%21%20Newsletter/Coco%20Nutz%21%20Vol%202%20Issue%202%2C%20July%202006.pdf#page=12>
[gault]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Coco%20Nutz%21%20Newsletter/Coco%20Nutz%21%20Vol%202%20Issue%203%2C%20October%202006.pdf#page=38>
