# Validate modeled audio output

Use this after [DAC timing checks](audio-timing.md) when the question
is whether the modeled audio route actually produces a waveform. The private
capture now establishes that boundary for the original sound-slots program and
its [CoCo 2 adaptation](sound-coco2.md). It does not establish host
speaker output, listening quality or physical CoCo output.

## Hardware and upstream boundary

Primary hardware passages inspected as page images for this experiment:

- Tandy, [Color Computer Technical Reference Manual][technical], PDF 38
  (printed 31), table 4 and figure 11: the six-bit DAC feeds the MC14529B mux;
  SNDEN high and both selects low route DAC sound to the modulator. The
  cassette output is a different route. PDF 13 (printed 6) identifies the
  mux select bits in the PIA control registers.
- Tandy, [Color Computer 2 NTSC Service Manual, 26-3134/26-3136][service],
  PDF/printed 37–38: IC3 combines DAC and mux functions; select `00` chooses
  DAC, and low SNDEN disables sound except the separate single-bit source.
  The selected sound goes to the modulator; buffered cassette recording output
  is separate. This does not transfer the original CoCo's analog circuit or
  voltage response to the CoCo 2.

Examined [XRoar 1.12.1 source][upstream], archive SHA-256
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`:

- `src/dragon/coco.c`, `pia1a_data_postwrite_coco`, passes the six output bits
  to `sound_set_dac_level`; cassette output is updated separately.
- `src/dragon/dragon.c` connects PIA select and enable callbacks to
  `sound_set_mux_source` and `sound_set_mux_enabled`.
- `src/sound.c`, `sound_update`, selects the mux source and applies mux gain,
  bus offset, additional sources and output gain. `send_buffer` converts the
  mixed float buffer to the selected sample format, then invokes `write_buffer`.
- `src/null/ao_null.c` normally requests `SOUND_FMT_NULL` with no output buffer.
  The private instrumentation instead supplies a static 1,024-frame buffer and
  requests `SOUND_FMT_S16_LE`. Its callback copies the completed buffer to disk
  and logs the current emulated event tick. The original timing code remains.
  Start/end markers bracket that backend's lifetime. `src/xroar.c` logs
  snapshot checkpoint ticks before `write_snapshot`, without changing trap
  actions. No DAC logger, expected-sample generator or Python synthesizer
  supplies PCM.

This is the emulator's digital mixer output before any host audio driver.
Callback event ticks identify buffer handoff, not each DAC transition or host
playback time. The final incomplete fragment is not captured. At most 1,023
frames (23.20 ms) can be omitted at the end, with two sample periods of
conversion/scheduling tolerance in the validator. The experiment neither measures
nor models the RF modulator, television, speaker or room acoustics.

## Contract and independent expectations

All eight cases use `-c /dev/null`, null UI, no cartridge, nonzero startup RAM,
6809, NTSC, `cocous`, non-T1 `6847`, and explicitly verified absolute ROM paths.
CoCo 1 uses 32 KiB, BASIC 1.1 and Extended BASIC 1.0; CoCo 2 uses 64 KiB,
BASIC 1.2 and Extended BASIC 1.1. Assembly selects the slow clock. Output gain
is explicitly `-ao-gain -3`. No installed emulator is modified or launched as
an interactive window. Host acceleration does not change modeled clock speed.

Each run stops at the 64th application update. These are not VDG frames.
The existing independent sound-slots `verify_ram` oracle checks final sample
count, phase, pitch, button, framebuffer and guards. An unreachable data-label
trap must produce no snapshot. This establishes program execution separately
from the PCM checks. Scripted input substitutes a value after the real PIA
read; it is not physical joystick evidence.

The phase increments are 2,048 and 4,096 in a 65,536-unit cycle, so the expected
waveform repeats every 32 or 16 writes. The independently examined slow-clock
model gives 894,886.25 cycles/s. The original inner loop costs 57 cycles per
write, plus foreground work once per 256 writes. That predicts roughly
488 Hz for released input and 976 Hz for the final scripted high-pitch block.
These expectations are fixed before reading PCM, not fitted to its spectrum.
The original timing investigations retain the exact cycle-gap evidence.

Analysis removes the mean from the last 6,615 samples (150 ms), applies a Hann
window and selects the strongest non-DC FFT bin. Bin spacing is 6.667 Hz; a
15 Hz tolerance allows bin quantization and the uneven cooperative schedule.
AC RMS must exceed 0.01 full scale. The final scripted block is longer than
150 ms plus one missing fragment, so that window avoids pitch transitions and
ROM boot. This is a bounded dominant-pitch check, not proof of uniform periods
or absence of distortion. The delayed-work case from the earlier timing study
is outside this output experiment.

## Capture completeness and build provenance

Timing expectations come from the pinned source and program, independently of
captured length or callback count:

- `src/events.h` defines `EVENT_TICK_RATE` as 14,318,180 ticks/s.
- `src/sound.c`, `sound_interface_new`, initializes `last_cycle` at the current
  event tick. `sound_update` accumulates elapsed ticks times sample rate with a
  fractional remainder. `flush_buffer` schedules the next buffer boundary.
  Each callback must therefore be within two sample periods of
  `audio_start + callback_number * 1024 * 14318180 / 44100`.
- `src/xroar.c` queues `do_load_binaries` at `EVENT_MS(2000)`. In the original
  assembly, clearing 6,144 screen bytes costs about 0.09 s, followed by bounded
  setup. The first sample must occur 2.08–2.12 s after audio initialization.
- From that sample to update 64, 16,384 samples at 57 slow cycles each take
  about 1.044 s. Foreground work and the constant control's extra two-cycle
  `LDA` per sample fit a 1.04–1.10 s budget. These bounds cover both programs
  and controls and are fixed before reading PCM.
- The snapshot action in `handle_trap` supplies the completion tick. Audio end
  must follow it within 256 ticks (16 slow CPU cycles). Captured frames must
  reach that tick with less than one fragment plus two frames outstanding.

The first-sample trap uses `-trap-range 1-1` explicitly. There must be exactly
one start and end marker and exactly the first-sample and final checkpoint rows.
The final RAM oracle still independently checks application completion.
A final incomplete fragment is expected; a missing complete fragment is not.
Regression tests remove first, middle and final whole fragments together with
matching callback rows, and keep only the last 46,080 frames. All are rejected.

The tracked `build_capture.py` verifies the archive, patches pristine source,
builds in a new directory and records source, executable, instrumenter, builder
and reused `examples/sound-slots/expected.py` hashes. Before capture, actual
source inputs are compared against archive bytes plus the exact patch, not
merely their manifest entries. The executable and tool hashes must also match
the build record. Tests replace the executable, change source and its manifest
together, and supply missing or mismatched provenance.

This is a reproducible local procedure, not a signed or hermetic attestation.
The compiler, linked system libraries, configure-generated files and host are
trusted. A party able to replace both executable and manifest can forge their
association. The historical contract's archive hash was an expected input,
not verification of the executable's origin.

## Results and controls

The original private build on Apple Silicon macOS produced these historical
results on 2026-11-14. They predate completeness and build-provenance checks:

| Program | Released peak | Scripted final peak | AC RMS, released/scripted |
| --- | ---: | ---: | ---: |
| CoCo 1 sound slots | 486.667 Hz | 973.333 Hz | 0.2000 / 0.1995 |
| CoCo 2 sound adaptation | 486.667 Hz | 973.333 Hz | 0.2000 / 0.1996 |

Two controls run on each target and still pass the final RAM oracle:

- Muted mux: replace the sound-enable operation with clearing bit 3 of `$FF23`.
  The program still computes and writes its varying DAC values, but captured
  steady-window AC RMS is zero.
- Constant DAC: insert `LDA #$80` immediately before the sample store.
  Phase, application state and drawing still progress, but captured
  steady-window AC RMS is zero. The extra instruction changes timing, so this
  control does not make a cycle-equivalence claim.

Both controls are rejected when assessed against the positive tone expectation.
Positive tones are rejected as silent controls, and the doubled-pitch capture
is rejected against the low-pitch expectation. Silence has no reported pitch;
a first FFT bin in an all-zero spectrum would not be a measured frequency.
The historical checks rejected missing, partial-fragment and all-zero evidence,
but did not reject whole-fragment loss. An ordinary XRoar formerly reached
the RAM checkpoint and failed for lack of PCM. It now fails before launch
because it has no verified capture-build provenance.

Measured artifacts are in `build/audio-output/measured-final/`; test artifacts
are in `build/audio-output/pytest-final/`. Each `contract.json` records commands,
ROM digests, executable and original/copied assembly digests, instrumentation
and runner digests, format and gain. Each `result.json` records measured RMS,
DC mean, peak, expected pitch, sample count, callback edge ticks and WAV digest.
Full WAVs contain boot audio and steady output; only the stated tail is analyzed.

The historical scoped suite passed 15 tests with 94.96% combined
statement/branch coverage.
Ruff lint/format and Markdown fix/check passed. The full starter suite was not
run. The build reused a checksum-verified cached upstream archive, retaining
license files under `local/research/audio-output/`; this was not a fresh-machine
installation test. See the [reproduction procedure](../../../experiments/audio-output/README.md).

The rerun with timing instrumentation is retained separately in
`experiments/audio-output/.work/measured-checked/`. All eight cases passed and
all eight WAV hashes match their historical counterparts byte for byte. The
released, scripted and muted cases retain 138,240 frames; constant-DAC cases
retain 140,288. Audio-end and completion ticks match exactly in every case.
The uncaptured remainder is about 634 frames for released/muted, 693 for
scripted and 201 for constant, all inside the permitted unfinished fragment.
The new contracts embed verified build provenance and the RAM-oracle digest.
Historical evidence has not been overwritten or relabeled as newly verified.

The revised scoped suite passed 33 tests with 95.44% combined statement/branch
coverage. This includes a fresh archive-to-executable build and real capture,
plus an ordinary executable substituted into a copied build with its executable
hash rewritten: the latter still fails at runtime for missing PCM. Test outputs
and coverage are under `experiments/audio-output/.work/pytest-final/` and
`experiments/audio-output/.work/tests-final.log`. Ruff lint/format and Markdown
fix/check passed. The full starter suite was not run.

No rendered-display check, listening session, host audio playback, physical
input or physical-hardware measurement was performed. A passing PCM capture
closes the gap after modeled DAC updates; it cannot close those other gaps.

[technical]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[service]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf
[upstream]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
