# Draw in the CoCo 3 GIME graphics modes

Read this before you choose a graphics mode for a CoCo 3 project, or before
you write its display setup. It covers the native graphics modes of the CoCo 3
video chip (GIME) on the 1986 and 1987 revisions, at 128 KiB and 512 KiB.

For the VDG modes that the CoCo 3 keeps for CoCo 1 and 2 programs, read
[the VDG graphics guide](graphics.md). For how a colour code looks on a
display, read [the colour guide](colour.md#coco-3-palette-meanings). This guide
does not cover text modes, scrolling, page flips or interrupts. The
[text-addressing](../../examples/text-addressing/README.md),
[scrolling](scrolling.md) and [animation](animation.md) guides cover them.

`scripts/graphics.py` converts artwork to the GIME modes and chooses the
palette codes. Run it with `--help`, or read the
[retro-art skill](../../.agents/skills/retro-art/SKILL.md).

The [gime-graphics example](../../examples/gime-graphics/README.md) sets up
each mode. Its README has the table of all twenty modes, the register values,
the steps and the check commands.

## Choose a mode

`$FF99` selects the mode. HRES (bits 4 to 2) selects the bytes in each row.
CRES (bits 1 and 0) selects 1, 2 or 4 bits for each pixel.
[Tepolt, PDF 41 and 42, Table 4-10][tepolt-modes]

- A row of 20, 40, 80 or 160 bytes fills the width of the screen (HRES bit 0
  is 1). A row of 16, 32, 64 or 128 bytes is short: the picture has a border
  at the left and the right. [Tepolt, PDF 39 and 41][tepolt-format]
- CRES `10` gives 16 colours, `01` gives 4 and `00` gives 2. CRES `11` blanks
  the screen. [Tepolt, PDF 41 and 42][tepolt-modes]
- HRES `000` or `001` with CRES `10` is "Not Used".
  [Tepolt, PDF 41][tepolt-modes]
- HRES `110` or `111` with CRES `00` uses two bytes for each pixel. Tepolt
  calls this format X. Only bit 7 of the first byte selects palette 0 or 1.
  [Tepolt, PDF 42][tepolt-change] Nobody has checked format X in this starter.

BASIC uses four of the modes. [Unravelled, PDF 58][unravelled-res] and
[Tepolt, PDF 42][tepolt-change] agree:

| BASIC | Pixels | Colours | `$FF99` |
| --- | --- | --- | --- |
| `HSCREEN 1` | 320 | 4 | `$15` |
| `HSCREEN 2` | 320 | 16 | `$1E` |
| `HSCREEN 3` | 640 | 2 | `$14` |
| `HSCREEN 4` | 640 | 4 | `$1D` |

`$FF99` bits 6 and 5 (LPF) select 192, 200 or 225 rows. LPF `10` is
reserved. [Service Manual, PDF 12][service-video]
[Tepolt, PDF 32][tepolt-rows]

Our advice for a game:

1. Start with 320 pixels and 16 colours (`$1E`). It is the 16-colour mode with
   the most pixels. It uses 30720 bytes, four 8 KiB pages.
2. If memory is short, use 256 pixels and 16 colours (`$1A`): 24576 bytes,
   three pages, with a border at each side.
3. For two complete screens (a page flip), budget eight pages for 320 pixels
   or six for 256 pixels.
4. Use 192 rows unless the design needs more. A screen of 225 rows at 160
   bytes is 36000 bytes, five pages.

This is our adaptation of the sourced table. It is not a measured speed or a
measured picture quality.

## Set up the display

The [gime-graphics example](../../examples/gime-graphics/README.md#set-up-the-screen)
gives the steps. In short:

1. Write the palette registers `$FFB0-$FFBF`. Each holds a six-bit colour code.
   [Service Manual, PDF 17][service-palette]
2. Write `$FF90` with bit 7 clear (CoCo 3 modes) and the MMU on.
   [Service Manual, PDF 11][service-init]
3. Write `$80` to `$FF98`: graphics, one scan line for each row of pixels.
   BASIC writes the same value. [Unravelled, PDF 58][unravelled-res]
4. Write the mode to `$FF99`.
5. Write `$FF9C` to `$FF9F`: scroll, the display address and the horizontal
   offset. [Service Manual, PDF 12 and 13][service-address]

Each pixel value selects a palette register. The leftmost pixel is in the high
bits of the byte. [Tepolt, PDF 38 and 39][tepolt-format]

The GIME reads physical memory. `$FF9D` holds address bits 18 to 11, and
`$FF9E` holds bits 10 to 3. [Service Manual, PDF 13][service-address] The CPU
writes the screen through an 8 KiB MMU window. A 128 KiB machine does not use
address bits 18 and 17. [Tepolt, PDF 29][tepolt-memory] The
[text-addressing example](../../examples/text-addressing/README.md#choose-the-physical-address)
explains why one physical address must give both values.

Sock's reference says that some GIMEs crash with an odd value in `$FF9E` in
some modes. It advises steps of 16 bytes. [Sock, FF9D-FF9E][sock] Use a
screen address that is a multiple of 16.

## Know the two GIME revisions

**Published explanation.** Sock's reference names one difference between the
revisions. The timer counts a stored value `n` as `n+2` on the 1986 GIME and
as `n+1` on the 1987 GIME. [Sock, FF94-FF95][sock] The odd-`$FF9E` crash is in
"some versions of the GIME". Sock does not say which versions.
[Sock, FF9D-FF9E][sock]

**Emulator model.** XRoar 1.13.1 models the two revisions with different
constants in `src/tcc1014/tcc1014.c`:

- the timer offset (2 on the 1986 GIME, 1 on the 1987 GIME), as Sock says
- the length of horizontal sync (80 or 72 samples)
- the left border of a short graphics line with HRES bit 2 set (104 or 106
  samples)
- the front porch, and one more horizontal timing

**Measured result.** In XRoar, every mode in the example shows the same
picture on both revisions, except one thing. On the 1987 GIME, a short line
with HRES bit 2 set starts 2 samples later. The example's check models this.
Its negative control removes the shift and fails.

Thus the mode setup is the same on both revisions. A program that counts
timer ticks or times work to the raster must allow for the difference.

## Know what is verified

The [gime-graphics example](../../examples/gime-graphics/README.md) check runs
in XRoar 1.13.1 on three targets: the 1986 GIME at 128 KiB, the 1987 GIME at
128 KiB and the 1986 GIME at 512 KiB. Run it from the starter folder:

```sh
uv run python scripts/coco.py check examples/gime-graphics
```

- All twenty modes and both larger row counts match the screen bytes and the
  rendered picture on all three targets.
- `scripts/coco_spec.py` has four negative controls. Each keeps the screen
  bytes correct and fails the rendered check. They are a wrong palette code, a
  wrong HRES, a wrong LPF and a model without the 1987 shift.
- The rendered colour of sixteen palette codes is measured. It is XRoar's
  composite picture, not an RGB monitor.
- The capture is 512 samples wide and 192 lines high. It shows only the middle
  of a full-width line. It shows rows 2 to 193 of a 200-row screen and rows 17
  to 208 of a 225-row screen. XRoar's top border values give the same rows.

Nobody has checked a GIME mode on a television, an RGB monitor or a physical
CoCo 3.

## Open questions

- **Lines per row.** For `$FF98` LPR, the Service Manual gives `001` two,
  `010` three and `110` twelve lines. [Service Manual, PDF 12][service-video]
  Sock gives `001` one, `010` two, `101` ten and `110` eleven.
  [Sock, FF98][sock] Graphics uses `000`, where both agree. A text-mode or
  stretched-graphics check in XRoar, then on hardware, would settle it.
- **`$FF9C`.** Tepolt calls bit 3 SCEN, a scroll enable.
  [Tepolt, PDF 33][tepolt-scroll] Sock calls bits 3 to 0 the scroll value.
  [Sock, FF9C][sock] The example writes 0, which both read as no scroll.
- **200 rows.** XRoar shows 199 rows for LPF `01` and calls the value
  measured. The sources say 200. The capture does not show the last rows, so
  the check cannot settle it.
- **Odd `$FF9E`.** Nobody has reproduced the crash. XRoar may not model it.
- **Format X.** Not checked.
- **Revisions on hardware.** The 1987 short-line shift is XRoar's model. A
  capture from a physical 1987 GIME would settle it.

## Sources

- Tandy, *Color Computer 3 Service Manual*, PDF 11 to 13 and 15 to 18.
  Resource `coco3-service`.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*, 1987,
  PDF 29, 32, 33, 38, 39, 41 and 42. PDF 42 is the author's change page for
  Table 4-10. Resource `tepolt-coco3`.
- Spectral Associates, revised by Walter K. Zydhek, *Super Extended Basic
  Unravelled II*, 1999, PDF 58. Resource `super-extended-basic-unravelled`.
- John Kowalski, *Sock's GIME register reference*,
  <http://users.axess.com/twilight/sock/gime.html>, read 2026-11-16 from the
  [Wayback Machine](http://web.archive.org/web/20211201002932/http://users.axess.com/twilight/sock/gime.html).
- XRoar 1.13.1, `src/tcc1014/tcc1014.c`, the pinned emulator.
- Tandy, *Color Computer 3 Extended Basic*, resource `coco3-extended-basic`.
  The user manual for `HSCREEN` and the other graphics commands. This guide
  does not cite it yet.

[service-init]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=11>
[service-video]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=12>
[service-address]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=13>
[service-palette]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=17>
[tepolt-memory]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=29>
[tepolt-rows]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=32>
[tepolt-scroll]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=33>
[tepolt-format]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=38>
[tepolt-modes]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=41>
[tepolt-change]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=42>
[unravelled-res]: <https://colorcomputerarchive.com/repo/Documents/Books/Unravelled%20Series/super-extended-basic-unravelled.pdf#page=58>
[sock]: <http://web.archive.org/web/20211201002932/http://users.axess.com/twilight/sock/gime.html>
