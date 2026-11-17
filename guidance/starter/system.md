# Work on the starter

Read this when a session switches to SYSTEM mode. SYSTEM mode changes the
starter itself: its tools, its emulator build, its guides about the starter,
and the agent entry point. It does not answer questions about CoCo
programming. A [lab](lab.md) does that.

## Start SYSTEM mode

Start SYSTEM mode only when the owner asks for it by name, for example "system
mode" or "start SYSTEM". Do not offer SYSTEM mode, and do not start it on your
own.

A change to the starter stays in the owner's copy. It can make that copy
different from the published starter. Thus the owner must make the decision.

When BUILD or LAB work finds a limit in the starter, do these steps:

1. Explain the limit to the owner in plain words. Do not name SYSTEM mode.
2. Continue with what the existing tools can do. If the tools cannot give the
   evidence, report that the evidence is missing. Do not make a tool in the
   project or in the lab as a substitute.

When SYSTEM mode starts, tell the owner the topic in one sentence.

## What SYSTEM mode changes

| Area | Examples |
| --- | --- |
| `scripts/` | A new `coco.py` command, a bug fix, a new check in a spec |
| The instrumented XRoar | A new XRoar release, a new patch in `scripts/xroar_patches/` |
| Starter guides | `AGENTS.md`, `README.md`, `PLAN.md`, `template/`, files in `guidance/starter/` |
| Dependencies | `pyproject.toml`, `uv.lock`, native tools |

SYSTEM mode never changes a folder in `projects/`. These folders belong to the
owner. Technique guides and examples change in LAB mode.

## Do the work

- Read the guide for the area first: [toolchain](toolchain.md),
  [Python tools](python.md) or [the XRoar patch](xroar-patch.md).
- Put an ability that an experiment needs into `scripts/coco.py`, with its
  tests. Put an emulator hook in the patch series of the
  [instrumented XRoar](toolchain.md#instrumented-xroar).
- Before you change the XRoar patch series or the XRoar pin, run the
  equivalence trial. Every capture must be identical, or each difference must
  have an explanation.
- Keep `AGENTS.md` short. It is a router to guides. Put task instructions in
  the guide for that task. Link to the guide, and tell when to read it.
- Write prose with the `simplified-technical-english` skill. Run its checker
  on each changed file.
- A limit, a new dependency or new equipment is a decision for the owner. Ask
  before you add one.

Put temporary files in ignored `local/system/<topic>/`. A small change needs no
folder. The XRoar trial makes `local/system/xroar-<version>/` with its own
`NOTES.md`.

## Finish

1. Run the full suite: `uv run pytest --cov`. Every test must pass.
2. Add the changes to `CHANGELOG.md` under a new section,
   `## [x.y.z] - YYYY-MM-DD`. Write for a person who uses the starter: what
   they can do now, and what they must do differently. Use the headings
   Added, Changed, Fixed and Removed.
3. Choose the new version. Before 1.0.0, increase the second number for a new
   ability or a change that a project or a person must adapt to. Increase the
   third number for a fix or a change to the guides only.
4. Set the version in `pyproject.toml`. Then run `uv lock` and
   `uv run python scripts/release.py check`.
5. Commit the scoped paths on `main`, and push.
6. Tag the commit and publish the release:

   ```sh
   git tag -a v<x.y.z> -m "retro-explorer-coco <x.y.z>"
   git push origin v<x.y.z>
   uv run python scripts/release.py notes > local/system/notes.md
   gh release create v<x.y.z> --title "<x.y.z>" --notes-file local/system/notes.md
   ```

7. Delete `local/system/<topic>/` and `local/system/notes.md`.
8. Tell the owner, in plain words, what changed, the new version and what to
   decide next.
9. Return to the mode that the session came from.

A copy of the starter with no remote of its own keeps steps 1 to 4 and the
commit. It does not push, tag or publish.
