# Reproduce a bounded investigation

Use this directory to inspect a hypothesis, reproduce a measurement, or test an
adaptation. For a complete playable game, use
[collect-room](../examples/collect-room/README.md). For smaller programs, use
[examples](../examples/README.md); some earlier research probes remain there.
For implementation advice, use the [technique guides](../guides/README.md).

## Choose an investigation

Read the report for its evidence boundary, then follow its reproduction
instructions. Where a package has no README, the report supplies that procedure.
The links below describe existing work; they do not claim a new validation run.

| Task | Code and procedure | Validation report |
| --- | --- | --- |
| Check a collection-game output journey | [collect-room-output](collect-room-output/README.md) | [Evidence and limits](../guidance/collect-room-output-validation.md) |
| Pack original artwork | [assets](assets/README.md) | [Evidence and limits](../guidance/asset-validation.md) |
| Consume prepared artwork on CoCo 1/2 | [asset-loading](asset-loading/README.md) | [Evidence and limits](../guidance/asset-loading-validation.md) |
| Check logical controls and collisions | [controls-collision](controls-collision/) | [Evidence and limits](../guidance/controls-collision-validation.md) |
| Exercise the keyboard matrix path | [keyboard-controls](keyboard-controls/) | [Evidence and limits](../guidance/keyboard-controls-validation.md) |
| Model turns and menu transitions on the host | [game-state](game-state/README.md) | [Evidence and limits](../guidance/game-state-validation.md) |
| Check a bounded CoCo 3 state subset | [game-state-coco3](game-state-coco3/README.md) | [Evidence and limits](../guidance/game-state-coco3-validation.md) |
| Compare selective and full redraw RAM | [selective-redraw](selective-redraw/README.md) | [Evidence and limits](../guidance/selective-redraw-validation.md) |
| Capture static CoCo 1 software-renderer output | [display-validation](display-validation/README.md) | [Evidence and limits](../guidance/display-validation.md) |
| Capture static non-T1 CoCo 2 output | [display-coco2](display-coco2/README.md) | [Evidence and limits](../guidance/display-coco2-validation.md) |
| Measure consecutive animation frames | [animation-cadence](animation-cadence/README.md) | [Evidence and limits](../guidance/animation-cadence-validation.md) |
| Check CoCo 1/2 hidden-buffer publication | [clean-animation](clean-animation/README.md) | [Evidence and limits](../guidance/clean-animation-validation.md) |
| Check native CoCo 3 hidden-buffer publication | [clean-animation-coco3](clean-animation-coco3/README.md) | [Evidence and limits](../guidance/clean-animation-coco3-validation.md) |
| Measure modeled DAC write intervals | [audio-timing](audio-timing/) | [Evidence and limits](../guidance/audio-timing-validation.md) |
| Check CoCo 2 sound scheduling | [sound-coco2](sound-coco2/README.md) | [Evidence and limits](../guidance/sound-coco2-validation.md) |
| Capture XRoar mixer PCM | [audio-output](audio-output/README.md) | [Evidence and limits](../guidance/audio-output-validation.md) |
| Check current-host macOS recovery | [macos-onboarding](macos-onboarding/) | [Evidence and limits](../guidance/macos-onboarding-validation.md) |
| Reproduce nonroot Ubuntu onboarding | [linux-onboarding](linux-onboarding/README.md) | [Evidence and limits](../guidance/linux-onboarding-validation.md) |
| Check sudo failure and recovery | [sudo-policy](sudo-policy/README.md) | [Evidence and limits](../guidance/sudo-policy-validation.md) |

## Choose the right test suite

Use the [validation command](../guidance/python.md#repository-validation-cli)
to list scopes and run selected suites separately. `root --heavy` runs the full
starter suite; named experiments retain their own coverage and prerequisites.

The root [pytest configuration](../pyproject.toml) selects `scripts/` and
co-located `*_spec.py` files. A root `uv run pytest --cov` checks starter scripts
and their integrations. It does not automatically collect `experiments/`.
Prepare the [complete starter validation environment](../guidance/python.md#complete-starter-validation-environment)
before that full run; selected-target setup alone is insufficient.

Experiment suites require an explicit path, such as
`uv run pytest experiments/game-state`. Use the package's documented command
for coverage, environment variables and preparation. Its scoped coverage
configuration measures that package, not the entire starter or assembly code.
Some suites need verified firmware, native tools, a private instrumented XRoar
build or Docker. Host-only models have narrower requirements.

A passing root suite does not replace experiment checks. A passing experiment
does not replace root integration checks. Report what ran, skipped or failed,
and keep the tested target and observation boundary attached to every result.
Independent expected outcomes and negative controls belong in the reproduction
procedure, not just a count of passing tests.

## Keep evidence reproducible

Keep original harnesses, specifications and instructions tracked. Keep downloaded
sources, ROMs, captures, binaries and generated reports in the ignored locations
named by each procedure, usually `local/` or `build/`. Do not reuse a pytest
temporary directory for evidence that must survive a rerun.

Emulator memory, software-renderer captures and mixer PCM are different
observations. None alone proves GUI interaction, audible host playback or a
physical CoCo run. Read the linked reports before transferring a result to a
new configuration. See [PLAN.md](../PLAN.md) for outstanding work.
