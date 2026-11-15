# Work in a lab

Read this when a session switches to LAB mode. A lab answers one technical
question that the guides and examples do not settle yet: crackly audio, slow
graphics, unreliable input, a mode nobody has tried. It ends by improving the
starter's guides, examples or tools, and then it is removed.

## Open a lab

Open a lab only when the owner asks for one, or after they agree to your
suggestion. Suggest one when a BUILD problem is not answered by the
[technique guides](../techniques/README.md) or examples, explaining in plain
words what you would investigate and why.

1. Name the lab after the problem in a few lowercase words joined by hyphens,
   such as `crackly-audio`.
2. Create `local/lab/<topic>/LAB.md` holding:
   - the question, in one sentence;
   - where it came from: the project and the symptom the owner saw, if any;
   - what a finished answer looks like, so you know when to stop;
   - the target machines the answer must cover.
3. If a project raised the question, add an `Open lab: <topic>` line to its
   `README.md`, so a later session knows to resume the lab.
4. Tell the owner the session is now in LAB mode, and what the question is.

`local/` is ignored, so nothing in the lab is committed. Lab folders survive
between sessions until closed.

## Explore

- Read primary sources with the [reference lookup](references.md) procedure.
  Note each fact with its title and PDF page in `LAB.md`.
- Test ideas as small experiments: a folder in the lab with `main.asm`,
  `coco.toml` and, where it helps, `expected.py`, run with `scripts/coco.py`.
  Keep each experiment small enough to answer one sub-question.
- Log every experiment in `LAB.md`: what was tried, the command, the result and
  what it showed. Failed attempts are findings; keep them in the log.
- `scripts/coco.py` already presses scripted keys and captures XRoar's rendered
  screen and mixer sound ([evidence methods](development.md#check-the-feature-you-claim)).
  If an experiment needs equipment it lacks, building that ability is part of
  the lab. Add it to `coco.py` with tests, not as a script in the lab; an
  emulator hook goes in the [instrumented XRoar](toolchain.md#instrumented-xroar)
  patch series.

Keep the evidence honest: separate source statements, deductions and measured
results, keep expectations independent of the implementation, include a
failure control, and report memory, rendered display, sound and physical
hardware as separate evidence.

## Converge

Stop exploring when `LAB.md` can state the answer in a few sentences, with the
evidence behind it and its limits. If the answer is "it depends", state what it
depends on. Check it on every target named when the lab opened.

## Codify the answer

Turn the answer into lasting, committed changes:

- Update the technique guide that covers it, or add one if none does, following
  the [guide contract](../../PLAN.md#guide-contract). Cite sources inline.
- Add or update an example in `examples/<name>/` when code demonstrates the
  answer better than prose. Its `coco.py check` is the reproducible evidence.
- Commit any new `coco.py` ability with its tests.

Do not commit lab notes, experiment folders, logs or captures. A result that
cannot be rerun cheaply gets one paragraph in its guide summarising what was
measured and its limits.

## Close the lab

1. Delete `local/lab/<topic>/`.
2. Remove the `Open lab` line from the project's `README.md`.
3. Tell the owner, in plain words, what was found and what changed in the
   guides, examples or tools.
4. Return to BUILD mode on the project that raised the question, and apply the
   answer there.

If the lab ends without an answer, still close it. Add one short paragraph to
the relevant guide naming the open question, what was tried, and what evidence
would settle it, so the next lab starts from there.
