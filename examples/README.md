# Examples

These are a variety of examples that show specific techniques for doing things in certain situations.

eg
- choosing and setting up the screen for your program
- getting keyboard input
- playing audio alongside gameplay

Each example may have code that builds up the context, which is actually not part of the example. After
that comes a marked example of doing the one special thing the example is about.

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

| Task | Example | Machines | Scope |
| --- | --- | --- | --- |
| Set up a graphics screen | [First screen](first-screen/README.md) | CoCo 1, 2, 3 | All eight VDG full-graphics modes, with the SAM and `$FF22` values and `PMODE` numbers. Rendered check of each mode. RG1, RG2 and RG3 are not checked on CoCo 3. |
| Select a colour set | [Palette swatches](palette-swatches/README.md) | CoCo 1, 2, 3 | `$FF22` CSS in CG6 and RG6, with the colour of each code. The evidence for the `xroar` and `xroar-coco3` palettes in `scripts/graphics.py`. |
| Restore scenery under moving objects | [Moving objects](moving-objects/README.md) | CoCo 1, 2, 3 | Scenery buffer, save-under and full-redraw methods over a changing background. Rendered check of each method. |
| Show only finished frames | [Page flip](page-flip/README.md) | CoCo 1, 2, 3 | Two moving rectangles, drawn into a hidden screen. SAM flip on every machine; GIME `$FF9D` flip (variant `coco3`) on CoCo 3 at 128 and 512 KiB. Rendered check of both screens at selected flips. |
| Draw transparent and opaque pixels | [Masked objects](masked-objects/README.md) | CoCo 1, 2, 3 | Mask, opaque and XOR draw methods over patterned scenery. Rendered check of each method. |
| Read held keys and single presses | [Keyboard controls](keyboard-controls/README.md) | CoCo 1, 2, 3 | Keyboard matrix scan, movement plus action and edge rejection. No display. |
| Keep room state in a tile map | [Tile room](tile-room/README.md) | CoCo 1, 2, 3 | Draw and move from one map of tile numbers; changed-cell and full redraw. Scripted moves, pictures converted from a drawing. Rendered check at every move. No keyboard or victory rule. |
| Accept input only in the right game phase | [Collect room](collect-room/README.md) | CoCo 1, 2, 3 | Title, play and won phases, a startup-held Space and restarts in a whole small game. Rendered and sound check at 95 key steps. |
| Queue turns and reject bad commands | [Turn queue](turn-queue/README.md) | CoCo 1, 2, 3 | Scheduled journeys, phases and a turn limit. RAM only. |
| Play a tone from the main loop | [Sound slots](sound-slots/README.md) | CoCo 1, 2, 3 | Cooperative DAC tone; sawtooth and square. |
| Play sound from a timer interrupt | [Timer sound](timer-sound/README.md) | CoCo 3 | GIME timer FIRQ, with cooperative builds for comparison. |
| Set up a CoCo 3 text screen | [Text addressing](text-addressing/README.md) | CoCo 3 | 32, 40, 64 and 80 columns at one physical address on 128 and 512 KiB. Rendered check of each width. |

Most examples run unchanged on all three machines, because the CoCo 3 keeps
the CoCo 1 and 2 hardware. Only the GIME practices are CoCo 3 only. When a
practice has a CoCo 3 form, it is a variant of the same example.
Each example names its own target and reproduction procedure. A result on one
emulator configuration does not establish another model or physical hardware.
Use the [technique guides](../guidance/techniques/README.md) to understand the design and its
sources before you adapt a program.

## Checks

`scripts/coco.py` builds, runs and checks every example. Run it with `--help`
to see its commands.
The `expected.py` oracle and `coco.py check` are the test of an example.
The root pytest suite runs the real check of each example and the negative
controls in `scripts/coco_spec.py`.

For prerequisites, obey each example's README.
For setup and contributor instructions, use the
[operational guidance](../guidance/README.md#using-the-starter).
