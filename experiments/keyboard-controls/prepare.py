"""Build a checksum-pinned, isolated XRoar with a keyboard-event test hook."""

import argparse
import hashlib
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "build/keyboard-controls"
URL = "https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz"
SHA256 = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"


def prepare() -> Path:
    """Download pristine release; patch only trap dispatch, build without GUI."""
    WORK.mkdir(parents=True, exist_ok=True)
    archive = WORK / "xroar-1.12.1.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive.write_bytes(response.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError("XRoar archive checksum differs")
    source = WORK / "xroar-1.12.1"
    # Reruns start from the verified archive, never a previously patched tree.
    if source.exists():
        shutil.rmtree(source)
    with tarfile.open(archive) as package:
        package.extractall(WORK, filter="data")
    path = source / "src/xroar.c"
    text = path.read_text()
    anchor = "static void handle_trap(void *sptr) {\n\tstruct trap_def *trap = sptr;"
    if text.count(anchor) != 1:
        raise ValueError("XRoar trap hook anchor differs")
    helper = (HERE / "key_hook.c").read_text()
    path.write_text(
        text.replace(anchor, helper + "\n" + anchor + "\n\texperiment_keyboard(trap->cond);")
    )
    commands = [
        ["./configure", "--without-gtk2", "--without-gtk3", "--without-sdl3", "--without-sdl2"],
        ["make", "-j2"],
    ]
    for index, command in enumerate(commands):
        with (WORK / f"build-{index}.log").open("w") as log:
            subprocess.run(
                command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240
            )
    return source / "src/xroar"


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(prepare())
