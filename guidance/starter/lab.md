# Work in a lab

Read this when a session switches to LAB mode. A lab answers one technical
question that the guides and examples do not settle yet. Examples are crackly
audio, slow graphics, unreliable input, a mode nobody has tried. A lab ends by
improving the starter's guides, examples or tools. Then you remove the lab.

## Open a lab

Open a lab only when the owner asks for one, or after they agree to your
suggestion. Suggest a lab when the
[technique guides](../techniques/README.md) or examples do not answer a BUILD
problem. Explain in plain words what you would investigate and why.

1. Name the lab after the problem in a few lowercase words joined by hyphens,
   such as `crackly-audio`.
2. Create `local/lab/<topic>/LAB.md`. Put these items in it:
   - The question, in one sentence.
   - Where the question came from: the project and the symptom the owner saw,
     if any.
   - What a finished answer looks like, so you know when to stop.
   - The target machines the answer must cover.
3. If a project raised the question, add an `Open lab: <topic>` line to its
   `README.md`. That line tells a later session to resume the lab.
4. Tell the owner that the session is now in LAB mode. Tell them the question.

`local/` is ignored, so nothing in the lab is committed. Lab folders survive
between sessions until the lab is closed.

## Explore

- Read primary sources with the [reference lookup](references.md) procedure.
  Write each fact in `LAB.md` with its citation: the title and PDF page, or
  the author, title, date and URL.
- Test ideas as small experiments. An experiment is a folder in the lab with
  `main.asm`, `coco.toml` and, where it helps, `expected.py`. Run it with
  `scripts/coco.py`. Keep each experiment small enough to answer one
  sub-question.
- Log every experiment in `LAB.md`: what you tried, the command, the result and
  what the result showed. Failed experiments are findings. Keep them in the log.
- `scripts/coco.py` already presses scripted keys and captures XRoar's rendered
  screen and mixer sound ([evidence methods](development.md#check-the-feature-you-claim)).
  If an experiment needs equipment it lacks, building that ability is part of
  the lab. Add the ability to `coco.py` with tests. Do not add it as a script
  in the lab. Put an emulator hook in the patch series of the
  [instrumented XRoar](toolchain.md#instrumented-xroar).

Keep the evidence honest:

- Separate source statements, deductions and measured results.
- Keep expectations independent of the implementation.
- Include a failure control.
- Report memory, rendered display, sound and physical hardware as separate
  evidence.

## Converge

Stop exploring when `LAB.md` can state the answer in a few sentences. The
statement must include the evidence behind the answer and its limits. If the
answer is "it depends", state what it depends on. Check the answer on every
target named when the lab opened.

## Codify the answer

Turn the answer into lasting, committed changes:

- Update the technique guide that covers the answer, or add a guide if none
  does. Obey the [guide contract](../../PLAN.md#guide-contract). Cite sources
  inline.
- Add or update an example in `examples/<name>/` when code shows the answer
  better than prose. Its `coco.py check` is the reproducible evidence.
- Commit any new `coco.py` ability with its tests.

Do not commit lab notes, experiment folders, logs or captures. You delete the
lab folder, so nothing that you commit can cite it.

A finding that the lab measured must leave a check that reruns. That check is
an example's `coco.py check` or a control in `scripts/coco_spec.py`. Cite the
check in the guide, as
[reference lookup](references.md#cite-each-kind-of-evidence) describes.

Some results cannot be a check, such as a listening test. Then give the result
one paragraph in its guide. Write the method so that a person can repeat it,
what was measured, and its limits. If you can do neither, record the finding
as an open question, not as a fact.

## Close the lab

1. Delete `local/lab/<topic>/`.
2. Remove the `Open lab` line from the project's `README.md`.
3. Tell the owner, in plain words, what was found and what changed in the
   guides, examples or tools.
4. Return to BUILD mode on the project that raised the question. Apply the
   answer there.

If the lab ends without an answer, still close it. Add one short paragraph to
the relevant guide. In it, name the open question, what was tried, and what
evidence would settle the question. The next lab then starts from there.
