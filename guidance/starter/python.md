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

The root pytest configuration in `pyproject.toml` collects the `*_spec.py`
files under `scripts/`, including the emulator integrations.
CI runs `uv run pytest --cov`, Ruff and Ruff's format check.
Keep test evidence that must survive a rerun under ignored `local/` or
`build/`. Do not keep it in a pytest temporary directory.

Examples have no specs. `scripts/coco_spec.py` runs the real check of each
example and its negative controls.

### Complete starter validation environment

Setup for a selected target prepares the demo, not the whole test suite of the
starter. The suite also runs emulator checks for CoCo 1, CoCo 2, and CoCo 3.
Install native tools using [toolchain.md](toolchain.md). Then provision the ROM
profile of each standard target without changing any project:

```sh
uv sync --locked
uv run python - <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import TARGETS, provision, verify_installed

root = Path.cwd()
for target in TARGETS:
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
uv run python scripts/doctor.py --profile demo --target coco2b &&
uv run python scripts/doctor.py --profile demo --target coco3 &&
uv run pytest --cov -ra
```

The full run includes real Docling conversion. Its first run can download model
weights. Inspect the exit status, coverage result, and skip reasons. Passing
tests with missing-machine integrations skipped do not establish a complete
validation pass.

Keep the 90% gate and the full measured scope. Provisioning removes an
environment gap but does not guarantee enough coverage.

### Repository size limits

The root suite runs `scripts/repository_size_spec.py`, so CI checks the size of
the tracked files. Together, the tracked files except `uv.lock` must be
1,200,000 bytes or less. Each tracked file except `uv.lock` must be
100,000 bytes or less. The check measures the files in the working tree.
Untracked files do not count.

Raise a limit only as a deliberate decision. Change its constant in
`scripts/repository_size.py` in its own commit. Give the reason in the commit
message.

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
