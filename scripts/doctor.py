"""Check CoCo executables and optional target firmware without launching XRoar."""

import argparse
import sys

import instrumented_xroar
from native import ROOT, VARIABLES, tool_path
from roms import TARGETS, verify_installed

TOOLS = {
    "lwasm": "LWTOOLS assembler",
    "lwlink": "LWTOOLS linker",
    "decb": "ToolShed Disk BASIC disk utility",
    "xroar": "XRoar machine emulator",
}


class ExecutableGateway:
    """Resolve overrides, project tools, PATH and Apple Silicon Homebrew, as the installer does."""

    def find(self, command: str) -> str | None:
        return tool_path(command)


def main(argv: list[str] | None = None, *, executables: ExecutableGateway | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("all", "demo"),
        default="all",
        help="demo checks assembly and emulator tools; all also requires disk tools",
    )
    parser.add_argument(
        "--target",
        choices=TARGETS,
        help="also validate installed firmware for this machine",
    )
    options = parser.parse_args(argv)
    executables = executables or ExecutableGateway()
    print(f"Python: {sys.executable}")
    missing = []
    for command, purpose in TOOLS.items():
        executable = executables.find(command)
        if executable:
            print(f"{command}: {executable} ({purpose})")
        else:
            print(f"{command}: missing ({purpose}); set {VARIABLES[command]} or add it to PATH")
            if options.profile == "demo" and command == "decb":
                print("  Optional for this demo; only needed to build disk images.")
            else:
                missing.append(command)
    print(
        "Instrumented XRoar (optional; screen, key and sound capture): "
        + instrumented_xroar.status(ROOT)
    )
    firmware_ok = True
    if options.target:
        try:
            paths = verify_installed(ROOT, options.target)
            for name, path in paths.items():
                print(f"Firmware verified: {name}: {path}")
        except ValueError as error:
            print(str(error))
            firmware_ok = False
    else:
        print(
            "Firmware NOT checked. Add --target with one of "
            + ", ".join(TARGETS)
            + " before launching XRoar."
        )
    print("Discovery and file checks do not prove boot. Run the selected example's check command.")
    if missing:
        print("Setup is incomplete. Ask your agent to install: " + ", ".join(missing))
        print(
            "Run uv run python scripts/native.py. It installs LWTOOLS and XRoar, and builds "
            "ToolShed from a pinned source release into local/toolchain/."
        )
    print("Read guidance/starter/toolchain.md for installation and verification.")
    return 1 if missing or not firmware_ok else 0


if __name__ == "__main__":
    sys.exit(main())
