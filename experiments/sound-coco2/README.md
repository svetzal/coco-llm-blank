# CoCo 2 cooperative sound validation

This bounded original adaptation of `examples/sound-slots/main.asm` checks
samples, logical input, drawing and actual modeled DAC write times together.
Read [the findings](../../guidance/techniques/validation/sound-coco2.md) for directly
examined sources, results and limits. Existing examples and scripts are inputs;
this package does not alter them.

## Prepare

Run from the repository root with its locked Python environment, LWTOOLS,
C compiler, make, patch and the XRoar build prerequisites already available.
For a fresh checkout, use `uv sync --locked` and the
[toolchain instructions](../../guidance/starter/toolchain.md). In a shared checkout,
use the existing environment without synchronizing it. There are no global
installs, GUI launches or changes to the shared project target here.

Provision firmware only if needed, then verify it:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts').resolve()))
from roms import provision, verify_installed
provision(Path.cwd(), 'coco2')
verify_installed(Path.cwd(), 'coco2', ('bas12.rom', 'extbas11.rom'))
PY
uv run --no-sync python scripts/doctor.py --profile demo --target coco2
```

Stop on firmware failure. ToolShed is optional for this direct DECB load.
The runner repeats checksum verification before each launch and passes absolute
ROM paths. Its `contract.json` records the isolated target before execution.

## Build private instrumentation

Use a fresh `local/research/sound-coco2/` source directory for the following
build. The patch is the retained original instrumentation from
[audio timing](../../guidance/techniques/validation/audio-timing.md). It logs the PIA DAC
callback's event tick, PC, output value, control and direction registers.
It does not alter emulated instructions or advance the clock. The CoCo 3
addition in that existing patch is unused by this experiment.

```sh
mkdir -p local/research/sound-coco2
curl --fail --location \
  https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz \
  --output local/research/sound-coco2/xroar-1.12.1.tar.gz
uv run --no-sync python - <<'PY'
import hashlib
import tarfile
from pathlib import Path
work = Path('local/research/sound-coco2')
archive = work / 'xroar-1.12.1.tar.gz'
expected = 'ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88'
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit('Archive checksum mismatch')
if (work / 'xroar-1.12.1').exists():
    raise SystemExit('Use a fresh source directory; do not patch twice')
with tarfile.open(archive) as source:
    source.extractall(work, filter='data')
note = Path('guidance/techniques/validation/audio-timing.md').read_text()
patch = note.split('```diff\n', 1)[1].split('\n```', 1)[0] + '\n'
(work / 'dac.patch').write_text(patch)
PY
patch -d local/research/sound-coco2/xroar-1.12.1 -p1 \
  < local/research/sound-coco2/dac.patch
(
  cd local/research/sound-coco2/xroar-1.12.1
  ./configure --without-gtk3 --without-gtk2 --without-sdl3 --without-sdl2 \
    --without-cocoa --without-coreaudio --without-alsa --without-oss \
    --without-pulse > ../configure.log 2>&1 &&
  make -j4 > ../make.log 2>&1
)
```

Stop if any step fails. Do not run `make install`. Keep upstream license files
with the downloaded source. An already cached archive with the exact digest
can replace the download; that was the approach used in the recorded run.

## Run and check

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python \
  experiments/sound-coco2/validate.py \
  --xroar local/research/sound-coco2/xroar-1.12.1/src/xroar
COVERAGE_FILE=build/sound-coco2/.coverage PYTHONDONTWRITEBYTECODE=1 \
  uv run --no-sync pytest experiments/sound-coco2 -p no:cacheprovider \
  --basetemp=build/sound-coco2/pytest \
  --cov=experiments/sound-coco2 \
  --cov-config=experiments/sound-coco2/coverage.ini \
  --cov-report=term-missing -ra
uv run --no-sync ruff check experiments/sound-coco2
uv run --no-sync ruff format --check experiments/sound-coco2
markdownlint --fix experiments/sound-coco2/README.md guidance/techniques/validation/sound-coco2.md
markdownlint experiments/sound-coco2/README.md guidance/techniques/validation/sound-coco2.md
```

The runner refuses existing output. Use `--output build/sound-coco2/another-run`
for a new measurement. Tests run the full experiment independently in their
isolated temporary directory; they require the private build above and the
installed uninstrumented XRoar for a missing-logger control. They also damage
captured evidence to check rejection of incorrect DAC values, PIA state,
timing, RAM, button, pitch, framebuffer, frame count and unreachable traps.
The scoped coverage gate is 90%; this is not the complete starter suite.

Each case checks frames 1, 16, 17, 32, 33, 63 and 64. These are application
updates, not VDG frames. Every checkpoint is a separate bounded launch,
20 emulated seconds overall and 40 host seconds maximum. Each assembly has a
30-second host bound. The completed 64-frame run supplies interval statistics.
The last delayed foreground update is checked in RAM but lies after the last
sample, outside the first-to-last-write timing span.

The released case reads the emulator's undriven fire-button input. Scripted
cases substitute logical release/press blocks after the real PIA read. The
substitution is deliberately included in timing. It is not keyboard automation
or physical-button evidence. `DELAYED` inserts 10,000 iterations of foreground
CPU work every 256 samples. It must keep the exact samples and state while
exposing an extra 80,003 slow cycles at every inter-block interval.

All logs, snapshots, binaries, symbols, exact commands and results are ignored
under `build/sound-coco2/`. Downloads and private source are ignored under
`local/research/sound-coco2/`. Tracked files contain original assembly, runner,
checks and instructions. No earlier ignored artifact is needed to reproduce.
