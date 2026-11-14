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
availability with `uv run python scripts/doctor.py`.
The check reports paths, returns nonzero for missing executables, and does not
launch XRoar or modify a disk. Set `LWASM`, `LWLINK`, `DECB`, or `XROAR`
to a particular executable path when needed. Use those same resolved paths in
project build commands. Do not copy a developer's private paths into defaults.

## Installation sources

On macOS, Homebrew supplies LWTOOLS and XRoar:

```sh
brew install lwtools xroar
```

Use the upstream instructions for ToolShed. On Linux, use a suitable
distribution package where available or the upstream build instructions. The
starter does not yet automate native-tool installation.

- [LWTOOLS downloads and build instructions](https://www.lwtools.ca/)
- [ToolShed documentation](https://toolshed.sourceforge.net/ToolShed.html)
- [XRoar downloads](https://www.6809.org.uk/xroar/)
- [XRoar build and configuration manual](https://www.6809.org.uk/xroar/doc/xroar.shtml)

## Verify the actual workflow

Finding an executable does not prove a working build. Assemble an original
small program, inspect its load address, then build and inspect its disk image.
For Disk BASIC, use the DECB binary format and test `LOADM` from the disk.
Read [development.md](development.md) for memory and evidence requirements.

XRoar requires matching firmware. Keep ROMs in ignored local storage or use
an explicit user-provided location. Record machine, RAM, video standard, CPU,
and ROM selection in the project configuration before running. A CPU simulator
cannot validate keyboard, graphics, disk, or ROM behavior. Emulator results do
not establish physical hardware timing.

Use [python.md](python.md) when adding build orchestration or test scripts.
