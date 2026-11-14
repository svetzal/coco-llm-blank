# Validate the rendered display

Read this when framebuffer checks pass but the selected video mode, pixel order,
or displayed geometry still needs evidence. RAM snapshots alone do not establish
what XRoar renders. The stock XRoar 1.12.1 null UI discards video scanlines.

## Measured result

A private XRoar 1.12.1 build captured actual software-renderer output without a
GUI on Apple Silicon macOS. The first-screen example was assembled unchanged.
Temporary copies of moving-objects stopped after completed frames 1, 35 and 65;
its drawing routines and display setup were unchanged. All five positive cases
matched every rendered sample. This closes the static geometry gap for the
configuration below, not the animation or physical-display gap.

| Case | Framebuffer bytes | Differing renderer samples |
| --- | --- | --- |
| First-screen | All 6144 match | 0 of 98,304 |
| Asymmetric probe | All 6144 match | 0 of 98,304 |
| Moving-objects, frozen frame 1 | All 6144 match | 0 of 98,304 |
| Moving-objects, frozen frame 35 | All 6144 match | 0 of 98,304 |
| Moving-objects, frozen frame 65 | All 6144 match | 0 of 98,304 |
| Probe with deliberately wrong SAM mode | All 6144 match | 3,040 of 98,304 |

The negative mode control changes only the probe's `$FFC5` write to `$FFC4`.
It demonstrates a display error that the framebuffer oracle cannot detect.
A separate unreachable-PC control produced no RAM checkpoint, despite XRoar
exiting successfully. A renderer image by itself is not a boot checkpoint.

The original asymmetric probe has individual pixels at `(0,0)`, `(7,1)`,
`(8,2)`, `(255,191)` and `(31,117)`, plus a 29-by-13 rectangle starting at
`(17,23)`. It distinguishes horizontal bit order, byte boundaries, row stride,
orientation and unequal dimensions. The probe copies independently generated
bytes into screen RAM after using the existing first-screen display setup.

The captured first-screen, asymmetric probe and frozen frame 35 PNGs were
inspected with an image-viewing tool. Automated comparisons cover every sample
of all listed cases. The PNGs are lossless conversions of renderer PPM output,
not pictures synthesized from RAM.

## Exact configuration and evidence boundary

The tested machine is XRoar `cocous`, 32 KiB, NTSC, stock MC6809 clock,
MC6847, no cartridge, direct DECB auto-run, nonzero initial RAM. These are the
existing example's test defaults; the incomplete shared `local/PROJECT.md`
was not changed or treated as owner confirmation. CoCo 2 and CoCo 3 were not
render-tested here.

`roms.verify_installed` validated the following explicit local ROM paths before
the capture runs. `doctor.py --profile demo --target coco1` also passed.

| ROM | SHA-256 |
| --- | --- |
| BASIC | `f772ee5ec3ce3bfc455098c0c9aca2b5c42b6aa1f998bb5113ca2250bfbf2c27` |
| Ext | `36ce538d261fa727152c41f66fe6b310268efe19f3ef7365e0bbc6d84a5a957e` |

In the table, BASIC is `local/roms/coco1/bas11.rom` and Ext is
`local/roms/coco1/extbas10.rom`.

The display path is XRoar's S-video input selection, composite palette renderer,
`-ccr none`, zoomed viewport and logical RGBA8 software buffer. It is not the
simulated composite decoder, RF output, OpenGL presentation or a host screenshot.
The output is 512 horizontal samples by 192 scanlines: each logical RG6 pixel
occupies two horizontal renderer samples. No vertical stretching or 4:3 window
presentation has been applied. A 64-by-64 logical square therefore occupies
128-by-64 samples in this raw image.

The measured palette entries are RGB `(0,31,0)` and `(46,188,36)` under this
configuration. The comparison rejects any third colour and checks the exact
sample positions. These RGB values describe this emulator's palette, not a
measurement of a real monitor's black or green.

The capture proves neither physical appearance nor cadence, tearing, keyboard
interaction or visual play-testing. Freezing a completed moving-object frame
removes concurrent redraw from the experiment. It does not prove that an
unmodified animation presents only completed frames. The chosen frames exercise
both drawing orders and the background inversion; they are not an exhaustive
motion or overlap test.

## How the capture works

The retained reproduction package is under `experiments/display-validation/`.
It contains only original transformations, orchestration, tests and provenance.
Downloaded source and generated evidence stay ignored under
`local/research/display-validation-reproduction/` and
`build/display-validation-reproduction/`. The original ignored experiment under
`local/research/display-validation/` and `build/display-validation/` remains
historical evidence. No existing example, supported runner, manifest, dependency
or installed tool was changed.

The source release is XRoar 1.12.1 from the project's existing pinned source
archive, originally at
<https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz>.
Its SHA-256 is
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
The private build uses the existing compiler and libraries; it is not installed.

`instrument.py` modifies only the extracted `src/null/ui_null.c`:

1. Create a normal `vo_interface` and initialize its messenger subscriptions.
2. Attach `vo_render_new(VO_RENDER_FMT_RGBA8)` with `vo_set_renderer`, allowing
   the machine's normal palette, signal and active-area configuration to apply.
3. Allocate a bounded software buffer and set its pitch with the viewport.
4. Attach a draw delegate that writes the current renderer buffer to PPM when
   `vo_vsync` requests drawing. The destination is the process-local
   `DISPLAY_CAPTURE` environment variable. Each draw replaces the prior capture.

The machine still reads video memory through its normal SAM/VDG path.
`src/dragon/dragon.c:vdg_render_line` passes generated scanlines to the selected
renderer. `src/vo.c:vo_set_renderer` connects palette and video delegates;
`src/vo.h:vo_vsync` calls draw before resetting the renderer for the next frame.
The capture does not parse a RAM dump or run the Python oracle to make pixels.

XRoar's `dragon_ui_set_ratelimit` forces frameskip to 10 when rate limiting is
disabled, even with `-fskip 0`. An initial 0.08-second post-checkpoint delay
returned stale or partial captures. The measured runs use 0.5 emulated seconds
after the stationary checkpoint to allow complete rendered frames. They also
use a 30-emulated-second overall timeout and a 60-second host subprocess
limit. `-no-ratelimit` changes host execution speed, not the assembly's stock
clock setup. Frame 65 required more than the initial 10-second overall limit.

## Reproduce from a fresh clone

Follow the [retained reproduction instructions](../../../experiments/display-validation/README.md)
for prerequisites, locked uv setup, firmware provisioning and checks. The package
needs no files from the original ignored experiment and preserves the current
project target. After the prerequisites are present, run from the repo root:

```sh
uv run --locked python experiments/display-validation/reproduce.py --run-id fresh
```

The runner obtains and checksum-verifies the pinned archive, checks pristine
source and exact replacement counts, and builds a private XRoar. LWASM uses the
existing `native.tool_path` discovery and explicit `LWASM` override. Both ROMs
are verified before launch and supplied by absolute path. No GUI is opened.
Choose a new run ID for each run; existing input or output directories are
rejected rather than reused.

The tracked [baseline provenance](../../../experiments/display-validation/baseline.json)
records the independent reproduction and input/tool/build hashes. Complete launch
commands and generated evidence remain in the ignored run's `results.json`.
All five positives reproduced exactly; wrong-SAM again matched the framebuffer
and differed in 3,040 renderer samples. The unreachable checkpoint now uses the
`state` symbol from the same frozen-frame-65 binary, instead of a hardcoded
address. A real reachable-trap mutation and artifact corruption tests check that
the acceptance controls reject false success.

These results concern the same static software-renderer configuration described
above. They do not extend the animation or physical-display claims.

## Hardware sources checked

The following local PDF pages were rendered and inspected as images before the
probe was constructed:

- Tandy, *Color Computer Technical Reference Manual*, PDF 14: `$FF22` display
  fields and `$FF23` register selection. PDF 15: SAM display offset, mode
  strobes and clock controls. PDF 31: the 256-by-192 mode row has SAM `110`
  and PIA bits 7 through 4 set.
- Inman, *Assembly Language Graphics for the TRS-80 Color Computer*, PDF 107:
  eight consecutive pixels per byte and colour-set-zero black/green values.

The 32-byte row and 6144-byte framebuffer follow from 256 pixels divided by
eight, multiplied by 192 rows. The renderer's two horizontal samples per pixel
are a measured XRoar representation, not a claim from those hardware manuals.
