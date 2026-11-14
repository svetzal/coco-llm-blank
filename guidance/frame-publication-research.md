# Publish a completed hidden frame

Read this before adding page switching to the moving-object or cadence examples.
This is source research and a proposed validation contract. No assembly listing
was copied, no emulator was launched, and no physical machine was tested.
The [animation guide](../guides/animation.md) motivates separate drawing and
display storage; the [cadence experiment](animation-cadence-validation.md)
demonstrates why completed RAM alone cannot establish clean publication.

My recommendation is to render off-screen, publish only a complete image in a
verified timing window, and retain the old front buffer until the display has
actually adopted the new base. A register write is a request, not evidence that
the old buffer is free. Keep model-specific publication code separate from
scene construction. The facts below support that design, but do not prove a
portable tear-free implementation.

## Primary sources and exact pages

All page numbers are one-based PDF pages. These pages were read as full-page
images, including register tables. Downloads and PNGs are ignored under
`local/research/frame-publication/`; shared reference files were only read.
Image names are `<resource>-<PDF-page>.png`. The reproduction below retains
original inspection logic in Git and produces a per-image SHA-256 manifest.

| Resource | Primary archive source | Pages used here; printed numbering |
| --- | --- | --- |
| `coco1-technical` | [Tandy, Color Computer Technical Reference Manual][c1] | 13, 15, 28, 36; printed 6, 8, 21, 29 |
| `coco2-service` | [Tandy, Color Computer 2 NTSC Service Manual, 26-3134/3136][c2] | 11, 13–14, 30, 34; same printed numbers |
| `coco3-service` | [Tandy, Color Computer 3 NTSC/PAL Service Manual, 26-3334][c3] | 9, 11–15, 21, 36–39; same printed numbers |
| `sam` | [Motorola, SN74LS783/MC6883 and SN74LS785 datasheet][sam] | 8–9, 15–17; printed 5-330–331, 5-337–339 |
| `sam-advance` | [Motorola, MC6883 advance information][advance] | 15; printed 15 / 4-644 |
| `pia` | [Motorola, MC6821 NMOS Peripheral Interface Adapter][pia] | 7–10; same printed numbers |
| `mc6847` | [Motorola, MC6847/MC6847Y, DS9823-R1][vdg] | 8, 12; same printed numbers |

Source SHA-256 values, in table order:

```text
coco1-technical 8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64
coco2-service   7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447
coco3-service   5c4c82d1b825daacf861be097d93d0a0eff78fbdf394234d4adb06df0cfd3c29
sam            1f763b10cc548a9bfee755831c42de44c6e2b7cf26658f81a456f18f33820579
sam-advance    7d8913ee86fada3c4019e5b4e87742529f58bf0c22aec1397a9c19ebdad4728c
pia            ae4751e18a23facd324b6bdcd348e42c0e23a80a465c7950571aa5300efffd1c
mc6847         2d4586d2fd3c82c60071bbe4cc3930e561c00dce1e43245b0c7ffd5e081fe88c
```

## CoCo 1/2 screen base and publication

Tandy C1 PDF 15 and C2 PDF 14 map F0 through F6 to the address pairs below.
Motorola SAM PDF 15 places them at address bits 9–15, with bits 0–8 zero.
Thus `base = F * 512`, with 512-byte alignment. SAM PDF 8 and 16 specify
address-selected writes: even clears, odd sets, and the data byte is irrelevant.
There is no single seven-bit write or commit register in this interface.

| Offset bit | Address weight | Clear write | Set write |
| --- | --- | --- | --- |
| F0 | `$0200` | `$FFC6` | `$FFC7` |
| F1 | `$0400` | `$FFC8` | `$FFC9` |
| F2 | `$0800` | `$FFCA` | `$FFCB` |
| F3 | `$1000` | `$FFCC` | `$FFCD` |
| F4 | `$2000` | `$FFCE` | `$FFCF` |
| F5 | `$4000` | `$FFD0` | `$FFD1` |
| F6 | `$8000` | `$FFD2` | `$FFD3` |

SAM PDF 8 describes loading display-counter bits B9–B15 from F0–F6 when
vertical preload is high, clearing B1–B8 at the same time. The detector uses
a high DA0 while the VDG outputs are high impedance. C1 PDF 28 explains the
board's FS-to-tristate connection. C2 PDF 30 describes the counter reset by FS
and subsequent DA0 advancement. These are counter-reload mechanisms, not an
instantaneous CPU pointer exchange.

Advance-information PDF 15 expressly places the offset's effect during FS-low.
The corresponding paragraph in the other SAM scan, PDF 15, omits that sentence;
its PDF 8 still describes vertical preload. Neither passage specifies a
software-visible commit acknowledgement, a setup/hold allowance for the last
strobe, or atomicity across several writes. Do not translate "during FS-low"
into "latched exactly on the falling edge" or "any sequence during blanking
is safe." The latter requires a demonstrated deadline and worst-case latency.

Our proposed CoCo 1/2 procedure is to prepare a complete hidden buffer, discard
any stale sync event, observe a fresh selected edge, and perform the short
publication sequence with bounded latency. Verify the sequence completes in
the reload window on the exact target. Then establish that the new buffer is
being scanned before reusing the former front buffer. Interrupt masking can
bound software interference; it does not stop the video circuit.

Choose buffers whose base encodings differ in one bit when the memory map
allows it. For example, two 6,144-byte regions `$2000..$37FF` and
`$4000..$57FF` need two bit changes, whereas `$2000..$37FF` and
`$6000..$77FF` differ only in F5. This is an original allocation example,
not a complete program memory map: reserve code, assets, state, guards, stack,
ROM workspace and loader needs independently. Initial setup must establish
all seven bits. A one-strobe switch reduces the intermediate-address problem;
it does not prove the buffer-reuse deadline.

## PIA vertical sync is an event flag

C1 PDF 13, C2 PDF 11 and C3 PDF 9 assign `$FF03` bit 7 to field sync,
bit 1 to edge selection (0 falling, 1 rising), and bit 0 to CPU IRQ enable.
Bit 2 chooses data versus DDR at `$FF02`; bit 3 controls a shared analog
selection line. The Motorola PIA diagrams identify CB1 as the B-side interrupt
input; PDF 7–10 supply the register contract used here.

PIA PDF 7–10 establishes that the selected transition sets the flag. IRQ enable
controls interrupt delivery, not whether a transition can be recorded. The
flag clears on a read of the corresponding peripheral data register. Therefore,
with CRB bit 2 set, reading `$FF02` acknowledges the field-sync flag. Reading
`$FF03` observes it without that acknowledgement. Reading `$FF00` acknowledges
the other side, and reading `$FF02` with bit 2 clear accesses DDR instead.
These address-specific conclusions combine the chip contract with Tandy's map.

An asserted flag is not a measurement of the current FS level or remaining
blank time. It may be old, and multiple transitions can collapse into one bit.
Assign one owner to acknowledgement. A keyboard routine or ROM interrupt
handler that reads port B can consume the event before a polling publisher.
Preserve the other writable control bits and the port/DDR selection; do not
replace `$FF03` with an unexplained constant. Select the edge explicitly.
Do not assume a CPU `SYNC` wait identifies vertical sync when other IRQ sources
can wake it.

MC6847 PDF 8 figure 8 specifies an FS-low width of 32 horizontal periods;
the field period is 262 periods for MC6847 and 262.5 for MC6847Y. That is a
chip timing relation, not a measured game budget. PDF 12 distinguishes those
non-interlaced/interlaced variants. It does not establish MC6847T1 or PAL board
timing. Remaining time after detection must allow for polling/IRQ latency,
register writes and counter reload. A full redraw need not fit there when it
is done in a genuinely hidden buffer; publication still has a deadline.

## CoCo 3 needs a separate publication contract

C3 PDF 13 maps `$FF9D` bits 7–0 to Y18–Y11 and `$FF9E` to Y10–Y3.
For native video with horizontal offset zero, the derived base is
`(FF9D << 11) | (FF9E << 3)`, an eight-byte granularity. This is a physical
video-memory address, not an MMU-mapped CPU pointer. PDF 15 separately describes
the CPU's 8 KiB MMU mappings. Establish which physical bytes the renderer fills.

Compatibility mode uses SAM F bits for Y15–Y9; PDF 13 prescribes Y18–Y16 = 1
and the other offset bits zero, plus `$FF9C = $0F`. PDF 21 limits SAM display
mode/offset bits to compatibility mode. A native GIME publisher must not reuse
the CoCo 1/2 strobe routine and assume it controls the same display.

C3 PDF 11 identifies vertical-border enable as bit 3 of `$FF92`/`$FF93`,
with overall IRQ/FIRQ enables in `$FF90`. PIA field sync remains described
separately on PDF 9. A vertical-border event must not be treated as the same
edge or acknowledgement interface as PIA FS. The examined manufacturer pages
do not specify the GIME read-to-clear sequence, the exact base-latch instant,
or atomic adoption of the two offset bytes. They also do not give a safe
register-write budget relative to PIA FS or VBORD. These are unresolved hardware
contracts here, not facts supplied by recollection.

For a native experiment, use complete prepared images, keep horizontal/vertical
scroll and geometry fixed, and vary only the base. Use conservative aligned
bases rather than depending on the smallest possible step. Check both offset
bytes changing across the eventual latch point. Even a CPU word store would
not, by itself, establish hardware-level atomicity. Keep the old buffer intact
until adoption is observed or a validated conservative wait has elapsed.
Do not advertise native CoCo 3 tear-free publication from this reading alone.

### Emulator source explains a model, not silicon

The original [XRoar 1.12.1 release][xroar] was downloaded and verified against
SHA-256 `ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
Only `src/tcc1014/tcc1014.c` was extracted into this task's evidence directory;
its SHA-256 is
`fc6d038e022908cc4cf939a5a41ffdf7802bfeb9ae6f8f055cc64649f458c102`.
It matches the locally examined cadence-source copy byte for byte.

Static reading of lines 1012–1020 shows each offset-byte write recomputing Y.
In `do_vb_irq`, lines 1190–1254, FS rises at sync count 4, while B receives Y
(or the compatibility combination) at count 7. VBORD is raised at the end of
the active area. This is an explicit model in which writing a base and adopting
it are distinct events. It provides a useful phase-sweep hypothesis for an
emulator experiment. It does not settle the manufacturer-document gap, prove
1986/1987 physical GIME equivalence, or report a run performed here.

## Board scope and conflicts to preserve

- C1 covers original CoCo circuitry. C2 covers the named NTSC service-manual
  boards, not every CoCo 2 or PAL revision. C3 covers a different integrated
  video/memory circuit. C3 PDF 36–38 describes different NTSC/PAL oscillators
  and PAL encoding; a shared register name does not imply identical timing.
- C2 PDF 13 says F2 selects `$0400`. Its PDF 14 map and SAM PDF 15 bit diagram
  imply F1 = `$0400`, F2 = `$0800`. Use the independent diagrams for test
  vectors and retain this prose error. C2 PDF 11 calls the keyboard PIA IC15,
  whereas PDF 34 calls the PIAs IC2/IC7. Use register addresses here; resolve
  the exact schematic before naming a probe point on a physical board.
- The SAM advance sheet's FS-low sentence is absent from the other scan's
  equivalent paragraph. The vertical-preload description supplies additional
  detail but no numeric final-write margin. Do not silently merge editions
  into a stronger timing promise.
- C3 PDF 14 describes HVEN as a 128-byte screen width. The examined XRoar
  implementation sets a 256-byte stride in `do_vb_irq`. This conflict is
  outside a fixed, zero-horizontal-offset publication experiment. Do not
  use either value as a universal scrolling contract without resolving it.
- The Tandy maps label field sync nominally 16.667 ms. That rounded label is
  not the cadence experiment's exact event-tick interval, nor a PAL guarantee.

## Independent expectations and failure controls

These are proposed integration tests, not completed hardware validation.
Establish expectations before reading measured output, and keep at least two
prepared images distinguishable in every row and at the first/last byte.

<!-- markdownlint-disable MD013 -->

| Boundary | Independent expectation | Failure control |
| --- | --- | --- |
| Base encoding | From the SAM diagram: `$0400` sets only F1, `$2000` only F4, `$6000` F4/F5. From C3 PDF 13: `$60000` gives `$C0,$00`; `$62000` gives `$C4,$00`. | Reverse clear/set selection; shift by 8 rather than 9; swap GIME bytes. Require wrong visible image/base, not just a changed trace. |
| Scene RAM | Every hidden-buffer byte matches an independently constructed scene; front remains unchanged throughout drawing; guards survive. | One wrong last byte, overlapping buffers, or a draw into front must fail. |
| PIA events | Two reads of `$FF03` retain a pending flag; a data-selected `$FF02` read clears it; a later selected edge sets it again with IRQ delivery disabled. | DDR-selected read, other-port read, stale pending flag, and a competing acknowledgement must not masquerade as a fresh field. |
| Publication/reuse | In consecutive rendered frames, every active image equals one complete prepared scene. Old front stays intact until the new base is adopted. | Slow drawing, premature reuse, and delayed/multi-strobe writes spanning the boundary must expose errors or explicitly miss/defer publication. A late write need not tear on every model. |
| Progress | Ready scenes eventually appear; repeated old frames are allowed when work misses a deadline. | A frozen front buffer must fail even though every captured image is individually complete. |
| Emulated timing | Record fresh-edge, last register write, first fetch from the new base and renderer-frame timestamps. Compare measured adoption against a separately declared model expectation. | Phase sweeps on both sides of the boundary, skipped captures, and a deliberately late publisher distinguish stale flags from real synchronization. |
| Audio | Record DAC/mux events separately if audio is part of the eventual workload. | Interrupt/polling delays or shared PIA-bit damage must be detected by audio evidence, not inferred from video. |
| Physical output | Record board/VDG/GIME revision, video standard, clock, sync/register timing and captured consecutive output. | Repeat boundary cases on that board; emulator success alone cannot pass this row. |

<!-- markdownlint-enable MD013 -->

Start the CoCo 1 experiment with the cadence configuration: explicit `cocous`,
MC6809, MC6847, 32 KiB, NTSC, stock slow clock, no cartridge, nonzero initial
RAM and direct DECB load. Use `-c /dev/null`, absolute verified ROM paths, a
private bounded headless capture, frame skip zero, and declared renderer/palette.
For CoCo 2, declare an independently selected profile, VDG variant and RAM;
for CoCo 3, additionally declare GIME revision, compatibility/native mode,
physical RAM mappings and geometry. Those later configurations are not selected
or tested by this note. Never transfer CoCo 1's cadence constants to them.

## Reproduce the inspection and checks

The original Python below downloads only the three extra chip references when
missing; the four existing resources remain read-only. It verifies all seven
source hashes before rendering, rejects a deliberately corrupted input, and
writes exact PNG hashes to `page-images.json`. It uses the repository's prepared
virtual environment and no emulator or document-model downloads.

Extract this fenced block to the ignored `local/research/frame-publication/reproduce.py`
and run `uv run --no-sync python` on that path from the repository root.
Rendering is not a substitute for opening the page images.

```python
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import pypdfium2 as pdf

OUTPUT = Path("local/research/frame-publication")
SOURCES = {
    "coco1-technical": (
        "8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64",
        [13, 15, 28, 36],
    ),
    "coco2-service": (
        "7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447",
        [11, 13, 14, 30, 34],
    ),
    "coco3-service": (
        "5c4c82d1b825daacf861be097d93d0a0eff78fbdf394234d4adb06df0cfd3c29",
        [9, 11, 12, 13, 14, 15, 21, 36, 37, 38, 39],
    ),
    "sam": (
        "1f763b10cc548a9bfee755831c42de44c6e2b7cf26658f81a456f18f33820579",
        [8, 9, 15, 16, 17],
    ),
    "sam-advance": (
        "7d8913ee86fada3c4019e5b4e87742529f58bf0c22aec1397a9c19ebdad4728c",
        [15],
    ),
    "pia": (
        "ae4751e18a23facd324b6bdcd348e42c0e23a80a465c7950571aa5300efffd1c",
        [7, 8, 9, 10],
    ),
    "mc6847": (
        "2d4586d2fd3c82c60071bbe4cc3930e561c00dce1e43245b0c7ffd5e081fe88c",
        [8, 12],
    ),
}
EXTRA = {
    "sam": "MC6883 Synchronous Address Multiplexer (Motorola).pdf",
    "sam-advance": "MC6883 Synchronous Address Multiplexer Advance Information (Motorola).pdf",
    "pia": "MC6821 NMOS Peripheral Interface Adapter (Motorola).pdf",
}


def verify(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Source identity changed")


def inspect():
    from urllib.parse import quote

    OUTPUT.mkdir(parents=True, exist_ok=True)
    verified = {}
    for name, (expected, pages) in SOURCES.items():
        source = (
            OUTPUT / f"{name}.pdf"
            if name in EXTRA
            else (Path("local/references") / name / "source.pdf")
        )
        if not source.exists() and name in EXTRA:
            url = (
                "https://colorcomputerarchive.com/repo/Documents/Datasheets/"
                + quote(EXTRA[name])
            )
            with urlopen(url, timeout=60) as response:
                data = response.read()
            verify(data, expected)
            source.write_bytes(data)
        data = source.read_bytes()
        verify(data, expected)
        try:
            verify(data + b"corrupt", expected)
        except ValueError:
            pass
        else:
            raise AssertionError("Corruption control did not fail")
        verified[name] = (source, pages)
    images = {}
    for name, (source, pages) in verified.items():
        with pdf.PdfDocument(source) as document:
            for number in pages:
                path = OUTPUT / f"{name}-{number}.png"
                document[number - 1].render(scale=1.5).to_pil().save(path)
                images[path.name] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    (OUTPUT / "page-images.json").write_text(
        json.dumps(images, indent=2) + "\n"
    )
    print(
        f"Verified {len(verified)} PDFs; rendered {len(images)} cited pages; "
        "controls passed"
    )


if __name__ == "__main__":
    inspect()
```

The inspection passed for seven PDFs and 32 cited page images, including the
corrupted-source rejection controls. The resulting `page-images.json` SHA-256
is `23d84225e70ac219d35d05fc30f3169c5f9f8cd2288778f20ee4e3dc73e1474c`.
Image bytes depend on PDFium/Pillow versions; source PDF hashes are the stable
identity check. The JSON maps every cited image name to its exact PNG hash.

Installed ROMs were read and verified with `roms.verify_installed` for
`coco1`, `coco2` and `coco3`. All matched [roms.json](../roms.json), including
Disk BASIC; the exact hashes are in ignored `rom-verification.json`.
This is firmware integrity evidence, not boot or publication evidence.

Scoped checks run for this document are the extracted inspection snippet, `uv
run --no-sync pytest scripts/roms_spec.py -k 'not launch_boundary' -q`, Ruff
check/format (80-column formatting) on the extracted original snippet, and
Markdown fix/check on this file. The firmware suite passed 20 tests, with 55
launch-boundary cases deselected. No runtime, renderer, emulated timing,
audible-output or physical publication result is claimed. Parent integration
owns implementation and review.

[c1]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[c2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20%2826-3134%20%26%2026-3136%29%20%28Tandy%29.pdf
[c3]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf
[sam]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6883%20Synchronous%20Address%20Multiplexer%20%28Motorola%29.pdf
[advance]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6883%20Synchronous%20Address%20Multiplexer%20Advance%20Information%20%28Motorola%29.pdf
[pia]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6821%20NMOS%20Peripheral%20Interface%20Adapter%20%28Motorola%29.pdf
[vdg]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20%28Motorola%29.pdf
[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
