"""Bounded, non-T1 CoCo 2 renderer experiment; original scene adaptations."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/display-validation"))
sys.path.insert(0, str(ROOT / "scripts"))

import masked_objects
import reproduce as shared
import tile_room
from cases import (
    Case,
    compare_capture,
    make_cases,
    probe_bytes,
    require_case,
    require_unreachable,
    symbol,
)
from coco import load_expected
from instrument import replace_once
from native import tool_path
from roms import verify_installed

RESEARCH = ROOT / "local/research/display-coco2"
OUTPUT = ROOT / "build/display-coco2"
PROFILE = {
    "target": "coco2",
    "machine": "cocous",
    "tv": "ntsc",
    "vdg": "6847 (non-T1)",
    "cpu": "6809",
    "ram_kib": 32,
    "clock": "normal",
    "loader": "direct DECB",
    "display": "S-video, ccr none, zoomed RGBA8 software renderer",
}

FIRST_SCREEN = load_expected(ROOT / "examples/first-screen")


def make_scenes() -> list[Case]:
    """Freeze completed scenes without changing original drawing or display setup."""
    first = (ROOT / "examples/first-screen/main.asm").read_text()
    moving = (ROOT / "examples/moving-objects/main.asm").read_text()
    result = make_cases(first, moving, FIRST_SCREEN.expected_screen(1))[1:3]
    for kind, indices, variable, oracle in (
        ("tile-room", (0, 5, 39, 41), "step", tile_room.expected_screen),
        ("masked-objects", (0, 2, 3, 8, 9, 10, 11), "scene", masked_objects.expected_screen),
    ):
        source = (ROOT / f"examples/{kind}/main.asm").read_text()
        for index in indices:
            frozen = replace_once(
                source,
                "\nframe_ready\n",
                f"""
frame_ready
        lda {variable}
        cmpa #{index}
        bne continue_scene
frozen  bra frozen
continue_scene
""",
            )
            result.append(
                Case(
                    name=f"{kind}-{index}",
                    source=frozen,
                    checkpoint="frozen",
                    expected=oracle(index),
                )
            )
    return result


def command(
    xroar: Path,
    roms: dict[str, Path],
    binary: Path,
    address: int,
    snapshot: Path,
    delay: str = "0.5",
) -> list[str]:
    """Reuse capture settings, replacing only the explicit machine/firmware contract."""
    cmd = shared.command(
        xroar,
        {"bas11.rom": roms["bas12.rom"], "extbas10.rom": roms["extbas11.rom"]},
        binary,
        address,
        snapshot,
    )
    cmd[cmd.index("-trap-timeout") + 1] = delay
    return cmd + ["-tv-type", "ntsc", "-vdg-type", "6847", "-machine-cpu", "6809"]


def stationary_checkpoint(case: Case, symbols: str, memory: bytes) -> dict:
    """Require an assembled self-loop and the independently specified scene state."""
    address = symbol(symbols, case.checkpoint)
    if memory[address : address + 2] != b"\x20\xfe":
        raise ValueError("Checkpoint is not a stationary BRA-to-self")
    if case.name.startswith("tile-room-"):
        index = int(case.name.rsplit("-", 1)[1])
        names = ("map_guard_before", "map_guard_after", "xpos", "ypos", "accepted", "step", "room")
        tile_room.verify_ram(memory, {n: symbol(symbols, n) for n in names}, index)
        return {"step": index, "actor": list(tile_room.expected_state(index)[0])}
    if case.name.startswith("masked-objects-"):
        index = int(case.name.rsplit("-", 1)[1])
        masked_objects.verify_ram(memory, {"scene": symbol(symbols, "scene")}, index)
        return {"scene": index}
    if memory[0x2FFF] != 0xA5:
        raise ValueError("Probe completion marker missing")
    return {"marker": "A5 at 2FFF"}


def capture_case(
    case: Case, assembler: str, xroar: Path, roms: dict[str, Path], work: Path, output: Path
) -> dict:
    binary, symbols = shared.assemble(case, assembler, work, output)
    address = symbol(symbols, case.checkpoint)
    records = []
    for delay in ("0.5", "1.0"):
        name = f"{case.name}-{delay}"
        cmd = command(xroar, roms, binary, address, output / f"{name}.ram", delay)
        code, ppm, ram = shared.launch(cmd, output, name)
        if code or not ppm.exists() or not ram.exists():
            raise ValueError(f"{name}: missing capture/checkpoint or exit {code}")
        state = stationary_checkpoint(case, symbols, ram.read_bytes())
        comparison = compare_capture(ppm, ram, case)
        require_case(case.name, comparison)
        records.append(
            {
                "command": cmd,
                "delay": delay,
                "state": state,
                "capture_sha256": shared.digest(ppm),
                "ram_sha256": shared.digest(ram),
                **comparison,
            }
        )
    if records[0]["capture_sha256"] != records[1]["capture_sha256"]:
        raise ValueError("Stationary captures differ between settling intervals")
    return {
        "name": case.name,
        "checkpoint": {"symbol": case.checkpoint, "address": address},
        "source_sha256": shared.digest(work / f"{case.name}.asm"),
        "binary_sha256": shared.digest(binary),
        "symbols_sha256": shared.digest(binary.with_suffix(".sym")),
        "captures": records,
    }


def run_cases(
    assembler: str, xroar: Path, roms: dict[str, Path], work: Path, output: Path, report: dict
) -> None:
    (work / "probe.raw").write_bytes(probe_bytes())
    report["cases"] = []
    for case in make_scenes():
        result = capture_case(case, assembler, xroar, roms, work, output)
        report["cases"].append(result)
        print(
            f"{case.name}: {result['captures'][0]['pixel_mismatches']} differing samples",
            flush=True,
        )
    binary = output / "masked-objects-11.bin"
    symbols = binary.with_suffix(".sym").read_text()
    cmd = command(xroar, roms, binary, symbol(symbols, "state"), output / "unreachable.ram")
    code, ppm, ram = shared.launch(cmd, output, "unreachable")
    report["unreachable"] = {
        "command": cmd,
        "returncode": code,
        "snapshot_exists": ram.exists(),
        "capture_exists": ppm.exists(),
    }
    require_unreachable(code, ram)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="fresh")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if not args.run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id
    ):
        parser.error("run-id must contain lowercase letters, digits, hyphens or underscores")
    work, output = RESEARCH / args.run_id, OUTPUT / args.run_id
    if work.exists() or output.exists():
        parser.error("Run directory exists; choose a new run-id")
    assembler = tool_path("lwasm", ROOT)
    if not assembler:
        parser.error("LWASM missing")
    roms = verify_installed(ROOT, "coco2", ("bas12.rom", "extbas11.rom"))
    work.mkdir(parents=True)
    output.mkdir(parents=True)
    report = shared.provenance(assembler, roms)
    inputs = [
        "examples/tile-room/main.asm",
        "examples/masked-objects/main.asm",
        "scripts/tile_room.py",
        "scripts/masked_objects.py",
    ]
    inputs += [str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob("*.py")]
    report["inputs_sha256"].update({name: shared.digest(ROOT / name) for name in inputs})
    report.update(profile=PROFILE, passed=False)
    (work / "contract.json").write_text(json.dumps(PROFILE, indent=2) + "\n")
    try:
        archive = shared.obtain_archive(work / "xroar-1.12.1.tar.gz", args.archive)
        xroar, report["build"] = shared.build(archive, work, output)
        run_cases(assembler, xroar, roms, work, output, report)
        report["passed"] = True
    finally:
        (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {output / 'results.json'}")


if __name__ == "__main__":
    main()
