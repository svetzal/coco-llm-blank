# CoCo 2 cooperative sound, input and drawing

Use this evidence when deciding whether small foreground work can coexist with
a software-driven DAC on a defined non-T1 CoCo 2. It closes the missing CoCo 2
runtime measurement for this bounded technique. It does not establish a
constant-rate player or validate audible output.

The [retained experiment](../../../experiments/sound-coco2/README.md) adapts the
repository's original sound-slots code and DAC-timestamp method. It adds an
explicit CoCo 2 target and a delayed-work control. The sources were not edited.

## Target and examined hardware sources

The board family is Tandy **26-3134/26-3136 NTSC**, as named by its service
manual, with the documented 64 KiB upgrade, MC6809E and original MC6847.
No particular PCB serial number or later T1 revision is claimed. The task
requires CoCo 2; 64 KiB and this board family are experiment choices.
Code uses only lower RAM. The emulator contract is XRoar 1.12.1 `cocous`,
explicit `-ram 64 -tv-type ntsc -vdg-type 6847 -machine-cpu 6809`, no cartridge,
nonzero startup RAM and direct DECB auto-run. `-c /dev/null` excludes user
configuration; null UI/audio excludes GUI and listening evidence.

Color BASIC 1.2 (`bas12.rom`) and Extended Color BASIC 1.1 (`extbas11.rom`) pass
`roms.verify_installed` before launch. Exact digests are in each generated
`contract.json`. Assembly writes `$FFD6` and `$FFD8` to clear both CPU-rate
bits. XRoar's examined event rate is 14,318,180 ticks/s and its continuing
slow cycle is 16 ticks, giving 894,886.25 modeled cycles/s. Host acceleration
changes neither this clock nor the measured intervals.

The following primary passages were directly examined as page images:

- Tandy, [Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)][service],
  PDF/printed 8: 16K DRAM configuration and 64K upgrade; SAM supplies timing
  and addressing. PDF/printed 11–12: `$FF00` bit 0 is the right joystick switch;
  `$FF01/$FF03` bit 3 selects the mux; `$FF20` bits 7–2 are the DAC;
  `$FF21/$FF23` bit 2 selects data versus direction; `$FF23` bit 3 enables
  six-bit sound. PDF/printed 13–14: SAM strobes, display offset and CPU rate;
  the text specifies 0.89 MHz and clearing R0/R1. The offset prose says F2
  for `$0400`, but the diagram's half-KiB offset requires binary 2, F1.
  The implementation follows that diagram and the independently checked
  original technical reference, writing `$FFC9` and clearing the other bits.
- Same manual, PDF/printed 26, figure 4-3: MC6809E read/write timing at
  0.89 MHz. PDF/printed 31, section 4.4: IC8 is MC6847, display data comes
  from DRAM through SAM addressing, with PIA-controlled mode inputs.
- Same manual, PDF/printed 35–38: keyboard column outputs and row inputs,
  shared joystick fire inputs, six-bit DAC input, sound enable, and the
  custom IC3 DAC/multiplexer. Page 37's selection table maps `00` to DAC;
  page 38 describes successive software values and high SNDEN for sound.
  This custom analog circuit differs from the original CoCo resistor DAC.
  No original-CoCo voltage formula is transferred to this board.
- Tandy, [Color Computer Technical Reference Manual][technical], PDF 13–15
  (printed 6–8), register and SAM diagrams; PDF 31 (printed 24), mode table:
  256×192 uses SAM `110` and PIA bits 7–4 set. PDF 37 (printed 30) explains
  normally high, grounded-on-press fire switches. These were cross-checked
  with the named CoCo 2's hardware passages above, not used as sole board proof.
- Inman, Inman and Dymax, [Assembly Language Graphics][graphics], PDF 107
  (printed 98): eight consecutive graphic elements per byte, zero black and
  one green in color set zero. Hence 32 bytes/row, 192 rows, 6,144 bytes.
  A whole `$FF` marker byte does not depend on a guessed horizontal bit order.

The CoCo 2 memory-map pages label PIAs IC14/IC15, while the manual's circuit
sections identify IC2/IC7. This note preserves that inconsistency. The register
addresses and functional connections agree; the IC labels are not used to
claim an independently checked schematic netlist.

## Examined emulator source and measurement method

The checksum-pinned [upstream XRoar 1.12.1 archive][xroar] was extracted and
built privately. No installed emulator was changed. Examined passages:

- `src/xroar.c`, machine definitions: `cocous` uses CoCo NTSC architecture;
  `coco2bus` explicitly selects `6847t1` and is not this target.
- `src/events.h`, `EVENT_TICK_RATE`; `src/mc6883.c`, `mc6883_mem_cycle`:
  event frequency and slow-cycle tick count.
- `src/dragon/dragon.c`, `cpu_cycle`: advance the SAM-derived clock before
  device access. `src/mc6821.c`, `mc6821_write` and `mc6821_update_a_state`:
  update port state before invoking the postwrite callback.
- `src/dragon/coco.c`, `pia1a_data_postwrite_coco`: the logger runs immediately
  before `sound_set_dac_level`. Filter records to PC `sample + 3`, require
  data-register selection and DAC output direction, then retain all writes,
  including repeated values. Initialization callbacks are excluded.
- `src/mc6809/mc6809.c`, short branches, LEAX, indexed-address calculation
  and immediate LDX paths: the added delay costs 3 + 10,000 × (5 + 3) =
  80,003 slow cycles. This predicts the control before comparing its result.

Intervals are adjacent event-tick differences modulo 2^32, divided by 16.
Every observed gap must be positive and divisible by 16. Timing begins at the
first accepted DAC write and ends at the last, without inferred edge intervals.
These are modeled DAC update times, not instruction counts, host time,
audio-buffer times or physical oscilloscope readings.

## Original adaptation and independent expectations

The assembly keeps interrupts masked, adds pitch to a 16-bit phase, emits the
upper six bits, then services input and drawing every 256 writes. The marker
moves one byte across row 96, erasing the old position. It wraps after 32
application updates. Screen `$0400–$1BFF`, guards `$03FF/$1C00`, code/state
`$3000` to the emitted `state_end`, and stack reserve `$7E00–$7EFF` are disjoint.
The runner rejects code/state reaching `$4000`. It initializes all state.

The existing independently expressed Python phase, button and framebuffer
oracle in `examples/sound-slots/expected.py` is reused unchanged. It computes every
expected sample, exact sample/frame counts, button and pitch, zero phase at
block boundaries, marker position and all 6,144 framebuffer bytes. Expectations
are not derived from captured RAM, output logs or assembly tables.

Frames 1, 16, 17, 32, 33, 63 and 64 cover release, hold, press, return to release,
and marker wrap. Scripted input is a substitution after a real PIA read;
it does not inject an electrical or host keyboard event. The normal case
checks the emulator's undriven input. An unreachable data-label trap must never
produce a snapshot. Missing instrumented samples fail even with valid RAM.

The delayed-work control adds a finite foreground loop. It must produce the
same samples and final state as the scripted case, the same inner-loop minimum,
a maximum over 100 times larger, and exactly 63 × 80,003 × 16 additional ticks
between first and last writes. There are only 63 inter-block gaps in 64 blocks;
the final foreground delay lies outside that span.

## Measured result

On 2026-11-14, all three cases passed all seven checkpoints. Each final run
emitted 16,384 samples and supplied 16,383 intervals across 64 application
updates. These updates are not video frames and are not synchronized to VDG.

| Case | Minimum cycles | Maximum cycles | Mean cycles | Span seconds |
| --- | ---: | ---: | ---: | ---: |
| Released input | 57 | 138 | 57.311481 | 1.049222 |
| Scripted input | 57 | 158 | 57.382531 | 1.050522 |
| Delayed scripted input | 57 | 80,161 | 365.030031 | 6.682734 |

The complete histograms in slow cycles are:

- Released: 16,320 intervals at 57 and 63 at 138.
- Scripted: 16,320 at 57, 32 at 155 and 31 at 158.
- Delayed: 16,320 at 57, 32 at 80,158 and 31 at 80,161.

The delay adds exactly 80,643,024 event ticks across the measured span.
It preserves functional correctness while making sample delivery much worse.
That is the useful result: a correct framebuffer and phase sequence do not
establish a suitable sample schedule. Budget input and drawing work between
DAC services; remeasure after increasing the workload. Do not promise a
constant pitch from this uneven cooperative schedule.

Generated evidence is under `build/sound-coco2/measured/`; the independent test
run uses `build/sound-coco2/pytest/`. Each includes commands, same-build symbols,
logs, RAM and result JSON. Private upstream source and build logs remain under
`local/research/sound-coco2/`. Reproduction commands are retained with the
experiment; no downloads or generated evidence are tracked.

## Verification

The original pre-review experiment test run passed 18 tests in 22.15 host seconds,
with 98.10% combined statement and branch coverage of the scoped Python
package. It repeated all 21 instrumented launches and checked damaged-evidence
rejections. An installed, uninstrumented XRoar reached the valid first-frame RAM
checkpoint but was rejected for missing DAC records. The unreachable data-label
trap produced no snapshot in every positive run. Tick-wrap handling and refusal
to overwrite an existing run were also checked.

Ruff lint and formatting checks, Markdown automatic fixing and subsequent
checking, and scoped whitespace checks passed. The full starter suite was not
run. Tests used an isolated coverage file and temporary/output directories;
the shared Python environment was not synchronized. This pass reused verified
installed ROMs and the cached, checksum-verified upstream archive, then rebuilt
the instrumentation in a separate source tree. It was not a fresh-clone setup
test. Host tools were Python 3.13.12, LWTOOLS 4.25 and XRoar 1.12.1 on macOS.

## Limits and integration

No audible output, audio quality, analog voltage, rendered display, physical
button, physical board, PAL, T1, 6309, fast clock or disk-loading result is
claimed. Framebuffer checks establish memory drawing only. This finite sample
window is not a worst-case bound for other workloads. Interrupts are masked;
ROM services and analog joystick conversion are not exercised.

The parent can link this note from the existing sound guide and coverage index.
Those shared files and production scripts were left unchanged. No commit,
branch, push, global install or unrelated process operation was performed.

[service]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf
[technical]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[graphics]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf
[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz

Publication review independently reproduced every retained interval. The runner
now also requires the exact added delay at each of the 63 boundaries, rather
than only the total. A regression shifts one sample block by one cycle, keeping
the total unchanged, and requires rejection. The revised scoped run passes
19 tests with 98.13% coverage; measured intervals remain unchanged.
