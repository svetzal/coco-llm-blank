# Ubuntu onboarding validation

Read this report when assessing the current bootstrap and firmware changes on
Linux. This experiment uses the current working tree, including uncommitted
changes. It does not establish support for every Linux host.

## Nonroot sudo validation

Publication review found that the harness inspected the pinned image before
Docker could fetch it. The retained run used a cached image and remains valid.
The harness now pulls before inspection. Two process-boundary regression cases
with a fixture Docker executable check acquisition from an absent-image state
and retention of a failed pull diagnostic. They do not establish an uncached
registry download or repeat the complete onboarding run.

The November 14, 2026 follow-up uses the tracked original harness in
[experiments/linux-onboarding](../experiments/linux-onboarding/README.md).
It asks whether the complete corrected bootstrap works as an ordinary user
with explicit noninteractive sudo, and whether missing sudo fails before
readiness. The earlier root runs below remain separate evidence.

### Nonroot host precondition

A fresh Ubuntu 24.04 ARM64 container uses the existing Docker engine and cached
image layers. The container administrator creates `learner`, installs only
`sudo` with `--no-install-recommends`, grants that account `NOPASSWD` access,
and assigns the unpacked source checkout to it. This is an explicit disposable
host assumption. Bootstrap does not create the account or grant sudo access.

Preflight reports UID/GID 1001, Ubuntu 24.04.5 LTS, and `aarch64`. It verifies
that curl, uv, Python, LWASM, XRoar, CA bundle, `.venv`, and `local` are absent,
and that `sudo -n` succeeds. Bootstrap must install curl and certificates,
then uv/Python, locked packages, native tools, and firmware. No host mounts,
virtual environment, tools, ROMs, source archives, or package caches are copied.
Only the checkout snapshot enters the container.

### Nonroot source provenance

Main's head at capture was the parent-supplied revision
`974d86c0c2f708e10dbf2baee4cdc079117612ff`. The tar contains 88 tracked
working-tree and experiment files. All tar member bytes were independently
checked against its SHA-256 manifest. Later concurrent edits are outside this
run. The snapshot is not claimed to be an atomic view of concurrent edits.

- Input tar SHA-256:
  `159669eb7cc185bbb020fb634552df029b420f26a843d3e4c58a96777f560ae3`.
- Bootstrap SHA-256:
  `ec1057fe000fbd957891c4563e6ed7d74600c59765b7cc945935883e5530fa44`.
- Lockfile SHA-256:
  `a7203eb44883bbee9776ffd5eda312c918c30c55fc1f664b997a9c72b662d975`.
- Ubuntu image digest:
  `sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5`.

The exact input and downloads live under ignored
`local/research/linux-onboarding/nonroot-1794677060331912000/`.
Commands, statuses, timings, and collected results live under ignored
`build/linux-onboarding/nonroot-1794677060331912000/`.
The snapshot includes the executed harness; its only later executable edit
replaces `dict(...)` with an equivalent dictionary literal for Ruff. The README
was added after capture. Reproduction logic is retained in the tracked harness,
not only in ignored evidence. Apt repositories and the uv installer remain
network-dependent inputs; their content is not pinned by this experiment.
Native source archives and firmware are checksum-verified by production setup.

### Independent no-sudo control

A separate fresh container receives only the account and source snapshot.
It has no sudo executable or granted privilege. Running the actual bootstrap
as UID 1001 exits 1 in 0.08 seconds. The message tells the caller that curl
installation requires root or noninteractive sudo, asks for administrator
installation of curl and certificates, and says to rerun bootstrap.
No readiness message, `.venv`, `local`, or uv executable is produced. The
harness asserts all these outcomes and removes only its named control container.
A present sudo executable with denied/password-required policy was not tested
in this container control.

### Nonroot measured result and limits

The complete nonroot path passed on Docker engine 29.8.2. Every bootstrap,
example, rerun, and doctor command used `docker exec --user learner` with its
own home and PATH. Root was used only for the stated host precondition.

| Check | Exit | Result |
| --- | --- | --- |
| First nonroot bootstrap | 0 | 1,138.06 seconds; tools and firmware ready |
| Real CoCo 2 moving-object check | 0 | 6.45 seconds; all 13 frames passed |
| Bootstrap rerun | 0 | 0.87 seconds; edited project notes preserved |
| Notes and doctor | 0 | Bytes equal; all three ROM members verified |
| Collection and cleanup | 0 | Artifacts copied; both containers removed |

Versions were uv 0.13.8, Python 3.13.18, LWTOOLS 4.25, and XRoar 1.12.1.
uv prepared 130 packages in 15 minutes 25 seconds and installed them in
11.53 seconds. Its container-local cache occupied 5.9 GiB. These measurements
include the unchanged lockfile's CUDA packages. They describe this run's cost,
not guaranteed performance or a dependency-change recommendation. ToolShed
remained absent and was correctly reported as optional for this direct demo.

The runtime results identify `cocous`, explicit non-T1 `6847`, 6809, 32 KiB,
NTSC, normal emulated clock, CoCo 2 BASIC/Extended BASIC, and direct DECB loading.
Frames 1, 15, 16, 17, 31, 32, 46, 64, 65, 185, 186, 369, and 370 pass exact
state, guard-byte, and 6,144-byte framebuffer checks. The unreachable checkpoint
passes its no-capture control. These are real assembly and bounded headless
execution results, not rendered-display evidence.

Both project-note copies have SHA-256
`ff7b13abaf554905fe163ee19af9e16d0ae4ebe7c0d54f26211089f872105a0a`.
The note sentinel simulates an owner edit. The whole file comparison, not just
presence of the sentinel, establishes preservation. Reruns reuse only this
container's own caches. Network access remains available; upstream cache use
was not measured.

After collection, native archive SHA-256 values match the captured
`scripts/native.py`: LWTOOLS
`9bb97e987d486d7abd85d04cb98a53f666f02785c108647b795c4a111c5eb09f`
and XRoar
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
The downloaded CoCo 2 ZIP matches `roms.json` with SHA-256
`b091bb40fa2fd7ce9be2d72346039894d1bff88243d03d3092746939bf60db38`.
The run's `artifact-hashes.json` retains hashes of all collected files.
Downloaded sources and firmware remain ignored.

The tracked harness has passed its real Docker boundary checks. The existing
21 bootstrap specifications also passed in 5.90 seconds. Scoped Ruff check and
format check, Markdown lint, and whitespace checks passed. No production defect
was found in this tested journey, and no production code was edited.

This establishes the explicit passwordless-sudo container case only. A native
desktop, x86-64, denied/password-required sudo policy, GUI, audible output,
physical hardware, PAL, T1, disk loading, other CoCo targets, book conversion,
and the complete starter suite remain outside this run. Missing/corrupt-ROM
injections were not repeated; their earlier results below remain distinct.
The harness is original reproducible logic, and earlier failed controls remain
in this report. Parent integration must update any shared plan claims about
nonroot coverage; this task does not edit that plan.

### Examined sources and attribution

This is an original onboarding validation, not a hardware technique adaptation.
The directly examined primary implementation passages are
[bootstrap's missing-curl privilege branch and final readiness sequence](../scripts/bootstrap.sh),
[HostGateway.dependencies and checksum-verified native source builds](../scripts/native.py),
and [the moving-object runner's emulator, verify_ram and capture functions](../scripts/moving_objects.py).
The latter checks real assembled output against a closed-form trajectory and
pixel-level framebuffer oracle, with an unreachable checkpoint control.
The [example contract](../examples/moving-objects/README.md#machine-contract)
defines the tested CoCo 2 configuration. This follow-up adds no hardware facts
and does not claim fresh examination of the example's cited book pages.

## Full corrected-bootstrap validation

The final November 14, 2026 run tests the corrected bootstrap from a fresh
Ubuntu 24.04 ARM64 container through the CoCo 2 moving-object check and a
bootstrap rerun with edited project notes. The earlier experiments below remain
as evidence of the original failure, recovery behavior, and isolated curl fix.

### Exact input and environment

The parent fetched main before dispatch. At capture, main's head was
`6a865c1adcdd4422f69ecb7fecc8472821f8bc15`, containing the curl prerequisite fix.
The snapshot includes 76 tracked files from the working tree; only AGENTS.md
was dirty. All tar member hashes were checked against the snapshot manifest.
No later concurrent edits form part of this run's evidence.

- Snapshot tar SHA-256:
  `52fa6f2fa60197589833a4f15d5bd3a0dec3e38a75b27a5d66448fd996666d6e`.
- Captured `git diff HEAD` SHA-256:
  `8169e43bb4a82122a3105209b1144e4900a9af1a83687c2ae02a3583c03175ab`.
- Executed bootstrap SHA-256:
  `ec1057fe000fbd957891c4563e6ed7d74600c59765b7cc945935883e5530fa44`.
- Cached Ubuntu image digest:
  `sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5`.

Docker engine 29.8.2 created a new root container with `--platform linux/arm64`.
It reported Ubuntu 24.04.5 LTS and `aarch64`. Existing Docker image layers
were reused. No host mounts, Python environment, native tools, ROMs, or package
cache were supplied. The snapshot excludes `.git/`, `.venv/`, `local/`, and
`build/`. Bootstrap itself installs curl and CA certificates, then real uv;
no installer wrapper or substitute executable is used in this run.

### Measured result

The full corrected journey passed. No prerequisite was manually installed.

| Check | Exit | Measured result |
| --- | --- | --- |
| First bootstrap | 0 | 796.40 seconds; tools and firmware ready |
| Moving-object check | 0 | 8.02 seconds; all 13 frames passed |
| Bootstrap rerun | 0 | 1.06 seconds; tools and firmware reused |
| Edited project notes | 0 | `cmp` equal; CoCo 2 target and sentinel preserved |
| Final target-aware doctor | 0 | All three firmware members verified |
| Collection and cleanup | 0 | Both copies and container removal completed |

The installed versions were uv 0.13.8, Python 3.13.18, LWTOOLS 4.25, and
XRoar 1.12.1. uv reported preparing 130 packages in 11 minutes 45 seconds.
The container's uv cache occupied 5.9 GiB after setup. These times describe this
run and network; they are not performance guarantees. ToolShed was absent and
reported as optional for the direct demo.

The checked configuration is `cocous`, explicit non-T1 `6847`, 6809, 32 KiB,
NTSC, normal emulated clock, CoCo 2 BASIC/Extended BASIC firmware, and direct
DECB loading. These are the existing experiment's choices, not newly supplied
owner requirements. Bootstrap's project notes keep unspecified application
choices unresolved. The headless runner uses null video and audio output.

Frames 1, 15, 16, 17, 31, 32, 46, 64, 65, 185, 186, 369, and 370 passed
frame-counter, position, guard-byte, and complete 6,144-byte framebuffer
checks. Thirteen 32,768-byte RAM captures were collected. The unreachable
checkpoint produced no capture. This proves assembly and completed-frame
execution against the existing runner's independent oracle. This run did not
repeat the earlier missing/corrupt-ROM injection checks below.

Both edited project-note copies have SHA-256
`64b004ff4cb30ae7556736ec55d56ba475b813873cf41ff13ae642353e4931d1`.
The CoCo 2 ZIP was fetched from
<https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/coco2.zip>.
Its SHA-256 is
`b091bb40fa2fd7ce9be2d72346039894d1bff88243d03d3092746939bf60db38`.
All extracted member hashes match `roms.json`; the collected ZIP and native
source archives were independently rehashed after copying back to the host.
`build/linux-onboarding-final/artifact-hashes.json` retains those hashes plus
hashes of the collected build evidence. Native archive sources and expected
hashes are in the captured `scripts/native.py`.

### Reproduction and evidence

From the repository root, create a tar containing only tracked working-tree
files. Record its SHA-256 and per-file hashes before starting Docker. The
retained `snapshot.tar` is the exact input for this run. Run:

```sh
docker create --platform linux/arm64 \
  --name coco-linux-onboarding-final-20261114 \
  --workdir /work ubuntu:24.04 sleep 7200
docker cp local/research/linux-onboarding-final/snapshot.tar \
  coco-linux-onboarding-final-20261114:/snapshot.tar
docker start coco-linux-onboarding-final-20261114
docker exec coco-linux-onboarding-final-20261114 \
  sh -c 'tar xf /snapshot.tar -C /work'
docker exec coco-linux-onboarding-final-20261114 \
  sh -c 'timeout 1800 sh scripts/bootstrap.sh coco2'
docker exec coco-linux-onboarding-final-20261114 \
  sh -c 'timeout 840 /root/.local/bin/uv run python \
    scripts/moving_objects.py check --target coco2'
```

Inside `/work` in that container, preserve an edited copy before rerunning:

```sh
mkdir -p build/linux-onboarding-final
printf '\n## Onboarding preservation sentinel\n\n%s\n' \
  'Owner-edit test: preserve this CoCo 2 project note exactly.' >> local/PROJECT.md
cp local/PROJECT.md build/linux-onboarding-final/PROJECT-before.md
PATH=/root/.local/bin:$PATH timeout 300 sh scripts/bootstrap.sh coco2
cmp local/PROJECT.md build/linux-onboarding-final/PROJECT-before.md
cp local/PROJECT.md build/linux-onboarding-final/PROJECT-after.md
/root/.local/bin/uv run python scripts/doctor.py --profile demo --target coco2
```

The sentinel simulates an owner's edit; it is not an owner requirement.
The rerun reuses this container's own package, native-source, and firmware
caches. Network access is available; upstream HTTP caching was not measured.

Collect evidence before removing only this named container:

```sh
docker cp coco-linux-onboarding-final-20261114:/work/build/. \
  build/linux-onboarding-final/container-build
docker cp coco-linux-onboarding-final-20261114:/work/local/. \
  local/research/linux-onboarding-final/container-local
docker rm -f coco-linux-onboarding-final-20261114
```

`build/linux-onboarding-final/commands.json` records every command, exit code,
and elapsed time. Adjacent logs retain bootstrap, rerun, versions, doctor,
notes, and hashes. `container-build/moving-objects/` holds the assembled binary,
symbols, RAM captures, logs, and result JSON. The ignored
`local/research/linux-onboarding-final/` folder holds the source snapshot,
manifest, dirty diff, orchestration driver, and collected local artifacts.
The commands above contain the experiment logic; reproducing the test does
not depend on retaining the ignored driver.

This run measures onboarding and the existing original moving-object
experiment. It introduces no hardware-source facts or new adaptation of a book
program. The existing example's source analysis is separate from this runtime
check. RAM evidence does not establish rendered appearance, audible output,
physical hardware, PAL, T1, CoCo 3, disk loading, x86-64 Linux, or non-root sudo.
The expensive full suite and document conversion were not rerun.
Scoped `markdownlint --fix`, `markdownlint`, and `git diff --check` passed for
this report. No production code was changed, committed, or pushed in this run.

## Earlier environment and snapshot

The November 14, 2026 experiment runs in a fresh Ubuntu 24.04 container on the
existing Docker Desktop engine. The host is Darwin ARM64; the container is
Linux ARM64 (`aarch64`), running as root. No host daemon, virtualization package,
global tool, shared project notes, or other project was changed.

The parent had fetched the repository. At capture, `HEAD` equalled `origin/main`
(both `a4ce0abbba8103b4adebab36ace157b05714c836`). The snapshot contains 56
tracked and non-ignored untracked files, copied from their working-tree bytes.
It excludes `.git/`, `local/`, `build/`, and `.venv/`. No host ROMs, source
archives, Python environment, or tool binaries were copied.

- SHA-256 of `git diff --binary HEAD`:
  `39daef14e18e62ece9afcbb5672036f466a3ba6437538f0196f253cebe1da388`.
- SHA-256 of the actual tar snapshot:
  `de44e1f0880aeb0caba19489d8a2bef73d9998ef4c2a8bb1bd6e62b83ed17ecf`.
- Ubuntu image repository digest:
  `sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5`.

The dirty diff covers tracked changes only. The snapshot manifest also records
the SHA-256 of each included file, including untracked files. Later concurrent
edits are outside this snapshot's evidence.

`docker pull ubuntu:24.04` reported that the image was already up to date.
The image layers were cached; this was a fresh container, not an uncached image
download. `/etc/os-release` reports Ubuntu 24.04.5 LTS.

## Bare-image failure

With no `local/` or `.venv/`, this command failed before uv installation:

```sh
sh scripts/bootstrap.sh coco2
```

The error was `scripts/bootstrap.sh: 29: curl: not found`. That bootstrap assumed
curl was installed before it could install uv. This exposed an onboarding gap
on the bare Ubuntu image, corrected and fully retested above. No production
script was changed for that first experiment.

The continuation explicitly installs prerequisites inside the container:

```sh
timeout 300 sh -c \
  'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y curl ca-certificates'
timeout 1200 sh scripts/bootstrap.sh coco2
```

After that prerequisite installation, bootstrap exited 0 within its 1,200-second
limit. It installed uv 0.13.8 and Python 3.13.18, synchronized the unchanged
lockfile, built LWTOOLS 4.25 and XRoar 1.12.1 from checksum-verified source
archives, downloaded CoCo 2 firmware, and passed the target-aware doctor check.
ToolShed was absent and correctly reported as optional for the direct demo.

The empty Python cache grew to 5.9 GiB. The lockfile installed PyTorch/CUDA
packages as part of the baseline; downloads took most of the attempt. This is
a measured onboarding cost, not a proposed dependency change.

## Runtime and recovery results

The one-off driver `local/research/linux-onboarding/validate.py` completed with
exit 0. All commands and their exit statuses are in
`build/linux-onboarding/commands.json`; each command has a corresponding log.

| Check | Result |
| --- | --- |
| Target-aware doctor | Exit 0; all three firmware members verified |
| Moving-object check before fault injection | Exit 0; 13 frames passed |
| Bootstrap rerun with edited notes | Exit 0; notes unchanged |
| Missing `bas12.rom`, doctor | Exit 1 |
| Missing `bas12.rom`, real runner | Exit 1 before XRoar launch |
| Setup with missing member, valid ZIP | Exit 0; original bytes restored |
| Same-size `bas12.rom` corruption, doctor | Exit 1 |
| Same-size corruption, real runner | Exit 1 before XRoar launch |
| Setup with differing existing member | Exit 1; corrupt file preserved |
| Setup after corrupt member removal | Exit 0; original bytes restored |
| Final doctor and moving-object check | Both exit 0; 13 frames passed again |

Both runner failures included the recovery command
`uv run python scripts/setup.py --target coco2 --roms-only`.
The corrupt runner reported `checksum mismatch`; setup reported
`existing ROM differs; inspect before replacing`. Negative runner tests used
an executable forwarding wrapper that would record an XRoar launch before
executing the real emulator. Its launch marker was never created. Passing
frame checks used the real installed emulator directly.

The moving-object runner reached `frame_ready` for frames 1, 15, 16, 17, 31,
32, 46, 64, 65, 185, 186, 369, and 370. For each frame it checked all 6,144
framebuffer bytes, the frame counter, positions, and framebuffer guard bytes
against its independent oracle. The unreachable data-address trap produced
no snapshot. The retained final run has thirteen 32,768-byte RAM captures.
This establishes execution through the completed-frame checkpoint, not just
process startup or successful assembly.

The first ROM provision fetched
`https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/coco2.zip` with no project
ROM cache. The successful provision checks the ZIP and member hashes.
`build/linux-onboarding/firmware.json` records the manifest and actual hashes
for the ZIP, `bas12.rom`, `extbas11.rom`, and `disk11.rom`; all match.
The ZIP SHA-256 is
`b091bb40fa2fd7ce9be2d72346039894d1bff88243d03d3092746939bf60db38`.
Repairs and reruns reused that container-local ZIP cache. They were not fresh
downloads. Upstream HTTP/CDN caching was not measured. Network access was
available for apt, uv, Python packages, native archives, and firmware.

## Evidence and commands

Ignored evidence is under `local/research/linux-onboarding/`. It includes
`snapshot.json`, `snapshot.tar`, `dirty.diff`, `image.json`,
`docker-version.txt`, `bare-bootstrap.log`, `prerequisites.log`, and
`bootstrap.log`. The snapshot is a current-working-tree copy, not a Git worktree.

The container was created and populated with:

```sh
docker pull ubuntu:24.04
docker create --name coco-linux-onboarding-20261114 \
  --workdir /work ubuntu:24.04 sleep 7200
docker cp local/research/linux-onboarding/snapshot.tar \
  coco-linux-onboarding-20261114:/snapshot.tar
docker start coco-linux-onboarding-20261114
docker exec coco-linux-onboarding-20261114 \
  sh -c 'tar xf /snapshot.tar -C /work'
```

There are no host bind mounts. All setup and emulator commands run inside this
container. Downloaded firmware and generated evidence stay ignored.

The validation driver and evidence were transferred with:

```sh
docker cp local/research/linux-onboarding/validate.py \
  coco-linux-onboarding-20261114:/validate.py
docker exec coco-linux-onboarding-20261114 \
  sh -c 'timeout 1800 /root/.local/bin/uv run python /validate.py'
docker cp coco-linux-onboarding-20261114:/work/build/linux-onboarding/. \
  build/linux-onboarding/
docker cp coco-linux-onboarding-20261114:/work/build/moving-objects \
  build/linux-onboarding/moving-objects
docker rm -f coco-linux-onboarding-20261114
```

The driver sets `/root/.local/bin` on its child PATH. The successful runtime
command, executed inside `/work`, is:

```sh
uv run python scripts/moving_objects.py check --target coco2
```

The driver bounds individual setup commands to 180 seconds, the bootstrap
rerun to 300 seconds, and each 13-frame run to 840 seconds. The existing runner
also imposes 60-second limits on individual emulator processes. The container
was removed after evidence collection; no task emulator process was left alive.

## Coverage limits

This is a root container test under Docker Desktop's Linux VM. It is not a
native Ubuntu desktop, x86-64, non-root sudo, GUI, audio, physical CoCo, or
network-isolated test. No visual appearance claim follows from RAM checks.
The selected CoCo 2 runner uses NTSC, a non-T1 MC6847, 32 KiB RAM, a stock
6809, and direct DECB loading. It does not prove PAL, T1, disk boot, or every
CoCo 2 revision.
This task did not run the repository-wide pytest suite, book conversion, or
model downloads. Its evidence is the specified onboarding and runtime journey.
Only the new report and ignored experiment/evidence paths were written on the
host. No commits, branches, pushes, or production-code fixes were made.

## Curl prerequisite correction validation

A follow-up on November 14, 2026 corrects the bare-image failure above. The
preceding experiment and its full runtime and recovery evidence remain intact;
its statements about unchanged production code describe that earlier run.

Bootstrap now installs `curl` and `ca-certificates` through apt when curl is
missing and neither uv nor Homebrew provides the fast path. It follows
`scripts/native.py`'s privilege convention: apt directly as root, otherwise
`sudo -n`. Missing apt or sudo produces an actionable error. Failed apt or
sudo access stops bootstrap before uv or readiness. Existing curl continues
straight to the official uv installer. This does not add automatic support for
other package managers or expand the native installer's supported platforms.

The fresh correction container used the existing Docker engine (29.8.2) and
cached Ubuntu image with repository digest
`sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5`.
It reported Ubuntu 24.04.5 LTS and `aarch64`. Before bootstrap, the harness
verified that curl, uv, and `/etc/ssl/certs/ca-certificates.crt` were absent.
No prerequisite was manually installed. Bootstrap itself ran apt update,
installed curl and CA certificates, downloaded the official installer over
HTTPS, and installed real uv 0.13.8 for `aarch64-unknown-linux-gnu`.

The harness supplied a `sh` wrapper only at the installer boundary. It ran the
installer with `/bin/sh`, checked the installed binary using `uv --version`,
retained it as `uv-real`, and then substituted a recording uv command. That
command recorded `sync --locked` and deliberately exited 86. Bootstrap stopped
there without claiming readiness. The harness asserted these outcomes and
exited 0. This proves the corrected bootstrap reaches real uv installation on
a bare root Ubuntu ARM64 container. It does not repeat Python synchronization,
native builds, firmware installation, or emulator validation. At that stage
those results were covered only by the earlier experiment. The full corrected
bootstrap run above now covers them without manually installed prerequisites.
Non-root sudo behavior is covered by shell-boundary tests, not by this root
container.

No host packages were installed, no project dependencies changed, and the
5.9 GiB observation did not trigger dependency work. There were no host bind
mounts. The container was removed after evidence collection.

### Correction snapshot and checks

The shared checkout was fetched and inspected before editing; no rebase was
attempted on its dirty tree. Another worker advanced main during this task.
At container capture and final checks, main and origin/main pointed to the
research-plan reconciliation revision,
`fcfd6b1c1bb238aeb5504756016e89645287ef63`. The correction was uncommitted.
Only bootstrap was copied into the container, alongside the isolated harness.

- Executed bootstrap SHA-256:
  `ec1057fe000fbd957891c4563e6ed7d74600c59765b7cc945935883e5530fa44`.
- Container-capture scoped diff SHA-256:
  `dac53e43300a1ad66a80e4770688041338549d6a65c963da3aad413b1e4392c9`.
- Final scoped diff SHA-256, after adding three fast-path/help cases:
  `2e779451eca72773c9c5864c2b6b3f59a46e9f624c5ea0252a1e13f2f60df5f9`.
- Final `bootstrap_spec.py` SHA-256:
  `cf3718770822450c7ce5278637c978778dca4658f2d19c2165583b2a2a16ef69`.

Both scoped diffs cover only `scripts/bootstrap.sh` and
`scripts/bootstrap_spec.py`, relative to HEAD. The executed bootstrap bytes did
not change after the container run. The report itself is not included in those
diff hashes. The earlier report's snapshot describes its own revision.

| Check | Exact result |
| --- | --- |
| Scoped pytest command below | Exit 0; 21 passed in 3.35s |
| Scoped Ruff check below | Exit 0; all checks passed |
| Scoped Ruff format check below | Exit 0; one file already formatted |
| `sh -n scripts/bootstrap.sh` | Exit 0 |
| `markdownlint --fix guidance/linux-onboarding-validation.md` | Exit 0 |
| `markdownlint guidance/linux-onboarding-validation.md` | Exit 0 |

The scoped Python check commands were:

```sh
uv run --no-sync pytest scripts/bootstrap_spec.py -q
uv run --no-sync ruff check scripts/bootstrap_spec.py
uv run --no-sync ruff format --check scripts/bootstrap_spec.py
```

The shell tests use an executable allowlist without host curl, apt, sudo, uv,
or Homebrew. Controlled executables exercise root and non-root installation,
apt update and install failures, absent apt, absent sudo, denied sudo, existing
uv, Homebrew, help, and the prior bootstrap behavior through `/bin/sh`.
No real host package installation occurs in these tests. `--no-sync` uses the
existing project environment without changing concurrent workers' dependencies.
The repository-wide test suite and coverage gate were not run for this scoped
correction.

Reproduce the container check from the repository root with:

```sh
python3 local/research/linux-bootstrap-fix/validate.py
```

Ignored evidence under `local/research/linux-bootstrap-fix/` contains the driver,
installer wrapper, executed bootstrap copy, container-capture `correction.diff`,
and `snapshot.json`. `build/linux-bootstrap-fix/commands.json` records the exact
Docker commands, exit statuses, and log names. The same directory holds fresh
state and install logs, real uv version, recorded sync call, check logs,
`final-correction.diff`, and `final-snapshot.json`. No commits, pushes, stashes,
or subagents were used for this correction.
