# Manual setup and checks

Use this guide if you want to run setup yourself or diagnose a setup problem.
For an agent-led start, use the [README](../../README.md).
Run all commands from the project folder.

## Agent setup entry point

For a new project, the agent can run:

```sh
sh scripts/bootstrap.sh coco1
```

Use the selected machine target. Bootstrap installs missing uv through Homebrew
when Homebrew is available. If not, it uses the
[official uv installer](https://docs.astral.sh/uv/getting-started/installation/).
If the current agent cannot find `uv` after installation, use the printed uv
path.

Bootstrap prepares the locked Python environment and preserves existing project
notes. It downloads and verifies firmware for the selected machine. It does not
download books or conversion models.

The final check needs the assembler, linker, emulator, and verified firmware.
Missing tools produce a nonzero exit and installation guidance. Bootstrap
installs missing native tools on Apple Silicon macOS and Ubuntu 24.04.
Other Linux distributions still need manual installation of the native tools.
If permissions or installation fail, use [toolchain.md](toolchain.md).

ToolShed is optional for directly launched demos. Disk projects still need it.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). Then run:

```sh
uv sync --locked
uv run python scripts/setup.py
```

uv creates a real `.venv` using the Python version in `.python-version` and the
packages pinned by `uv.lock`. Setup asks for CoCo 1, 2, or 3. It downloads the
reference manifest and converts it with Docling. Full-book conversion is slow.
Start with a few pages to inspect the output:

```sh
uv run python scripts/setup.py --target coco2 \
  --resource assembly-graphics --pages 10:12
```

Use this command to write the local reference index without downloading books
or loading models:

```sh
uv run python scripts/setup.py --target coco3 --guidance-only
```

Use `--list` to list resources. Repeat `--resource ID` to select several books.
Setup never reads or changes `projects/`. Pass `--target` for the firmware
you need. You can install several targets side by side.

Download the selected machine's firmware without starting book conversion:

```sh
uv run python scripts/setup.py --target coco1 --roms-only
```

`roms.json` identifies archive ZIPs and selected ROM members by SHA-256 and
size. Setup verifies cached files too. It preserves different existing
firmware. It writes only selected members to ignored `local/roms/TARGET/`.
The manifest uses the archive's MAME-MESS area. No ROM bytes ship in Git.

Bootstrap already does this step. For an existing checkout, `--roms-only`
prepares firmware without reinstalling tools or converting books.

Before you launch XRoar, validate the files again:

```sh
uv run python scripts/doctor.py --profile demo --target coco1
```

Use the selected target. A successful doctor check of executables only is not
firmware validation. `scripts/coco.py` also verifies the ROMs that a project
names before it starts XRoar. Do not launch XRoar manually to bypass a
checksum error.
See [toolchain](toolchain.md#firmware-and-launching) for launch options.

The Python baseline includes:

- Docling/RapidOCR
- NumPy
- Pillow
- pytest
- Ruff

Optional groups cover interactive prototypes and music analysis. Read
[Python tools](python.md) for their purpose and commands.

## Reference conversion

Docling replaces the original conversion path, which used plain text and
Tesseract. It processes layout, OCR, and tables locally. The first conversion
downloads model weights. Poppler and the Tesseract executable are no longer
necessary.

Results are in ignored `local/`:

- source PDFs
- page-numbered Markdown
- structured page records
- figure and full-page PNGs
- an index that reports completed pages

The Markdown links images for direct multimodal inspection. Reruns reuse
completed pages. A new range adds pages without losing earlier work.
Read [reference conversion](references.md) for cache behavior and limits.
OCR still needs checking, especially for assembly code and diagrams.

The baseline targets Apple Silicon macOS and Linux. Intel Macs are unsupported.
The [Linux onboarding report](validation/linux-onboarding.md) records tested
Ubuntu container journeys. Native desktop onboarding remains unverified.

Archive availability does not change copyright or licensing. Downloaded and
derived content stays outside Git.

## Native CoCo tools

LWTOOLS, ToolShed, and XRoar are separate host installations:

```sh
uv run python scripts/doctor.py
```

Read [toolchain](toolchain.md) for executable overrides, installation
sources, firmware requirements, and build verification. This starter currently
uses assembly. A C compiler is not part of the baseline.

## Agent entry point and checks

Agents start at [AGENTS.md](../../AGENTS.md). It routes each task to ordinary Markdown
files. No skill system is necessary, including for microgentic.

```sh
uv run pytest -m 'not integration'
uv run pytest -m integration
uv run pytest --cov
uv run ruff check .
uv run ruff format --check .
```

Integration tests use an original scanned PDF and the real Docling pipeline.
Their first run needs model downloads. Co-located `*_spec.py` files use the
pytest conventions `Describe*` / `should_*`. Other tests cover:

- local HTTP downloads
- cache and failure behavior
- target preservation
- executable discovery

See [PLAN.md](../../PLAN.md) for scope and remaining work.
