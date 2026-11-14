# Collect room renderer and mixer validation

## Question and scope

Does the existing Collect room keyboard API journey produce the independently
expected scenes and real mixer PCM through one complete game and restart on
explicit CoCo 1 and CoCo 2 profiles?

The [tracked experiment](../experiments/collect-room-output/README.md) combines
the existing Collect room keyboard and DAC hooks with the display-validation
renderer and audio-output mixer instrumentation in a new private XRoar build.
It does not change `scripts/collect_room.py`, game assembly, ROMs or another
experiment's executable. Original instrumentation is loaded from tracked files;
no downloaded emulator source is committed.

The bounded fixture is the first 43 rows of the original hand-authored
`examples/collect-room/journey.txt`. It includes title, startup-held Space,
release/repress, blocked movement, both pickups, locked exit, win, restart and
held Space after restart. It does not establish the full 95-step journey's
three-game coverage. Each run ends 50 ms after checkpoint 42, before another
input sample. That tail lets the renderer publish the restarted scene.

## Primary sources read

PDF pages are one-based positions, not printed page numbers. These pages were
read as images for this experiment:

- Inman, [Assembly Language Graphics][graphics], PDF 106, table 5-1:
  mode 6R is 256 by 192, occupies `$0400..$1BFF` and uses 6 KiB.
- Tandy, [Color Computer Technical Reference Manual][coco1], PDF 38,
  table 4 and figure 11: enabled sound and mux selection 00 route the DAC.
- Tandy, [Color Computer 2 NTSC Service Manual][coco2], PDF 37,
  section 4.9 and figure 4-11: selection 00 routes its six-bit DAC.

These facts support the reused scene layout and routing expectation; they do
not establish a physical board measurement. Exact keyboard, register and art
expectations are reused from the existing Collect room implementation and its
[documented source work](../examples/collect-room/README.md#verified-source-facts).

The checksum-verified XRoar 1.12.1 source is the primary source for emulator
measurement semantics. `src/events.h` defines 14,318,180 ticks/second.
`src/mc6847/mc6847.h` gives 912 ticks/line and 262 lines/frame.
`src/dragon/dragon.c` publishes frames at vertical sync and forces frameskip 10
when rate limiting is off. `src/sound.c` accumulates fractional sample timing
and schedules complete output fragments. `src/xroar.c` schedules direct binary
loading at 2,000 ms. These passages were read from the pinned source, not
inferred from a passing capture.

## What is checked

Input travels through XRoar `keyboard_press`/`keyboard_release`, its keyboard
matrix, PIA and the actual assembly scanner. The harness checks every injected
key mask and sequence number, then the original RAM oracle checks game state,
room contents, history, framebuffer, sound completion and guards at every
checkpoint. It does not inject game state or call game routines directly.

The null UI uses the real `vo_render` renderer. Every draw callback writes its
RGB buffer and event tick. S-video, no artifact decoding, zoomed viewport and
zero frameskip are explicit. Paced execution is required. A complete stream
has one 512-by-192 frame every 238,944 ticks, including boot, with less than one
frame outstanding at either boundary. Byte count, sequence, dimensions, spacing
and both edges must match. Dropping frames and renumbering the remaining log
cannot satisfy this check.

For every game checkpoint, all frames between one complete video period after
the checkpoint and the next input sample must exactly match the independent
per-pixel scene oracle. It uses literal original art rows and the hand-authored
collected-location fixture, rather than reading the game's prepared art table.
The lettering specification is shared, but pixel placement is independently
computed. The pinned emulator palette is RGB (0,31,0) and (46,188,36), with two
horizontal renderer samples per logical pixel. These are emulator output
expectations, not physical colorimetry. Frames during redraw are captured but
are not required to match a completed scene. This is not a tear-free claim.

The real mixer writes mono S16_LE PCM at 44,100 Hz in 1,024-frame fragments,
with gain -3 dB. No samples are synthesized from DAC writes. Start/end markers
and all callback ticks must match the sample timeline within two sample
periods. The final remainder must be less than one fragment plus two samples.
The first checkpoint must be 2.08–2.20 seconds after audio initialization;
the 42 subsequent scan intervals must total 4.5–5.5 seconds. These budgets
come from the 2-second loader delay, initial drawing, the 12,000-iteration
8-cycle delay per update and bounded redraw/effect work. The end marker must
be 50 ms after the final checkpoint within 256 ticks.

Five effects are expected at checkpoints 4, 14, 25, 37 and 41. Actual DAC values
and routing are checked separately. Each PCM window runs from input sampling
to completed game rendering. The analyzer trims its quiet suffix using a
0.1-full-scale activity threshold above the final level. It requires exactly
16 high runs, AC RMS between 0.02 and 0.5, and these independent bounds:

| Effect | Peak-frequency band | Active-span band |
| --- | --- | --- |
| Start/restart | 900–1,100 Hz | 14–18 ms |
| Pickup | 1,550–1,950 Hz | 7–11 ms |
| Win | 600–800 Hz | 21–25 ms |

The assembly's literal delays are 80, 40 and 120; the 5-cycle delay iterations
plus approximately 57 cycles of loop overhead give about 979, 1,741 and 681 Hz
at the selected emulated clock. Each effect has 32 alternating writes. Bounds
allow sampling and finite-window error. They are not musical-note or perceived
quality claims. The FFT is zero-padded to locate a bounded spectral maximum;
its bin spacing is not the frequency resolution of these short bursts.
The title interval must have AC RMS at most 0.0001.

## Results and failures

The original scoped suite passed all 24 tests on Apple Silicon macOS 27.2 with
Python 3.13.12, in 191.85 seconds. Combined statement/branch coverage was
94.75%, above the unchanged 90% gate. Scoped Ruff check and format check,
Markdown fix/check and scoped whitespace checks passed. No game issue was
found within this bounded lifecycle.

Fresh-build test evidence is retained under
`experiments/collect-room-output/.work/tests/captures0/`, with the suite output
in `.work/tests.log`. Each profile passed all 43 RAM/input checkpoints and all
229 stable rendered frames. Each captured 447 continuous renderer frames,
321 complete mixer callbacks and 328,704 PCM samples. Routing checks observed
160 alternating DAC writes across the five effects. The measured title AC RMS
was zero on both profiles.

CoCo 1 ran from audio tick 0 to 106,920,181, or 7.467442160945036 seconds.
Its first and final game checkpoints were ticks 30,793,856 and 106,204,272.
CoCo 2 ran to tick 106,920,165, or 7.467441043484577 seconds; its corresponding
checkpoints were ticks 30,793,840 and 106,204,256. Both streams' first and last
video callbacks were ticks 238,944 and 106,807,968. The uncaptured final audio
remainders were 610.1993 and 610.1500 sample periods, respectively. These
remainders are reported, not represented as captured samples.

CoCo 1's start/restart peaks were 978.415 Hz; pickup peaks were 1,738.806 Hz;
the win peak was 679.642 Hz. CoCo 2's corresponding peaks were
978.415/977.069 Hz, 1,738.806/1,740.152 Hz and 679.642 Hz. Active-span AC RMS
was 0.33862–0.33878 of full scale. Each effect had exactly 16 high runs.
The active spans contained 698, 393, 392, 1,003 and 698 samples in journey
order, respectively, on both profiles. Contract and result JSON retain the
full precision, command lines and input/output digests.

All six live controls failed at their intended boundary. Black renderer output
failed the first scene comparison; -100 dB mixer output failed the first PCM
effect; absent keyboard injection failed the input sequence check. Video and
audio controls passed the original game-state and routing checks first. The
suite also rejected damaged capture completeness, wrong collected-star
location, wrong effect expectation and altered build inputs. Failed controls
retain `status: failed` alongside their actual captures and contracts.

Three development failures remain recorded:

- `build/make.log`: the first video hook lacked `events.h`, so compilation
  failed. `first-coco1/result.json` records refusal to use that incomplete
  build. The fixed private build includes the event header.
- `measured-coco1/result.json`: the unpaced run produced only every eleventh
  frame. The continuity check rejected it; the runner now uses `-ratelimit`.
- `paced-coco1/result.json`: the full effect-window FFT selected the burst's
  on/off envelope near 15 Hz. The analyzer now removes the quiet suffix before
  measuring the alternating portion. Original pitch bands were retained.
  `reanalysis.json` records a separate analysis of that capture; the failed
  result was not overwritten or relabeled as a successful original run.

## Limitations

This establishes bounded emulator output on the measured host and profiles.
There was no host OS keyboard injection, GUI inspection, listening session,
host speaker playback, physical CoCo test or disk-loading test. It does not
cover composite artifacts, monitor calibration, every CoCo 2 revision,
long-running play or input timing outside the sampled path. PCM outside the
five effect windows and quiet title interval is retained and checked for
capture completeness, but has no separate waveform-content oracle. Renderer
frames during boot and redraw likewise have continuity checks without a
completed-scene equality requirement. macOS scope is
Apple Silicon; Intel support and Intel validation are excluded.

Local build provenance checks actual source inputs against the pinned archive
plus exact patches and verifies executable and tool hashes. It is not signed
or hermetic: the compiler, system libraries and generated configure files are
trusted. Someone able to replace both executable and manifest can forge their
association. Completeness controls detect accidental evidence loss, not a
malicious party rewriting every timestamp and capture consistently.

The full starter suite and fresh-machine installation are outside this scoped
experiment. No production installation, commit, push, Foundry registration or
other project change is part of this work.

[graphics]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf
[coco1]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[coco2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20%2826-3134%20%26%2026-3136%29%20%28Tandy%29.pdf

## Independent review correction

Both retained positive runs satisfy the input/checkpoint ordering. Independent
review found that the analyzer did not enforce it for future captures.
Acceptance now requires every input event at or after audio start, each input
at or before its checkpoint, each checkpoint before the next input, and the
last checkpoint before audio end. Five malformed-timestamp controls cover
capture start, capture end, input after its checkpoint, overlapping events and
a final checkpoint at shutdown. These checks strengthen evidence acceptance;
they do not change the game or claim host keyboard delivery.

The corrected suite passed 29 tests in 89.21 seconds with 94.38% combined
statement/branch coverage. The unified validation command also passed the
experiment's Ruff checks. Evidence is retained under
`build/validation/run-dzovodtm/collect-room-output/`.
