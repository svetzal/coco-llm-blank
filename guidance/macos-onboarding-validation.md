# Apple Silicon onboarding validation

Read this when assessing first-run claims or rerunning the bounded setup checks.
macOS means Apple Silicon. Intel Mac support is excluded, not pending validation.

## What was measured

On November 14, 2026, current-host checks ran on macOS 27.2 (26B123), arm64,
using the existing project environment's CPython 3.13.12, uv, and Homebrew
LWASM. No tools were installed, permissions changed, GUI opened, or agent
trial started. No shared production scripts were changed by this test task.

This is isolated-workspace evidence on a configured Mac. It is **not clean-host
proof**. The Python environment, interpreter, assembler, account, permissions,
and system configuration already existed. Temporary projects do not remove
those dependencies. No full bootstrap or native installation was attempted.

The reusable [boundary checks](../experiments/macos-onboarding/onboarding_spec.py)
add recovery sequences through real setup and launcher subprocesses, rather
than another static audit. They copy source into paths containing spaces and
run commands from outside those project directories. Fixture ROMs are original
arbitrary bytes with independent manifest checksums, not working firmware.
A recording executable replaces XRoar. LWASM itself runs for launcher checks.

## Results

Five new tests passed in 9.63 seconds:

- Project notes survive a conflicting target request unchanged; the request
  fails, then setup succeeds for the original target without converting books.
- A missing Extended BASIC member is restored from a verified ZIP. Different
  installed BASIC bytes cause failure without replacement or partial repair;
  deliberate removal of the damaged fixture allows recovery.
- A damaged ZIP is preserved and rejected before publishing members. Restoring
  the verified fixture allows setup to finish. An unlisted traversal member
  is never extracted.
- Launcher help and invalid arguments cause no build or launch. Missing and
  same-length corrupt Extended BASIC bytes prevent the recording executable
  from running. After repair, the real launcher invokes it with absolute ROM
  paths, the CoCo 1 profile, and 32 KiB RAM.
- A real loopback HTTP response with incorrect bytes leaves no partial PDF.
  Correcting the server response allows retry; the verified cache remains
  usable after the server stops. This fixture checks transport and caching,
  not PDF parsing or OCR.

The existing scoped suite passed **174 tests, with one integration test
explicitly deselected**, in 18.53 seconds. It covered bootstrap, setup, ROMs,
native tools, and the first-screen helper. Its installer tests use substitutes;
passing them does not prove Homebrew or uv installation. The deselected test
would run the real emulator. No complete-suite coverage claim is made.

The initial new-test invocation produced five fixture setup errors because
`build/macos-onboarding/` did not exist. No application checks ran in that
attempt. Creating the evidence parent directory fixed the invocation.

Scoped Ruff lint and format checks passed. Markdownlint fix and check passed
for this document. Generated workspaces and the discovery probe are under
ignored `build/macos-onboarding/`; no downloaded material is tracked.

## Concrete defect for the installer owner

With `PATH=/usr/bin:/bin` and executable overrides removed, a read-only probe
on this arm64 Mac observed:

- `HostGateway.brew()` returns `/opt/homebrew/bin/brew`.
- `/opt/homebrew/bin/lwasm`, `lwlink`, and `xroar` are executable.
- `native.tool_path()` returns `None` for all three in an empty project.

The recorded output is `build/macos-onboarding/path-probe.json`. To reproduce
without allowing any installation, use the already installed interpreter:

```sh
uv run --no-sync python - <<'PY'
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
import native

assert Path('/opt/homebrew/bin/brew').is_file()
os.environ['PATH'] = '/usr/bin:/bin'
for variable in ('LWASM', 'LWLINK', 'XROAR'):
    os.environ.pop(variable, None)
print('Homebrew:', native.HostGateway().brew())
for name in ('lwasm', 'lwlink', 'xroar'):
    print(name, os.access('/opt/homebrew/bin/' + name, os.X_OK),
          native.tool_path(name, Path('build/macos-onboarding/empty-project')))
PY
```

The code inspected calls Homebrew by absolute path but does not make its bin
folder discoverable to the later tool check. The measured defect is executable
discovery. The predicted consequence is unnecessary installation attempts and
then a discovery failure when Homebrew is absent from the agent's inherited
PATH, including after a fresh Homebrew install. That installation sequence was
**not executed**. Route the fix to `scripts/native.py` and check bootstrap's
separate Homebrew lookup in `scripts/bootstrap.sh`. Preserve explicit overrides
and local tools while fixing discovery. A regression should cover tools
becoming discoverable in the same process without shell-profile reloads.

## Discovery correction

The parent corrected the measured discovery defect after this audit. On native
Apple Silicon macOS, tool discovery now checks `/opt/homebrew/bin` after
explicit overrides, project-local tools and PATH. A broken explicit override
still fails rather than silently selecting another tool. Linux and Intel
processes do not use this fallback.

The focused native, doctor and non-integration first-screen run passed 43 tests
with one integration test deselected. Regression checks create executable tools
after an initial miss, resolve and execute them without a shell-profile reload,
and verify that existing tools avoid installation. A separate read-only probe
on this Mac removed Homebrew from PATH and resolved all three installed tools
under `/opt/homebrew/bin`. No installer ran. This closes the observed discovery
defect, not the clean-host installation gap. Independent review also corrected
the audit launcher prerequisite to use the same discovery helper. All five
audit tests then passed with PATH restricted to `/usr/bin:/bin` in 10.95 seconds.

## Reproduction and scope

From the repository root, with its dependencies and LWASM already available:

```sh
mkdir -p build/macos-onboarding
uv run --no-sync pytest -q experiments/macos-onboarding/onboarding_spec.py \
  --basetemp=build/macos-onboarding/pytest
uv run --no-sync pytest -q scripts/bootstrap_spec.py scripts/setup_spec.py \
  scripts/roms_spec.py scripts/native_spec.py scripts/first_screen_spec.py \
  -m 'not integration' --basetemp=build/macos-onboarding/existing
uv run --no-sync ruff check experiments/macos-onboarding
uv run --no-sync ruff format --check experiments/macos-onboarding
markdownlint --fix guidance/macos-onboarding-validation.md
markdownlint guidance/macos-onboarding-validation.md
```

`--no-sync` intentionally prevents changing the user's Python environment.
Pytest replaces each named basetemp directory on rerun; these paths are reserved
for this experiment. Do not point them at an existing project. Commands read
working-tree source, including concurrent workers' edits. The copied scripts
in each retained workspace identify what that workspace exercised; the batch
is not a transactional snapshot or a committed-release certification.

## Remaining clean-host evidence

A clean-host claim needs a disposable Apple Silicon macOS machine or VM with
a documented initial state, not another folder on this Mac. It must establish
which prerequisites are absent, including Homebrew, uv, managed Python, native
tools, project environments, ROMs, and conversion caches. Run the actual
bootstrap as an ordinary account, capture permission failures and later
recovery, and verify tool discovery from the original agent environment.
Do not pre-seed tools or caches and then call that a clean first run.

After bootstrap, validate real manifest ROMs and run a headless example with
an independent state oracle and an unreachable-checkpoint control. Preserve
owner notes through reruns. Separately validate first reference conversion
and model downloads if claiming that workflow. Real upstream download
availability, TLS/certificates, Homebrew dependencies, developer tools, and
installation permissions remain untested by this run.

This report makes no boot, framebuffer, GUI, audio, physical-hardware, disk
loading, or OCR claims. No clean-host work was launched or queued here.
