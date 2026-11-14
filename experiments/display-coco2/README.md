# Validate the non-T1 CoCo 2 rendered display

This original experiment freezes selected completed scenes from the repository's
original tile-room and masked-object examples. It reuses the guarded private
XRoar build and software-renderer capture in `../display-validation/` without
editing that package. Read the [findings and limits](../../guidance/techniques/validation/display-coco2.md).

## Reproduce

Run from the repository root. The prerequisites are uv, the locked Python
environment, LWASM, a C compiler, make, pkg-config and the platform build
headers described in [toolchain guidance](../../guidance/starter/toolchain.md).
No global install or GUI launch is performed. Prepare Python with
`uv sync --locked`. Provision firmware without changing the shared target:

```sh
uv run --locked python - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import provision, verify_installed

provision(Path.cwd(), "coco2")
verify_installed(Path.cwd(), "coco2", ("bas12.rom", "extbas11.rom"))
PY
uv run --locked python scripts/doctor.py --profile demo --target coco2
uv run --locked python experiments/display-coco2/coco2.py --run-id fresh
```

The runner verifies both ROMs again, downloads and verifies pinned XRoar 1.12.1,
and builds privately. Optional `--archive /absolute/path/to/xroar-1.12.1.tar.gz`
uses a checksum-verified local archive. `LWASM` can select an explicit assembler.
The source URL and SHA-256 are retained in each report and in the imported
[build implementation](../display-validation/reproduce.py).

Each run refuses existing directories. Inputs, downloaded upstream source and
the scoped target contract stay in ignored `local/research/display-coco2/ID/`.
Logs, executable outputs, PPM/PNG captures, RAM, symbols and `results.json` stay
in ignored `build/display-coco2/ID/`. Choose a new ID to rerun. No files from
an earlier ignored experiment are required. All essential transformations and
oracles are tracked here or in the imported repository modules. No third-party
source bodies are copied into this package.

## How acceptance works

The renderer receives the emulator's actual SAM/VDG scanlines. The null-UI draw
hook exports its RGBA8 buffer as RGB PPM; PNG is only a lossless conversion.
The oracle never supplies image pixels to that hook. Expected scene pixels come
from the independent graph/text-art model in `scripts/tile_room.py` and the
geometric ring model in `scripts/masked_objects.py`, not captured RAM or assembly
art tables. The probe has five isolated pixels and an asymmetric rectangle.

The runner checks all 6,144 screen bytes and all 98,304 renderer samples at
both 0.5 and 1.0 emulated seconds after each checkpoint. It verifies assembled
`BRA`-to-self bytes and the scene identity, guards and map where applicable.
The scene programs mask interrupts at entry and the added loop performs no
writes. Identical captures at both intervals support stationary output, without
claiming numbered VDG frames or animation synchronization.

The positive cases are the asymmetric probe, tile-room steps 0, 5, 39 and 41,
and masked scenes 0, 2, 3, 8, 9, 10 and 11. These include collection and return,
partial overlap in both drawing orders, inverted background, object removal,
and edge placement. They are a bounded selection, not exhaustive rendering
coverage. Existing examples are read but never edited.

The wrong-SAM probe changes only `$FFC5` to `$FFC4`. Acceptance requires matching
RAM and differing rendered pixels. The unreachable trap uses `state` in the
same frozen masked-scene-11 binary. It must produce no RAM checkpoint even
though a renderer image can exist. A real reachable-trap mutation must be
rejected by that negative-control validator.

The launcher has a 30-emulated-second overall bound and a 60-second host bound.
Configure and make each have 600-second host bounds, assembly 30 seconds.
Normal emulated clock is explicit in the original SAM setup; `-no-ratelimit`
only accelerates host execution. Every launch excludes user configuration and
passes verified absolute firmware paths.

## Checks

The test fixture downloads and builds a fresh private XRoar, then repeats the
complete measurement. It does not reuse the standalone result.

```sh
COVERAGE_FILE=build/display-coco2/.coverage \
  uv run --locked pytest experiments/display-coco2 \
  --basetemp=build/display-coco2/pytest-tmp \
  --cov=experiments/display-coco2 \
  --cov-config=experiments/display-coco2/coverage.ini \
  --cov-report=term-missing -ra
uv run --locked ruff check experiments/display-coco2
uv run --locked ruff format --check experiments/display-coco2
markdownlint --fix experiments/display-coco2/README.md guidance/techniques/validation/display-coco2.md
markdownlint experiments/display-coco2/README.md guidance/techniques/validation/display-coco2.md
```

The scoped coverage gate is 90% statements and branches of this package.
Imported helpers retain their own specifications. This is not a full starter
suite result. Corrupt checkpoint identity, nonstationary code, wrong-mode
images, removed mode mutations, reachable negative traps and damaged source
archives must fail. Help, invalid IDs and existing-run protection are checked.

## Evidence scope

Only NTSC, 32 KiB, normal 6809, MC6847 non-T1, BASIC 1.2 / Extended BASIC 1.1,
no cartridge and direct DECB auto-run are tested. Output is XRoar's S-video
palette software path with `ccr none`. There is no PAL, T1, composite artifact,
RF, GUI presentation, cadence, tearing, keyboard, disk-loading or physical
hardware claim. A raw 512×192 capture has two horizontal samples per logical
pixel; it is not a 4:3 host window.
