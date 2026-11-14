"""Check CoCo executables and optional target firmware without launching XRoar."""

import argparse
import os
import shutil
import sys

from native import ROOT, tool_path
from roms import verify_installed

TOOLS = {
    "lwasm": ("LWASM", "LWTOOLS assembler"),
    "lwlink": ("LWLINK", "LWTOOLS linker"),
    "decb": ("DECB", "ToolShed Disk BASIC disk utility"),
    "xroar": ("XROAR", "XRoar machine emulator"),
}


class ExecutableGateway:
    """Resolve explicit environment overrides or search PATH."""

    def find(self, command: str, variable: str) -> str | None:
        return (
            tool_path(command)
            if command != "decb"
            else shutil.which(os.environ.get(variable, command))
        )


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
        choices=("coco1", "coco2", "coco3"),
        help="also validate installed firmware for this machine",
    )
    options = parser.parse_args(argv)
    executables = executables or ExecutableGateway()
    print(f"Python: {sys.executable}")
    missing = []
    for command, (variable, purpose) in TOOLS.items():
        executable = executables.find(command, variable)
        if executable:
            print(f"{command}: {executable} ({purpose})")
        else:
            print(f"{command}: missing ({purpose}); set {variable} or add it to PATH")
            if options.profile == "demo" and command == "decb":
                print("  Optional for this demo; only needed to build disk images.")
            else:
                missing.append(command)
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
        print("Firmware NOT checked. Add --target coco1, coco2, or coco3 before launching XRoar.")
    print("Discovery and file checks do not prove boot. Run the selected example's check command.")
    if missing:
        print("Setup is incomplete. Ask your agent to install: " + ", ".join(missing))
        print(
            "On Apple Silicon macOS, Homebrew provides assembly and emulator tools: brew install lwtools xroar"
        )
    print("Read guidance/starter/toolchain.md for installation and verification.")
    return 1 if missing or not firmware_ok else 0


if __name__ == "__main__":
    sys.exit(main())
