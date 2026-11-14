# Masked objects over patterned scenery

This is an original 6809 software masking algorithm and scene design. It draws
two hollow 16×10 objects with opaque green and opaque black edges. Their holes
and outer rows are transparent. It does not copy a historical program listing.

The renderer computes `(destination AND preserve_mask) OR ink` for each pair
of screen bytes. A mask bit of one preserves the pixel underneath; a zero
replaces it with the ink bit. Ink bits beneath preserve bits are zero. Opaque
black is therefore different from transparency.

Every scene redraws the current checker background before drawing the objects.
This restores old positions and handles overlap by composing both objects again
in the requested order. It needs no saved-background storage. This is a bounded
full-redraw design, not an implementation of GrafExpress's restoration buffers
or Dunkey Munkey's renderer. The [source review](../../guidance/techniques/research/rendering-sources.md)
explains what those historical sources actually establish.

## Run and check

The native tools and validated firmware must already be installed. From the
repository root:

```sh
uv run python scripts/coco.py check examples/masked-objects
uv run python scripts/coco.py run examples/masked-objects --target coco1
```

`check` covers both targets declared in [coco.toml](coco.toml); add
`--target coco2` to check one. Frame N of the check shows scene N - 1.

`run` opens a normal-speed XRoar window and cycles through 12 discrete scenes.
Close that window to stop. There are no controls or return to BASIC.
`check` uses bounded headless processes and never opens a window. Both actions
rebuild the DECB binary and verify the firmware bytes before launching XRoar.
The resulting absolute firmware paths are passed explicitly.

This is direct DECB auto-run. No disk image, disk boot or `LOADM` result is claimed.

## Hardware contract and direct sources

Both targets are NTSC CoCo 1/2 with 32 KiB RAM, a normal-clock 6809, and the
non-T1 MC6847. The program explicitly clears both SAM CPU-rate bits. IRQ and
FIRQ are masked after entry. It relies on BASIC firmware's initialized PIA
direction registers, then selects the data register and preserves `$FF22`'s
low three bits when setting graphics fields.

| Target | XRoar architecture | VDG / CPU | Firmware |
| --- | --- | --- | --- |
| CoCo 1 | `cocous`, 32 KiB | `6847` / `6809` | `bas11.rom`, `extbas10.rom` |
| CoCo 2 | `cocous`, 32 KiB | `6847` / `6809` | `bas12.rom`, `extbas11.rom` |

The CoCo 2 configuration deliberately selects the shared NTSC architecture and
CoCo 2 firmware with a non-T1 VDG. It does not prove all CoCo 2 board revisions.

The following source pages were inspected as rendered images before implementation:

- Inman, Inman and Dymax, *Assembly Language Graphics for the TRS-80 Color
  Computer*, printed 97–98 / PDF 106–107: mode 6R is 256×192, uses 6 KiB,
  and encodes eight pixels per byte. CSS zero gives black for zero and green
  for one. [Graphics book][graphics]
- Motorola, *MC6847/MC6847Y Video Display Generator*, PDF 19, Table 3:
  RG6 uses one bit per element, with L7 leftmost and L0 rightmost.
  [Motorola datasheet][motorola]
- Tandy, *Color Computer Technical Reference Manual*, printed 7–8 / PDF 14–15:
  PIA `$FF22` fields, `$FF23` data-register selection, SAM offset and rate
  strobes. Printed 24 / PDF 31: 256×192 uses SAM V=`110` and PIA bits 7–4
  `1111`. [Technical manual][technical]
- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
  printed/PDF 31: MC6847 video generation, SAM addressing and PIA video
  control connections for the board family. [Service manual][service]

Derived layout: 256 / 8 = 32 bytes per row; 32 × 192 = 6,144 bytes.
Display offset F=2 selects `$0400`. SAM V=6 and PIA upper bits `$F0`
select RG6 with CSS zero. These hardware facts justify the setup; the mask
format, ring geometry and scene sequence are our own design.

## Bounds and memory

| Region | Addresses |
| --- | --- |
| Framebuffer | `$0400–$1BFF` |
| Framebuffer guards | `$03FF`, `$1C00` |
| Code, scene table, shape data, mutable state | `$3000` to `program_end - 1` |
| Stack reservation | `$7E00–$7EFF`, initial S=`$7F00` |

The build rejects a program that reaches the stack reservation. Shape data has
10 rows, each holding a 16-bit preserve mask and a 16-bit ink value, 40 bytes
per object. All mutable state is initialized before use.

Origins are whole byte columns, 0–30, and pixel rows, 0–182. Callers must keep
the entire 16×10 bounding box on screen. There is no clipping, negative-coordinate
support or arbitrary pixel alignment. The fixed scene table respects those bounds.
Each object has a one-row transparent margin at top and bottom and a hollow
interior. Its two side edges have different colours, which exercises bit order.

Transparency describes which displayed pixels survive. There is no collision
representation, collision detection, hit testing or solidity rule here.

## Evidence and limits

The 12 scenes cover all four corners, partial overlap in both draw orders,
complete overlap in both orders, separation, removal of both objects, and
inverted scenery beneath overlapping objects. Removal and subsequent redraw
exercise restoration across consecutive scenes, not only isolated blank starts.

Each real XRoar capture starts with nonzero RAM and checks the scene checkpoint,
all 6,144 screen bytes, both framebuffer guards, and an unreachable data trap.
The independent oracle uses per-pixel ring geometry and layer composition. It
neither reads the assembly's masks nor repeats its byte blend loop. Host tests
also anchor left/right bit order and distinguish zero ink from a transparent hole.

Tests deliberately move the negative trap to reachable code and move the ready
trap to unreachable data. These controls must fail, erase stale snapshots, and
then recover on a valid capture. Damaged guards, framebuffers, counters, wrong
RAM sizes, missing firmware and stack overlap are rejected too.

XRoar 1.12.1 passed all 12 scenes on both configurations. The scoped suite
passed 18 tests with 96.09% combined statement and branch coverage. Ruff and
Markdown checks passed. Independent integration review passed the full suite
with 195 tests, zero skips and 94.65% coverage. Subsequent stale-evidence and
firmware-launch regression checks passed in a 95-test focused run.

Run only this example's specifications with:

```sh
COVERAGE_FILE=build/masked-objects/.coverage uv run pytest \
  examples/masked-objects --cov=examples/masked-objects
uv run ruff check examples/masked-objects
uv run ruff format --check examples/masked-objects
```

Generated binaries, symbols, logs, RAM captures, coverage and results live under
ignored `build/masked-objects/`. Source-page images remain ignored under
`local/research/masked-objects/`. No copyrighted source material is distributed
with the example.

The headless checks establish framebuffer contents, not a visually inspected
emulator display. Physical hardware, composite colour appearance, PAL, T1,
CoCo 3, disk loading and frame rate remain untested. Rendering writes directly
to the displayed buffer without vertical synchronization, so tearing or flicker
is possible. The delay loop is for scene visibility, not calibrated timing.
`-no-ratelimit` accelerates host execution during checks; it does not select a
faster emulated CPU clock.

[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=106>
[motorola]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=19>
[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=14>
[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>
