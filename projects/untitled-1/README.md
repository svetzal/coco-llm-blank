# Untitled 1

A game for the CoCo 3 with richer graphics than the CoCo 1 and 2 can show. The
owner has not named it yet. The game design is not decided yet.

The program in this folder is still the template: it prints `HELLO, WORLD!`
and returns to BASIC.

## What the owner asked for

> A CoCo 3 game with some richer graphics. Call it untitled-1 for now.

## How to run it

Commands start in the starter folder:

```sh
uv run python scripts/coco.py run projects/untitled-1
uv run python scripts/coco.py check projects/untitled-1
```

The `run` command opens XRoar. Close the window to stop it.

## Contract

The owner chose the CoCo 3, 512 KiB, the 6309 and NTSC.

The other values come from the `coco3` table in
[the target tables](../../guidance/starter/toolchain.md#target-tables). They are
defaults for the CoCo 3, not choices of the owner.

- CoCo model and revision: CoCo 3 (owner requirement) with the 1986 GIME
  (target default)
- XRoar machine profile: `coco3` (target default)
- RAM: 512 KiB (owner requirement)
- CPU and clock: Hitachi 6309 (owner requirement) at the stock clock (target
  default)
- Video standard: NTSC (owner requirement)
- Firmware: the CoCo 3 ROM, `coco3.rom` (target default)
- Graphics: richer than the CoCo 1 and 2 (owner requirement). The mode is not
  chosen yet.
- Controls: not decided yet
- Loader: XRoar runs the DECB binary directly (starter default)
- Disk: `coco.toml` names Disk BASIC, `disk11.rom`, for a disk image only.
  Read [disk images](../../guidance/starter/toolchain.md#disk-images).

## Check

`coco.toml` names the label where the check takes its snapshot.
