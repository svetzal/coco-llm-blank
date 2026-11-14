# Guidance by task and audience

For a first project, start with the [beginner README](../README.md).
Agents start with [AGENTS.md](../AGENTS.md). Builders can choose a
[technique](../guides/README.md) or [example](../examples/README.md).
This index separates instructions, source research and measured evidence without
moving their files. [PLAN.md](../PLAN.md) holds outstanding work.

## Operational guidance

Read the instructions for the task at hand:

- [Set up manually or recover a first run](setup.md).
- [Build binaries and launch with verified firmware](toolchain.md).
- [Establish a target and verify CoCo behavior](development.md).
- [Work on host scripts and prepare the full starter suite](python.md).
- [Find source pages and inspect diagrams](references.md).
- [Choose extracted text or page images](conversion-quality.md).

## Source research

Use these records to trace examined sources, adaptations, rejected matches and
unresolved questions. A source description is not a runtime validation.
For practical implementation advice, start with the [technique guides](../guides/README.md).

- [Research for games and demos](game-research.md).
- [Rendering sources examined](rendering-sources.md).
- [Publish a completed hidden frame](frame-publication-research.md).
- [Sound while a game runs](sound-research.md).
- [CoCo keyboard and shared input hardware](input-hardware-research.md).
- [Tile-map rendering and collision research](tile-map-research.md).
- [Legacy CoCo maze and tile research](legacy-tile-research.md).
- [Follow-up search for a legacy bitmap tile renderer](tile-source-followup.md).
- [CoCo 3 demos: update less memory and separate colour from geometry](coco3-game-source-research.md).
- [Later community sources for asset preparation](community-game-research.md).
- [Color Computer Magazine game-loop research](color-computer-magazine-research.md).
- [Hot CoCo game techniques](hot-coco-game-research.md).
- [Undercolor techniques for game state, input and small updates](undercolor-game-research.md).

## Validation reports

Use these reports to inspect recorded commands, targets, expectations, failure
controls and limitations. They record earlier measurements, not a fresh check
of your environment. Reproduction code is indexed under
[experiments](../experiments/README.md); example-specific checks also live in
[example READMEs](../examples/README.md).

### Setup and permissions

- [Ubuntu onboarding validation](linux-onboarding-validation.md).
- [Sudo policy validation](sudo-policy-validation.md).

### Display and animation

- [Validate the rendered display](display-validation.md).
- [Validate static CoCo 2 display output](display-coco2-validation.md).
- [Measure continuous animation](animation-cadence-validation.md).
- [Hidden drawing and field-boundary publication](clean-animation-validation.md).
- [Native CoCo 3 hidden-buffer publication](clean-animation-coco3-validation.md).
- [Selective-redraw RAM validation](selective-redraw-validation.md).

### Controls, state and assets

- [Controls and collision policy validation](controls-collision-validation.md).
- [Keyboard matrix to movement and action](keyboard-controls-validation.md).
- [Host validation of scheduled journeys and menu transitions](game-state-validation.md).
- [CoCo 3 bounded game-state validation](game-state-coco3-validation.md).
- [Original host asset preparation validation](asset-validation.md).
- [Prepared RG6 asset loading validation](asset-loading-validation.md).

### Sound

- [Measure intervals between DAC writes](audio-timing-validation.md).
- [CoCo 2 cooperative sound, input and drawing](sound-coco2-validation.md).
- [Validate modeled audio output](audio-output-validation.md).

Keep assembly, emulator state, software-renderer output, host playback,
listening and physical-hardware evidence distinct. A report supports only the
boundary and target it actually measured.
