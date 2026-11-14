# Draw the prepared RG6 assets on CoCo 1/2

This original 6809 consumer connects the existing
[host converter](../assets/README.md) to a bounded target execution check.
It loads a DECB executable containing prepared picture rows, a terrain-pointer
translation table and room data. The CPU clears the screen and draws all 48
cells. It does not copy the host bundle's precomposed framebuffer.

The converter remains a host-only tool. JSON parsing and descriptor validation
happen on the host; this is not a JSON parser, disk loader or general target
asset format. No existing example or production script is changed.

## Run from a fresh clone

From the repository root, prepare the locked Python environment and have
LWTOOLS and XRoar available. See [toolchain setup](../../guidance/starter/toolchain.md)
if they are absent. These commands do not install global native tools or launch
a GUI. Firmware setup writes only ignored local storage and does not convert
books or change an existing project contract.

```sh
uv sync --locked
uv run --no-sync python - <<'PYTHON'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import provision, verify_installed

for target in ("coco1", "coco2"):
    provision(Path.cwd(), target)
    verify_installed(Path.cwd(), target)
PYTHON
uv run --no-sync python scripts/doctor.py --profile demo --target coco1
uv run --no-sync python scripts/doctor.py --profile demo --target coco2
uv run --no-sync python experiments/asset-loading/loading.py
COVERAGE_FILE=build/asset-loading/.coverage uv run --no-sync pytest \
  experiments/asset-loading --cov=loading \
  --cov-config=experiments/asset-loading/coverage.ini \
  --cov-report=term-missing \
  -o cache_dir=build/asset-loading/pytest-cache \
  --basetemp=build/asset-loading/pytest-tmp
uv run --no-sync ruff check experiments/asset-loading
uv run --no-sync ruff format --check experiments/asset-loading
markdownlint --fix experiments/asset-loading/README.md \
  guidance/techniques/validation/asset-loading.md
markdownlint experiments/asset-loading/README.md \
  guidance/techniques/validation/asset-loading.md
```

The executable search honors the repository's `LWASM` and `XROAR` overrides
and local native-tool installation. The tested host already had both tools
and verified firmware. No native install or download was needed in this pass.
The project bootstrap is the normal full setup path; it may install global
tools on macOS. This bounded experiment uses the provisioner and doctor directly
when the environment is already prepared.

Use `--output build/asset-loading/another-run` for another evidence directory.
Default results are under ignored `build/asset-loading/run/`. Each test fixture
uses its own `spec-*` directory. `--basetemp` is a disposable test directory;
pytest replaces its contents. Do not point it at retained evidence.

`results.json` records resolved commands, tool versions and hashes, ROM hashes,
source/code hashes, symbols, executable and snapshot hashes, and runtime
control results. It starts with `passed: false` before any build. Treat only a
new successful run as evidence; old files in its directory are not certification.
A missing checkpoint cannot reuse an earlier RAM snapshot.

## Explicit experiment configuration

Both runs select XRoar's `cocous` architecture, 6809 CPU, 32 KiB RAM, NTSC,
non-T1 MC6847, no cartridge, null UI and null audio, and `-c /dev/null`.
The CoCo 1 run uses `bas11.rom` and `extbas10.rom`; the CoCo 2 run uses
`bas12.rom` and `extbas11.rom`. The runner calls `roms.verify_installed` before
each launch and passes its absolute ROM paths. Missing, partially installed
and corrupt ROM selections fail before starting the emulator.

These are agent-selected prototype settings, using the documented CoCo 1
32 KiB/NTSC default and an explicit matching CoCo 2 experiment configuration.
They are not owner-confirmed physical machine specifications. This README is
the isolated experiment contract; it does not rewrite shared `local/PROJECT.md`.

The assembly masks IRQ/FIRQ, initializes DP and stack, selects normal SAM CPU
rate, and preserves the low three PIA port bits during display setup. It relies
on BASIC firmware's initial PIA direction setup. `-no-ratelimit` accelerates
host execution, not the emulated CPU clock. No timing claim is made.

| Allocation | Inclusive addresses |
| --- | --- |
| Framebuffer guard before | `$03FF` |
| RG6 framebuffer | `$0400–$1BFF` |
| Framebuffer guard after | `$1C00` |
| Program, state and prepared tables | `$3000` to `program_end - 1` |
| Reserved stack | `$7E00–$7EFF` (initial S `$7F00`) |

The build rejects a program reaching the stack reservation. The unmodified
build occupies `$3000–$310A`, 267 bytes, excluding the framebuffer and stack.
All four pictures occupy 32 bytes; the room uses 48 bytes and pointer table
uses eight. These are this experiment's allocations, not a minimum-memory
claim or a BASIC-callable interface. It never returns to BASIC.

## Original artwork and validation boundary

The input is the tracked `experiments/assets/art.json`, format
`original-rg6-room-v1`. Its original art identity is:

| Terrain | Asset ID | Picture | Literal rows in hexadecimal |
| --- | --- | --- | --- |
| Floor 0 | 10 | Offset dot | `00 00 20 00 00 00 00 00` |
| Wall 1 | 40 | Open notched frame | `ff 80 b8 a0 ae 82 80 fd` |
| Collectible 2 | 70 | Offset sparkle | `20 70 f8 70 20 00 02 00` |
| Exit 3 | 90 | Right-pointing stroke | `e0 80 a0 a4 be 84 80 c1` |

The art was created for the existing host experiment, not copied from a
historical game or the older tile-room assembly. The room arrangement is that
repository's original eight-column, six-row layout. This consumer adds original
assembly and tests; it does not claim new authorship of the input art.

Each asset declares 8×8 pixels, one byte per row, MSB-first 1bpp,
`rg6-css0-black-green`, and top-left anchor `[0, 0]`. The consumer captures the
bundle bytes and compares them exactly with the public `prepare.prepare`
result for the current source. That validates descriptors, source digest,
references, pixel bytes and the host framebuffer before generation. It does not
call private converter functions or add target responsibilities to the converter.

The assembly include contains picture labels keyed by asset ID, four pointers
in terrain order and 48 terrain cells. Reordering the source asset list leaves
the include unchanged. Assembly and symbols are generated together with
`lwasm --6809 --format=decb`. Identical input gives identical includes, binary
and symbol addresses; this is tested in two separate output directories.

Bad source geometry, altered descriptors, payload changes, a truncated or
missing bundle, stale source digest, wrong screen descriptor and changed mapping
are rejected before assembly. An attempted rebuild first removes its old binary,
symbols and include. Rebuilding after a rejected bundle is tested. This is a
single-writer experiment, not a concurrent publication protocol.

## What the target checks establish

The renderer clears a deliberately poisoned framebuffer, translates terrain
through the pointer table and copies each picture row at a 32-byte screen stride.
After drawing it writes completion marker `$5A` and reaches `ready`. A PC trap
at that symbol captures raw RAM; a second trap on unreachable data must not fire.

The checker compares all 6,144 framebuffer bytes with an independent pixel
oracle using literal picture rows and independently specified cell positions.
It also checks all original picture bytes, all 48 room cells, six guards, the
completion marker and 32 KiB dump size. The literal rows are separately decoded
and compared with every source pixel. The oracle never reads the prepared
framebuffer or generated assembly to decide its expected image.

Actual assembly controls complement picture bytes and write past the framebuffer.
Both must be detected on both ROM configurations. Another test builds a valid
source with swapped floor/wall assignments, runs it on CoCo 1 and requires an
oracle mismatch. Snapshot controls alter the completion marker, last framebuffer
byte, an asset guard, art and room data, and truncate the capture. A real
unreachable checkpoint run must remove its stale snapshot and produce no new one.

See [source readings and results](../../guidance/techniques/validation/asset-loading.md).
Headless RAM checks establish execution and memory contents. They do not establish
rendered appearance, physical hardware, disk loading, PAL/T1 behavior, CoCo 3,
controls, audio, frame rate or runtime parsing of damaged binary data.
