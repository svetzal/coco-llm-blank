"""Build, check, or launch the original CoCo 1 first-screen example."""

import argparse
import re
import subprocess
from pathlib import Path

from native import ROOT, tool_path
from roms import verify_installed


def executable(name: str) -> str:
    path = tool_path(name)
    if not path:
        raise ValueError(f"Missing {name}; run uv run python scripts/native.py first.")
    return path


def build() -> tuple[Path, int]:
    output = ROOT / "build/first-screen"
    output.mkdir(parents=True, exist_ok=True)
    binary = output / "first-screen.bin"
    symbols = output / "symbols.txt"
    subprocess.run(
        [
            executable("lwasm"),
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
            str(ROOT / "examples/first-screen/main.asm"),
        ],
        check=True,
    )
    match = re.search(r"^ready\s+EQU\s+\$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE)
    if not match:
        raise ValueError("Assembler did not emit the ready checkpoint.")
    return binary, int(match[1], 16)


def emulator(binary: Path) -> list[str]:
    roms = verify_installed(ROOT, "coco1", ("bas11.rom", "extbas10.rom"))
    return [
        executable("xroar"),
        "-machine",
        "cocous",
        "-ram",
        "32",
        "-bas",
        str(roms["bas11.rom"]),
        "-extbas",
        str(roms["extbas10.rom"]),
        "-no-cart",
    ]


def expected_screen() -> bytes:
    """Independent pixel specification: perimeter and a centred 64-pixel square."""
    result = bytearray(6144)
    for y in range(192):
        for x in range(256):
            if x in (0, 255) or y in (0, 191) or (96 <= x < 160 and 64 <= y < 128):
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def verify_ram(data: bytes) -> None:
    if len(data) != 32768 or data[0x2FFF] != 0xA5:
        raise ValueError("The emulator did not reach the initialized program state.")
    if data[0x0400:0x1C00] != expected_screen():
        raise ValueError("The emulator screen bytes differ from the pixel specification.")


def check(binary: Path, ready: int) -> None:
    for name, address in (("ready", ready), ("unreachable", ready + 1)):
        snapshot = binary.parent / f"{name}.ram"
        snapshot.unlink(missing_ok=True)
        command = emulator(binary) + [
            "-ui",
            "null",
            "-ao",
            "null",
            "-ram-init",
            "set",
            "-no-ratelimit",
            "-timeout",
            "10",
            "-trap",
            f"pc=0x{address:04x}",
            "-trap-snap",
            str(snapshot),
            "-trap-timeout",
            "0.01",
            "-run",
            str(binary),
        ]
        subprocess.run(command, check=True, timeout=30, capture_output=True)
        if name == "ready":
            verify_ram(snapshot.read_bytes())
        elif snapshot.exists():
            raise ValueError("The unreachable checkpoint unexpectedly fired.")
    print("PASS: XRoar reached ready; all 6144 screen bytes match; negative control passed.")
    print("This is a memory check. Inspect the emulator window for visual correctness.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "check", "run"))
    action = parser.parse_args().action
    binary, ready = build()
    if action == "check":
        check(binary, ready)
    elif action == "run":
        subprocess.run(emulator(binary) + ["-ratelimit", "-run", str(binary)], check=True)
    else:
        print(binary)


if __name__ == "__main__":
    main()
