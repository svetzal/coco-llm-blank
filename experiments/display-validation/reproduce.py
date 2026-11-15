"""Shared private XRoar 1.12.1 build helpers, kept only for other open experiments.

The display lab is closed: its evidence is in examples/first-screen and
examples/palette-swatches (`scripts/coco.py check --video`). This module and
instrument.py remain because animation-cadence, clean-animation,
clean-animation-coco3 and collect-room-output use them. Delete this folder
when those experiments close.
"""

import hashlib
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
URL = "https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz"
ARCHIVE_SHA256 = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
CONFIGURE = ["./configure", "--without-gtk2", "--without-gtk3", "--without-sdl3", "--without-sdl2"]


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


def provenance(assembler: str, roms: dict[str, Path]) -> dict:
    inputs = [
        "examples/first-screen/main.asm",
        "examples/moving-objects/main.asm",
        "examples/first-screen/expected.py",
        "examples/first-screen/coco.toml",
        "scripts/coco.py",
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
