"""Build and check original byte-aligned masked objects on CoCo 1/2 NTSC."""

import argparse
import json
import re
import subprocess
from pathlib import Path

from coco import Host
from native import ROOT
from roms import verify_installed

executable = Host().executable

ROM_NAMES = {"coco1": ("bas11.rom", "extbas10.rom"), "coco2": ("bas12.rom", "extbas11.rom")}
# Scene input specification, independently expressed in PIXEL coordinates.
SCENES = (
    (0, 0, 240, 182, False, "ab"),
    (240, 0, 0, 182, False, "ab"),
    (112, 88, 120, 88, False, "ab"),
    (112, 88, 120, 88, False, "ba"),
    (112, 88, 112, 88, False, "ab"),
    (112, 88, 112, 88, False, "ba"),
    (16, 20, 216, 160, False, "ab"),
    (16, 20, 216, 160, False, ""),
    (112, 88, 120, 88, True, "ab"),
    (112, 88, 120, 88, True, "ba"),
    (112, 88, 120, 88, True, ""),
    (0, 182, 240, 0, True, "ab"),
)


def build() -> tuple[Path, dict[str, int]]:
    output = ROOT / "build/masked-objects"
    output.mkdir(parents=True, exist_ok=True)
    binary = output / "masked-objects.bin"
    symbols = output / "symbols.txt"
    subprocess.run(
        [
            executable("lwasm"),
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
            str(ROOT / "examples/masked-objects/main.asm"),
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
        raise ValueError("Program overlaps reserved stack.")
    return binary, addresses


def emulator(target: str) -> list[str]:
    basic, extended = ROM_NAMES[target]
    roms = verify_installed(ROOT, target, (basic, extended))
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


def ring_pixel(x: int, y: int, name: str) -> int | None:
    """Geometric oracle: None is transparent, zero is opaque black."""
    if not (0 <= x < 16 and 1 <= y <= 8):
        return None
    if y == 1:
        return int(name == "a")
    if y == 8:
        return int(name == "b")
    if x in (0, 15):
        return int((x == 0) == (name == "a"))
    return None


def expected_screen(scene: int) -> bytes:
    ax, ay, bx, by, invert, order = SCENES[scene]
    origins = {"a": (ax, ay), "b": (bx, by)}
    result = bytearray(6144)
    for y in range(192):
        for x in range(256):
            pixel = ((x // 8 + y // 8) % 2) ^ invert
            for name in order:
                left, top = origins[name]
                ink = ring_pixel(x - left, y - top, name)
                if ink is not None:
                    pixel = ink
            if pixel:
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def verify_ram(data: bytes, symbols: dict[str, int], scene: int) -> None:
    if len(data) != 32768:
        raise ValueError("Expected a 32 KiB RAM snapshot.")
    if (data[0x3FF], data[0x1C00]) != (0xA5, 0xA5):
        raise ValueError("Framebuffer guards damaged.")
    if data[symbols["scene"]] != scene:
        raise ValueError("Wrong scene checkpoint.")
    if data[0x400:0x1C00] != expected_screen(scene):
        raise ValueError("Framebuffer differs from independent pixel oracle.")


def capture(binary: Path, symbols: dict[str, int], target: str, scene: int) -> bytes:
    snapshot = binary.with_name(f"{target}-{scene}.ram")
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
        "20",
        "-trap",
        f"pc=0x{symbols['state']:x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        str(scene + 1),
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0",
        "-run",
        str(binary),
    ]
    with binary.with_name(f"{target}-{scene}.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    if negative.exists():
        raise ValueError("Unreachable data trap fired.")
    if not snapshot.exists():
        raise ValueError(f"{target} did not reach scene {scene}.")
    return snapshot.read_bytes()


def check(binary: Path, symbols: dict[str, int], target: str) -> dict[str, object]:
    for scene in range(len(SCENES)):
        verify_ram(capture(binary, symbols, target, scene), symbols, scene)
    return {
        "target": target,
        "machine": "cocous",
        "vdg": "6847",
        "cpu": "6809",
        "ram_kib": 32,
        "clock": "normal",
        "video": "NTSC",
        "roms": list(ROM_NAMES[target]),
        "scenes": len(SCENES),
        "framebuffer_bytes_per_scene": 6144,
        "guards": "passed",
        "unreachable_trap": "passed",
        "visual": "not inspected",
        "physical_hardware": "not tested",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--target", choices=tuple(ROM_NAMES), default="coco1")
    options = parser.parse_args()
    evidence = ROOT / "build/masked-objects" / f"{options.target}-results.json"
    if options.action == "check":
        evidence.unlink(missing_ok=True)
    binary, symbols = build()
    if options.action == "run":
        subprocess.run(emulator(options.target) + ["-ratelimit", "-run", str(binary)], check=True)
        return
    result = check(binary, symbols, options.target)
    evidence.write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS: {options.target}, {len(SCENES)} scenes, pixels, guards and unreachable trap.")
    print("Visual appearance and physical hardware remain untested.")


if __name__ == "__main__":
    main()
