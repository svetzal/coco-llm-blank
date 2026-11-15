"""Build the one instrumented XRoar that coco.py uses to capture screens, keys and sound.

It is the pinned XRoar release archive with the patch series in
scripts/xroar_patches/ applied. It is built once, into ignored
local/toolchain/xroar-instrumented/, the first time a project asks for one of
those abilities, and rebuilt when the pinned release, the series or the build
output no longer match the recorded provenance. Ordinary build, run and check
keep using the installed XRoar and need no C compiler.

The series is carried forward to new XRoar releases with
scripts/xroar_upstream.py; see guidance/starter/xroar-patch.md.
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
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from native import ROOT, cached_source
from pydantic import BaseModel, ConfigDict, ValidationError

PATCHES = Path(__file__).resolve().parent / "xroar_patches"
PIN = "upstream.json"
HOME = Path("local/toolchain/xroar-instrumented")
RECORD = "build.json"
# The series adds source files to src/Makefile.am, so the build files are regenerated.
AUTORECONF = ["autoreconf", "-fi"]
# No window, no host audio: only the null UI and null audio modules are needed.
CONFIGURE = ["./configure"] + [
    f"--without-{name}"
    for name in ("gtk3", "gtk2", "sdl3", "sdl2", "cocoa", "coreaudio", "alsa", "oss", "pulse")
]
MAKE = ["make", "-j4"]
# Each tool, and the environment variable that names a substitute for it.
PREREQUISITES = {
    "cc": "CC",
    "make": "MAKE",
    "autoreconf": None,
    "automake": None,
    "pkg-config": None,
}
INSTALL_HINT = (
    "Install a C compiler, make, Autoconf, Automake and pkg-config, then rerun. "
    "On Apple Silicon macOS run `xcode-select --install` and "
    "`brew install autoconf automake pkgconf`; on Ubuntu 24.04 run "
    "`sudo apt-get install build-essential pkg-config autoconf automake`. "
    "See guidance/starter/toolchain.md#instrumented-xroar."
)
EMPTY_BLOB = "0" * 40
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
UNSUPPORTED = ("deleted file", "rename ", "copy ", "similarity", "old mode", "new mode", "Binary")


class Upstream(BaseModel):
    """The pinned XRoar release: its git tag and its checksum-pinned source archive."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    tag: str
    tag_commit: str
    git_url: str
    archive_url: str
    archive_sha256: str

    @property
    def tree(self) -> str:
        return f"xroar-{self.version}"


class Hunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    old_start: int
    lines: tuple[str, ...]


class FileChange(BaseModel):
    """One file in a patch; the git blob hashes name its exact before and after bytes."""

    model_config = ConfigDict(frozen=True)

    path: str
    old_blob: str | None
    new_blob: str
    hunks: tuple[Hunk, ...]


class Patch(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    subject: str
    changes: tuple[FileChange, ...]


class Series(BaseModel):
    model_config = ConfigDict(frozen=True)

    patches: tuple[Patch, ...]
    digest: str
    text: str


class Provenance(BaseModel):
    """What was built, from what, and the hash of what it produced."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    upstream_version: str
    tag: str
    tag_commit: str
    archive_url: str
    archive_sha256: str
    series: list[str]
    series_sha256: str
    patched_sha256: dict[str, str]
    commands: dict[str, list[str]]
    tools: dict[str, str]
    executable: str
    executable_sha256: str
    host: str


# --- Pure decisions -------------------------------------------------------------------------


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    """The object name git gives these bytes; patches name files by it."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def subject_of(name: str, header: list[str]) -> str:
    for index, line in enumerate(header):
        if line.startswith("Subject: "):
            folded = [line[9:]] + [
                more.strip() for more in header[index + 1 :] if more.startswith((" ", "\t"))
            ]
            return re.sub(r"^\[PATCH[^]]*\]\s*", "", " ".join(folded))
    raise ValueError(f"{name}: no Subject line; export the series with git format-patch.")


def checked_path(name: str, path: str) -> str:
    parts = PurePosixPath(path).parts
    if not parts or PurePosixPath(path).is_absolute() or ".." in parts:
        raise ValueError(f"{name}: refusing a patch path outside the XRoar tree: {path!r}")
    return path


def hunk_lines(where: str, body: list[str], old_left: int, new_left: int) -> list[str]:
    """Exactly the lines a hunk header counts: context and removals, context and additions."""
    lines = []
    while old_left > 0 or new_left > 0:
        line = body[len(lines)] if len(lines) < len(body) else ""
        kind = line[:1]
        if (
            kind not in (" ", "-", "+")
            or (kind != "+" and not old_left)
            or (kind != "-" and not new_left)
        ):
            raise ValueError(f"{where}: a hunk is truncated or malformed")
        old_left -= kind != "+"
        new_left -= kind != "-"
        lines.append(line)
    return lines


def parse_hunks(name: str, path: str, body: list[str]) -> tuple[Hunk, ...]:
    hunks, index = [], 0
    while index < len(body) and body[index]:
        if not (match := HUNK.match(body[index])):
            raise ValueError(f"{name}: {path}: unexpected line {body[index][:60]!r}")
        old, new = int(match[2] or 1), int(match[4] or 1)
        lines = hunk_lines(f"{name}: {path}", body[index + 1 :], old, new)
        hunks.append(Hunk(old_start=int(match[1]), lines=tuple(lines)))
        index += 1 + len(lines)
    if any(body[index:]):
        raise ValueError(f"{name}: {path}: unexpected text after the last hunk")
    return tuple(hunks)


def parse_change(name: str, section: list[str]) -> FileChange:
    body = next((i for i, line in enumerate(section) if line.startswith("@@")), len(section))
    meta = section[:body]
    if unsupported := [line for line in meta if line.startswith(UNSUPPORTED)]:
        raise ValueError(f"{name}: unsupported change {unsupported[0]!r}; only edits and new files")
    index = next((m for line in meta if (m := re.match(r"index (\w+)\.\.(\w+)", line))), None)
    if not index or len(index[1]) != 40 or len(index[2]) != 40:
        raise ValueError(f"{name}: export the series with git format-patch --full-index.")
    target = next((line[6:] for line in meta if line.startswith("+++ b/")), None)
    if target is None:
        raise ValueError(f"{name}: a file change has no +++ line")
    path = checked_path(name, target)
    new_file = any(line.startswith("new file mode") for line in meta)
    return FileChange(
        path=path,
        old_blob=None if new_file else index[1],
        new_blob=index[2],
        hunks=parse_hunks(name, path, section[body:]),
    )


def parse_patch(name: str, text: str) -> Patch:
    """Read one git format-patch file: its subject and each file it edits or adds."""
    text = re.sub(r"\n-- \n[^\n]*\n*\Z", "\n", text)
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.startswith("diff --git ")]
    if not starts:
        raise ValueError(f"{name}: no file changes")
    return Patch(
        name=name,
        subject=subject_of(name, lines[: starts[0]]),
        changes=tuple(
            parse_change(name, lines[start:end])
            for start, end in zip(starts, [*starts[1:], len(lines)], strict=True)
        ),
    )


def series_digest(files: list[tuple[str, bytes]]) -> str:
    """Identify the series by each patch file's name, order and bytes."""
    return sha256(json.dumps([[name, sha256(data)] for name, data in files]).encode())


def parse_series(files: list[tuple[str, bytes]]) -> Series:
    if not files:
        raise ValueError("The XRoar patch series is empty.")
    return Series(
        patches=tuple(parse_patch(name, data.decode()) for name, data in files),
        digest=series_digest(files),
        text="".join(data.decode() for _, data in files),
    )


def hunk_index(hunk: Hunk) -> int:
    """Where a hunk's first old line sits; a pure insertion follows its start line."""
    removes_or_keeps = any(line[0] != "+" for line in hunk.lines)
    return hunk.old_start - 1 if removes_or_keeps else hunk.old_start


def apply_hunks(where: str, lines: list[bytes], hunks: tuple[Hunk, ...]) -> bytes:
    result, position = [], 0
    for hunk in hunks:
        start = hunk_index(hunk)
        if start < position:
            raise ValueError(f"{where}: hunks overlap")
        result += lines[position:start]
        for line in hunk.lines:
            content = (line[1:] + "\n").encode()
            if line[0] != "+":
                if start >= len(lines) or lines[start] != content:
                    raise ValueError(f"{where}: a hunk does not match the source")
                start += 1
            if line[0] != "-":
                result.append(content)
        position = start
    return b"".join(result + lines[position:])


def apply_change(patch: str, change: FileChange, source: bytes | None) -> bytes:
    """Patch exactly the bytes the patch names; drifted, missing or patched files are refused."""
    where = f"{patch}: {change.path}"
    if change.old_blob is None and source is not None:
        raise ValueError(f"{where} already exists, but the patch adds it.")
    if change.old_blob is not None and source is None:
        raise ValueError(f"{where} is missing from the XRoar source.")
    if change.old_blob is not None and git_blob(source) != change.old_blob:
        raise ValueError(
            f"{where} is not the XRoar source this patch was made against "
            f"(expected git blob {change.old_blob[:12]}, found {git_blob(source)[:12]}). "
            "The source is a different release or already patched; see "
            "guidance/starter/xroar-patch.md."
        )
    result = apply_hunks(where, (source or b"").splitlines(keepends=True), change.hunks)
    if git_blob(result) != change.new_blob:
        raise ValueError(f"{where}: applying the patch did not give the bytes it records.")
    return result


def apply_series(series: Series, read: Callable[[str], bytes | None]) -> dict[str, bytes]:
    """The final bytes of every file the series touches, applied patch by patch."""
    files: dict[str, bytes | None] = {}
    for patch in series.patches:
        for change in patch.changes:
            current = files[change.path] if change.path in files else read(change.path)
            files[change.path] = apply_change(patch.name, change, current)
    return files


def key_names(series: Series) -> tuple[str, ...]:
    """XRoar key names the keyboard equipment accepts, read from the series itself."""
    return tuple(dict.fromkeys(re.findall(r'\{ "(\w+)", DSCAN_\w+ \}', series.text)))


def stale_reason(home: Path, pin: Upstream, series: Series) -> str | None:
    """Why the recorded build cannot be used, or None when every hash still matches."""
    try:
        record = Provenance.model_validate_json((home / RECORD).read_text())
    except FileNotFoundError:
        return "not built yet"
    except ValidationError:
        return "its build record is unreadable or from an older format"
    if (record.upstream_version, record.archive_sha256) != (pin.version, pin.archive_sha256):
        return "the pinned XRoar release changed"
    if record.series_sha256 != series.digest:
        return "the patch series changed"
    for name, expected in {
        **record.patched_sha256,
        record.executable: record.executable_sha256,
    }.items():
        path = home / name
        if not path.is_file() or sha256(path.read_bytes()) != expected:
            return f"{name} no longer matches its build record"
    return None


# --- Imperative shell -----------------------------------------------------------------------


def load_pin(patches: Path = PATCHES) -> Upstream:
    return Upstream.model_validate_json((patches / PIN).read_text())


def load_series(patches: Path = PATCHES) -> Series:
    return parse_series(
        [(path.name, path.read_bytes()) for path in sorted(patches.glob("*.patch"))]
    )


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

    def version(self, name: str) -> str:
        result = subprocess.run([name, "--version"], capture_output=True, text=True, check=True)
        return result.stdout.splitlines()[0]


def missing_prerequisites(host: BuildHost) -> list[str]:
    return [
        name
        for name, variable in PREREQUISITES.items()
        if not host.which(os.environ.get(variable, name) if variable else name)
    ]


def extract(archive: Path, pin: Upstream, series: Series, work: Path) -> dict[str, str]:
    """Unpack the release archive and apply the series; returns the patched files' hashes."""
    with tarfile.open(archive) as source:
        source.extractall(work, filter="data")
    tree = work / pin.tree
    if not tree.is_dir():
        raise ValueError(f"The XRoar {pin.version} archive does not unpack to {pin.tree}/.")

    def read(path: str) -> bytes | None:
        return (tree / path).read_bytes() if (tree / path).is_file() else None

    hashes = {}
    for path, data in apply_series(series, read).items():
        (tree / path).parent.mkdir(parents=True, exist_ok=True)
        (tree / path).write_bytes(data)
        hashes[f"{pin.tree}/{path}"] = sha256(data)
    return hashes


def build(host: BuildHost, pin: Upstream, series: Series, archive: Path, home: Path) -> Provenance:
    """Patch, regenerate, configure and make in a fresh folder, then replace the old build."""
    if sha256(archive.read_bytes()) != pin.archive_sha256:
        raise ValueError(f"{archive} does not match the pinned XRoar {pin.version} checksum.")
    work = home.with_name(home.name + ".building")
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    patched = extract(archive, pin, series, work)
    tree = work / pin.tree
    commands = {"autoreconf": AUTORECONF, "configure": CONFIGURE, "make": MAKE}
    for step, command in commands.items():
        host.run(command, tree, work / f"{step}.log")
    executable = f"{pin.tree}/src/xroar"
    record = Provenance(
        upstream_version=pin.version,
        tag=pin.tag,
        tag_commit=pin.tag_commit,
        archive_url=pin.archive_url,
        archive_sha256=pin.archive_sha256,
        series=[patch.name for patch in series.patches],
        series_sha256=series.digest,
        patched_sha256=patched,
        commands=commands,
        tools={name: host.version(name) for name in ("autoreconf", "automake")},
        executable=executable,
        executable_sha256=sha256((work / executable).read_bytes()),
        host=f"{platform.system()} {platform.machine()}",
    )
    (work / RECORD).write_text(record.model_dump_json(indent=2) + "\n")
    shutil.rmtree(home, ignore_errors=True)
    work.rename(home)
    return record


def build_verified(
    host: BuildHost,
    pin: Upstream,
    series: Series,
    archive: Callable[[], Path],
    home: Path,
    say: Callable[[str], None],
) -> Path:
    """Return the executable built from this pin and series, building it when needed."""
    if (reason := stale_reason(home, pin, series)) is None:
        return home / pin.tree / "src/xroar"
    if missing := missing_prerequisites(host):
        raise ValueError(
            f"The instrumented XRoar ({reason}) needs {', '.join(missing)}, which "
            f"{'is' if len(missing) == 1 else 'are'} not installed. {INSTALL_HINT}"
        )
    say(f"Building the instrumented XRoar {pin.version} ({reason}); this takes a minute or two.")
    build(host, pin, series, archive(), home)
    if (reason := stale_reason(home, pin, series)) is not None:
        raise ValueError(f"The instrumented XRoar build did not verify: {reason}.")
    return home / pin.tree / "src/xroar"


def ensure(
    root: Path = ROOT, host: BuildHost | None = None, say: Callable[[str], None] = print
) -> Path:
    """Return the verified instrumented executable, building it first when needed."""
    host = host or BuildHost()
    return build_verified(
        host,
        load_pin(),
        load_series(),
        lambda: cached_source("xroar", root, host.download),
        root / HOME,
        say,
    )


def status(root: Path = ROOT, host: BuildHost | None = None) -> str:
    """One line for doctor.py: built and verified, or what building it needs."""
    host = host or BuildHost()
    home, pin = root / HOME, load_pin()
    if (reason := stale_reason(home, pin, load_series())) is None:
        return f"built and verified: {home / pin.tree / 'src/xroar'}"
    missing = missing_prerequisites(host)
    needs = f"missing {', '.join(missing)}. {INSTALL_HINT}" if missing else "build tools found"
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
