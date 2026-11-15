# Accept input only in the right game phase

This example lets each game phase accept only its own input. The game has
three phases: title, play and won.

Space starts play from the title and starts it again after a win. The arrows
move the actor only in play. Each start restores the room.

The example does not show the keyboard scan, the room drawing or the sound.
Those are context. It does not show pause, menus, a time limit, interrupt
input or key repeat.

The context is a whole small game for CoCo 1, CoCo 2B and CoCo 3. It has an
8×6 room in RG6, two stars to collect, an exit, phase messages and short DAC
effects.

## Machines

The same program runs on the three targets, with no extra setup:

| Target | Machine | What is different |
| --- | --- | --- |
| `coco1` | CoCo 1, 32 KiB, Color BASIC 1.1 | Nothing |
| `coco2` | CoCo 2B, 32 KiB, Color BASIC 1.2 | Nothing |
| `coco3` | CoCo 3, 128 KiB, GIME 1986 | The colours on the screen and the place of RAM in the snapshot |

On the CoCo 3, these items are the same as on the CoCo 1:

- The keyboard position of each arrow and Space.
- The PIA bits for the keyboard, the DAC and the sound selection.
- The RG6 mode setup.

The [Sources](#sources) give the pages.

On the CoCo 3, each colour code selects a palette register. The program
keeps the values that BASIC loads into them. XRoar shows other green and
black values than on the CoCo 1 (measured in XRoar, not a monitor).

The CoCo 3 RAM snapshot holds the physical memory. Logical address `$xxxx`
is at offset `0x10000 + $xxxx` in it. `expected.py` adds this offset.

## Choose what each phase accepts

The default policy suits a game with a title and an end screen. Space acts
only on a new press. The arrows act while they are held.

| Phase | `phase` | Message | New Space press | Arrows | Next phase |
| --- | --- | --- | --- | --- | --- |
| Title | 0 | SPACE TO START | Restore the room, then play | Nothing | Play |
| Play | 1 | COLLECT BOTH THEN EXIT | Nothing | Move one tile for each update | Won, at the open exit |
| Won | 2 | YOU WIN SPACE RESTART | Restore the room, then play | Nothing | Play |

These rules are our adaptation. The
[game-state guide](../../guidance/techniques/game-state.md#decide-which-phases-accept-input)
gives the reason: write down the input for each phase before you write the
loop.

- A Space held at startup does not start the game. Release it and press it
  again.
- A Space held across a phase change does not count again. The history
  update after each sample stops it.
- The exit stays locked until the actor collects both stars.

Other ways that this example does not show:

- Accept a Space held at startup. Set `previous` to zero instead of a startup
  sample.
- Let Space pause the game in play. Add a fourth phase.
- Start on any key. Test all the held bits, not only Space.

## Follow the phases

The six `>>> EXAMPLE` parts of [main.asm](main.asm) show the practice:

1. Before the loop, take one sample. Copy `held` to `previous`, so a Space
   held at startup is not a new press.

2. At `reset_room`, put the actor at (0, 0), set two stars to collect and copy
   `initial_map` to `room`. Each start calls it.

3. At `update`, accept a new Space press only in title or won. Call
   `reset_room`, then set `phase` to 1.

4. At `movement`, end the update unless `phase` is 1. The arrows then do
   nothing in title and won.

5. At the exit, reject the move while `remaining` is not zero. When the exit
   is open, set `phase` to 2.

6. At `history`, copy `held` to `previous` after every update. Rejected moves
   and every phase must reach this step.

The `--- CONTEXT` blocks are not part of the practice:

- They set up RG6 at `$0400` with colour set 0, as in
  [first-screen](../first-screen/README.md).
- They set the keyboard directions and scan the arrows and Space, as in
  [keyboard-controls](../keyboard-controls/README.md).
- They route the DAC to the sound output and play 32 DAC writes for each
  effect. The game reads no keys during an effect. The
  [sound guide](../../guidance/techniques/sound.md) explains this limit.
- They draw the phase message, the room and the actor after each change.

These files are only context:

- [terrain.png](terrain.png): the floor, wall, star and exit pictures.
- [assets.py](assets.py): converts `terrain.png` with `scripts/graphics.py`
  and writes the art and lettering before the build.
- [letters.json](letters.json): the 5×7 letters of the messages.
- [journey.txt](journey.txt) and [expected.py](expected.py): the check.

The guard bytes and the `accepted`, `starts`, `effects`, `last_effect` and
`sample_count` values exist only for the check. Remove them in a project.

The program keeps the interrupts, stack, direct page and CPU clock that BASIC
sets. The `room` label is data. The check fails if the CPU runs it.

## Play and check the game

Open a terminal in the starter folder. Copy one line and paste it to play on
that machine. Press and release Space, then use the arrows. Close the window
to stop.

```sh
# CoCo 1
uv run python scripts/coco.py run examples/collect-room --target coco1
# CoCo 2B
uv run python scripts/coco.py run examples/collect-room --target coco2
# CoCo 3
uv run python scripts/coco.py run examples/collect-room --target coco3
```

The CoCo 2B and CoCo 3 targets need their own firmware. If it is missing,
run `uv run python scripts/setup.py --roms-only --target coco2`, or the same
line with `--target coco3`.

To check both builds on all three targets, paste this line:

```sh
uv run python scripts/coco.py check examples/collect-room
```

The check needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
It takes a snapshot at each of 95 hits of `frame_ready`.

- The plain build gets no keys. It must stay on the title at each snapshot,
  with no sound.
- The `journey` build plays [journey.txt](journey.txt) through XRoar's
  keyboard, one line for each sample. Each line gives the held keys and the
  state that the phase rules require.

At each snapshot, the check compares these items with
[expected.py](expected.py):

- the phase, position, stars and counters
- the held keys and the history
- the room map and the guard bytes
- all 6,144 screen bytes and XRoar's rendered picture
- each effect in XRoar's sound output: 32 steps, in the pitch band for its
  kind

The journey includes these cases:

- Space held at startup, then released and pressed again
- Space held and pressed in play
- arrows at walls and room edges, and two arrows together
- M held with the arrows
- the locked exit, then the open exit
- three wins and three restarts

The model in `expected.py` draws each pixel from the art rows and the letters.
It does not read the tables in `main.asm`.

Negative controls in `scripts/coco_spec.py` must fail on all three targets:

| Define | Fault |
| --- | --- |
| `WRONG_COLUMN` | Scan the wrong column for Up |
| `STALE_HISTORY` | Skip the history after a rejected move |
| `HELD_SPACE` | Start on a Space held at startup |
| `SILENT` | Write only the zero DAC level |

The check uses XRoar's keyboard, not host key events. It does not prove the
result on a television, a physical CoCo or other CoCo 2 boards. It does not
find tearing or audible clicks between snapshots.

## Sources

PDF pages are one-based positions in the archive files. Read these pages before
you change the context.

- Inman, Inman and Dymax, *Assembly Language Graphics for the TRS-80 Color
  Computer*, PDF 106: mode 6R (RG6) is 256×192 and uses `$0400` to `$1BFF`.

- Motorola, *MC6847 Video Display Generator* datasheet, PDF 19, Table 3: the
  RG6 bit order.

- Tandy, *Color Computer Technical Reference Manual*:
  - PDF 13: `$FF00` holds the keyboard rows and `$FF02` the columns. Control
    bit 2 selects the direction register. `$FF01` bit 3 is SEL 1 and `$FF03`
    bit 3 is SEL 2.
  - PDF 14: `$FF20` bits 7 to 2 are the 6-bit DAC. `$FF23` bit 3 enables the
    sound.
  - PDF 31, Table 1: RG6 is SAM V=`110` with `$FF22` bits 7 to 4 `1111`.
  - PDF 38, Table 4: sound enabled with SEL 1 and SEL 2 at 0 selects the DAC.

- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*, PDF 36,
  figure 4-10: Up, Down, Left, Right and Space are row PA3 at columns PB3 to
  PB7.

- Tandy, *Color Computer 3 Service Manual*:
  - PDF 9 and 10: the same bits at `$FF00` to `$FF03` and `$FF20` to `$FF23`
    as on the CoCo 1.
  - PDF 40, figure 5-9: Up, Down, Left, Right and Space are row PA3 at
    columns PB3 to PB7.
  - PDF 43: Sel B 0 and Sel A 0 select the DAC. SNDEN must be high.

- Tepolt, *Assembly Language Programming for the CoCo3*:
  - PDF 46: in the VDG modes, each colour code selects a palette register.
  - PDF 56, step 14: the reset clears all SAM registers. PDF 62: the
    cleared rate is the low CPU speed. So the effects play in the same pitch
    bands as on the CoCo 1. In XRoar, each pitch is within 2% of the CoCo 1
    pitch (measured).
  - PDF 57, step 44: BASIC loads the palette registers.
  - PDF 58: the memory map. Under BASIC's map, logical `$0000` is physical
    `$10000` on a 128 KiB machine.

The phase rules, the game, the art and the effects are our own design.
