# Programs to play and study

Start with [collect-room](collect-room/README.md) for a complete playable game.
In the game, you collect two stars and reach the exit. After that, you
restart. Its README gives setup, launch commands, controls and the exact
emulator contract for CoCo 1/2B. Read its evidence limits separately from its
instructions for playing.

## Choose a smaller building block

| Task | Example | Scope |
| --- | --- | --- |
| Set up a graphics screen | [First screen](first-screen/README.md) | All eight VDG full-graphics modes, with the SAM and `$FF22` values and `PMODE` numbers. Rendered check of each mode. |
| See every VDG graphics colour | [Palette swatches](palette-swatches/README.md) | CG6 and RG6 bars for both colour sets. The evidence for the `xroar` palette in `scripts/graphics.py`. |
| Redraw objects over scenery | [Moving objects](moving-objects/README.md) | Ordered opaque rectangles over a changing background. |
| Show only finished frames | [Page flip](page-flip/README.md) | The moving-objects scene, drawn into a hidden screen on CoCo 1/2. Rendered check at every flip. |
| Show only finished frames on CoCo 3 | [Page flip on CoCo 3](page-flip-coco3/README.md) | Native GIME buffers at 128 and 512 KiB. Rendered check at every flip. |
| Draw transparent and opaque pixels | [Masked objects](masked-objects/README.md) | Software masks over patterned scenery. |
| Read held keys and single presses | [Keyboard controls](keyboard-controls/README.md) | Keyboard matrix scan, movement plus action and edge rejection on CoCo 1/2. No display. |
| Keep room state separate from drawing | [Tile room](tile-room/README.md) | Scripted movement and collection, with tile pictures converted from a drawing. Rendered check at every move. No keyboard or victory rule. |
| Queue turns and reject bad commands | [Turn queue](turn-queue/README.md) | Scheduled journeys, phases and a turn limit on CoCo 3. RAM only. |
| Combine sound, drawing and input | [Sound slots](sound-slots/README.md) | Cooperative scheduling probe, not a music engine. |
| Compare sound scheduling on CoCo 3 | [Timer sound](timer-sound/README.md) | Cooperative and GIME interrupt builds. |
| Investigate CoCo 3 display addresses | [Text addressing](text-addressing/README.md) | Address probe, not a scrolling demo. |

Each example names its own target and reproduction procedure. A result on one
emulator configuration does not establish another model or physical hardware.
Use the [technique guides](../guidance/techniques/README.md) to understand the design and its
sources before you adapt a program.

## Checks

`scripts/coco.py` builds, runs and checks every example. See its README.
The root pytest suite selects `scripts/` and `examples/`, including each
example model's spec.

For prerequisites, obey each example's README.
For setup and contributor instructions, use the
[operational guidance](../guidance/README.md#using-the-starter).
