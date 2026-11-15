# Project name

Replace this file with the README of your project. Copy the `template/` folder
to `projects/<name>/` first. Name the folder after the idea of the owner.

The program in this folder prints `HELLO, WORLD!` with the Color BASIC ROM and
returns to BASIC. Replace it with your program.

## What the owner asked for

Write the request of the owner here, in plain words.

## How to run it

Commands start in the starter folder:

```sh
uv run python scripts/coco.py run projects/<name>
uv run python scripts/coco.py check projects/<name>
```

The `run` command opens XRoar. Close the window to stop it.

## Contract

Write each item before you write hardware-dependent code. Keep `coco.toml`
the same as this list. Mark a starter default as a default, not as a choice of
the owner.

- CoCo model and revision: CoCo 1 (starter default)
- XRoar machine profile: `cocous` (starter default)
- RAM: 32 KiB (starter default)
- CPU and clock: 6809 at the stock clock (starter default)
- Video standard: NTSC (starter default)
- Firmware: Color BASIC 1.1, `bas11.rom`, and Extended Color BASIC 1.1,
  `extbas11.rom` (starter default)
- Controls: none yet
- Loader: XRoar runs the DECB binary directly (starter default)
- Disk: `coco.toml` names Disk BASIC, `disk11.rom`, for a disk image only.
  Read [disk images](../guidance/starter/toolchain.md#disk-images).

## Check

`coco.toml` names the label where the check takes its snapshot.

Add `expected.py` with an independent model of the result when the program draws
or stores something that you can check. Read
[development practice](../guidance/starter/development.md) for the files and
the commands.
