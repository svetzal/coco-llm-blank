# Held keys and single presses

This example reads the keyboard matrix directly on CoCo 1 and CoCo 2. It
moves a position while an arrow key is held. It counts one action for each
new press of Space, also while an arrow moves.

The program writes a record of each update to memory. After 16 updates it
stops. This is a test probe, not a game. It shows nothing on the screen.

## What the program does

The program scans three keyboard columns: left arrow, right arrow and Space.
It reads all three keys before it applies the policy. The policy is an
original adaptation, not a hardware rule:

- A held left or right arrow moves the position one cell for each update.
  Both arrows together cancel.
- The world holds positions 0 to 4. The program rejects a move to -1 or 5.
  The position starts at 2.
- Space counts one action on a rising edge only. A held Space does not repeat.
- The startup sample seeds the history, so a Space held at startup is not a
  press.
- The history updates after every sample, also after a rejected move.

The program does exactly one startup sample and 16 updates. It has no timer,
repeat delay, debounce or display. IRQ and FIRQ stay masked.

## Contract

The program runs on two targets, both NTSC, 32 KiB, normal-clock 6809 and
direct DECB loading:

- `coco1`: `cocous`, Color BASIC 1.1.
- `coco2`: `coco2bus`, Color BASIC 1.2.

| Region | Use |
| --- | --- |
| `$3000..program_end` | Code and state, below `$4000` |
| `$4000..$406F` | 16 update records of seven bytes |
| `$7E00..$7EFF` | Stack, down from `$7F00` |

Each record holds the three row reads, the held bits (left 1, right 2,
Space 4), the position, the action count and the history.

## Source facts

The keyboard experiment that came before this example read these pages as
images. PDF pages are one-based positions in the archive files.

- Tandy, **Color Computer Technical Reference Manual**, PDF 13: port B
  (`$FF02`) drives the eight columns. Port A (`$FF00`) bits 0–6 read the
  rows. Bit 7 of `$FF00` is the joystick comparator. Bit 2 of each control
  register selects the data register when set.

- The same manual, PDF 40: to scan, write zero to one column bit and ones to
  the other seven. A pressed key reads zero on its row.

- Tandy, **Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)**, PDF 36,
  figure 4-10: left, right and Space are on row PA3 at columns PB5, PB6 and
  PB7. M is on row PA1 at column PB5.

- Motorola, **MC6821 PIA datasheet**, PDF 7–8: a DDR bit of zero makes the
  line an input, and one makes it an output.

The derived column strobes are `$DF`, `$BF` and `$7F`. The scanner tests
only bit 3 of the row read. It restores all columns high after each scan.
The [controls guide](../../guidance/techniques/controls-and-collision.md) gives
the archive links and the wider matrix.

## Check it

From the repository root, after the setup has prepared CoCo 1 and CoCo 2
firmware:

```sh
uv run python scripts/coco.py check examples/keyboard-controls
```

The check needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
It runs two builds on each target:

- The main build gets no keys. All 16 records must show no key, position 2
  and no action. This is the no-input control.
- The `keys` build plays [keys.txt](keys.txt) through XRoar's keyboard
  matrix, one line for each scan. Line 1 is the startup sample.

[expected.py](expected.py) compares each record with the hand-written
position and action count beside each line of `keys.txt`. It calculates
the row reads from the matrix positions above. It also checks these items:

- the program finished 16 updates
- the writable bits of both PIA control registers did not change
- all columns are high at the end

The script includes these cases:

- Space held at startup
- movement and action in the same update
- M held with right: M shares the left column but is not left
- Space released and pressed again at an edge
- both arrows held
- a move back from each edge

## Negative controls

`main.asm` has four broken builds. The integration tests in
`scripts/coco_spec.py` play `keys.txt` through each build on both targets.
Each build must fail at the stated update:

| Define | Fault | First failed update |
| --- | --- | --- |
| `WRONG_COLUMN` | Scans PB4 for left | 4: the M row read is missing |
| `WRONG_SELECT` | Leaves bit 2 of `$FF03` clear, so column writes go to the DDR | 1: Space is not read |
| `HELD_FIRE` | Counts a held Space on every update | 1: startup-held Space counts |
| `STALE_HISTORY` | Skips the history update after a blocked move | 6: the history is stale |

The example spec checks the same faults against the model alone.

## Limits

The keys go into XRoar's keyboard matrix through its keyboard API. The real
PIA and the 6809 scanner read them. Each key is held for a complete scan.
This is not evidence for these items:

- host key events or window focus
- physical keys, switch bounce or rapid taps
- joystick buttons, sound or a display
- CoCo 3, or every CoCo 2 board (the result is for `coco2bus`)
