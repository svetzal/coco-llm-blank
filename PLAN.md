# Active plan

Keep this file limited to open work. Remove each item when its acceptance
criteria are met and its report is available; keep evidence in the relevant
guide or validation record. The items below are dispatched, not confirmed
complete. Dependencies describe integration order, not additional tasks.

## Current batch

1. **Unified experiment checks.** Provide a documented way to run the existing
   experiment checks with explicit prerequisites and bounded evidence scopes.
   Acceptance: exercise the real check entry points, demonstrate that a failing
   check produces a failure, and expose missing prerequisites or skipped checks
   without presenting them as passes. Preserve independent expectations and
   negative controls. Final integration depends on the collection-game check
   interface and the documented host support boundary.
2. **Integrated collection-game renderer and audio.** Validate the existing
   [collection game](examples/collect-room/README.md) through renderer output
   and digital audio during the same bounded game journeys. Acceptance: name
   the tested machine profiles, verify expected scenes and sound events against
   independent expectations, and show controls that reject incorrect output.
   Report RAM, rendered frames, timing and mixer PCM separately. Do not infer
   host listening, UI interaction or physical-hardware results. Document the
   runnable checks for inclusion in the unified experiment checks.
3. **Full restricted-sudo recovery.** Extend the
   [sudo-policy validation](guidance/sudo-policy-validation.md) beyond
   prerequisite-only recovery. Acceptance: record the initial restriction and
   actionable failure, then complete bootstrap and an existing target execution
   check after the permitted recovery; verify reruns preserve edited project
   notes. Record the exact host/container and privilege conditions. Container
   evidence does not establish native desktop or GUI onboarding.
4. **Apple Silicon onboarding audit.** Distinguish checks in an isolated
   workspace on this configured Mac from evidence on a clean host. Record
   actual first-run and recovery behavior without claiming clean-host proof
   unless that environment was tested.

Finish integration after the worker reports arrive: reconcile changed
interfaces, run the applicable combined checks, and record actual results and
remaining limitations in the relevant records. The existing 274-test result
with 95.06% coverage is prior evidence, not an outstanding task or proof of
this batch. Remove accepted items rather than adding completed status sections.

The historical tile-source hunt is stopped; no further search is queued.
Keep downloads and generated evidence ignored. Do not modify `coco-lines`,
start new beginner trials, or register Foundry for this batch.

## Open work beyond this batch

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

## Permanent technique guides

This anchor remains the guide contract until it is relocated and its callers
are updated. Use the [technique index](guides/README.md) to find a guide.
Research notes preserve source selection and uncertainty; guides explain how
to apply findings; original examples supply bounded implementation evidence.
A source list alone does not complete a research pass.

Keep task-focused guides under `guides/` in ordinary Markdown. Each needs:

- The task, applicable machines and configuration limits.
- Practical steps, memory or timing tradeoffs, and likely failure cases.
- Citations beside sourced claims: author, title, edition or issue, exact PDF
  pages, printed pages when known, archive URL and resource ID.
- Separate attribution for published explanations, our adaptations, derived
  calculations, measured results and untested proposals.
- Links to original examples and checks where implementation evidence exists.
- Unresolved conflicts and the evidence needed to settle them.

Credit examined authors without claiming they invented a technique. Cite only
read passages, including necessary continuations; inspect diagrams and listings
as images when conversion is uncertain. Keep copyrighted source content in
ignored storage and publish original explanations and source metadata.

Examined techniques may precede reproduction if procedures remain labelled
proposals. Only measured claims gain tested status. Keep assembly, execution,
framebuffer, rendered display, timing, audible output and physical-hardware
results separate; test every claimed target. Require independent expectations
and meaningful failure controls. Update the relevant guide and navigation,
check citations and runnable commands, and rerun affected checks before
calling a pass complete.
