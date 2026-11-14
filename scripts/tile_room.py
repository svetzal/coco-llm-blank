"""Build, check, or run an original, bounded CoCo 1/2 tile room."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from coco import Host
from native import ROOT
from roms import verify_installed

executable = Host().executable

OUTPUT = ROOT / "build/tile-room"
ROM_NAMES = {"coco1": ("bas11.rom", "extbas10.rom"), "coco2": ("bas12.rom", "extbas11.rom")}
ROOM = ("..#.....", ".*#..#..", "..#.....", "....##..", ".#......", "......E.")
# Specification of requested directions, not read from the assembly or RAM.
MOVES = "LURRDDDRURUUUURRDRRRDDDDDDLRLLLLLULULUUDU"
# Pixel drawings are independent of the packed assembly byte table.
ART = (
    ("........",) * 8,
    (
        "########",
        "#......#",
        "#......#",
        "########",
        "...##...",
        "...##...",
        "...##...",
        "########",
    ),
    (
        "........",
        "........",
        "...##...",
        "..####..",
        "..####..",
        "...##...",
        "........",
        "........",
    ),
    (
        ".######.",
        ".#....#.",
        ".#.##.#.",
        ".#.#..#.",
        ".#.##.#.",
        ".#....#.",
        ".######.",
        "........",
    ),
    (
        "...##...",
        "..####..",
        ".######.",
        "##.##.##",
        "########",
        "..#..#..",
        "..#..#..",
        ".##..##.",
    ),
)


def build() -> tuple[Path, dict[str, int]]:
    """Assemble fresh DECB and symbols, invalidating evidence before any failure."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.ram", "*.log", "*-results.json", "*.bin", "symbols.txt"):
        for path in OUTPUT.glob(pattern):
            path.unlink()
    binary, symbols = OUTPUT / "tile-room.bin", OUTPUT / "symbols.txt"
    subprocess.run(
        [
            executable("lwasm"),
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
            str(ROOT / "examples/tile-room/main.asm"),
        ],
        check=True,
    )
    addresses = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }
    if addresses["start"] != 0x3000 or addresses["program_end"] >= 0x7E00:
        raise ValueError("Program overlaps the memory reservation.")
    return binary, addresses


def emulator(target: str) -> list[str]:
    """Verify both firmware images before constructing a launch command."""
    basic, extended = ROM_NAMES[target]
    roms = verify_installed(ROOT, target, (basic, extended))
    return [
        executable("xroar"),
        "-c",
        "/dev/null",
        "-machine",
        "cocous",
        "-tv-type",
        "ntsc",
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


def expected_state(step: int) -> tuple[tuple[int, int], bytes, int]:
    """Walk a graph of passable cells, independent of assembly address arithmetic."""
    if not 0 <= step <= len(MOVES):
        raise ValueError("Checkpoint outside the scripted movement.")
    cells = {(x, y): value for y, row in enumerate(ROOM) for x, value in enumerate(row)}
    edges = {}
    for x, y in cells:
        for direction, neighbor in zip("RDLU", ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))):
            if cells.get(neighbor, "#") != "#":
                edges[(x, y), direction] = neighbor
    position, accepted = (0, 0), 0
    for direction in MOVES[:step]:
        next_position = edges.get((position, direction), position)
        accepted = int(next_position != position)
        position = next_position
        if cells[position] == "*":
            cells[position] = "."
    return position, bytes(".#*E".index(value) for value in cells.values()), accepted


def expected_screen(step: int) -> bytes:
    """Compose individual pixels across the entire framebuffer, including blank space."""
    actor, room, _ = expected_state(step)
    screen = bytearray(6144)
    for y in range(48):
        for x in range(64):
            cell = (x // 8, y // 8)
            tile = 4 if cell == actor else room[cell[1] * 8 + cell[0]]
            if ART[tile][y % 8][x % 8] == "#":
                screen[y * 32 + x // 8] |= 128 >> (x % 8)
    return bytes(screen)


def verify_ram(data: bytes, symbols: dict[str, int], step: int) -> None:
    """Check state, complete map, guards, and every screen byte at a checkpoint."""
    guards = (0x03FF, 0x1C00, symbols["map_guard_before"], symbols["map_guard_after"])
    if len(data) != 32768 or any(data[address] != 0xA5 for address in guards):
        raise ValueError("Missing RAM or damaged guards.")
    position, room, accepted = expected_state(step)
    observed = tuple(data[symbols[name]] for name in ("xpos", "ypos", "accepted", "step"))
    if observed != (*position, accepted, step):
        raise ValueError(f"Movement checkpoint {step} differs: {observed}.")
    if data[symbols["room"] : symbols["room"] + 48] != room:
        raise ValueError("Map state differs, including collected tile.")
    if data[0x0400:0x1C00] != expected_screen(step):
        raise ValueError("Framebuffer differs from the independent pixel scene.")


def capture(binary: Path, symbols: dict[str, int], target: str, step: int) -> bytes:
    """Capture one completed frame with an unreachable-trap negative control."""
    snapshot = binary.with_name(f"{target}-{step}.ram")
    negative = binary.with_name(f"{target}-unreachable.ram")
    for path in (snapshot, negative):
        path.unlink(missing_ok=True)
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
        f"pc=0x{symbols['room']:x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        str(step + 1),
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0",
        "-run",
        str(binary),
    ]
    with binary.with_name(f"{target}-{step}.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    if negative.exists():
        raise ValueError("Unreachable data checkpoint fired.")
    if not snapshot.exists():
        raise ValueError(f"{target} did not reach checkpoint {step}.")
    return snapshot.read_bytes()


def check(binary: Path, symbols: dict[str, int], target: str) -> None:
    """Save a success record only after every checkpoint passes."""
    result = binary.with_name(f"{target}-results.json")
    result.unlink(missing_ok=True)
    for pattern in (f"{target}-*.ram", f"{target}-*.log"):
        for path in binary.parent.glob(pattern):
            path.unlink()
    for step in range(len(MOVES) + 1):
        verify_ram(capture(binary, symbols, target, step), symbols, step)
    result.write_text(
        json.dumps(
            {
                "target": target,
                "machine": "cocous",
                "vdg": "6847",
                "video": "NTSC",
                "ram_kib": 32,
                "cpu": "6809",
                "clock": "normal",
                "roms": list(ROM_NAMES[target]),
                "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "checkpoints": list(range(len(MOVES) + 1)),
                "framebuffer_bytes_each": 6144,
                "map_bytes_each": 48,
                "guards": 4,
                "unreachable_trap": "passed",
                "visual": "not inspected",
                "physical_hardware": "not tested",
            },
            indent=2,
        )
        + "\n"
    )
    print(f"PASS: {target}; {len(MOVES) + 1} complete tile-room checkpoints.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--target", choices=tuple(ROM_NAMES), default="coco1")
    args = parser.parse_args()
    binary, symbols = build()
    if args.action == "check":
        check(binary, symbols, args.target)
    else:
        subprocess.run(emulator(args.target) + ["-ratelimit", "-run", str(binary)], check=True)


if __name__ == "__main__":
    main()
