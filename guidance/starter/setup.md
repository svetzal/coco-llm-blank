# Manual setup and checks

Use this guide if you want to run setup yourself or diagnose a setup problem.
For an agent-led start, use the [README](../../README.md).
Run all commands from the starter folder.

## Bootstrap

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
Intel Macs are unsupported.

If permissions or installation fail, use
[toolchain.md](toolchain.md). Its
[supported hosts](toolchain.md#supported-hosts) section gives the limits.

Bootstrap builds XRoar from its pinned source release. This build needs a C
compiler. On macOS, install the Xcode Command Line Tools with
`xcode-select --install` if bootstrap asks for them. Read
[Instrumented XRoar](toolchain.md#instrumented-xroar).

Bootstrap also builds ToolShed. Directly launched demos do not need it. The
`disk` command of `scripts/coco.py` needs it to make disk images.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/). Then run:

```sh
uv sync --locked
uv run python scripts/setup.py
```

uv creates a real `.venv` using the Python version in `.python-version` and the
packages pinned by `uv.lock`. Setup downloads the reference manifest and converts
it with Docling. With `--roms-only` and no `--target`, setup asks for `coco1`,
`coco2`, `coco2b` or `coco3`. Full-book conversion is slow.
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
No ROM bytes ship in Git.

Bootstrap already does this step. For an existing checkout, `--roms-only`
prepares firmware without reinstalling tools or converting books.

Bootstrap checks the installed firmware for the selected target.
`scripts/coco.py` checks the ROMs in the project settings before each launch.
If a checksum fails, correct the firmware before you launch XRoar.
See [toolchain](toolchain.md#firmware-and-launching) for launch options.

## Reference conversion

Docling processes layout, OCR, and tables locally. The first conversion
downloads model weights.

Results are in ignored `local/`:

- source PDFs
- page-numbered Markdown
- structured page records
- figure and full-page PNGs
- an index that reports completed pages

The Markdown links images for direct multimodal inspection. Reruns reuse
completed pages. A new range adds pages without losing earlier work.
Read [reference lookup](references.md) for cache behavior and limits.
OCR still needs checking, especially for assembly code and diagrams.

Archive availability does not change copyright or licensing. Downloaded and
derived content stays outside Git.

## Native CoCo tools

LWTOOLS and ToolShed are separate host installations. XRoar is built from
source into ignored `local/toolchain/`. Check all three with:

```sh
uv run python scripts/doctor.py
```

Read [toolchain](toolchain.md) for executable overrides, installation
sources, firmware requirements, and build verification.

## Checks of the starter

To run the starter's own tests and style checks, read
[Python tools](python.md). It gives the commands, the optional dependency
groups and the [complete validation environment](python.md#complete-starter-validation-environment).
