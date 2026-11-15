# Reproduce a bounded investigation

Use this directory to inspect a hypothesis, reproduce a measurement, or test an
adaptation. For a complete playable game, use
[collect-room](../examples/collect-room/README.md). For smaller programs, use
[examples](../examples/README.md); some earlier research probes remain there.
For implementation advice, use the [technique guides](../guidance/techniques/README.md).

## Choose an investigation

Read the report for its evidence boundary, then follow its reproduction
instructions. Where a package has no README, the report supplies that procedure.
The links below describe existing work; they do not claim a new validation run.

| Task | Code and procedure | Validation report |
| --- | --- | --- |
| Play the collection game with injected keys | [collect-room-journey](collect-room-journey/README.md) | [Collect room evidence](../examples/collect-room/README.md) |
| Check a collection-game output journey | [collect-room-output](collect-room-output/README.md) | [Evidence and limits](../guidance/techniques/validation/collect-room-output.md) |
| Pack original artwork | [assets](assets/README.md) | [Evidence and limits](../guidance/techniques/validation/assets.md) |
| Consume prepared artwork on CoCo 1/2 | [asset-loading](asset-loading/README.md) | [Evidence and limits](../guidance/techniques/validation/asset-loading.md) |
| Check logical controls and collisions | [controls-collision](controls-collision/) | [Evidence and limits](../guidance/techniques/validation/controls-collision.md) |
| Exercise the keyboard matrix path | [keyboard-controls](keyboard-controls/) | [Evidence and limits](../guidance/techniques/validation/keyboard-controls.md) |
| Model turns and menu transitions on the host | [game-state](game-state/README.md) | [Evidence and limits](../guidance/techniques/validation/game-state.md) |
| Check a bounded CoCo 3 state subset | [game-state-coco3](game-state-coco3/README.md) | [Evidence and limits](../guidance/techniques/validation/game-state-coco3.md) |
| Check current-host macOS recovery | [macos-onboarding](macos-onboarding/) | [Evidence and limits](../guidance/starter/validation/macos-onboarding.md) |
| Reproduce nonroot Ubuntu onboarding | [linux-onboarding](linux-onboarding/README.md) | [Evidence and limits](../guidance/starter/validation/linux-onboarding.md) |
| Check sudo failure and recovery | [sudo-policy](sudo-policy/README.md) | [Evidence and limits](../guidance/starter/validation/sudo-policy.md) |

## Choose the right test suite

Use the [validation command](../guidance/starter/python.md#repository-validation-cli)
to list scopes and run selected suites separately. `root --heavy` runs the full
starter suite; named experiments retain their own coverage and prerequisites.

The root [pytest configuration](../pyproject.toml) selects `scripts/`,
`examples/` and their co-located `*_spec.py` files. A root
`uv run pytest --cov` checks starter scripts, the example models and their
integrations. It does not automatically collect `experiments/`.
Prepare the [complete starter validation environment](../guidance/starter/python.md#complete-starter-validation-environment)
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
