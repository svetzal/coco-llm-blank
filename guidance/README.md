# Agent guidance

This folder holds everything an agent reads to work well in this starter.
Beginners do not need it. They start with the [README](../README.md).
Agents enter through [AGENTS.md](../AGENTS.md), which says when to read each part.
[PLAN.md](../PLAN.md) holds outstanding work.

| Folder | Holds | Read it when |
| --- | --- | --- |
| [starter/](#using-the-starter) | How to use this repository: setup, tools, references and development practice | Setting up, building, testing, or looking up a source |
| [techniques/](techniques/README.md) | Game and demo domain guidance: how to animate, draw, control, store and play sound | Choosing or applying a technique for the owner's project |
| `techniques/research/` | Source research behind the techniques | Tracing a claim, or extending a technique with new sources |
| `techniques/validation/` | Measured results behind the techniques | Checking what a technique has actually been shown to do |
| `starter/validation/` | Measured results for setup and permissions | Diagnosing setup on a new host |

Read the guide for the task at hand. Research and validation records are the
evidence trail. Open them when a guide's claim matters to the work.

## Using the starter

- [Set up manually or recover a first run](starter/setup.md).
- [Build binaries and launch with verified firmware](starter/toolchain.md).
- [Move the instrumented XRoar's patch to a new XRoar release](starter/xroar-patch.md).
- [Establish a target and check CoCo behavior](starter/development.md).
- [Work on host scripts and prepare the full starter suite](starter/python.md).
- [Find source pages and inspect diagrams](starter/references.md).
- [Choose extracted text or page images](starter/conversion-quality.md).
- [Work in a lab: answer a technical question, then codify it](starter/lab.md).

## Game and demo techniques

Start with the [technique index](techniques/README.md). It maps the effect the
owner wants to a guide and states the current evidence for each.

## Technique research

Use these records to trace examined sources, adaptations, rejected matches and
unresolved questions. A source description is not a runtime validation.
For practical implementation advice, start with the [technique guides](techniques/README.md).

- [Research for games and demos](techniques/research/README.md).
- [Rendering sources examined](techniques/research/rendering-sources.md).
- [CoCo keyboard and shared input hardware](techniques/research/input-hardware.md).
- [Tile-map rendering and collision research](techniques/research/tile-map.md).
- [Legacy CoCo maze and tile research](techniques/research/legacy-tile.md).
- [Follow-up search for a legacy bitmap tile renderer](techniques/research/tile-source-followup.md).
- [CoCo 3 demos: update less memory and separate colour from geometry](techniques/research/coco3-game-source.md).
- [Later community sources for asset preparation](techniques/research/community-game.md).
- [Color Computer Magazine game-loop research](techniques/research/color-computer-magazine.md).
- [Hot CoCo game techniques](techniques/research/hot-coco-game.md).
- [Undercolor techniques for game state, input and small updates](techniques/research/undercolor-game.md).

## Validation records

Use these reports to inspect recorded commands, targets, expectations, failure
controls and limitations. They record earlier measurements, not a fresh check
of your environment. The index under [experiments](../experiments/README.md)
lists the reproduction code. Example-specific checks are also in the
[example READMEs](../examples/README.md).

### Starter setup and permissions

- [Apple Silicon current-host onboarding audit](starter/validation/macos-onboarding.md).
- [Ubuntu onboarding validation](starter/validation/linux-onboarding.md).
- [Sudo policy validation](starter/validation/sudo-policy.md).

### Controls, state and assets

- [Collection-game keyboard, renderer and PCM journey](techniques/validation/collect-room-output.md).
- [Controls and collision policy validation](techniques/validation/controls-collision.md).
- [Keyboard matrix to movement and action](techniques/validation/keyboard-controls.md).
- [Host validation of scheduled journeys and menu transitions](techniques/validation/game-state.md).
- [CoCo 3 bounded game-state validation](techniques/validation/game-state-coco3.md).
- [Original host asset preparation validation](techniques/validation/assets.md).
- [Prepared RG6 asset loading validation](techniques/validation/asset-loading.md).

Keep these kinds of evidence distinct:

- assembly
- emulator state
- software-renderer output
- host playback
- listening
- physical hardware

A report supports only the boundary and target that it measured.
