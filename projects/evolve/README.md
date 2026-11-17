# Evolve

A sliding puzzle about evolution, for the CoCo 3. The owner named it Evolve.
Its first name was `untitled-1`.

Creatures sit on a grid. Each arrow key slides all creatures in that
direction. When two equal creatures meet, they merge into the next creature of
the evolution chain. After each move, a new simple creature appears in an empty
square. The player wins when the last creature of the chain appears. The game
ends when no move can change the grid.

The title screen shows the name and all eleven creatures, like a family
that poses for a photo. Press Space to start. If nobody presses a key for 5
seconds, a demo shows how to play.

The program draws the 4 by 4 board in 320×192 with 16 colours. The arrow keys slide and merge the
creatures. When you win, the squares turn green and the words "YOU WIN!"
appear. When you lose, the squares turn red and the words "GAME OVER" appear.
Then press Space for a new game.

Each merge plays a short note. A creature that appears for the first time in
a game plays three rising notes. A win and a loss each have their own sound.

The program draws each change on a second screen that you do not see. Then
it shows that screen between two video frames, so the whole change appears at
once.

### Speed

The program reads the keys once in each video frame. It copies each row with
the 6309 instruction `TFM`. Thus the program needs the 6309. In XRoar, from
one stop of the check to the next (emulated time):

| Step | Time |
| --- | --- |
| A scan with no change | 17 ms, one video frame |
| A move | 100 to 168 ms |
| Space on the title, and the first move after it | 300 to 335 ms each |

Each of these times includes two waits for the vertical blank. The first
move is slower because each screen must first be made black.

A sound uses CPU time while it plays. With the sounds, some moves take one or
two more video frames than without them (measured in the `rules` and `play`
builds).

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

## The score

- Each merge scores 2 to the power of the new creature's level: a jellyfish
  (level 2) scores 4, a trilobite 8, and the human (level 11) 2048 (agent
  choice).
- "SCORE" at the left of the board shows the score of this game. A new game
  starts at 0.
- "BEST" at the right shows the highest score since the program started. It
  is not kept when the CoCo is switched off.
- Each number shows its five low digits (agent choice). A game that reaches
  the human scores about 20000.

## The sounds

The sound is a square wave from the 6-bit DAC. The GIME timer starts each
edge of the wave (agent choice). The notes come from the C major scale, from
C5 (523 Hz) to B6 (1976 Hz) (agent choice).

Each note has an envelope, so that it sounds plucked, not like a beep (owner
request). The envelope has eight equal steps. Each step sets the amplitude:
how far the wave goes above and below the rest level. In DAC units, the
amplitudes are `$10`, `$18`, `$14`, `$10`, `$0C`, `$08`, `$08` and `$04`
(agent choice). Thus the note rises in its first eighth. After that, it fades.

The owner asked for a softer sound than the first envelope. Thus the highest
amplitude is `$18`, not `$20`, and the fade ends lower. One DAC step is
`$04`. After a sound, the DAC goes back to the rest level, `$80`.

| Event | Sound |
| --- | --- |
| A merge | One note of 40 ms. A merge to level L plays note L-2 of the scale: the jellyfish is C5, the human E6. |
| A creature that appears for the first time in this game | Notes L-2, L and L+2 of the scale: 40 ms, 40 ms, then 80 ms. |
| A win | C6, E6 and G6 for 80 ms each, then C7 for 240 ms. |
| A loss | G5 and E5 for 150 ms each, then C5 for 300 ms. |

- If one move makes more than one merge, the highest new level sets the
  sound.
- A loss or a win replaces the sound of its merge.
- A move without a merge is silent.
- A new sound stops a sound that still plays.
- At the start of a game, the highest level on the board counts as seen.
  Thus a new game starts with the microbe seen.

The squares change colour because palette register 1 changes. Grey parts of
the creatures change colour too. Words on the screen come later.

## The demo

The demo teaches the game by cause and effect (owner request). It plays the
real game from fixed boards, with the same creatures and the same sounds. An
arrow key lights first. Then the creatures move.

- On the title screen, 300 scans without a held key start the demo: 5
  seconds (owner request). A held key starts the count again.
- In the demo, Space starts a new game. An arrow key goes back to the title.
  The program reads only these five keys.
- At the end, the demo goes back to the title, and the count starts again.
- The demo does not change the best score.

The left margin shows "DEMO" and a caption. The right margin shows "SPACE TO
PLAY" and the four arrow keys. The key of the next move turns yellow.

| Lesson | Caption | What happens |
| --- | --- | --- |
| 1 | ARROWS PUSH ALL THAT WAY | Left, then Down: two creatures slide to the edge. |
| 2 | AFTER EACH MOVE A NEW ONE COMES | Right: a microbe appears after the move. |
| 3 | TWO ALIKE MERGE AND EVOLVE | Right: two microbes make the first jellyfish, with three notes. |
| 4 | KEEP GOING UP THE CHAIN | Up: two jellyfish make a trilobite, with one note. Up: two trilobites make the first fish, with three notes. |
| 5 | BOARD FULL AND STUCK GAME OVER | Right fills the board, and no two neighbours are equal: the loss. |
| 6 | MAKE THE HUMAN TO WIN! | Left: two primates make the human: the win. |

[demo.py](demo.py) holds the captions and the steps. The new microbe of each
move goes in a square that the demo gives, so each lesson is always the
same. The waits of the demo come to 1940 scans, about 32 seconds (calculated).
The scans that draw take longer, so the demo lasts some seconds more. The
captions and keys are agent choices. Their places are in
[layout.py](layout.py).

## What the owner asked for

> A CoCo 3 game with some richer graphics. Call it untitled-1 for now.

> A sliding puzzle where matching tiles merge, with creatures that evolve:
> fish, primates, dinosaurs, and so on. Keyboard controls.

> I'd like the title screen to default to a demo after 5 seconds.

The owner also asked that the demo teach the cause and effect of each
action. The arrow keys push the tiles. Two equal creatures merge and evolve.
A game can be lost and won. The demo uses the game's creatures and sounds.

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
uv run python scripts/graphics.py convert projects/evolve/art/creatures/05-frog.png --mode gime-320x16 --size 48x40 --codes 00,10,20,30,05,15,25,24,0E,12,21,0B,1C,2D,07,16 --mask --out build/evolve/art/05-frog
```

The trilobite is wide and low. Crop it to the creature first, so that its face
is as large as the faces of the other creatures. Add `--box 90,133,849,826`
to its command (the owner chose this).

## How to run it

Commands start in the starter folder:

```sh
uv run python scripts/coco.py run projects/evolve
uv run python scripts/coco.py check projects/evolve
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
  default). The program uses `TFM`, so it needs the 6309.
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
- Sound: the owner asked for a short sound for a merge, and a larger sound
  for the first appearance of each creature. The notes, the win and loss
  sounds, the square wave and the GIME timer are agent choices. Read
  [the sound guide](../../guidance/techniques/sound.md) and
  [timer sound](../../examples/timer-sound/README.md).
- Demo: after 5 seconds on the title, a demo of moves, merges, a loss and
  a win, with the game's creatures and sounds (owner requirement). The
  lessons, captions, keys and timings are agent choices.
- Loader: XRoar runs the DECB binary directly (starter default)
- Disk: `coco.toml` names Disk BASIC, `disk11.rom`, for a disk image only.
  Read [disk images](../../guidance/starter/toolchain.md#disk-images).

## Next steps

Open lab: sliding-tiles. The lab measures how fast the creatures can slide
to their new squares in a move (owner request).

In order of importance:

1. A faster start: draw only the board's own area when a screen changes
   from the title to the board.
2. A board colour that is not grey, so that grey creatures stand out.

## Check

```sh
uv run python scripts/coco.py check projects/evolve
```

The check runs seven builds. Each build stops at `ready` at scans 1 to 40,
and at scans 300 and 301. The program comes to `ready` once for each scan of
the keyboard.

At each stop, the check compares both screens,
30720 bytes each at physical `$00000` and `$08000`, with
[expected.py](expected.py). The shown screen must hold the new picture, and
the hidden screen the picture before it. The check also compares XRoar's
rendered picture of the shown screen. The rendered picture shows the colour
of the squares.

At each stop, the check also records XRoar's mixer output from the start.
The model gives each sound that started up to that scan. The check finds the
DAC edges and compares each note: its number of edges, and its pitch within
1%. The size of each edge inside a note must follow the envelope, within 10%.
The mixer's scale is not known, so the check uses the median scale of all
the edges.

The model calculates the pitch from the timer: a period is the reload
value plus 2 counts of 279.365 ns on the 1986 GIME. A sound can still play at
a stop, so the last sound can end early in the recording. A sound that the
next move stops is also accepted. The `play` build has one.

| Build | Defines | Keys | What it checks |
| --- | --- | --- | --- |
| main | none | none | The title screen. No change without keys. |
| `play` | none | [play.txt](play.txt) | Space on the title, then seven moves of the game that you play, with the random microbes. |
| `rules` | `LAYOUT`, `RULES`, `FIRST_EMPTY` | [keys.txt](keys.txt) | The rules of a move, the score, and the keys. |
| `win` | `LAYOUT`, `WIN`, `FIRST_EMPTY` | [win.txt](win.txt) | The human wins, with its banner. No moves after it. Space starts a new game, and the banner goes. The best score stays. |
| `lose` | `LAYOUT`, `LOSE`, `FIRST_EMPTY` | [lose.txt](lose.txt) | A press that changes nothing. A full board with no pair loses, with its banner. No moves after it. Space. |
| `demo` | `QUICKDEMO` | none | The full demo, each step at its own scan, and its sounds. Then the title, and the demo again. |
| `demoexit` | `QUICKDEMO` | [demoexit.txt](demoexit.txt) | An arrow ends the demo. A held key on the title starts the count again. Space in the demo starts a game. |

The main build shows the title at scan 300 and the demo at scan 301: 300
scans without a key.

`QUICKDEMO` is a test control. The demo starts after 2 scans, and each wait
of the demo is 1 scan, so the stops show each step. The model plays the
steps of [demo.py](demo.py) by the rules. It must agree with the board that
`demo.py` gives by hand after each move.

The keys go through XRoar's keyboard matrix and the program's own scanner.

The main and `play` builds are the game that you play. The model in
`expected.py` follows the rules and the generator of this README.

The other three builds have test controls, which are only for the check.
`LAYOUT` with `RULES`, `WIN` or `LOSE` starts from a fixed layout.
`FIRST_EMPTY` puts each new microbe in the first empty square. Thus the
scripts give the board, the phase and the score after each scan, written by
hand from the rules. The model must agree with each of them.

These builds do not check
the random choice. The main and `play` builds check it.

The model converts the creature pictures by its own route. It draws the
letters from the drawings in [font.py](font.py), also by its own route. It does
not read bytes from the build or the emulator.

These faults were run once on a copy, and each failed the check:

| Fault | Build | What failed |
| --- | --- | --- |
| `NO_DAA`: the score adds in binary, not in decimal | `rules` | screen A: 74 bytes |
| `NO_BEST`: the best score is not kept | `win` | screen A: 38 bytes |
| `NO_PAGE_STEP`: a row that passes $8000 does not map the next page | `play` | screen B: 2416 bytes |
| `ONE_SCREEN`: the program draws on the shown screen | `play` | screen A: 18262 bytes |
| `KEEP_FRAME`: the banner frame stays after the banner goes | `win` | screen A: 70 bytes |
| `WRONG_COLUMN`: Up is read from the wrong column | `rules` | screen B: 5010 bytes |
| `HELD_REPEAT`: a held arrow moves at every scan | `rules` | screen A: 18117 bytes |
| `REMERGE`: a merged creature can merge again | `rules` | screen A: 908 bytes |
| `SPAWN_ALWAYS`: a microbe after a press that changes nothing | `lose` | screen A: 17954 bytes |
| `NO_SCAN_STEP`: the generator does not step at each scan | `play` | screen A: 1664 bytes |
| `NO_JUDGE`: no win and no loss | `win` | screen A: 4382 bytes |
| `SILENT`: no timer FIRQ | `play` | scan 6: no sound |
| `NO_FIND`: a new creature plays the merge note | `play` | scan 6: 41 edges, not three notes |
| `FLAT`: each merge plays the note below | `play` | scan 6: the notes do not fit |
| `NO_ENVELOPE`: each note stays at its first step | `play` | scan 6: an edge differs from the envelope by 150% |
| `IDLE_KEEP`: a held key does not stop the count on the title | `demoexit` | scan 10: the demo shows, not the title |
| `DARK_KEYS`: no key lights in the demo | `demo` | screen B: 50 bytes |
| `$FF99` for 640×192 with 4 colours (board step) | main | rendered check only |

The fault defines are only for the check. The game that you play has none of
them.

Not checked: a full board that still has an equal pair, which must not lose.
Physical keys, the host keyboard and window focus are not tested.
The mixer output is XRoar's digital signal. The check does not prove the
sound on a television or a physical CoCo, and nobody has listened to it yet.

The check sees the screens at each stop, and one rendered frame after it. It
does not see the frames while the program draws. Thus it shows that the
program draws only on the hidden screen, but not the absence of a ripple. That
comes from the order of the work, and from a person who looks at the game.

The capture shows the middle 512 of the 640 samples of each line. It shows
all of the board, but not the outer 32 pixels at each side of the screen. On
the title screen, the outer parts of the backdrop are outside the capture.

The scores are mostly outside the capture too. The screen bytes include them.
XRoar sets its picture window once for each field, from the mode at that
time. Thus the program waits some fields after the mode change before the
first stop.

Memory: the program, the sprites, the words and the program's own stack are
at CPU `$0E00-$5FFF`. CPU `$6000-$9FFF` is the window to two pages of a
screen, so a row is never split. The program does not use BASIC, which is in
`$8000-$9FFF`. Screen A is
at physical `$00000` and screen B at `$08000`.

The program masks IRQ, so
nothing of BASIC runs after the start. It turns on the GIME's VBORD flag and
reads it at `$FF92`. FIRQ comes only from the GIME timer, for the sound.
The FIRQ jump table entry at `$FEF4` holds `JMP firq`.

Sources disagree whether an interrupt can stop a `TFM`. The HD63B09EP
Technical Reference Guide, PDF 12, says that it can. The 6309 Book, PDF 230,
says that the interrupt waits until the transfer ends. The program keeps
each `TFM` to 256 bytes or fewer, so either way a sound edge waits at most
0.87 ms. This question is open.
