# Measure continuous animation

Read this when a completed-frame snapshot passes but the animation's consecutive
video output still needs evidence. The existing moving-objects example exposes
intermediate redraws to XRoar's software-video output. A correct completed
frame does not establish that only complete scenes are presented.

## Boundary and configuration

This measures software renderer buffers delivered to a private null-UI draw
callback. It does not measure a GUI compositor, monitor refresh, host frame
pacing or perceived smoothness. No GUI was launched. No physical hardware was
tested. In this note, a video frame is one draw callback; a scene is one
completed redraw by the assembly program.

The explicit configuration is CoCo 1 (`cocous`), MC6809, MC6847, 32 KiB,
NTSC, stock slow clock, nonzero initial RAM, no cartridge and direct DECB load.
It uses S-video input, the composite-palette software renderer, `-ccr none`,
a zoomed 512-by-192 sample viewport and RGBA8 internal storage. These are
experiment choices based on the starter's defaults, not additional owner
requirements. The shared incomplete `local/PROJECT.md` was preserved.

Every launch calls `roms.verify_installed` and passes absolute BASIC and Extended
BASIC paths. Configuration starts with `-c /dev/null`; the user's emulator
configuration does not participate. The CoCo 1 doctor check passed; ToolShed
was missing and optional for these direct DECB runs. Firmware hashes are:

- `bas11.rom`:
  `f772ee5ec3ce3bfc455098c0c9aca2b5c42b6aa1f998bb5113ca2250bfbf2c27`
- `extbas10.rom`:
  `36ce538d261fa727152c41f66fe6b310268efe19f3ef7365e0bbc6d84a5a957e`

Rate limiting is enabled and frame skip is zero. This choice avoids XRoar's
forced frame skip when rate limiting is disabled. Host time never enters the
measurement statistics.

## Sources examined and adaptations

The primary implementation source is the
[XRoar 1.12.1 release archive](https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz),
SHA-256
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
These passages were read directly in the extracted source:

- `src/vo.h`, `vo_vsync` and `vo_refresh` (lines 273-287): draw is called before
  resetting renderer state. Refresh can also request draw. The experiment does
  not single-step and rejects any interval other than the expected video period.
- `src/vo.c`, `vo_set_renderer` (lines 102-118): the renderer receives palette,
  active-area and scanline delegates from the machine.
- `src/dragon/dragon.c`, `vdg_fsync` and `vdg_render_line` (lines 1451-1464):
  the frame-sync callback requests draw and the scanline callback forwards VDG
  output. `dragon_ui_set_ratelimit` (lines 1019-1023) sets frameskip to 10 when
  rate limiting is disabled.
- `src/mc6847/mc6847.c`, `do_hs_fall` (lines 341-399): finish the scanline,
  advance the scanline count and signal frame sync. `EVENT_VDG_TIME` at line 41
  uses the 14.31818 MHz event timebase.
- `src/mc6847/mc6847.h` (lines 44-75): horizontal timing sums to 912
  quarter-VDG-clocks and a frame has 262 lines.
- `src/events.h` (lines 33-41): event rate is 14,318,180 ticks per second;
  `EVENT_TICKS_14M31818` is identity.
- `src/xroar.c`, `set_trap_count` and `handle_trap`: a missing upper bound
  remains unlimited. This experiment uses `-trap-range 1-1`. The manual's
  debugging section describes trap actions and emulated timeouts. The built-in
  `cocous` profile at lines 461-465 explicitly selects NTSC; RAM is overridden
  to 32 KiB by this runner.

Our deduction from these timing constants is 912 × 262 = 238,944 event ticks
per video frame, approximately 59.9227 frames per emulated second. This
expectation was established before checking measured intervals. It describes
this emulator model, not a measurement of a physical oscillator.

The original [moving-objects source](../../../examples/moving-objects/main.asm) clears
and redraws the background, draws both objects, pauses, advances positions and
repeats. It writes the visible framebuffer without synchronizing to vertical
blanking. No hardware register, display mode or drawing routine was changed in
the normal case. The workload control inserts 32 NOP instructions after each
background-byte store in an ignored source copy. It retains the same completed
scene specification and adds CPU work. Its expected effect is fewer completed
scene states in the same number of video frames.

Our capture adapts the guarded renderer initialization from
[display validation](display.md). It replaces the overwrite-only PPM
writer with a bounded sequence of RGB buffers and emulated event timestamps.
The machine's normal SAM/VDG and renderer paths still create every sample.
The [audio timing experiment](audio-timing.md) supplied the approach
of timestamping at the modeled output boundary and separating host time.
No DAC logger or CoCo 3 timing conclusion is reused.

## Acceptance and partial-update tests

A trap saves the first completed redraw. RAM guards, position, scene count and
every framebuffer byte must match the existing independent scene oracle. An
unreachable data-label trap must produce no snapshot. This checkpoint proves
execution; the video log separately proves rendered output.

The analyzer finds the first exact rendered scene 1, excludes startup, and
checks the next 150 consecutive buffers. Each adjacent timestamp must differ
by 238,944 ticks. Every sample must use the expected black/green palette and
both horizontal samples of each logical pixel must agree. Each packed image is
compared with independently specified complete scenes 1 through 64. This is a
bounded early-animation window, not coverage of every motion state.

Two different mixture tests are retained:

1. Every row must match one of two adjacent complete scenes, with rows unique
   to each. No measured normal frame met this stronger test.
2. Every row must match either a complete scene or its object-free background,
   with both unerased object rows and erased rows present. Two normal video
   frames met this test. This demonstrates partial object erasure in renderer
   output, rather than merely assuming every oracle mismatch is a partial frame.

An exact object-free checkerboard is counted separately. Other mismatches are
left unclassified. The analyzer does not label all mismatches as tearing.
The row proofs record zero-based video indexes and exact row numbers in JSON.

## Measured result

The normal case and its repeat produced the same measurement object. Each
window contains 150 consecutive video frames, 149 intervals of 238,944 ticks,
and a first-to-last span of 35,602,656 ticks (about 2.487 emulated seconds).

| Case | Changed transitions | Complete scene images | Other images |
| --- | ---: | ---: | ---: |
| Unmodified animation | 41 | 47 | 103 |
| Added background workload | 16 | 13 | 137 |
| Unmodified repeat | 41 | 47 | 103 |

The unmodified window contains 99 exact object-free backgrounds. At video
index 75, rows 15-16 retain scene 10's object data while rows 9-14 match its
erased background. At index 132, rows 19-23 retain scene 17's object data while
rows 16-18 match its erased background. Every other row in each image matches
at least one of the two specified states. The remaining two non-complete
images are not classified by these tests.

Unmodified identical-image runs last 1-6 video frames; workload runs last
1-31. The edge runs are censored by the measurement window, so these are
observed run lengths, not a worst-case bound. A changed renderer image is not
necessarily a completed new scene or a full-screen change.

The first exploratory run failed the scene-1 RAM assertion because
`-trap-range 1` allowed later snapshots to overwrite it. Reading the trap
implementation identified the open upper bound. The corrected runner uses
`1-1`; the failed output remains ignored under the `initial` run directory.
No result from that failed run is accepted as cadence evidence.

## Reproduction and limits

The retained [runner and instructions](../../../experiments/animation-cadence/README.md)
include the original instrumentation, workload transformation, analyzer and
co-located tests. All downloaded source and generated evidence remain ignored.
Successful reports record exact input, ROM, executable, source, capture and
snapshot SHA-256 hashes, plus commands in per-case files.

This closes a bounded continuous software-video observation gap for this CoCo 1
configuration. It demonstrates intermediate redraw output and workload-sensitive
scene progression. It does not establish physical tearing, host GUI smoothness,
composite/RF appearance, real monitor colors, PAL, CoCo 2/3 or sustained gameplay.
No video-blank synchronization fix or double buffer is implemented here.

Exact original inputs for the measured run:

- `examples/moving-objects/main.asm`:
  `5dbd9405a0fae62c2573deac127c37591f27886af71bb37db5fc5c28fb1ec703`
- Independent scene oracle, `scripts/moving_objects.py`:
  `ca80a4a160b30e6fbf79d38658bed2d15380827cc2c82132a1764e1816545939`
- Reused renderer setup, `experiments/display-validation/instrument.py`:
  `60312c732f4e82973ed520add62b2fb6422586109bad18a12aa9c2af8d659993`

These identify the examined original inputs. The downloaded release archive hash
above identifies the complete upstream source; runtime reports also hash the
individual source passages listed above. Executable hashes identify a local
build and are not claims of reproducible binaries across different compilers.

The fresh private build and three-case reproduction completed on 2026-11-14 in
`build/animation-cadence/spec-7ed90045de12/`. Its report records the complete
source/build provenance and measurement objects. The normal run visited complete
scenes 1-19; the workload run visited scenes 1-5 in the same 150-video-frame
window. The workload also yielded one partial-erasure proof at video index 72,
130 object-free backgrounds and six otherwise unclassified images.

- Runner `cadence.py` SHA-256:
  `fdc957e555ec16db3cee4d28c97ccda2bfa651b511d2da11e47fc1a8c5977e0b`
- Instrumented `src/null/ui_null.c` SHA-256:
  `e897b482903cf69fc1ffbd42c495c5e26370fe679bbadbe61bf2b19df005235b`
- Private executable SHA-256:
  `db84073cb623d8cf87f0fd81782c8f05a47598318f661e6a54e98a5aa99dabed`

The original pre-review scoped suite passed all 24 tests with 95.54% combined
statement/branch coverage (305.56 seconds, including the fresh private build).
Real negative runs rejected a frozen program and an uninstrumented installed
emulator; the latter still produced a valid RAM checkpoint. Corruption checks
rejected truncated captures, bad sequence/viewport data, skipped frame
intervals, frozen image streams, wrong colors, unequal horizontal sample pairs
and failed cross-case controls. Source-drift and CLI argument/help checks
passed too. Ruff check, Ruff format check, and Markdown fix/check passed.
Coverage and test outputs are isolated under `build/animation-cadence/`. The
whole starter suite was not run for this assigned experiment.

## Publication review corrections

Independent review confirmed the retained normal and repeat captures are
byte-identical, including the two partial-erasure proofs. It found that the
original repeat assertion compared summaries and could miss a changed pixel
pair in an unclassified frame. The revised measurement retains each of the
150 timestamps and RGB hashes and compares them on repeat. Regression cases
alter a valid pixel pair at video indexes 26 and 83 and require rejection.

Runtime provenance now includes `scripts/moving_objects.py`, which supplies the
independent complete-scene and RAM oracle. The retained original runner hash
above identifies the earlier execution; the revised runner records its own
hashes on each new run.

The revised fresh-build suite passed 27 tests in 321.58 seconds with 95.58%
combined statement/branch coverage of `cadence.py`. Exact repeated timestamps
and RGB hashes passed, both altered-pixel cases were rejected, and the oracle
hash was recorded. This run includes a new private emulator build and the real
capture controls; it does not establish host GUI or physical-display behavior.
