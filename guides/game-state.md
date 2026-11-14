# Schedule turns and menu transitions

Read this when building a turn-based strategy game with journeys that take
several turns, or a menu operated by one switch. Keep world state, pending
commands and presentation state separate. A redraw must not advance a turn.

All pseudocode and design rules below are original, untested adaptations.
They can inform CoCo 1, 2 or 3 projects, but establish no machine compatibility,
RAM budget or timing result. The sources use contemporary BASIC; *Conqueror!*
also requires an external assembly screen expander and does not state its RAM
requirement (printed 11, PDF 13). Verify each target's input and display adapters
separately. No register writes, wiring or BASIC delay loops are recommended here.

## Store an arrival, not every position along the route

Tony Byorick's "Conqueror!", *Undercolor*, volume 1, issue 6, March 8, 1985,
printed 10–12, PDF 12–14, separates planet data from scheduled arrivals. Its
turn has arrival, command and production phases. The command path checks source
ownership and available strength before recording destination, strength, player
and arrival turn. [Source pages][conqueror]

For a new game, give each journey an active flag, owner, destination, strength
and arrival turn. Add departure data only if route animation needs it. Keep that
animation subordinate to the scheduled arrival rule. Choose one capacity `N`
for allocation, arrival resolution and checks for fleets still in transit.
Storage is bounded by `N * bytes_per_record`, plus planet and control state;
field widths and alignment belong to the new game's format.

This trades a fixed event table for repeated movement calculations. Scanning
that table still costs work each turn, and a full table must have defined
behavior. It suits delayed orders; it does not supply arcade movement physics.

### Reject a command before changing the world

Validate the whole command and construct its event before deducting ships.
Cancellation, invalid input, arithmetic overflow and queue exhaustion must
leave both planets and journeys unchanged.

```text
try_send(player, source, destination, count):
    if not command_phase_for(player): return WRONG_PHASE
    if not valid_distinct_planets(source, destination): return INVALID
    if source.owner != player: return NOT_OWNER
    if count <= 0 or count > source.ships: return INVALID_COUNT
    delay = travel_turns(source, destination)
    if delay < 1 or not representable(turn + delay): return INVALID_TIME
    slot = first_inactive_slot(journeys[0:N])
    if slot is absent: return QUEUE_FULL
    event = Journey(player, destination, count, turn + delay)
    commit_together:
        journeys[slot] = active(event)
        source.ships -= count
    return ACCEPTED
```

`commit_together` specifies an observable contract, not a hardware instruction:
no observer sees half a command, and neither write can fail after mutation starts.
A single-owner game loop can keep input and drawing outside that commit. Choose
an explicit turn limit or a wrap-safe time representation before implementing
`representable`; this example does not handle clock wrap.

## Make phase order part of the rules

Use one explicit order and keep it stable. This proposed order follows the
article's three phases but places the final continuation check after production:

```text
start_next_turn():
    require previous turn finished and next turn representable
    turn += 1
    phase = ARRIVALS
    resolve each active journey with arrival_turn <= turn in slot order
    retire each resolved journey exactly once
    phase = COMMANDS
    collect and validate each player's commands in the declared player order
    phase = PRODUCTION
    apply production and planet capacity limits
    phase = FINISHED if victory_or_turn_limit() else TURN_COMPLETE
```

Slot order is this example's tie rule, not a claim that simultaneous battles
must work that way. Reusing a low slot can change battle order. If that is
undesirable, assign a sequence number or resolve simultaneous arrivals together.
Likewise, define whether a newly captured planet produces immediately and whether
a player with no planets but a fleet in transit remains active. Presentation
updates may occur within phases, but cannot repeat production or resolve an
arrival twice. Do not start another turn while commands are still pending.

### Preserve the source discrepancies

Do not copy the listing's bounds as a reusable queue contract. It initializes
and searches slots 1–25, but arrival resolution checks 1–15. The player-out
check also scans only 1–15. The free-slot search returns slot 1 when full.
See lines 590–610 and 1000, printed 11–12, PDF 13–14; lines 3890–3930 and
4360–4380, printed 16, PDF 18. [Listing continuation][conqueror-slots]
The final page repeats lines 5200–5270 after 5320 (printed 17, PDF 19).
[Final listing page][conqueror-ending]

These are image-reading findings, not reproduced failures or published fixes.
The research did not locate a correction for them. Its issue-6 contents footer
also repeats February 20 while the article pages say March 8; use issue identity
and PDF position. The proposed rejection and consistent capacity deliberately
replace these listing behaviors.

## Consume one selection in one menu state

Mike Rigsby's "Entry Way", *Undercolor*, volume 1, issue 5, February 20, 1985,
printed 10–12, PDF 12–14, describes scanning columns, then entries within a
selected column. Passing the entries without selecting returns to column scan.
Its input routines support keyboard, audio or switch activation; short delays
address long sounds and contact bounce. They do not establish release-before-
reselection behavior. [Software explanation, printed 11, PDF 13][entry-way]

Our menu adaptation consumes an already accepted `SELECT` event. The input
adapter must emit only one event per press and require release before another;
keep its held/pressed and debounce algorithm outside this state machine. A held
switch must not select a column and then immediately select an item in it.

```text
on_menu_event(event):
    if event == SELECT:
        if phase == COLUMNS:
            phase = ITEMS
            highlight = first_item(selected_column)
        else:
            submit_highlighted_command_for_validation()
            phase = COLUMNS
        restart_dwell()
        return                       # consume this event once
    if event == DWELL_EXPIRED:
        advance_highlight_or_return_to_columns()
        restart_dwell()
```

When selection and dwell expiry coincide, process selection and discard that
expiry. Start a fresh dwell after the transition. Changing menu state does not
reset the input adapter's release requirement. Keep a composed command outside
the menu display so changing dwell speed need not erase it; the historical SPEED
option clears the message (printed 11, PDF 13). This is a proposal for accessible
menus and turn-based commands, not evidence for simultaneous arcade controls.

## Check the behavior before relying on it

These are proposed acceptance checks, not completed tests:

- Fill all `N` slots. Reject the next send with identical planet and journey
  state; then resolve a journey in the last slot and reuse that slot.
- Reject invalid ownership, count, destination and time without mutation.
  Cancel a partially entered command with the same result.
- Resolve two arrivals on one turn in the declared order, retire both once,
  and apply production once. Check a captured planet and a fleet-only player.
- Redraw or animate repeatedly while awaiting commands. The turn and world
  state must remain unchanged.
- Hold selection across a column-to-item transition. It must cause only one
  transition. Release and press again to select the item. Exercise no input,
  the last item, timeout, coincident expiry and selection, and a speed change
  with a command partly composed.

## Sources and provenance

The [Undercolor research record](../guidance/undercolor-game-research.md)
contains archive hashes, full reading coverage, correction-search limits and
configuration gaps. These sources have no manifest resource IDs. PDF pages are
one-based positions in the archived files. No historical listing or adaptation
has been run here; there is no build, runtime, framebuffer, rendered-display,
audio or physical-hardware evidence for this guide.

- Byorick, Tony. "Conqueror!" *Undercolor*, volume 1, issue 6, March 8, 1985.
  Passages used here: printed 10–12 and 16–17, PDF 12–14 and 18–19.
  [Archive][conqueror]
- Rigsby, Mike. "Entry Way." *Undercolor*, volume 1, issue 5, February 20, 1985.
  Passages used here: printed 10–12, PDF 12–14.
  [Archive][entry-way]

[conqueror]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf#page=12>
[conqueror-slots]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf#page=18>
[conqueror-ending]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf#page=19>
[entry-way]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n05%20%281985%29%28ColorPlus%20Inc%29.pdf#page=13>
