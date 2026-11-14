# Bounded native CoCo 3 frame publication

This original experiment draws a white outline and an 8×8 square at five
positions on a black 256×192 bitmap. It redraws the hidden buffer, waits for a
fresh GIME vertical-border event, writes the display base, and retains the old
front through two further vertical-border events before reusing it.

The target is explicit: CoCo 3, 128 or 512 KiB, NTSC, normal-clock MC6809,
GIME 1986, native two-colour bitmap, RGB software renderer, no cartridge,
nonzero initial RAM, and direct DECB loading. There are no controls or audio.
The two capacities use the same low physical display pages. This is a bounded
five-position sequence, not a general animation engine.

Read the [validation note](../../guidance/clean-animation-coco3-validation.md)
for primary citations, the physical/CPU address distinction, and the unresolved
hardware timing contract. Passing this experiment proves the tested emulator
model. It does not establish physical tear-free switching.

## Reproduce

From the repository root, with its prepared virtual environment and native
LWASM available:

```sh
uv run python scripts/doctor.py --profile demo --target coco3
uv run python experiments/clean-animation-coco3/animation.py --run-id local-check
```

Each run ID must be new. `--help` and invalid arguments do not build or launch.
The runner verifies the actual `coco3.rom` bytes before every launch. It downloads
the checksum-pinned XRoar 1.12.1 archive and builds a private headless executable.
It does not install anything or open a GUI. An optional `--archive PATH` reuses
a downloaded archive after checksum verification.

All downloads, binaries, logs, snapshots and consecutive RGB captures go under
ignored `build/clean-animation-coco3/<run-id>/`. The private build changes only
its null UI capture and diagnostic GIME trace. The retained implementation is
`main.asm`; `oracle.py` constructs expectations independently in pixel space.
`capture.c` and `animation.py` retain the instrumentation and reproduction logic.
The baseline null-renderer adapter and archive/build helpers are imported from
`experiments/display-validation/` without editing those files.

The report records source, ROM, executable, configuration and capture hashes,
tool versions, per-case commands, scene matches and model timing. Failures leave
available evidence and a report with `passed: false`. A run that fails before
appending its result retains case files but has no successful result entry.
The initial build/measurement failures described in the note are evidence of
failed attempts, not accepted runs.

## Required controls

The six runs cover normal, wrong-base and unsafe-publication builds under both
RAM capacities. Every build must finish and preserve guards. All four publication
checkpoints compare both complete RAM scenes, and the final snapshot checks
both scenes plus a completion marker.

- `WRONG_BASE` adds one to the high display-offset byte. The intended buffers
  remain correct, but GIME reads 2 KiB past the intended base.
- `UNSAFE` publishes the destination before clearing and redrawing it. It waits
  two fields before drawing so the incorrect ownership is observable. The
  analyzer requires an explicit partial-erasure witness, not just any mismatch.

The normal acceptance window must contain exactly 42 complete frames from the
first exact scene, with scene transitions in order from 0 through 4. Every
frame must equal a complete independent scene. Truncated windows, reordered
scenes and frozen streams fail acceptance. Trace checks require normal-clock operation,
publication outside active display and within one scanline after VBORD, adoption
by the next model latch, and 192 consecutive row fetches from that base.

## Scoped checks

```sh
COVERAGE_FILE=build/clean-animation-coco3/.coverage \
  uv run pytest experiments/clean-animation-coco3 --cov \
  --cov-config=experiments/clean-animation-coco3/coverage.ini
uv run ruff check experiments/clean-animation-coco3
uv run ruff format --check experiments/clean-animation-coco3
markdownlint --fix experiments/clean-animation-coco3/README.md \
  guidance/clean-animation-coco3-validation.md
markdownlint experiments/clean-animation-coco3/README.md \
  guidance/clean-animation-coco3-validation.md
```

The real-emulator specifications build a fresh private XRoar, run the six cases,
repeat the normal 128 KiB case, and reject the installed uninstrumented emulator
even though its RAM checkpoint is correct. Unit controls reject corrupt captures,
missing progression, changed clock/phase/fetch evidence and damaged RAM.
This suite is scoped to the experiment; it is not the whole starter suite.
