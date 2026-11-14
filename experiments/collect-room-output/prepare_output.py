"""Private combined capture build from pinned pristine XRoar sources."""

import argparse
import hashlib
import json
import runpy
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SHA = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
CONFIGURE = ["./configure"] + [
    f"--without-{n}"
    for n in ("gtk3", "gtk2", "sdl3", "sdl2", "cocoa", "coreaudio", "alsa", "oss", "pulse")
]
REUSED = [
    "experiments/audio-output/instrument.py",
    "experiments/display-validation/instrument.py",
    "examples/collect-room/key_hook.c",
    "examples/collect-room/audio_hook.c",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Instrumentation anchor differs: {old}")
    return text.replace(old, new)


def patched(archive: Path) -> dict[str, bytes]:
    if digest(archive) != SHA:
        raise ValueError("Pinned archive mismatch")
    with tarfile.open(archive) as tar:
        inputs = {
            str(Path(m.name).relative_to("xroar-1.12.1")): tar.extractfile(m).read()
            for m in tar.getmembers()
            if m.isfile()
            and (
                Path(m.name).suffix in (".c", ".h", ".am", ".in")
                or Path(m.name).name == "configure"
            )
        }
    audio = runpy.run_path(str(ROOT / REUSED[0]))
    display = runpy.run_path(str(ROOT / REUSED[1]))
    inputs["src/null/ao_null.c"] = audio["instrument"](inputs["src/null/ao_null.c"])
    video = display["instrument"](inputs["src/null/ui_null.c"]).decode()
    start, end = (
        video.index("static void capture_draw("),
        video.index("static void capture_viewport("),
    )
    video = video[:start] + (HERE / "video_hook.c").read_text() + video[end:]
    inputs["src/null/ui_null.c"] = video.encode()
    hook = (
        (ROOT / REUSED[2])
        .read_text()
        .replace('xroar_set_timeout("0")', 'xroar_set_timeout("0.05")')
    )
    anchor = "static void handle_trap(void *sptr) {\n\tstruct trap_def *trap = sptr;"
    inputs["src/xroar.c"] = replace(
        inputs["src/xroar.c"].decode(),
        anchor,
        hook + "\n" + anchor + "\n\tcollect_keyboard(trap->cond);",
    ).encode()
    anchor = "static void pia1a_data_postwrite_coco(void *sptr) {\n\tstruct dragon *md = sptr;"
    inputs["src/dragon/coco.c"] = replace(
        inputs["src/dragon/coco.c"].decode(), anchor, anchor + "\n" + (ROOT / REUSED[3]).read_text()
    ).encode()
    return inputs


def tool_hashes() -> dict:
    paths = [ROOT / p for p in REUSED] + [Path(__file__), HERE / "video_hook.c"]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def verify(executable: Path) -> dict:
    source = executable.parent.parent
    manifest = json.loads((source / "output-build.json").read_text())
    for name, value in patched(Path(manifest["archive"])).items():
        if (source / name).read_bytes() != value:
            raise ValueError(f"Build source mismatch: {name}")
    if manifest["executable"] != digest(executable) or manifest["tools"] != tool_hashes():
        raise ValueError("Build provenance mismatch")
    return manifest


def build(archive: Path, output: Path) -> Path:
    inputs = patched(archive)
    output.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive) as tar:
        tar.extractall(output, filter="data")
    source = output / "xroar-1.12.1"
    for name, value in inputs.items():
        (source / name).write_bytes(value)
    for name, command in (("configure", CONFIGURE), ("make", ["make", "-j4"])):
        with (output / f"{name}.log").open("w") as log:
            subprocess.run(
                command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240
            )
    executable = source / "src/xroar"
    manifest = {
        "archive": str(archive.resolve()),
        "archive_sha256": SHA,
        "executable": digest(executable),
        "tools": tool_hashes(),
        "configure": CONFIGURE,
    }
    (source / "output-build.json").write_text(json.dumps(manifest, indent=2) + "\n")
    verify(executable)
    return executable


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(args.archive.resolve(), args.output.resolve()))
