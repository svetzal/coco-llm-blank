"""One bounded, private build and seven headless display-validation runs."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from cases import (
    Case,
    compare_capture,
    make_cases,
    probe_bytes,
    require_case,
    require_unreachable,
    symbol,
)
from first_screen import expected_screen
from instrument import instrument
from native import tool_path
from roms import verify_installed

URL = "https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz"
ARCHIVE_SHA256 = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
CONFIGURE = ["./configure", "--without-gtk2", "--without-gtk3", "--without-sdl3", "--without-sdl2"]
RESEARCH = ROOT / "local/research/display-validation-reproduction"
OUTPUT = ROOT / "build/display-validation-reproduction"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_archive(path: Path) -> None:
    if digest(path) != ARCHIVE_SHA256:
        raise ValueError("XRoar archive checksum mismatch")


def obtain_archive(destination: Path, supplied: Path | None) -> Path:
    if supplied:
        checked_archive(supplied)
        shutil.copyfile(supplied, destination)
    else:
        with urllib.request.urlopen(URL, timeout=60) as response:
            destination.write_bytes(response.read())
    checked_archive(destination)
    return destination


def logged(command: list[str], cwd: Path, log: Path, timeout: int = 600) -> None:
    with log.open("wb") as output:
        subprocess.run(
            command, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=timeout
        )


def build(archive: Path, work: Path, output: Path) -> tuple[Path, dict]:
    with tarfile.open(archive) as source:
        source.extractall(work, filter="data")
    tree = work / "xroar-1.12.1"
    target = tree / "src/null/ui_null.c"
    pristine_hash = digest(target)
    target.write_bytes(instrument(target.read_bytes()))
    logged(CONFIGURE, tree, output / "configure.log")
    logged(["make", "-j2"], tree, output / "make.log")
    binary = tree / "src/xroar"
    return binary, {
        "configure": CONFIGURE,
        "make": ["make", "-j2"],
        "pristine_ui_sha256": pristine_hash,
        "instrumented_ui_sha256": digest(target),
        "config_status_sha256": digest(tree / "config.status"),
        "config_log_sha256": digest(tree / "config.log"),
        "config_h_sha256": digest(tree / "config.h"),
        "executable_sha256": digest(binary),
    }


def command(
    xroar: Path, roms: dict[str, Path], binary: Path, address: int, snapshot: Path
) -> list[str]:
    return [
        str(xroar),
        "-c",
        os.devnull,
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        "cocous",
        "-ram",
        "32",
        "-bas",
        str(roms["bas11.rom"]),
        "-extbas",
        str(roms["extbas10.rom"]),
        "-no-cart",
        "-tv-input",
        "svideo",
        "-ccr",
        "none",
        "-vo-picture",
        "zoomed",
        "-fskip",
        "0",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "30",
        "-trap",
        f"pc=0x{address:04x}",
        "-trap-snap",
        str(snapshot),
        "-trap-timeout",
        "0.5",
        "-run",
        str(binary),
    ]


def launch(cmd: list[str], output: Path, name: str) -> tuple[int, Path, Path]:
    ppm, ram = output / f"{name}.ppm", output / f"{name}.ram"
    for path in (ppm, ram):
        path.unlink(missing_ok=True)
    environment = os.environ.copy()
    environment["DISPLAY_CAPTURE"] = str(ppm)
    result = subprocess.run(cmd, env=environment, capture_output=True, timeout=60, check=False)
    (output / f"{name}.log").write_bytes(result.stdout + result.stderr)
    return result.returncode, ppm, ram


def assemble(case: Case, assembler: str, work: Path, output: Path) -> tuple[Path, str]:
    source = work / f"{case.name}.asm"
    source.write_text(case.source)
    binary, symbols = output / f"{case.name}.bin", output / f"{case.name}.sym"
    subprocess.run(
        [
            assembler,
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
            str(source),
        ],
        cwd=work,
        check=True,
        timeout=30,
    )
    return binary, symbols.read_text()


def run_cases(
    assembler: str, xroar: Path, roms: dict[str, Path], work: Path, output: Path, report: dict
) -> None:
    (work / "probe.raw").write_bytes(probe_bytes())
    cases = make_cases(
        (ROOT / "examples/first-screen/main.asm").read_text(),
        (ROOT / "examples/moving-objects/main.asm").read_text(),
        expected_screen(),
    )
    report["cases"] = []
    for case in cases:
        binary, symbols = assemble(case, assembler, work, output)
        address = symbol(symbols, case.checkpoint)
        cmd = command(xroar, roms, binary, address, output / f"{case.name}.ram")
        code, ppm, ram = launch(cmd, output, case.name)
        if code or not ppm.exists() or not ram.exists():
            raise ValueError(f"{case.name}: missing capture/checkpoint or exit {code}")
        result = {
            "name": case.name,
            "command": cmd,
            "returncode": code,
            "checkpoint": {"symbol": case.checkpoint, "address": address},
            "source_sha256": digest(work / f"{case.name}.asm"),
            "binary_sha256": digest(binary),
            "symbols_sha256": digest(binary.with_suffix(".sym")),
            "capture_sha256": digest(ppm),
            "ram_sha256": digest(ram),
            **compare_capture(ppm, ram, case),
        }
        report["cases"].append(result)
        require_case(case.name, result)
        print(
            f"{case.name}: RAM matches; {result['pixel_mismatches']} differing samples", flush=True
        )
    # 'state' follows an RTS, is data, and is never executed. Use the same frame-65 build.
    address = symbol(symbols, "state")
    cmd = command(xroar, roms, binary, address, output / "unreachable.ram")
    code, ppm, ram = launch(cmd, output, "unreachable")
    report["unreachable"] = {
        "command": cmd,
        "returncode": code,
        "checkpoint": {"symbol": "state", "address": address},
        "binary_sha256": digest(binary),
        "snapshot_exists": ram.exists(),
        "capture_exists": ppm.exists(),
    }
    require_unreachable(code, ram)
    print("unreachable state symbol: no RAM checkpoint", flush=True)


def provenance(assembler: str, roms: dict[str, Path]) -> dict:
    inputs = [
        "examples/first-screen/main.asm",
        "examples/moving-objects/main.asm",
        "scripts/first_screen.py",
        "scripts/native.py",
        "scripts/roms.py",
        "scripts/references.py",
        "roms.json",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
    ]
    inputs += [str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob("*.py")]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {
        "base_revision": revision,
        "revision_meaning": "HEAD; working input hashes below",
        "platform": platform.platform(),
        "python": sys.version,
        "inputs_sha256": {name: digest(ROOT / name) for name in sorted(inputs)},
        "roms_sha256": {name: digest(path) for name, path in roms.items()},
        "archive": {"url": URL, "sha256": ARCHIVE_SHA256},
        "assembler": {
            "path": assembler,
            "sha256": digest(Path(assembler)),
            "version": subprocess.check_output([assembler, "--version"], text=True).strip(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id", default="fresh", help="New directory name; refuses existing runs"
    )
    parser.add_argument(
        "--archive", type=Path, help="Optional checksum-verified offline source archive"
    )
    args = parser.parse_args()
    if not args.run_id or any(
        c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in args.run_id
    ):
        parser.error("run-id must contain only lowercase letters, digits, hyphens or underscores")
    work, output = RESEARCH / args.run_id, OUTPUT / args.run_id
    if work.exists() or output.exists():
        parser.error("Run directory exists; choose a new run-id (no reuse of stale evidence)")
    assembler = tool_path("lwasm", ROOT)
    if not assembler:
        parser.error("LWASM missing; install the prerequisite or set LWASM explicitly")
    roms = verify_installed(ROOT, "coco1", ("bas11.rom", "extbas10.rom"))
    work.mkdir(parents=True)
    output.mkdir(parents=True)
    report = provenance(assembler, roms)
    report["passed"] = False
    try:
        archive = obtain_archive(work / "xroar-1.12.1.tar.gz", args.archive)
        xroar, report["build"] = build(archive, work, output)
        run_cases(assembler, xroar, roms, work, output, report)
        report["passed"] = True
    finally:
        (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {output / 'results.json'}")


if __name__ == "__main__":
    main()
