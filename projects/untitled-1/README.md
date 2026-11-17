# Evolve

A sliding puzzle about evolution, for the CoCo 3. The owner named it Evolve.
The project folder keeps its first name, `untitled-1`.

Creatures sit on a grid. Each arrow key slides all creatures in that
direction. When two equal creatures meet, they merge into the next creature of
the evolution chain. After each move, a new simple creature appears in an empty
square. The player wins when the last creature of the chain appears. The game
ends when no move can change the grid.

The title screen shows the name and all eleven creatures, like a family
that poses for a photo. Press Space to start.

The program draws the 4 by 4 board in 320×192 with 16 colours. The arrow keys slide and merge the
creatures. When you win, the squares turn green and the words "YOU WIN!"
appear. When you lose, the squares turn red and the words "GAME OVER" appear.
Then press Space for a new game.

The program draws each change on a second screen that you do not see. Then
it shows that screen between two video frames, so the whole change appears at
once.

## The rules of a move

- One press of one arrow key makes one move. A held arrow does not repeat.
- Two arrows held together do nothing. An arrow held when the game starts
  does nothing until you release it and press it again.
- In a move, all creatures slide as far as they can toward that edge.
- Two equal creatures that meet merge into the next creature of the chain.
  The pairs nearest the edge merge first.
- A creature made by a merge does not merge again in the same move.
- A press that changes nothing is not a move.
- After each move, a microbe appears in an empty square.
- You win when the human appears. The squares turn green.
- You lose when the board is full and no two neighbours are equal. The
  squares turn red.
- After a win or a loss, the arrows do nothing. Space starts a new game with
  two microbes.
- In play, other keys do nothing.

The squares change colour because palette register 1 changes. Grey parts of
the creatures change colour too. Words on the screen come later.

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

Two creatures of level `n` merge into one creature of level `n + 1`.

## New creatures

The owner gave these rules:

- The game starts with 2 creatures on the board.
- A new creature is always the first creature of the chain, the microbe.
- A new creature appears after every move.

A press that changes nothing on the board is not a move, so no creature
appears (agent default). Without this rule, the player can fill the board with
presses that do nothing. New creatures appear in a random empty square
(agent default).

### The random choice

The generator is a 16-bit xorshift with the shifts 7, 9 and 8 (agent
choice). One step is:

1. `seed = seed XOR (seed << 7)`
2. `seed = seed XOR (seed >> 9)`
3. `seed = seed XOR (seed << 8)`

All values are 16 bits. The seed starts at `$7A35`. The generator steps once
at each keyboard scan, except the first scan. It steps once more for each new
microbe. Then the low byte of the seed, modulo the number of empty squares,
gives `k`. The microbe goes in empty square `k`, counted from 0 in row order.

The scans step the generator, also on the title screen. Thus the time
before you press Space changes the first board, and the time between your
presses changes where the microbes appear.

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
- Name: Evolve (owner requirement)
- Title screen: the eleven creatures pose like a family for a photo (owner
  requirement). The name, the backdrop and the two rows are agent choices.
- Board: 4 by 4 squares (agent-selected prototype choice)
- Display: two screens, and a switch in the vertical blank, so that a change
  appears at once (owner requirement)
- Controls: the keyboard (owner requirement). The four arrow keys slide the
  creatures, one move for each press. Space starts a game on the title
  screen, and a new game after a win or a loss (agent-selected prototype
  choices).
- Words: an 8×8 font drawn in [font.py](font.py) (agent choice)
- Loader: XRoar runs the DECB binary directly (starter default)
- Disk: `coco.toml` names Disk BASIC, `disk11.rom`, for a disk image only.
  Read [disk images](../../guidance/starter/toolchain.md#disk-images).

## Next steps

In order of importance:

1. Sound: a short sound for a merge, and a larger sound for the first
   appearance of each creature.
2. A score.
3. Faster drawing, so that the next board is ready sooner after the key
   press. The owner found the game responsive, so this is not urgent.
4. A board colour that is not grey, so that grey creatures stand out.

## Check

```sh
uv run python scripts/coco.py check projects/untitled-1
```

The check runs five builds. Each build stops at `ready` 21 times, once for
each scan of the keyboard. At each stop, the check compares both screens,
30720 bytes each at physical `$00000` and `$08000`, with
[expected.py](expected.py). The shown screen must hold the new picture, and
the hidden screen the picture before it. The check also compares XRoar's
rendered picture of the shown screen. The rendered picture shows the colour
of the squares.

| Build | Defines | Keys | What it checks |
| --- | --- | --- | --- |
| main | none | none | The title screen. No change without keys. |
| `play` | none | [play.txt](play.txt) | Space on the title, then seven moves of the game that you play, with the random microbes. |
| `rules` | `LAYOUT`, `RULES`, `FIRST_EMPTY` | [keys.txt](keys.txt) | The rules of a move, and the keys. |
| `win` | `LAYOUT`, `WIN`, `FIRST_EMPTY` | [win.txt](win.txt) | The human wins, with its banner. No moves after it. Space starts a new game, and the banner goes. |
| `lose` | `LAYOUT`, `LOSE`, `FIRST_EMPTY` | [lose.txt](lose.txt) | A press that changes nothing. A full board with no pair loses, with its banner. No moves after it. Space. |

The keys go through XRoar's keyboard matrix and the program's own scanner.

The main and `play` builds are the game that you play. The model in
`expected.py` follows the rules and the generator of this README.

The other three builds have test controls, which are only for the check.
`LAYOUT` with `RULES`, `WIN` or `LOSE` starts from a fixed layout.
`FIRST_EMPTY` puts each new microbe in the first empty square. Thus the
scripts give the board and the phase after each scan, written by hand from
the rules. The model must agree with each of them.

These builds do not check
the random choice. The main and `play` builds check it.

The model converts the creature pictures by its own route. It draws the
letters from the drawings in [font.py](font.py), also by its own route. It does
not read bytes from the build or the emulator.

These faults were run once on a copy, and each failed the check:

| Fault | Build | What failed |
| --- | --- | --- |
| `ONE_SCREEN`: the program draws on the shown screen | `play` | screen A: 18262 bytes |
| `KEEP_FRAME`: the banner frame stays after the banner goes | `win` | screen A: 70 bytes |
| `WRONG_COLUMN`: Up is read from the wrong column | `rules` | screen B: 5010 bytes |
| `HELD_REPEAT`: a held arrow moves at every scan | `rules` | screen A: 18117 bytes |
| `REMERGE`: a merged creature can merge again | `rules` | screen A: 908 bytes |
| `SPAWN_ALWAYS`: a microbe after a press that changes nothing | `lose` | screen A: 17954 bytes |
| `NO_SCAN_STEP`: the generator does not step at each scan | `play` | screen A: 1664 bytes |
| `NO_JUDGE`: no win and no loss | `win` | screen A: 4382 bytes |
| `$FF99` for 640×192 with 4 colours (board step) | main | rendered check only |
| No page advance in the screen window (board step) | main | 119 screen bytes |

The fault defines are only for the check. The game that you play has none of
them.

Not checked: a full board that still has an equal pair, which must not lose.
Physical keys, the host keyboard and window focus are not tested.

The check sees the screens at each stop, and one rendered frame after it. It
does not see the frames while the program draws. Thus it shows that the
program draws only on the hidden screen, but not the absence of a ripple. That
comes from the order of the work, and from a person who looks at the game.

The capture shows the middle 512 of the 640 samples of each line. It shows
all of the board, but not the outer 32 pixels at each side of the screen. On
the title screen, the outer parts of the backdrop are outside the capture.
XRoar sets its picture window once for each field, from the mode at that
time. Thus the program waits some fields after the mode change before the
first stop.

Memory: the program, the sprites, the words and the program's own stack are
at CPU `$0E00-$5FFF`. CPU `$6000-$7FFF` is the window to a screen. Screen A is
at physical `$00000` and screen B at `$08000`. The program masks IRQ and FIRQ,
so nothing of BASIC runs after the start. It turns on the GIME's VBORD flag
and reads it at `$FF92`.
