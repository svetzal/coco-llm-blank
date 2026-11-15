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

> A fixed speed of 30 frames each second.

> A fun little sound at the start of a game and a sad sound at the end. Score,
> 3 lives, and an extra life after each so many points. Later: enemies that
> shoot. Things to collect: points, or power-ups such as shots in 2, 4 or 8
> directions, or a bomb that clears the enemies near the player. Easy first
> levels that teach the game. A high-score table.

The plan for these requests:

| Increment | Contents |
| --- | --- |
| 5 | Score, 3 lives, extra lives, a pause after a death, game over, the start and game-over sounds |
| 6 | A title screen, a high-score table with initials, text |
| 7 | The first levels: each one teaches one new thing |
| 8 | Enemies that shoot |
| 9 | Things to collect: points, shots in more directions, a bomb |

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

The check runs eight builds for 200 frames each. At each frame it compares
both screens, the game state, the rendered picture and the mixer output with
`expected.py`. See [Checks](#checks).

## Status

Increment 6: the title screen, the high-score table and the initials.
Increment 5 added score, lives, game over and the start and game-over sounds.
Increment 4 added faster drawing and the fixed speed of 30 frames each second.
Increment 7 adds the first levels that teach the game.

The owner chose the fixed speed of 30 frames each second. Each frame lasts two
fields of the picture (one field is 1/60 second). Measured speed in XRoar, in
fields for each frame:

| Build | Increment 3 | Faster drawing | Now (fixed speed) |
| --- | --- | --- | --- |
| `main` (level 1, 6 grunts) | 1.71 | 1.01 | 2.00 |
| `level10` (20 grunts) | 3.02 | 2.01 | 2.00, but 3 or 4 when the player dies |

When the player dies on level 10, the restart places 20 grunts and draws them
all, so that frame takes one or two more fields. All the other frames in the
six check builds take two fields. See [Drawing](#drawing).

Each step is twice the step of increment 3, so the game plays at the same
speed as before on a light load.

Measured sound in XRoar (increment 3, before the fixed speed): the sound plays only while the program waits for the
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
| `$3C00`-`$5850` | Code, sprites, font, text and the high-score table |
| `$5851`-`$7FFF` | Free, about 10 KiB |

The game needs 32 KiB. The two screens use 12 KiB, so a 16 KiB machine
does not have space for the program. The game state uses 242 of the 256
bytes of the direct page.

### Arena

- Rows 0-11 and 188-191 are blue. Rows 3-7 show the score and the reserve
  lives.
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
| Grunts (green) | 4 + 2 x level, not more than 20. One step each 2 frames. |
| Hunters (red) | One step each frame. One comes each 330 - 30 x level frames, not less than 45. |
| Level 1 | 6 grunts, a hunter each 300 frames (10 seconds) |
| Level 5 | 14 grunts, a hunter each 180 frames (6 seconds) |
| Level 10 | 20 grunts, a hunter each 45 frames (1.5 seconds) |

- All counts in frames are at 30 frames each second.
- An enemy step is 1 pixel across and up to 2 rows down or up, toward the
  player. Enemies are 6x10 pixels, the same size as the player.
- There are 24 enemy slots. A hunter needs a free slot.
- Grunt number N (from 0) makes its first step after (N AND 1) + 1 frames, so
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

### Score and lives

The numbers are agent choices. The owner can change them.

- A grunt gives 10 points. A hunter gives 50 points.
- The score has 6 digits. It shows at the top left, in yellow on the blue
  band: pixels 4-27, rows 3-7. The program keeps it as 3 BCD bytes.
- A game starts with 3 lives. Each 1000 points give one more life.
- The reserve lives show as small player icons at the top right: the first
  at pixel 120, then each 4 pixels to the left, up to 6 icons.
- The digits and the icon are 4 pixels wide and 5 rows high, one byte for
  each row (`font.txt`).
- When an enemy touches the player, the game stops for 45 frames (1.5
  seconds). Then the player loses a life, and the same level starts again.
- When no life is left, the game-over sound plays, and the game stops for 90
  frames (3 seconds). Then a new game starts with the start sound.

### Title and high scores

The program has three phases: the title, a game and the initials. The
numbers and the words are agent choices. The owner can change them.

- At power-on, the title screen shows. It has the name of the game in big
  text, the high-score table, a grunt and a hunter with their points, and
  the keys. "SHOOT TO START" shows for 16 frames, then goes for 16 frames.
- A shoot key starts a game. The key must be new: held now, but not held
  in the last frame. So a shoot key that is held from before does not
  start a game.
- After the pause of game over, the score goes to the table if it is more
  than the score of an entry. A score the same as an entry goes below that
  entry. If the score gets no place, the title screen comes.
- The initials screen shows "NEW HIGH SCORE", the score and three big
  letters. All three letters start as A. A yellow bar is under the letter
  that changes.
- W gives the next letter and S gives the letter before. After Z comes A.
  A held W or S changes the letter at once and again after 12 frames.
  After that, it changes the letter each 4 frames. A letter change plays the shot sound.
- A new shoot key goes to the next letter, with the shot sound. After the
  third letter, the entry goes into the table and the level sound plays.
  Each lower entry moves down one place, and the last entry goes out. The
  title screen comes, with the new entry in green.
- The table has 10 entries of a 6-digit score and 3 letters. It starts with
  made-up entries: 10000 down to 1000 in steps of 1000. The table is in RAM,
  so it keeps new entries until the machine goes off.

The text uses the glyphs in `font.txt`: 4 pixels wide and 5 rows high, one
byte for each row. A glyph is yellow on blue. Red text sets each yellow
pixel to red: the byte OR (the yellow bits shifted left). Green text sets
each yellow pixel to green: the byte AND `$AA`. Big text shows each pixel as
2x2 pixels, so a big character is 2 bytes wide and 10 rows high.

A new screen (the arena, the title or the initials) goes into both screens.
That work takes more than two fields. So after it, the frame waits for the
start of a field, as at power-on. Then each frame draws only the part that
changes into the hidden screen. On the title, this part is the prompt. On
the initials screen, it is the letters and the bar.

### Sound

One effect plays at a time. A new effect replaces the current one only if its
priority is the same or higher. Each effect is a list of records. A record
has a mode (square wave or noise), a period, a volume (0-63) and a number of
fields. Each field plays one record or a part of one, so each frame plays
two fields of the effect.

| Effect | Priority | When | Sound |
| --- | --- | --- | --- |
| Shot | 1 | A shot starts | Square, periods 8, 10, 13, 17, 22; volume 24 down to 10 |
| Explosion | 2 | A shot removes an enemy | Noise, periods 2-6; volume 44 down to 6 |
| Hunter | 3 | A hunter comes | Square, periods 10 and 14 in turn, 8 fields; volume 26 |
| Level | 4 | The arena is clear | Square, periods 30, 22, 16, 11, 3 fields each; volume 28 |
| Extra life | 4 | The score reaches the next 1000 | Square, periods 15 and 10 in turn, 2 fields each, 14 fields; volume 30 |
| Letter | 1 | A change or the next letter in the initials | The shot sound |
| Entry | 4 | The initials go into the table | The level sound |
| Death | 5 | An enemy touches the player | Noise, periods 1-10, 14 fields; volume 60 down to 8 |
| Start | 6 | A game starts | Square, periods 48, 38, 31, 23 (C, E, G, C), then 31, 23; 41 fields; volume 28 |
| Game over | 6 | The last life is lost | Square, periods 32, 40, 43, 48 (G, E flat, D, C), 120 fields; volume 28 down to 12 |

- The sound plays only while the program waits for the falling edge and
  the rising edge of field sync. Each field starts at DAC 0.
- A square wave changes the output after `period` passes of the wait loop.
  A pass takes 17 cycles, and a pass with a change takes 52 cycles. So the
  pitch is 894,886 / (2 x (17 x period + 35)) Hz: period 8 is 2617 Hz and
  period 30 is 816 Hz.
- Noise: after `period` passes, an 8-bit shift register steps (exclusive OR
  with `$1D` when a 1 bit falls out). A 1 bit changes the output.

### Rules for each frame

1. Do one step of the random numbers. Read the keys. If O and K are held
   and both W and S read as held, use the vertical keys of the last frame.
   Find the new shoot keys: held now, but not in the last frame.
   On the title, a new shoot key starts a game: go to step 9. If not, take
   the next sound record, draw the prompt and go to step 10. For the
   initials, do the rules of "Title and high scores". Then take the next
   sound record, draw the letters and the bar, and go to step 10.
   After game over, count down the pause and go to step 9. At 0, show the
   initials screen or the title. After a death, count down the pause and go
   to step 9. At 0, take a life. Then start the same level again, or start
   game over.
2. Move the player 2 pixels across and 4 rows down or up. Stop the player at
   the arena edge. The player is 6 pixels wide and 10 rows high. It starts at
   pixel 61, row 95.
3. Move each shot 6 pixels across and 12 rows down or up. Remove a shot that
   leaves the arena.
4. If the shoot delay is more than 0, decrease it by 1. If not, and a shoot
   key is held, and a shot slot is free, start a shot from the player. Then
   set the delay to 2.
5. Move each enemy whose step count reaches 0.
6. Count down the hunter wait. At 0, try to start a hunter.
7. A shot that overlaps an enemy removes the shot and the enemy, and adds its
   points. Each shot removes only the first enemy in slot order.
8. If an enemy overlaps the player, start the pause after a death. If not, and no
   enemy is left, start the next level. A new level puts the player back at
   the start and removes all shots.
9. Take the next sound record. Erase what this screen showed two frames
   before. Draw the shots and the enemies. Draw the player. Then draw the
   score and the reserve lives.
10. Wait for the end of the first field, unless it ended during the work.
    The field-sync flag stays set until a read of `$FF02` (MC6821 PDF 10,
    Figure 18), so a set flag tells that the first field ended. Take the next
    sound record. Wait for the end of the second field, then show the new
    screen.

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
- The field-sync flag (`$FF03` bit 7) goes high on the selected edge and
  stays high until a read of `$FF02`. Motorola, *MC6821*, PDF 10, Figure 18.
- `DAA` after an addition corrects A to BCD and sets the carry for the next
  byte. Leventhal, *6809 Assembly Language Programming*, PDF 488.
- Cycle counts of the sound loop: Leventhal, *6809 Assembly Language
  Programming*, Appendix C, PDF 553-555.

## Checks

`expected.py` holds the rules of the game. Each check build except `main`
uses test-harness controls: assembler defines, only for the check, that
remove one part of the game. The key scripts are short and written by hand.

| Build | Controls | Keys | What it checks |
| --- | --- | --- | --- |
| `main` | none | none | The real power-on: the title screen, the table and the prompt that comes and goes |
| `moves` | `SKIP_TITLE` `NO_ENEMIES` | `moves.txt` | Movement, walls, shots, the wrong key C, the K/O/S/W rectangle rule, shot sounds |
| `hit` | `SKIP_TITLE` `FIXED_ENEMIES` `STILL` `FIRST_SCORE=0x0990` | `hit.txt` | Hits on a grunt (frame 9) and a hunter (frame 32), their points, an extra life at 1000, the extra-life and level sounds, level 2 |
| `touch` | `SKIP_TITLE` `FIXED_ENEMIES` | none | The hunter reaches the player at frames 34, 113 and 192 |
| `hunter` | `SKIP_TITLE` `NO_ENEMIES` `HUNTER_SOON` `NO_DEATH` | none | A hunter each 15 frames, its place and the hunter sound |
| `level10` | `SKIP_TITLE` `FIRST_LEVEL=10` | none | 20 grunts and the level-10 hunter wait |
| `over` | `SKIP_TITLE` `FIRST_LIVES=1` | none | Death at frame 39, game over at frame 84 with its sound. A score of 0 gets no place, so the title comes at frame 174. |
| `scores` | `FIXED_ENEMIES` `FIRST_LIVES=1` `FIRST_SCORE=0x5000` | `scores.txt` | A start from the title (frame 3), game over (frame 82), the initials screen (frame 172), a held W that repeats, S from A to Z, the entry CZA at place 7 below REX (frame 192), a held shoot key that does not start a game |

The controls:

- `SKIP_TITLE`: at power-on, a game starts at once, with no title screen.
- `NO_ENEMIES`: no grunts, and an empty arena does not end the level.
- `FIXED_ENEMIES`: a grunt at x 100, y 90 and a hunter at x 100, y 40. No
  other hunters.
- `STILL`: enemies do not move.
- `HUNTER_SOON`: the hunter wait is 15 frames.
- `NO_DEATH`: a touch does not kill the player.
- `FIRST_LEVEL=N`: the game starts at level N.
- `FIRST_LIVES=N`: a game starts with N lives.
- `FIRST_SCORE=0xNNNN`: a game starts with this score (BCD, the low four
  digits). lwasm reads `0x` in a define, but not `$`.

The sound check looks at the last 4 ms of the mixer output at each frame.
That is the end of the wait for the second field, where the second record of
the frame plays. It checks the volume of each step, the pitch of a square
wave (within 5%) and that noise is not regular. With the fixed speed, it
checks every frame of every build. The mixer scale, 352.5 for each DAC step, is
measured in these captures.

Negative controls, run on copies. Each one must fail:

- Increment 6: an `insert` that does not move the lower entries down fails
  at frame 192 (`scores`).
- Increment 5: an `add_score` without `DAA` fails at frame 9 (`hit`).
- Increment 4: a `show` without the record of the second field failed at
  frame 40 (`main`), because the death sound played its records too slowly.
  Erase routines without their last store failed at frame 3 (`main`): the
  screen kept a trail.
- Increment 3: no DAC write in the square wave failed at frame 16 (`moves`).
  No rectangle rule failed at frame 77 (`moves`).
- Increment 2: a copy with no hunters failed at frame 90.
