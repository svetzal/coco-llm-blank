"""Assemble original fixtures and compare XRoar RAM with a full pixel oracle."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from native import tool_path
from roms import verify_installed


class Region(BaseModel):
    top: int = Field(ge=0, le=8)
    bottom: int = Field(ge=0, le=8)
    colour: int = Field(ge=0, le=15)
    background: int = Field(ge=0, le=15)

    def record(self) -> list[int]:
        return [1, self.top, self.bottom, self.colour, self.background]


class Frame(BaseModel):
    name: str
    buffer: int
    regions: tuple[Region, Region]
    external: bool = False
    invalidate: bool = False


def fixtures() -> list[Frame]:
    a = Region(top=2, bottom=6, colour=3, background=1)
    b = Region(top=1, bottom=7, colour=9, background=2)
    colour = a.model_copy(update={"colour": 5})
    shrink = colour.model_copy(update={"top": 3, "bottom": 4})
    growth = shrink.model_copy(update={"top": 0, "bottom": 8})
    world = b.model_copy(update={"background": 7})
    return [
        Frame(name="initial-invalid", buffer=0, regions=(a, b)),
        Frame(name="unchanged", buffer=0, regions=(a, b)),
        Frame(name="colour-only", buffer=0, regions=(colour, b)),
        Frame(name="shrink", buffer=0, regions=(shrink, b)),
        Frame(name="growth", buffer=0, regions=(growth, b)),
        Frame(name="world-background", buffer=0, regions=(growth, world)),
        Frame(name="alternate-first-use", buffer=1, regions=(growth, world)),
        Frame(name="alternate-return", buffer=0, regions=(growth, world)),
        Frame(name="alternate-change", buffer=1, regions=(a, b)),
        Frame(name="alternate-old-history", buffer=0, regions=(growth, world)),
        Frame(
            name="external-invalidated",
            buffer=0,
            regions=(growth, world),
            external=True,
            invalidate=True,
        ),
        Frame(name="after-invalidation", buffer=0, regions=(growth, world)),
    ]


def oracle(regions: tuple[Region, Region]) -> bytes:
    """Full pixel redraw, no retained state or assembly byte-fill logic."""
    pixels = [[10, 5] * 80 for _ in range(8)]
    for index, region in enumerate(regions):
        for y in range(8):
            for x in range(index * 16, index * 16 + 8):
                pixels[y][x] = (
                    region.colour if region.top <= y < region.bottom else region.background
                )
    return bytes(row[x] * 16 + row[x + 1] for row in pixels for x in range(0, 160, 2))


def driver(frames: list[Frame], omit_invalidation: bool = False) -> str:
    lines = []
    for i, frame in enumerate(frames):
        base = 0x4000 + frame.buffer * 0x1000
        history = "history_b" if frame.buffer else "history_a"
        if frame.external:
            lines += ["        lda #$EE", f"        sta ${base:04X}"]
        if frame.invalidate and not omit_invalidation:
            lines += [f"        clr {history}"]
        lines += [
            "        clr writes",
            "        clr writes+1",
            f"        ldx #record_{i}",
            f"        ldy #{history}",
            f"        ldu #${base:04X}",
            "        jsr render",
            f"frame_{i} nop",
        ]
    lines += ["        jmp finished"]
    for i, frame in enumerate(frames):
        values = [v for region in frame.regions for v in region.record()]
        lines += [f"record_{i} fcb " + ",".join(map(str, values))]
    return "\n".join(lines) + "\n"


def assemble(output: Path, variant: str, frames: list[Frame]) -> tuple[Path, dict[str, int]]:
    directory = output / variant
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "driver.inc").write_text(driver(frames, variant == "missing-invalidation"))
    binary = directory / "renderer.bin"
    symbols = directory / "renderer.sym"
    assembler = tool_path("lwasm", ROOT)
    if not assembler:
        raise RuntimeError("LWASM is required")
    defines = {"full": "FULL_REDRAW", "shared-history": "BROKEN_HISTORY"}
    command = [
        assembler,
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
        f"--includedir={directory}",
    ]
    if variant in defines:
        command += [f"--define={defines[variant]}"]
    subprocess.run(command + [str(HERE / "main.asm")], check=True, timeout=30)
    table = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+) EQU \$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }
    if table["state_end"] >= 0x4000:
        raise ValueError("Code/state overlaps framebuffer")
    return binary, table


def capture(
    output: Path,
    variant: str,
    ram_kib: int,
    binary: Path,
    symbols: dict[str, int],
    rom: Path,
    frames: list[Frame],
) -> tuple[list[bytes], list[str]]:
    xroar = tool_path("xroar", ROOT)
    if not xroar:
        raise RuntimeError("XRoar is required")
    directory = output / variant
    command = [
        xroar,
        "-c",
        "/dev/null",
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        "coco3",
        "-machine-cpu",
        "6809",
        "-tv-type",
        "ntsc",
        "-vdg-type",
        "gime1986",
        "-ram",
        str(ram_kib),
        "-extbas",
        str(rom),
        "-no-cart",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "10",
    ]
    paths = [directory / f"{ram_kib}-{i}.ram" for i in range(len(frames))]
    negative = directory / f"{ram_kib}-unreachable.ram"
    for path in [*paths, negative]:
        path.unlink(missing_ok=True)
    command += ["-trap", f"pc=0x{symbols['state']:04x}", "-trap-snap", str(negative)]
    for i, path in enumerate(paths):
        command += ["-trap", f"pc=0x{symbols[f'frame_{i}']:04x}", "-trap-snap", str(path)]
    command += [
        "-trap",
        f"pc=0x{symbols['finished']:04x}",
        "-trap-timeout",
        "0.001",
        "-run",
        str(binary),
    ]
    with (directory / f"{ram_kib}.log").open("wb") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=45, check=True)
    if negative.exists():
        raise ValueError("Unreachable data trap fired")
    return [path.read_bytes() for path in paths], command


def assess(
    snapshots: list[bytes], symbols: dict[str, int], frames: list[Frame], ram_kib: int
) -> list[dict]:
    expected = [bytes([0xA5]) * 640, bytes([0xA5]) * 640]
    results = []
    for snapshot, frame in zip(snapshots, frames, strict=True):
        if len(snapshot) != ram_kib * 1024:
            raise ValueError("Incorrect raw RAM snapshot size")
        # Executive pages $38-$3F map to top 64 KiB on both capacities.
        memory = snapshot[-65536:]
        expected[frame.buffer] = oracle(frame.regions)
        differences = sum(
            sum(a != b for a, b in zip(memory[base : base + 640], data, strict=True))
            for base, data in zip((0x4000, 0x5000), expected, strict=True)
        )
        if any(memory[address] != 0xA5 for address in (0x3FFF, 0x4280, 0x4FFF, 0x5280)):
            raise ValueError("Framebuffer guard damaged")
        writes = int.from_bytes(memory[symbols["writes"] : symbols["writes"] + 2], "big")
        results.append(
            {"frame": frame.name, "differing_bytes": differences, "renderer_stores": writes}
        )
    return results


def tool_identity(name: str) -> dict:
    path = tool_path(name, ROOT)
    if not path:
        raise RuntimeError(f"{name} is required")
    return {
        "path": path,
        "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "version": subprocess.check_output([path, "--version"], text=True).strip(),
    }


def check(output: Path, capacities: tuple[int, ...] = (128, 512)) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "results.json"
    report_path.write_text(json.dumps({"passed": False, "status": "incomplete"}) + "\n")
    frames = fixtures()
    rom = verify_installed(ROOT, "coco3", ("coco3.rom",))["coco3.rom"]
    report = {
        "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "tools": {name: tool_identity(name) for name in ("lwasm", "xroar")},
        "inputs_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (HERE / "main.asm", HERE / "selective_redraw.py")
        },
        "runs": [],
    }
    output.mkdir(parents=True, exist_ok=True)
    for variant in ("selective", "full", "shared-history", "missing-invalidation"):
        binary, symbols = assemble(output, variant, frames)
        for capacity in capacities:
            snapshots, command = capture(output, variant, capacity, binary, symbols, rom, frames)
            rows = assess(snapshots, symbols, frames, capacity)
            report["runs"].append(
                {"variant": variant, "ram_kib": capacity, "command": command, "frames": rows}
            )
    for run in report["runs"]:
        failures = [row["frame"] for row in run["frames"] if row["differing_bytes"]]
        if run["variant"] in ("selective", "full"):
            assert not failures, (run["variant"], failures)
        elif run["variant"] == "shared-history":
            assert "alternate-first-use" in failures
        else:
            assert "external-invalidated" in failures
    report["passed"] = True
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/selective-redraw")
    args = parser.parse_args()
    check(args.output.resolve())
    print("PASS: both RAM capacities, full oracle, both mutations, unreachable trap")


if __name__ == "__main__":
    main()
