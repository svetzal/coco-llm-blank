# CoCo development toolchain

Load this file before assembling, compiling, building disk images, or launching
an emulator. First read [the local target](../local/PROJECT.md). Do not infer
RAM, video standard, or firmware from whatever happens to be installed.

## Tool roles

| Tool | Executable | Purpose |
| --- | --- | --- |
| LWTOOLS | `lwasm`, `lwlink` | 6809 assembly and linking |
| ToolShed | `decb` | Disk BASIC disk image creation and inspection |
| XRoar | `xroar` | CoCo machine emulation |

These are host executables, separate from the uv Python environment. Check
availability with `uv run python scripts/doctor.py`. For a directly launched
emulator demo, use `--profile demo`; this treats ToolShed as optional.
Add `--target coco1`, `--target coco2`, or `--target coco3` to validate firmware
as well. Without a target, the doctor explicitly reports that firmware is
unchecked.
The check reports paths, returns nonzero for missing executables or invalid
selected firmware, and does not
launch XRoar or modify a disk. Set `LWASM`, `LWLINK`, `DECB`, or `XROAR`
to a particular executable path when needed. Use those same resolved paths in
project build commands. Do not copy a developer's private paths into defaults.

## Installation sources

Bootstrap runs `uv run python scripts/native.py` to install missing tools.
On macOS it uses Homebrew, installing Homebrew from its official source if
needed.
System permissions may require the owner's help; failures stop with an
explanation.
Existing tools and explicit executable overrides are preserved.

On Ubuntu 24.04, it installs build dependencies with apt and builds verified
LWTOOLS and XRoar release archives into `local/toolchain/`. A non-root account
needs sudo permission for apt. The installer uses non-interactive sudo and
stops if permission is unavailable. It never asks an agent to collect a
password.
Reruns reuse working executables and verify cached source archives.

`doctor.py` and `first_screen.py` find the local tools without shell profile
changes. For custom commands, use the paths reported by the doctor or add
`local/toolchain/bin` to PATH. ToolShed installation is still separate and is
needed only for disk images. Other Linux distributions need manual installation.

- [LWTOOLS downloads and build instructions](https://www.lwtools.ca/)
- [ToolShed documentation](https://toolshed.sourceforge.net/ToolShed.html)
- [XRoar downloads](https://www.6809.org.uk/xroar/)
- [XRoar build and configuration manual](https://www.6809.org.uk/xroar/doc/xroar.shtml)

## Verify the actual workflow

Finding an executable does not prove a working build. Assemble an original
small program and inspect its load and execution addresses. Build and inspect
a disk image only when the project needs one.
For Disk BASIC, use the DECB binary format and test `LOADM` from the disk.
Read [development.md](development.md) for memory and evidence requirements.

## Firmware and launching

XRoar requires matching firmware even when auto-running a DECB binary.
Bootstrap downloads it. For an existing checkout, run setup with the selected
target:

```sh
uv run python scripts/setup.py --target coco1 --roms-only
```

This downloads the manifest's ZIP from the
[archive ROM directory](https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/).
It verifies ZIP and member checksums and extracts only named ROMs. It does not
convert books. Reruns validate the cache; a mismatch stops without replacing
existing firmware. Inspect a damaged file before removing it and retrying.

Before every new launch workflow, run:

```sh
uv run python scripts/doctor.py --profile demo --target coco1
```

Use the actual target. This checks installed member sizes and SHA-256 hashes.
It does not use file existence as proof of valid firmware. The existing example
runners perform the same checks for the ROMs they need before starting XRoar.
For a new Python runner, use `roms.verify_installed(ROOT, target, names)` and
pass the returned absolute paths. Include `disk11.rom` when using Disk BASIC.
Custom firmware needs an explicit, reviewed configuration and independent boot
validation; renaming different bytes to a manifest filename does not validate
them.

| Target | Firmware directory | BASIC | Extended BASIC | Disk BASIC |
| --- | --- | --- | --- | --- |
| CoCo 1 | `local/roms/coco1/` | `bas11.rom` | `extbas10.rom` | `disk11.rom` |
| CoCo 2 | `local/roms/coco2/` | `bas12.rom` | `extbas11.rom` | `disk11.rom` |
| CoCo 3 | `local/roms/coco3/` | Combined | `coco3.rom` | `disk11.rom` |

The CoCo 3 profile supplies NTSC firmware; pass its combined BASIC image with
`-extbas`. Select appropriate user-provided
firmware for a PAL CoCo 3; the manifest does not yet include that variant.

For a CoCo 1 NTSC project targeting 32 KiB, a DECB binary can auto-run with:

```sh
xroar -machine cocous -ram 32 \
  -bas local/roms/coco1/bas11.rom \
  -extbas local/roms/coco1/extbas10.rom \
  -no-cart -ratelimit -run build/demo.bin
```

Use the actual project's binary name and RAM requirement. For Disk BASIC,
replace `-no-cart` with `-cart rsdos -cart-rom local/roms/coco1/disk11.rom`.
Direct binary auto-run is not evidence that a disk boots or that `LOADM` works.
Do not require ToolShed for a direct DECB binary launch; it is needed for disk
work. Read the installed XRoar help for other machine profiles and ROM options.

Keep ROMs in ignored local storage or use an explicit user-provided location.
Record machine, RAM, video standard, CPU,
and ROM selection in the project configuration before running. A CPU simulator
cannot validate keyboard, graphics, disk, or ROM behavior. Emulator results do
not establish physical hardware timing.

Use [python.md](python.md) when adding build orchestration or test scripts.

## Diagnose binary startup

For a directly launched LWASM DECB program, give the entry label explicitly
with `end start` (where `start` is your entry label). `org` selects placement;
it does not supply the execution address. Inspect both records in the emitted
binary. XRoar's log name "RS-DOS BIN" is compatible with this DECB output;
it is not evidence that you should invent a different header or byte order.

Use an explicit hexadecimal prefix in XRoar traps, such as `pc=0x3005`.
Derive the address from the current build's symbols. Put the overall timeout
before the PC trap and attach snapshot actions after that trap. Allow ROM boot
and binary loading to finish; a fraction-of-a-second trace of ROM initialization
does not establish an infinite loop. For a bounded headless check:

```sh
xroar -ui null -machine cocous -ram 32 \
  -bas local/roms/coco1/bas11.rom \
  -extbas local/roms/coco1/extbas10.rom \
  -no-cart -no-ratelimit -timeout 10 \
  -trap "pc=$READY_ADDRESS" -trap-snap build/ready.ram \
  -trap-timeout 0.01 -run build/demo.bin
```

Set `READY_ADDRESS` to the actual checkpoint address, including `0x`.
Remove any stale snapshot first. Check its size and known state bytes; also
check that an unreachable trap produces no snapshot. Keep a host timeout around
the emulator. A raw `.ram` dump supports memory checks, not visual claims.

A checkerboard is not a successful boot check or a diagnosis by itself.
Missing or zero-filled ROMs can leave XRoar running without reaching the
program.
In a bounded local probe, both cases returned exit code zero without the
first-screen ready checkpoint. Do not treat a process exit as boot evidence.

When a probe fails, validate firmware bytes and explicit command paths first.
Then check entry point, address notation, trap ordering, and boot duration.
Change one variable per
probe. After repeated identical results, consult the installed manual and
record the unresolved question instead of restating a guess as a root cause.
