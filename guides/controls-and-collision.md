# Separate controls, collision, and artwork

Read this when held movement must coexist with single-press actions, or when
changing a picture must not change what blocks the player. The proposals below
use logical controls and collision coordinates. They can inform CoCo 1/2/3
designs. The host model checks bounded collision policies; the separate
[keyboard experiment](../guidance/keyboard-controls-validation.md) now supplies
a bounded CoCo 1/2B scanner and execution check. The examined articles concern
the original CoCo generation; broader target compatibility needs its own checks.

## Sample controls before choosing actions

Larry Landwehr's "Read the Keyboard in Assembly," *Hot CoCo*, October 1983,
compares complete keyboard-read bytes and branches on left before checking
right or space. Its demonstration therefore has an early-branch priority.
[Printed/PDF 106 and 108][keyboard]. Our inference is
that whole-byte equality can also reject an intended key when another input
bit changes. Neither behaviour is a suitable default for movement plus fire.

Keep the printed discrepancies visible: Landwehr's M-key example says 233,
but the table places M under 223 (printed/PDF 106). The continuation says
eight rows by eight columns, while the table has seven labelled row values
(printed/PDF 106, 108). [Landwehr, "Read the Keyboard in Assembly"][keyboard].
These conflicts remain unresolved here. Before writing a scanner, check the
target hardware reference for PIA setup, row masks, shared input bits, and
supported key combinations. Use the [primary input-hardware findings](../guidance/input-hardware-research.md)
for board-specific matrix coordinates and shared-input limits. This article
alone is not a register recipe.

Our adaptation is to sample every required control, then apply an explicit
policy. Use held state for movement and a rising edge for a single action.
This original pseudocode chooses neutral movement when left and right are
both held, allows movement plus fire, and suppresses a startup-held fire key:

```text
previous = input.sample_required_controls()  # Before the first update.

each update:
    held = input.sample_required_controls()
    pressed = held AND NOT previous
    horizontal = integer(held.right) - integer(held.left)
    request_movement(horizontal)
    if pressed.fire:
        request_one_shot()
    previous = held
```

The adapter returns logical booleans, independent of electrical polarity.
For startup-held buttons to count as presses, initialize `previous` to all
false instead. For automatic fire, use held state with a chosen repeat
interval. Define the same opposing-direction rule for a vertical axis, and
choose whether diagonal movement is allowed before adding it. These are game
policies, not Landwehr's rules. Edge detection neither debounces switches nor
repairs matrix ghosting; it can also miss a press released between samples.

## Give scenery and objects different collision questions

Matt Togliatti's "Attacker," *Hot CoCo*, October 1983, uses four screen-point
tests around the player in line 150. Its projectile code combines screen
tests with coordinate comparisons against the player in lines 530–550 and
650–660. This is an examined example of mixing scenery and object tests,
not a general collision library. [Printed/PDF 86 and 88][attacker].

Our proposed division is:

- Ask scenery whether a location is solid. Screen colours can answer this
  when drawing intentionally defines the world. Then colour choices, erasure,
  and drawing order are part of collision behaviour. Use a separate occupancy
  map when decoration must change independently. That requires storage and a
  rule that scenery edits update both collision data and the picture.
- Ask objects whether their explicit collision shapes intersect. Use this for
  a projectile hitting an actor, even if their pictures have transparent holes
  or overlap decorative scenery. Bounds are a deliberate approximation; they
  do not imply pixel-perfect contact.

Choose collision units, world boundaries, whether touching counts, and the
response to contact (stop, slide, damage, or collect). Decide which positions
object tests compare within an update. Testing one actor's new position against
another's old position introduces update-order policy. Rendering should follow
the resolved state when collision is independent of artwork.

The [moving-object guide](moving-objects.md#decide-whether-the-picture-is-also-the-collision-map)
explains the rendering side and distinguishes visibility from solidity.
Its full-redraw and masked-object examples do not implement collision.

## Use sparse probes only where gaps are acceptable

A few probe offsets are easy to inspect for a small ship in broad tunnels.
Keep those offsets as collision data, separate from the sprite. Togliatti's
four screen tests motivate this choice, but the separate scenery query and
substeps below are our additions, with bounded host-model checks linked below.
[Matt Togliatti, "Attacker," October 1983, printed/PDF 86, line 150][attacker].

This original pseudocode deliberately handles integer, horizontal movement
against stationary scenery. It assumes a valid starting position, solid cells
on a unit grid, and a policy that stops at the first blocked candidate:

```text
function blocked(position, probes, scenery):
    for offset in probes:
        point = position + offset
        if outside_world(point) OR scenery.is_solid(point):
            return true
    return false

function move_horizontal(position, dx, probes, scenery):
    for step in 1 through abs(dx):  # No iterations when dx is zero.
        candidate = position + (sign(dx), 0)
        if blocked(candidate, probes, scenery):
            break
        position = candidate
    return position
```

Unit steps prevent a probe from skipping a solid grid cell along this path.
They do not fill gaps between probes: a one-cell obstacle can lie between two
probe tracks throughout the move. Thin posts, corners, and irregular obstacles
need all relevant edge cells or an explicit shape-intersection method. A larger
sprite also needs a deliberate collision-shape review.

Do not extend this loop to diagonal motion without defining the path and corner
rule. Axis-by-axis movement introduces axis priority; diagonal endpoint tests
can miss intervening contact. Moving objects require relative-motion checks or
a separately specified shared stepping scheme. Arbitrary fractional geometry
needs a step bound derived from that geometry, or a swept collision test.
Simply adding more substeps is not a completeness proof. If an update caps its
substeps, defer or reject remaining movement; do not jump to the destination.

## Minimum checks before adopting either proposal

Use expected positions and events written independently of the renderer:

1. Hold a direction across updates, then release. Movement continues only
   while held. Hold fire across those same updates: one shot, then another
   only after release and a new press. Check the chosen startup policy.
2. Press direction plus fire, and both opposing directions plus fire. Expect
   movement plus one shot in the first case, neutral movement plus one shot
   in the second. Test the real input adapter on each claimed machine too.
3. Accept a clear path and stop before a wall. Cross a thin wall with a large
   displacement; a destination-only failure control must miss it while the
   unit-step version detects it when a probe track crosses the wall.
4. Put a one-cell obstacle between probe tracks. Demonstrate the sparse
   method's miss, then require the chosen fuller shape test to detect it if
   that obstacle belongs in the game. Check boundaries and corner policy.
5. Change decoration without changing collision data; expect identical
   movement with an independent map. Change solid scenery and verify both
   representations. Check projectile/actor contact separately from scenery,
   including crossing paths between updates and the chosen touching rule.

A [host reference model](../guidance/controls-collision-validation.md) now checks
26 bounded scenarios for logical input, horizontal grid movement and one-axis
sweeps, including naive failure controls. That does not validate a CoCo input
adapter, arbitrary geometry, performance, display or physical hardware.
The broader target-specific checks above remain required.

The separate [keyboard report and reproduction commands](../guidance/keyboard-controls-validation.md)
record 21 passing tests with 97.06% runner coverage. Original 6809 code scans
left, right and space on explicit NTSC, 32 KiB, stock-clock CoCo 1 and CoCo 2B
profiles. Both match all 16 update records, including startup-held suppression,
movement plus action, opposing directions, blocked release/repress and return
from both boundaries. Wrong-column, wrong-register-selection, held-action and
stale-history controls fail the independent expectations.

Injection calls XRoar's `keyboard_press`/`keyboard_release` API. Its real matrix
and PIA feed the 6809 scanner; the hook does not write logical input or RAM.
This is not OS key-event, physical-key, debounce or general chord evidence.
There is no cadence, rendered-output, sound or CoCo 3 result. The host collision
model remains separate; these bounded position checks do not port that model.

Source reading and page-image
inspection support the historical descriptions only. The
[research provenance](../guidance/hot-coco-game-research.md#sources-and-reading-coverage)
records local evidence, hashes, full reading coverage, and research-local IDs
`hot-coco-games-keyboard` and `hot-coco-games-attacker`; these are not manifest
IDs. Its bounded correction search does not establish that no later errata
exist. Citations here use one-based PDF pages, equal to printed pages in the
linked October 1983 OCR edition, Vol. 1 No. 5.

[keyboard]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=106>
[attacker]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=86>
