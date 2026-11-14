"""Build pinned instrumented XRoar and retain locally verifiable provenance."""

import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

from instrument import instrument, instrument_traps

ARCHIVE_SHA256 = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
HERE = Path(__file__).resolve().parent
CONFIGURE = ["./configure"] + [
    f"--without-{name}"
    for name in ("gtk3", "gtk2", "sdl3", "sdl2", "cocoa", "coreaudio", "alsa", "oss", "pulse")
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_inputs(archive: Path) -> dict[str, bytes]:
    if digest(archive) != ARCHIVE_SHA256:
        raise ValueError("Pinned archive mismatch")
    with tarfile.open(archive) as tar:
        inputs = {
            str(Path(member.name).relative_to("xroar-1.12.1")): tar.extractfile(member).read()
            for member in tar.getmembers()
            if member.isfile()
            and (
                Path(member.name).suffix in (".c", ".h", ".am", ".in")
                or Path(member.name).name == "configure"
            )
        }
    inputs["src/null/ao_null.c"] = instrument(inputs["src/null/ao_null.c"])
    inputs["src/xroar.c"] = instrument_traps(inputs["src/xroar.c"])
    return inputs


def verify_build(executable: Path) -> dict:
    """Check inputs against pinned bytes, not just claims inside a manifest."""
    manifest_path = executable.parent.parent / "capture-build.json"
    if not manifest_path.is_file():
        raise ValueError("Missing capture build provenance")
    manifest = json.loads(manifest_path.read_text())
    source = manifest_path.parent
    inputs = source_inputs(Path(manifest["archive"]))
    for name, expected in inputs.items():
        if (source / name).read_bytes() != expected:
            raise ValueError(f"Build source mismatch: {name}")
    expected = {
        "archive_sha256": ARCHIVE_SHA256,
        "executable_sha256": digest(executable),
        "instrumentation_sha256": digest(HERE / "instrument.py"),
        "builder_sha256": digest(Path(__file__)),
        "configure": CONFIGURE,
        "ram_oracle_sha256": digest(HERE.parents[1] / "examples/sound-slots/expected.py"),
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Build provenance mismatch")
    return manifest


def build(archive: Path, output: Path) -> Path:
    inputs = source_inputs(archive)
    output.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as tar:
        tar.extractall(output, filter="data")
    source = output / "xroar-1.12.1"
    for name, content in inputs.items():
        (source / name).write_bytes(content)
    for name, command in (("configure", CONFIGURE), ("make", ["make", "-j4"])):
        with (output / f"{name}.log").open("w") as log:
            subprocess.run(
                command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240
            )
    executable = source / "src/xroar"
    manifest = {
        "archive": str(archive.resolve()),
        "archive_sha256": ARCHIVE_SHA256,
        "executable_sha256": digest(executable),
        "instrumentation_sha256": digest(HERE / "instrument.py"),
        "builder_sha256": digest(Path(__file__)),
        "ram_oracle_sha256": digest(HERE.parents[1] / "examples/sound-slots/expected.py"),
        "configure": CONFIGURE,
        "make": ["make", "-j4"],
        "source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in inputs.items()},
        "attestation_limit": "Local build record, not signed or hermetic; compiler, libraries and host are trusted.",
    }
    (source / "capture-build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify_build(executable)
    return executable


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(build(args.archive.resolve(), args.output.resolve()))


if __name__ == "__main__":
    main()
