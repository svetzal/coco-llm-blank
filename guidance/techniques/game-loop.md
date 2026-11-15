# Keep input available across game phases

Read this when a game prepares pictures, waits for a command, plays an animated
sequence, then returns to play.
Decide which phases accept input before choosing the drawing routine.
A faster renderer alone does not make an unpolled sequence interactive.

The procedure and pseudocode below are original, untested adaptations.

The sources concern the original CoCo generation, with Color BASIC or Extended
Color BASIC hosts.
One adds assembly copying.
They establish no tested CoCo 2 or CoCo 3 compatibility.

The design can inform all three machines, but input, clock, display and sound
adapters need target-specific evidence.
There is no new runtime, timing, visual, audio or physical-hardware result here.

## Decide what advances without a command

Two historical structures answer different needs:

- Scott Norman's "Field of Honor", March 1983, prepares pictures behind a text
  message and waits for C.
  It then completes a charge animation before calculating the outcome.
  The playback path has no key polling.
  This is a noninteractive sequence after a choice.
  [Printed 24–27, PDF 22–25][honor]

- Richard Ramella's "The Sorcerer's Puzzles", April 1983, includes Color Stones
  and Red Rover.
  Color Stones redraws after accepted keys.
  Red Rover also blinks a cursor on idle passes.
  Its move counter changes in movement routines, independently of the blink.
  [Printed 33–34, PDF 35–36][puzzles]

For a new puzzle, advance world state only after an accepted command.
Idle animation may change the presentation without consuming a move.

If a scene must accept cancel or pause during playback, return to input polling
between bounded pieces of work.
A deliberately noninteractive cutscene is a valid choice too.
Document that choice instead of promising controls that its loop cannot read.

Before implementation, specify these phase contracts in the game's own terms:

| Phase | World changes | Input policy for this proposed puzzle |
| --- | --- | --- |
| Prepare pictures | None | Cancel only. Discard play commands. |
| Await command | Commit once | Validate. Rejection leaves state unchanged. |
| Play sequence | None | Cancel only. Discard play commands. |
| Return to play | None | Reset presentation and await a fresh command. |

The table is our policy, not the historical programs' contract.
If animation represents ongoing physics, it needs a different world-update
policy.
This guide does not establish a fixed-step physics loop or a catch-up algorithm.

## Validate before committing, then show the result

Norman's explanatory text adds validation for the defensive choice and moves
the bout-count increment after it.
The printed listing lacks that fix.
Its scanned lower-bound expression is incomplete.
["Field of Honor", printed 25 and 27, PDF 23 and 25][honor-fix]

Do not copy damaged syntax.
Use the menu's stated domain when you specify an original implementation.

Our adaptation validates a command before changing the puzzle, commits it once,
and creates a presentation sequence for that result.
Repainting or replaying that sequence must never apply the command again.
This deliberately differs from Norman's ordering, where the charge precedes
outcome calculation.
A renderer or a sound callback cannot own the move counter.

When entering a new phase, consume the triggering event.
Keep the input adapter's held/released state across transitions.
Then a held button does not become a new press merely because preparation
finished.

The [controls guide](controls-and-collision.md#sample-controls-before-choosing-actions)
covers that distinction.
This guide adds the phase boundary.

## Prepare pictures once, with an explicit validity rule

William Barden Jr.'s "Color Animation", May and June 1983, moves from repeated
DRAW/clear operations to five stored poses.
It moves from there to assembly copies under a BASIC host.

The eight-position sequence reuses poses.
The captured rectangles cover the same fixed footprint, including the background.
This explains why replacement can erase the previous pose in that example.
Moving the rectangle elsewhere needs a separate restoration design.
[Part I, printed 26, 28–31, 34, PDF 24, 26–29, 32][barden-one].
[Part II, printed 32–35, PDF 34–37][barden-two].

Prepare immutable pose data before an interactive sequence where memory permits.
If preparation itself takes noticeable time, divide it into bounded steps or
make its input restriction explicit.
Merely displaying a waiting message does not provide cancellation.

Mark pictures ready only when all required data is complete.
Rebuild them when their source artwork or captured background changes.
For general scenery, use the [moving-object guide](moving-objects.md).

Storage trades against construction work.
Keep the sequence order and dwell values separate from stored pictures.
Then repeating a pose need not duplicate its pixels.

Count actual payload, stride and bounds.
Barden's June prose says 648 bytes, but its nine-byte rows over 76 rows need
684.
The historical 700-byte buffer spacing still fits.
This arithmetic is our source-reading check, not a tested allocator.
[Printed 33–34, PDF 35–36][barden-copy]

## Return to the outer loop after one piece of work

This original pseudocode specifies an untimed puzzle's presentation.
`now` is an abstract monotonic counter.
An implementation must define units, wrap handling and the maximum interval it
supports.

Each preparation step and each presentation call must have a finite, checked
cost.
A whole-frame renderer can still delay the next input sample.

```text
initialize world, phase=PREPARE, preparation cursor, sequence cursor
initialize input edge state from current held controls

repeat:
    event = sample_and_consume_one_logical_event()
    now = clock()

    if event == CANCEL:
        discard unfinished presentation
        leave puzzle                       # highest priority; commit no new move
    else if phase == PREPARE:
        prepare_one_bounded_piece()
        if all_required_pictures_ready():
            phase = AWAIT_COMMAND
    else if phase == AWAIT_COMMAND:
        if is_play_command(event) and valid(event, world):
            commit_one_move(world, event)
            sequence = presentation_for_committed_result(world)
            cursor = 0
            deadline = now
            phase = PLAY_SEQUENCE
    else if phase == PLAY_SEQUENCE and due(now, deadline):
        if cursor < sequence.length:
            present(sequence[cursor])       # no world mutation
            deadline = clock() + sequence[cursor].dwell
            cursor += 1
        else:
            phase = AWAIT_COMMAND           # final dwell has completed
```

Each loop takes one phase branch, so an event cannot both finish preparation
and issue a play command.
The loop discards unused events.
This proposal does not queue commands during animation, and cancellation does
not undo an already committed move.
If undo is required, define and test it as a separate rule.

The loop sets the deadline after presentation to provide a minimum dwell.
Work delays therefore lengthen the sequence rather than causing unbounded
catch-up.
This is a chosen cutscene policy, not calibrated motion timing.
It adds a phase, cursor and deadline but avoids keeping the entire sequence on
the call stack.

Long blocking sound routines would still defeat the input contract.
Read [sound scheduling](sound.md) before combining the two.

## Checks required before relying on this proposal

These are proposed acceptance checks, not completed tests:

1. Send no command while idle presentation changes. World state and move count
   remain identical. Reject an invalid command with the same result. A control
   version that increments before validation must fail that expectation.

2. Hold a play button through preparation and playback. It must not issue a
   command on entry to the next phase. Release the button. Press it again to
   issue one.

3. Accept one command. Redraw its sequence repeatedly. Expect one move and
   one result. Check the final dwell, return to command input, and a second
   accepted command. A test that only proves the game remains paused is
   incomplete.

4. Request cancel during preparation and during playback. Expect exit at the
   next poll. Compare with a deliberately blocking whole-sequence control that
   cannot see the request until it returns. Measure the real longest poll
   interval before claiming a response-time bound.

5. Delay rendering and sound. Confirm the chosen dwell policy. Test brief
   presses entirely between polls. Polling alone cannot guarantee detecting
   those presses. Require a stronger input contract only with adapter evidence.

6. Change captured background data and invalidate prepared pictures. Compare
   the next visible result with an independent redraw. Test first use and
   memory guards, not just repeated identical poses.

The [research record](research/color-computer-magazine.md) contains these
items:

- complete reading coverage
- download hashes
- research-local IDs
- configuration limits
- errata boundaries

In particular, Ramella's June correction changes the April claim of Color BASIC
compatibility for Color Stones and Firecracker.
Read that correction before you try either historical listing.
No sources here have manifest IDs yet.
No historical listings are redistributed.

[honor]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=22>
[honor-fix]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=23>
[puzzles]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208304%20-%20April%201983.pdf#page=35>
[barden-one]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208305%20-%20May%201983.pdf#page=24>
[barden-two]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=34>
[barden-copy]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=35>
