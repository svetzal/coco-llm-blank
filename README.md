# coco-llm-blank

A starting repository for agent-assisted Tandy Color Computer projects.
Choose a machine target, prepare local references, and use Python support tools
alongside the CoCo assembler, disk utilities, and emulator. No books or ROMs
ship in this repository.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run:

```sh
uv sync --locked
uv run python scripts/setup.py
```

uv creates a real `.venv` using the Python version in `.python-version` and the
packages pinned by `uv.lock`. Setup asks for CoCo 1, 2, or 3, downloads the
reference manifest, and converts it with Docling. Full-book conversion is slow;
start with a few pages to inspect the output:

```sh
uv run python scripts/setup.py --target coco2 \
  --resource assembly-graphics --pages 10:12
```

To initialize project notes without downloading books or loading models:

```sh
uv run python scripts/setup.py --target coco3 --guidance-only
```

Use `--list` to list resources. Repeat `--resource ID` to select several books.
Existing project notes are preserved. Change the target deliberately in
`local/PROJECT.md` before requesting a different target.

The Python baseline includes Docling/RapidOCR, NumPy, Pillow, pytest, and Ruff.
Optional groups cover interactive prototypes and music analysis. Read
[Python tools](guidance/python.md) for their purpose and commands.

## Reference conversion

Docling replaces the original plain text and Tesseract conversion path.
It processes layout, OCR, and tables locally. The first conversion downloads
model weights. Poppler and the Tesseract executable are no longer required.

Results live in ignored `local/`: source PDFs, page-numbered Markdown,
structured page records, and an index that reports completed pages. Reruns
reuse completed pages. A new range adds pages without losing earlier work.
Read [reference conversion](guidance/references.md) for cache behavior and limits.
OCR still needs checking, especially for assembly code and diagrams.

The baseline targets Apple Silicon macOS and Linux. Intel macOS needs separate
PyTorch compatibility work and is not covered by this environment. Linux still
needs a clean-host verification. Archive availability does not change copyright
or licensing; downloaded and derived content stays outside Git.

## Native CoCo tools

LWTOOLS, ToolShed, and XRoar are separate host installations:

```sh
uv run python scripts/doctor.py
```

Read [toolchain](guidance/toolchain.md) for executable overrides, installation
sources, firmware requirements, and build verification. This starter currently
uses assembly; a C compiler is not part of the baseline.

## Agent entry point and checks

Agents start at [AGENTS.md](AGENTS.md). It routes each task to ordinary Markdown
files. No skill system is required, including for microgentic.

```sh
uv run pytest -m 'not integration'
uv run pytest -m integration
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

Integration tests use an original scanned PDF and the real Docling pipeline.
Their first run needs model downloads. Co-located `*_spec.py` files use
`Describe*` / `should_*` pytest conventions. Other tests cover local HTTP downloads,
cache and failure behavior, target preservation, and executable discovery.

See [PLAN.md](PLAN.md) for scope and remaining work.
