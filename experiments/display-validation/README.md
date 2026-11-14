# Reproduce the software-renderer capture

This is a bounded research experiment for XRoar 1.12.1, CoCo 1 NTSC,
32 KiB and stock MC6809 timing. It is not a supported launcher or CI gate.
It retains the original instrumentation generator, asymmetric probe, frozen-frame
transformations and comparisons. It uses the repository's original first-screen
and moving-objects assembly without editing them. No upstream source bodies,
ROMs, binaries or rendered assets belong in this directory.

Read [the evidence boundary](../../guidance/techniques/validation/display.md) before using
the results. Static software-renderer samples do not establish animation cadence,
tearing, physical display appearance or keyboard play-testing.

## Prerequisites and fresh-clone run

Run from the repository root. You need Git, uv, Python 3.13, a working C compiler,
make, pkg-config and LWTOOLS `lwasm`. On macOS the XRoar configure script also
uses the Apple command-line development tools and framework headers. On Linux,
use the native build prerequisites in
[toolchain guidance](../../guidance/starter/toolchain.md). The private configure step
records the host libraries it discovers. No GUI is launched. The experiment
never installs tools, runs `make install`, or changes the project target.

The root `uv.lock` is the only Python environment lock. Prepare it with:

```sh
uv sync --locked
```

Provide the checksum-verified CoCo 1 ROMs under `local/roms/coco1/`. For a fresh
clone, the existing provisioner can obtain them without running project setup or
changing `local/PROJECT.md`:

```sh
uv run --locked python - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import provision, verify_installed

provision(Path.cwd(), "coco1")
verify_installed(Path.cwd(), "coco1", ("bas11.rom", "extbas10.rom"))
PY
```

The runner verifies those firmware bytes again before building. It passes the
returned absolute BASIC and Extended BASIC paths on every launch. It discovers
LWASM through `native.tool_path`: `LWASM` override, project-local tool, then PATH.
Set `LWASM=/absolute/path/to/lwasm` if necessary. An installed stock XRoar is not
needed for this private build.

```sh
uv run --locked python experiments/display-validation/reproduce.py --run-id fresh
```

That command downloads the pinned archive directly from the XRoar release URL,
checks its SHA-256 before extraction, verifies the pristine `ui_null.c` hash,
and requires exactly one occurrence of each transformation target. Applying the
generator twice fails. It builds with `make -j2` in a new private source tree.
Configure and make each have a 600-second host limit; assembly has 30 seconds;
each XRoar process has 30 emulated seconds and a 60-second host limit. Completed
frames have a 0.5-emulated-second settling interval after the checkpoint.

For an offline source download, append
`--archive /absolute/path/to/xroar-1.12.1.tar.gz`. The same pinned checksum is
mandatory. ROMs and the locked Python environment must already be available.
There is no fallback to an installed emulator or an unchecked download.

Each run owns two new directories:

- `local/research/display-validation-reproduction/<run-id>/` contains the
  verified source archive, private build and generated assembly inputs.
- `build/display-validation-reproduction/<run-id>/` contains logs, symbols,
  binaries, RAM, PPM, PNG and `results.json`.

The runner refuses either directory if it exists. To rerun, choose a new ID,
for example `--run-id second`. A failed build retains its evidence and a report
with `passed: false`. No original ignored experiment files are required.

## Acceptance and negative controls

The five positive cases must match all 6,144 framebuffer bytes and all 98,304
renderer samples. Every comparison requires a 32 KiB RAM checkpoint, a
512-by-192 RGB image and exactly the measured two-colour palette
`(0,31,0)` / `(46,188,36)`. PNGs are conversions of captured PPMs.

The wrong-SAM case must satisfy both conditions: its framebuffer still matches,
and its rendered output differs. The reviewed baseline has 3,040 differences.
The runner accepts any nonzero difference for this control; the regression spec
also requires the observed baseline count of 3,040.

The unreachable-PC control uses `state` from the same frozen-frame-65 symbol
file and binary. That data label follows the final `rts` in the original
moving-objects source; no path executes it. The control runs the full timeout
and requires a zero exit with no RAM snapshot. A renderer image alone does not
pass the checkpoint requirement. The tests move that trap to the reachable
`frozen` symbol in a real emulator run and require the negative control to reject
it.

## Checks

This test command performs another fresh download and private build. It does
not reuse the preceding run. The temporary path is confined to this experiment;
pytest replaces that particular temporary directory on subsequent invocations.

```sh
COVERAGE_FILE=build/display-validation-reproduction/.coverage \
  uv run --locked pytest experiments/display-validation \
  --basetemp=build/display-validation-reproduction/pytest-tmp \
  --cov=experiments/display-validation \
  --cov-config=experiments/display-validation/coverage.ini \
  --cov-report=term-missing -ra
uv run --locked ruff check experiments/display-validation
uv run --locked ruff format --check experiments/display-validation
markdownlint --fix experiments/display-validation/README.md guidance/techniques/validation/display.md
markdownlint experiments/display-validation/README.md guidance/techniques/validation/display.md
```

The coverage gate is 90% combined statements and branches for the experimental
Python code, excluding specs and fixtures. This scoped run does not claim a full
starter-suite pass. Tests reject modified archives, modified or re-patched
upstream source, ambiguous replacements and symbols, invalid firmware, wrong
palette/dimensions, corrupt framebuffer data, a removed wrong-mode mutation,
and a reachable negative checkpoint. Help and invalid arguments have no build
side effects.

## Provenance

[baseline.json](baseline.json) records the measured reproduction with hashes,
not generated assets. `base_revision` identifies the repository HEAD used;
`inputs_sha256` identifies the actual working inputs, including the new scripts
that are not yet committed. It does not imply the working tree was clean.
The baseline includes archive and ROM hashes, assembler identity, pristine and
instrumented source hashes, configure/build commands and build hashes, plus
assembly, symbol, binary and capture hashes for each case.

The complete ignored `results.json` also retains absolute launch commands and
RAM hashes. Native executables and configure files can differ across hosts and
build paths; their hashes identify the measured build, not portable expected
bytes. Exact sample comparisons and control outcomes are the acceptance test.
The test suite can run offline only if its fresh-download fixture is adapted;
the standalone runner's `--archive` option is the retained offline route.
