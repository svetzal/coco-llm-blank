# Read held keys and single presses

This example reads controls from the CoCo keyboard matrix. It runs on CoCo 1,
both CoCo 2 targets and CoCo 3 without changes. It samples all controls before it chooses
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
   Mask IRQ while `$FF03` selects the column direction register. The next
   section gives the reason.

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
The program keeps the stack, direct page and CPU clock that BASIC sets. It
keeps BASIC's interrupts, except for the short mask in part 1.

[coco.toml](coco.toml) copies the standard target tables: NTSC, 6809, normal
clock and direct DECB loading. Each target adds the keyboard layout of its
machine for the key script. The program does not use Extended BASIC. The
standard tables load it because it sets the machine state at entry.

| Target | XRoar machine | Memory | Firmware |
| --- | --- | --- | --- |
| `coco1` | `cocous`, MC6847 | 32 KiB | Color BASIC 1.1, Extended BASIC 1.1 |
| `coco2` | `cocous`, MC6847 | 32 KiB | Color BASIC 1.2, Extended BASIC 1.1 |
| `coco2b` | `coco2bus`, MC6847T1 | 32 KiB | Color BASIC 1.3, Extended BASIC 1.1 |
| `coco3` | `coco3`, GIME 1986 | 128 KiB | CoCo 3 ROM |

## Mask IRQ while the direction register is selected

Extended BASIC turns on the field-sync interrupt (IRQ) on every target.
`$FF03` bit 0 enables it (*Color Basic Unravelled II*, PDF 23–24). The IRQ
vector points to BASIC's handler at `$894C` (the same book, PDF 20). The
handler reads `$FF02` to clear the field-sync flag. Only a read of the data
register clears the flag (Motorola, *MC6821 PIA* datasheet, PDF 7).

When `$FF03` bit 2 is 0, `$FF02` is the direction register (*Color Basic
Unravelled II*, PDF 24). If a field sync occurs in that window, the handler
reads the direction register. The flag stays set, and the CPU runs the handler
again forever. Thus part 1 sets the IRQ mask before it selects the direction
register. It restores the mask that BASIC set after it selects the data
register again. The window is a few instructions, so the hang is rare, but
it is possible on every target.

Port A needs no mask. BASIC leaves the `$FF01` interrupt off (bit 0), so no
port A flag must be cleared. We measured `$FF01` as `$B4` and `$FF03` as `$35`
at entry on all four targets in the pinned XRoar. The program does not change
`$FF03` bit 0. Between scans, BASIC's handler runs every field and reads
`$FF02`. That read does not change the column outputs.

## What is different on the CoCo 3

The program and the expected results are the same on all four targets.
These items are different on the CoCo 3:

- The RAM snapshot is physical memory. Under BASIC's memory map, logical
  `$xxxx` is at snapshot offset `0x10000 + $xxxx` (Tepolt, PDF 58).
  [expected.py](expected.py) adds this offset for the `coco3` target.
- Row PA3 is also left joystick switch 2 (*Color Computer 3 Service Manual*,
  PDF 9). A held second button on the left joystick reads as a key in every
  column of row PA3. The check uses no joystick.

Code and state start at `$3000` and end below `$4000`. The check records use
`$4000..$406F`. Extended BASIC does not use that memory at entry (measured:
the check passes on all four targets). [keys.txt](keys.txt) and
[expected.py](expected.py) are only check context. Their expected positions
and action counts come from the policy.

## Run and check the variations

Start the commands in the starter folder. Use `snapshot` to run each variation
and save its RAM. This example shows nothing on the screen.

```sh
# CoCo 1, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco1
# CoCo 1, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco1 --variant keys
# CoCo 2, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco2
# CoCo 2, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco2 --variant keys
# CoCo 2B, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco2b
# CoCo 2B, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco2b --variant keys
# CoCo 3, no input
uv run python scripts/coco.py snapshot examples/keyboard-controls --target coco3
# CoCo 3, scripted keys
uv run python scripts/coco.py snapshot examples/keyboard-controls \
  --target coco3 --variant keys
```

To compare both variations on all four targets, use this command:

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

Four negative controls in `scripts/coco_spec.py` must fail on all four
targets:

| Define | Fault | First failed update |
| --- | --- | --- |
| `WRONG_COLUMN` | Scan PB4 for Left | 4: the M row read is missing |
| `WRONG_SELECT` | Leave the column direction register selected | 1: Space is missing |
| `HELD_FIRE` | Count held Space on every update | 1: startup-held Space counts |
| `STALE_HISTORY` | Skip history after a rejected move | 6: history is stale |

`WRONG_SELECT` also sets the IRQ mask. Without the mask, the fault can stop
the program in BASIC's handler before `finished`. Whether it stops depends on
when the next field sync occurs. With the mask, the fault fails at update 1
on every target (measured). Thus the control shows that the check rejects a
wrong register selection through the records.

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
  interrupt flag. PDF 7 says that only a read of the data register clears
  the flag.

- Spectral Associates, *Color Basic Unravelled II*: PDF 20 gives the IRQ
  vector, `$894C` under Extended BASIC. PDF 23–24 give the `$FF01` and `$FF03`
  bits: bit 0 enables the interrupt, and bit 2 selects the direction register.
  PDF 29 describes the keyboard routine in Color BASIC 1.2. This example does
  not call it.
