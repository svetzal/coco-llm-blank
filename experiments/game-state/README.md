# Bounded game-state reference model

This original Python experiment makes the proposals in
[Schedule turns and menu transitions](../../guides/game-state.md) executable.
It is host-side evidence only. It is neither a BASIC port nor a CoCo program.
Read the [validation and source record](../../guidance/game-state-validation.md)
for examined passages, measured results and remaining adapter work.

## Reproduce from a fresh clone

Run these commands from the repository root with Python and uv available:

```sh
uv sync --locked
mkdir -p build/game-state
COVERAGE_FILE=build/game-state/.coverage uv run --no-sync pytest \
  experiments/game-state --cov \
  --cov-config=experiments/game-state/coverage.ini \
  --cov-report=term-missing \
  --cov-report=json:build/game-state/coverage.json \
  --junitxml=build/game-state/results.xml -q
uv run --no-sync ruff check experiments/game-state
uv run --no-sync ruff format --check experiments/game-state
markdownlint experiments/game-state/README.md guidance/game-state-validation.md
```

No ROMs, source downloads, emulator, graphics window or model weights are
needed to execute this experiment. The repository's existing locked Python
setup installs its standard dependencies. Markdown lint is a separate host
tool, not a requirement for executing the model. Tests are co-located and
explicitly selected because the starter's default test path is `scripts/`.
The scoped coverage configuration excludes specifications, includes the
intentional controls, and retains the 90% gate. Generated reports stay in
ignored `build/game-state/`.

## Original rules used by the oracle

These are experiment choices, not claims about the historical games or decisions
about a future game. Tests use literal outcomes and hand arithmetic, not a
second call to the production algorithm to calculate expected results.

- Two to 26 planets; one to 25 journey slots; player identifiers 1 through 6;
  owner 0 is neutral. Players have an explicit, unique order.
- Ships and production use integers 0 through 255; a journey carries 1 through
  255 ships. Turns stop at a configured limit no greater than 65535. No wrap.
- The caller supplies travel delay as an integer number of turns. Delay must
  be at least one and arrival must fit within the configured game limit.
  Geometry, routes and travel-time calculation are outside this model.
- Sending validates phase, planet indices, ownership, count, time and capacity
  before constructing a replacement world. Rejection returns the unchanged
  world and a reason. Input records and world snapshots are frozen.
- Allocation uses the first free slot. Arrivals resolve in increasing slot order
  when their due turn is less than or equal to the new turn. Each resolved slot
  becomes free. Reuse of a low slot can affect later simultaneous battle order.
- Friendly arrivals add strength, capped at 255. Enemy strength subtracts;
  a strictly stronger attacker takes ownership with the difference. A tie leaves
  the defender owning the planet with zero ships. Neutral planets can be captured.
- Arrival resolution happens before commands. A player is active while owning
  any planet or any fleet, including the last queue slot. Surviving players issue
  commands in declared order; finishing one player permits the next.
- After the last player's commands, each owned planet produces once, capped
  at 255. A newly captured planet produces immediately. Neutral planets do not
  produce. Then one or zero surviving players, or the turn limit, ends play.
  An entirely ownerless world ends directly after arrivals, with no commands.
- `begin_turn` and final `finish_commands` are whole transitions. Arrival and
  production phases are internal synchronous computations; callers see only
  `turn_complete`, `commands` or `finished`. Starting a new turn during commands
  or after the limit is rejected. Repeating completed production is rejected.
- Menu events contain an already accepted selection and/or one logical tick.
  Selection wins over a coincident tick, consumes one transition and resets dwell.
  Dwell expiry advances the column or item. Passing the last item returns to
  the first column. Selecting an item returns its command label without executing
  a world command. Changing dwell resets its countdown and preserves highlight.
- The caller owns a partially composed command. Display, dwell changes, timeout
  and draft cancellation never call `try_send`. Tests exercise this composition
  boundary; there is no command editor, persistence layer or UI framework.

## Use the small API

`game_state_model.py` contains immutable validated records and pure functions.
The executable specifications are its runner; no separate application is needed.
For a small interactive host check, run from the repository root:

```sh
PYTHONPATH=experiments/game-state uv run --no-sync python - <<'PY'
from game_state_model import Planet, World, begin_turn, try_send

world = World(
    planets=(Planet(owner=1, ships=20), Planet(owner=2, ships=10)),
    journeys=(None, None),
)
world, resolved_slots = begin_turn(world)
world, status = try_send(world, 1, 0, 1, 7, 3)
assert resolved_slots == ()
assert status == "accepted"
assert world.planets[0].ships == 13
assert world.journeys[0].arrival == 4
print(status, world.model_dump_json())
PY
```

The returned immutable world is the commit boundary. Retaining the old snapshot
is safe; publish the returned value once in a single-owner loop. This does not
prove interrupt-safe multi-byte writes on a 6809, allocation-failure recovery,
thread safety of a surrounding application, or a validated external input parser.
Public function arguments follow their Python integer/type contracts.

## Preserve controls that fail the contract

`game_state_controls.py` is deliberately wrong. Its functions exist only to
show that the independent acceptance outcomes distinguish the failures:

| Control | Required outcome | Observed wrong outcome |
| --- | --- | --- |
| Scan only first 15 of 25 slots | Slot 24 resolves | No slot resolves |
| Survival scans 15 slots | Players `(1, 2)` survive | Only player 1 survives |
| Deduct before validation | Source retains 20 ships | Source has 18 ships |
| Full-queue fallback | Original event preserved | First event overwritten |

The specifications pass by explicitly detecting these wrong results alongside
correct outcomes. They are not expected-failure skips or hidden failures.
The truncated scans and overwrite are source-inspired controls. Early deduction
is an invented partial-mutation control, not an assertion that Conqueror!
executes that exact failure path. No historical listing has been executed.
