# Nonroot Ubuntu onboarding experiment

Run this when checking the complete bootstrap on Ubuntu 24.04 ARM64 with an
ordinary user and explicit noninteractive sudo access. This is original test
orchestration, not a published CoCo program adaptation. It runs the existing
original moving-object example without changing its assembly or oracle.

From the repository root, with Docker already running and host Python available:

```sh
uv run python experiments/linux-onboarding/validate.py
```

The host Python only orchestrates Docker. It is not transferred to the container.
The harness pulls the pinned Ubuntu image before inspecting it or creating
containers. No Docker installation, GUI, host package installation, Git
mutation, or bind mount is performed. Expect several GiB of downloads and allow
40 minutes for the bootstrap timeout. Network and repository availability are
external requirements; package repositories and the uv installer are not pinned
by this harness.

## Host assumption versus bootstrap work

The harness acts as container administrator solely to create `learner`, unpack
and assign ownership of the source checkout, and, in the positive case, install
`sudo --no-install-recommends` and an explicit `NOPASSWD` sudoers entry.
This broad sudo grant is a controlled disposable-container assumption. It is
not bootstrap behavior or a recommendation to change desktop account policy.
The image's existing Ubuntu user is left alone; `learner` receives its own UID.

Before bootstrap, checks require a nonzero UID and absence of curl, uv, Python,
LWASM, XRoar, CA bundle, `.venv`, and `local`. Bootstrap must provision its own
prerequisites, Python packages, native sources/tools, and firmware. The positive
case checks that `sudo -n` is usable. No host tools, ROMs, or caches enter it.

The separate negative container receives only the account and checkout, with
no sudo installation. Bootstrap must exit 1, mention noninteractive sudo and
an administrator, explain rerunning bootstrap, and omit its readiness message.
The harness checks that `.venv`, `local`, and the uv executable remain absent.
This tests missing sudo; it does not test a present sudo executable whose policy
denies access or requires a password.

## Observable checks and evidence

The positive case runs the entire bootstrap, then the real headless CoCo 2
moving-object check. It appends a simulated owner note, saves its exact bytes,
reruns bootstrap, compares the whole note file, and runs target-aware doctor.
The sentinel is a preservation fixture, not an actual owner requirement.
The example supplies its existing unreachable-checkpoint control and independent
framebuffer/state oracle. See [the example](../../examples/moving-objects/README.md)
for its machine contract and separate source research.

Each run creates unique ignored directories:

- `local/research/linux-onboarding/nonroot-*/` holds the exact source tar,
  per-file SHA-256 manifest, downloaded sources, and firmware.
- `build/linux-onboarding/nonroot-*/` holds command arguments, exit statuses,
  elapsed times, environment and version logs, Git provenance, collected emulator
  evidence, before/after notes, and artifact hashes after a successful run.

Snapshot input is tracked working-tree files plus this experiment's direct files.
It excludes `.git`, `.venv`, `local`, and `build`. Concurrent changes after capture
cannot alter container input. Git HEAD and diff describe capture-time context;
the tar and its per-file hashes identify actual tested bytes. Files are captured
one at a time, so this is not a transactional snapshot of concurrent writers.
The harness records the exact input before either container starts.

Each named container is removed in `finally`, including after a failed assertion.
Failed command output and statuses remain on the host. Successful runs also copy
container build and local artifacts before removal. On failure before collection,
internal artifacts are not copied; diagnose from the retained command logs.
An externally killed host orchestrator can prevent cleanup. Remove only the
specific container name recorded in that run's `commands.json` in that case.

Read [the validation report](../../guidance/linux-onboarding-validation.md)
for measured results. These checks do not prove native desktop onboarding,
x86-64, GUI appearance, audio, physical hardware, PAL, T1, disk loading, or the
complete starter test suite. They do not convert books or download OCR models.
