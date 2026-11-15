# Arena Blaster

A fast arena shooter for the CoCo 1. You move with one hand and shoot with the
other hand, in eight directions. The game uses four-colour graphics.

## What the owner asked for

> A retro arena shooter game in the style of Robotron. Keyboard controls: S, F,
> E and C move. J, L, I and the comma key fire in that direction. It must be
> fast, with audio and four-colour graphics, in the style of PMODE 3.

The game, its name, its art and its rules are our own. They are not a copy of
another game.

## How to play

| Key | Action |
| --- | --- |
| E | Move up |
| C | Move down |
| S | Move left |
| F | Move right |
| I | Shoot up |
| , (comma) | Shoot down |
| J | Shoot left |
| L | Shoot right |

Hold two keys of the same hand to move or shoot on a diagonal. Hold a shoot key
to shoot again and again.

## How to run it

Commands start in the starter folder:

```sh
uv run python scripts/coco.py run projects/arena-blaster
uv run python scripts/coco.py check projects/arena-blaster
```

The `run` command opens XRoar. Close the window to stop it.

The check runs three builds for 300 frames each. It compares both screens,
the game state and the rendered picture with `expected.py` at each frame:

- `main`: no keys. The grunts reach the player, and the level starts again.
- `journey`: the keys in `journey.txt`. They clear levels 1 and 2.
- `hunters`: starts at level 10 and plays `hunters.txt`. Hunters come at
  frames 90 and 251, and level 10 is clear at frame 161.

## Status

Increment 2: levels of enemies. There is no sound, no score and no game over
yet. When an enemy touches you, the level starts again.

Measured speed in XRoar: on levels 1 and 2, most frames take one field of
the picture (60 frames each second). With 20 grunts on level 10, most frames
take two or three fields (30 or 20 frames each second). The game slows down
when the arena is full, because each step is one frame.

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
- Controls: S, F, E and C move. J, L, I and comma shoot (owner request). Two
  keys give a diagonal, opposite keys cancel, and a held shoot key repeats
  (agent choice).
- Sound: the six-bit DAC (owner request for audio). Not yet in the game.
- Loader: XRoar runs the DECB binary directly (starter default). There is no
  disk image yet.

The CoCo 1 defaults come from
[development practice](../../guidance/starter/development.md#establish-the-contract).

## Design

### Memory

| Addresses | Use |
| --- | --- |
| `$0400`-`$1BFF` | Screen A, 6144 bytes |
| `$1C00`-`$1FFF` | Game state and erase lists (direct page `$1C`) |
| `$2000`-`$23FF` | Stack, from `$2400` down |
| `$2400`-`$3BFF` | Screen B, 6144 bytes |
| `$3C00`-`$7FFF` | Code and sprite data |

### Arena

- Rows 0-11 and 188-191 are blue. They are for the score in a later increment.
- A red wall is on rows 12 and 187, and on pixel columns 3 and 124.
- Objects stay inside pixel columns 4-123 and rows 13-186. These are byte
  columns 1-30. Each shifted copy of a sprite is only as wide as the bytes
  that its pixels touch, so an erase never touches the wall.

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

### Rules for each frame

1. Do one step of the random numbers. Read the keys.
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
9. Erase what this screen showed two frames before. Draw the shots, the
   enemies. Draw the player last.
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
  reads 0. Tandy manual, PDF 13 and the keyboard diagram on PDF 75. E, F and C
  are row PA0 at columns PB5, PB6 and PB3. I, J and L are row PA1 at PB1, PB2
  and PB4. S is row PA2 at PB3. Comma is row PA5 at PB4.
- Our deduction from the diagram: no three of these eight keys make a
  rectangle with a fourth key of the set. Thus the keys cannot make a false
  press of a game key. No check tests this.
