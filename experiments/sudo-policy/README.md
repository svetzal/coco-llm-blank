# Sudo policy prerequisite experiment

Run this when checking whether bootstrap fails usefully with present but unusable
sudo, then recovers after a container administrator corrects permission.

```sh
uv run --no-sync python experiments/sudo-policy/sudo_policy.py
```

Use the project's already prepared Python environment and an existing Docker
engine. The host harness uses only Python's standard library. It pulls the pinned
Ubuntu 24.04 image and creates two disposable Linux ARM64 containers, one for
password-required sudo and one for an explicit command denial. Each command has
a 300-second host timeout; each container's keepalive ends after 1,800 seconds.
No host directories are mounted and no host permission or package is changed.

## Test boundary

The administrator installs only sudo, creates `learner`, and writes one explicit
sudoers policy. The initial account has no authentication timestamp. Preflight
requires missing curl, uv, and CA bundle. A small existing project-note fixture
is present. No Python environment, CoCo tools, ROMs, or package caches enter the
container from the host.

The actual, unmodified bootstrap runs as `learner` with target `coco2`. Each
failure must exit 1, explain noninteractive sudo access and rerunning bootstrap,
and stop before uv installation or readiness. The exact note bytes must survive.

The administrator then replaces the policy with `NOPASSWD: ALL` inside that same
container. This is an experiment assumption, not a host-policy recommendation.
Recovery executes the exact production prefix before the uv-installer message,
with only two closing `fi` lines appended. This isolates real apt update and
curl/CA installation. The harness refuses a missing or ambiguous boundary marker.
It does not substitute successful uv, setup, doctor, or readiness commands.

Recovery requires apt success, working curl, installed-package records, a nonempty
CA bundle, and a real HTTPS download of the uv installer without executing it.
Project notes must still match their original bytes. Python environment, native
tools, and firmware must remain absent. This is successful prerequisite recovery,
not successful complete bootstrap. No emulator runs. The separate
[full onboarding report](../../guidance/linux-onboarding-validation.md)
contains earlier positive full-journey evidence.

## Evidence and cleanup

Each invocation writes to ignored `build/sudo-policy/sudo-policy-*/`. It keeps the
exact bootstrap, extracted prefix, note fixture, executed harness, image metadata,
Git context, command arguments, statuses, timings, package versions, sudo help,
and output logs. `hashes.json` identifies those exact bytes. `passed.json` is
written only after both journeys and cleanup succeed.

The input is deliberately minimal; it is not a complete checkout snapshot.
The bootstrap hash identifies the production script tested, while Git HEAD
records context. Concurrent changes after capture cannot alter that script.
Apt repositories and the HTTPS installer response remain mutable network inputs.
The installer response's hash is retained, but its bytes are discarded with the
container. No successful install of that installer is claimed.

The harness removes only its unique named containers in `finally`. A host kill
can prevent cleanup. In that case, the exact names are in `commands.json`; remove
only those containers. Failed assertions and timeout output remain on the host.
A timeout stops the local Docker client; container cleanup terminates remaining
container processes.

This is original test orchestration. Read
[the validation report](../../guidance/sudo-policy-validation.md) for examined
sources, measured results, failed experiment controls, and limitations.

## Scoped checks

Run from the repository root:

```sh
uv run --no-sync pytest experiments/sudo-policy/sudo_policy_spec.py \
  -o cache_dir=build/sudo-policy/pytest-cache -q
uv run --no-sync pytest scripts/bootstrap_spec.py \
  -o cache_dir=build/sudo-policy/pytest-cache -q
uv run --no-sync ruff check experiments/sudo-policy
uv run --no-sync ruff format --check experiments/sudo-policy
markdownlint --fix experiments/sudo-policy/README.md guidance/sudo-policy-validation.md
markdownlint experiments/sudo-policy/README.md guidance/sudo-policy-validation.md
```
