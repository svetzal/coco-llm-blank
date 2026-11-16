# Maintain the XRoar patch

Read this guide when XRoar publishes a release, and before you change the
capture equipment in the [instrumented XRoar](toolchain.md#instrumented-xroar).
It tells an agent how to move the patch series to a new XRoar release, how to
judge the result, and what to commit.

## What the series is

The instrumented XRoar is the pinned XRoar release with the series in
`scripts/xroar_patches/` applied. Each `.patch` file is one `git format-patch`
commit with a subject and a message. The series adds the equipment as new
source files and changes upstream files only at their call sites.

`scripts/xroar_patches/upstream.json` is the one XRoar pin. It holds these
items:

- The release version, its git tag, and the commit that the tag names.
- The base commit. The series is made against this commit, and its files
  match the release archive. Usually it is the tag's commit.
- The URL and SHA-256 of the release archive.

The build applies the series to the checksum-pinned archive, not to a git
checkout. The archive needs no clone, and it holds the generated `configure`
script. It is also the archive that the Ubuntu install builds.

Each patch names the git blob of every file before and after the change. The
build refuses a file whose bytes do not match.

`scripts/xroar_upstream.py` runs this procedure. Its `--help` shows the
commands and makes no changes. It never commits, pushes or contacts anyone.

## When to run the procedure

- Run `report` at the start of lab work on capture, and when the owner asks
  about XRoar versions.
- Do a trial for each new XRoar release that `report` shows.
- Do a trial on the pinned release before you change the equipment.

```sh
uv run python scripts/xroar_upstream.py report
```

The report shows these items:

- the pin
- the newest git tag
- the newest archive on the download page
- how many releases the pin is behind
- the version of the ordinary XRoar

## Move to a new release

A version bump is a short lab. Obey [the lab guide](lab.md): the trial makes
`local/lab/xroar-<version>/LAB.md`. Log each command, result and decision
there.

1. Get the archive's SHA-256 from a source other than the download. XRoar does
   not publish checksums. The Homebrew formula records one. Run
   `brew info --json=v2 xroar` and read `urls.stable.checksum`. Record the
   source in `LAB.md`.
2. Start the trial:

   ```sh
   uv run python scripts/xroar_upstream.py trial 1.13 --sha256 <sha256>
   ```

3. If the trial stops at a conflict, do the steps in
   [resolve a conflict](#resolve-a-conflict). Then run the same trial command
   again.
4. If the build refuses a file as "not the XRoar source this patch was made
   against", do the steps in [find the base](#find-the-base).
5. If `make` fails, do the steps in [fix a build failure](#fix-a-build-failure).
6. Read the verdict. Do the steps in [judge equivalence](#judge-equivalence).
7. Write the result into the repository:

   ```sh
   uv run python scripts/xroar_upstream.py adopt 1.13 --sha256 <sha256>
   ```

   Add `--accept-differences` only after each difference has an explanation.
8. Rebuild and check the result:

   ```sh
   uv run python scripts/instrumented_xroar.py build
   uv run pytest --cov
   ```

9. Do the steps in [keep the ordinary XRoar consistent](#keep-the-ordinary-xroar-consistent).
10. Commit as [what to commit](#what-to-commit) describes.
11. Close the lab: delete `local/lab/xroar-<version>/`.

The trial clones upstream once into `local/toolchain-sources/xroar.git` and
fetches tags after that. It treats the clone and the archive as untrusted data.
It runs only XRoar's `autoreconf`, `configure` and `make` from them.

The lab clone commits as a neutral identity and turns off your git hooks. Thus
the patches carry only their own messages.

## Resolve a conflict

The trial applies the series to the pinned base. Then it runs
`git rebase --onto <new base> <pinned base>`. A three-way merge is therefore
available for every file, also for files that an earlier patch changed.

1. Read the files that the message names. Run `git status` in the lab clone,
   `local/lab/xroar-<version>/xroar`.
2. Read the upstream change to each file:
   `git log -p <pinned base>..<new base> -- <file>`.
3. Keep the upstream version of the upstream code.
4. Put our call sites back where upstream moved that code.
5. Change the patch message if it no longer describes the patch.
6. Run `git add` for the files. Then run `git rebase --continue`.
7. Run the trial command again without `--fresh`. `--fresh` discards your
   resolution.

## Find the base

A release archive can contain commits made after its tag. Then the archive
does not match the tag, and the build refuses the first patched file that is
different.

1. Unpack the archive into a new folder under the lab.
2. Compare it with the tag: `git archive <tag> | tar -x -C <folder>`, then
   `diff -rq`. The archive alone holds the generated build files.
3. Find the commit whose files match, usually a commit just after the tag.
   Do the comparison again for that commit.
4. In the lab clone, run
   `git rebase --onto <commit> <tag> coco-capture`.
5. Run the trial again with `--base <commit>`.

[The current pin](#the-current-pin) is an example: its base is one commit
after its tag.

## Fix a build failure

1. Read `local/lab/xroar-<version>/build.building/make.log`.
2. Fix the code in the lab clone on branch `coco-capture`.
3. Commit the fix with `git commit --fixup=<commit of the patch it fixes>`.
4. Merge it into that patch with `git rebase --autosquash <base>`.
5. Run the trial again.

Keep one equipment feature in each patch. Put new code in new files, not in
upstream files.

## Judge equivalence

The trial runs each check three times: on the pinned build, on the pinned
build again as a control, and on the trial build.

| Check | What it covers |
| --- | --- |
| `examples/first-screen --video` | CoCo 1, 2, 2B and 3 rendered frames |
| `examples/collect-room` | CoCo 1, 2, 2B and 3 frames and mixer sound, main and key-journey variants |
| `examples/sound-slots` | CoCo 1, 2, 2B and 3 mixer sound, main and square variants |
| `examples/timer-sound --video` | CoCo 3, both GIME revisions, four variants |

It compares every file that each run wrote in `build/<example>/`, byte for
byte. It compares these files:

- RAM snapshots
- Rendered frames
- Sound recordings
- Key scripts
- XRoar logs
- Binaries
- Result records

The comparison ignores the emulator path in a result record.
The files of each run stay in `local/lab/xroar-<version>/captures/`.

- `identical`, exit code 0: adopt the release.
- `different`, exit code 3: every check passed, but some files are different.
  Examine each different file before you adopt.
- `failed`, exit code 1: a check failed or the pinned build did not repeat.
  Do not adopt.

Captures must be identical, unless an upstream change explains a difference.
For each different file, do these steps:

1. Find the kind and size of the difference. Examples are bytes in a RAM
   snapshot or ticks in a log line.
2. Find the upstream change in the ChangeLog and in `git log <old>..<new>`.
3. Prove the cause with a control. Revert that upstream commit in a lab
   branch. Build the series and the revert, run the same checks, and compare
   with the pinned captures.
4. Record the difference, the upstream change and the control result in
   `LAB.md` and in the commit message.

Do not adopt a release if one difference has no explanation. Report what
blocked it, and keep the old pin.

## Keep the ordinary XRoar consistent

The ordinary XRoar runs `build`, `run` and plain `check`. The instrumented
XRoar runs every check that uses frames, sound or keys.

- Ubuntu: `scripts/native.py` builds the ordinary XRoar from the same pin.
  A new install gets the pinned version, and an existing install keeps its
  version. To change it, delete `local/toolchain/bin/xroar` and run
  `uv run python scripts/native.py`.

- macOS: Homebrew supplies the ordinary XRoar, and nothing pins it. Its
  version can be older or newer than the pin. Upgrade it with
  `brew upgrade xroar` only when the owner agrees.

`report` shows the version of the ordinary XRoar and the pin. The two can be
different, because plain checks compare only RAM at checkpoints. A difference
is important only when an upstream change alters behavior that a plain check
measures.

To find out, run the plain checks with `XROAR` set to the trial's executable.
If a plain check gives a different result on two hosts, compare their
`report` output first.

## Change the equipment

1. Run a trial on the pinned release, for example
   `trial 1.13 --base <base commit>`. This makes the lab clone with the
   series as commits.

2. Change the code in `local/lab/xroar-<version>/xroar` on branch
   `coco-capture`. Use the steps in [fix a build failure](#fix-a-build-failure)
   to change a patch.

3. Run the trial again. Every check must pass. A planned change to a capture
   gives the verdict `different`.

4. Adopt with `--accept-differences` only for the changes that you planned.

5. Add the matching `scripts/coco.py` ability and its tests to the same
   commit.

## What to commit

Commit these items together, in one commit:

- Every file in `scripts/xroar_patches/`, which holds the patch files and
  `upstream.json`.
- The update to [the current pin](#the-current-pin) in this guide.
- Changes to `scripts/coco.py`, examples or guides that the new release needs.

In the message, give the release, the base commit, how you resolved each
conflict, the equivalence results, and each difference with its explanation.
Do not commit `local/`. Make changes to `scripts/xroar_upstream.py` and
`scripts/instrumented_xroar.py` in a separate commit before the adoption.

## The current pin

XRoar 1.13: tag commit `af501b71`, base commit `1630182d`. The base is one
commit after the tag, and the release archive matches it. The series has four
patches. Its captures are the reference for the next trial.

## Toward upstream

The series is test equipment for this starter. It is not ready to send to
XRoar. Do not send it, and do not contact the maintainer, unless the owner
asks.

The changes below would make it acceptable. Send each feature as its own
small patch against the newest release.

### Use XRoar's option and module conventions

Replace the environment variables and fixed values with XRoar options:

- Frame dump: a trap action, such as `-trap-screenshot <file>`, next to
  `-trap-snap`. Write PNG with the existing `screenshot_write_png()` where
  libpng is available.

- Sound capture: an audio module, such as `-ao wav`, with the file in
  `-ao-device`. Take the rate, format and channels from `-ao-rate`,
  `-ao-format` and `-ao-channels`.

- Key presses: trap actions, such as `-trap-press` and `-trap-release`, or a
  key script for each trap. Use the key names that `-kbd-bind` accepts in
  `src/dkbd.c`, for example `fullstop`.

- Frame skip: keep the value that `-fskip` sets when the rate limit is off,
  as an explicit option.

Report events with the `LOG_MOD_*` logging calls, not with lines on stderr.

### Cover more machines

Cover more machines where the work is small. The frame skip change also
belongs in `src/mc10.c`. Check the Dragon and MC-10 keyboard maps, and test
the equipment on those machines.

### Obey XRoar's style and documentation

- Use tabs and `//` comments, as the XRoar source does.
- Give each new file the `\file` header with its copyright and licence
  block. The licence text is the owner's decision.
- Document each option in the matching options table of the Texinfo manual,
  `doc/xroar.texi`.
- Add a line to `ChangeLog` for each feature.

To find the maintainer's contact details, use the "Personal / Contact" link on
the [XRoar home page](https://www.6809.org.uk/xroar/). Do not copy a personal
email address into this repository.
