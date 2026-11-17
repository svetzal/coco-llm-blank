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
availability with `uv run python scripts/doctor.py`. The starter builds its
XRoar from source. Read [Instrumented XRoar](#instrumented-xroar).

For an emulator demo that you launch directly, use `--profile demo`.
This profile treats ToolShed as optional. Bootstrap installs ToolShed all the
same, because the `disk` command needs it.
Add `--target` with `coco1`, `coco2`, `coco2b` or `coco3` to validate firmware
as well.
Without a target, the doctor explicitly reports that firmware is unchecked.

The check reports paths. It returns nonzero for missing executables or invalid
selected firmware. It does not launch XRoar or modify a disk.

Set `LWASM`, `LWLINK`, `DECB`, or `XROAR` to a particular executable path when
needed. Use those same resolved paths in project build commands.
Do not copy a developer's private paths into defaults.

## Installation sources

Bootstrap runs `uv run python scripts/native.py` to install missing tools and
the packages that the XRoar build needs. Then it runs
`uv run python scripts/instrumented_xroar.py build` to build XRoar.
macOS support is limited to Apple Silicon (arm64). Intel Macs are unsupported.

Bootstrap and the native installer reject non-arm64 macOS before they install
anything, even when tools are already present.
On Apple Silicon, run a native arm64 terminal and Python rather than an x86-64
process under Rosetta.

Use Ubuntu 24.04 for the supported installation path on Linux.

On Apple Silicon macOS the installer uses Homebrew. If needed, it installs
Homebrew from its official source. Homebrew supplies LWTOOLS, Autoconf,
Automake, `pkg-config` and SDL2.

System permissions may need the owner's help. Failures stop with an
explanation.
The installer keeps existing tools and explicit executable overrides.

On native Apple Silicon macOS, tool discovery also checks `/opt/homebrew/bin`
when PATH does not include it.
It does this check after it checks overrides, project-local tools and PATH.

On Ubuntu 24.04, it installs build dependencies with apt. These include
Autoconf, Automake, `pkg-config`, and the SDL2, ALSA and PulseAudio development
files for XRoar. It builds a verified LWTOOLS release archive into
`local/toolchain/`.

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

Homebrew has no ToolShed formula. On both hosts, the installer builds a
ToolShed release from source into `local/toolchain/`. `native.py` pins the
release and the SHA-256 of its archive. The build leaves out `cocofuse`,
because that tool needs FUSE. `decb` and `os9` do not need it.

On macOS, the ToolShed build needs the Xcode Command Line Tools. The installer
asks `xcode-select -p`, because `/usr/bin/cc` and `/usr/bin/make` are present
without the tools. If the tools are missing, install them with
`xcode-select --install`. Then run the installer again.

A ToolShed failure does not stop bootstrap. Directly launched programs do not
need ToolShed. The installer gives the cause and continues. The doctor then
reports `decb` as missing.

Other Linux distributions need manual installation.

- [LWTOOLS downloads and build instructions](https://www.lwtools.ca/)
- [ToolShed documentation](https://toolshed.sourceforge.net/ToolShed.html)
- [XRoar downloads](https://www.6809.org.uk/xroar/)
- [XRoar build and configuration manual](https://www.6809.org.uk/xroar/doc/xroar.shtml)

## Supported hosts

Bootstrap supports Apple Silicon macOS and Ubuntu 24.04. On Ubuntu it needs
root, or an account with non-interactive sudo. Without that permission it
stops at once, installs nothing and gives the administrator message.

The first bootstrap can take 20 minutes. Most of that time is the first
download of the Python packages. Allow about 6 GiB for the uv cache. A later
bootstrap takes about one second and keeps the project notes.

The root suite checks the sudo, apt and firmware failures and their
recoveries with substitute commands. `bootstrap_spec.py` covers sudo and apt.
`roms_spec.py` and `coco_spec.py` cover firmware.

No check covers a complete bootstrap on a clean Apple Silicon Mac, a native
Linux desktop, x86-64 Linux, other distributions or an interrupted apt.

## Check the actual workflow

Finding an executable does not prove a working build. Assemble an original
small program. Inspect its load and execution addresses.

Build a disk image only when the project needs one. Use the `disk` command in
[Disk images](#disk-images). It tests `LOADM` from the disk.
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

`scripts/coco.py disk` sets up the Disk BASIC cartridge from the target's
`disk` ROM. Read [Disk images](#disk-images).

Custom firmware needs an explicit, reviewed configuration and independent boot
validation.
Renaming different bytes to a manifest filename does not validate them.

### Standard targets

The starter has four standard targets. Each target has a firmware profile with
the same name in `roms.json`. Setup, doctor and bootstrap accept these names.
Setup installs each profile in `local/roms/<target>/`.

| Target | Machine | XRoar machine | VDG | Color BASIC | Extended BASIC |
| --- | --- | --- | --- | --- | --- |
| `coco1` | CoCo 1, NTSC | `cocous` | MC6847 | 1.1, `bas11.rom` | 1.1, `extbas11.rom` |
| `coco2` | CoCo 2, NTSC | `cocous` | MC6847 | 1.2, `bas12.rom` | 1.1, `extbas11.rom` |
| `coco2b` | CoCo 2B, NTSC | `coco2bus` | MC6847T1 | 1.3, `bas13.rom` | 1.1, `extbas11.rom` |
| `coco3` | CoCo 3, NTSC | `coco3` | GIME 1986 | In `coco3.rom` | In `coco3.rom` |

Each profile also holds `disk11.rom`, Disk Extended Color BASIC 1.1. Each
target table names it with `disk`. Only the `disk` command loads it.

The CoCo 1 and CoCo 2 targets load Extended Color BASIC. Most real machines
have it, and the CoCo 3 ROM includes it. Extended BASIC turns on the
field-sync interrupt (IRQ) at each cold start. Thus a program starts in the
same machine state as on most real machines. A check without Extended BASIC
hides this interrupt.

Evidence for the interrupt:

- Bit 0 of `$FF03` enables the IRQ from the field-sync input. Source: Color
  Computer Technical Reference Manual (Tandy), PDF page 13.
- Measured in XRoar on `cocous` with `bas11.rom`: `$FF03` holds `$35` at the
  entry of a program with `extbas11.rom`. It holds `$34` without it.

The CoCo 3 has one combined BASIC image. XRoar loads it with `-extbas`.
The CoCo 3 profile supplies NTSC firmware. The manifest does not yet include
PAL firmware for the CoCo 3.

#### Target tables

Copy the table of the target into `coco.toml`. Examples and projects use these
tables. Examples leave out `disk`, because no example makes a disk image.
Change a value only when the project contract records a different machine.
Then record the reason in the contract.

```toml
[targets.coco1]
machine = "cocous"
cpu = "6809"
tv = "ntsc"
vdg = "6847"
ram_kib = 32
basic = "bas11.rom"
extended = "extbas11.rom"
disk = "disk11.rom"

[targets.coco2]
machine = "cocous"
cpu = "6809"
tv = "ntsc"
vdg = "6847"
ram_kib = 32
basic = "bas12.rom"
extended = "extbas11.rom"
disk = "disk11.rom"

[targets.coco2b]
machine = "coco2bus"
cpu = "6809"
tv = "ntsc"
vdg = "6847t1"
ram_kib = 32
basic = "bas13.rom"
extended = "extbas11.rom"
disk = "disk11.rom"

[targets.coco3]
machine = "coco3"
cpu = "6809"
tv = "ntsc"
vdg = "gime1986"
ram_kib = 128
extended = "coco3.rom"   # XRoar loads the single CoCo 3 ROM as -extbas
disk = "disk11.rom"
screen = 0x10400         # logical $0400 in the physical RAM snapshot
```

The table name selects the firmware profile. A table with a different name
must give the profile with `firmware = "<target>"`. Add `keyboard = "coco"`,
or `keyboard = "coco3"` on the CoCo 3, when a check sends keys.

#### A 6309 target

A target with `cpu = "6309"` runs on the Hitachi 6309. Set it only when the
project contract names the 6309. `scripts/coco.py` then makes these changes
for builds of that target:

- LWASM assembles with `--6309`, so it accepts the 6309 instructions.
- The build defines `H6309`. Put code for each CPU under `ifdef H6309`, so
  that one source can also build for a 6809 target.
- The build files end in `-6309`, such as `main-6309.bin`.

Every other target assembles with `--6809`, and a 6309 instruction stops the
build. A disk image serves all of its disk targets, so those targets must use
one CPU. Name one target with `--target` when they do not.

The 6309 starts in 6809 emulation mode. Its new instructions also run in that
mode. Bit 0 of the MD register selects native mode, which runs many
instructions in fewer cycles. In native mode an interrupt also stacks the W
register, so a handler that changes its return address at `10,S` must use
`12,S`. Source: *HD63B09EP Technical Reference Guide*, PDF 3, 5 and 7.

`DescribeThe6309InXRoar` in `scripts/coco_spec.py` checks a program that
stores the result of `LDW` on a 6309 target. Its control runs the same program
on a 6809, and the check fails. A 6309 target is not a stock CoCo 3: a stock
machine has a 6809, so it cannot run a program that uses 6309 instructions.

#### Firmware sources

The archive ZIP files are copies of the MAME ROM sets. The table gives the
CoCo 1 and CoCo 2 ROMs. Their CRC32 and SHA-1 agree with the MAME ROM
definitions in
[`src/mame/trs/coco12.cpp`](https://github.com/mamedev/mame/blob/518bb5e53379c124833415da5cb2d22d6acf845a/src/mame/trs/coco12.cpp).
Their CRC32 agrees with the ROM table in `src/rom.c` of XRoar 1.13. At launch,
XRoar gives the name of each image and marks none as a bad dump.

| ROM | SHA-256 | CRC32 | ZIP files |
| --- | --- | --- | --- |
| `bas11.rom` | `f772ee5e...` | `6270955a` | `coco.zip` |
| `bas12.rom` | `40413d0f...` | `54368805` | `coco2.zip` |
| `bas13.rom` | `5375b1ca...` | `d8f4d15e` | `coco2b.zip` |
| `extbas11.rom` | `a18f270d...` | `a82a6254` | `coco.zip`, `coco2.zip`, `coco2b.zip` |

`roms.json` holds the full checksums. Do not use `extbas10.rom`. XRoar marks
the archive copy as a bad dump.

For reference, `scripts/coco.py run` launches a project on the `coco1` target
with options equivalent to:

```sh
xroar -machine cocous -tv-type ntsc -vdg-type 6847 -ram 32 \
  -bas local/roms/coco1/bas11.rom \
  -extbas local/roms/coco1/extbas11.rom \
  -no-cart -ratelimit -run build/demo.bin
```

A target with no `extended` ROM gets `-no-extbas`. XRoar's machine profiles
otherwise search for an Extended BASIC ROM.

Use the actual project's binary name and RAM requirement. The `disk` command
replaces `-no-cart` with `-cart rsdos -cart-rom local/roms/coco1/disk11.rom`.
Direct auto-run of a binary is not evidence that a disk boots or that `LOADM`
works.

Do not require ToolShed for a direct launch of a DECB binary.
Disk work needs ToolShed.
For other machine profiles and ROM options, read the help of the
instrumented XRoar.

## Disk images

Use the `disk` command to put a project on a Disk BASIC disk image. The target
table must name the Disk BASIC ROM with `disk = "disk11.rom"`, as the
[target tables](#target-tables) do.

```sh
uv run python scripts/coco.py disk projects/<name>
uv run python scripts/coco.py disk projects/<name> --run
uv run python scripts/coco.py disk projects/<name> --check
```

- Without a flag, the command assembles the program. It writes a new image,
  `build/<name>/main.dsk`, and prints the path.
- With `--run`, XRoar opens at normal speed with the image in drive 0. XRoar
  types `LOADM"<NAME>":EXEC` and RETURN.
- With `--check`, XRoar boots the image without a window and types the same
  command. The program must reach the first `[check]` checkpoint before the
  unreachable label runs.

`--variant` selects a variant build, as for `build`. A variant key script is
not used on a disk boot.

The image holds one file, `<NAME>.BIN`. ToolShed's `decb dskini` formats a
blank image. `decb copy -2 -b` copies the DECB binary as a machine-language
file. Give the name in `coco.toml`:

```toml
[disk]
name = "ARENA"   # 1 to 8 capital letters or digits
```

Without `[disk]`, the command uses the first eight letters and digits of the
folder name in capitals. For `arena-blaster`, the name is `ARENABLA`.

### What the disk check shows

The disk check shows that Disk BASIC loaded the program and that the program
reached its checkpoint. It does not compare the screen or the model. The typed
command is on the screen, and `expected.py` does not describe it. Run `check`
for that evidence. The check uses `-no-disk-write-back`, so it does not change
the image.

The record of the check is `build/<name>/<target>-<build>-disk-results.json`.
The build is `main` or the variant name.

The check adds 10 emulated seconds to `[check] emulated_seconds` for the boot
and the load. The template needs 3 to 4 seconds.

Measured in the pinned XRoar with the `disk11.rom` of each profile:

- The template loads from a disk and reaches its checkpoint on `coco1`,
  `coco2`, `coco2b` and `coco3`.
- On `coco1` with Color BASIC and no Extended BASIC, Disk BASIC never runs the
  typed command. A disk target needs Extended BASIC.

`DescribeDisksInXRoar` in `scripts/coco_spec.py` repeats these checks.

### Memory for a disk program

Disk BASIC uses some RAM for its own work. The disk check measures only one
program. Before you place code or data for a disk program, find the RAM that
Disk BASIC uses in a reference. Cite it in the project contract. If no
reference settles it, open a lab.

A program that ran only without Extended BASIC can fail on a disk target.
Extended BASIC starts the field-sync interrupt, as
[Standard targets](#standard-targets) describes. Run `check` on a target with
Extended BASIC first. Then make the disk.

## Instrumented XRoar

The starter uses one XRoar, the instrumented XRoar. It is the pinned XRoar
release, built from source with the patch series in `scripts/xroar_patches/`
applied. Every `scripts/coco.py` command that starts XRoar uses it: `run`,
`check`, `snapshot`, `disk` and `record`. The patches add scripted keys,
rendered frames, mixer sound and the frame stream for videos.

Bootstrap builds it into ignored `local/toolchain/xroar-instrumented/`. If the
build is missing or out of date, `scripts/coco.py` builds it before it starts
XRoar. The doctor reports it as a required tool.

```sh
uv run python scripts/instrumented_xroar.py status
uv run python scripts/instrumented_xroar.py build
```

### Window, sound and joystick

The build has a window and host sound. SDL2 supplies the window on both hosts.
The configure step leaves out GTK and SDL3. On Ubuntu it adds
`--enable-ui-sdl`, because no GTK window is available.

After the build, the tool runs `xroar -ui help`. This command lists the window
modules and starts no window. If the list holds only the `null` module, the
tool stops and tells you what to install. The previous build stays in place.

Each check, snapshot, disk check and recording runs without a window and
without host sound, with `-ui null -ao null`. It also connects both joystick
ports to an empty joystick profile:

```sh
-joy none -joy-right none -joy-left none
```

Thus a gamepad on the host cannot change the evidence. Each port reads as a
joystick in the center position, with no button pushed. `run` and
`disk --run` keep the default joystick of XRoar. Thus a person can play with a
gamepad.

### Build tools

The build needs these tools (set `CC` or `MAKE` to choose others):

- A C compiler
- `make`
- Autoconf
- Automake
- `pkg-config`
- The SDL2 development files

`scripts/native.py` installs all of them except the C compiler. To install
them yourself:

- macOS: `xcode-select --install`, then
  `brew install autoconf automake pkgconf sdl2`.
- Ubuntu 24.04: `sudo apt-get install build-essential pkg-config autoconf
  automake libsdl2-dev libasound2-dev libpulse-dev`.

If a tool is missing, the build stops before it downloads anything and says
what to install.

The series adds its own source files to XRoar's `src/Makefile.am`. Thus the
build regenerates XRoar's build files with `autoreconf -fi` before it
configures.

### Pin and build record

`scripts/xroar_patches/upstream.json` is the one XRoar pin.
[The XRoar patch procedure](xroar-patch.md#what-the-series-is) lists what it
holds. Run `uv run python scripts/xroar_upstream.py report` to see how far the
pin is behind upstream.

In guidance and example READMEs, write "the pinned XRoar" for a current claim.
Name a release only where the claim depends on that release, such as a line
number in its source.
The archive is cached under `local/toolchain-sources/` and must match the
pinned SHA-256.

Each patch names every changed file by its exact git blob hash. The build
refuses a file whose bytes differ from that blob. Thus a different XRoar
release fails with a plain message instead of a silently wrong patch.

`build.json` beside the build records what the tool built and from which
sources. Each use checks that record. The tool rebuilds when one of these
items no longer matches, and it says which:

- the pin
- the series
- the configure options
- a patched file
- the executable

Set `XROAR` to an executable path to make `scripts/coco.py` use that XRoar
instead. The tool does not check it. It must hold every patch in the series.
The XRoar patch procedure uses it to run the same checks against a trial
build.

To move the series to a new XRoar release, or to change the equipment, obey
[the XRoar patch procedure](xroar-patch.md).

## Record a video

`record` runs a build from power-on for a number of emulated seconds. It
writes every frame that XRoar renders and the mixer sound into one HEVC video:

```sh
uv run python scripts/coco.py record <project-folder> --seconds 95
uv run python scripts/coco.py record <project-folder> --variant <name> --seconds 20
```

The command prints the path of the video, `build/<name>/<build>-<target>-record.mp4`.
The video shows the emulator's output only: no model draws a frame. Use it to
show a project to people. It is not a check: no expected result is compared.

- `--variant`, `--target` and `--keys` work as they do for `snapshot`.
  A variant's key script plays.
- The instrumented XRoar sends each frame to ffmpeg through a named pipe.
  Thus a long recording needs no disk space for frames.
- The emulator's clock sets the frame rate and the start of the picture
  against the sound. A CoCo field is about 59.92 frames each second.
- The picture is scaled by whole numbers to at least 768 lines and is shown
  at 4:3. The video uses the `hvc1` tag, so Apple players open it.
- A declared `unreachable` label stops the recording with a failure.

`record` needs ffmpeg with libx265. Set `FFMPEG` to use another executable.

- macOS: `brew install ffmpeg`.
- Ubuntu 24.04: `sudo apt-get install ffmpeg`.

Allow about one second of wall time for every 3 emulated seconds. Encoding
takes most of this time. `coco_spec.py` records `first-screen` on the CoCo 1
and the CoCo 3, and checks the codec, the size, the frame count and the
length of the sound.

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
  -extbas local/roms/coco1/extbas11.rom \
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
program. In both cases XRoar can return exit code zero.
Do not treat a process exit as boot evidence.

When a probe fails, validate firmware bytes and explicit command paths first.
Then check entry point, address notation, trap ordering, and boot duration.
Change one variable per probe.

After repeated identical results, consult the installed manual. Record the
unresolved question. Do not restate a guess as a root cause.
