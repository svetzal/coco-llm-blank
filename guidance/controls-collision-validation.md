# Controls and collision policy validation

Read this alongside [controls and collision](../guides/controls-and-collision.md)
when selecting logical input and collision policies. The original executable
[model](../experiments/controls-collision/controls_collision.py) and
[literal scenarios](../experiments/controls-collision/controls_collision_spec.py)
validate a bounded subset of that guide's proposals on the host. They are not
a keyboard driver, a historical program reproduction, or 6809 performance proof.
The existing guide's hardware and broader implementation proposals remain open.

## Examined source and original additions

This pass examined the local full-page images of Larry Landwehr's
"Read the Keyboard in Assembly," *Hot CoCo*, October 1983, Vol. 1 No. 5,
printed/PDF pages [106 and 108][keyboard]. The page-106 listing compares whole
read bytes and branches for left before checking right and space; page 108
explains the demonstration's loop. Page 106's M-key prose and matrix table
conflict, and page 108's matrix dimensions differ from the table's labelled
rows. This experiment supplies no register recipe and does not resolve those
source discrepancies. Logical simultaneous-input fixtures do not establish
which physical key combinations work.

Matt Togliatti's "Attacker," in the same issue, printed/PDF
[86 and 88][attacker], was also examined as page images. Line 150 on page 86
uses four screen-point tests. Lines 530–550 and 650–660 on page 88 combine
screen tests with coordinate comparisons. These passages motivate separate
questions about scenery and objects. They do not specify our occupancy grid,
substeps, startup policy, or swept calculation.

The source PDF has SHA-256
`76218e4e0bc98ca0545ef3db34ce89bfb080998d7e89370f3ced483a2909e7a4`.
The examined images already existed under ignored
`local/research/hot-coco-games/1983-10-p{86,88,106,108}.png`.
[Prior research provenance](hot-coco-game-research.md#sources-and-reading-coverage)
records that edition and broader reading coverage. This pass examined only the
four pages named above and made no new errata search. No downloaded material
is needed to execute the original tests or included in the experiment.

All executable logic here is an original adaptation of the guide's proposals.
The swept interval example is an original, deliberately narrow addition.
No historical listing or artwork is copied.

## Contract and pseudocode correspondence

`actions(previous, held)` corresponds to the guide's subtraction of logical
left/right states and rising fire edge. The caller seeds `previous` with its
startup sample and saves every later sample, including release. Opposing keys
cancel movement; fire remains independent. A blocked move must not prevent the
input caller from recording its new sample. There is no repeat timer, debounce,
keyboard scan, or electrical polarity model.

`blocked` corresponds to the guide's loop over probe offsets. Coordinates are
integer cells in a half-open world: zero is inside, width and height are outside.
Outside cells are solid. Occupancy is immutable and supplied separately from
artwork. A probe touching an occupied cell is rejected. Probes must be nonempty,
and the starting position must be valid; these are preconditions, not checked
input-validation features.

`move_horizontal` corresponds to the guide's candidate-before-commit loop.
It stops at the first blocked unit step and returns the last accepted position.
Rejection leaves the input position and scenery unchanged. The caller fixture
also checks unrelated score and life values; the model does not implement a
score or life system. A clear return path remains usable after rejection.

The one extension is a nonnegative step budget, default 32. Excess displacement
is discarded, never applied as a destination jump. The caller can request later
movement explicitly. This bounds each call by budget times probe count; it is
not a cycle or wall-clock measurement. A negative budget raises `ValueError`.
The fixtures use a 12-by-6 world, with one-cell and three-cell vertical shapes.
The fuller shape covers this fixture; it is not a general shape solver.

`swept_interval_contact` handles only closed, nonnegative-width intervals on one
axis, moving linearly during the same update. Touching counts. It subtracts B's
motion from A's, then checks whether the resulting relative-position interval
intersects `[-a_width, b_width]`. Fractions keep this calculation exact.
This follows directly from the two overlap inequalities. It detects contact,
not time of impact or a collision response. It does not solve diagonal,
accelerating, rotating, or deforming motion.

## Literal scenarios and failed controls

The expected positions and event sequences are literal test data independent
of rendering. Negative controls pass their tests by exhibiting the documented
wrong result; they are retained executable examples, not skipped or expected
failures hiding a broken suite.

- A direction remains active across held samples. Fire produces two events
  across press/hold/release/repress; naive held-fire produces three.
- Startup-held fire is suppressed until release and repress. Movement remains
  held at startup. Initializing the previous sample to idle fires immediately.
- Left plus fire, right plus fire, and opposing directions plus fire retain
  the fire edge. A direction-first early return loses fire or imposes priority.
- A wall at `(5, 2)` stops travel from `(1, 2)` at `(4, 2)` and travel from
  `(8, 2)` at `(6, 2)`. Destination-only controls cross the wall both ways.
  Repeated rejection preserves state; travel away from the wall still works.
- Probes at vertical offsets 0 and 2 miss an obstacle at `(4, 2)` while moving
  at y=1. Adding offset 1 stops at x=3. Unit substeps alone retain the miss.
- Changing a flower into wall-coloured artwork and hiding the real wall leaves
  occupancy-driven movement unchanged. The art-derived failure control stops
  at x=2 instead of x=4. Explicitly removing the solid cell and its wall art
  permits crossing and return. This fixture demonstrates coordinated edits;
  it does not implement an editor or prove automatic synchronization.
- Boundary cells, zero movement, clear travel, zero and negative budgets, and
  an exhausted budget are checked. A subsequent request still stops at the wall.
- A diagonal endpoint at `(2, 2)` is clear while both orthogonal neighbours
  are blocked. A policy that forbids corner cutting must reject it. There is
  no implemented diagonal movement policy here.
- Two unit-width objects swap sides without overlapping at either endpoint.
  The relative sweep detects contact. Comparing one new position with the
  other's old position instead produces false contact in a same-speed case.
- A point crosses the fractional obstacle `[2/5, 3/5]` between samples 0 and 1.
  Those samples miss it; the interval sweep detects it. Initial overlap,
  exact endpoint contact, separation, and equal velocities are also checked.

A press and release entirely between idle samples is indistinguishable from no
press. The retained test records this information limit; it cannot simulate or
validate a physical switch. Likewise, more finite samples cannot guarantee
contact detection for arbitrarily thin continuous geometry.

## Reproduce and interpret the result

From the repository root, after preparing the locked project environment:

```sh
(
set -e
mkdir -p build/controls-collision
if COVERAGE_FILE=build/controls-collision/.coverage \
  uv run --no-sync pytest experiments/controls-collision \
  --cov=controls_collision --cov-branch --cov-report=term-missing \
  --cov-report=json:build/controls-collision/coverage.json -q \
  > build/controls-collision/pytest.txt 2>&1; then
  cat build/controls-collision/pytest.txt
else
  test_status=$?
  cat build/controls-collision/pytest.txt
  exit "$test_status"
fi
uv run --no-sync ruff check experiments/controls-collision
uv run --no-sync ruff format --check experiments/controls-collision
markdownlint guidance/controls-collision-validation.md
)
```

Use `uv sync --locked` first in a fresh clone. No firmware, native tools, source
PDFs, network access during tests, or GUI is required. The normal default
pytest path is `scripts`, so explicitly select this experiment as above.
Generated evidence belongs under ignored `build/controls-collision/`.

The original run passed 25 scoped cases on macOS with Python 3.13.12.
A review follow-up adds a combined blocked-movement and input-history scenario:
press, hold, release and repress while blocked, then movement away. The naive
caller that saves input only after movement produces extra fire events.
All 26 cases passed after that correction.
Coverage was 100% of this model's 30 statements and six branches. This is a
finite host test result, not a proof over arbitrary shapes or an execution-speed
benchmark. The full starter suite was not run for this isolated addition.

Assembly, emulator execution, framebuffer, rendered display, physical input,
and physical-machine checks were not performed. No CoCo 1/2/3 compatibility or
6809 timing result follows. Next implementation work needs a target-specific
input adapter and separate execution checks, plus an explicit geometry and
contact-response contract before expanding beyond horizontal scenery motion.

[keyboard]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=106>
[attacker]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=86>
