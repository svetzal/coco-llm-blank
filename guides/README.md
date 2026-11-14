# Techniques for games and demos

Start with the effect you want. Each guide explains a practical approach,
credits its sources, and states what has actually been tested.
Your agent can read one guide without loading the whole research collection.

| I want to… | Read | Current evidence |
| --- | --- | --- |
| Animate objects or alternate pictures | [Plan animation storage](animation.md) | Examined BASIC articles; assembly adaptations remain untested. |
| Move objects over scenery or detect collisions | [Move objects without losing the world](moving-objects.md) | Original full-redraw and masked-object framebuffer checks on defined CoCo 1/2 configurations; broader collision proposals remain untested. |
| Decide which parts of a scene to redraw | [Decide what to redraw](selective-redraw.md) | [Bounded CoCo 3 RAM validation](../guidance/selective-redraw-validation.md): 12 checkpoints for each selective/full build at 128/512 KiB; no rendered-output or speed claim. |
| Combine movement, firing and collision rules | [Separate controls, collision, and artwork](controls-and-collision.md) | [26 host cases](../guidance/controls-collision-validation.md) check bounded logical input and collision policies; no target execution or physical-input evidence. |
| Schedule turns, journeys and menu transitions | [Separate game state from presentation](game-state.md) | [60 host cases](../guidance/game-state-validation.md) check bounded state transitions and rejection; CoCo execution remains unverified. |
| Prepare reusable artwork | [Prepare assets before drawing](assets.md) | [33 host cases](../guidance/asset-validation.md) check original RG6 packing and publication; target loading and banked storage remain untested. |
| Keep controls available during preparation and playback | [Define game phases](game-loop.md) | [Four examined Color Computer Magazine articles and a correction](../guidance/color-computer-magazine-research.md); original game-loop adaptation remains untested. |
| Build a room from tiles | [Separate map, drawing, and movement](tile-maps.md) | Original fixed tile-room checked on defined CoCo 1/2 targets; [bounded source follow-up](../guidance/tile-source-followup.md) leaves historical CoCo 1/2 tile-ID provenance unresolved. The hunt is stopped pending a substantive new lead, not evidence of archive-wide absence. |
| Smooth CoCo 3 text output | [Text scrolling and the 512K correction](scrolling.md#scroll-text-a-scan-line-at-a-time) | Hardware cross-check and instrumented display-address probe complete; scrolling itself unverified. |
| Scroll a CoCo 3 playfield | [Plan scrolling and memory](scrolling.md) | Examined book; no scrolling implementation reproduced. |
| Get the intended colours | [Design for the display](colour.md) | Static CoCo 1/2 renderer geometry measured; CoCo 2 has 12 positive cases at two settling times on an explicit non-T1 target. Animation and physical displays remain unverified. |
| Play sound during drawing and input | [Schedule sound](sound.md) | CoCo 1/3 execution and eleven DAC interval cases measured; no worst-case, listening or physical evidence. |

CoCo 1, 2, and 3 all belong in this collection. Evidence is uneven today.
A shared hardware description does not establish that an example runs on
another model. Each guide names its narrower scope.

The [current dispatched batch](../PLAN.md#current-dispatched-batch-in-progress)
is in progress: keyboard input, target assets, a CoCo 3 state subset, CoCo 2
sound and animation cadence. Input source reading and the bounded sudo-policy
checks are complete; the remaining contracts add no completed runtime results.

For setup evidence, the [nonroot Ubuntu record](../guidance/linux-onboarding-validation.md#nonroot-sudo-validation)
reports passwordless-sudo bootstrap, 13 CoCo 2 moving-object frames and preserved
notes on rerun. Separate [sudo-policy checks](../guidance/sudo-policy-validation.md)
cover denied/password-required failures and prerequisite recovery. This is
ARM64 container evidence, not a native desktop,
GUI, audible-output or physical-machine check.

## Read the evidence correctly

**Published explanation** means we examined the cited passage. It does not
mean we reproduced its program or established who first invented the idea.
**Our adaptation** means the starter authors derived the advice or procedure.
**Measured result** means a linked experiment checked a stated outcome.
A proposal remains untested until an experiment supplies that evidence.

Citations sit beside the claims they support. PDF page numbers are one-based
positions in the archive file. Printed page numbers appear separately when known.
Source resource IDs resolve to URLs and checksums in [resources.json](../resources.json).
Use [reference lookup](../guidance/references.md) to download only the needed pages.
Check diagrams, tables, and assembly listings against their page images.

These guides explain techniques in our own words. They do not redistribute
books, magazine listings, music, or art. Archive availability grants no license
to reuse someone else's code or assets.

## Before writing a game

Read the selected guide, then inspect its cited hardware passages for your target.
Record the machine, memory, video standard, display, and CPU clock in project notes.
Keep unresolved details visible. Do not fill gaps from model memory.

Start with a small example and check its memory writes and timing.
Treat an assembled binary, emulator execution, visible output, audible output,
and physical-machine behaviour as separate evidence.

For source selection, rejected matches, and open questions, read the
[game research notes](../guidance/game-research.md) or
[sound research notes](../guidance/sound-research.md).
The [plan](../PLAN.md#permanent-technique-guides) defines how this collection grows.
