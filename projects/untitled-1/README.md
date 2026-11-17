# Untitled 1

A sliding puzzle about evolution, for the CoCo 3. The owner has not named it
yet.

Creatures sit on a grid. Each arrow key slides all creatures in that
direction. When two equal creatures meet, they merge into the next creature of
the evolution chain. After each move, a new simple creature appears in an empty
square. The player wins when the last creature of the chain appears. The game
ends when no move can change the grid.

The program draws the 4 by 4 board in 320×192 with 16 colours. The arrow
keys slide and merge the creatures. The game starts from a fixed layout, and
new creatures do not appear yet. Random new creatures, the win and the end of
the game come next.

## The rules of a move

- One press of one arrow key makes one move. A held arrow does not repeat.
- Two arrows held together do nothing. An arrow held when the game starts
  does nothing until you release it and press it again.
- In a move, all creatures slide as far as they can toward that edge.
- Two equal creatures that meet merge into the next creature of the chain.
  The pairs nearest the edge merge first.
- A creature made by a merge does not merge again in the same move.
- The human is the last creature. Two humans do not merge.
- Other keys do nothing.

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
  creatures, one move for each press (agent-selected prototype choice).
- Loader: XRoar runs the DECB binary directly (starter default)
- Disk: `coco.toml` names Disk BASIC, `disk11.rom`, for a disk image only.
  Read [disk images](../../guidance/starter/toolchain.md#disk-images).

## Check

```sh
uv run python scripts/coco.py check projects/untitled-1
```

The check runs two builds. Each build stops at `ready` 21 times, once for
each scan of the keyboard. At each stop, the check compares the 30720 screen
bytes at physical `$00000` and XRoar's rendered picture with
[expected.py](expected.py).

- **The main build** gets no keys. The board must stay at the opening layout.
- **The keys build** plays [keys.txt](keys.txt) through XRoar's keyboard
  matrix and the program's own scanner. Each line gives the held keys and the
  board after that scan. The boards are written by hand from the rules above.
  The model in `expected.py` applies the rules too, and it must agree with
  each board.

The opening layout has one rule in each row: four equal creatures, a merged
creature next to an equal one, gaps, and two humans. The script tests a held
arrow, two arrows, a new arrow while another is held, a move that changes
nothing, and Space.

The model converts the creature pictures by its own route. It does not read
bytes from the build or the emulator.

These faults were run once on a copy, and each failed the check:

| Fault | First failed stop |
| --- | --- |
| `WRONG_COLUMN`: Up is read from the wrong column | 7: no move up |
| `HELD_REPEAT`: a held arrow moves at every scan | 2: the startup arrow moves |
| `REMERGE`: a merged creature can merge again | 4: three microbes make a trilobite |
| `$FF99` for 640×192 with 4 colours (board step) | rendered check only |
| No page advance in the screen window (board step) | 119 screen bytes |

The defines of the first three faults are only for the check. The game that
you play has none of them.

Not checked: the rule that two humans do not merge has no fault control.
Physical keys, the host keyboard and window focus are not tested.

The capture shows the middle 512 of the 640 samples of each line. It shows
all of the board, but not the outer 32 pixels at each side of the screen.
XRoar sets its picture window once for each field, from the mode at that
time. Thus the program waits some fields after the mode change before the
first stop.

Memory: the program, the sprites and the program's own stack are at CPU
`$2000-$5FFF`. CPU `$6000-$7FFF` is the window to the screen. The program
masks IRQ and FIRQ, so nothing of BASIC runs after the start.
