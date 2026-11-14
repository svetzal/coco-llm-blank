# Python support tools

Load this file when writing host-side scripts, asset converters, reference
implementations, or tests. Run commands from the repository root.

## Environment

Use `uv sync --locked` to create `.venv` from `uv.lock`. Use `uv run` for scripts
and checks. Do not install into system Python or maintain a second requirements
file. Declare a dependency with `uv add`; commit `pyproject.toml` and `uv.lock`
together. Python 3.13 is selected in `.python-version`.

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
synchronizing the environment. Keep the group flag on commands that use them.

## What Python does here

The original `coco-llm` used Python for fixed-point reference models, exact test
vectors, waveforms and WAV output, palette and sprite packing, bitmap fonts,
RS-DOS disk images, and XRoar test/capture orchestration. Those are useful
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

Place `module_spec.py` beside `module.py`; do not create a separate `tests/`
directory. Pytest discovers `Describe*` classes and `should_*` methods. Use
fixtures in the nearest `conftest.py`, plain assertions, and parametrized cases.
Do not use `unittest.TestCase`, importlib loading, or imports from another spec.
Separate setup, action, and assertions with blank lines. Test outcomes rather
than private methods, call order, or elapsed time. Test interrupted work and its
later resumption together.

Run `uv run pytest --cov` before completing a change. Combined statement and
branch coverage must reach 90%, but the threshold does not replace checking the
behavior changed. The coverage report includes production scripts and excludes
specs and fixtures.

### Complete starter validation environment

Selected-target setup prepares the demo, not the whole starter test suite.
The suite also runs CoCo 1, CoCo 2, and CoCo 3 emulator checks. Install native
tools using [toolchain.md](toolchain.md), then provision all three ROM profiles
without rerunning project setup or changing `local/PROJECT.md`:

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

Stop if provisioning fails. This uses `roms.json` checksums and keeps firmware
under ignored `local/roms/`; it does not change the application's target.
Then run:

```sh
uv run python scripts/doctor.py --profile demo --target coco1 &&
uv run python scripts/doctor.py --profile demo --target coco2 &&
uv run python scripts/doctor.py --profile demo --target coco3 &&
uv run pytest --cov -ra
```

The full run includes real Docling conversion; its first run can download model
weights. Inspect the exit status, coverage result, and skip reasons. Passing
tests with missing-machine integrations skipped do not establish a complete
validation pass. Keep the 90% gate and the full measured scope; provisioning
removes an environment gap but does not guarantee sufficient coverage.

### Other checks

Ruff enforces a maximum function complexity of 10. Keep larger workflows readable
by separating validation, decisions, and external operations.

For dependency checks, audit the lockfile, including optional groups:

```sh
uv export --all-groups --format requirements-txt --no-emit-project \
  | uvx pip-audit -r /dev/stdin --disable-pip
uv pip list --outdated
```

Do not audit only the temporary environment containing pip-audit. There is no
MkDocs site in this starter; check the linked Markdown guides and examples.

Run `uv run pytest -m 'not integration'`, `uv run ruff check .`, and
`uv run ruff format --check .` after changes. For document conversion changes,
also run `uv run pytest -m integration`; this loads real Docling models.

For CoCo binaries and emulator checks, load [toolchain.md](toolchain.md).
For books and OCR, load [references.md](references.md).
