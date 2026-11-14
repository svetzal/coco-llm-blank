# Publish only complete scenes

This original CoCo 1/2 experiment adapts the moving-objects renderer to draw
into a hidden screen and publish it after drawing, at a fresh field boundary.
The [moving-objects baseline](../../examples/moving-objects/main.asm) is unchanged.
Read [the validation note](../../guidance/clean-animation-validation.md) for
source facts, evidence and limits.

## Reproduce

Run from the repository root with the prepared project environment, LWASM,
a C compiler, make, and verified CoCo 1 and CoCo 2 ROMs. No global installation,
GUI, cartridge or disk image is involved. Existing shared environments use
`--no-sync`; new checkouts must follow the starter's bootstrap instructions.

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python scripts/doctor.py \
  --profile demo --target coco1
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python scripts/doctor.py \
  --profile demo --target coco2
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python \
  experiments/clean-animation/clean.py --run-id measured
```

Use a new run ID. Existing directories are rejected. Optional `--archive PATH`
uses a local XRoar 1.12.1 release archive only after checking its pinned SHA-256.
Otherwise the runner downloads the pinned release. It builds its own null-UI
executable under ignored `local/research/clean-animation/<run-id>/`.
Generated assembly variants, binaries, symbols, raw RAM, consecutive renderer
records, event logs, commands and results go under ignored
`build/clean-animation/<run-id>/`. Budget about 1 GB per full matrix plus the
private build. The primary sources and downloaded firmware remain ignored.
Only a final `results.json` with `passed: true` is a completed reproduction.

The matrix runs normal hidden drawing, increased drawing workload, unchanged
single-buffer animation, and an exact normal repeat on each target. The workload
adds 32 NOPs per background byte through the retained cadence transformation.
Each continuous run ends 3.5 emulated seconds after its first complete draw;
its host timeout is 40 seconds. Each RAM-only run stops at its selected
completed scene (at most 370), with a 120-second emulated limit and a 40-second
host limit. Build steps have
600-second host limits. No process outside these child commands is inspected.

## Target and memory contract

Both configurations use the `cocous` NTSC architecture, an explicit 6809,
non-T1 MC6847, 32 KiB RAM, stock slow SAM clock, nonzero initial RAM, and direct
DECB loading. CoCo 1 uses `bas11.rom` and `extbas10.rom`; CoCo 2 uses `bas12.rom`
and `extbas11.rom`. Every launch verifies firmware bytes and passes absolute
paths. `-c /dev/null` excludes user configuration. These are experiment
configurations, not evidence for every board revision. `local/PROJECT.md` is
preserved.

The software renderer uses S-video input, no cross-colour rendering, a zoomed
512×192 viewport, RGBA8 storage, rate limiting and frame skip zero. The captured
RGB stream comes from the normal SAM/VDG renderer, not a reconstruction from RAM.
Rate limiting prevents XRoar's forced frame skip in unrestricted mode. All time
measurements use emulated ticks, never elapsed host time.

| Allocation | Addresses | Bytes |
| --- | --- | ---: |
| Screen A | `$0400–$1BFF` | 6,144 |
| Screen B | `$2400–$3BFF` | 6,144 |
| Screen guards | `$03FF`, `$1C00`, `$23FF`, `$3C00` | 4 |
| Measurement stores | `$3F00–$3F03` | 4 |
| Code and state | `$4000` through `program_end - 1` | Build checked |
| Reserved stack | `$7E00–$7EFF`, top `$7F00` | 256 |

The screens consume 12,288 bytes. Screen B adds 6,144 bytes over the baseline.
The 2,048-byte gap between screens makes their bases differ only in SAM F4;
a single strobe changes the display selection. The code placement requires
32 KiB. This is not a 16 KiB build, despite the screens alone fitting below
16 KiB. There is no return to BASIC, loader coexistence claim, collision,
clipping, arbitrary pixel alignment, keyboard polling or sound engine.

## Publication sequence

1. Draw the background and both rectangles into the hidden screen.
2. Mark completion, then read `$FF02` to discard any old field-sync flag.
3. Poll bit 7 of `$FF03` for the next falling FS edge.
4. Select the completed screen with `$FFCE` or `$FFCF`.
5. Select rising-edge detection, acknowledge the old event, and wait for a fresh
   rising event. In XRoar this follows SAM adoption of the requested base.
6. Restore falling-edge detection, swap the drawing pointer, advance motion,
   and start the next hidden draw.

The flag records an edge event, not the current FS level. The renderer owns its
acknowledgement. Manufacturer sources do not establish the exact silicon latch
edge or reuse deadline; the adoption rule here is specific to XRoar 1.12.1.

The renderer can take longer than one video frame. The visible screen stays
unchanged during that work. Waiting for vertical blank *before* drawing into
the visible screen would still expose an overlong redraw. This implementation
waits after drawing and publishes a screen base, not 6,144 pixels.

## Check the implementation

```sh
COVERAGE_FILE=build/clean-animation/.coverage \
  PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest \
  experiments/clean-animation -p no:cacheprovider \
  --basetemp=build/clean-animation/test-tmp \
  --cov=experiments/clean-animation \
  --cov-config=experiments/clean-animation/coverage.ini \
  --cov-report=term-missing \
  --cov-report=json:build/clean-animation/coverage.json
uv run --no-sync ruff check experiments/clean-animation
uv run --no-sync ruff format --check experiments/clean-animation
markdownlint --fix experiments/clean-animation/README.md \
  guidance/clean-animation-validation.md
markdownlint experiments/clean-animation/README.md \
  guidance/clean-animation-validation.md
```

The suite builds a fresh private emulator and runs the real matrix. It also
runs an uninstrumented emulator as a missing-capture control. Unit failure
controls corrupt scene progression, pixels, screen guards, state and time logs.
The reuse of cadence capture and its parser is read-only. Changes specific to
this experiment, including the timestamp hook, are retained in `clean.py`.
