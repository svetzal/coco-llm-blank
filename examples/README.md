# Examples

These are a variety of examples that show specific techniques for doing things in certain situations.

eg
- choosing and setting up the screen for your program
- getting keyboard input
- playing audio alongside gameplay

Each example may have code that builds up the context that is actually not part of the example, and then
a marked example of doing the one special thing the example is about.

It's not always about the best way, it's an illustration of a technique or a starting point if you don't
know what else to do.

Think of these examples as building blocks, not to necessarily copy as-is, but to study to decide what to
do in your own code.

## Try one now

Open a terminal in the starter folder. Paste this line to see the
[first-screen](first-screen/README.md) example in XRoar. Close the window to
stop it.

```sh
uv run python scripts/coco.py run examples/first-screen
```

Each example README gives the commands for that example.

## The Example Catalogue

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
