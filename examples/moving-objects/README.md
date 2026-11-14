# Moving objects over changing scenery

This original experiment redraws a patterned background, then draws two opaque
rectangles in a defined order. It asks whether objects can cross, separate,
reach the edges, and leave the current scenery intact.

It implements the full-redraw proposal in
[Move objects without losing the world](../../guidance/techniques/moving-objects.md).
It does not implement masks, saved-background rectangles, clipping, or collision.
The assembly and scene design are original work, not a copied book program.

## Run it

Prepare the starter's native tools and the selected machine's firmware first.
From the repository root:

```sh
uv run python scripts/coco.py check examples/moving-objects
uv run python scripts/coco.py run examples/moving-objects --target coco1
```

`check` covers both targets declared in [coco.toml](coco.toml); add
`--target coco2` to check one. Each command rebuilds the binary. The run
command opens XRoar at normal speed. Close its window to stop it. There are no
controls and no return to BASIC. The loader is direct DECB auto-run, not a disk
boot or `LOADM` check.

The intended picture is two 16×8 rectangles over an 8×8 checker pattern.
One rectangle uses set pixels; the other uses clear pixels. They move in
opposite horizontal directions and share a vertical position. Layer order
changes every 32 frames. Scenery inverts every 64 frames.

The display has not been visually inspected. These descriptions specify the
intended picture; the checks below establish its memory representation.

## Machine contract

Both targets use NTSC, 32 KiB RAM, a normal-clock 6809, and an MC6847.
The assembly explicitly selects the slow SAM clock. It masks IRQ and FIRQ.

| Target | XRoar architecture | VDG | Explicit firmware |
| --- | --- | --- | --- |
| CoCo 1 | `cocous` | `6847` | `bas11.rom`, `extbas10.rom` |
| CoCo 2 | `cocous` | `6847` | `bas12.rom`, `extbas11.rom` |

The CoCo 2 test uses the shared NTSC CoCo architecture with the CoCo 2 ROMs
and an explicit non-T1 VDG. It does not use the `coco2bus` profile's T1 default.
This is a defined emulator configuration, not proof for every CoCo 2 revision.
The check reports the exact configuration in its results file.

ROMs remain in ignored `local/roms/` storage. The project manifest identifies
their source and checksums. The check never changes `local/PROJECT.md`.

## Source facts and our design

Tandy's *Color Computer Technical Reference Manual* establishes these controls:

- PDF 14 (printed 7): `$FF22` video fields and `$FF23` data-register selection.
- PDF 15 (printed 8): SAM display offset, video mode, and CPU rate strobes.
- PDF 31 (printed 24): 256×192 mode uses SAM `110` and PIA bits 7–4 `1111`.

The implementation reuses the starter's
[first-screen setup](../first-screen/README.md). It selects CSS zero while
preserving PIA low bits. The framebuffer contains 32 bytes per row for 192 rows,
so its derived size is 6,144 bytes. [Tandy technical manual][technical]

Tandy's *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
PDF/printed 31, identifies its MC6847, SAM display addressing, and PIA-controlled
video inputs. It establishes the board family used for the source comparison,
not T1 or PAL behaviour. [CoCo 2 service manual][service]

Don Inman, Kurt Inman with Dymax, *Assembly Language Graphics for the TRS-80
Color Computer*, chapter 7, printed 151–156 / PDF 159–164, supplies the research
starting point: shape data, placement bounds, and rectangle erasure.
Our full-scene redraw replaces the old-rectangle erase design. We did not
reproduce that program or its ROM joystick calls. [Graphics book][graphics]

All rendered bytes here are either `$00` or `$FF`. The rectangles and checker
cells are byte-aligned. Their visible geometry does not depend on which bit
appears first inside a byte. Arbitrary pixel alignment remains outside this test.

## Memory and motion

| Region | Addresses |
| --- | --- |
| Framebuffer | `$0400–$1BFF` |
| Framebuffer guards | `$03FF`, `$1C00` |
| Code and initialized state | `$3000` through `program_end - 1` |
| Reserved stack | `$7E00–$7EFF`, growing down from `$7F00` |

The build rejects code that reaches the stack reservation. Symbols come from
the same assembled binary used by the emulator checks.

The object origins move one byte horizontally and one pixel vertically per frame.
Horizontal origin bounds are 0–30 bytes; vertical origin bounds are 0–184 pixels.
Those bounds include the whole 16×8 rectangle. Motion reverses before the next
step would leave the screen. The objects share their vertical trajectory.

Every frame draws the complete current background before either object.
There is no saved image that can accidentally restore old scenery.
Changing layer order and inverting the background exercise that distinction.

This simplicity costs a full framebuffer redraw per frame. The program does
not synchronize with vertical blanking, so it may flicker or tear.
No frame-rate or smoothness measurement is claimed.

## Emulator checks

The check captures completed frames 1, 15, 16, 17, 31, 32, 46, 64, 65,
185, 186, 369, and 370. Each capture checks:

- The actual frame counter and both object-position coordinates.
- All 6,144 framebuffer bytes against an independent pixel-level scene.
- Guard bytes immediately before and after the framebuffer.
- An unreachable data-address trap that must not produce a snapshot.

The independent movement oracle uses a closed-form reflected trajectory.
It does not repeat the assembly's direction-update loop. The scene oracle
composes the background and objects by pixel coordinates, rather than copying
the assembly's byte-writing loops.

Frames 16 and 46 exercise opposite overlap orders. Frames around those overlaps
check restoration after separation. Frames 64 and 65 check changed scenery.
The selected boundaries and their following frames check motion reversal.
Tests also reject corrupted RAM, guards, positions, and frame counters.

XRoar 1.12.1 passed these checks for both defined configurations on the
Apple Silicon development Mac. Native tests start with nonzero RAM.
`-no-ratelimit` accelerates host execution; the emulated CPU remains at its
normal clock. Each process has both emulator and host timeouts.

The CI workflow provisions CoCo 2 firmware before pytest, alongside its existing
CoCo 1 and CoCo 3 firmware. It preserves the CoCo 1 project target.
The development Mac passes all 133 tests with 93.99% combined coverage.
The non-integration run passes 124 tests; Ruff check and format checks pass.

Results, logs, symbols, and snapshots are ignored under `build/moving-objects/`.
The implementation files are [main.asm](main.asm), the machine and checkpoint
settings in [coco.toml](coco.toml), the independent scene model in
[expected.py](expected.py), and [its specifications](moving_objects_spec.py).

Visual appearance, physical hardware, PAL, T1, CoCo 3, sound during redraw,
independent vertical object motion, and partial-byte placement remain untested.

[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=14>
[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>
[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=159>
