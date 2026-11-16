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

- Clean Apple Silicon host and native Linux desktop onboarding, including
  x86-64 Linux. Current container and configured host results do not
  establish these journeys.
- ToolShed installation on a clean Ubuntu 24.04 host, and Linux distribution
  coverage beyond the tested Ubuntu setup. The ToolShed source build has run
  only on Apple Silicon macOS.
- Target-specific reference groups and further difficult-page conversion checks.
  Existing page samples do not establish whole-book OCR quality.
- Technique-driven source and errata reading, especially scrolling and broader
  sound/input integration. Continue only against a concrete builder need.
- Make the instrumented XRoar's patch series acceptable to XRoar upstream.
  [Toward upstream](guidance/starter/xroar-patch.md#toward-upstream) lists
  the work:
  - XRoar-native trap actions and an audio module instead of environment
    variables
  - Dragon and MC-10 coverage where cheap
  - XRoar's code style and licence headers
  - Texinfo documentation

  Keep it current with
  [the XRoar patch procedure](guidance/starter/xroar-patch.md). Submit nothing
  and contact no one until the owner asks.
- Bring the measured claims that cite a closed lab under the
  [evidence rules](guidance/starter/references.md#cite-each-kind-of-evidence).
  The animation and controls-and-collision guides each have one result that
  is "not rerun". Give each one a check, a method to repeat it, or an
  entry in the open questions. Do the same for the CoCo 3 examples: label the
  facts that only their checks establish.
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
  PDF page (printed page when known) and resource ID. For a page at a URL,
  give the author, title, date, URL and date read. Add a Wayback Machine link
  when one exists. Cite only read passages.
  Inspect diagrams and listings as images when conversion is uncertain.
- Which claims are published explanations, our adaptations, derived
  calculations, measured results or untested proposals.
- For each measured result, the check that reruns it. If no check can, the
  method to repeat it.
- The example that shows it, and what that example's check proves.
- Unresolved conflicts and the evidence that would settle them.

Credit examined authors without claiming they invented a technique. Keep
copyrighted source content in ignored storage. Publish original explanations
and source metadata only.
