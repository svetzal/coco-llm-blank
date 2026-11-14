# Sudo policy validation

Read this when assessing bootstrap's response to present but unusable sudo on
Ubuntu. The original reproducible harness and instructions are in
[experiments/sudo-policy](../experiments/sudo-policy/README.md).

## Question and scope

Does an ordinary user receive a bounded, actionable failure when sudo requires a
password or explicitly denies commands? After an administrator corrects that
policy, does the real curl/CA prerequisite phase succeed in the same container,
without damaging existing project notes or falsely declaring readiness?

Two isolated Ubuntu 24.04 ARM64 containers test those transitions. The
administrator installs sudo and creates `learner`; each run starts without curl,
uv, or a CA bundle. Password-required policy is `PASSWD: ALL`; denial is
`NOPASSWD: !ALL`. The account has no cached authentication timestamp. Recovery
replaces that policy with `NOPASSWD: ALL` in the disposable container only.
These policies are controlled experiment inputs, not recommendations for host
sudo configuration. No credentials are requested or supplied.

Failure runs the complete production bootstrap. Recovery runs its unchanged
prefix through apt installation, with two closing conditionals appended. This
adaptation isolates the actual prerequisite boundary and never runs a successful
stand-in for uv, setup, doctor, or readiness. Curl must perform a real HTTPS
installer download after apt succeeds; the installer is not executed.

## Examined primary sources and attribution

The directly examined [bootstrap implementation](../scripts/bootstrap.sh)
selects `sudo -n` for a nonroot caller when sudo exists. Its apt error branch
returns 1 and asks the caller to resolve the error, ensure root or noninteractive
sudo access, and rerun bootstrap. Its readiness message follows environment,
notes, native tools, firmware, and doctor phases. Those are implementation
statements, not proof those phases succeed on every host.

The installed sudo executable's captured `--help` is an additional primary
source for its `-n` option. The exact sudoers entries, `visudo` validation, and
administrator policy listing are retained per container. The harness and its
prefix extraction are original experiment logic. No CoCo hardware facts or
published program adaptations are introduced here.

The [existing full onboarding report](linux-onboarding-validation.md) supplies
separate earlier evidence of complete nonroot setup and bounded emulator
execution. This experiment does not repeat or independently establish those
results.

## Measured result

On November 14, 2026, run `sudo-policy-1794679454536037000` completed both
journeys on Docker 29.8.2, Ubuntu 24.04.5 LTS, `aarch64`, UID/GID 1001.
The password-required bootstrap exited 1 in 0.29 seconds with
`sudo: a password is required`. The denied bootstrap exited 1 in 0.59 seconds
and named the refused `/usr/bin/apt-get update` command. Both also printed the
bootstrap recovery guidance. Neither attempted uv installation or printed ready.

After administrator correction, the password case's prerequisite phase exited 0
in 23.66 seconds and the denied case's phase exited 0 in 24.86 seconds. Both
installed curl `8.5.0-2ubuntu10.16` and ca-certificates
`20260816ubuntu0.24.04.2`; sudo was `1.9.15p5-3ubuntu5.24.04.4`.
Both downloaded the installer over HTTPS successfully. Its SHA-256 was
`4d8fa56e00f16b66feecacbd943773c61d61ab768b13856de350d86fd8740e2f`.

All four whole-file note comparisons passed, after failure and after recovery
for each policy. All checks for absence of `.venv`, uv, native tools, and ROMs
passed. Both named containers were removed successfully before `passed.json`
was written. No production defect was found within this boundary.

Exact input and command evidence is retained in
[the ignored run directory](../build/sudo-policy/sudo-policy-1794679454536037000/).
The directory contains the executed harness, bootstrap, extracted prefix, note
fixture, per-command logs, statuses, timings, image inspection, and hashes.
The retained `validate.py` copy identifies the executed harness. It was renamed
to `sudo_policy.py` to avoid module-name collisions, then changed by the
publication-review corrections below. The current harness therefore differs
from the retained executed copy; the original run evidence is unchanged.

- Main's head at capture, as context:
  `37303e2cbede0c47b85d9d3f76ba32902206f0f2`.
- Pinned Ubuntu image digest:
  `sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5`.
- Bootstrap SHA-256:
  `ec1057fe000fbd957891c4563e6ed7d74600c59765b7cc945935883e5530fa44`.
- Extracted prerequisite script SHA-256:
  `e8103b8e9415a08fd912b2807b22909fccfaaaa9b1948057e3dcd46fbed8381d`.
- Preserved note SHA-256:
  `3bebbec6a96f420fbd32b82bbe72d3e7b1f8dfef3faeb7c6629a6c6fa4b3d4f5`.
- Executed harness SHA-256:
  `da83c82d4fc88f4726e564000324a1a0a37653695a6803c88428e8705d4435f8`.

Three extraction-boundary specifications passed in 0.58 seconds. They check
missing and ambiguous markers, preservation of the production prefix, and real
shell syntax validation. The existing 21 bootstrap specifications passed in
7.95 seconds. Scoped Ruff lint/format and Markdown fix/check passed. Test cache
was isolated under `build/sudo-policy/`; these runs generated no coverage file
and do not claim full-suite coverage.

## Failed experiment setup and retained evidence

The first run, `sudo-policy-1794679355709506000`, assumed that `sudo -n -l` could
inspect a password-required account without authentication. It returned 1
before bootstrap ran. Inspection was moved to administrator `sudo -l -U learner`.

The second run, `sudo-policy-1794679380382215000`, passed the password-required
failure and prerequisite recovery. It then failed to collect a sudo manual that
the minimal Ubuntu image does not contain. Collection now uses installed
`sudo --version` and `sudo --help`. Neither earlier invocation establishes a
complete two-policy pass. Both removed their own container; their logs remain
under ignored `build/sudo-policy/`.

## Limits and parent integration

This is a prerequisite-policy test, not a complete bootstrap or desktop test.
It does not run Python dependency installation, native compilation, firmware
provisioning, book conversion, or an emulator. Thus it makes no new assembly,
runtime, display, audio, or physical-hardware claim. No ROM validation is needed
because no emulator is launched. It does not cover x86-64, other distributions,
PAM configurations, command-restricted positive grants, or interrupted apt.

Docker image layers may be cached. Apt repositories and the HTTPS response are
network-dependent and unpinned. Logs record exact package versions and the
response hash; the response bytes are discarded with the container. A small
original note fixture tests whole-file preservation, not every possible project.

Parent integration should link this report where sudo-policy coverage is
summarized, while keeping successful prerequisite recovery distinct from the
separate complete onboarding result. Shared indexes, production scripts, and
the existing Linux onboarding files were not changed by this task.

## Publication review corrections

Independent review verified the retained commands, hashes and all four raw
note comparisons. It also found weaknesses in future-run detection. The
harness now uses explicit shell failures for unexpected tools, compares note
logs as raw bytes, and retains assertion errors with phase and traceback in
`failure.json`. Failed runs do not publish `passed.json`.

Nine scoped harness cases pass, including each unexpected executable, an empty
tool path, CRLF mutation of the note, and retained failure evidence. Ruff lint
and formatting pass. These local regression checks do not repeat either real
container journey; the original retained results remain the execution evidence.
