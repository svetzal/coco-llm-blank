"""Run real 6809 scans via XRoar's keyboard matrix and PIA, headless and bounded."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from native import tool_path
from roms import verify_installed

WORK = ROOT / "build/keyboard-controls"
PROFILES = {
    "coco1": ("cocous", "bas11.rom", "extbas10.rom"),
    "coco2": ("coco2bus", "bas12.rom", "extbas11.rom"),
}
# Independent literal oracle: row bit 3 for L/R/space, held, x, shots, history.
# No calculation from injected masks, scanner source, or controls-collision model.
EXPECTED = [
    [8, 8, 0, 4, 2, 0, 4],
    [8, 8, 8, 0, 2, 0, 0],
    [8, 0, 0, 6, 3, 1, 6],
    [8, 0, 0, 6, 4, 1, 6],
    [8, 0, 0, 6, 4, 1, 6],
    [8, 0, 8, 2, 4, 1, 2],
    [8, 0, 0, 6, 4, 2, 6],
    [8, 0, 0, 6, 4, 2, 6],
    [0, 8, 0, 5, 3, 2, 5],
    [0, 8, 8, 1, 2, 2, 1],
    [0, 8, 0, 5, 1, 3, 5],
    [0, 0, 0, 7, 1, 3, 7],
    [8, 8, 8, 0, 1, 3, 0],
    [0, 8, 8, 1, 0, 3, 1],
    [0, 8, 8, 1, 0, 3, 1],
    [8, 0, 8, 2, 1, 3, 2],
]


def symbols(path: Path) -> dict[str, int]:
    return {
        name: int(value, 16)
        for name, value in re.findall(r"(\w+) EQU \$([0-9A-Fa-f]+)", path.read_text())
    }


def run(
    target: str, variant: str = "normal", inject: bool = True, unreachable: bool = False
) -> dict:
    """Retain command, log, symbols, binary, RAM and decoded evidence per case."""
    suffix = f"{target}-{variant}-{'keys' if inject else 'idle'}-{'miss' if unreachable else 'hit'}"
    output = WORK / suffix
    output.mkdir(parents=True, exist_ok=True)
    for name in ("result.json", "result.ram", "main.bin", "main.sym", "command.json", "xroar.log"):
        (output / name).unlink(missing_ok=True)
    report = output / "result.json"
    report.write_text('{"status": "incomplete", "matches_expected": false}\n')
    try:
        result = execute_case(target, variant, inject, unreachable, output)
    except BaseException as error:
        report.write_text(
            json.dumps(
                {
                    "status": "failed",
                    "matches_expected": False,
                    "error": str(error),
                    "type": type(error).__name__,
                },
                indent=2,
            )
            + "\n"
        )
        raise
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def execute_case(target: str, variant: str, inject: bool, unreachable: bool, output: Path) -> dict:
    """Build and inspect one attempt after its prior evidence is invalidated."""
    profile, basic, extended = PROFILES[target]
    roms = verify_installed(ROOT, target, (basic, extended))
    assembler = tool_path("lwasm", ROOT)
    if not assembler:
        raise RuntimeError("lwasm is required; no tools are installed by this runner")
    binary = output / "main.bin"
    sym = output / "main.sym"
    command = [assembler, "--6809", "--format=decb", f"--output={binary}", f"--symbol-dump={sym}"]
    if variant != "normal":
        command.append(f"--define={variant}")
    subprocess.run([*command, str(HERE / "main.asm")], check=True, timeout=20)
    labels = symbols(sym)
    assert labels["program_end"] < 0x4000
    snapshot = output / "result.ram"
    snapshot.unlink(missing_ok=True)
    sample_trap = f"pc=0x{labels['sample']:04x}"
    end = 0x2000 if unreachable else labels["finished"]
    emulator = WORK / "xroar-1.12.1/src/xroar"
    command = [
        str(emulator),
        "-no-c",
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        profile,
        "-machine-cpu",
        "6809",
        "-machine-keyboard",
        "coco",
        "-ram",
        "32",
        "-ram-init",
        "set",
        "-tv-type",
        "ntsc",
        "-bas",
        str(roms[basic]),
        "-extbas",
        str(roms[extended]),
        "-no-cart",
        "-no-ratelimit",
        "-timeout",
        "10",
        "-trap",
        sample_trap,
        "-trap-range",
        "1-17",
        "-trap",
        f"pc=0x{end:04x}",
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0.001",
        "-run",
        str(binary),
    ]
    env = dict(os.environ)
    env.pop("KEYBOARD_EVENTS", None)
    env.pop("KEYBOARD_TRAP", None)
    if inject:
        env.update(KEYBOARD_EVENTS=str(HERE / "events.txt"), KEYBOARD_TRAP=sample_trap)
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (output / "xroar.log").open("w") as log:
        subprocess.run(
            command,
            cwd=output,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=30,
        )
    log_text = (output / "xroar.log").read_text()
    assert log_text.count("keyboard-sample ") == (17 if inject else 0)
    if unreachable:
        assert not snapshot.exists(), "Unreachable checkpoint unexpectedly captured RAM"
        return {"unreachable_trap": "no snapshot"}
    ram = snapshot.read_bytes()
    assert len(ram) == 32768
    assert ram[labels["complete"]] == 0xA5
    assert ram[labels["count"]] == 16
    raw = [list(ram[0x4000 + i * 7 : 0x4000 + (i + 1) * 7]) for i in range(16)]
    records = [[*(value & 8 for value in row[:3]), *row[3:]] for row in raw]
    control = list(ram[labels["control_a_before"] : labels["columns_after"] + 1])
    result = {
        "control": control,
        "target": target,
        "variant": variant,
        "injected": inject,
        "records": records,
        "raw_records": raw,
        "matches_expected": records == EXPECTED,
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "emulator_sha256": hashlib.sha256(emulator.read_bytes()).hexdigest(),
        "rom_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in roms.items()
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=PROFILES, default="coco1")
    parser.add_argument(
        "--variant",
        choices=["normal", "WRONG_COLUMN", "WRONG_SELECT", "HELD_FIRE", "STALE_HISTORY"],
        default="normal",
    )
    parser.add_argument("--no-injection", action="store_true")
    parser.add_argument("--unreachable", action="store_true")
    args = parser.parse_args()
    result = run(args.target, args.variant, not args.no_injection, args.unreachable)
    print(json.dumps(result, indent=2))
    if args.variant == "normal" and not args.no_injection and not args.unreachable:
        assert result["matches_expected"]


if __name__ == "__main__":
    main()
