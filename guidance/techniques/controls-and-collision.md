# Separate controls, collision, and artwork

Read this when held movement must work together with single-press actions,
or when a change to a picture must not change what blocks the player. The
keyboard facts apply to CoCo 1 and the named CoCo 2 NTSC boards. The CoCo 3
manual describes the same scan. The checked examples run on CoCo 1 and CoCo 2
only. The policies are original adaptations for all three machines.

## Read the keyboard matrix

**Published explanation.** The manuals give these facts. Each cell is a PDF
page in that machine's manual.

| Fact | CoCo 1 | CoCo 2 | CoCo 3 |
| --- | --- | --- | --- |
| `$FF02` drives eight columns. `$FF00` bits 0–6 read seven rows. Bit 7 is the joystick comparator. | [13][coco1map] | 11 | 9 |
| Control bit 2 (`$FF01`, `$FF03`) selects the data register when set, the DDR when clear. | [13][coco1map] | 11 | 9 |
| Scan: write zero to one column bit, ones to the others. A pressed key reads zero on its row. | [40][coco1scan] | 36 | 40 |
| Matrix diagram | [75][coco1matrix] | [36, figure 4-10][coco2matrix] | 40, figure 5-9 |
| Fire buttons pull rows low: right fire PA0, left fire PA1. | [13, 37][coco1fire] | 11 | 9, also PA2/PA3 |
| The analog select bits (bit 3) choose the joystick axis and the sound source. | [37–38][coco1fire] | 37–38 | 42–43 |

A DDR bit of zero makes a line an input, and one makes it an output.
[MC6821 datasheet, PDF 7–8][pia]

The diagrams give these positions, as zero-based port bits:

| Keys | Row | Columns, in key order |
| --- | --- | --- |
| Up, Down, Left, Right, Space | PA3 | PB3, PB4, PB5, PB6, PB7 |
| X, Y, Z | PA3 | PB0, PB1, PB2 |
| A, B, C | PA0 | PB1, PB2, PB3 |
| M | PA1 | PB5 |
| Enter, Clear, Break | PA6 | PB0, PB1, PB2 |
| Either Shift | PA6 | PB7 |
| Alt, Ctrl, F1, F2 (CoCo 3 only) | PA6 | PB3, PB4, PB5, PB6 |

Both Shift keys share one position, so a scanner cannot tell them apart.

**Our adaptation**, used in [keyboard-controls](../../examples/keyboard-controls/README.md)
and [collect-room](../../examples/collect-room/README.md):

1. Clear control bit 2 and write the DDR. Then set bit 2 again. Keep the
   other control bits. Rows are inputs (`$00`) and columns are outputs (`$FF`).
2. Strobe one column at a time: `$F7`, `$EF`, `$DF`, `$BF` and `$7F` for the
   arrows and Space.
3. Test only the bit of the row that you need. Do not compare the whole byte.
4. Write `$FF` to the columns after the scan.

A write to `$FF02` is not a column strobe until bit 2 of `$FF03` is set.
Keyboard-controls keeps the interrupt state that BASIC sets. Collect-room
masks IRQ and FIRQ. Neither check establishes safe sharing with another
keyboard scanner or a handler that changes the column port.

### Shared inputs

A held fire button can look like a key in every column of its row. Joystick
conversion uses the DAC and the select bits of the sound path. Our adaptation:
decide which routine owns the mux and the DAC. A scan does not restore the DAC
value or the sound routing. Decide if the game supports fire buttons and keys
on rows PA0 and PA1 at the same time. See the [sound guide](sound.md).

### Several keys at once

The diagrams show no diode for each key. **Our deduction:** three held
corners of a rectangle can connect the fourth. A, B and I hold (PA0,PB1),
(PA0,PB2) and (PA1,PB1), so J at (PA1,PB2) can read as held. No result for
this probe exists. Define the chords that the game supports. Test same-row
pairs, same-column pairs and opposite arrows.

## Sample controls before choosing actions

**Published explanation.** Larry Landwehr's assembly demonstration compares
the complete row byte with a constant. It branches on left before it checks
right or Space. [Landwehr, *Hot CoCo*, October 1983, printed/PDF 106 and 108][keyboard]
Our inference: a whole-byte test can reject a key when another row bit
changes, and the early branch gives left priority.

**Our adaptation:** sample every control, then apply an explicit policy. Use
held state for movement and a rising edge for a single action:

```text
previous = sample_required_controls()   # before the first update

each update:
    held = sample_required_controls()
    pressed = held AND NOT previous
    request_movement(integer(held.right) - integer(held.left))
    if pressed.fire:
        request_one_shot()
    previous = held      # also after a rejected move
```

This policy cancels opposite arrows and allows movement plus fire. It ignores
a fire key held at startup. To count a startup-held key, start `previous` at
all false. For automatic fire, use held state with a repeat interval. These
are game choices, not Landwehr's rules.

Edge detection does not debounce a switch or repair ghosting. The program
cannot see a press and release between two samples. For phase changes, read
the [game-state guide](game-state.md#decide-which-phases-accept-input).

## Give scenery and objects different collision questions

**Published explanation.** Matt Togliatti's *Attacker* tests four screen
points around the ship (line 150). Its projectile code combines screen tests
with coordinate comparisons against the player (lines 530–550 and 650–660).
It is one game, not a general collision method.
[Togliatti, *Hot CoCo*, October 1983, printed/PDF 86 and 88][attacker]

**Our adaptation:**

- Ask the scenery if a location is solid. Screen colours can answer if the
  drawing defines the world. Then colour, erasure and drawing order are part
  of the collision rule. Use a separate occupancy map when decoration must
  change alone. Then each edit to solid scenery must change the map and the
  picture.
- Ask objects if their collision shapes intersect. Use this for a projectile
  that hits an actor. A bounding box is a deliberate approximation.

Decide the collision units, the world edges, whether touching counts and the
response: stop, slide, damage or collect. A test of one actor's new position
against another actor's old position adds an update-order rule.

[Tile-room](../../examples/tile-room/README.md) and collect-room keep a map
apart from the drawing and reject a move into a wall or past the room edge.
See also the [moving-object guide](moving-objects.md#decide-whether-the-picture-is-also-the-collision-map).

### Probes and steps

A few probe points are easy to check for a small ship in wide tunnels. Keep
the probe offsets as collision data, apart from the sprite. Move one grid cell
at a time and stop at the first blocked step:

```text
function move_horizontal(position, dx, probes, scenery):
    for step in 1 through abs(dx):
        candidate = position + (sign(dx), 0)
        if any probe of candidate is outside the world or solid:
            break
        position = candidate
    return position
```

Unit steps stop a probe from skipping a solid cell on its own track. They do
not fill the gaps between probes: a one-cell post can pass between two probe
tracks. Thin posts and corners need every relevant edge cell or a shape test.
Do not extend the loop to diagonal motion without a corner rule. If you limit
the steps in one update, drop or defer the remaining steps. Do not jump to the
destination. Two moving objects need a relative-motion test.

**Measured result, not rerun here.** A host Python model of these policies
passed 26 cases (Python 3.13). No example uses it, it ran no 6809 code and
it shows nothing about speed or arbitrary shapes. Its cases agree with the
advice above:

- A destination-only test crossed a thin wall. Unit steps stopped at it.
- Probes at offsets 0 and 2 missed a one-cell obstacle. Offset 1 found it.
- Wall-coloured decoration changed art-derived movement, not map movement.
- Two objects that swap places in one update overlap at neither end. A
  relative sweep of the two intervals found the contact.
- A new-against-old position test reported a false contact.

## What the examples check

`uv run python scripts/coco.py check examples/keyboard-controls` plays a key
script through the pinned instrumented XRoar's keyboard matrix and PIA to the
6809 scanner, on CoCo 1 (`cocous`) and CoCo 2 (`coco2bus`). It compares 16
update records with the model. The build without keys must stay idle.
Integration tests in `scripts/coco_spec.py` break the scanner four ways: a
wrong column, a DDR left selected, a held-fire count and a stale history.

Collect-room's `journey` variant plays 95 scans with arrows, walls, a locked
exit and restarts. Its check compares memory, the rendered frame and the
mixer output at each scan. Integration tests break its scanner three ways: a
wrong column, a stale history and a held Space at startup.

Both examples deliver keys through XRoar's API. They are not evidence for host
key events, physical keys, switch bounce, joystick buttons or CoCo 3. The
A+B+I probe and most chords are not tested.

## Unresolved source conflicts

- Landwehr's M-key prose gives 233, but his table puts M under 223 (PDF 106).
  His text gives eight rows, but the table has seven (PDF 106 and 108). The
  manuals give seven rows.
- *Attacker* says "right" twice in its horizontal-control prose (PDF 82).
  Lines 100–110 (PDF 86) give the exact threshold behaviour.
- The CoCo 1 schematic labels the lower PIA port PA0–PA7 (PDF 75). The prose
  and the block diagram (PDF 36) call it port B. The register roles settle
  this for software.
- The CoCo 2 manual names the PIA IC15 on PDF 11 and IC7 on PDF 34–36. Use
  the register addresses, not the label. A board schematic would settle this.

## Sources

- Tandy manuals: CoCo 1 *Technical Reference Manual* (`coco1-technical`),
  CoCo 2 *NTSC Service Manual, 26-3134/3136* (`coco2-service`), CoCo 3
  *Service Manual* (`coco3-service`).
- Motorola, *MC6821 PIA* datasheet, outside the manifest, SHA-256
  `1fa14d31bb39172610d63fd05ee6624cca50c7adb8ec3114579e7018222c3872`.
- *Hot CoCo*, Vol. 1 No. 5, October 1983, archive OCR edition, SHA-256
  `76218e4e0bc98ca0545ef3db34ce89bfb080998d7e89370f3ced483a2909e7a4`. PDF
  pages equal printed pages. We read as page images Landwehr, "Read the
  Keyboard in Assembly", 106 and 108, and Togliatti, "Attacker", 82, 84, 86,
  88 and 89, with their complete listings.
- Errata search, 2026-11-14: the November 1983 Feedback section (printed 8 and
  10, PDF 10 and 12, read as images), a text search of that issue, and web
  searches for the titles and authors. We found no correction to these
  articles. That does not prove that none exists.

The examples are our original work. They copy no magazine listing.

[coco1map]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[coco1fire]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=37>
[coco1scan]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=40>
[coco1matrix]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=75>
[coco2matrix]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=36>
[pia]: <https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Motorola/Motorola%206821.pdf#page=7>
[keyboard]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=106>
[attacker]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=86>
