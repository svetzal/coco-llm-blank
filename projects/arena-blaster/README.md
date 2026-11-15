# Arena Blaster

A fast arena shooter for the CoCo 1. You move with one hand and shoot with the
other hand, in eight directions. The game uses four-colour graphics.

## What the owner asked for

> A retro arena shooter game in the style of Robotron. Keyboard controls: S, F,
> E and C move. J, L, I and the comma key fire in that direction. It must be
> fast, with audio and four-colour graphics, in the style of PMODE 3.

> Level by level, starting with slow enemies that increase in number on each
> level. Then hunters that come at times: not often on the low levels, and
> more often as the levels go up.

> Change the keys to A, D, W, S and K, semicolon, O, L. Then add sound.

The game, its name, its art and its rules are our own. They are not a copy of
another game.

## How to play

| Key | Action |
| --- | --- |
| W | Move up |
| S | Move down |
| A | Move left |
| D | Move right |
| O | Shoot up |
| L | Shoot down |
| K | Shoot left |
| ; (semicolon) | Shoot right |

Hold two keys of the same hand to move or shoot on a diagonal. Hold a shoot key
to shoot again and again.

A limit of these keys: K, O, S and W are the corners of a rectangle in the
keyboard matrix. When three of them are held, the fourth reads as held too.
So when you shoot up and left (O and K), the game cannot see whether you hold
W or S. It keeps the vertical movement of the last frame. To change from up
to down while you shoot up and left, release O or K for a moment.

## How to run it

Commands start in the starter folder:

```sh
uv run python scripts/coco.py run projects/arena-blaster
uv run python scripts/coco.py check projects/arena-blaster
```

The `run` command opens XRoar. Close the window to stop it.

The check runs six builds for 200 frames each. At each frame it compares
both screens, the game state, the rendered picture and the mixer output with
`expected.py`. See [Checks](#checks).

## Status

Increment 4, in progress: faster drawing. Increment 3 added sound effects and
the A, D, W, S and K, semicolon, O, L keys. There is no score and no game over
yet. When an enemy touches you, the level starts again.

Measured speed in XRoar, in fields of the picture for each frame (one field is
1/60 second):

| Build | Before increment 4 | Now |
| --- | --- | --- |
| `main` (level 1, 6 grunts) | 1.71 | 1.01 |
| `level10` (20 grunts) | 3.02 | 2.01 |

The game still slows down when the arena is full, because each step is one
frame. See [Drawing](#drawing).

Measured sound in XRoar (increment 3): the sound plays only while the program waits for the
end of the picture. During an effect, the sound is present in 56% of each
millisecond slice with a light load, and in 23% with 20 grunts. So the sound
has gaps 60 times each second, and it gets weaker when the arena is full.
Nobody has listened to it yet.

## Contract

- CoCo model and revision: CoCo 1 (owner choice)
- XRoar machine profile: `cocous` (starter default)
- RAM: 32 KiB (starter default)
- CPU and clock: 6809 at the stock clock (starter default)
- Video standard: NTSC (starter default)
- Firmware: Color BASIC 1.1, `bas11.rom` (starter default)
- Keyboard: the CoCo layout, `keyboard = "coco"` in XRoar (agent choice)
- Graphics: CG6, the mode of PMODE 3: 128x192 pixels, four colours (owner
  request). Colour set 0: green, yellow, blue and red (agent choice). The
  floor of the arena is blue, because CG6 has no black (agent choice).
- Controls: A, D, W and S move. K, semicolon, O and L shoot (owner request). Two
  keys give a diagonal, opposite keys cancel, and a held shoot key repeats
  (agent choice). The rule for the K, O, S and W rectangle is an agent choice.
- Sound: the six-bit DAC (owner request for audio). One effect at a time,
  played in the wait for the end of the picture (agent choice).
- Loader: XRoar runs the DECB binary directly (starter default). There is no
  disk image yet.

The CoCo 1 defaults come from
[development practice](../../guidance/starter/development.md#establish-the-contract).

## Design

### Memory

| Addresses | Use |
| --- | --- |
| `$0400`-`$1BFF` | Screen A, 6144 bytes |
| `$1C00`-`$1FFF` | Game state and erase lists (direct page `$1C`). An erase-list entry is the first screen byte and the erase routine of a sprite. |
| `$2000`-`$23FF` | Stack, from `$2400` down |
| `$2400`-`$3BFF` | Screen B, 6144 bytes |
| `$3C00`-`$7FFF` | Code and sprite data |

### Arena

- Rows 0-11 and 188-191 are blue. They are for the score in a later increment.
- A red wall is on rows 12 and 187, and on pixel columns 3 and 124.
- Objects stay inside pixel columns 4-123 and rows 13-186. These are byte
  columns 1-30. An erase routine stores the floor only in the bytes that
  its draw routine changes, so an erase never touches the wall.

### Drawing

Each frame erases all that the hidden screen showed two frames before. Then
it draws all objects again. `assets.py` turns each sprite in `sprites.txt`
into code: a draw routine and an erase routine for each of the 4 pixel shifts
in a byte.

- A byte that the sprite fills gets a plain store of the picture.
- An edge byte keeps the screen bits where the mask is 1 and adds the
  picture: screen = (screen AND mask) OR picture.
- A byte that the sprite does not use gets no code.
- The erase routine stores the floor in each byte that the draw routine
  changes.

Measured with a counter of the idle passes in the wait, frames 41-100 of
`level10`: the rules of the game take about 9,600 CPU cycles each frame. The
drawing took about 31,400 cycles with a loop over mask and picture data, and
takes about 12,600 cycles with this code. A field is about 14,900 cycles.

We also tried to draw only the objects that changed. Each screen kept a record
of each object, and a map of damaged areas told which unchanged objects to
draw again. On `level10` it drew 14 objects and erased 10 objects each frame,
not 21 of each. But the compares and the map took as much time as this saved,
so we removed it.

### Levels and enemies

The owner asked for slow enemies that increase in number on each level, and
for hunters that come more often on higher levels. The numbers are agent
choices:

| Item | Rule |
| --- | --- |
| Grunts (green) | 4 + 2 x level, not more than 20. One step each 4 frames. |
| Hunters (red) | One step each 2 frames. One comes each 660 - 60 x level frames, not less than 90. |
| Level 1 | 6 grunts, a hunter each 600 frames |
| Level 5 | 14 grunts, a hunter each 360 frames |
| Level 10 | 20 grunts, a hunter each 90 frames |

- An enemy step is 1 pixel across and up to 2 rows down or up, toward the
  player. Enemies are 6x10 pixels, the same size as the player.
- There are 24 enemy slots. A hunter needs a free slot.
- Grunt number N (from 0) makes its first step after (N AND 3) + 1 frames, so
  the grunts do not all step together.
- At the start of a level, each grunt goes to a random place. A place with x
  33-89 and y 50-140 is near the player's start, so the grunt tries again.
- A hunter goes to a random place on a random side of the arena. If the place
  is less than 20 pixels across and 30 rows from the player, or no slot is
  free, it tries again in the next frame.
- Random numbers: a 16-bit shift register starts at `$ACE1`. One step
  shifts it right. If a 1 bit falls out, the step does an exclusive OR with
  `$B400`. The game does one step each frame. A random byte is the low byte
  after eight more steps. A random x is 4 + (byte AND 127), and tries again
  above 114. A random y is 13 + byte, and tries again above 164. A random
  side is byte AND 3: top, bottom, left, right.

### Sound

One effect plays at a time. A new effect replaces the current one only if its
priority is the same or higher. Each effect is a list of records, one record
for each frame: a mode (square wave or noise), a period and a volume (0-63).

| Effect | Priority | When | Sound |
| --- | --- | --- | --- |
| Shot | 1 | A shot starts | Square, periods 8, 10, 13, 17, 22; volume 24 down to 10 |
| Explosion | 2 | A shot removes an enemy | Noise, periods 2-6; volume 44 down to 6 |
| Hunter | 3 | A hunter comes | Square, periods 10 and 14 in turn, 8 frames; volume 26 |
| Level | 4 | The arena is clear | Square, periods 30, 22, 16, 11, 3 frames each; volume 28 |
| Death | 5 | An enemy touches the player | Noise, periods 1-10, 14 frames; volume 60 down to 8 |

- The sound plays only while the program waits for the falling edge and
  the rising edge of field sync. Each frame starts at DAC 0.
- A square wave changes the output after `period` passes of the wait loop.
  A pass takes 17 cycles, and a pass with a change takes 52 cycles. So the
  pitch is 894,886 / (2 x (17 x period + 35)) Hz: period 8 is 2617 Hz and
  period 30 is 816 Hz.
- Noise: after `period` passes, an 8-bit shift register steps (exclusive OR
  with `$1D` when a 1 bit falls out). A 1 bit changes the output.

### Rules for each frame

1. Do one step of the random numbers. Read the keys. If O and K are held
   and both W and S read as held, use the vertical keys of the last frame.
2. Move the player 1 pixel across and 2 rows down or up. Stop the player at
   the arena edge. The player is 6 pixels wide and 10 rows high. It starts at
   pixel 61, row 95.
3. Move each shot 3 pixels across and 6 rows down or up. Remove a shot that
   leaves the arena.
4. If the shoot delay is more than 0, decrease it by 1. If not, and a shoot
   key is held, and a shot slot is free, start a shot from the player. Then
   set the delay to 5.
5. Move each enemy whose step count reaches 0.
6. Count down the hunter wait. At 0, try to start a hunter.
7. A shot that overlaps an enemy removes the shot and the enemy. Each shot
   removes only the first enemy in slot order.
8. If an enemy overlaps the player, start the level again. If not, and no
   enemy is left, start the next level. A new level puts the player back at
   the start and removes all shots.
9. Take the next sound record. Erase what this screen showed two frames
   before. Draw the shots and the enemies. Draw the player last.
10. Wait for the end of the picture, then show the new screen.

### Sources for the hardware facts

- PMODE 3 is the VDG mode "6C" (CG6). *The Rainbow*, October 1986, PDF 119,
  Table 1.
- CG6: SAM V2-V0 = `110`, `$FF22` bits 7-4 = `1110`, bit 3 is the colour set.
  Tandy, *Color Computer Technical Reference Manual*, PDF 31, Table 1.
- CG6 has 128x192 pixels, 2 bits for each pixel, 32 bytes for each row, 6144
  bytes. The leftmost pixel is in bits 7 and 6. Colour set 0: code 0 green,
  1 yellow, 2 blue, 3 red. Motorola *MC6847* datasheet, PDF 18-21, through
  the [graphics guide](../../guidance/techniques/graphics.md).
- The SAM display offset is in units of 512 bytes. F4 is `$FFCE` (clear) and
  `$FFCF` (set). Screens A and B differ only in F4. Tandy manual, PDF 15.
- `$FF03` bit 7 is the field-sync flag. Bit 1 selects the edge. A read of
  `$FF02` clears the flag. Tandy manual, PDF 13. The method is the
  [page flip](../../examples/page-flip/README.md) example.
- Keys: `$FF02` drives the columns and `$FF00` reads the rows. A pressed key
  reads 0. Tandy manual, PDF 13 and the keyboard diagram on PDF 75. A and D
  are row PA0 at columns PB1 and PB4. K, L and O are row PA1 at PB3, PB4 and
  PB7. S and W are row PA2 at PB3 and PB7. Semicolon is row PA5 at PB3.
- The diagram has no diode for each key. K, O, S and W make a rectangle, so
  three of them make the fourth read as held. The pinned XRoar models this
  (`keyboard_read_matrix` in `src/keyboard.c`), and the `moves` check
  measures it.
- Sound: `$FF20` bits 7-2 are the DAC. `$FF21` bit 2 = 0 selects its
  direction register. SEL 1 (`$FF01` bit 3) = 0, SEL 2 (`$FF03` bit 3) = 0
  and sound enable (`$FF23` bit 3) = 1 select the DAC. Tandy manual, PDF
  13-14 and PDF 38, Table 4.
- The CPU clock is 14.31818 MHz / 16. Tandy manual, PDF 26.
- Cycle counts of the sound loop: Leventhal, *6809 Assembly Language
  Programming*, Appendix C, PDF 553-555.

## Checks

`expected.py` holds the rules of the game. Each check build except `main`
uses test-harness controls: assembler defines, only for the check, that
remove one part of the game. The key scripts are short and written by hand.

| Build | Controls | Keys | What it checks |
| --- | --- | --- | --- |
| `main` | none | none | The real start. The grunts reach the player at frame 77: death sound, level again. |
| `moves` | `NO_ENEMIES` | `moves.txt` | Movement, walls, shots, the wrong key C, the K/O/S/W rectangle rule, shot sounds |
| `hit` | `FIXED_GRUNTS` `STILL` | `hit.txt` | Shot hits (frames 15 and 58), explosion and level sounds, level 2 |
| `touch` | `FIXED_GRUNTS` | none | A grunt reaches the player at frame 133: death sound |
| `hunter` | `NO_ENEMIES` `HUNTER_SOON` `NO_DEATH` | none | A hunter each 30 frames, its place and the hunter sound |
| `level10` | `FIRST_LEVEL=10` | none | 20 grunts and the level-10 hunter wait |

The controls:

- `NO_ENEMIES`: no grunts, and an empty arena does not end the level.
- `FIXED_GRUNTS`: two grunts, at x 100, y 90 and at x 100, y 40. No hunters.
- `STILL`: enemies do not move.
- `HUNTER_SOON`: the hunter wait is 30 frames.
- `NO_DEATH`: a touch does not start the level again.
- `FIRST_LEVEL=N`: the game starts at level N.

The sound check looks at the last 4 ms of the mixer output at each frame.
That is the end of the wait, where the record of the frame plays. It checks
the volume of each step, the pitch of a square wave (within 5%) and that
noise is not regular. On a heavy frame the wait can be shorter than 4 ms
(measured), so `main`, `level10` and `hunter` after frame 150 check only the
silence between effects. The mixer scale, 352.5 for each DAC step, is
measured in these captures.

Negative controls, run on copies: no DAC write in the square wave fails at
frame 16 (`moves`). No rectangle rule fails at frame 77 (`moves`). A copy
with no hunters failed at frame 90 (increment 2). Erase routines without
their last store fail at frame 3 (`main`): the screen keeps a trail.
