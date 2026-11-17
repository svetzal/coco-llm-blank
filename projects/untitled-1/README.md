# Untitled 1

A sliding puzzle about evolution, for the CoCo 3. The owner has not named it
yet.

Creatures sit on a grid. Each arrow key slides all creatures in that
direction. When two equal creatures meet, they merge into the next creature of
the evolution chain. After each move, a new simple creature appears in an empty
square. The player wins when the last creature of the chain appears. The game
ends when no move can change the grid.

The program draws the 4 by 4 board in 320×192 with 16 colours. It shows a
fixed showcase of all eleven creatures. Input and the game rules are not
written yet.

## What the owner asked for

> A CoCo 3 game with some richer graphics. Call it untitled-1 for now.

> A sliding puzzle where matching tiles merge, with creatures that evolve:
> fish, primates, dinosaurs, and so on. Keyboard controls.

The game is original: it uses this kind of play, but its own name, creatures
and art.

## The evolution chain

The owner confirmed this chain.

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

## The art

The art comes from structured specs in [art/](art/), made with the
[retro-art skill](../../.agents/skills/retro-art/SKILL.md):

- `art/game.contract.json`: the shared style, the 16 colour codes for the
  palette registers and the rules for every picture.
- `art/creatures.spec.json`: one picture for each creature of the chain.

The board has 4 by 4 squares. A square is 56 by 48 pixels, which looks square
on the display. Each creature is 48 by 40 pixels inside its square, with a
transparent background (agent-selected prototype choice). The owner agrees to
each generation before it runs.

Convert each creature with the 16 codes of the contract, in register order:

```sh
uv run python scripts/graphics.py convert projects/untitled-1/art/creatures/05-frog.png --mode gime-320x16 --size 48x40 --codes 00,10,20,30,05,15,25,24,0E,12,21,0B,1C,2D,07,16 --mask --out build/untitled-1/art/05-frog
```

The trilobite is wide and low. Crop it to the creature first, so that its face
is as large as the faces of the other creatures. Add `--box 90,133,849,826`
to its command (the owner chose this).

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

`check` compares the 30720 screen bytes at physical `$00000` and XRoar's
rendered picture with [expected.py](expected.py). The model converts the
creature pictures by its own route. It does not read bytes from the build or
the emulator. Two faults were run once, and each failed the check:

- a wrong display mode (`$FF99` for 640×192 with 4 colours): the rendered
  check fails, and the screen bytes still match
- no page advance in the screen window: 119 screen bytes differ

The capture shows the middle 512 of the 640 samples of each line. It shows
all of the board, but not the outer 17 pixels at each side of the screen.

Memory: the program, the sprites and the program's own stack are at CPU
`$2000-$5FFF`. CPU `$6000-$7FFF` is the window to the screen.

`coco.toml` names the label where the check takes its snapshot.
