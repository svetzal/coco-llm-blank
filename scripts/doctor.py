"""Report CoCo executables without launching an emulator or modifying disks."""

import argparse
import os
import shutil
import sys

from native import tool_path

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
    print("This checks executable discovery only, not ROMs or build/run compatibility.")
    if missing:
        print("Setup is incomplete. Ask your agent to install: " + ", ".join(missing))
        print("On macOS, Homebrew provides assembly and emulator tools: brew install lwtools xroar")
    print("Read guidance/toolchain.md for installation and verification.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
