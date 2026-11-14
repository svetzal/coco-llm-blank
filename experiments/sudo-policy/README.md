# Sudo policy recovery experiment

Run this when checking whether bootstrap fails usefully with present but unusable
sudo, then completes setup after a container administrator corrects permission.

```sh
uv run --no-sync python experiments/sudo-policy/sudo_policy.py
```

Use the project's prepared Python environment and an existing Docker engine.
The host harness uses only Python's standard library. It pulls a pinned Ubuntu
24.04 image using its digest and `--platform linux/arm64` before inspection or
creation, including when no local image exists. It creates two uniquely named
containers, one for password-required sudo and one for explicit command denial.
No host directories are mounted and no host packages or permissions change.

## Test boundary

Each container receives a captured copy of tracked working-tree files, excluding
`.git`, `.venv`, `local`, and `build`, plus an original project-note fixture.
No host Python environment, CoCo tools, firmware, or package cache enters it.
Capture is per file, not transactional across concurrent writers. The saved
inputs and hashes identify the actual tested bytes; Git HEAD is context only.
Untracked work elsewhere is excluded.

The administrator installs only sudo, creates `learner`, assigns source
ownership, and writes `PASSWD: ALL` or `NOPASSWD: !ALL`. The ordinary account
has no cached authentication timestamp. Preflight requires missing curl, uv,
and CA bundle. Production bootstrap runs with target `coco2` and must exit 1,
explain noninteractive sudo access and rerunning bootstrap, and omit uv
installation and readiness. Exact project-note bytes must survive. Python,
native tool directories and firmware must remain absent.

The administrator replaces the policy with `NOPASSWD: ALL` inside the same
container. This is a disposable experiment input, not host-policy advice.
The unchanged production prefix through apt, with two closing `fi` lines,
checks prerequisite recovery separately. Extraction rejects missing or ambiguous
boundary markers. Curl then downloads the uv installer over HTTPS without
executing that particular download. Notes and absent-tool checks repeat.

The entire production bootstrap then runs without substitution. It installs uv,
the locked Python environment, native tools and checksum-verified CoCo 2 ROMs.
The harness requires successful exit and the readiness message, then runs the
selected-target doctor independently. The two example checks are:

- [Moving objects](../../examples/moving-objects/README.md): 13 checkpoints,
  complete framebuffer comparison against an independent pixel/trajectory
  oracle, guards and an unreachable checkpoint.
- [Collect Room](../../examples/collect-room/README.md): builds its separately
  instrumented pinned XRoar, checks 95 hand-authored game checkpoints, idle and
  unreachable controls, and four deliberately broken variants. These establish
  RAM/state and DAC callback outcomes, not visible or audible output.

Both are existing original examples, executed without changing their assembly,
fixtures, or oracle. Their READMEs retain hardware source provenance and machine
contracts. The note fixture declares the moving-object test configuration;
Collect Room selects its own documented `coco2bus` profile.

After successful checks, the harness appends an owner-edit fixture, captures
and compares its exact bytes, reruns full bootstrap, and compares those bytes
again. It reruns doctor and records Python, uv, LWASM and XRoar versions.

## Bounds, evidence and cleanup

Ordinary commands have a 300-second host timeout. Initial full bootstrap allows
2,400 seconds, moving-object checks 840 seconds, and game preparation and checks
900 seconds each. Each container keepalive ends after 7,200 seconds. Network
availability and several GiB of downloads are prerequisites for this experiment.
Apt, the uv installer and package servers are mutable network inputs; the image,
project lockfile, native release archives and ROM checksums constrain other inputs.

Ignored `build/sudo-policy/sudo-policy-*/` retains captured sources, harness,
notes, image metadata, command arguments, statuses, bounds, timings and logs.
Successful journeys copy emulator artifacts before removal. `hashes.json`
identifies retained bytes. `passed.json` is written only after both complete
journeys and their cleanup. Exceptions record the policy, exact failed stage,
error and traceback in `failure.json`; they never publish a pass. Full bootstrap
compares notes before and after the command, including a failed command.
Failure before artifact collection retains command logs but not the container's
internal build.

Cleanup discovers and removes only containers carrying this attempt's unique
ownership label, including containers created before a failed start. A timeout
kills the local Docker client; container removal terminates remaining container
work. An externally killed host orchestrator
can prevent cleanup. Names and labels are retained in `commands.json` for that
case. Cleanup failures record their own stage and retain any preceding failure
separately.

Read [the validation report](../../guidance/starter/validation/sudo-policy.md) for actual
results and limitations. This is Linux ARM64 container evidence. It is not native
desktop, x86-64, Apple Silicon macOS, GUI, listening, or physical-hardware evidence.
Intel Mac support is outside the project scope and is not a queued validation.

## Scoped checks

Run from the repository root:

```sh
uv run --no-sync pytest experiments/sudo-policy/sudo_policy_spec.py \
  scripts/bootstrap_spec.py -o cache_dir=build/sudo-policy/pytest-cache -q
uv run --no-sync ruff check experiments/sudo-policy
uv run --no-sync ruff format --check experiments/sudo-policy
markdownlint --fix experiments/sudo-policy/README.md guidance/starter/validation/sudo-policy.md
markdownlint experiments/sudo-policy/README.md guidance/starter/validation/sudo-policy.md
```
