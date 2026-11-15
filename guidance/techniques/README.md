# Techniques for games and demos

Start with the effect you want. Each guide explains a practical approach,
credits its sources, and states what has been tested.
Read one guide at a time. The research and validation records are below this
folder.

| I want to… | Read | Current evidence |
| --- | --- | --- |
| Animate objects or alternate pictures | [Plan animation storage](animation.md) | [150-frame renderer windows](validation/animation-cadence.md) expose partial erasure. Published [CoCo 1/2](validation/clean-animation.md) hidden-buffer checks pass 38 tests (97.01% coverage), 150-frame windows and cross-sequence chronology. Published [CoCo 3](validation/clean-animation-coco3.md) checks pass 28 tests (93.51%), all 42 frames and ordered scenes 0–4 on both RAM capacities. |
| Move objects over scenery or detect collisions | [Move objects without losing the world](moving-objects.md) | Original full-redraw and masked-object framebuffer checks on defined CoCo 1/2 configurations. Broader collision proposals remain untested. |
| Decide which parts of a scene to redraw | [Decide what to redraw](selective-redraw.md) | [Bounded CoCo 3 RAM validation](validation/selective-redraw.md): 12 checkpoints for each selective/full build at 128/512 KiB. No rendered-output or speed claim. |
| Combine movement, firing and collision rules | [Separate controls, collision, and artwork](controls-and-collision.md) | [26 host cases](validation/controls-collision.md) check bounded logical input and collision policies. Separate [keyboard validation](validation/keyboard-controls.md) passes 21 tests on CoCo 1/2B through the XRoar keyboard API, matrix/PIA and 6809 scanner, not OS or physical input. |
| Schedule turns, journeys and menu transitions | [Separate game state from presentation](game-state.md) | [60 host cases](validation/game-state.md) check bounded state transitions and rejection. A separate [CoCo 3 subset](validation/game-state-coco3.md) passes 35 tests and 44 checkpoints at both 128/512 KiB, not the full host model. |
| Choose a graphics mode or convert artwork to screen bytes | [Draw in the VDG graphics modes](graphics.md) | Mode table, colour sets and bit order from the MC6847 datasheet. The `xroar` palette in `scripts/graphics.py` is measured by [palette swatches](../../examples/palette-swatches/README.md) on CoCo 1 in CG6 and RG6. The NTSC pixel shape is a deduction. |
| Prepare reusable artwork | [Prepare assets before drawing](assets.md) | [33 host cases](validation/assets.md) check original RG6 packing and publication. A separate [6809 consumer](validation/asset-loading.md) passes 35 tests and all 6,144 framebuffer bytes on CoCo 1/2. Banked storage remains untested. |
| Keep controls available during preparation and playback | [Define game phases](game-loop.md) | [Four examined Color Computer Magazine articles and a correction](research/color-computer-magazine.md). Original game-loop adaptation remains untested. |
| Build a room from tiles | [Separate map, drawing, and movement](tile-maps.md) | Original fixed tile-room checked on defined CoCo 1/2 targets. [Bounded source follow-up](research/tile-source-followup.md) leaves historical CoCo 1/2 tile-ID provenance unresolved. The hunt is stopped pending a substantive new lead, not evidence of archive-wide absence. |
| Smooth CoCo 3 text output | [Text scrolling and the 512K correction](scrolling.md#scroll-text-a-scan-line-at-a-time) | Hardware cross-check and instrumented display-address probe complete. Scrolling itself unverified. |
| Scroll a CoCo 3 playfield | [Plan scrolling and memory](scrolling.md) | Examined book. No scrolling implementation reproduced. |
| Get the intended colours | [Design for the display](colour.md) | Static CoCo 1/2 renderer geometry measured. CoCo 2 has 12 positive cases at two settling times on an explicit non-T1 target. Animation and physical displays remain unverified. |
| Play sound during drawing and input | [Schedule sound](sound.md) | CoCo 1/3 execution and eleven DAC interval cases measured. Separate [CoCo 2 validation](validation/sound-coco2.md) passes 19 tests with per-boundary delay checks and scripted logical input. [Reviewed mixer PCM capture](validation/audio-output.md) adds 33 tests and 95.44% scoped coverage on CoCo 1/2. No host playback, listening or physical-output claim. |

CoCo 1, 2, and 3 all belong in this collection. Evidence is uneven today.
A shared hardware description does not establish that an example runs on
another model. Each guide names its narrower scope.

## Put a technique to work

For a complete playable example, start with
[collect-room](../../examples/collect-room/README.md). Its instructions cover play,
reproduction checks and the limits of its evidence. For smaller building blocks,
use the [example index](../../examples/README.md).

To reproduce a measurement or inspect its failure controls, use the
[experiment index](../../experiments/README.md). For setup instructions, source
research and validation reports, use the separate sections of the
[guidance index](../README.md).
See [PLAN.md](../../PLAN.md) for outstanding work.

## Read the evidence correctly

**Published explanation** means we examined the cited passage. It does not
mean we reproduced its program or established who first invented the idea.
**Our adaptation** means the starter authors derived the advice or procedure.
**Measured result** means a linked experiment checked a stated outcome.
A proposal remains untested until an experiment supplies that evidence.

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

For source selection, rejected matches, and open questions, read the
[game research notes](research/README.md) or
[sound research notes](research/sound.md).
The [plan](../../PLAN.md#guide-contract) defines what each guide contains.
