"""Build, check, or run original overlapping objects on a patterned background."""

import argparse
import json
import re
import subprocess
from pathlib import Path

from first_screen import executable
from native import ROOT
from roms import verify_installed

CHECK_FRAMES = (1, 15, 16, 17, 31, 32, 46, 64, 65, 185, 186, 369, 370)
ROM_NAMES = {"coco1": ("bas11.rom", "extbas10.rom"), "coco2": ("bas12.rom", "extbas11.rom")}


def build() -> tuple[Path, dict[str, int]]:
    output = ROOT / "build/moving-objects"
    output.mkdir(parents=True, exist_ok=True)
    binary = output / "moving-objects.bin"
    symbols = output / "symbols.txt"
    subprocess.run(
        [
            executable("lwasm"),
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
            str(ROOT / "examples/moving-objects/main.asm"),
        ],
        check=True,
    )
    addresses = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }
    if addresses["program_end"] >= 0x7E00:
        raise ValueError("Program overlaps the reserved stack.")
    return binary, addresses


def emulator(target: str) -> list[str]:
    basic, extended = ROM_NAMES[target]
    roms = verify_installed(ROOT, target, (basic, extended))
    # The NTSC CoCo architecture plus explicit VDG/firmware defines the model.
    # Do not use the CoCo 2B T1 default for the non-T1 board reference.
    return [
        executable("xroar"),
        "-machine",
        "cocous",
        "-vdg-type",
        "6847",
        "-machine-cpu",
        "6809",
        "-ram",
        "32",
        "-bas",
        str(roms[basic]),
        "-extbas",
        str(roms[extended]),
        "-no-cart",
    ]


def position(frame: int) -> tuple[int, int]:
    """Closed-form reflected motion, independent of the assembly's direction state."""
    tick = frame - 1
    return 30 - abs(tick % 60 - 30), 184 - abs(tick % 368 - 184)


def expected_screen(frame: int) -> bytes:
    """Pixel-level scene specification; B is above A except every other 32 frames."""
    xbyte, top = position(frame)
    lefts = {"a": xbyte * 8, "b": (30 - xbyte) * 8}
    order = ("b", "a") if frame & 32 else ("a", "b")
    result = bytearray(6144)
    for y in range(192):
        for x in range(256):
            pixel = ((x // 8 + y // 8) % 2) ^ bool(frame & 64)
            for name in order:
                if lefts[name] <= x < lefts[name] + 16 and top <= y < top + 8:
                    pixel = name == "a"
            if pixel:
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def verify_ram(data: bytes, symbols: dict[str, int], frame: int) -> None:
    if len(data) != 32768 or (data[0x03FF], data[0x1C00]) != (0xA5, 0xA5):
        raise ValueError("Missing initialized RAM or damaged framebuffer guards.")
    count = int.from_bytes(data[symbols["frames"] : symbols["frames"] + 2], "big")
    actual_position = (data[symbols["xpos"]], data[symbols["ypos"]])
    if count != frame or actual_position != position(frame):
        raise ValueError("Movement state differs from the independent trajectory.")
    if data[0x400:0x1C00] != expected_screen(frame):
        raise ValueError("Framebuffer differs from the independent scene specification.")


def capture(binary: Path, symbols: dict[str, int], target: str, frame: int) -> bytes:
    snapshot = binary.with_name(f"{target}-{frame}.ram")
    negative = binary.with_name(f"{target}-unreachable.ram")
    snapshot.unlink(missing_ok=True)
    negative.unlink(missing_ok=True)
    command = emulator(target) + [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "60",
        "-trap",
        f"pc=0x{symbols['state']:x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        str(frame),
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0",
        "-run",
        str(binary),
    ]
    with binary.with_name(f"{target}-{frame}.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=60)
    if negative.exists():
        raise ValueError("Unreachable data checkpoint fired.")
    if not snapshot.exists():
        raise ValueError(f"{target} did not reach frame {frame}.")
    return snapshot.read_bytes()


def check(binary: Path, symbols: dict[str, int], target: str) -> dict[str, object]:
    for frame in CHECK_FRAMES:
        verify_ram(capture(binary, symbols, target, frame), symbols, frame)
    return {
        "target": target,
        "machine": "cocous",
        "vdg": "6847",
        "ram_kib": 32,
        "cpu": "6809",
        "clock": "normal",
        "video": "NTSC",
        "roms": list(ROM_NAMES[target]),
        "frames": list(CHECK_FRAMES),
        "screen_bytes_checked_per_frame": 6144,
        "unreachable_checkpoint": "passed",
        "visual": "not inspected",
        "physical_hardware": "not tested",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--target", choices=tuple(ROM_NAMES), default="coco1")
    options = parser.parse_args()
    binary, symbols = build()
    if options.action == "run":
        subprocess.run(emulator(options.target) + ["-ratelimit", "-run", str(binary)], check=True)
        return
    result = check(binary, symbols, options.target)
    binary.with_name(f"{options.target}-results.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(f"PASS: {options.target}; {len(CHECK_FRAMES)} frames; exact scene, motion and guards.")
    print("Display appearance and physical hardware remain untested.")


if __name__ == "__main__":
    main()
