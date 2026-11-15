# Programs to play and study

Start with [collect-room](collect-room/README.md) for a complete playable game.
In the game, you collect two stars and reach the exit. After that, you
restart. Its README gives setup, launch commands, controls and the exact
emulator contract for CoCo 1/2B. Read its evidence limits separately from its
instructions for playing.

## Choose a smaller building block

| Task | Example | Scope |
| --- | --- | --- |
| Check a first CoCo 1 screen | [First screen](first-screen/README.md) | Border and square. A setup checkpoint, not a game. |
| See every VDG graphics colour | [Palette swatches](palette-swatches/README.md) | CG6 and RG6 bars for both colour sets. The evidence for the `xroar` palette in `scripts/graphics.py`. |
| Redraw objects over scenery | [Moving objects](moving-objects/README.md) | Ordered opaque rectangles over a changing background. |
| Draw transparent and opaque pixels | [Masked objects](masked-objects/README.md) | Software masks over patterned scenery. |
| Keep room state separate from drawing | [Tile room](tile-room/README.md) | Scripted movement and collection. No keyboard or victory rule. |
| Combine sound, drawing and input | [Sound slots](sound-slots/README.md) | Cooperative scheduling probe, not a music engine. |
| Compare sound scheduling on CoCo 3 | [Timer sound](timer-sound/README.md) | Cooperative and GIME interrupt builds. |
| Investigate CoCo 3 display addresses | [Text addressing](text-addressing/README.md) | Address probe, not a scrolling demo. |

Each example names its own target and reproduction procedure. A result on one
emulator configuration does not establish another model or physical hardware.
Use the [technique guides](../guidance/techniques/README.md) to understand the design and its
sources before you adapt a program.

## Examples and experiments

Examples are entry points for building, running and studying programs. Some
existing examples are deliberately small research probes, as the table notes.
Their location does not imply a complete game or general support.

[Experiments](../experiments/README.md) hold bounded investigations, host models
and measurement harnesses. They often consume examples without changing them.
Use experiments when you reproduce evidence. Do not use them as a substitute
for a playable example. Existing files stay in place. These indexes describe
their roles.

## Checks

`scripts/coco.py` builds, runs and checks every example. See its README.
The root pytest suite selects `scripts/` and `examples/`, including each
example model's spec.

Experiment specs are separate. You must select them explicitly. For
prerequisites and scoped commands, obey
[the suite boundaries](../experiments/README.md#choose-the-right-test-suite)
and each example's README.
For setup and contributor instructions, use the
[operational guidance](../guidance/README.md#using-the-starter).
