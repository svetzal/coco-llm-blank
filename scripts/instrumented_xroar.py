"""Build the one instrumented XRoar that coco.py uses to capture screens, keys and sound.

It is XRoar built from the pinned release archive with the tracked hooks in
scripts/xroar_hooks/ patched in. It is built once, into ignored
local/toolchain/xroar-instrumented/, the first time a project asks for one of
those abilities, and rebuilt when the pinned source, the patch or the build
output no longer match the recorded provenance. Ordinary build, run and check
keep using the installed XRoar and need no C compiler.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path

from native import ROOT, SOURCES, cached_source
from pydantic import BaseModel, ConfigDict, ValidationError

HOOKS = Path(__file__).resolve().parent / "xroar_hooks"
HOME = Path("local/toolchain/xroar-instrumented")
RECORD = "build.json"
VERSION, URL, ARCHIVE_SHA256 = SOURCES["xroar"]
TREE = f"xroar-{VERSION}"
EXECUTABLE = Path(TREE) / "src/xroar"
# No window, no host audio: only the null UI and null audio modules are needed.
CONFIGURE = ["./configure"] + [
    f"--without-{name}"
    for name in ("gtk3", "gtk2", "sdl3", "sdl2", "cocoa", "coreaudio", "alsa", "oss", "pulse")
]
MAKE = ["make", "-j4"]
PREREQUISITES = {"cc": "CC", "make": "MAKE"}
INSTALL_HINT = (
    "Install a C compiler and make, then rerun. On Apple Silicon macOS run "
    "`xcode-select --install`; on Ubuntu 24.04 run "
    "`sudo apt-get install build-essential pkg-config`. "
    "See guidance/starter/toolchain.md#instrumented-xroar."
)


class Edit(BaseModel):
    model_config = ConfigDict(frozen=True)

    anchor: str
    replacement: str


class FilePatch(BaseModel):
    """Exact edits to one pristine source file, identified by its SHA-256."""

    model_config = ConfigDict(frozen=True)

    path: str
    pristine_sha256: str
    edits: tuple[Edit, ...]


class Provenance(BaseModel):
    """What was built, from what, and the hash of what it produced."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    archive_url: str
    archive_sha256: str
    patch_sha256: str
    patched_sha256: dict[str, str]
    configure: list[str]
    make: list[str]
    executable: str
    executable_sha256: str
    host: str


# --- Pure decisions -------------------------------------------------------------------------


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hook(name: str, hooks: Path = HOOKS) -> str:
    return (hooks / name).read_text()


def recipe(hooks: Path = HOOKS) -> tuple[FilePatch, ...]:
    """Every change made to the pinned XRoar sources; anything else stays pristine."""
    trap = "static void handle_trap(void *sptr) {\n\tstruct trap_def *trap = sptr;"
    snapshot = "\t\twrite_snapshot(trap->snap);\n"
    null_render = (
        "static void null_render(void *sptr, unsigned burst, unsigned npixels, uint8_t const *data)"
    )
    return (
        FilePatch(
            path="src/xroar.c",
            pristine_sha256="6898598f808f1afece007781ea05d89dd28081b1752887d09b5eee7a6f83e0f1",
            edits=(
                Edit(
                    anchor=trap,
                    replacement=hook("keys.c", hooks)
                    + "\n"
                    + trap
                    + "\n\tcoco_keys_trap(trap->cond);",
                ),
                Edit(
                    anchor=snapshot,
                    replacement=snapshot + "\t\tcoco_snapshot_written(trap->snap);\n",
                ),
            ),
        ),
        FilePatch(
            path="src/null/ui_null.c",
            pristine_sha256="b813f70b890375c467dc1c7135e4172884ee659c1e6f63ef058f929d83cca85c",
            edits=(
                Edit(
                    anchor="#include <stdlib.h>\n",
                    replacement='#include <stdio.h>\n#include <stdlib.h>\n\n#include "events.h"\n',
                ),
                Edit(anchor=null_render + ";\n", replacement=hook("video.c", hooks)),
                Edit(
                    anchor="struct vo_interface *vo = xmalloc(sizeof(*vo));",
                    replacement="struct vo_interface *vo = vo_interface_new(sizeof(*vo));",
                ),
                Edit(
                    anchor="*vo = (struct vo_interface){0};", replacement="coco_video_attach(vo);"
                ),
                Edit(
                    anchor="\tvo->render_line = DELEGATE_AS3(void, unsigned, unsigned, uint8cp, "
                    "null_render, vo->renderer);\n\n",
                    replacement="",
                ),
                Edit(
                    anchor="\n"
                    + null_render
                    + " {\n\t(void)sptr;\n\t(void)burst;\n\t(void)npixels;\n\t(void)data;\n}\n",
                    replacement="",
                ),
            ),
        ),
        FilePatch(
            path="src/null/ao_null.c",
            pristine_sha256="e9fa06289dab8a8d025c21d38c0cc2c6c2b44cd7248443197aad6af83ece124f",
            edits=(
                Edit(
                    anchor="#include <signal.h>\n",
                    replacement="#include <signal.h>\n#include <stdio.h>\n",
                ),
                Edit(
                    anchor="static void *new(void *cfg);\n",
                    replacement=hook("audio.c", hooks) + "\nstatic void *new(void *cfg);\n",
                ),
                Edit(
                    anchor="sound_interface_new(NULL, SOUND_FMT_NULL, 44100, 1, 1024)",
                    replacement="sound_interface_new(coco_audio_buffer, SOUND_FMT_S16_LE, "
                    "COCO_AUDIO_RATE, 1, COCO_AUDIO_FRAMES)",
                ),
                Edit(
                    anchor="\taonull->last_pause_ms = current_time();\n\treturn aonull;",
                    replacement="\taonull->last_pause_ms = current_time();\n"
                    "\tcoco_audio_open();\n\treturn aonull;",
                ),
                Edit(
                    anchor="\tsound_interface_free(aonull->public.sound_interface);",
                    replacement="\tcoco_audio_close();\n"
                    "\tsound_interface_free(aonull->public.sound_interface);",
                ),
                Edit(
                    anchor="static void *ao_null_write_buffer(void *sptr, void *buffer) {\n",
                    replacement="static void *ao_null_write_buffer(void *sptr, void *buffer) {\n"
                    "\tcoco_audio_write(buffer);\n",
                ),
            ),
        ),
        # Unlimited speed normally forces a ten-frame skip; capture needs every frame.
        FilePatch(
            path="src/dragon/dragon.c",
            pristine_sha256="12e686625bb0c0a1c1122cc39db9d1f12c102647a99965f5f1eb97b598aeaa47",
            edits=(
                Edit(
                    anchor="\t\tmd->frameskip = 10;\n",
                    replacement="\t\tmd->frameskip = md->configured_frameskip;\n",
                ),
            ),
        ),
        FilePatch(
            path="src/coco3.c",
            pristine_sha256="4e70fc1de1bf0b801be79815a686ae62360f87419accf78bea89da23c9d41c9d",
            edits=(
                Edit(
                    anchor="\t\tmp->frameskip = 10;\n",
                    replacement="\t\tmp->frameskip = mp->configured_frameskip;\n",
                ),
            ),
        ),
    )


def replace_once(text: str, anchor: str, replacement: str, path: str) -> str:
    if (count := text.count(anchor)) != 1:
        raise ValueError(
            f"{path}: expected one instrumentation anchor, found {count}: {anchor[:60]!r}"
        )
    return text.replace(anchor, replacement, 1)


def apply(patch: FilePatch, source: bytes) -> bytes:
    """Patch pristine bytes only; drifted or already patched source is refused."""
    if sha256(source) != patch.pristine_sha256:
        raise ValueError(
            f"{patch.path} is not the pristine XRoar {VERSION} source; "
            "the archive or a previous patch changed it."
        )
    text = source.decode()
    for edit in patch.edits:
        text = replace_once(text, edit.anchor, edit.replacement, patch.path)
    return text.encode()


def patch_digest(patches: Iterable[FilePatch]) -> str:
    """Identify the patch itself: pristine hashes, anchors and hook text."""
    return sha256(json.dumps([p.model_dump() for p in patches], sort_keys=True).encode())


def key_names(hooks: Path = HOOKS) -> tuple[str, ...]:
    """XRoar key names the keyboard hook accepts, read from the hook itself."""
    return tuple(re.findall(r'\{ "(\w+)", DSCAN_\w+ \}', hook("keys.c", hooks)))


def stale_reason(home: Path, patches: tuple[FilePatch, ...]) -> str | None:
    """Why the recorded build cannot be used, or None when every hash still matches."""
    try:
        record = Provenance.model_validate_json((home / RECORD).read_text())
    except FileNotFoundError:
        return "not built yet"
    except ValidationError:
        return "its build record is unreadable"
    if record.archive_sha256 != ARCHIVE_SHA256:
        return "the pinned XRoar source changed"
    if record.patch_sha256 != patch_digest(patches):
        return "the hooks or patch changed"
    for name, expected in {
        **record.patched_sha256,
        record.executable: record.executable_sha256,
    }.items():
        path = home / name
        if not path.is_file() or sha256(path.read_bytes()) != expected:
            return f"{name} no longer matches its build record"
    return None


# --- Imperative shell -----------------------------------------------------------------------


class BuildHost:
    """Gateway for executable discovery, downloads and build processes."""

    def which(self, name: str) -> str | None:
        return shutil.which(name)

    def download(self, url: str, destination: Path) -> None:
        with urllib.request.urlopen(url, timeout=60) as response:
            destination.write_bytes(response.read())

    def run(self, command: list[str], cwd: Path, log: Path) -> None:
        with log.open("w") as stream:
            subprocess.run(
                command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=900
            )


def missing_prerequisites(host: BuildHost) -> list[str]:
    return [
        name
        for name, variable in PREREQUISITES.items()
        if not host.which(os.environ.get(variable, name))
    ]


def extract(archive: Path, patches: tuple[FilePatch, ...], work: Path) -> dict[str, str]:
    """Unpack the pinned archive and patch it; returns the patched files' hashes."""
    with tarfile.open(archive) as source:
        source.extractall(work, filter="data")
    hashes = {}
    for patch in patches:
        path = work / TREE / patch.path
        path.write_bytes(apply(patch, path.read_bytes()))
        hashes[str(Path(TREE) / patch.path)] = sha256(path.read_bytes())
    return hashes


def build(root: Path, host: BuildHost, patches: tuple[FilePatch, ...]) -> Provenance:
    """Configure and make in a fresh folder, then replace the previous build."""
    archive = cached_source("xroar", root, host.download)
    home = root / HOME
    work = home.with_name(home.name + ".building")
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    patched = extract(archive, patches, work)
    tree = work / TREE
    host.run(CONFIGURE, tree, work / "configure.log")
    host.run(MAKE, tree, work / "make.log")
    record = Provenance(
        archive_url=URL,
        archive_sha256=ARCHIVE_SHA256,
        patch_sha256=patch_digest(patches),
        patched_sha256=patched,
        configure=CONFIGURE,
        make=MAKE,
        executable=str(EXECUTABLE),
        executable_sha256=sha256((work / EXECUTABLE).read_bytes()),
        host=f"{platform.system()} {platform.machine()}",
    )
    (work / RECORD).write_text(record.model_dump_json(indent=2) + "\n")
    shutil.rmtree(home, ignore_errors=True)
    work.rename(home)
    return record


def ensure(
    root: Path = ROOT, host: BuildHost | None = None, say: Callable[[str], None] = print
) -> Path:
    """Return the verified instrumented executable, building it first when needed."""
    host = host or BuildHost()
    patches = recipe()
    home = root / HOME
    if (reason := stale_reason(home, patches)) is None:
        return home / EXECUTABLE
    if missing := missing_prerequisites(host):
        raise ValueError(
            f"The instrumented XRoar ({reason}) needs {' and '.join(missing)}, which "
            f"{'is' if len(missing) == 1 else 'are'} not installed. {INSTALL_HINT}"
        )
    say(f"Building the instrumented XRoar once ({reason}); this takes a minute or two.")
    build(root, host, patches)
    if (reason := stale_reason(home, patches)) is not None:
        raise ValueError(f"The instrumented XRoar build did not verify: {reason}.")
    return home / EXECUTABLE


def status(root: Path = ROOT, host: BuildHost | None = None) -> str:
    """One line for doctor.py: built and verified, or what building it needs."""
    host = host or BuildHost()
    home = root / HOME
    if (reason := stale_reason(home, recipe())) is None:
        return f"built and verified: {home / EXECUTABLE}"
    missing = missing_prerequisites(host)
    needs = f"missing {', '.join(missing)}. {INSTALL_HINT}" if missing else "cc and make found"
    return f"{reason}; scripts/coco.py builds it on first use ({needs})"


def main(argv: list[str] | None = None, host: BuildHost | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("status", "build"), help="report the build, or build it if needed"
    )
    arguments = parser.parse_args(argv)
    try:
        if arguments.action == "status":
            print(status(ROOT, host))
        else:
            print(ensure(ROOT, host))
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
