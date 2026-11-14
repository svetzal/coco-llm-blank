# CoCo keyboard and shared input hardware

Use this note when selecting game keys or reviewing a direct PIA scanner.
These are primary-source findings and proposed validation cases, not emulator
or physical-hardware results. No historical program listing was copied or run.

## Examined sources

PDF page numbers below are one-based, including covers. The local PDF bytes
were hashed and the cited pages read as rendered images, including the tables
and matrix diagrams. Archive links identify the source; hashes identify the
particular scans examined.

| ID | Tandy manual and scope | PDF pages = printed pages examined for input |
| --- | --- | --- |
| C1 | [Color Computer Technical Reference Manual][c1], original CoCo circuitry | 13 = 6; 36–38 = 29–31; 40 = 33; 75 = 68 (schematic sheet 3) |
| C2 | [Color Computer 2 NTSC Service Manual][c2], catalog 26-3134/3136 | 11 = 11; 34–38 = 34–38 |
| C3 | [Color Computer 3 Service Manual][c3], NTSC/PAL, catalog 26-3334 | 9 = 9; 39–43 = 39–43 |

[c1]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[c2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20%2826-3134%20%26%2026-3136%29%20%28Tandy%29.pdf
[c3]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf

SHA-256, in source order:

```text
C1 8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64
C2 7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447
C3 5c4c82d1b825daacf861be097d93d0a0eff78fbdf394234d4adb06df0cfd3c29
```

This is not coverage of every CoCo 1 revision, CoCo 2 PAL board, replacement
keyboard, or joystick adapter. Component numbers must not be transferred
between boards.

## Source statements applicable to a scanner

C1 PDF 40, C2 PDF 36 §4.8 and C3 PDF 40 §5.6 describe the same operation:
configure port B as outputs and port A's seven keyboard lines as inputs.
Select one column by writing zero to its bit and ones to the other seven.
A pressed key returns zero on its row. Scan the columns separately.

The memory maps (C1 PDF 13, C2 PDF 11, C3 PDF 9) establish:

| Address/bit | Function |
| --- | --- |
| `$FF00`, bits 0–6 | Keyboard rows 1–7 (PA0–PA6) |
| `$FF00`, bit 7 | Joystick comparator input, not an eighth keyboard row |
| `$FF02`, bits 0–7 | Keyboard columns 1–8 (port B) |
| `$FF01`, bit 2 | 0 selects DDR at `$FF00`; normally 1 for data |
| `$FF03`, bit 2 | 0 selects DDR at `$FF02`; normally 1 for data |
| `$FF01` / `$FF03`, bit 3 | Analog multiplexer selects SEL1 / SEL2 |
| `$FF01` / `$FF03`, bits 0–1 | Horizontal / vertical sync interrupt setup |

The PIA descriptions say reset establishes direction, normally left unchanged
(C1 PDF 36–37; C2 PDF 34–35; C3 PDF 39, 41). These passages specify the required
input/output directions but do not supply a complete DDR initialization recipe
or DDR bit-polarity table. Consult a primary MC6821 register description before
introducing new initialization code. Do not treat a write to `$FF02` as a column
strobe until control bit 2 is known to select data.

### Matrix facts and board differences

The diagrams are C1 PDF 75, C2 PDF 36 figure 4-10, and C3 PDF 40 figure 5-9.
Coordinates below use zero-based **port bit** indices, not the manuals'
one-based row/column names. They are a transcription of wiring, not ASCII or
host-key codes.

| Keys | Input row | Output column bits, in key order |
| --- | --- | --- |
| A, B, C | PA0 | PB1, PB2, PB3 |
| W | PA2 | PB7 |
| X, Y, Z | PA3 | PB0, PB1, PB2 |
| Up, Down, Left, Right, Space | PA3 | PB3, PB4, PB5, PB6, PB7 |
| Enter, Clear, Break | PA6 | PB0, PB1, PB2 |
| Either Shift | PA6 | PB7 |
| Alt, Ctrl, F1, F2 (C3 only) | PA6 | PB3, PB4, PB5, PB6 |

C1 and C2 leave the four C3-only positions empty. The two Shift switches share
one matrix position, so a scanner cannot distinguish left Shift from right
Shift. C3 labels the Break position ESC/BREAK.

C1 calls the keyboard PIA U8. C2's keyboard description and matrix call it IC7;
C3 calls it IC5. C1 uses separate converter/multiplexer circuitry (PDF 37–38);
C2 and C3 describe a custom DAC chip with joystick comparison and sound
selection (C2 PDF 37–38; C3 PDF 42–43). Shared register roles do not imply
identical analog circuitry.

### Joystick and audio interactions

C1 PDF 37 explicitly says the fire switches ground inputs normally high and
warns of conflicts with keyboard rows 1 and 2. The memory maps assign right
fire to PA0 and left fire to PA1. C3 additionally assigns right switch 2 to PA2
and left switch 2 to PA3 (PDF 9, corroborated by PDF 39's pins 2–5).

The analog select lines control both joystick selection and sound routing.
C1 PDF 38 table 4, C2 PDF 37's table and C3 PDF 43's table agree: SEL2/SEL1
values 00, 01, 10, 11 select DAC, cassette, cartridge, and unused/no sound,
respectively, when sound is enabled. C2/C3 name the columns Sel B/Sel A.
Joystick position conversion also uses the DAC as the comparator reference
(C1 PDF 37; C2 PDF 37–38; C3 PDF 42–43).

**Adaptation:** keep keyboard scanning confined to column data and row reads
once direction is established. Preserve multiplexer and interrupt configuration
when changing control bit 2. Coordinate joystick analog conversion with audio:
restoring only the keyboard column byte cannot restore changed DAC values or
sound routing. This is a software ownership requirement derived from shared
hardware, not a measured timing or audio-quality result.

## Simultaneous inputs and limits

The examined matrix drawings show switches without per-key isolation diodes.
The examined prose does not promise N-key rollover, specify a maximum safe
chord, or describe a software anti-ghosting algorithm.

**Deduction:** three closed corners of a two-row/two-column rectangle can join
rows and columns through unintended paths. A+B+I, for example, occupies
(PA0,PB1), (PA0,PB2), (PA1,PB1); J is the fourth corner (PA1,PB2).
Use this as an ambiguity probe. It is not a claim that every board or emulator
will return J: actual thresholds, output drive, contact resistance and emulator
matrix modeling require separate evidence. Software cannot reconstruct the
true switch set from electrically indistinguishable readings.

**Adaptation:** define supported chords explicitly. Test two keys on one row,
two on one column, and cross-row pairs before choosing movement-plus-action
controls. Do not collapse several selected columns into one read when identity
matters. Normalize keyboard input with `(~rows) & 0x7f` only after a valid scan;
this is a derived expression, not copied historical code.

**Deduction:** a grounded fire input can look like a key in each selected
column of that row. An all-columns-high read can help identify a fire button,
but cannot recover keyboard information hidden by the grounded row. Decide
whether the game supports concurrent joystick fire and keyboard controls on
those rows; do not silently advertise universal simultaneous input.

## Conflicts and unresolved details

- C2 PDF 11 labels the PIA IC15; PDF 34–36 identify IC7. The register addresses
  and scan description agree, but the component label does not. Use the actual
  board schematic for repair or pin probing.
- C1 PDF 75 labels the lower PIA port pins PA0–PA7, although its prose assigns
  columns to port B and its block diagram (PDF 36) calls pins 10–17 PB0–PB7.
  Use pin numbers and register roles to reconcile this drawing error.
- The PIA prose lists CA2/CB2 with pins 19/39 in that order (C1 PDF 37,
  C2 PDF 35, C3 PDF 41). The block diagrams assign CA2 to 39 and CB2 to 19.
  Do not copy the prose's order into a pin-level interface.
- C2 PDF 11 and C3 PDF 9 also label PB6 as RAM-size output. Do not turn that
  label into a board-independent memory-control operation without tracing
  the selected board's circuit.
- No measured debounce interval, settling delay, ghosting behavior, interrupt
  side effects, or host-key translation coverage is established here.

## Target-input validation checklist

These are proposed acceptance checks, not completed runtime results.

- Record model, board/video standard, RAM, keyboard, joystick model/buttons,
  clock and loader. For emulation, record XRoar version and host-key mapping.
  Verify ROM bytes through the repository's verifier; use explicit absolute
  ROM paths and isolated machine configuration before any launch.
- Verify port A input and port B output direction and data-register selection.
  Include a failure control with wrong DDR/data selection, without driving
  physical input lines against peripherals.
- With no keys/buttons, require keyboard bits 0–6 high in every column. Change
  comparator input independently and require no spurious keyboard action.
- For every supported key, check its independently transcribed matrix position,
  press, hold, release, and press again. Observe raw scan and game action
  separately. Verify Shift sharing and C3-only keys on the correct target.
- Check each supported chord, same-row and same-column pairs, opposing movement
  keys, and the A+B+I ambiguity probe. Record raw per-column bytes; report
  emulator observations separately from a physical board's results.
- Test each fire button with all columns high, then during a full keyboard
  scan. Include both fire buttons and C3 second buttons. Specify the game's
  policy for a fire button that masks a keyboard row.
- Compare control/direction state before and after the scan. Test audio routing
  and analog joystick sampling together; require the owning routine's intended
  state to be restored, including DAC data where relevant.
- Test short taps and contact bounce separately from held-key repeat. An
  injected host event proves only the injection path unless the assembly
  scanner and resulting game action are observed too.

## Reproduce the source inspection

Use the linked archive PDFs as `source.pdf` in the existing ignored reference
folders named below. Do not replace shared converted text or indexes. This
original snippet verifies identity and renders only the cited pages; it has no
emulator dependency. Run from the repository root with the prepared project
virtual environment (`uv run --no-sync python` and the body below).

```python
from hashlib import sha256
from pathlib import Path

import pypdfium2 as pdf

sources = (
    ("coco1-technical",
     "8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64",
     (13, 36, 37, 38, 40, 75)),
    ("coco2-service",
     "7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447",
     (11, 34, 35, 36, 37, 38)),
    ("coco3-service",
     "5c4c82d1b825daacf861be097d93d0a0eff78fbdf394234d4adb06df0cfd3c29",
     (9, 39, 40, 41, 42, 43)),
)
output = Path("local/research/input-hardware")
output.mkdir(parents=True, exist_ok=True)
for name, expected, pages in sources:
    source = Path("local/references") / name / "source.pdf"
    if sha256(source.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Source identity changed: {name}")
    with pdf.PdfDocument(source) as document:
        for number in pages:
            document[number - 1].render(scale=2.5).to_pil().save(
                output / f"{name}-{number}.png"
            )
    print(f"{name}: verified source; rendered {len(pages)} pages")
```

Open each PNG with an image-reading tool. Rendering success alone does not
establish that a diagram was read correctly. No runtime, audible, or physical
hardware evidence is claimed. Parent integration should link this note from
the eventual input guide and use its source coordinates as independent test
expectations; shared indexes and production scripts are outside this task.
