# Active plan

Keep this file limited to open work. Remove each item when its acceptance
criteria are met. Keep its evidence in the relevant guide or example. The items
below are open. Nobody is working on them now.

## Continue from here

Read [AGENTS.md](AGENTS.md), then choose one open item below. Use the
[guidance index](guidance/README.md) for the current guides.

Preserve ignored `local/`, `build/` and the prepared `.venv`. Do not treat a
previous report as a new validation run.

The repository is public, uses `main`, and remains unregistered with Foundry.
Leave the separate `coco-lines` project and its processes untouched. Start no new beginner-agent
trial without a new request.

## Open work

- Finish closing the old labs. Every topic is closed. Two items remain:
  1. Delete `experiments/README.md`. Decide whether
     `scripts/validate_repository.py` still earns its place now that it has
     only the root scope.
  2. Add a size check to CI so growth is a deliberate decision.
- Remove the over-testing from the examples. Most examples have a
  `*_spec.py` that tests the example's `expected.py` or `scripts/coco.py`, not
  the program. The oracle in `expected.py` and `coco.py check` are the test of
  an example. For each example:
  1. Delete the spec, as for first-screen.
  2. Move any test of the tool into `scripts/coco_spec.py`.
  3. Keep a negative control only where the check would otherwise pass a
     wrong result. Put it in `scripts/coco_spec.py`, as for the wrong-SAM
     control. Palette-swatches' orientation controls are the first case to
     decide.
  4. Update the guidance that tells agents to write a model spec:
     [development practice](guidance/starter/development.md) and the
     [examples index](examples/README.md).
- Clean Apple Silicon host and native Linux desktop onboarding, including
  x86-64 Linux. Current container and configured host results do not
  establish these journeys.
- Disk-tool installation and Linux distribution coverage beyond the tested
  Ubuntu setup.
- Target-specific reference groups and further difficult-page conversion checks.
  Existing page samples do not establish whole-book OCR quality.
- Technique-driven source and errata reading, especially scrolling and broader
  sound/input integration. Continue only against a concrete builder need.
- Make the instrumented XRoar's patch series acceptable to XRoar upstream, as
  [Toward upstream](guidance/starter/xroar-patch.md#toward-upstream) lists:
  XRoar-native trap actions and an audio module instead of environment
  variables, Dragon and MC-10 coverage where cheap, XRoar's code style and
  licence headers, and Texinfo documentation. Keep it current with
  [the XRoar patch procedure](guidance/starter/xroar-patch.md). Submit nothing
  and contact no one until the owner asks.
- Host keyboard delivery, window presentation, listening, and physical-machine
  validation where required by a guide's claim. Emulator-only checks must keep
  their stated limits.

Out of scope: Intel Mac support. The historical tile-ID hunt stays stopped
unless a new lead meets the boundary in the
[tile-map guide](guidance/techniques/tile-maps.md#open-questions).

## Guide contract

A technique guide tells an agent how to achieve an effect on the CoCo. Keep it
in ordinary Markdown in `guidance/techniques/`, under about 200 lines. Each
guide states:

- The task, the machines and configurations it applies to, and their limits.
- Practical steps, memory and timing tradeoffs, and likely failure cases.
- Inline citations beside sourced claims: author, title, edition or issue,
  PDF page (printed page when known) and resource ID. Cite only read passages;
  inspect diagrams and listings as images when conversion is uncertain.
- Which claims are published explanations, our adaptations, derived
  calculations, measured results or untested proposals.
- The example that demonstrates it, and what that example's check proves.
- Unresolved conflicts and the evidence that would settle them.

Credit examined authors without claiming they invented a technique. Keep
copyrighted source content in ignored storage; publish original explanations
and source metadata only.
