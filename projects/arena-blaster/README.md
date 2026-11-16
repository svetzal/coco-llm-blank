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

> Increment 7: the first levels that teach the game.

> Increment 8: enemies that shoot.

> Make the bullets a bit bigger: they are hard to see. Make sure that the
> game runs on Disk BASIC, from a disk.

> The bullets are too big now. Make them 2 pixels high, not 1.

> Increment 9: things to collect (agreed with the owner: points, shots in
> 2, 4 or 8 directions, and a bomb).

> Negative pickups: half fire speed, half move speed, or a hunter blitz.
> Make them different from the good pickups, but subtle. A jinx lasts 5
> seconds. Put the name of the gift or the jinx at the top of the screen
> while it lasts. Call them jinxes.

> A demo sequence that starts after the high-score screen is idle for more
> than 10 seconds, as on arcade machines. It introduces the enemy types and
> their behaviour, then the gifts and the jinxes. Each scene shows the
> player moving, shooting the enemy, or collecting the gift or the jinx and
> shooting with that effect. "Press fire to start" flashes in the score
> area. Break the demo up with several visits back to the title screen.

The plan for these requests:

| Increment | Contents |
| --- | --- |
| 5 | Score, 3 lives, extra lives, a pause after a death, game over, the start and game-over sounds |
| 6 | A title screen, a high-score table with initials, text |
| 7 | The first levels: each one teaches one new thing |
| 8 | Enemies that shoot |
| 9 | Things to collect: points, shots in more directions, a bomb |
| 10 | Jinxes, and the names of the gift and the jinx at the top of the screen |
| 11a | The demo: the idle time, scenes, captions, the flashing prompt, and the grunt scene |
| 11b | Demo part A: the hunter and the shooter |
| 11c | Demo parts B and C: points, the three powers and the bomb |
| 11d | Demo part D: the three jinxes |

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

To run the game from a Disk BASIC disk:

```sh
uv run python scripts/coco.py disk projects/arena-blaster --run
uv run python scripts/coco.py disk projects/arena-blaster --check
```

The `disk` command writes `build/arena-blaster/main.dsk` with one file,
`ARENA.BIN`. With `--run`, XRoar starts Disk BASIC with the disk in drive 0
and types `LOADM"ARENA":EXEC`. On a real CoCo, type the same command. With
`--check`, XRoar does the same without a window, and the game must reach its
first frame.

The check runs thirty-four builds for 200 frames each, with Extended BASIC in
the machine. At each frame it compares
both screens, the game state, the rendered picture and the mixer output with
`expected.py`. See [Checks](#checks).

## Status

Increment 11d: demo part D shows the three jinxes. This completes the demo:
four parts, each between two visits to the title.

Increment 11c added demo parts B and C: points, the double, the spread, the
star and the bomb.
Increment 11b added the hunter and shooter scenes to demo part A, and the
full SHOOT TO START prompt (owner request).
Increment 11a added the demo. When the title has no key for 10 seconds, a
part of the demo plays. A shoot key during the demo starts a game.

Increment 10 added jinxes from level 8. A jinx is a pickup that hurts: half
the fire speed, half the move speed, or a blitz of hunters. The band at the
top shows the name of the gift and of the jinx, each with a bar of the
time that is left.

Increment 9 added things to collect, from level 4: points, shots in 2, 4
or 8 directions, and bombs from level 6.
Increment 8 added shooters, enemies that fire bullets at the player, from
level 5.
Increment 7 added the first levels that teach the game, and a "LEVEL N"
banner at the start of each level.
Increment 6 added the title screen, the high-score table and the initials.
Increment 5 added score, lives, game over and the start and game-over sounds.
Increment 4 added faster drawing and the fixed speed of 30 frames each second.

The owner chose the fixed speed of 30 frames each second. Each frame lasts two
fields of the picture (one field is 1/60 second). Measured speed in XRoar, in
fields for each frame:

| Build | Increment 3 | Faster drawing | Now (fixed speed) |
| --- | --- | --- | --- |
| `main` (level 1, 6 grunts) | 1.71 | 1.01 | 2.00 |
| `level10` (20 grunts; now 16 grunts and 4 shooters) | 3.02 | 2.01 | 2.00, but 4 when the player dies |

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
- Firmware: Color BASIC 1.1 `bas11.rom` and Extended Color BASIC 1.1
  `extbas11.rom` (starter default). Disk Extended Color BASIC 1.1
  `disk11.rom` for the disk (owner request).
- Keyboard: the CoCo layout, `keyboard = "coco"` in XRoar (agent choice)
- Graphics: CG6, the mode of PMODE 3: 128x192 pixels, four colours (owner
  request). Colour set 0: green, yellow, blue and red (agent choice). The
  floor of the arena is blue, because CG6 has no black (agent choice).
- Controls: A, D, W and S move. K, semicolon, O and L shoot (owner request). Two
  keys give a diagonal, opposite keys cancel, and a held shoot key repeats
  (agent choice). The rule for the K, O, S and W rectangle is an agent choice.
- Sound: the six-bit DAC (owner request for audio). One effect at a time,
  played in the wait for the end of the picture (agent choice).
- Loader: XRoar runs the DECB binary directly (starter default). The disk
  `main.dsk` holds `ARENA.BIN`, and `LOADM"ARENA":EXEC` runs it from Disk
  BASIC (owner request).
- Disk BASIC RAM: Disk BASIC keeps its RAM from `$600`, just above the text
  screen, up to the graphics pages (*Disk Basic Unravelled II*, PDF 20). The
  game loads at `$3C00`-`$6C9C`, above that area. After `EXEC`, the game
  does not go back to BASIC, so it uses all RAM.
- Drive motor: Disk BASIC turns the motor off in its IRQ handler (PDF 70).
  The game masks the IRQ, so at its start it stores 0 in `$FF40`. Bit 3 of
  that write-only latch is the motor enable (PDF 15). XRoar does not show
  the motor, so this is not measured.

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
| `$3C00`-`$6C9C` | Code, sprites, font, text, the demo and the high-score table |
| `$6C9D`-`$7FFF` | Free, about 4.8 KiB |

The game needs 32 KiB. The two screens use 12 KiB, so a 16 KiB machine
does not have space for the program. The game state uses 198 of the 256
bytes of the direct page. More state is at `$1F00`-`$1F91`, after the erase
lists: a line buffer for text, the shot slots and the bullet slots.

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
for hunters that come more often on higher levels. The owner also asked for
first levels that teach the game. Each of the first four levels adds one
thing. The numbers and the hints are agent choices:

| Level | Grunts | Hunters | Hint |
| --- | --- | --- | --- |
| 1 | 4 | None | SHOOT THE GRUNTS |
| 2 | 8 | None | HOLD TWO KEYS FOR DIAGONALS |
| 3 | 6 | The first after 60 frames (2 seconds), then each 240 frames (8 seconds) | HUNTERS ARE FAST |
| 4 | 10. Pickups start. | Each 210 frames (7 seconds) | COLLECT THE POWER UPS |
| 5 | 12, and 2 shooters. A bullet each 60 frames. | Each 180 frames (6 seconds) | SHOOTERS FIRE BACK |
| 6 | 13, and 3 shooters. A bullet each 36 frames. Bombs start. | Each 150 frames (5 seconds) | BOMBS CLEAR THE AREA |
| 7 and more | See below | Each 330 - 30 x level frames, not less than 45 | None, except level 8 |
| 8 | See below. Jinxes start. | Each 90 frames (3 seconds) | SOME GIFTS BITE |

From level 7, a level has 4 + 2 x level enemies at the start, not more
than 20. Of these, level - 3 are shooters, not more than 4. The rest are
grunts. A shooter fires each 84 - 8 x level frames, not less than 24. So
level 6 has 13 grunts and 3 shooters, with a bullet each 36 frames. Level
10 has 16 grunts and 4 shooters, with a bullet each 24 frames, and a hunter
each 45 frames (1.5 seconds).

- Grunts (green) make one step each 2 frames. Hunters (red) make one step
  each frame. Shooters (yellow) make one step each 3 frames.
- At the start of a level, a banner shows for 60 frames (2 seconds). It
  has "LEVEL N" in big yellow text on rows 60-69. The hint of the level is
  in green on rows 76-80. Nothing moves during the banner. The banner also
  shows when the same level starts again after a death.
- Level 8 is the first level without a row in the teaching table, but it
  has a hint, because jinxes start there. The first hint was NOT EVERY
  GIFT IS KIND. It made the banner frames too long, and the start sound had
  a gap in the last 4 ms of frame 3 (`level8`). The shorter hint has no gap.
- The banner is drawn after the enemies and the player. Its erase-list
  entry stores the floor in byte columns 2-29 of rows 60-80.

- All counts in frames are at 30 frames each second.
- An enemy step is 1 pixel across and up to 2 rows down or up, toward the
  player. Enemies are 6x10 pixels, the same size as the player.
- There are 24 enemy slots. A hunter needs a free slot.
- At the start of a level, the grunts fill the first slots, and the
  shooters fill the slots after them.
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

### Things to collect

The owner asked for points and power-ups to collect. The numbers are agent
choices. The owner can change them.

| Pickup | Sprite | When the player collects it |
| --- | --- | --- |
| Points | A coin | 100 points |
| Double | 2 | For 300 frames (10 seconds), each shot is 2 shots: forward and back |
| Spread | 4 | For 300 frames, each shot is 4 shots, at right angles |
| Star | 8 | For 300 frames, each shot is 8 shots, in all directions |
| Bomb | A yellow bomb | Removes each enemy less than 40 pixels across and 60 rows from the player, with its points. Removes all bullets. |
| Slow (jinx) | A red hourglass | For 150 frames (5 seconds), the shoot delay is 5, not 2: half as many shots |
| Heavy (jinx) | A red weight | For 150 frames, each player step is half: 1 pixel across and 2 rows down or up |
| Blitz (jinx) | A red lightning bolt | Up to 3 hunters come in at once, each as a normal hunter comes. The name shows for 60 frames. |

The good pickups are gifts. A gift has a yellow icon and a jinx has a red
icon, in the same green box. The difference is small, as the owner asked:
a player who looks closely can tell them apart. The bomb was red in
increment 9. Now it is yellow, so that red is only on jinxes.

- From level 4, each 6th enemy that a shot removes leaves a pickup at its
  place, if no pickup is on the floor. The count goes on from level to
  level, and starts again with each game.
- The types come in this order: points, double, slow, bomb, spread,
  heavy, points, star, bomb, blitz, double. After that, the order starts
  again. Before level 6, a bomb is points. Before level 8, a jinx is
  skipped, so levels 4-7 have the order of increment 9. From level 8,
  3 of each 11 pickups are jinxes.
- A pickup is 6x7 pixels in a green box. Its x is a multiple of 4, so it
  is in whole bytes, and it needs only one draw routine.
- A pickup stays for 150 frames (5 seconds). In its last 60 frames, it
  blinks: it does not show when bit 2 of its frame count is 1.
- A new power replaces the old one. A new jinx replaces the old one, so a
  blitz ends a slow or a heavy jinx. A power and a jinx can be on at the
  same time. A death ends both. A new level keeps both.
- With a power, the shots go around a ring of the 8 directions. The first
  shot goes in the direction of the keys. A double puts 2 shots each 4
  places, a spread 4 shots each 2 places, and a star 8 shots each place. Each shot needs a free slot of the 10 shot slots. A
  shot that gets no slot does not start.
- Speed: a test copy at level 10, with the star power and a shoot key held
  for 200 frames, measured 2 frames of 3 fields. All the other frames took
  2 fields, except the new level after the arena was clear. Each shot is
  tested against each enemy, so 10 shots and 20 enemies are the heaviest
  load. A copy with 8 shot slots measured 1 frame of 3 fields, so we kept
  10 slots. A frame of 3 fields also has a short gap in the sound.
- The band at the top shows the name of the gift (the power) in yellow at
  byte column 8. The name of the jinx is in red at byte column 17. Both are
  on rows 3-7. Points and the bomb have no time, so they have no name.
- Under each name, on rows 9-10, a bar shows the time that is left. It has
  1 byte for each 50 frames of a gift, or for each 25 frames of a jinx. The
  count is rounded up, and a bar has 6 bytes at most. The gift bar is
  yellow and the jinx bar is red.
- A name changes rarely, so each screen keeps the gift and the jinx that it
  shows. The game draws a name only when it changes. The bars are drawn in
  each frame.

### Shooters

The numbers are agent choices. The owner can change them.

- A level has one fire wait. When it ends, the next shooter in slot order,
  after the one that fired last, fires one bullet. Then the wait starts
  again. If no bullet slot is free, that shooter does not fire.
- There are 4 bullet slots. A bullet is 3x4 pixels, with a yellow middle
  2 rows high. The first bullet was 3x3, with a yellow middle 1 row high,
  and it was hard to see. A 4x6 bullet was too big (owner choice). It moves 3 pixels
  across and 6 rows down or up each frame, about the speed of the player.
- The bullet starts in the middle of the shooter and goes toward the
  player in one of 8 directions. AX is the number of pixels across to the
  player and AY is the number of rows. A pixel is about two rows wide. If
  AX is more than AY, the bullet goes only across. If AY / 4 is more than
  AX, it goes only down or up. If not, it goes on a diagonal.
- A bullet that leaves the arena goes away. A bullet that overlaps the
  player starts the pause after a death. Shots do not stop bullets.
- Bullets do not move during the banner or the pause after a death. A new
  level, or the same level again, removes all bullets.

### Score and lives

The numbers are agent choices. The owner can change them.

- A grunt gives 10 points. A shooter gives 30 points. A hunter gives 50
  points.
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
  text and the high-score table. Under the table are a grunt, a hunter and
  a shooter with their points, and the keys. "SHOOT TO START" shows for 16 frames, then goes for 16 frames.
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

A new screen (the arena, the title or the initials) goes into the hidden
screen only. The other screen is on view, and a change to it shows at once
as a torn picture. The `demo` check found this tear at the change from the
demo to the title. The first frame that draws into the other screen draws
the new screen there first.

A new screen takes more than two fields, so
after it, the frame waits for the start of a field. Then each frame draws
only the part that changes into the hidden screen. On the title, this part
is the prompt. On the initials screen, it is the letters and the bar. A
change of screen takes 15 to 20 fields over its two frames.

### Demo

The owner asked for a demo that starts when the title is idle, and for
several visits back to the title. The scenes, the captions and the keys of
the demo player are agent choices.

- On the title, a frame with no game key adds 1 to the idle count. A game
  key sets it to 0. At 300 frames (10 seconds), the next part of the demo
  starts. A new shoot key on the title or in the demo starts a game.
- A part is a list of scenes. After the last scene of a part, the title
  shows again, and the next idle time plays the next part. After the last
  part, the first part comes again. The next part stays the same during a
  game.
- A scene record gives the caption, the player, the enemies and a pickup.
  It also gives the waits for bullets and hunters, the start of the random
  sequence, a power and a jinx. So a scene plays the same each time.
- A scene starts with the banner for 60 frames. It shows the caption: a
  name in big yellow text and a line in green. Then the script gives the
  keys of each frame: pairs of a key byte and a number of frames. The game
  rules do the rest.
- The demo player has one life and cannot die. The demo plays at level 1,
  so no enemy leaves a pickup, and a clear arena does not start a level.
  The end of the script ends the scene.
- SHOOT TO START flashes in the band at byte column 9, at the rate of the
  title prompt. The owner asked for the full prompt. It needs the place of
  the gift name, so the band shows no score, no reserve lives and no names
  in the demo. The caption of a scene names its gift or jinx.

| Part | Scenes |
| --- | --- |
| A | Grunt: SLOW  10 POINTS. Three grunts. The player shoots up, walks left and shoots, then walks right and shoots. |
| A | Hunter: FAST  50 POINTS. A hunter comes from the right edge after 10 frames, and the player shoots it. The next one comes from the left 50 frames later, and the player shoots it when it is near. |
| A | Shooter: FIRES BACK  30 POINTS. A shooter fires each 20 frames. The player steps aside, the bullet goes past, and the player steps back and shoots up. |
| B | Points: COLLECT FOR 100. The player walks right onto a coin. |
| B | Double: SHOTS GO TWO WAYS. The player takes the double. One shot right hits a grunt on each side. |
| B | Spread: SHOTS GO FOUR WAYS. The player steps down onto the spread. One shot up hits four grunts: above, below, left and right. |
| C | Star: SHOTS GO EIGHT WAYS. The player takes the star. One shot up hits a ring of 8 grunts. |
| C | Bomb: CLEARS THE AREA. Six grunts close in. The player steps onto the bomb, and they all go. |
| D | Slow: JINX  SLOWER SHOTS. The player takes the hourglass and holds a shoot key. A shot goes each 6 frames, and three grunts in a line fall one by one. |
| D | Heavy: JINX  SLOWER STEPS. The player takes the weight, walks away from a grunt at half speed, and shoots it. |
| D | Blitz: JINX  HUNTERS RUSH IN. The player takes the bolt. Three hunters come, and the player shoots up and right, then left, then right. |

The keys of each scene come from the model. `expected.py` played each
scene with many sets of keys. We kept keys that hit each enemy with no
bullet on the player. The hunter scene starts the random sequence at
`$1234`. So its first hunter comes from the right, and the second from the
left. The blitz scene starts it at `$2718`, so that its three hunters come
from the left, the top and the bottom.

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
| Bullet | 1 | A shooter fires | Square, periods 12, 16, 20; volume 22 down to 14 |
| Pickup | 4 | The player collects points or a power | Square, periods 31, 23, 16 (C, E, G); volume 26 |
| Jinx | 4 | The player collects a jinx | Square, periods 16, 23, 31, 40 (the pickup notes in reverse, then lower); volume 26 |
| Bomb | 5 | The player collects a bomb | Noise, periods 1-12, 22 fields; volume 62 down to 8 |
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
   On the title, a new shoot key starts a game: go to step 9. If not, count
   the idle frames. At 300, start the demo and go to step 9. If not, take
   the next sound record, draw the prompt and go to step 10. In the demo, a
   new shoot key starts a game: go to step 9. For the
   initials, do the rules of "Title and high scores". Then take the next
   sound record, draw the letters and the bar, and go to step 10.
   After game over, count down the pause and go to step 9. At 0, show the
   initials screen or the title. After a death, count down the pause and go
   to step 9. At 0, take a life. Then start the same level again, or start
   game over. During the banner, count it down and go to step 9. In the
   demo, take the keys from the script. At its end, start the next scene
   or show the title, and go to step 9.
2. Move the player 2 pixels across and 4 rows down or up, or half that
   with the heavy jinx. Stop the player at
   the arena edge. The player is 6 pixels wide and 10 rows high. It starts at
   pixel 61, row 95.
3. Move each shot 6 pixels across and 12 rows down or up. Remove a shot that
   leaves the arena. Then move each bullet, and remove a bullet that leaves
   the arena.
4. If a power is on, count down its time. If a jinx is on, count down its
   time. If the shoot delay is more than 0, decrease it by 1. If not, and
   a shoot key is held, start the shots of the power in the free slots. If
   a shot started, set the delay to 2, or to 5 with the slow jinx.
5. Move each enemy whose step count reaches 0.
6. Count down the hunter wait. At 0, try to start a hunter. Then count
   down the fire wait. At 0, the next shooter fires.
7. A shot that overlaps an enemy removes the shot and the enemy, and adds its
   points. Each shot removes only the first enemy in slot order. The enemy
   can leave a pickup. Then, if the player overlaps the pickup, collect it.
   If not, count down the time of the pickup.
8. If an enemy or a bullet overlaps the player, start the pause after a
   death. If not, and no enemy is left, start the next level. A new level
   puts the player back at the start and removes all shots and bullets.
9. Take the next sound record. Erase what this screen showed two frames
   before. Draw the shots, the bullets, the pickup and the enemies. Draw
   the player. During the banner, draw the banner. Then draw the score, the
   reserve lives, the names of the gift and the jinx, and their bars.
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
- Disk BASIC: `$FF40` is a write-only latch, and bit 3 = 0 turns the drive
  motors off (PDF 15). Disk BASIC RAM starts at `$600` (PDF 20). The IRQ
  handler turns the motors off after a wait (PDF 70). *Disk Basic Unravelled
  II*, Spectral Associates, revised by Walter K. Zydhek, 1999, read as page
  images. The PDF is not in the starter manifest. It is in the
  `Unravelled Series` folder of the Color Computer Archive, beside
  *Color Basic Unravelled II*.

## Checks

`expected.py` holds the rules of the game. Each check build except `main`
uses test-harness controls: assembler defines, only for the check, that
remove one part of the game. The key scripts are short and written by hand.

| Build | Controls | Keys | What it checks |
| --- | --- | --- | --- |
| `main` | none | none | The real power-on: the title screen, the table and the prompt that comes and goes |
| `moves` | `SKIP_TITLE` `NO_READY` `NO_ENEMIES` | `moves.txt` | Movement, walls, shots, the wrong key C, the K/O/S/W rectangle rule, shot sounds |
| `hit` | `SKIP_TITLE` `NO_READY` `FIXED_ENEMIES` `STILL` `FIRST_SCORE=0x0990` | `hit.txt` | Hits on a grunt (frame 9) and a hunter (frame 32), their points, an extra life at 1000, the extra-life and level sounds, level 2 |
| `touch` | `SKIP_TITLE` `FIXED_ENEMIES` | none | The banner, then the hunter reaches the player at frame 94. The banner shows again at frame 139. |
| `hunter` | `SKIP_TITLE` `NO_READY` `NO_ENEMIES` `HUNTER_SOON` `NO_DEATH` | none | A hunter each 15 frames, its place and the hunter sound |
| `level1` | `SKIP_TITLE` | none | The level 1 banner and hint, 4 grunts, no hunter. A death at frame 119 and the banner again at frame 164. |
| `level3` | `SKIP_TITLE` `FIRST_LEVEL=3` `NO_DEATH` | none | The level 3 banner and hint, 6 grunts, the first hunter at frame 120 |
| `level5` | `SKIP_TITLE` `FIRST_LEVEL=5` `NO_DEATH` | none | The level 5 banner and hint, 12 grunts and 2 shooters, bullets across at frames 120 and 180 |
| `shooter` | `SKIP_TITLE` `NO_READY` `ONE_SHOOTER` | `shooter.txt` | Bullets down, on both diagonals and across, the bullet sound, deaths by a bullet at frames 28 and 174 |
| `pickups` | `SKIP_TITLE` `NO_READY` `FIXED_ENEMIES` `STILL` `FIRST_LEVEL=4` `DROP_EVERY=1` | `pickups.txt` | A coin from the grunt at frame 9, collected at frame 26 (100 points, pickup sound). The hunter leaves a double at frame 34, but the level ends and removes it. |
| `bomb` | `SKIP_TITLE` `NO_READY` `FIXED_ENEMIES` `STILL` `FIXED_PICKUP=5` | `bomb.txt` | A bomb at frame 8 removes both enemies (60 points) and ends the level. A second bomb at frame 37, with the bomb sound. |
| `double` | `SKIP_TITLE` `NO_READY` `NO_ENEMIES` `FIRST_POWER=2` `POWER_TIME=100` | `powers.txt` | 2 shots for each shot, the bar in the band, the end of the power at frame 100, then single shots |
| `spread` | the same, with `FIRST_POWER=3` | `powers.txt` | 4 shots for each shot, and all 10 shot slots in use |
| `star` | the same, with `FIRST_POWER=4` | `powers.txt` | 8 shots for each shot, and shots that get no slot |
| `slow` | `SKIP_TITLE` `NO_READY` `NO_ENEMIES` `FIRST_POWER=3` `FIRST_JINX=6` | `jinxes.txt` | A spread at half the fire speed, both names and both bars in the band, the end of the jinx at frame 150, then the normal speed |
| `heavy` | `SKIP_TITLE` `NO_READY` `NO_ENEMIES` `FIRST_JINX=7` | `jinxes.txt` | Half steps across and up, the end of the jinx at frame 150, then normal steps |
| `blitz` | `SKIP_TITLE` `NO_READY` `FIXED_ENEMIES` `NO_DEATH` `FIXED_PICKUP=8` | `blitz.txt` | A blitz at frame 8: 3 hunters, the jinx sound, BLITZ in the band until frame 68 |
| `jinxdrop` | `SKIP_TITLE` `NO_READY` `FIXED_ENEMIES` `STILL` `FIRST_LEVEL=8` `DROP_EVERY=1` `FIRST_DROP=2` | `pickups.txt` | The grunt leaves a slow jinx at frame 9 (red icon), collected at frame 26. The hunter leaves a bomb at frame 34. |
| `level8` | `SKIP_TITLE` `FIRST_LEVEL=8` `NO_DEATH` | none | The level 8 banner with its hint, 16 grunts and 4 shooters |
| `demo` | `DEMO_SOON` | none | The title, the demo at frame 30, the grunt scene (hits at frames 104, 124 and 143), then the hunter scene at frame 163. The prompt flashes. |
| `demohunter` | `DEMO_SOON` `FIRST_SCENE=1` | none | The hunter scene at frame 30: hunters at frames 100 and 150, hits at frames 116 and 171. The shooter scene at frame 189. |
| `demoshooter` | `DEMO_SOON` `FIRST_SCENE=2` | none | The shooter scene at frame 30: a bullet at frame 110 that goes past, a hit at frame 146, the title at frame 159. Part B starts at frame 189 with the points scene. |
| `demopoints` | `DEMO_SOON` `FIRST_PART=1` | none | The points scene: the coin at frame 114, then the double scene |
| `demodouble` | `DEMO_SOON` `FIRST_PART=1` `FIRST_SCENE=1` | none | The double at frame 98, both grunts at frames 115 and 116 |
| `demospread` | `DEMO_SOON` `FIRST_PART=1` `FIRST_SCENE=2` | none | The spread at frame 95, four grunts at frames 112-116, the title at frame 145, part C at frame 175 |
| `demostar` | `DEMO_SOON` `FIRST_PART=2` | none | The star at frame 97, eight grunts at frames 115-118, then the bomb scene |
| `demobomb` | `DEMO_SOON` `FIRST_PART=2` `FIRST_SCENE=1` | none | The bomb at frame 103 removes six grunts. The title at frame 135, then part D at frame 165. |
| `demoslow` | `DEMO_SOON` `FIRST_PART=3` | none | The hourglass at frame 97, shots each 6 frames, grunts at frames 112, 120 and 127 |
| `demoheavy` | `DEMO_SOON` `FIRST_PART=3` `FIRST_SCENE=1` | none | The weight at frame 97, half steps to the left, the grunt at frame 150 |
| `demoblitz` | `DEMO_SOON` `FIRST_PART=3` `FIRST_SCENE=2` | none | The bolt at frame 97 and three hunters, hit at frames 108, 122 and 138. The title at frame 157, then part A again. |
| `demoshoot` | `DEMO_SOON` | `demoshoot.txt` | W at frame 10 starts the idle count again, so the demo starts at frame 40. A shoot key at frame 120 starts a game. |
| `level10` | `SKIP_TITLE` `FIRST_LEVEL=10` | none | The banner with a two-digit level, 16 grunts and 4 shooters, a bullet up, a death at frame 91 |
| `over` | `SKIP_TITLE` `NO_READY` `FIRST_LIVES=1` | none | Death at frame 39, game over at frame 84 with its sound. A score of 0 gets no place, so the title comes at frame 174. |
| `scores` | `NO_READY` `FIXED_ENEMIES` `FIRST_LIVES=1` `FIRST_SCORE=0x5000` | `scores.txt` | A start from the title (frame 3), game over (frame 82), the initials screen (frame 172), a held W that repeats, S from A to Z, the entry CZA at place 7 below REX (frame 192), a held shoot key that does not start a game |

The controls:

- `SKIP_TITLE`: at power-on, a game starts at once, with no title screen.
- `NO_READY`: a level starts with no banner. The builds with key scripts
  use it, so that their scripts stay short.
- `NO_ENEMIES`: no grunts, no bullets, and an empty arena does not end
  the level.
- `FIXED_PICKUP=N`: a level starts with a pickup of type N at x 60, y 60.
  Type 5 is a bomb and type 8 is a blitz.
- `DROP_EVERY=N`: each Nth enemy that a shot removes leaves a pickup.
- `FIRST_POWER=N`, `POWER_TIME=N`: a game starts with power N (2 double, 3
  spread, 4 star), and a power lasts N frames.
- `FIRST_JINX=N`, `JINX_TIME=N`: a game starts with jinx N (6 slow, 7
  heavy), and a jinx lasts N frames.
- `FIRST_DROP=N`: the first drop is place N of the drop order (from 0).
- `DEMO_SOON`: the demo starts after 30 idle frames, not 300.
- `FIRST_PART=N`: the first part of the demo (from 0).
- `FIRST_SCENE=N`: the first demo after power-on starts at scene N of its
  part (from 0). Later parts start at their first scene.
- `ONE_SHOOTER`: one shooter at x 61, y 30 that fires each 20 frames, and
  no other enemies.
- `FIXED_ENEMIES`: a grunt at x 100, y 90 and a hunter at x 100, y 40. No
  other hunters and no bullets.
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

- Increment 11a: a demo that does not stop the scene at the end of its
  script fails at frame 163 (`demo`).
- Increment 11b: a demo that starts each part at its first scene, with no
  `FIRST_SCENE`, fails at frame 30 (`demohunter`).
- Increment 11c: a `FIRST_SCENE` for each part, not only the first part,
  fails at frame 189 (`demoshooter`). Part B starts at its spread scene,
  not at its points scene.
- Increment 11d: a demo with three parts, not four, fails at frame 30
  (`demobomb`). When part C starts, the next part is A, not D.
- Increment 10: a slow jinx that keeps the shoot delay at 2 fails at frame
  1 (`slow`): the delay is 2, not 5.
- Increment 9: a spread power with a step of 4 places, not 2, fails at
  frame 1 (`spread`): it fires 2 directions, not 4.
- Increment 8: an aim that never sends a bullet only across fails at frame
  120 (`level5`), at the first bullet.
- Increment 7: an `erase_banner` without the store to byte columns 12-13
  fails at frame 60 (`level1`), the first frame after the banner. A copy
  without the store to columns 28-29 passed, because no text of the level 1
  banner is in those columns.
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
