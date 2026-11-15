# Reproduce a bounded investigation

Use this directory to inspect a hypothesis, reproduce a measurement, or test an
adaptation. For a complete playable game, use
[collect-room](../examples/collect-room/README.md). For smaller programs, use
[examples](../examples/README.md); some earlier research probes remain there.
For implementation advice, use the [technique guides](../guidance/techniques/README.md).

## Choose an investigation

No investigation remains here. The setup checks are now root specifications
in `scripts/`. The [toolchain guide](../guidance/starter/toolchain.md#measured-setup-results)
records the measured setup results.

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
`uv run pytest experiments/<name>`. Use the package's documented command
for coverage, environment variables and preparation. Its scoped coverage
configuration measures that package, not the entire starter or assembly code.
Some suites need verified firmware, native tools or Docker. Host-only models have narrower requirements.

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
