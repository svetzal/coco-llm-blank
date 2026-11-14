# Host validation of scheduled journeys and menu transitions

Use this record with the [game-state guide](../guides/game-state.md) when
turning its proposals into a game. The original
[bounded reference model](../experiments/game-state/README.md) supplies executable
host checks. It does not establish CoCo 1, 2 or 3 implementation compatibility.
The existing guide's historical research remains distinct from this experiment.

## Examined primary passages

This pass read the following local PDF page images, not only the earlier guide's
summary. Page numbers below are one-based PDF positions. The archived files
have no manifest resource IDs; exact links and SHA-256 identify them.
Downloaded PDFs and reading images remain ignored in
`local/research/undercolor-games/`. This task did not download or copy them into
tracked files. A fresh clone needs none of these files to execute the experiment.

Tony Byorick, "Conqueror!", *Undercolor* 1(6), March 8, 1985:

- Printed 11, PDF 13: prose describes arrival, command and production phases.
  Lines 590–610 allocate and initialize 25 events. The prose requires an
  external screen expander. Our adaptation keeps journeys separate from planets
  and has no display or screen expander.
- Printed 12, PDF 14, lines 980–1510: the arrival scan at 1000 ends at 15.
  Commands check ownership, destination and strength, then record arrival data
  and deduct strength. Our adaptation uses one capacity for all scans and
  validates the entire command before publishing a replacement snapshot.
- Printed 16, PDF 18, lines 3890–3930 and 4360–4380: the free-slot search scans
  25 and returns slot 1 when full. The player-out fleet scan ends at 15.
  Our adaptation rejects full queues and scans every slot for survival.
  Executable negative controls preserve those mismatches.

Mike Rigsby, "Entry Way", *Undercolor* 1(5), February 20, 1985, printed 11,
PDF 13, Software and Connections sections: selection changes column scan to
entry scan. Passing entries returns to the first column. SPEED clears the
message. Input delays address long sounds/contact bounce. Our adaptation
consumes accepted events once, prioritizes selection over expiry and preserves
the caller's draft on speed changes. Physical debounce is outside the model.

Source links and locally rechecked hashes:

- [Byorick, issue 6, PDF 13][uc6]; PDF 14 and 18 were also examined.
  SHA-256:
  `ece378326dbb9445862baf54633e68f98196e4cc17745c7d3781546d083e2a78`.
- [Rigsby, issue 5, PDF 13][uc5]. SHA-256:
  `147a2fe3791911ab677a0c16d691d303991f88f71682455735957b255a08de48`.

These source findings do not establish that the historical listing fails in a
particular executed session. The earlier
[Undercolor research record](undercolor-game-research.md) records broader reading,
issue-date ambiguity and unsuccessful correction searches. This pass did not
repeat that wider correction search and does not claim no correction exists.
No new claim relies on the unexamined final listing page or its duplicated lines.

## Test contract and independent expectations

All model code and specifications are original adaptations. The
[experiment rules](../experiments/game-state/README.md#original-rules-used-by-the-oracle)
state the battle, capacity, phase and menu policies explicitly. Source combat
includes random firing and retreat; this model deliberately uses deterministic
subtraction to make ordering observable. It does not validate source combat.

For the simultaneous-arrival fixture, a neutral defence of 5 receives player 1's
8 ships, leaving player 1 with 3. Player 2's 4 ships then capture it with 1.
Production of 2 leaves player 2 with 3. Reversing those events would leave
player 1 with 7 before production, so the assertion distinguishes order.
Those literal expected values are in the specification.

Other checks cover:

- Rejection with identical full state for invalid source/destination, ownership,
  strength, phase and time. Successful sending changes both queue and source
  together while the previous snapshot stays unchanged.
- Queue capacities 1, 15, 16 and 25. Every accepted event resolves once, excess
  commands are rejected, all slots retire, and later turns repeat none of them.
- A full 25-slot queue, final-slot arrival and subsequent reuse of that slot.
- Overdue and future events, reinforcement saturation, defender survival on a
  tie, neutral capture and immediate production after capture.
- Declared player order, refusal to advance during pending commands, production
  once per turn, and victory only after final production.
- A player with no planet and a fleet in slot 24. The player stays active and
  later captures a planet. A separate case loses the final fleet and ends play.
- Arrival on turn 65535, rejection beyond it, production on the final turn and
  refusal to advance or schedule beyond the configured limit.
- One selection per menu transition, selection/expiry precedence, no-event
  input, column wrap, last-item selection, timeout back to columns, and speed
  changes with a caller-owned partial command.
- Repeated presentation and logical menu ticks leave the entire world unchanged.
  Draft cancellation is tested as a caller operation with no world dispatch;
  there is no simulated command editor to mistake for a real input adapter.

The [retained negative controls](../experiments/game-state/game_state_controls.py)
miss the final slot, eliminate a fleet-only player, mutate ships on rejected
input, and overwrite a full queue. Tests require those wrong outputs to differ
from the independently stated expected values. Partial deduction is an invented
transaction failure, not a copied BASIC routine. No historical listing, art,
music, ROM or copyrighted prose is included in the experiment.

## Measured host result

The scoped run on macOS with Python 3.13.12 passed **60 specifications** after
independent review added a constructor check for arrivals beyond the turn
limit. The boundary test also resolves an arrival exactly at that limit.
Combined statement and branch coverage was **100%** for the reference model
and intentional controls. Scoped Ruff checks and formatting, and Markdown lint
for the two new documents, passed. This is a local measured result, not a
full-starter-suite result or a claim of cross-host execution.

[Fresh-clone commands](../experiments/game-state/README.md#reproduce-from-a-fresh-clone)
use the tracked model, specifications, coverage configuration and repository
lockfile. This session used the existing project environment with `--no-sync`
to avoid disturbing parallel workers. Generated JUnit and coverage evidence is
ignored under `build/game-state/`. No untracked private script is required.

Coverage measures exercised paths, not the completeness of the game design.
The tests do not prove every possible ordering or all states within the bounds.
They provide explicit counterexamples for the capacity and atomicity hazards.

## Remaining CoCo and adapter evidence

There is no assembly, emulator execution, framebuffer, rendered display, audio
or physical-hardware evidence from this experiment. In particular:

- Choose a record layout and RAM budget for each target. Python object size is
  not a CoCo memory measurement. Implement bounded integer arithmetic and reject
  overflow before writes, including route-to-delay calculations.
- Make the multi-field commit unobservable until complete in the actual game
  loop. Interrupts, input polling and drawing must not observe a partial update.
  The immutable host API does not establish that property on hardware.
- Verify the input adapter's release requirement and debounce with held,
  released, bounced and repressed input. Here a held press is represented by
  the caller supplying no second accepted SELECT; no electrical behaviour was
  measured or inferred from that test.
- Verify timer-to-tick conversion, event arbitration and display adapters on
  each selected CoCo, ROM, video standard and clock. One Boolean logical tick
  is not a wall-clock duration; the menu has no catch-up or interrupt scheduler.
- Replay these vectors against the assembly adapter, then inspect its display
  and controls separately. Nothing in this run establishes stock-clock cost,
  PAL/NTSC dwell timing, machine compatibility or physical accessibility.

[uc6]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n06%20%281985%29%28ColorPlus%20Inc%29.pdf#page=13>
[uc5]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n05%20%281985%29%28ColorPlus%20Inc%29.pdf#page=13>
