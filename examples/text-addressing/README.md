# CoCo 3 display-address probe

This original probe checks why a text display address that works on a 128 KiB
CoCo 3 can select different memory on a 512 KiB CoCo 3. Read it when choosing
physical display addresses. It is a research experiment, not a scrolling demo.

The result supports the address explanation in the
[scrolling guide](../../guides/scrolling.md#understand-the-512k-correction).
It does not reproduce Blochowiak's SMOOTHY program or validate its BASIC hooks.

## What was measured

The probe writes four distinguishable words through the CPU MMU, then selects
a 40-column attributed text display. Low memory is written first, high memory
second. On a 128 KiB machine those regions alias; on a 512 KiB machine they do
not. Each build changes only the high display-address register, `$FF9D`.
`$FF9E` remains zero.

| Physical address written | Word written |
| --- | --- |
| `$0C000` | `$4141` |
| `$0C800` | `$4242` |
| `$6C000` | `$4343` |
| `$6C800` | `$4444` |

An instrumented XRoar 1.12.1 logged the address and returned word in
`src/coco3.c`'s `fetch_vram` callback. This is the RAM read used by the GIME
video path, separate from CPU reads. The diagnostic did not change address
calculation, memory contents, or the returned word.

| `$FF9D` | Video address | 128 KiB word read | 512 KiB word read |
| --- | --- | --- | --- |
| `$18` | `$0C000` | `$4343` | `$4141` |
| `$19` | `$0C800` | `$4444` | `$4242` |
| `$D8` | `$6C000` | `$4343` | `$4343` |
| `$D9` | `$6C800` | `$4444` | `$4444` |

All eight configurations produced 40 matching reads at the selected address.
A ready-PC trap produced a complete RAM snapshot of the requested size in
each run. An unreachable-PC control produced no snapshot, although video reads
confirmed that the program had run. Evidence is generated under ignored
`build/text-addressing/`, including `results.json`, logs, symbols and snapshots.

The emulator used NTSC, a stock 6809 at normal clock, GIME 1986 and explicit
Tandy Super Extended Color BASIC firmware. XRoar identified its CRC32 as
`b4c88d6c`. The ROM SHA-256 was
`ad358430568250eb8330a37f85361d9ce67e5ae6d5a28c17b31802cd3953a5d2`.

This establishes selection at the instrumented emulator's video-memory read
boundary. It does not establish rendered glyphs, screen appearance, scrolling,
tearing, timing, GIME 1987 behavior, or physical-machine behavior. Stock XRoar's
RAM snapshot alone would not establish which memory the display reads.

## Reproduce the experiment

Keep the instrumented executable separate from the installed XRoar. Do not
replace the user's emulator. The stock null UI discards rendered lines, and
its RAM snapshots do not retain the displayed pixels. CPU read watchpoints do
not observe GIME video fetches.

Download the [XRoar 1.12.1 source archive][xroar] into ignored `local/` and
check its SHA-256 before extracting it:

```text
ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88
```

Inside `src/coco3.c`, insert this original diagnostic immediately before
`return D;` in the definition of `fetch_vram(void *sptr, uint32_t A)`:

```c
if (A == 0xc000 || A == 0xc800 || A == 0x6c000 || A == 0x6c800) {
    fprintf(stderr, "VRAM %05x %04x\n", (unsigned)A, (unsigned)D);
}
```

The source already includes the declarations needed for `fprintf` and `stderr`.
From the extracted source directory, build without installing:

```sh
./configure --without-gtk2 --without-gtk3 --without-sdl3 --without-sdl2
make -j4
```

The recorded build used
`local/research/gime-scrolling/xroar-1.12.1/src/xroar`. Its configure and build
logs remain beside that source directory. No global executable was changed.

From the starter root, assemble the original probe. The definition is decimal
24 for `$18`; repeat with 25, 216 and 217 for `$19`, `$D8` and `$D9`.

```sh
mkdir -p build/text-addressing
lwasm --6809 -DFF9D_HIGH=24 --format=decb \
  --output=build/text-addressing/18.bin \
  --symbol-dump=build/text-addressing/18.sym \
  examples/text-addressing/main.asm
```

Use the `ready` address from that build's symbols. It was `$306F` in the tested
source. Obtain CoCo 3 firmware through the starter's setup if it is missing;
never substitute a launch without firmware. For the first configuration:

```sh
local/research/gime-scrolling/xroar-1.12.1/src/xroar \
  -machine coco3 -machine-cpu 6809 -ram 128 -vdg-type gime1986 \
  -extbas "$PWD/local/roms/coco3/coco3.rom" -no-cart \
  -ui null -ao null -ram-init set -no-ratelimit -timeout 8 \
  -trap pc=0x306f -trap-range 1-1 \
  -trap-snap "$PWD/build/text-addressing/128-18.ram" \
  -trap-timeout 0.1 -run "$PWD/build/text-addressing/18.bin" \
  > build/text-addressing/128-18.log 2>&1
```

Repeat all four binaries with `-ram 128` and `-ram 512`, using distinct output
names. Check the ROM-loaded message, the ready snapshot's size, and every
`VRAM` line against the table. Require at least eight matching fetches;
absence of diagnostic output is a failed observation. For a negative control,
use the unreachable address immediately after `ready`'s two-byte branch and
a fresh snapshot path. No snapshot should be created before the timeout.

The code occupies `$3000` onwards. CPU `$6000-$7FFF` temporarily maps the two
physical 8 KiB pages being filled. Interrupts are masked, and no stack
operation occurs during that mapping. The executive mapping is restored
before the ready loop. This probe has no interrupt or BASIC-return contract.

## Sources and provenance

The assembly and diagnostic are original. No magazine listing was copied.
These primary-source pages were read, with tables checked against page images:

- Tandy, *Color Computer 3 Service Manual*, PDF 11–13 and 15–16:
  initialization, display-mode/address registers and CPU MMU mapping.
  [Archive][service]
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*, PDF 29:
  128 KiB address aliasing; PDF 33: eight-byte display-base units;
  PDF 36: 40-column attributed text selection; PDF 58: BASIC's high-resolution
  text buffer at `$6C000`. [Archive][tepolt]
- John Blochowiak, "A Smooth Operator," *The Rainbow*, January 1988,
  printed 78, 80 / PDF 80, 82; and April 1988, printed/PDF 14, correction.
  These motivated comparing `$18/$19` with `$D8/$D9`.
  [Article][article] [Correction][correction]

The expected table combines those published address rules with our chosen
sentinel values. The measured table came from the independent GIME fetch path
in the pinned emulator source. Its relevant implementation is
`src/coco3.c:fetch_vram`; the GIME caller is in
`src/tcc1014/tcc1014.c:fetch_byte_vram`. [XRoar source][xroar]

[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=13>
[tepolt]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=29>
[article]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2006%20-%20January%201988.pdf#page=80>
[correction]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2009%20-%20April%201988.pdf#page=14>
