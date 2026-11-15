# Separate game state from presentation

Read this for a turn-based game, a menu for one switch, or a game that waits
for a command before it plays a sequence.
Keep the world state, the pending commands and the presentation state apart.
A redraw, an animation or a sound must never advance a turn or apply a command
again.

The design can inform the CoCo 1, 2 and 3.
The [turn-queue example](../../examples/turn-queue/README.md) tests the state
rules on the CoCo 3 only.
The sources are BASIC programs from 1983 to 1985, which we did not run.
Each target needs its own checks of input, clock and display.

## Store an arrival, not every position on the route

**Published explanation.** Tony Byorick's *Conqueror!*, *Undercolor* 1(6),
March 8, 1985, keeps the planet data apart from the scheduled arrivals.
Its turn has arrival, command and production phases.
A command checks the source owner and strength before it records the
destination, strength, player and arrival turn.
[Printed 10–12, PDF 12–14][conqueror]
It needs an external assembly screen expander and does not state its RAM need.

**Our adaptation.** Give each journey a used flag, an owner, a destination, a
strength and an arrival turn.
Add departure data only if a route animation needs it.
Use one capacity `N` to allocate journeys, land them and find fleets in
transit.
The table costs `N` times the record size.
A scan each turn replaces the movement calculations.
This suits delayed orders, not arcade movement.

Do every check before the first write: phase, player, planets, ships, time and
a free slot.
Then fill the slot and take the ships as one commit.
A rejected command, an overflow and a full queue leave the world unchanged.
Choose a turn limit, or a time that cannot wrap, before you write the time
check.
The `send` routine in the turn-queue example does this in 6809 code.
No observer may see half a commit.
An interrupt handler that reads the world needs more care, and nothing here
tests it.

## Make the phase order part of the rules

**Our adaptation.** This order uses the article's three phases.
It puts the check for the end of play after production.

```text
start_next_turn():
    require the previous turn complete and the next turn in range
    turn += 1
    land each due or overdue journey in slot order; free each slot once
    collect and check each player's commands, in the declared player order
    apply production and capacity limits
    phase = FINISHED if victory or turn limit, else COMPLETE
```

Slot order is our tie rule, and a reused low slot can change the battle order.
If that matters, give each journey a sequence number.
Decide whether a captured planet produces at once.
Decide whether a player with only a fleet in transit is still active.
Do not start a turn while commands are pending.

**Published listing.** Do not copy the listing's bounds.
It allocates and searches slots 1–25, but the arrival scan checks only 1–15
(lines 590–610 and 1000, PDF 13–14).
The check for a player who is out also scans 1–15.
The free-slot search returns slot 1 when the queue is full (lines 3890–3930
and 4360–4380, printed 16, PDF 18). [Listing][conqueror-slots]

The last page repeats lines 5200–5270 (PDF 19).
We read these from page images, ran none of them and found no correction.
The `BAD_LAST` and `BAD_FULL` controls of the example are faults of this kind.

## Consume one selection in one menu state

**Published explanation.** Mike Rigsby's *Entry Way*, *Undercolor* 1(5),
February 20, 1985, scans columns, then the entries of the selected column.
After the last entry, it returns to the column scan.
Keyboard, audio and switch routines report a selection.
Short delays reduce long-sound and contact-bounce problems.
The SPEED option changes the dwell time but clears the message.
[Printed 11, PDF 13][entry-way]

**Our adaptation.** The menu consumes one accepted `SELECT` event.
The input adapter sends one event for each press and needs a release before
the next.
The source delays do not show that release rule.
A selection in the column scan opens the items.
A selection in the items submits the command and returns to the columns.
Each selection or dwell expiry starts a new dwell.

When a selection and a dwell expiry come together, use the selection.
Keep a partly composed command outside the menu display.
Then a change of dwell speed does not erase it.

## Decide which phases accept input

**Published explanation.** Scott Norman's *Field of Honor*, *Color Computer
Magazine*, March 1983, builds pictures behind a text message.
It waits for a charge command and plays the charge with no key polling.
Only then does it calculate the outcome. [Printed 24–27, PDF 22–25][honor]

Richard Ramella's *The Sorcerer's Puzzles*, April 1983, has two useful parts.
*Color Stones* redraws only after an accepted key.
*Red Rover* blinks the cursor on idle passes, and only movement changes the
move count. [Printed 33–34, PDF 35–36][puzzles]
His June correction says that *Color Stones* and *Firecracker* need Extended
Color BASIC. [June 1983, printed 12, PDF 14][correction]

**Our adaptation.** Specify the input for each phase before you write the loop:

| Phase | World changes | Input |
| --- | --- | --- |
| Prepare pictures | None | Cancel only. Discard play commands. |
| Wait for a command | One commit | Check. A rejection changes nothing. |
| Play the sequence | None | Cancel only. Discard play commands. |
| Return to play | None | Reset the presentation. Wait for a new command. |

A cutscene that reads no input is a valid choice.
Write that choice down instead of promising controls that the loop cannot read.

**Measured.** The [collect-room example](../../examples/collect-room/README.md)
applies this table to a title, play and won phase on CoCo 1 and CoCo 2B. Its
check plays 95 key steps through the emulated keyboard. A Space key that is
held at startup or across a phase change does not start or restart the game.

## Commit once, then present the result

**Published explanation.** Norman's prose adds a check of the defensive choice
and moves the bout count after it.
The printed listing does not have that fix, and its lower bound is not
readable. [Printed 25 and 27, PDF 23 and 25][honor-fix]

**Our adaptation.** Check a command, commit it once, then make a presentation
for the result.
Showing that presentation again must never apply the command again.
A renderer or a sound routine must not own the move count.
At a phase change, consume the event that caused it.
Keep the held state of the controls across phases, as the
[controls guide](controls-and-collision.md#sample-controls-before-choosing-actions)
describes.

**Published explanation.** William Barden Jr.'s *Color Animation*, May 1983,
builds five poses once and captures each with its background.
[Printed 26, 28–31, 34, PDF 24, 26–29, 32][barden-one]
In Part II, June 1983, the prose gives 648 bytes for each picture.
Our arithmetic for 76 rows of 9 bytes gives 684. [PDF 34–37][barden-two]
Mark prepared pictures ready only when they are complete, and make them again
when their artwork or background changes.

## Return to the outer loop after one piece of work

**Our adaptation, not tested.** Each pass of the loop samples one event, then
does one bounded piece of work in the current phase.
Cancel comes first and makes no new commit.
Start the dwell of each shown item after you show it, so slow work makes the
sequence longer but never makes it catch up.
A long blocking sound routine defeats this loop.
Read [sound scheduling](sound.md) before you combine them.

## What the example checks

**Measured result.** On the pinned XRoar, `coco.py check examples/turn-queue`
matches all 44 records of 19 cases on a 128 KiB CoCo 3.
The records cover these items:

- rejection without a change, then a valid send
- slot reuse, landing once, overdue landing and saturation at 255
- phase guards and the turn limit at 65535

Five broken builds fail at their named steps.
The program keeps the machine state that BASIC sets, with interrupts on.
No interrupt handler reads the world.
This is RAM state only.

## Open questions

These proposals have no check yet:

- A held switch across the column-to-item change makes only one change.
- Cancel works within one pass during preparation and playback.
- A brief press between two samples, which polling alone can miss.
- Changed artwork makes prepared pictures out of date.
- An interrupt handler never sees a commit half done.
- The same state routines on the CoCo 1 and CoCo 2.

PDF pages are positions in the archive files, and these sources have no
resource IDs. *Undercolor* 1(5) has SHA-256
`147a2fe3791911ab677a0c16d691d303991f88f71682455735957b255a08de48`.
*Undercolor* 1(6) has SHA-256
`ece378326dbb9445862baf54633e68f98196e4cc17745c7d3781546d083e2a78`. Its
contents footer repeats February 20, but its article pages say March 8.

We read the contents pages of all eleven *Undercolor* issues and the indexed
corrections. Issue 8, printed 18 / PDF 20, is a speech-processor test. Issue 9,
printed 22 / PDF 24, adds a missing figure to an earlier clock project. Neither corrects *Conqueror!*, *Entry
Way* or *Winky*, and web searches found no correction. That does not prove
that none exists.

[conqueror]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf#page=12>
[conqueror-slots]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf#page=18>
[entry-way]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n05%20%281985%29%28ColorPlus%20Inc%29.pdf#page=13>
[honor]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=22>
[honor-fix]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=23>
[puzzles]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208304%20-%20April%201983.pdf#page=35>
[correction]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=14>
[barden-one]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208305%20-%20May%201983.pdf#page=24>
[barden-two]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=34>
