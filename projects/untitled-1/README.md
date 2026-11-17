# Untitled 1

A sliding puzzle about evolution, for the CoCo 3. The owner has not named it
yet.

Creatures sit on a grid. Each arrow key slides all creatures in that
direction. When two equal creatures meet, they merge into the next creature of
the evolution chain. After each move, a new simple creature appears in an empty
square. The player wins when the last creature of the chain appears. The game
ends when no move can change the grid.

The program in this folder is still the template: it prints `HELLO, WORLD!`
and returns to BASIC.

## What the owner asked for

> A CoCo 3 game with some richer graphics. Call it untitled-1 for now.

> A sliding puzzle where matching tiles merge, with creatures that evolve:
> fish, primates, dinosaurs, and so on. Keyboard controls.

The game is original: it uses this kind of play, but its own name, creatures
and art.

## The evolution chain

This chain is a proposal. The owner has not confirmed it.

| Level | Creature |
| --- | --- |
| 1 | Microbe |
| 2 | Jellyfish |
| 3 | Trilobite |
| 4 | Fish |
| 5 | Frog |
| 6 | Lizard |
| 7 | Dinosaur |
| 8 | Bird |
| 9 | Mouse |
| 10 | Primate |
| 11 | Human |

Two creatures of level `n` merge into one creature of level `n + 1`. A new
creature is level 1 on most moves and level 2 on some moves.

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
- Graphics: richer than the CoCo 1 and 2 (owner requirement). GIME 320×192
  with 16 colours, `$FF99` = `$1E` (agent-selected prototype choice). Read
  [the GIME graphics guide](../../guidance/techniques/gime-graphics.md).
- Board: 4 by 4 squares (agent-selected prototype choice)
- Controls: the keyboard (owner requirement). The four arrow keys slide the
  creatures (agent-selected prototype choice).
- Loader: XRoar runs the DECB binary directly (starter default)
- Disk: `coco.toml` names Disk BASIC, `disk11.rom`, for a disk image only.
  Read [disk images](../../guidance/starter/toolchain.md#disk-images).

## Check

`coco.toml` names the label where the check takes its snapshot.
