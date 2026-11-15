# Read held keys and single presses

This example reads controls from the CoCo keyboard matrix. It runs on CoCo 1,
CoCo 2 and CoCo 3 without changes. It samples all controls before it chooses
actions. It shows held movement and one action for
each new Space press, including movement and action together.

It does not provide timing, key repeat, debounce, sound or a display. A small
movement model and a record of 16 updates supply the context for the check.

## Choose how to read a control

These are input policies, not hardware rules. Use held arrows and a new Space
press as the default for movement with one action per press.

| Policy | Use | Result while held | Startup choice | Example |
| --- | --- | --- | --- | --- |
| Held state | Continuous movement | One move per update | Read the current keys | Left and Right |
| New press | A single action | One action until release and repress | Seed history from a startup sample | Space |

Both arrows together cancel. A Space held at startup does not count as a new
press.

To accept that startup press, initialize `previous` to zero instead.
Automatic fire needs held state and a repeat interval. This example has no
repeat interval. A press and release between samples can go undetected.

The scan uses these matrix positions. The strobes come from clearing the
column bit in `$FF`. The row mask is `$08`.

| Control | Column | Row | Strobe at `$FF02` | Logical bit in `held` |
| --- | --- | --- | --- | --- |
| Left | PB5 | PA3 | `$DF` | 1 |
| Right | PB6 | PA3 | `$BF` | 2 |
| Space | PB7 | PA3 | `$7F` | 4 |

Sources: Tandy, *Color Computer Technical Reference Manual*, PDF 13, 40 and
75. Tandy's *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*, PDF 36,
figure 4-10. Tandy's *Color Computer 3 Service Manual*, PDF 40, figure 5-9. M
shares PB5 but uses PA1. Test the row bit, not the full byte.

The CoCo 3 figure puts Left, Right, Space and M at the same positions. Its
extra keys (Alt, Ctrl, F1 and F2) are on row PA6, columns PB3 to PB6. This
scan does not read row PA6. For the CoCo 3 PIAs, Tepolt, *Assembly Language
Programming for the CoCo3*, PDF 16, refers to his book on the original Color
Computer (PDF 5). He gives no new PIA behaviour.

Color BASIC 1.2 also has a keyboard routine, `KEYIN` (*Color Basic
Unravelled II*, PDF 29). This example uses direct scanning to read the
supported combinations. It does not compare the methods.

## Read the controls

The five `>>> EXAMPLE` parts of [main.asm](main.asm) show the input practice:

1. Set the PIA directions before the first scan. Clear control bit 2 to select
   each direction register. Set the rows to inputs and the columns to outputs.
   Set control bit 2 to select the data registers. Keep the other control bits.

2. Take one startup sample. Copy `held` to `previous` to ignore startup-held
   Space as a new press.

3. At `sample`, read Left, Right and Space into `held`. Write each strobe to
   `$FF02`. Test PA3 in `$FF00`. Write `$FF` to `$FF02` after the scan.

4. At `update`, count an action only if Space is held now and
   the previous sample showed a release. The counter `shots` is the action
   for this context.

5. At `history`, save `held` to `previous` after every update. A rejected move
   must still reach this step.

Part 1 uses Tandy's *Color Computer Technical Reference Manual*, PDF 13, and
Motorola's *MC6821 PIA* datasheet, PDF 7–8. Part 3 uses the matrix sources
above. Parts 2, 4 and 5 are our input policy.

The `--- CONTEXT` blocks initialize state, move a position within 0 to 4 and
record the results. The position starts at 2. These blocks are demonstration
code, not a collision technique.

The raw row copies and final PIA copies exist only for the check.
The program keeps the interrupts, stack, direct page and CPU clock that BASIC
sets.

[coco.toml](coco.toml) declares these targets: NTSC, 6809, normal clock and
direct DECB loading. Each target uses the keyboard layout of its machine.

| Target | XRoar machine | Memory | Firmware |
| --- | --- | --- | --- |
| `coco1` | `cocous` | 32 KiB | Color BASIC 1.1 |
| `coco2` | `coco2bus` | 32 KiB | Color BASIC 1.2 |
| `coco3` | `coco3`, GIME 1986 | 128 KiB | CoCo 3 ROM |

## What is different on the CoCo 3

The program and the expected results are the same on all three machines.
These items are different on the CoCo 3:

- The RAM snapshot is physical memory. Under BASIC's memory map, logical
  `$xxxx` is at snapshot offset `0x10000 + $xxxx` (Tepolt, PDF 58).
  [expected.py](expected.py) adds this offset for the `coco3` target.
- BASIC leaves the field-sync interrupt on. We measured `$FF03` as `$35`
  on `coco3` and `$34` on `coco1` and `coco2` in XRoar. Bit 0 enables that
  interrupt (*Color Computer 3 Service Manual*, PDF 9). The program does not
  change it.
- Row PA3 is also left joystick switch 2 (*Color Computer 3 Service Manual*,
  PDF 9). A held second button on the left joystick reads as a key in every
  column of row PA3. The check uses no joystick.

Code and state start at `$3000` and end below `$4000`. The check records use
`$4000..$406F`. [keys.txt](keys.txt) and [expected.py](expected.py) are only
check context. Their expected positions and action counts come from the policy.

## Run and check the variations

Start the commands in the starter folder. Use `snapshot` to run each variation
and save its RAM. This example shows nothing on the screen.

```sh
# CoCo 1, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco1
# CoCo 1, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco1 --variant keys
# CoCo 2B, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco2
# CoCo 2B, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco2 --variant keys
# CoCo 3, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco3
# CoCo 3, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco3 --variant keys
```

To compare both variations on all three targets, use this command:

```sh
uv run python scripts/coco.py check examples/keyboard-controls
```

The scripted variation needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check compares all 16 records with [expected.py](expected.py). It checks
the row reads, held bits, position, action count and history. It also checks
the update count, control bits and final column value.

The build without keys must stay at position 2 with no action.

The script checks startup-held Space, release and repress, both arrows,
movement with action, rejected moves and M held with Right. Line 1 supplies
the startup sample. The next 16 lines supply the updates.

Four negative controls in `scripts/coco_spec.py` must fail on all three
targets:

| Define | Fault | First failed update |
| --- | --- | --- |
| `WRONG_COLUMN` | Scan PB4 for Left | 4: the M row read is missing |
| `WRONG_SELECT` | Leave the column direction register selected | 1: Space is missing |
| `HELD_FIRE` | Count held Space on every update | 1: startup-held Space counts |
| `STALE_HISTORY` | Skip history after a rejected move | 6: history is stale |

On `coco3`, `WRONG_SELECT` fails differently: the program never reaches
`finished`. The field-sync interrupt stays on. While the direction register is
selected, a read of `$FF02` cannot clear the interrupt flag. Only a read of the
data register clears it (Motorola, *MC6821 PIA* datasheet, PDF 7–8). We
measured that this fault fails at update 1 when the program masks IRQ.

The check delivers keys through XRoar's keyboard matrix, PIA and the 6809
scanner.

It does not test host key events, window focus, physical keys, switch
bounce or rapid taps. It does not establish safe sharing with another scanner
or a handler that changes the column port. It does not test other CoCo 2
boards, a 512 KiB CoCo 3 or the 1987 GIME.

## Sources

PDF pages are one-based positions in the archive files. Read these pages before
you change the scan. The
[controls guide](../../guidance/techniques/controls-and-collision.md#sources)
gives the source links and the wider matrix.

- Tandy, *Color Computer Technical Reference Manual*: PDF 13 gives the PIA
  registers and joystick comparator bit. PDF 40 explains scanning. PDF 75
  shows the matrix wiring.

- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*:
  PDF 36, figure 4-10, gives the matrix positions.

- Tandy, *Color Computer 3 Service Manual*: PDF 9 gives the PIA registers,
  the control bits and the joystick switches on each row. PDF 40, figure 5-9,
  gives the matrix positions.

- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*: PDF 16
  refers to his earlier book for the PIAs. PDF 58 gives the
  memory map that sets the snapshot offset.

- Motorola, *MC6821 PIA* datasheet: PDF 7–8 gives the direction bits,
  register selection, writable control bits and how a read clears an
  interrupt flag.

- Spectral Associates, *Color Basic Unravelled II*: PDF 29 describes the
  keyboard routine in Color BASIC 1.2. This example does not call it.
