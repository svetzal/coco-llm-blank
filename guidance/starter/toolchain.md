# CoCo development toolchain

Load this file before you assemble, compile, build disk images, or launch an
emulator. First read the project's contract in `projects/<name>/README.md`.
Do not infer RAM, video standard, or firmware from whatever is installed.

## Tool roles

| Tool | Executable | Purpose |
| --- | --- | --- |
| LWTOOLS | `lwasm`, `lwlink` | 6809 assembly and linking |
| ToolShed | `decb` | Disk BASIC disk image creation and inspection |
| XRoar | `xroar` | CoCo machine emulation |

These are host executables, separate from the uv Python environment. Check
availability with `uv run python scripts/doctor.py`.

For an emulator demo that you launch directly, use `--profile demo`.
This profile treats ToolShed as optional.
Add `--target coco1`, `--target coco2`, or `--target coco3` to validate firmware
as well.
Without a target, the doctor explicitly reports that firmware is unchecked.

The check reports paths. It returns nonzero for missing executables or invalid
selected firmware. It does not launch XRoar or modify a disk.

Set `LWASM`, `LWLINK`, `DECB`, or `XROAR` to a particular executable path when
needed. Use those same resolved paths in project build commands.
Do not copy a developer's private paths into defaults.

## Installation sources

Bootstrap runs `uv run python scripts/native.py` to install missing tools.
macOS support is limited to Apple Silicon (arm64). Intel Macs are unsupported.

Bootstrap and the native installer reject non-arm64 macOS before they install
anything, even when tools are already present.
On Apple Silicon, run a native arm64 terminal and Python rather than an x86-64
process under Rosetta.

Use Ubuntu 24.04 for the supported installation path on Linux.
Its architecture handling is unchanged.

On Apple Silicon macOS it uses Homebrew. If needed, it installs Homebrew from
its official source.
Existing Homebrew discovery through PATH and known prefixes is preserved.

System permissions may need the owner's help. Failures stop with an
explanation.
Existing tools and explicit executable overrides are preserved.

On native Apple Silicon macOS, tool discovery also checks `/opt/homebrew/bin`
when PATH does not include it.
It does this check after it checks overrides, project-local tools and PATH.

On Ubuntu 24.04, it installs build dependencies with apt. It builds verified
LWTOOLS and XRoar release archives into `local/toolchain/`.

A non-root account needs sudo permission for apt. The installer uses
non-interactive sudo and stops if permission is unavailable.
It never asks an agent to collect a password.
Reruns reuse working executables and check cached source archives.

When uv, Homebrew and curl are all missing, bootstrap installs curl and CA
certificates with apt. It uses the same non-interactive sudo. If sudo needs a
password or refuses the command, bootstrap stops before it installs uv.

Do not ask the owner for a password. Tell the owner that an administrator must
give the account non-interactive sudo access for apt. Alternatively, the
administrator can install `curl` and `ca-certificates`. Then run bootstrap
again. Bootstrap does not change the folders in `projects/`.

`doctor.py` and `coco.py` find the local tools without shell profile
changes. For custom commands, use the paths that the doctor reports, or add
`local/toolchain/bin` to PATH.

ToolShed installation is still separate. Only disk images need it.
Other Linux distributions need manual installation.

- [LWTOOLS downloads and build instructions](https://www.lwtools.ca/)
- [ToolShed documentation](https://toolshed.sourceforge.net/ToolShed.html)
- [XRoar downloads](https://www.6809.org.uk/xroar/)
- [XRoar build and configuration manual](https://www.6809.org.uk/xroar/doc/xroar.shtml)

## Measured setup results

On November 14, 2026, setup journeys ran in new Ubuntu 24.04.5 ARM64
containers. The host was an Apple Silicon Mac with Docker 29.8.2. A digest
pinned the Ubuntu image. These results came from the bootstrap of that date.

As root, the bare image first stopped because curl was missing. Bootstrap now
installs curl. After that change, a full bootstrap took 796 seconds.

An ordinary account with `NOPASSWD` sudo completed bootstrap in 1,138 seconds.
Without sudo, bootstrap stopped in 0.08 seconds and gave the administrator
message. In two more containers, sudo needed a password or denied the command.
Bootstrap stopped in less than 0.1 seconds and installed nothing. After the
administrator changed the policy, bootstrap completed in 1,189 and 542 seconds.

Each completed journey then passed the doctor for CoCo 2 and the CoCo 2
moving-objects check. The two sudo journeys also passed an earlier
collect-room check on CoCo 2. A second bootstrap took less than 1.1 seconds.
It kept an edited project note byte for byte.

Most of the time went to the first download of 130 Python packages, with a
5.9 GiB uv cache. The versions were uv 0.13.8, Python 3.13.18, LWTOOLS 4.25
and XRoar 1.12.1.

On the same date, recovery checks ran on a configured Apple Silicon Mac with
macOS 27.2. They used temporary project folders and fixture ROMs, not a clean
host. They found that tool discovery missed `/opt/homebrew/bin` when PATH did
not include it. A later change fixed that defect, and `native_spec.py` checks
the fix.

These results do not show a clean Apple Silicon Mac, a native Linux desktop,
x86-64 Linux, other distributions or an interrupted apt. They do not show a
GUI, audio or physical hardware. The scripts changed after these runs, and
nobody ran the containers again.

The root suite checks the same failures and recoveries with substitute
commands. `bootstrap_spec.py` covers sudo and apt. `roms_spec.py` and
`coco_spec.py` cover firmware.

## Verify the actual workflow

Finding an executable does not prove a working build. Assemble an original
small program. Inspect its load and execution addresses.

Build and inspect a disk image only when the project needs one.
For Disk BASIC, use the DECB binary format. Test `LOADM` from the disk.
Read [development.md](development.md) for memory and evidence requirements.

## Firmware and launching

XRoar needs matching firmware even when it auto-runs a DECB binary.
Bootstrap downloads the firmware. For an existing checkout, run setup with the
selected target:

```sh
uv run python scripts/setup.py --target coco1 --roms-only
```

This command downloads the manifest's ZIP from the
[archive ROM directory](https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/).
It checks ZIP and member checksums and extracts only named ROMs.
It does not convert books.

Reruns validate the cache. A mismatch stops without replacing existing
firmware. Inspect a damaged file before you remove it and try again.

Before every new launch workflow, run:

```sh
uv run python scripts/doctor.py --profile demo --target coco1
```

Use the actual target. This command checks installed member sizes and SHA-256
hashes. It does not use file existence as proof of valid firmware.

`scripts/coco.py` does the same checks for the ROMs that a project's
`coco.toml` names before it starts XRoar. It passes their absolute paths.

The tool does not yet set up a Disk BASIC cartridge. Disk BASIC work needs
`disk11.rom` and a reviewed launch configuration.

Custom firmware needs an explicit, reviewed configuration and independent boot
validation.
Renaming different bytes to a manifest filename does not validate them.

| Target | Firmware directory | BASIC | Disk BASIC |
| --- | --- | --- | --- |
| CoCo 1 | `local/roms/coco1/` | `bas11.rom` | `disk11.rom` |
| CoCo 2 | `local/roms/coco2/` | `bas12.rom` | `disk11.rom` |
| CoCo 3 | `local/roms/coco3/` | `coco3.rom` | `disk11.rom` |

The starter does not use Extended Color BASIC on the CoCo 1 or CoCo 2. XRoar's
machine profiles load it by default, so `scripts/coco.py` passes `-no-extbas`.
Add an Extended BASIC ROM only when a project has a specific need for it.

The CoCo 3 profile supplies NTSC firmware. The CoCo 3 has one combined BASIC
image. XRoar loads it with `-extbas`.
Select appropriate user-provided firmware for a PAL CoCo 3.
The manifest does not yet include that variant.

For reference, `scripts/coco.py run` launches a CoCo 1 NTSC, 32 KiB project
with options equivalent to:

```sh
xroar -machine cocous -ram 32 \
  -bas local/roms/coco1/bas11.rom \
  -no-extbas \
  -no-cart -ratelimit -run build/demo.bin
```

Use the actual project's binary name and RAM requirement. For Disk BASIC,
replace `-no-cart` with `-cart rsdos -cart-rom local/roms/coco1/disk11.rom`.
Direct auto-run of a binary is not evidence that a disk boots or that `LOADM`
works.

Do not require ToolShed for a direct launch of a DECB binary.
Disk work needs ToolShed.
Read the installed XRoar help for other machine profiles and ROM options.

Keep ROMs in ignored local storage or use an explicit user-provided location.
Record machine, RAM, video standard, CPU, and ROM selection in the project
configuration before a run.

A CPU simulator cannot validate keyboard, graphics, disk, or ROM behavior.
Emulator results do not establish physical hardware timing.

Use [python.md](python.md) when you add build orchestration or test scripts.

## Instrumented XRoar

Scripted keys, rendered frames and mixer sound need a second XRoar. This is the
pinned XRoar release built from source with the patch series in
`scripts/xroar_patches/` applied.

`scripts/coco.py` builds it the first time that a project asks for one of
those abilities. The build goes into ignored
`local/toolchain/xroar-instrumented/`. The tool reuses it afterwards.

Bootstrap does not build it. `build`, `run` and a plain `check` keep using the
installed XRoar. Thus the beginner path needs no C compiler.
The doctor reports its state as an optional line that never changes its exit
code.

```sh
uv run python scripts/instrumented_xroar.py status
uv run python scripts/instrumented_xroar.py build
```

The build needs these tools (set `CC` or `MAKE` to choose others):

- A C compiler
- `make`
- Autoconf
- Automake
- `pkg-config`

The series adds its own source files to XRoar's `src/Makefile.am`. Thus the
build regenerates XRoar's build files with `autoreconf -fi` before it
configures.

It is configured without any window, audio driver or GUI toolkit, so it needs
no SDL, GTK or other library.
If a tool is missing, the build stops before it downloads anything and says
what to install:

- macOS: `xcode-select --install`, then `brew install autoconf automake pkgconf`.
- Ubuntu 24.04: `sudo apt-get install build-essential pkg-config autoconf automake`.

`scripts/xroar_patches/upstream.json` is the one XRoar pin. It holds these
items:

- The release version, its git tag and commit
- The base commit that the series is made against
- The URL and SHA-256 of the source archive

The native installer's Ubuntu build of the ordinary XRoar reads the same file.
On macOS, Homebrew supplies the ordinary XRoar, so its version can differ from
the pin. `uv run python scripts/xroar_upstream.py report` shows both versions.
When the pin moves, run `brew upgrade xroar`.

In guidance and example READMEs, write "the pinned XRoar" for a current claim.
Name a release only in a record of a measurement, such as "XRoar 1.12.1 passed
these checks". Do not edit that record when the pin moves. Add the new release
only after you run the check again on it.
The archive is cached under `local/toolchain-sources/` and must match the
pinned SHA-256.

The series is a set of `git format-patch` files exported with `--full-index`.
Thus each patch names every changed file by its exact git blob hash before and
after.

The build refuses a file whose bytes differ from the blob that the patch
expects. Thus a different XRoar release fails with a plain message instead of
a silently wrong patch.

`build.json` beside the build records these items:

- The release, tag, archive URL and hash
- The patch names and a hash of the whole series
- The hash of each patched or added file
- The commands
- The Autoconf and Automake versions
- The host
- The hash of the executable

Each use checks that record. When the pin, the series, a patched file or the
executable no longer match, the tool says why and rebuilds.

Set `XROAR_INSTRUMENTED` to an executable path to make `scripts/coco.py` use
that instrumented XRoar instead. The tool does not check it.
The XRoar patch procedure uses it to run the same checks against a trial build.

To move the series to a new XRoar release, or to change the equipment, obey
[the XRoar patch procedure](xroar-patch.md). Run
`uv run python scripts/xroar_upstream.py report` to see how far the pin is
behind upstream.

## Diagnose binary startup

For an LWASM DECB program that you launch directly, give the entry label
explicitly with `end start` (where `start` is your entry label).
`org` selects placement. It does not supply the execution address.
Inspect both records in the emitted binary.

XRoar's log name "RS-DOS BIN" is compatible with this DECB output. It is not
evidence that you should invent a different header or byte order.

Use an explicit hexadecimal prefix in XRoar traps, such as `pc=0x3005`.
Derive the address from the current build's symbols.
Put the overall timeout before the PC trap.
Attach snapshot actions after that trap.

Allow ROM boot and binary loading to finish. A fraction-of-a-second trace of
ROM initialization does not establish an infinite loop.
For a bounded headless check:

```sh
xroar -ui null -machine cocous -ram 32 \
  -bas local/roms/coco1/bas11.rom \
  -no-extbas \
  -no-cart -no-ratelimit -timeout 10 \
  -trap "pc=$READY_ADDRESS" -trap-snap build/ready.ram \
  -trap-timeout 0.01 -run build/demo.bin
```

Set `READY_ADDRESS` to the actual checkpoint address, including `0x`.
Remove any stale snapshot first. Check its size and known state bytes.
Also check that an unreachable trap produces no snapshot.

Keep a host timeout around the emulator. A raw `.ram` dump supports memory
checks, not visual claims.

A checkerboard is not a successful boot check or a diagnosis by itself.
Missing or zero-filled ROMs can leave XRoar running without reaching the
program.

In a bounded local probe, both cases returned exit code zero without the
ready checkpoint of first-screen.
Do not treat a process exit as boot evidence.

When a probe fails, validate firmware bytes and explicit command paths first.
Then check entry point, address notation, trap ordering, and boot duration.
Change one variable per probe.

After repeated identical results, consult the installed manual. Record the
unresolved question. Do not restate a guess as a root cause.
