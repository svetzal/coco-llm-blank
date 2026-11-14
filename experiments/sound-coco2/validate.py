"""Bounded non-T1 NTSC CoCo 2 cooperative DAC/input/drawing experiment."""

import argparse
import collections
import hashlib
import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from native import tool_path
from roms import verify_installed
from sound_slots import expected_samples, verify_ram

HERE = Path(__file__).resolve().parent
FRAMES = (1, 16, 17, 32, 33, 63, 64)
TICKS = 14318180


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble(output: Path, scripted: bool, delayed: bool) -> tuple[Path, dict[str, int]]:
    binary, symbols = output / "program.bin", output / "program.sym"
    assembler = tool_path("lwasm")
    if not assembler:
        raise ValueError("LWASM is required")
    command = [
        assembler,
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
    ]
    command += ["--define=SCRIPTED"] if scripted else []
    command += ["--define=DELAYED"] if delayed else []
    command += [str(HERE / "main.asm")]
    (output / "assemble.json").write_text(json.dumps(command, indent=2))
    subprocess.run(command, check=True, timeout=30)
    addresses = {
        k: int(v, 16)
        for k, v in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9a-fA-F]+)", symbols.read_text(), re.MULTILINE
        )
    }
    assert 0x3000 < addresses["state_end"] < 0x4000, "code/state allocation"
    return binary, addresses


def command(xroar: Path, binary: Path, syms: dict[str, int], output: Path, frame: int) -> list[str]:
    roms = verify_installed(ROOT, "coco2", ("bas12.rom", "extbas11.rom"))
    return [
        str(xroar),
        "-c",
        "/dev/null",
        "-machine",
        "cocous",
        "-ram",
        "64",
        "-tv-type",
        "ntsc",
        "-vdg-type",
        "6847",
        "-machine-cpu",
        "6809",
        "-bas",
        str(roms["bas12.rom"]),
        "-extbas",
        str(roms["extbas11.rom"]),
        "-no-cart",
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
        f"pc=0x{syms['state']:x}",
        "-trap-snap",
        str(output / "negative.ram"),
        "-trap",
        f"pc=0x{syms['frame_ready']:x}",
        "-trap-range",
        str(frame),
        "-trap-snap",
        str(output / f"{frame}.ram"),
        "-trap-timeout",
        "0",
        "-run",
        str(binary),
    ]


def samples(log: str, address: int) -> list[tuple[int, int]]:
    result = []
    for line in log.splitlines():
        if not line.startswith("AT,"):
            continue
        _, tick, pc, value, cr, ddr = line.split(",")
        if int(pc, 16) != address + 3:
            continue
        assert int(cr, 16) & 4 and int(ddr, 16) & 0xFC == 0xFC, "PIA configuration"
        result.append((int(tick), int(value, 16) & 0xFC))
    return result


def analyze(
    log: str, ram: bytes, syms: dict[str, int], frame: int, scripted: bool, negative: bool
) -> dict:
    assert not negative, "unreachable trap fired"
    assert len(ram) == 65536, "missing or truncated RAM"
    # Independent existing phase/button/framebuffer oracle, not assembly table data.
    verify_ram(ram[:32768], syms, frame, scripted)
    records = samples(log, syms["sample"])
    assert [v for _, v in records] == expected_samples(scripted)[: frame * 256], "DAC sequence"
    gaps = [(b[0] - a[0]) & 0xFFFFFFFF for a, b in itertools.pairwise(records)]
    assert all(g > 0 and g % 16 == 0 for g in gaps), "tick intervals"
    return {
        "frames": frame,
        "samples": len(records),
        "intervals": len(gaps),
        "boundary_ticks": gaps[255::256],
        "min_cycles": min(gaps) // 16,
        "max_cycles": max(gaps) // 16,
        "mean_cycles": sum(gaps) / len(gaps) / 16,
        "span_ticks": sum(gaps),
        "span_seconds": sum(gaps) / TICKS,
        "histogram_ticks": dict(sorted(collections.Counter(gaps).items())),
    }


def run_case(xroar: Path, output: Path, scripted: bool, delayed: bool) -> dict:
    output.mkdir()
    binary, syms = assemble(output, scripted, delayed)
    results = []
    for frame in FRAMES:
        cmd = command(xroar, binary, syms, output, frame)
        (output / f"{frame}.command.json").write_text(json.dumps(cmd, indent=2))
        with (output / f"{frame}.log").open("w") as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=40)
        results.append(
            analyze(
                (output / f"{frame}.log").read_text(),
                (output / f"{frame}.ram").read_bytes(),
                syms,
                frame,
                scripted,
                (output / "negative.ram").exists(),
            )
        )
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results[-1]


def controls(results: dict) -> None:
    normal, delayed = results["scripted"], results["delayed"]
    assert normal["samples"] == delayed["samples"] == 16384, "sample count control"
    assert normal["min_cycles"] == delayed["min_cycles"], "inner-loop control"
    assert delayed["max_cycles"] > normal["max_cycles"] * 100, "delayed-work control"
    # Delay loop: LDX immediate 3 cycles, 10000 * (LEAX 5 + BNE 3).
    # Only 63 boundaries lie between the first and last of 64 sample blocks.
    assert delayed["span_ticks"] - normal["span_ticks"] == 63 * 80003 * 16, "delay budget"
    assert len(normal["boundary_ticks"]) == len(delayed["boundary_ticks"]) == 63
    assert all(
        b - a == 80003 * 16
        for a, b in zip(normal["boundary_ticks"], delayed["boundary_ticks"], strict=True)
    ), "boundary delay budget"


def run(xroar: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    roms = verify_installed(ROOT, "coco2", ("bas12.rom", "extbas11.rom"))
    provenance = {
        "target": "26-3134/26-3136 NTSC non-T1, 64 KiB, 6809 normal clock",
        "tick_rate": TICKS,
        "ticks_per_cycle": 16,
        "rom_sha256": {k: digest(v) for k, v in roms.items()},
        "xroar_sha256": digest(xroar),
        "assembly_sha256": digest(HERE / "main.asm"),
        "runner_sha256": digest(Path(__file__)),
        "oracle_sha256": digest(ROOT / "scripts/sound_slots.py"),
        "lock_sha256": digest(ROOT / "uv.lock"),
    }
    (output / "contract.json").write_text(json.dumps(provenance, indent=2) + "\n")
    results = {
        name: run_case(xroar, output / name, scripted, delayed)
        for name, scripted, delayed in [
            ("released", False, False),
            ("scripted", True, False),
            ("delayed", True, True),
        ]
    }
    controls(results)
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xroar", required=True, type=Path, help="Private DAC-instrumented XRoar 1.12.1 executable"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "build/sound-coco2/measured")
    options = parser.parse_args()
    if not __debug__:
        parser.error("Assertions required; do not use optimized Python")
    results = run(options.xroar.resolve(), options.output.resolve())
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
