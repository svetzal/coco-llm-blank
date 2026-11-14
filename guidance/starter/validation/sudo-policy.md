# Sudo policy validation

Read this when assessing bootstrap's response to present but unusable sudo on
Ubuntu and recovery after an administrator corrects access. Reproduction and
bounds are in [the harness README](../../../experiments/sudo-policy/README.md).

## Question and scope

Does an ordinary user receive a bounded, actionable failure when sudo requires a
password or denies commands? After explicit administrator correction in the same
container, can the user complete real bootstrap, verify firmware, pass CoCo 2
example checkpoints, and rerun setup without losing edited notes?

Two isolated Ubuntu 24.04 ARM64 containers test `PASSWD: ALL` and
`NOPASSWD: !ALL`. Each starts without curl, uv or a CA bundle. The administrator
installs sudo, creates `learner`, assigns source ownership and sets the policy.
Recovery changes it to `NOPASSWD: ALL` in that container only. These are controlled
experiment inputs, not recommended host policies. No password is collected.

The full production bootstrap runs for the expected denial. After correction,
its unchanged prefix through apt runs first to retain the earlier prerequisite
boundary evidence. Then the entire bootstrap runs, including the real uv
installer, locked Python dependencies, native compilation and firmware setup.
Nothing substitutes a successful setup, doctor or readiness phase.

## Sources and independent expectations

The examined [bootstrap](../../../scripts/bootstrap.sh) selects noninteractive sudo for
nonroot callers. Its failed apt branch explains the permission requirement and
asks the caller to resolve the error and rerun. Readiness follows environment,
notes, tools, ROMs and doctor. These are implementation statements; the container
results below establish only the tested execution.

Installed sudo help, exact sudoers entries, `visudo` output, administrator policy
listings and per-command logs are retained. Source capture includes tracked
working-tree bytes, not host tools or caches. Captured files and their hashes
identify the tested implementation even when another worker edits the checkout.
Capture is not atomic across files. Untracked work elsewhere is excluded.

The experiment reuses the original
[moving-object checks](../../../examples/moving-objects/README.md) and
[Collect Room checks](../../../examples/collect-room/README.md). Their READMEs retain
source citations, configurations and oracle provenance. No new CoCo hardware
implementation or historical program adaptation is introduced here.

Moving objects compares 13 frames against a closed-form trajectory and per-pixel
scene oracle, checks guards, and requires an unreachable checkpoint not to fire.
Collect Room checks 95 hand-authored input/state checkpoints, framebuffer and
room bytes, input history, guards and DAC callback records. Idle and unreachable
controls must pass; four broken variants must fail their expected outcome, not
merely fail to build. Raw memory and callback records do not establish GUI or
speaker behavior.

Project notes are compared as raw whole-file bytes after the initial failure,
after prerequisite recovery, after bootstrap, and before and after the edited-note
rerun. The fixture is original test data, not an actual owner instruction.

## Current execution

Run `sudo-policy-1794686568067059000` completed both journeys on November 14,
2026, using Docker 29.8.2, Ubuntu 24.04.5 LTS, ARM64 (`aarch64`) and UID/GID
1001. Both named containers were removed before `passed.json` was written.
A final Docker query found none of this task's three runs' containers remaining.

The password-required failure exited 1 in 0.07 seconds. Corrected prerequisite
recovery took 7.16 seconds, full bootstrap 1,188.57 seconds, and bootstrap rerun
0.46 seconds. The denied failure exited 1 in 0.04 seconds; its corrected
prerequisite recovery took 4.71 seconds, full bootstrap 541.94 seconds, and rerun
0.53 seconds. Both initial failures printed actionable permission/retry guidance,
omitted readiness, and preserved the notes without producing tools or ROMs.

After correction, each journey passed target-aware doctor, all 13 moving-object
frames and all 95 Collect Room checkpoints. Moving objects checked 6,144
framebuffer bytes per frame, motion, guards and its unreachable control.
Collect Room passed idle/unreachable controls and rejected all four mutations
(`WRONG_COLUMN`, `STALE_HISTORY`, `HELD_SPACE`, `SILENT`). Each game journey
recorded 384 DAC callback writes. No listening or renderer inspection occurred.

All whole-file original-note comparisons passed, before and after full bootstrap
as well as after initial failure and prerequisite recovery. Both later edited
notes matched exactly before and after bootstrap rerun. The executed harness performed
one redundant pre-rerun note read; both reads passed and retained identical bytes.
The initial publication revision removed that duplicate call. Its bootstrap
helper still checks the notes before and after rerun. This one-line deletion is
the only difference
between the executed harness and that revision; the container run was not
repeated for it.

Doctor verified `bas12.rom`, `extbas11.rom` and `disk11.rom`. Recorded versions
were uv 0.13.8, Python 3.13.18, LWTOOLS 4.25 and XRoar 1.12.1. ToolShed was absent
and optional for these direct DECB checks. Firmware hashes and emulator evidence
are retained in the captured example reports.

Exact inputs and commands are in
[the ignored run directory](../../../build/sudo-policy/sudo-policy-1794686568067059000/).
It contains per-command logs and original/edited note captures, plus both games'
and moving-object binaries, symbols, RAM and result JSON files. All 3,037 retained
artifact hashes were independently recomputed and matched. The captured
bootstrap, native installer, setup and both example runners matched the working
tree at final inspection. No claim depends on an uncaptured later edit.

- Pinned Ubuntu image digest:
  `sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5`.
- Executed bootstrap SHA-256:
  `c95f8920f1ddb14753773e9df2857c3d3c5eca33f3f49db0a0518962f8f8bf0d`.
- Executed native installer SHA-256:
  `4625b3ceb6a92c3d86a778ab045e1beaf6cd59d8e92f74b04ac5046d6a654cfd`.
- Executed harness SHA-256:
  `ca6afe1be0f0eb437b8e756240b8c974b097575bd2a1c6974fbc1cfc9e7fcfd5`.

## Earlier evidence and failed attempts

Run `sudo-policy-1794679454536037000` on November 14, 2026 established only
prerequisite recovery. Password-required and denied bootstrap exited 1 in 0.29
and 0.59 seconds respectively. Corrected prerequisite phases exited 0 in 23.66
and 24.86 seconds. All four whole-file note comparisons passed; Python, native
tools and ROMs remained absent. Both containers were removed before its pass
record. It did not execute a complete bootstrap or emulator.

Earlier run `sudo-policy-1794679355709506000` failed while trying to inspect
password-required policy as the ordinary account. Inspection now uses
administrator `sudo -l -U learner`. Run `sudo-policy-1794679380382215000` failed
collecting a manual absent from the minimal image. Collection now uses installed
sudo help. Both removed their containers; neither establishes a two-policy pass.

During this extension, `sudo-policy-1794685023868369000` was deliberately
interrupted during the password case's full bootstrap to add the separate game
check before continuing. Failure and prerequisite recovery had passed. Its
container was removed and `failure.json` retained `KeyboardInterrupt`, with no
`passed.json`. That earlier runner recorded its interrupted command status as
`timeout`; this was an instrumentation limitation, not an actual timeout.
The current runner distinguishes interruption from `TimeoutExpired`.

Run `sudo-policy-1794685134897562000` reached real Python dependency installation,
then failed at guidance setup after 1,278.19 seconds. The inherited fixture used
`Target: coco2`, which the production setup correctly rejects. Its error names
the accepted `Target: CoCo 2` spelling. This was a harness defect, not a bootstrap
defect. No readiness message or pass record was produced, and cleanup succeeded.
The corrected fixture now passes a real setup test, including later edits; a
wrong-target control fails without changing the file. The harness now captures
notes before and after full bootstrap, including failed full-bootstrap attempts.
The failed invocation did not capture its post-bootstrap note bytes, so that
specific preservation result remains unmeasured.

All these logs remain under ignored `build/sudo-policy/`. Earlier published
results identify their captured harness, not the current extended implementation.

## Regression checks and limits

The scoped suite checks extraction boundaries, real shell syntax, absent-tool
negative controls, raw newline and edited-note mutations, real subprocess
failure, timeout bounds, and retained failure evidence without a pass record.
Before the cleanup review corrections, 18 harness specifications and
30 production bootstrap specifications passed together (48 passed in
7.03 seconds after the duplicate-read removal). Scoped
Ruff lint/format, Markdown fix/check
and `git diff --check` passed. These checks do not claim full-suite coverage.

This is ARM64 Ubuntu container evidence only. It does not establish native Linux
desktop or x86-64 onboarding, Apple Silicon macOS onboarding, GUI appearance,
listened-to audio, physical CoCo behavior, PAL, T1, disk loading, OCR conversion,
other distributions, other PAM configurations, or interrupted apt recovery.
Intel Mac support is outside scope, not a pending validation task.

Image layers may be cached. The image digest is pinned, but apt repositories,
the uv installer response and package servers are network inputs. Version logs
and checksums constrain what was observed; they do not promise future network
availability. Failure before collection retains command logs but loses internal
build artifacts when the container is removed. A host kill can prevent cleanup.

Only `experiments/sudo-policy/` and this report were edited. Shared indexes,
production scripts and the existing Linux onboarding harness belong to other
work and were not changed here.

## Cleanup review corrections

Independent review verified all 3,037 retained hashes, both full journeys and
their RAM, note-preservation and cleanup evidence. It then found two harness
failure-path gaps. Cleanup now discovers only containers bearing this attempt's
unique ownership label, including when Docker created a container but start
failed or the client was interrupted. A cleanup failure records its own stage;
any preceding failure remains separately recorded.

The revised harness passed 21 specifications. A real Docker run using the cached
image failed after daemon-side creation because its test executable was absent.
The retained probe logs show discovery and successful removal of that owned
container. Its command records are under
`build/sudo-policy/sudo-policy-1794688689594322000/`.

The full bootstrap journeys were not repeated for these cleanup changes. Their
captured implementation remains the evidence for full recovery; the focused
regressions and actual failed-start probe establish the later cleanup behavior.
An external hard kill of the orchestrator can still prevent cleanup.
