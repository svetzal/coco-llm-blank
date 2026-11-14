# Your first screen

This original example draws a green border and a solid square on a black screen.
It is a starting point for CoCo 1 projects, not a complete game.

Ask your agent to run these steps. Commands start in the project folder:

```sh
sh scripts/bootstrap.sh coco1
uv run python scripts/setup.py --target coco1 --roms-only
uv run python scripts/coco.py check examples/first-screen
uv run python scripts/coco.py run examples/first-screen
```

The last command opens XRoar. Close the window to stop it. Run that command
again whenever you want to see the example.

## Start your own project from this folder

Copy this folder to a new folder, for example `projects/my-demo`, and run the
same commands with that folder's path. No launcher script is needed. The folder
holds three files:

- `main.asm`: the program.
- `coco.toml`: the machine, firmware, memory layout and checkpoint settings.
  The `[targets.coco1]` table records the emulated machine; change it only
  after recording the choice in `local/PROJECT.md`.
- `expected.py`: an independent model of the memory the program must produce.
  Write it from the sourced pixel layout and your requirements, never from the
  assembled bytes. Without it, `check` proves only that the checkpoint was
  reached.

Run `uv run python scripts/coco.py --help` for the commands. The Python under
`scripts/` holds no CoCo knowledge; you do not need to read or copy it.

## What the example proves

The check assembles the actual source and runs it in XRoar. It starts with
nonzero RAM, waits for the program's ready label, and checks all 6144 screen
bytes against the independent pixel specification in `expected.py`. An
unreachable checkpoint must produce no snapshot. This prevents startup RAM from
passing as a result.

The check passes on Apple Silicon macOS and in a clean Ubuntu 24.04 container.
It does not inspect the displayed image or prove physical hardware operation.
A visual check is still needed after changes to display setup.

## Target and memory

The target is a CoCo 1 with 32 KiB RAM, NTSC video, and a stock-clock 6809.
The display is 256 by 192 pixels with two colours. Each byte holds eight pixels,
so each row uses 32 bytes and the screen uses 6144 bytes.

| Purpose | Address range |
| --- | --- |
| Screen | $0400-$1BFF |
| Ready marker | $2FFF |
| Program | Starts at $3000; see generated symbols |
| Reserved stack | $7E00-$7EFF; starts at $7F00 and grows down |

The program disables interrupts while showing the static image. It does not
return to BASIC. An interactive or animated program must choose its own timing
and interrupt handling instead of assuming this loop provides them.

## Check the sources before adapting it

The program is original code. Its hardware facts were checked against:

- Tandy, *Color Computer Technical Reference Manual*, PDF pages 14-15 and 30-31:
  PIA fields, SAM display base, stock clock, and the 256x192 mode row.
- Inman, *Assembly Language Graphics for the TRS-80 Color Computer*, PDF pages
  106-108: screen size, two-colour pixel layout, and mode selection.

The SAM mode bits are V2..V0 = 110. The PIA high nibble is 1111, CSS is zero,
and the program preserves the low three data bits. The display offset is two
512-byte units. Read the tables and diagrams before changing those values.

Use [reference lookup](../../guidance/starter/references.md) to download and inspect
those pages. No book pages, converted text, or firmware are included here.
Build outputs and snapshots stay in ignored `build/first-screen/`.
