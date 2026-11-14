# Hidden drawing and field-boundary publication

Read this when a correct completed framebuffer is insufficient because the
continuous display exposes intermediate drawing. The original
[clean-animation experiment](../../../experiments/clean-animation/README.md) draws
complete scenes into a hidden screen, then changes the SAM display base at a
fresh field boundary. The original moving-objects example remains unchanged.

## Source facts and the original adaptation

These primary passages were read before relying on their hardware facts:

- Tandy, *Color Computer Technical Reference Manual*, PDF 13, printed 6:
  `$FF03` bit 7 is the field-sync flag; bit 1 selects its edge; bit 0 controls
  IRQ output; bit 2 selects the data register at `$FF02`. PDF 14, printed 7,
  defines the video fields at `$FF22`. PDF 15, printed 8, defines the SAM
  display offset in 512-byte units, F4 clear/set at `$FFCE`/`$FFCF`, and the
  slow-clock strobes. PDF 31, printed 24, specifies SAM `110` and PIA bits
  7–4 `1111` for 256×192 graphics. The page images were inspected directly.
  [Technical manual][tandy]
- Motorola, *MC6821 Peripheral Interface Adapter*, PDF/printed 10, Figure 18:
  bit 1 zero selects a falling edge; the flag is cleared by reading the
  corresponding data register; bit 2 one selects that register. Its page image
  was inspected. This supports discarding a stale flag after drawing, before
  waiting for the next edge. [MC6821 datasheet][pia]
- Motorola, *MC6847/MC6847Y Video Display Generator*, PDF/printed 22:
  field sync becomes active at the end of the display window and remains
  active until the trailing edge of vertical sync. The stated interval is
  32 scanlines, about 2.03 ms. This is field sync, not the composite vertical
  sync waveform. The page image was inspected. Its generic non-6883 system
  discussion does not alone establish SAM latching. [MC6847 datasheet][vdg]
- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
  PDF/printed 31: the non-T1 MC6847 FS output is a PIA interrupt source and
  disables the VDG address bus after active display so SAM can refresh RAM.
  This is the board family examined, not every CoCo 2 revision. [Service manual][coco2]

The release-pinned XRoar 1.12.1 source supplies the emulator-specific facts:

- `src/dragon/dragon.c`, `dragon_vdg_fs`, forwards FS to PIA0 port B and SAM.
- `src/mc6821.c`, `mc6821_set_cx1` and `mc6821_read`, sets the edge flag even
  with IRQ output disabled and clears it on a data-register read.
- `src/mc6847/mc6847.c`, `do_hs_fall`, signals FS falling after the active
  display ends, and rising at vertical blank start.
- `src/mc6883.c`, `mc6883_vdg_fsync`, reloads the display counter from F on
  the rising edge. Thus the falling-edge publication occurs before this reload.
- `src/mc6847/mc6847.h` and `src/events.h` specify 912 event ticks per line,
  262 lines per NTSC frame, and 14,318,180 ticks per emulated second.

The original timing deduction is 238,944 ticks per video frame, about
59.9227 frames per emulated second. Every measured renderer interval must equal
that value. Source SHA-256 hashes and the private executable hash are recorded
in each completed report. The pinned [release archive][xroar] SHA-256 is
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.

The original adaptation keeps the baseline's scene rules and redraw routines,
replaces their fixed destination with a drawing pointer, moves code to `$4000`,
and removes the arbitrary pause loop. Screens at `$0400` and `$2400` differ
only in F4. Drawing may span several refresh periods. After completion the
program clears the old FS flag, waits for a new falling edge, then writes one
SAM strobe. No display-memory copy is needed at publication. Before reusing
the old screen, the program selects rising-edge detection,
clears the previous event and waits for a fresh rising edge. In XRoar, SAM
reload and the renderer callback occur before the CPU resumes and sees that
event. This is an emulator adoption contract, not a proven silicon deadline.

This does not assume that waiting before visible drawing fixes an overlong
redraw. A blanking interval cannot contain arbitrary work. The experiment keeps
that work hidden and waits only to publish its result. The memory cost is
12,288 screen bytes, twice the baseline, plus a two-byte drawing pointer.
The explicit memory map and target limits are in the experiment README.

The [primary-source crosscheck](../research/frame-publication.md) preserves a
critical limit: manufacturer preload/FS-low passages do not establish an exact
atomic latch edge, a final-strobe margin, or a buffer-reuse deadline. The PIA
flag records an event, not the current pin level. This experiment gives the
publisher sole acknowledgement ownership, explicitly selects data access and
the relevant edge, and masks IRQ/FIRQ. A single F4 write reduces intermediate
address encodings; it does not prove physical adoption or safe reuse.

## Independent expectations and observation boundaries

RAM checks use the existing pixel-coordinate oracle in
`scripts/moving_objects.py`. Its reflected-motion formula and pixel composition
are independent of the assembly's movement branches and byte-writing loops.
Completed scenes 1, 2, 16, 32, 64, 65, 185, 186, 369 and 370 check the hidden
screen, counter, position, pointer and all four guards. After scene 1, the other
screen must still equal the preceding complete scene. These cases cover both
buffers, overlap order, changed scenery and motion reversals. A trap at the
unreachable state-data label must never fire.

Continuous output uses the existing cadence experiment's private null-UI
capture hook, unchanged. The normal SAM/VDG and software renderer generate each
RGB record. Starting at the first exact scene-1 image, the analyzer checks 150
consecutive buffers against complete scenes 1–64. It validates every colour and
horizontal sample pair before comparing every pixel. Every buffer in the
150-frame acceptance window must be a complete scene; blank, background-only
and partial images are rejected. Observed scene changes must advance by exactly
one, and at least two must occur. Startup before the first full scene is
explicitly excluded.

The workload adds 32 NOPs per background-byte store without changing scene
expectations. The unchanged, unsynchronized single-buffer baseline must fail
complete-scene acceptance. A repeated normal capture must have identical
per-frame timestamps, RGB hashes and cost measurements. Synthetic controls
introduce blank, background-only, partial, skipped, reversed and frozen scenes.
RAM corruption controls change both buffers, guards and movement state. A real
uninstrumented XRoar run can produce correct RAM but must fail for missing
renderer evidence.

The original cost hook logs emulated event ticks on four ordinary RAM marker
stores. It observes only CPU execution inside `$4000–$7DFF`, excludes debugger
writes and leaves machine behavior unchanged. Marker 0 precedes the scene
counter and drawing; marker 1 follows both objects; marker 2 follows the display
base strobe; marker 3 follows observation of the subsequent rising FS event.
Thus draw cost includes the scene counter and its marker boundary;
wait/publication cost includes flag clearing, polling and the strobe. It is not
a count of stores. The four stores add measurement overhead to the experiment.
Publication intervals also include the adoption wait, motion advancement and
drawing-pointer swap. `timing.py` independently checks that the publication
marker lies within one scanline (912 ticks) after the model's falling FS,
and the reuse marker within one scanline after its rising FS. The rising edge
is observed through the actual renderer callback timestamps; falling FS is
32 scanlines earlier according to the inspected timing constants. Controls
reject publication outside that window, reuse before the boundary and delayed
reuse. This observes a modeled adoption boundary, not the first memory fetch
from the new buffer, and does not perform a hardware phase sweep.

A draw callback is a video frame. A completed draw and its later publication
are separate events. The observed completed-scene rate comes from publication
marker intervals, while exact rendered scene matches independently show what
reached the software display. Neither measure is host GUI pacing.

## Results and limits

The first exploratory run passed complete-scene rendering but failed the cost
log check because ROM startup also wrote the marker addresses. The corrected
hook restricts observation to the experiment's execution region. Evidence from
that failed run stays ignored under `build/clean-animation/initial/`; it is not
a successful reproduction.

The first RAM-matrix attempt exceeded XRoar's breakpoint capacity and lacked
later snapshots. The runner now launches one bounded counted checkpoint at a
time. Missing evidence failed the run instead of silently reducing coverage.

The final fresh-build matrix completed on 2026-11-14 under
`build/clean-animation/spec-8ed72cf56374/`. Its `results.json` has `passed: true`.
Each listed window contains 150 video frames and 149 intervals of 238,944 ticks,
a first-to-last span of 35,602,656 ticks (about 2.487 emulated seconds).
Both firmware configurations gave these image counts:

| Case, on each target | Complete images | Other images | Complete scenes seen |
| --- | ---: | ---: | --- |
| Hidden drawing | 150 | 0 | 1–22 |
| Hidden drawing, added work | 150 | 0 | 1–5 |
| Unchanged single-buffer control | 47 | 103 | 1–19 |
| Hidden drawing repeat | 150 | 0 | 1–22 |

All twenty selected RAM checkpoints passed, including both buffers, guards,
changed scenery and reversals. Each target's repeat matched all 150 timestamps
and RGB hashes, plus its entire cost measurement. The two target configurations
were checked independently; identical summary counts do not imply identical
firmware or every identical timing sample.

Cost logs cover the full bounded run, beyond the 150-image acceptance window.
Normal runs completed thirty publication/adoption sequences; heavy runs seven.
The normal draw cost was 1,417,072 ticks (98.970 ms) on both targets. Added work
raised it to 7,708,528 ticks (538.373 ms). Both exceed one video frame. Normal
publication cadence was approximately 8.5604 completed scenes per emulated
second (about seven video periods per scene); heavy cadence was 1.81584
(about thirty-three periods). These are measured marker intervals, not rates
inferred from store counts.

Normal completion-to-publication waiting ranged from 117,696 to 225,216 ticks,
including the shorter first wait. Heavy waiting ranged from 38,720 to 146,368
ticks across the two targets. Publication markers occurred 368–528 ticks after
the modeled falling FS, and reuse markers 128–240 ticks after the subsequent
rising FS. Every measured sequence passed the independently declared one-line
bounds. The conservative adoption wait costs time too. The experiment removes
the baseline's arbitrary pause, so these figures do not isolate a speed benefit
from double buffering.

The normal code/state image occupies `$4000–$417D` (382 bytes); the workload
variant ends at `$419D` (414 bytes). Neither approaches the reserved stack.
The report records exact ROM, source, binary, capture and private-build hashes.
The measured assembly SHA-256 is
`bbd1ad0b05c0aff9aeee862107ca46627fa4fa86d7c78bd12e4243202b3c9bfd`;
the private executable SHA-256 is
`0b420e305510c706d523c0c9617ebd578e26e7ce14eb320888f554d3911d7357`.

The original scoped suite passed all 37 tests in 323.73 seconds, with 97.73% combined
statement/branch coverage of the runner and phase checker. The real
uninstrumented-emulator control failed for absent renderer capture after its
RAM checkpoint passed. Corrupt scene, RAM, cost, phase and cross-case controls
were rejected. Ruff check/format and Markdown fix/check passed. Logs and
coverage reports are under `build/clean-animation/`. The whole starter suite
was not run for this assigned experiment.

These are defined CoCo 1 and CoCo 2 NTSC, non-T1, 32 KiB emulator configurations.
They do not establish PAL, CoCo 3, physical board timing, RF/composite appearance,
physical tearing, monitor behaviour or host smoothness. There is no audio
measurement: output uses the null audio backend and IRQ/FIRQ remain masked.
A game requiring sound, controls or ROM services must budget and integrate those
separately. No physical hardware was accessed, and no GUI was launched.

## Independent review corrections

Independent review found no defect in the retained assembly sequence, but the
cost checker did not reject a new draw that preceded the previous buffer reuse.
It now checks chronology across sequence boundaries. A regression case moves
the next draw start 16 ticks before reuse and requires rejection.
The continuous-output claim is limited to the 150-frame acceptance window;
additional captured frames are not included in that acceptance claim.

The revised run passed all 38 tests in 237.01 seconds. Its first coverage
command accidentally included imported starter helpers and failed the aggregate
gate. Reporting the same retained data with the experiment's documented scope
passes at 97.01% combined statement/branch coverage of `clean.py` and `timing.py`.
The full log and corrected scoped report are retained under
`build/clean-animation/revision-tests.log` and
`build/clean-animation/revision-scoped-coverage.log`.

[tandy]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[pia]: <https://sowerbutts.com/replica1-serial/6821.pdf#page=10>
[vdg]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>
[coco2]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>
[xroar]: <https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz>
