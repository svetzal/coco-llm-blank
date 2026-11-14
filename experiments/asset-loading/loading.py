"""Validate and consume the original host RG6 bundle in a bounded 6809 experiment."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments/assets"))
import prepare
from native import tool_path
from roms import verify_installed

SOURCE = ROOT / "experiments/assets/art.json"
ROM_NAMES = {"coco1": ("bas11.rom", "extbas10.rom"), "coco2": ("bas12.rom", "extbas11.rom")}
# Independent hand-calculated picture rows, not extracted from the bundle.
LITERALS = {
    10: bytes.fromhex("0000200000000000"),
    40: bytes.fromhex("ff80b8a0ae8280fd"),
    70: bytes.fromhex("2070f87020000200"),
    90: bytes.fromhex("e080a0a4be8480c1"),
}
WALLS = {(2, 0), (2, 1), (5, 1), (2, 2), (4, 3), (5, 3), (1, 4)}


def expected_screen() -> bytes:
    """Pixel oracle with independently specified positions and literal artwork."""
    pixels = [["0"] * 256 for _ in range(192)]
    for row in range(6):
        for column in range(8):
            identity = 40 if (column, row) in WALLS else 10
            if (column, row) == (1, 1):
                identity = 70
            if (column, row) == (6, 5):
                identity = 90
            for y, value in enumerate(LITERALS[identity]):
                pixels[row * 8 + y][column * 8 : column * 8 + 8] = f"{value:08b}"
    return bytes(int("".join(row[x : x + 8]), 2) for row in pixels for x in range(0, 256, 8))


def assembly_data(source: Path, bundle: Path) -> str:
    """Compare captured bundle bytes against the converter's public canonical API.

    This validates every descriptor, source digest, reference and payload before
    emitting anything. Retain the same bytes after validation to avoid a reread.
    """
    raw = bundle.read_bytes()
    if raw != prepare.prepare(source.read_bytes()):
        raise ValueError("prepared bundle is stale or corrupt")
    data = json.loads(raw)
    lines = ["asset_guard_before fcb $A5"]
    for asset in data["assets"]:
        values = bytes.fromhex(asset["hex"])
        lines.append(f"asset_{asset['asset_id']} fcb " + ",".join(f"${v:02X}" for v in values))
    lines += ["asset_guard_after fcb $A5", "terrain_pointers"]
    lines += ["        fdb " + ",".join(f"asset_{i}" for i in data["terrain_to_asset"])]
    lines += ["map_guard_before fcb $A5", "room"]
    lines += ["        fcb " + ",".join(map(str, row)) for row in data["room"]]
    lines += ["map_guard_after fcb $A5"]
    return "\n".join(lines) + "\n"


def executable(name: str) -> str:
    path = tool_path(name, ROOT)
    if not path:
        raise RuntimeError(f"Required tool missing: {name}")
    return path


def build(source: Path, bundle: Path, output: Path, mutation: str = "") -> tuple[Path, dict]:
    """Invalidate old build products before validating inputs or assembling."""
    output.mkdir(parents=True, exist_ok=True)
    binary, symbols, include = (output / name for name in ("room.bin", "room.sym", "assets.inc"))
    for path in (binary, symbols, include):
        path.unlink(missing_ok=True)
    include.write_text(assembly_data(source, bundle))
    command = [
        executable("lwasm"),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
        f"--includedir={output}",
    ]
    if mutation:
        command.append(f"--define={mutation}")
    subprocess.run(command + [str(HERE / "main.asm")], check=True, timeout=30)
    table = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+) EQU \$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }
    if table["start"] != 0x3000 or table["program_end"] >= 0x7E00:
        raise ValueError("code/data overlaps reserved memory")
    return binary, table


def capture(target: str, binary: Path, symbols: dict, output: Path) -> tuple[bytes, dict]:
    """No config search, GUI, audio, cartridge, default ROM search or turbo CPU."""
    names = ROM_NAMES[target]
    roms = verify_installed(ROOT, target, names)
    output.mkdir(parents=True, exist_ok=True)
    snapshot, negative = output / "ready.ram", output / "unreachable.ram"
    for path in (snapshot, negative):
        path.unlink(missing_ok=True)
    command = [
        executable("xroar"),
        "-c",
        "/dev/null",
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        "cocous",
        "-machine-cpu",
        "6809",
        "-tv-type",
        "ntsc",
        "-vdg-type",
        "6847",
        "-ram",
        "32",
        "-ram-init",
        "set",
        "-bas",
        str(roms[names[0]]),
        "-extbas",
        str(roms[names[1]]),
        "-no-cart",
        "-no-ratelimit",
        "-timeout",
        "10",
        "-trap",
        f"pc=0x{symbols['asset_guard_before']:04x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['ready']:04x}",
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0.001",
        "-run",
        str(binary),
    ]
    with (output / "xroar.log").open("wb") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=45, check=True)
    if negative.exists():
        raise ValueError("unreachable data trap fired")
    return snapshot.read_bytes(), {
        "target": target,
        "command": command,
        "rom_sha256": {name: digest(path) for name, path in roms.items()},
        "snapshot_sha256": digest(snapshot),
        "unreachable_absent": True,
    }


def assess(memory: bytes, symbols: dict) -> None:
    if len(memory) != 32768:
        raise ValueError("incorrect raw RAM size")
    if memory[symbols["completed"]] != 0x5A:
        raise ValueError("completion checkpoint missing")
    guards = [0x3FF, 0x1C00] + [
        symbols[name]
        for name in (
            "asset_guard_before",
            "asset_guard_after",
            "map_guard_before",
            "map_guard_after",
        )
    ]
    if any(memory[address] != 0xA5 for address in guards):
        raise ValueError("guard damaged")
    if memory[0x400:0x1C00] != expected_screen():
        raise ValueError("framebuffer differs from independent pixel oracle")
    for identity, literal in LITERALS.items():
        address = symbols[f"asset_{identity}"]
        if memory[address : address + 8] != literal:
            raise ValueError("prepared art changed in RAM")
    room = bytes(
        ".#*E".index(c)
        for row in ("..#.....", ".*#..#..", "..#.....", "....##..", ".#......", "......E.")
        for c in row
    )
    if memory[symbols["room"] : symbols["room"] + 48] != room:
        raise ValueError("room data changed in RAM")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    result = output / "results.json"
    result.write_text('{"passed":false}\n')
    bundle = output / "prepared.json"
    prepare.publish(SOURCE, bundle)
    report = {
        "passed": False,
        "source_sha256": digest(SOURCE),
        "runs": [],
        "input_sha256": {
            str(p.relative_to(ROOT)): digest(p)
            for p in (
                HERE / "main.asm",
                HERE / "loading.py",
                ROOT / "experiments/assets/prepare.py",
            )
        },
        "tools": {
            name: {
                "path": executable(name),
                "sha256": digest(Path(executable(name))),
                "version": subprocess.check_output(
                    [executable(name), "--version"], text=True
                ).strip(),
            }
            for name in ("lwasm", "xroar")
        },
    }
    for mutation in ("", "WRONG_BITS", "OVERFLOW"):
        directory = output / (mutation or "valid")
        binary, symbols = build(SOURCE, bundle, directory, mutation)
        for target in ROM_NAMES:
            memory, run = capture(target, binary, symbols, directory / target)
            run["differing_framebuffer_bytes"] = sum(
                actual != expected
                for actual, expected in zip(memory[0x400:0x1C00], expected_screen(), strict=True)
            )
            try:
                assess(memory, symbols)
            except ValueError as error:
                if not mutation:
                    raise
                run["detected"] = str(error)
            else:
                if mutation:
                    raise ValueError("mutation escaped detection")
                run["checked_framebuffer_bytes"] = 6144
            run.update(mutation=mutation, binary_sha256=digest(binary), symbols=symbols)
            report["runs"].append(run)
    report["passed"] = True
    result.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/asset-loading/run")
    args = parser.parse_args()
    check(args.output.resolve())
    print("PASS: CoCo 1/2 checkpoints, all framebuffer bytes, guards, two runtime controls")


if __name__ == "__main__":
    main()
