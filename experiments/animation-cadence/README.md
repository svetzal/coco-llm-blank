# Continuous animation at the video boundary

Use this experiment to distinguish completed assembly redraws from consecutive
software-video frames. It uses the existing original moving-objects example.
It does not launch a GUI or measure a physical display.

Read [the findings](../../guidance/techniques/validation/animation-cadence.md) for the
measurement boundary, primary sources and limitations.

## Reproduce

Start in the repository root. Follow the project's bootstrap and firmware
instructions for CoCo 1 if the checkout is new. The experiment expects the
locked project environment, LWASM, a C compiler, make and verified CoCo 1 ROMs.
It does not install tools or alter project settings. On an already prepared
shared checkout, retain its environment with `--no-sync`:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python scripts/doctor.py \
  --profile demo --target coco1
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python \
  experiments/animation-cadence/cadence.py --run-id measured
```

A new checkout needs `uv sync --locked` first. Do not synchronize someone else's
active environment merely to run this experiment.

The runner downloads and verifies XRoar 1.12.1, builds a private executable,
assembles unchanged and workload copies of moving-objects, runs both and repeats
the unchanged case. `--archive PATH` accepts an existing archive with the pinned
checksum. There is no global install. `--help` performs no setup.

Choose a new run ID each time. Existing work or output directories are rejected.
Downloads, modified upstream source and assembly copies stay under ignored
`local/research/animation-cadence/<run-id>/`. Commands, binaries, snapshots,
renderer records, build logs and results stay under ignored
`build/animation-cadence/<run-id>/`. Allow roughly 300 MB for capture files per
three-case run, plus the private build. Tests create another private build and
capture set.

Only `results.json` with `passed: true` establishes a completed run. Individual
files from interrupted or failed runs are diagnostic evidence, not a pass.
Each emulator run has a 12-second emulated overall limit, a three-second
post-checkpoint limit and a 30-second host timeout. The logger rejects more than
1,000 draw calls. Configure and make each have a 600-second host limit.

## Checks

Run the whole scoped suite. It rebuilds the private emulator and exercises real
frozen-animation and uninstrumented-emulator controls. It needs network access
to download the checksum-pinned source archive.

```sh
COVERAGE_FILE=build/animation-cadence/.coverage \
  PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest \
  experiments/animation-cadence -p no:cacheprovider \
  --basetemp=build/animation-cadence/test-tmp \
  --cov=experiments/animation-cadence \
  --cov-config=experiments/animation-cadence/coverage.ini \
  --cov-report=term-missing \
  --cov-report=json:build/animation-cadence/coverage.json
uv run --no-sync ruff check experiments/animation-cadence
uv run --no-sync ruff format --check experiments/animation-cadence
markdownlint --fix experiments/animation-cadence/README.md \
  guidance/techniques/validation/animation-cadence.md
markdownlint experiments/animation-cadence/README.md \
  guidance/techniques/validation/animation-cadence.md
```

The capture format is a decimal ASCII header `sequence tick width height` plus
newline, followed by `width * height * 3` RGB bytes. Each record is the actual
software renderer buffer at a draw callback. It is not reconstructed from RAM.
The analyzer excludes startup only after an exact rendered first-scene match,
then uses 150 consecutive records. It checks all samples before packing them
for comparison. Two horizontal samples represent each logical pixel here.

Original code reuses the retained display experiment's guarded null-UI renderer
setup and archive/build utilities. It reuses moving-objects' independent scene
oracle and RAM verification. These imports are tracked dependencies, not files
copied out of an old ignored experiment. Source hashes identify these dependencies
in each successful report. No supported production runner is changed.
