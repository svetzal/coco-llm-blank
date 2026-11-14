"""Report CoCo executables without launching an emulator or modifying disks."""

import argparse
import os
import shutil
import sys

TOOLS = {
    "lwasm": ("LWASM", "LWTOOLS assembler"),
    "lwlink": ("LWLINK", "LWTOOLS linker"),
    "decb": ("DECB", "ToolShed Disk BASIC disk utility"),
    "xroar": ("XROAR", "XRoar machine emulator"),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    print(f"Python: {sys.executable}")
    missing = []
    for command, (variable, purpose) in TOOLS.items():
        configured = os.environ.get(variable, command)
        executable = shutil.which(configured)
        if executable:
            print(f"{command}: {executable} ({purpose})")
        else:
            print(f"{command}: missing ({purpose}); set {variable} or add it to PATH")
            missing.append(command)
    print("This checks executable discovery only, not ROMs or build/run compatibility.")
    print("Read guidance/toolchain.md for installation and verification.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
