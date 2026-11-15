# Python support tools

Load this file when you write host-side scripts, asset converters, reference
implementations, or tests. Run commands from the repository root.

## Environment

Use `uv sync --locked` to create `.venv` from `uv.lock`. Use `uv run` for scripts
and checks. Do not install into system Python. Do not maintain a second
requirements file.

Declare a dependency with `uv add`. Commit `pyproject.toml` and `uv.lock`
together. `.python-version` selects Python 3.13.

The baseline has Docling and RapidOCR for documents, NumPy for numeric reference
models and test vectors, and Pillow for image conversion and previews.
Development tools are pytest, pytest-cov, and Ruff. Optional groups provide
pygame-ce for interactive prototypes and music21 for music analysis:

```sh
uv sync --locked --group interactive --group music
uv run --group interactive python path/to/prototype.py
uv run --group music python path/to/music_tool.py
```

Without these flags, later `uv run` commands can remove optional packages while
they synchronize the environment. Keep the group flag on commands that use them.

## What Python does here

The original `coco-llm` used Python for:

- fixed-point reference models
- exact test vectors
- waveforms and WAV output
- palette and sprite packing
- bitmap fonts
- RS-DOS disk images
- orchestration of XRoar test/capture

Those are useful
patterns for future projects. Their game and language-model implementations
are not part of this blank starter.

Keep pure transformations separate from file and process I/O. Test packed
bytes and numeric outputs, not only rendered previews. Use `pathlib`, `struct`,
`wave`, and `subprocess` from the standard library where they fit. Put generated
assets in `build/` and reference implementations in `src/reference/` when needed.

## Python and specification conventions

Use typed public functions and Pydantic models for validated records. Keep
pure transformations separate from I/O. Put third-party calls behind a small,
named gateway when tests need a controlled boundary. Mock only those gateways,
with `Mock(spec=GatewayClass)`. Keep real HTTP, filesystem, executable discovery,
and Docling checks where their behavior matters.

Place `module_spec.py` beside `module.py`. Do not create a separate `tests/`
directory. Pytest discovers `Describe*` classes and `should_*` methods.

Use fixtures in the nearest `conftest.py`, plain assertions, and parametrized
cases. Do not use `unittest.TestCase`, importlib loading, or imports from
another spec. Separate setup, action, and assertions with blank lines.

Test outcomes, not private methods, call order, or elapsed time. Test
interrupted work and its later resumption together.

Run `uv run pytest --cov` before you complete a change. Combined statement and
branch coverage must reach 90%. But the threshold does not replace checking the
behavior changed. The coverage report includes production scripts and excludes
specs and fixtures.

### Complete starter validation environment

Setup for a selected target prepares the demo, not the whole test suite of the
starter. The suite also runs emulator checks for CoCo 1, CoCo 2, and CoCo 3.
Install native tools using [toolchain.md](toolchain.md). Then provision all
three ROM profiles without changing any project:

```sh
uv sync --locked
uv run python - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import provision, verify_installed

root = Path.cwd()
for target in ("coco1", "coco2", "coco3"):
    provision(root, target)
    verify_installed(root, target)
PY
```

Stop if provisioning fails. Provisioning uses `roms.json` checksums and keeps
firmware under ignored `local/roms/`. It does not change the application's
target.

Then run:

```sh
uv run python scripts/doctor.py --profile demo --target coco1 &&
uv run python scripts/doctor.py --profile demo --target coco2 &&
uv run python scripts/doctor.py --profile demo --target coco3 &&
uv run pytest --cov -ra
```

The full run includes real Docling conversion. Its first run can download model
weights. Inspect the exit status, coverage result, and skip reasons. Passing
tests with missing-machine integrations skipped do not establish a complete
validation pass.

Keep the 90% gate and the full measured scope. Provisioning removes an
environment gap but does not guarantee enough coverage.

### Other checks

Ruff enforces a maximum function complexity of 10. Keep larger workflows readable
by separating validation, decisions, and external operations.

For dependency checks, audit the lockfile, including optional groups:

```sh
uv export --all-groups --format requirements-txt --no-emit-project \
  | uvx pip-audit -r /dev/stdin --disable-pip
uv pip list --outdated
```

Do not audit only the temporary environment containing pip-audit.

This starter has no MkDocs site. Check the linked Markdown guides and examples.

After changes, run:

- `uv run pytest -m 'not integration'`
- `uv run ruff check .`
- `uv run ruff format --check .`

For changes to document conversion, also run `uv run pytest -m integration`.
This command loads real Docling models.

For CoCo binaries and emulator checks, load [toolchain.md](toolchain.md).
For books and OCR, load [references.md](references.md).

## Repository validation CLI

Use the existing locked environment. Prepare it explicitly with
`uv sync --locked` when needed. The runner never installs packages or tools.
On macOS, the supported host is Apple Silicon.

```sh
uv run --locked --no-sync python scripts/validate_repository.py list
uv run --locked --no-sync python scripts/validate_repository.py run root --heavy
uv run --locked --no-sync python scripts/validate_repository.py run assets sudo-policy
```

Each selection runs pytest, Ruff, and Ruff's format check in separate processes
from the repository root. Root selects the complete `scripts` and `examples`
suites, including integrations. Root needs `--heavy`. It preserves the full
coverage gate of the starter. It does not present a partial run as root
validation.

Experiment names select only that experiment. Coverage uses its `coverage.ini`
where present. Otherwise, coverage uses the root configuration with the
documented module targets.

The light experiment scopes are `assets`, `linux-onboarding`, and
`sudo-policy`. The last two run host specifications with
controlled process boundaries, not the Docker onboarding or sudo journeys.
`linux-onboarding`, `macos-onboarding`, and `sudo-policy` have no scoped
coverage gate. The runner does not invent one or borrow the root's
measured source scope.

Other experiments need `--heavy`, even if their prerequisites are cached.
The runner checks the entire selection before any work starts. `all` means all
experiments, excluding root. Scopes run sequentially and stop at the first failed
check. These commands explicitly opt into expensive work:

```sh
uv run --locked --no-sync python scripts/validate_repository.py run root --heavy
uv run --locked --no-sync python scripts/validate_repository.py run \
  collect-room-output --heavy
uv run --locked --no-sync python scripts/validate_repository.py run all --heavy
```

Before you opt in, read the README or validation guide of the selected
experiment.

Root with `--heavy` needs the complete starter environment described above.
Docling can download model weights. Animation and output suites can download
pinned XRoar sources and compile private emulators. Native runs need the
assembler, build tools, and verified ROMs for their documented machines.

Some scopes have their own prerequisites:

- `macos-onboarding` needs installed `lwasm`. It checks current-host recovery
  with fixture firmware and a recording launcher, not clean-host installation.
- `collect-room-journey` downloads the pinned XRoar release and builds it with
  the example's keyboard and audio hooks. It needs CoCo 1/2 ROMs.
- `collect-room-output` builds a private emulator from `COLLECT_ARCHIVE`
  (default `local/research/audio-timing/xroar-1.12.1.tar.gz`). It needs
  CoCo 1/2 ROMs.

The runner does not prepare these inputs, launch experiment setup scripts, or
start an interactive GUI. Missing prerequisites follow the behavior of the
selected suite: some fail, while others skip tests. The runner preserves these
outcomes and does not convert skips into failures.

Inspect the pytest log and JUnit report before you claim full validation.
A zero exit alone does not mean every check ran.

Each invocation retains a new directory under ignored `build/validation/`.
Each scope has numbered merged stdout/stderr logs and JSON records. The JSON
records contain the command and the raw exit status of the child.
Pytest writes JUnit results there and, where configured, coverage JSON and its
data file. Temporary test files are isolated per invocation. The terminal
prints log paths and statuses.

An ordinary child failure becomes the runner's exit status. Signal termination
uses `128 + signal`, and the JSON retains the raw negative status. The runner
records a process that cannot start as 127. Later checks do not run after
failure. A retry leaves earlier logs intact.

Evidence paths that an experiment owns still obey the experiment's own rules.
These results establish only what the selected tests measure. They do not
establish physical hardware operation, visible display, or audible output.
