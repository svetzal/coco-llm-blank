# Techniques for games and demos

Start with the effect you want. Each guide explains a practical approach,
credits its sources, and states what has been tested.
Read one guide at a time. Each guide ends with its sources and open
questions.

| I want to… | Read | Current evidence |
| --- | --- | --- |
| Animate objects without showing unfinished frames, or decide what to redraw | [Plan animation and redraw](animation.md) | [Page flip](../../examples/page-flip/README.md) on CoCo 1, 2, 2B and 3, with a GIME variant for CoCo 3: rendered checks at selected flips, with a partial-erasure and a wrong-base control. Selective redraw has one RAM-only lab result. |
| Move objects over scenery or detect collisions | [Move objects without losing the world](moving-objects.md) | Original restore-method and masked-object checks of screen bytes and rendered pictures on defined CoCo 1, 2, 2B and 3 configurations. Broader collision proposals remain untested. |
| Combine movement, firing and collision rules | [Separate controls, collision, and artwork](controls-and-collision.md) | [Keyboard controls](../../examples/keyboard-controls/README.md) on CoCo 1, 2, 2B and 3: 16 update records from keys played through XRoar's keyboard matrix, PIA and the 6809 scanner, with wrong-column, DDR-selection, held-fire and stale-history controls. Not host or physical input. Sparse-probe and swept-collision advice has one host-model result. |
| Schedule turns, journeys and menu transitions, or keep input available across game phases | [Separate game state from presentation](game-state.md) | [Turn queue](../../examples/turn-queue/README.md) on CoCo 1, 2, 2B and 3: 44 hand-written state records, with rejection, wrong-slot, repeat and wrap controls. RAM only. [Collect room](../../examples/collect-room/README.md) on CoCo 1, 2, 2B and 3: phase input through the emulated keyboard, 95 steps. Menu and loop proposals remain untested. |
| Choose a graphics mode or convert artwork to screen bytes | [Draw in the VDG graphics modes](graphics.md) | Mode table, colour sets and bit order from the MC6847 datasheet. The `xroar` palette in `scripts/graphics.py` is measured by [palette swatches](../../examples/palette-swatches/README.md) on CoCo 1 and both CoCo 2 targets (MC6847 and MC6847T1) in CG6 and RG6. The `xroar-coco3` palette is measured the same way on CoCo 3, with the palette that BASIC loads. The NTSC pixel shape is a deduction. |
| Prepare reusable artwork | [Prepare assets before the drawing loop](assets.md) | [Tile room](../../examples/tile-room/README.md) converts a drawing with `scripts/graphics.py` at each build and checks 42 rendered frames on CoCo 1, 2, 2B and 3. Banked storage and disk loading remain untested. |
| Build a room from tiles | [Separate map, drawing, and movement](tile-maps.md) | [Tile room](../../examples/tile-room/README.md) on CoCo 1, 2, 2B and 3: changed-cell and full redraw, 42 frames of screen bytes and the rendered picture. PacDude (CoCo 3) and other sources read, not run. We stopped the historical tile-ID hunt. The guide gives the boundary for reopening it. |
| Smooth CoCo 3 text output | [Text scrolling and the 512K correction](scrolling.md#scroll-text-a-scan-line-at-a-time) | [Text addressing](../../examples/text-addressing/README.md) sets up a text screen at 128 and 512 KiB, with a 128K-alias control. Scrolling itself unverified. |
| Scroll a CoCo 3 playfield | [Plan scrolling and memory](scrolling.md) | Examined book. No scrolling implementation reproduced. |
| Get the intended colours | [Design for the display](colour.md) | Static CoCo 1, 2, 2B and 3 rendered geometry is checked by `coco.py check --video` on first-screen and palette-swatches, with a wrong-SAM control. CoCo 3 RG1, RG2 and RG3 are an open question. Artifact colours and physical displays remain unverified. |
| Play sound while the game draws | [Keep sound playing while the game works](sound.md) | [Sound slots](../../examples/sound-slots/README.md) on CoCo 1, 2, 2B and 3 and [timer sound](../../examples/timer-sound/README.md) on CoCo 3: DAC values, memory and the mixer's tone at every checkpoint, with muted, constant, slow-foreground and masked-timer controls. No host playback, listening or physical-output claim. |

CoCo 1, 2, and 3 all belong in this collection. Evidence is uneven today.
A shared hardware description does not establish that an example runs on
another model. Each guide names its narrower scope.

## Put a technique to work

For a complete playable example, start with
[collect-room](../../examples/collect-room/README.md). Its instructions cover play,
reproduction checks and the limits of its evidence. For smaller building blocks,
use the [example index](../../examples/README.md).

To reproduce a measurement, use the example that the guide links. Its
`expected.py` and `coco.toml` hold the check. For setup instructions, use
the [guidance index](../README.md).
See [PLAN.md](../../PLAN.md) for outstanding work.

## Read the evidence correctly

**Published explanation** means we examined the cited passage. It does not
mean we reproduced its program or established who first invented the idea.
**Our adaptation** means the starter authors derived the advice or procedure.
**Measured result** means a linked example or check measured a stated outcome.
A proposal remains untested until a check supplies that evidence.

Citations are beside the claims they support. PDF page numbers are one-based
positions in the archive file. Printed page numbers appear separately when
known.
The resource IDs of sources resolve to URLs and checksums in [resources.json](../../resources.json).

Use [reference lookup](../starter/references.md) to download only the needed pages.
Check diagrams, tables, and assembly listings against their page images.

These guides explain techniques in our own words. They do not redistribute
books, magazine listings, music, or art. Archive availability grants no license
to reuse someone else's code or assets.

## Before writing a game

Read the selected guide. Then inspect its cited hardware passages for your
target.
Record these items in project notes:

- the machine
- the memory
- the video standard
- the display
- the CPU clock

Keep unresolved details visible. Do not fill gaps from model memory.

Start with a small example. Check its memory writes and timing.
Treat each of these as separate evidence:

- an assembled binary
- emulator execution
- visible output
- audible output
- physical-machine behaviour

BASIC articles can explain useful ideas. Their ROM calls, storage formats and
performance do not transfer to assembly. The sources and open questions in
each guide record what we read, what we rejected and what is still open.
The [plan](../../PLAN.md#guide-contract) defines what each guide contains.
