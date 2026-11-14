# Techniques for games and demos

Start with the effect you want. Each guide explains a practical approach,
credits its sources, and states what has actually been tested.
Your agent can read one guide without loading the whole research collection.

| I want to… | Read | Current evidence |
| --- | --- | --- |
| Animate objects or alternate pictures | [Plan animation storage](animation.md) | Examined BASIC articles; assembly adaptations remain untested. |
| Move objects over scenery or detect collisions | [Move objects without losing the world](moving-objects.md) | Original full-redraw and masked-object examples checked on defined CoCo 1/2 configurations; collision remains untested. |
| Decide which parts of a scene to redraw | [Decide what to redraw](selective-redraw.md) | CoCo 3 Gloom/Symmetry source reading only; original adaptation untested. |
| Combine movement, firing and collision rules | [Separate controls, collision, and artwork](controls-and-collision.md) | Examined Hot CoCo articles; original adaptations remain untested. |
| Schedule turns, journeys and menu transitions | [Separate game state from presentation](game-state.md) | Examined Undercolor articles; original adaptations remain untested. |
| Build a room from tiles | [Separate map, drawing, and movement](tile-maps.md) | CoCo 3 tile source and legacy BASIC room-map reading complete; CoCo 1/2 bitmap renderer gap and original adaptation remain open. |
| Smooth CoCo 3 text output | [Text scrolling and the 512K correction](scrolling.md#scroll-text-a-scan-line-at-a-time) | Hardware cross-check and instrumented display-address probe complete; scrolling itself unverified. |
| Scroll a CoCo 3 playfield | [Plan scrolling and memory](scrolling.md) | Examined book; no scrolling implementation reproduced. |
| Get the intended colours | [Design for the display](colour.md) | Static CoCo 1 renderer geometry measured, including frozen frames; animation, other targets and physical displays unverified. |
| Play sound during drawing and input | [Schedule sound](sound.md) | CoCo 1/3 execution and eleven DAC interval cases measured; no worst-case, listening or physical evidence. |

CoCo 1, 2, and 3 all belong in this collection. Evidence is uneven today.
A shared hardware description does not establish that an example runs on
another model. Each guide names its narrower scope.

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
