# Undercolor techniques for game state, input and small updates

Use this note when designing a turn-based game, a single-switch menu, or a
small procedural animation. It complements the [technique index](../guides/README.md)
without changing the starter's renderer or input routines.

Four articles were read from page images, including listings and continuations.
The procedures below are original, untested adaptations. No historical program
was assembled or run. There are no measured speed, framebuffer, rendered-display,
audio or physical-hardware results from this research.

## Choose the relevant technique

| Task | Source article | Issue |
| --- | --- | --- |
| Schedule arrivals and turn phases | *Conqueror!* | 6 |
| Select commands with one switch | *Entry Way* | 5 |
| Animate part of a static picture | *Another Fine Mess* | 3 |
| Grow a picture without a shape history | *Summer Frippery* | 11 |

*Conqueror!* requires an external assembly screen expander; its RAM requirement
is unstated. *Entry Way* uses BASIC with keyboard, audio or switch input.
Its wiring and register reads need independent target verification.
*Another Fine Mess* uses Extended Color BASIC. Its companion listings identify
16K, but Winky's header does not independently specify RAM. *Flower Fantasy*
is explicitly 16K Extended Color BASIC and includes an optional speed POKE.

These are 1985 sources for the contemporary Color Computer environment.
They do not establish CoCo 3 compatibility. The state and menu proposals can
be implemented for CoCo 1, 2 or 3, but each machine still needs its own verified
input/display adapter and runtime checks. No particular ROM revision, PAL/NTSC
configuration, display path or stock-clock performance is established here.
Do not transplant POKEs, PMODE changes or BASIC delays into an assembly driver.

## Schedule events instead of simulating every journey

Byorick divides play into arrival, command and production phases. Planet arrays
hold coordinates, ownership, strength and production. Separate arrival arrays
hold arrival turn, strength, destination and player. Commands check ownership
and available strength before scheduling a journey. See *Conqueror!*, printed
10–12, PDF 12–14, especially lines 570–610 and 980–1510. The external screen
expander requirement is explicit on printed 11, PDF 13. [Issue 6][uc6]

The listing has hazards worth preserving in the record. It allocates and searches
25 arrival slots, but the arrival loop checks 15 (lines 590, 1000 and 3890–3930;
PDF 13–14 and 18). When no empty slot is found, the search returns slot 1.
The final page also repeats lines 5200–5270 after line 5320 (PDF 19).
These are image-reading findings, not reproduced failures or published errata.

### Original adaptation for scheduled journeys

For a strategy game, retain journeys as future events. Choose a capacity and
use that same capacity for allocation, resolution and player-elimination checks.
Reject a command without changing state if there is no free slot.

```text
accept_send(player, source, destination, count):
    require valid distinct planets
    require source.owner == player
    require 0 < count <= source.ships
    slot = find_free_journey_slot()
    if slot is absent: return QUEUE_FULL
    event = journey(player, destination, count,
                    turn + travel_turns(source, destination))
    install(slot, event)
    source.ships -= count
    return ACCEPTED

advance_turn():
    turn += 1
    due = active journeys whose arrival_turn <= turn
    resolve due journeys in a documented stable order
    retire each resolved journey exactly once
    collect each player's commands
    apply production and capacity limits
    determine whether play continues
```

This deliberately changes the historical implementation. Specify whether
simultaneous arrivals resolve in insertion order or as a combined battle.
Specify whether production occurs before or after the final victory check.
Those are game rules, not performance optimizations.

The proposal trades a bounded event table for repeated movement calculations.
It does not require drawing ships in transit. An animated route can derive its
picture from departure and arrival state without changing the arrival rule.
Capacity, field widths and clock wrap must be chosen for the new game; the
article does not supply a reusable memory budget.

Before implementation is accepted, check a full queue, its last slot, multiple
arrivals on one turn, cancellation of invalid input, and a player who owns no
planet but still has a fleet in transit. Independently assert that rejection
preserves both ship counts and scheduled journeys. Advancing presentation alone
must not advance a turn.

## Make a single-switch menu a small state machine

Rigsby's cursor scans columns, then scans the selected column's entries. If no
entry is selected, it returns to the column scan. Separate input subroutines
report activation from keyboard, audio or switch. The audio/switch routines add
short delays to reduce long-sound/contact-bounce problems. The SPEED option
changes dwell time but clears the message. Characters are arranged by expected
frequency rather than alphabetically. See *Entry Way*, printed 10–14, PDF 12–16;
software explanation on PDF 13–14, complete listing on PDF 15–16. [Issue 5][uc5]

### Original adaptation for a single-switch menu

A game menu can share one selection event across several devices. Keep the
selection logic independent of how the device is sampled. Require release before
a held switch can select again; the historical delay alone is not proof of
that behavior.

```text
on_sample(raw_pressed, elapsed_ticks):
    event = debounce_and_detect_new_press(raw_pressed)
    if event:
        if phase == COLUMNS:
            phase = ITEMS
            item = first_item(column)
        else:
            execute_command(item)
            phase = COLUMNS
        dwell_remaining = dwell_ticks
    else:
        dwell_remaining -= elapsed_ticks
        if dwell_remaining <= 0:
            advance_highlight_or_return_to_columns()
            dwell_remaining = dwell_ticks
```

The adapter needs a stated debounce interval and release rule. The pseudocode
assumes it produces one event per accepted press; it does not implement a
hardware scanner. Define precedence when activation and dwell expiry coincide.
Here activation wins. Start a fresh dwell interval after a selection so the
newly highlighted item cannot expire immediately.

Keep dwell settings and pending game commands separate from the menu display.
Changing scan speed should preserve a partially composed command unless the
new game's rules explicitly say otherwise. A small elapsed-time counter replaces
the source's blocking delay loops, but its tick source remains target-specific.

Test no input, a held switch across both phases, bounce, release/repress, the
last item, timeout back to columns, and a speed change during a selection.
This design suits turn-based commands and accessible menus. It is not evidence
for responsive simultaneous movement and firing in an arcade game.

## Draw the scene once, then change the animated feature

Ramella's *Another Fine Mess* includes three complete listings. *Winky* builds
a face and then loops over the eye's arcs (lines 670–760, PDF 6). The continuation
suggests stopping after individual drawing commands to inspect their effect
(PDF 25). Read printed 2–4, 6 and 23, PDF 4–6, 8 and 25. [Issue 3][uc3]

The prose's listing-line references sometimes disagree with the actual numbers;
for example, its description of the final music calls does not match Listing 1.
Use the listing and image together. Its statement that the horizontal axis has
255 points also should not replace the project's verified graphics references.

### Original adaptation for a static scene

For a title-screen blink or gauge, give the changing feature a fixed rectangle.
Draw the rest once. Restore that rectangle before drawing each new state.
Restoration is our addition, not an algorithm established by Winky.

```text
enter_title():
    draw_static_title()
    saved_region = capture(feature_bounds)
    displayed_state = NONE

show_feature(next_state):
    if next_state == displayed_state: return
    restore(feature_bounds, saved_region)
    draw_feature(next_state)
    displayed_state = next_state
```

A captured rectangle costs memory proportional to its packed pixel area.
Redrawing the same rectangle from original scene data can save that storage at
the cost of more drawing. Neither choice has been timed here. If another object
can overlap the rectangle, restoration can erase it; use the overlap discipline
in [moving objects](../guides/moving-objects.md), or prohibit that overlap.

Check that pixels outside the rectangle never change, reopening the eye removes
all closed-eye pixels, and repeated identical states produce the same picture.
Use an original design, not the magazine's character artwork or music.

## Let the accumulated image be the demo's history

*Flower Fantasy* chooses a centre and colour, rejects a colour matching the
existing centre pixel, and adds circle segments without clearing the screen on
each pass. Its prose identifies 16K Extended Color BASIC and says to omit the
speed POKE if unsupported. *Summer Frippery*, printed 16, PDF 18, contains both
complete listings and prose. [Issue 11][uc11]

The centre-pixel check is not collision detection. It does not test the new
shape's complete area. *Life on Saturn!* on the same page is a comic audiovisual
demo; it is not an examined game-rule or collision source.

### Original adaptation for an accumulating demo

An accumulating garden, trail or paint demo can retain its history in the
framebuffer instead of storing a list of every past shape. Use a logical palette
index supplied by the target renderer; do not copy the source's colour offset.

```text
grow_one_step():
    centre = choose_valid_centre()
    old_colour = read_logical_colour(centre)
    alternatives = allowed_colours except old_colour
    if alternatives is empty: return
    colour = choose(alternatives)
    draw_bounded_shape(centre, colour)
```

Choosing directly from the remaining colours bounds selection work; it replaces
the source's retry loop. Bounds, clipping and a guaranteed exit are our additions.
The technique avoids a growing shape-history list, but gives up independent
reconstruction and undo unless more state is stored. It also couples later
choices to prior rendering. A decorative palette change must not silently become
a game collision rule.

Check an empty alternative set, a deterministic seed, edge centres, clipping,
and a reset that clears both drawing and random-generator state. A framebuffer
comparison and a rendered display check would establish different things.
No such checks were run in this research pass.

## Corrections, exclusions and coverage

The contents pages of all eleven archived issues were inspected. This is not a
claim to have read all eleven issues. Full article image coverage is recorded
above; advertisements between article pages were excluded.

The explicitly indexed corrections were also inspected:

- Issue 8, printed 18, PDF 20, supplies Michael J. Lill's speech-processor test
  associated with issue 6 correspondence. It does not correct these four articles.
  [Issue 8][uc8]
- Issue 9's contents advertises corrections at printed 21, but the missing clock
  figure is actually on printed 22, PDF 24. It belongs to the earlier real-time
  clock project. Both PDF 23 and 24 were inspected. [Issue 9][uc9]

Targeted web searches did not locate corrections for Conqueror, Entry Way or
Winky. That does not prove none exist. The issue-6 slot discrepancy and duplicated
lines remain unresolved source defects, not fixes authorized by a later notice.
The clock correction is not evidence that the game listings were corrected.

The contents leads *Cross Talk*, *EPROM Erasers* and *Disk Punch* were rejected
for this task because their stated subjects are serial communication, EPROMs and
disks. *Graphics* in issue 9 remains an unexamined article, not evidence for a
collision engine. No general arcade collision technique was established by this
pass. Existing collision guidance remains the appropriate starting point.

## Source identity and local evidence

All sources are *Undercolor*, volume 1, published by ColorPlus Inc. PDF page
numbers are one-based positions in the downloaded files. Each file has 28 pages.
No manifest resource IDs were assigned in this scoped task. The links below and
SHA-256 values identify the exact archive editions instead.

| Issue | Date used | SHA-256 |
| --- | --- | --- |
| [3][uc3] | January 11, 1985 | `86b30ed5b747eac47ad21b9b28d5a241cee8807f7a06d6d14dfa436eb6c6ca96` |
| [5][uc5] | February 20, 1985 | `147a2fe3791911ab677a0c16d691d303991f88f71682455735957b255a08de48` |
| [6][uc6] | March 8, 1985 | `ece378326dbb9445862baf54633e68f98196e4cc17745c7d3781546d083e2a78` |
| [8][uc8] | April 1, 1985 | `3a6994a8dfc82207d4d2811280eef515f8b15077cbb1f865fc3e7eb2f10c86cc` |
| [9][uc9] | April 22, 1985 | `a4f6a256637ab510a703ef91143af85a0469281f0aa5c5e61248267b8bc71243` |
| [11][uc11] | June 30, 1985 | `3120b8fa4fa96baba7a6337541ad93428d4b77c3dbdd7fde441f66b50b8edbb4` |

Issue 6's contents footer incorrectly repeats February 20; its article pages
say March 8. Issue 9's correction page carries a stray April 1 footer alongside
the printed page 22 footer. Use issue identity, PDF position and hash to avoid
those date/page ambiguities.

Downloads, source metadata and rendered reading images are ignored under
`local/research/undercolor-games/`. `sources.json` records URLs, hashes and page
counts for all eleven issues. The PDFs have no useful embedded text in the
attempted extraction; reading used full-page PDFium images, with sideways
Entry Way listings rotated. No Docling conversion or shared index was changed.
No downloaded prose, historical listing, music, image or ROM is included here.
Archive availability is not a redistribution license.

[uc3]: https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n03%20%281985%29%28ColorPlus%20Inc%29.pdf
[uc5]: https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n05%20%281985%29%28ColorPlus%20Inc%29.pdf
[uc6]: https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf
[uc8]: https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n08%20%281985%29%28ColorPlus%20Inc%29.pdf
[uc9]: https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n09%20%281985%29%28ColorPlus%20Inc%29.pdf
[uc11]: https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n11%20%281985%29%28ColorPlus%20Inc%29.pdf
