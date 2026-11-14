# Active plan

Keep this file limited to open work. Remove each item when its acceptance
criteria are met and its report is available; keep evidence in the relevant
guide or validation record. The items below are open; they are not currently
dispatched.

## Continue from here

Read [AGENTS.md](AGENTS.md), then choose one open item below. Use the
[guidance index](guidance/README.md) for the current guides.

Preserve ignored `local/`, `build/` and the prepared `.venv`. Do not treat a previous report as a new validation run. The repository
is public, uses `main`, and remains unregistered with Foundry. Leave the separate
`coco-lines` project and its processes untouched. Start no new beginner-agent
trial without a new request; the completed Claude 03 assessment is under
`/Users/svetzal/Work/Experiments/coco-starter-onboarding/claude-03-evaluation.json`.

## Open work

- Close the labs that were never closed. `experiments/`,
  `guidance/techniques/research/` and both `validation/` folders are leftover
  lab material from before [the lab workflow](guidance/starter/lab.md). Close
  them as that workflow describes, in order:
  1. Lab equipment: move the experiments' screen capture, scripted keyboard
     input and sound capture into `scripts/coco.py`, built on one shared
     instrumented XRoar. BUILD projects use the same abilities in `check`.
  2. One topic at a time (animation, display, sound, controls, game state,
     assets, tiles, setup): codify what its experiments, research notes and
     validation reports established into the technique guide and examples,
     moving useful assembly programs into `examples/`. Then delete that
     topic's leftover files. Setup checks become `scripts/` tests.
  3. Add a size check to CI so growth is a deliberate decision.
- Clean Apple Silicon host and native Linux desktop onboarding, including
  x86-64 Linux. Intel Mac support is excluded. Current container and configured
  host results do not establish these journeys.
- Disk-tool installation and Linux distribution coverage beyond the tested
  Ubuntu setup.
- Target-specific reference groups and further difficult-page conversion checks.
  Existing page samples do not establish whole-book OCR quality.
- Technique-driven source and errata reading, especially scrolling and broader
  sound/input integration. Continue only against a concrete builder need;
  the stopped historical tile-ID hunt is not reopened.
- Host keyboard delivery, window presentation, listening, and physical-machine
  validation where required by a guide's claim. Emulator-only checks must keep
  their stated limits.

The historical tile-source hunt remains stopped unless a substantive new lead
meets its documented boundary. Intel Mac support is excluded.

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
