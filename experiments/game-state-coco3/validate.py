"""Build and execute a small original CoCo 3 state-machine experiment."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

from vectors import Case, fixtures, require_host_agreement

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
from native import tool_path
from roms import verify_installed

VARIANTS = {
    "correct": None,
    "rejection-mutation": "BAD_REJECT",
    "overwrite-full": "BAD_FULL",
    "miss-last": "BAD_LAST",
    "repeat-arrival": "BAD_REPEAT",
    "wrap-turn": "BAD_WRAP",
}
WITNESSES = {
    "rejection-mutation": "wrong-player",
    "overwrite-full": "queue-lifecycle:2",
    "miss-last": "overdue-saturation-last-slot",
    "repeat-arrival": "queue-lifecycle:7",
    "wrap-turn": "maximum-turn:5",
}


def driver(cases: list[Case]) -> str:
    lines = ["        ldu #results"]
    for index, case in enumerate(cases):
        lines += [
            f"        ldx #initial_{index}",
            "        ldy #world",
            "        ldb #17",
            f"reset_{index} lda ,x+",
            "        sta ,y+",
            "        decb",
            f"        bne reset_{index}",
        ]
        for step in case.steps:
            if step.action == "send":
                values = [*step.command[:4], step.command[4] >> 8, step.command[4] & 255]
                for offset, value in enumerate(values):
                    lines += [f"        lda #{value}", f"        sta command+{offset}"]
            lines += ["        clr resolved", f"        jsr {step.action}", "        jsr record"]
    lines += ["        lda #$5A", "        sta $420B", "        jmp finished"]
    for index, case in enumerate(cases):
        lines += [f"initial_{index} fcb " + ",".join(map(str, case.initial.raw()))]
    return "\n".join(lines) + "\n"


def require_tool(name: str) -> str:
    path = tool_path(name, ROOT)
    if path is None:
        raise RuntimeError(f"Missing required native tool: {name}")
    return path


def assemble(directory: Path, variant: str, cases: list[Case]) -> tuple[Path, dict[str, int]]:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "driver.inc").write_text(driver(cases))
    binary, symbols = directory / "state.bin", directory / "state.sym"
    command = [
        require_tool("lwasm"),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
        f"--includedir={directory}",
    ]
    if VARIANTS[variant]:
        command.append(f"--define={VARIANTS[variant]}")
    subprocess.run(command + [str(HERE / "main.asm")], check=True, timeout=30)
    table = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+) EQU \$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }
    if table["code_end"] > 0x4000 or sum(len(c.steps) for c in cases) * 19 >= 0x1000:
        raise ValueError("Experiment exceeds its allocated memory")
    return binary, table


def capture(directory: Path, capacity: int, binary: Path, symbols: dict[str, int]) -> dict:
    # Verify bytes immediately before each launch, never trust a preceding doctor alone.
    rom = verify_installed(ROOT, "coco3", ("coco3.rom",))["coco3.rom"]
    snapshot = directory / f"{capacity}.ram"
    negative = directory / f"{capacity}-unreachable.ram"
    for path in (snapshot, negative):
        path.unlink(missing_ok=True)
    command = [
        require_tool("xroar"),
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
        str(capacity),
        "-extbas",
        str(rom),
        "-no-cart",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "10",
        "-trap",
        f"pc=0x{symbols['unreachable']:04x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['finished']:04x}",
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0.001",
        "-run",
        str(binary),
    ]
    with (directory / f"{capacity}.log").open("wb") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=45)
    if negative.exists():
        raise ValueError("Unreachable data trap fired")
    return {"command": command, "rom_sha256": digest(rom), "snapshot": str(snapshot)}


def assess(snapshot: bytes, capacity: int, cases: list[Case]) -> list[str]:
    if len(snapshot) != capacity * 1024:
        raise ValueError("Incorrect raw RAM capture size")
    memory = snapshot[-65536:]
    count = sum(len(case.steps) for case in cases)
    guards = (0x40FF, 0x4111, 0x41FF, 0x420C, 0x4FFF, 0x5000 + count * 19, 0x7DFF, 0x7F00)
    if any(memory[address] != 0xA5 for address in guards):
        raise ValueError("State, scratch, results or stack guard damaged")
    if memory[0x420B] != 0x5A:
        raise ValueError("Completion marker missing")
    failures = []
    offset = 0x5000
    for case in cases:
        for index, step in enumerate(case.steps):
            expected = step.expected.raw() + bytes([step.status, step.resolved])
            if memory[offset : offset + 19] != expected:
                failures.append(f"{case.name}:{index}")
            offset += 19
    return failures


def require_result(variant: str, failures: list[str]) -> None:
    if variant == "correct":
        if failures:
            raise ValueError(f"Correct build mismatched checkpoints: {failures}")
    elif not any(f.startswith(WITNESSES[variant]) for f in failures):
        raise ValueError(f"Faulty control escaped detection: {variant}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "results.json"
    report_path.write_text('{"passed": false, "status": "incomplete"}\n')
    cases = fixtures()
    require_host_agreement(cases)
    report = {
        "passed": False,
        "cases": len(cases),
        "checkpoints": sum(len(case.steps) for case in cases),
        "tools": {},
        "source_sha256": {},
        "runs": [],
    }
    try:
        for name in ("lwasm", "xroar"):
            path = require_tool(name)
            report["tools"][name] = {
                "path": path,
                "sha256": digest(Path(path)),
                "version": subprocess.check_output([path, "--version"], text=True).strip(),
            }
        for name in ("main.asm", "validate.py", "vectors.py"):
            report["source_sha256"][name] = digest(HERE / name)
        report["source_sha256"]["host_model"] = digest(
            ROOT / "experiments/game-state/game_state_model.py"
        )
        for variant in VARIANTS:
            directory = output / variant
            binary, symbols = assemble(directory, variant, cases)
            for capacity in (128, 512):
                run = capture(directory, capacity, binary, symbols)
                failures = assess(Path(run["snapshot"]).read_bytes(), capacity, cases)
                run.update(
                    variant=variant,
                    ram_kib=capacity,
                    mismatches=failures,
                    binary_sha256=digest(binary),
                    code_end=symbols["code_end"],
                )
                report["runs"].append(run)
                require_result(variant, failures)
    except BaseException as error:
        report["status"] = "failed"
        report["failure"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        raise
    report["passed"] = True
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/game-state-coco3")
    args = parser.parse_args()
    report = check(args.output.resolve())
    print(f"PASS: {report['checkpoints']} checkpoints, both RAM sizes, five faulty controls")


if __name__ == "__main__":
    main()
