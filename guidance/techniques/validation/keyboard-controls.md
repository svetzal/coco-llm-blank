# Keyboard matrix to movement and action

Read this when adapting the logical policies in
[controls and collision](../controls-and-collision.md) to a CoCo 1/2
PIA scanner. The [original experiment](../../../experiments/keyboard-controls/main.asm)
reads the emulated keyboard matrix, moves a bounded position and counts rising
space-key edges. It is a finite integration experiment, not a playable game.

## Contract and source facts

The experiment selects CoCo 1 `cocous` and CoCo 2B `coco2bus`, NTSC, 32 KiB,
6809, stock emulated clock, no cartridge, direct DECB loading, null UI and null
audio. These are experiment choices, not owner-confirmed hardware choices.
`-no-ratelimit` removes host pacing; no program write accelerates the CPU.
`-no-c` prevents loading personal XRoar configuration. The runner supplies
explicit machine, CPU, keyboard layout, RAM, video standard and verified
absolute ROM paths. It does not modify the shared `local/PROJECT.md`.
The CoCo 2B emulator profile is not proof for every board in the service manual.

The following primary pages were directly examined as images for this work:

- Tandy, [Color Computer Technical Reference Manual][c1], PDF 13, 36–37,
  40 and 75 (printed 6, 29–30, 33 and schematic sheet 3/68). Port B strobes
  columns; port A reads rows. `$FF00` has seven keyboard bits and a joystick
  comparator bit. `$FF02` has eight column bits. Control-register bit 2
  selects data when set and DDR when clear. The diagram places the selected
  controls on PA3 and columns PB5/PB6/PB7. Sheet 3 mislabels the lower port's
  pins PA rather than PB; the register map, pin numbers and PIA diagram
  resolve that discrepancy for this use.
- Tandy, [Color Computer 2 NTSC Service Manual, 26-3134/3136][c2], PDF/printed
  11, 35–36. Figure 4-10 independently places left, right and space at
  (PA3,PB5), (PA3,PB6), (PA3,PB7). M is (PA1,PB5). The prose specifies
  one low column with all other columns high and a low row for a pressed key.
  PDF 11 calls the PIA IC15 while the keyboard description calls it IC7;
  this experiment uses the register roles, not component-label assumptions.
- Motorola, [MC6821 Peripheral Interface Adapter datasheet][pia], PDF/printed
  7–8, sections "PIA Peripheral Interface Lines" and "Internal Controls".
  DDR bits are zero for inputs and one for outputs. Control bit 2 selects
  the data register when one, DDR when zero. This supplies the initialization
  detail missing from the Tandy passages. The downloaded PDF SHA-256 is
  `1fa14d31bb39172610d63fd05ee6624cca50c7adb8ec3114579e7018222c3872`.
- Larry Landwehr, ["Read the Keyboard in Assembly," Hot CoCo, October 1983][article],
  printed/PDF 106. Its table and listing use column bytes `$DF`, `$BF`, `$7F`
  for left, right and space and compare full row bytes. The M prose says 233
  while the table gives 223. No historical listing is copied here.

The [independent hardware review](../research/input-hardware.md) records manual
hashes, wider board comparisons and missing physical evidence. Its matrix
transcription corroborates the literal expectations; expected game positions
come from the stated policy below, not from reading back implementation output.
The Motorola PDF is an additional directly examined primary source.

Derived scan constants are `$DF`, `$BF`, `$7F` (one zero column bit) and `$08`
(PA3 only). The assembly sets DDRA to zero and DDRB to `$FF`, preserving other
control bits while changing bit 2. Each scan restores all columns high. It
masks PA3 rather than comparing the entire input byte. PA0/PA1 overlap joystick
fire inputs and PA7 is the comparator; none is used as a movement/action bit.
Reading PIA data can acknowledge interrupt flags. This standalone experiment
masks CPU IRQ/FIRQ and makes no claim of transparent integration with a ROM
interrupt handler, joystick conversion or sound player.

## Original adaptation and bounds

`main.asm` samples left, right and space before deciding anything. Its logical
bits are 1, 2 and 4. Startup seeds previous input, suppressing startup-held
space. Held left/right moves one cell per update; both directions cancel.
Space increments an action count only on a rising edge. Input history updates
even when movement is blocked. The position starts at 2, accepts 0 through 4,
and rejects candidates -1 and 5. Returning from either boundary remains possible.
These are original adaptations of the
[existing host model](controls-collision.md), not hardware rules.

There is one startup sample and exactly 16 updates. No elapsed-time cadence,
repeat timer, debounce or rendering is implemented. Code and initialized state
start at `$3000`; the runner requires `program_end < $4000`. The 16 seven-byte
records occupy `$4000..$406F`; the stack starts at `$7F00` and has the separate
`$7E00..$7EFF` reservation. No ROM calls occur after entry. The binary's entry
point is explicitly `start`. RAM begins nonzero with XRoar `-ram-init set`.

The tracked event file supplies key names; F means the space key. The startup
line is F. The independent expected update outcomes are:

| Update | Keys held | Position | Total actions | Purpose |
| --- | --- | --- | --- | --- |
| 1 | F | 2 | 0 | Startup-held action suppressed |
| 2 | None | 2 | 0 | Release |
| 3 | R+F | 3 | 1 | Movement and action together |
| 4 | R+F+M | 4 | 1 | Hold; unrelated row must not become left |
| 5 | R+F | 4 | 1 | Blocked hold |
| 6 | R | 4 | 1 | Release action while blocked |
| 7 | R+F | 4 | 2 | Repress while blocked |
| 8 | R+F | 4 | 2 | Blocked hold must not repeat |
| 9 | L+F | 3 | 2 | Return while action remains held |
| 10 | L | 2 | 2 | Release action while moving |
| 11 | L+F | 1 | 3 | Repress while moving |
| 12 | L+R+F | 1 | 3 | Opposing directions cancel |
| 13 | None | 1 | 3 | Release all |
| 14 | L | 0 | 3 | Left repress |
| 15 | L | 0 | 3 | Left boundary blocks hold |
| 16 | R | 1 | 3 | Return from left boundary |

## Actual injection boundary

The installed XRoar manual's Keyboard options section says `-type` intercepts
ROM calls to type into BASIC. That is not a PIA keyboard test. This experiment
instead builds [XRoar 1.12.1's release source][xroar] locally, with checksum
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
No global installation or GUI launch occurs.

The tracked `key_hook.c` adds a call in `xroar.c:handle_trap`. At the scanner's
symbol-derived PC it calls XRoar `keyboard_press` / `keyboard_release` using
`DSCAN_LEFT`, `DSCAN_RIGHT`, `DSCAN_SPACE` and `DSCAN_M`. Repeated lines retain
the keys without release/repress. The hook never writes CPU registers, PIA
registers, emulated RAM or logical button states. The decoded records include
three raw PIA reads, logical held bits, position, action count and history.

Directly inspected upstream files in that release establish the path:

- `src/keyboard.h`: `keyboard_press` and `keyboard_release` change keymap-selected
  matrix contacts and notify the machine.
- `src/keyboard.c`: `keyboard_read_matrix` resolves row/column connections,
  including its ghosting model.
- `src/dragon/dragon.c`: `pia0a_data_preread` calls `dragon_keyboard_update`,
  which passes PIA output state to the matrix and stores resulting input sinks.
- `src/mc6821.c`: DDR/data selection and PIA reads remain upstream code.
- `src/xroar.c`: traps normally disable after their configured range;
  `-trap-range 1-17` retains all required sample triggers.

Thus this tests emulated key contacts through XRoar's real matrix/PIA path and
6809 code. It does not test OS key events, host layout translation, focus,
USB keyboard rollover, switch bounce or physical hardware.

## Reproduction and failure controls

From the repository root with the locked environment and native assembler
already prepared (`uv sync --locked` in a fresh checkout):

```sh
uv run --no-sync python scripts/doctor.py --profile demo --target coco1
uv run --no-sync python scripts/doctor.py --profile demo --target coco2
uv run --no-sync python experiments/keyboard-controls/prepare.py
uv run --no-sync python experiments/keyboard-controls/keyboard_run.py --target coco1
uv run --no-sync python experiments/keyboard-controls/keyboard_run.py --target coco2
COVERAGE_FILE=build/keyboard-controls/.coverage \
  uv run --no-sync pytest experiments/keyboard-controls \
  --cov=keyboard_run --cov-branch --cov-report=term-missing \
  --cov-report=json:build/keyboard-controls/coverage.json -q
uv run --no-sync ruff check experiments/keyboard-controls
uv run --no-sync ruff format --check experiments/keyboard-controls
markdownlint --fix guidance/techniques/validation/keyboard-controls.md
markdownlint guidance/techniques/validation/keyboard-controls.md
```

Preparation downloads only the pinned source archive to ignored
`build/keyboard-controls/`, verifies its checksum, extracts a fresh tree,
applies the original hook and builds without GTK/SDL. It needs a working C
compiler and make; it does not install them. Configure and make each have a
240-second host limit. Each emulator run has a ten-second emulated deadline
and a 30-second host deadline. ROM verification precedes every launch.
Both public commands parse help and invalid arguments before doing work.

The runner saves exact arguments, binary, same-build symbols, log, raw RAM,
decoded records and binary/emulator/ROM hashes in a separate directory per
case. A successful process exit is insufficient: a fresh 32 KiB snapshot,
completion marker, update count and exact key-hook sample count are required.
Normal command-line checks also require every expected record to match.

A source-integrity test compares the extracted keyboard, matrix and PIA files
with the verified release archive and requires exactly the tracked hook in
trap dispatch. The suite runs these failure controls on both targets:

- `--variant WRONG_COLUMN` scans PB4 for left. Returning from the wall fails.
- `--variant WRONG_SELECT` leaves control B bit 2 clear. Column writes hit DDR
  instead of data, and the expected input sequence fails.
- `--variant HELD_FIRE` counts held space repeatedly, including startup hold.
- `--variant STALE_HISTORY` returns early on blocked movement. It misses the
  action repress because the blocked release was forgotten.
- `--no-injection` leaves the real scanner active with no key events. All
  sixteen records remain idle at position 2 with zero actions.

A separate CoCo 1 `--unreachable` check uses a PC trap at `$2000` and requires
no snapshot. Correct runs also compare writable control bits before/after and
require all columns restored high. The M-key observation requires PA1 to change
without changing the left action. These are bounded checks, not proof that all
keys or chords work. Negative-control CLI runs report mismatch rather than
exiting in failure; the tests assert their specific wrong outcomes.

## Results and limits

The first instrumented run used the default one-shot sample trap. Only the
startup F event reached the matrix and all sixteen records remained at position
2 with zero actions. The independent checker rejected it. Generated evidence
is retained in `build/keyboard-controls/initial-one-shot-trap/`. The fix was to
request 17 trap occurrences; the event count is now checked explicitly.

The original pre-review scoped run passed 19 tests on macOS with Python 3.13.12 and the
instrumented XRoar 1.12.1. Both profiles matched all 16 literal records, ending
at position 1 with exactly three actions. All four broken variants were
rejected on both profiles; no-injection and unreachable-trap controls passed.
Runner statement/branch coverage was 94.38% (77 statements, 12 branches).
Ruff check/format and Markdown fix/check passed. The full starter suite was
not run for this isolated addition.

Coverage measures the Python run/check module only, not C or 6809 instructions.
Preparation is exercised as a real build; Python coverage does not claim to
cover its download/build branches. Generated evidence and downloaded sources
are ignored; the scanner, injector, event sequence, oracle and tests remain
in the assigned experiment directory.

No display, framebuffer rendering, audible output, disk loading or physical
machine check was performed. There is no settling-time or cycle-budget result.
The sample hook deliberately holds keys across complete scans; asynchronous
changes during a scan, rapid taps and contact bounce remain untested. Three
same-row controls are covered; broader matrix ambiguity and joystick/audio
coexistence remain outside this experiment. Do not advertise CoCo 3 support.

Parent integration should link this note alongside the logical-controls guide
and the independent hardware research. A game must choose a real update cadence,
coordinate PIA/interrupt ownership and provide a visible response before this
becomes a playable control system. Shared indexes and production scripts were
not changed by this implementation task.

[c1]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[c2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20%2826-3134%20%26%2026-3136%29%20%28Tandy%29.pdf
[pia]: https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Motorola/Motorola%206821.pdf
[article]: https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=106
[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz

## Publication review correction

A failed rerun could leave a previous successful `result.json`. Each attempt
now invalidates old results, snapshots, binaries and logs before firmware or
assembly work, and records explicit failure diagnostics. Two regressions run a
successful case before an assembler failure or empty-event failure and require
failed status with no stale snapshot. The revised run passes 21 tests with
97.06% runner coverage. Original retained captures describe the earlier runner;
these changes affect evidence handling, not the scanner or key sequence.
