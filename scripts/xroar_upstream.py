"""Track XRoar releases and carry the instrumented XRoar's patch series forward.

  report   compare the pin with upstream's git tags and download page
  trial    rebase the series onto a release in local/system/xroar-<version>/ with
           git am -3, build it, and compare capture checks with the pinned build
  adopt    write a passing trial's series and pin into scripts/xroar_patches/

The procedure is guidance/starter/xroar-patch.md. Nothing here commits, pushes,
submits a patch or contacts anyone. Downloaded archives and clones are kept
under ignored local/ and only XRoar's documented autoreconf, configure and make
build is run from them.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Literal

import instrumented_xroar as ix
from instrumented_xroar import BuildHost, Upstream
from native import ROOT, tool_path
from pydantic import BaseModel, ConfigDict, ValidationError

DOWNLOADS = "https://www.6809.org.uk/xroar/dl/"
CLONE = Path("local/toolchain-sources/xroar.git")
WORK = Path("local/system")
# Trial clones commit as a neutral identity, without the owner's git hooks.
IDENTITY = {"user.name": "CoCo starter", "user.email": "coco-starter@example.invalid"}
EXPORT = ["format-patch", "--quiet", "--full-index", "--no-signature", "--zero-commit"]
BRANCH = "coco-capture"
# Checks whose captures must match the pinned build's, byte for byte.
EQUIVALENCE = (
    ("examples/first-screen", ("--video",)),
    ("examples/collect-room", ()),  # [capture] video and audio; main and journey, CoCo 1, 2 and 3
    ("examples/sound-slots", ()),  # [capture] audio = true; main and square variants
    ("examples/timer-sound", ("--video",)),  # CoCo 3, both GIME revisions
)
PINNED, AGAIN = "pinned", "pinned-again"
RELEASE = re.compile(r"\d+(?:\.\d+)+")
NOTE = """# System: XRoar {version}

- Question: does the instrumented XRoar patch series carry forward to XRoar
  {version} with captures identical to the pinned {pinned} build?
- Where it came from: the procedure in guidance/starter/xroar-patch.md.
- Finished when: the series applies and builds, every equivalence check passes,
  and every capture difference is explained by an upstream ChangeLog entry; or
  the bump is rejected with the reason.
- Targets: CoCo 1, CoCo 2 and CoCo 3, the machines the equivalence checks use.

## Log
"""


class CheckRun(BaseModel):
    """One equivalence check: exit codes per build and how the trial's files compare."""

    model_config = ConfigDict(frozen=True)

    example: str
    arguments: list[str]
    exit_codes: dict[str, int]
    deterministic: bool
    identical: list[str]
    different: list[str]
    missing: list[str]
    extra: list[str]

    @property
    def passed(self) -> bool:
        return self.deterministic and not any(self.exit_codes.values())


class Trial(BaseModel):
    """What a trial rebased, built and compared, and its verdict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pin: Upstream
    application: str
    series: list[str]
    series_sha256: str
    build: ix.Provenance
    checks: list[CheckRun]
    verdict: Literal["identical", "different", "failed"]


# --- Pure decisions -------------------------------------------------------------------------


def release_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def releases(names: Iterable[str]) -> list[str]:
    """Release version numbers among tag or archive names, oldest first."""
    return sorted({name for name in names if RELEASE.fullmatch(name)}, key=release_key)


def tags_listed(ls_remote: str) -> list[str]:
    names = re.findall(r"refs/tags/([^\s^]+)", ls_remote)
    return releases(names)


def archives_listed(page: str) -> list[str]:
    return releases(re.findall(r"xroar-(\d+(?:\.\d+)+)\.tar\.gz", page))


def newer_than(pinned: str, versions: Iterable[str]) -> list[str]:
    return [v for v in releases(versions) if release_key(v) > release_key(pinned)]


def source_line(label: str, versions: list[str] | None) -> str:
    if versions is None:
        return f"  {label}: unavailable"
    return f"  {label}: newest {versions[-1]}" if versions else f"  {label}: no releases found"


def stock_line(pin: Upstream, stock: tuple[str, str] | None) -> str:
    if stock is None:
        return "Ordinary XRoar: not found; run uv run python scripts/native.py."
    path, banner = stock
    found = re.search(r"\d+(?:\.\d+)+", banner)
    version = found[0] if found else "unknown"
    match = "matches the pin" if version == pin.version else f"differs from the pin {pin.version}"
    return f"Ordinary XRoar: {path} is {version}; it {match}."


def report_lines(
    pin: Upstream,
    tags: list[str] | None,
    archives: list[str] | None,
    stock: tuple[str, str] | None,
) -> list[str]:
    known = [*(tags or []), *(archives or [])]
    ahead = newer_than(pin.version, known)
    if ahead:
        status = (
            f"Behind by {len(ahead)} release{'s' if len(ahead) > 1 else ''}: {', '.join(ahead)}. "
            f"Next: uv run python scripts/xroar_upstream.py trial {ahead[-1]}"
        )
    elif known:
        status = "Up to date with the newest upstream release."
    else:
        status = "Upstream releases could not be read."
    return [
        (
            f"Pinned: XRoar {pin.version} (tag {pin.tag}, base {pin.base_commit[:12]}, "
            f"archive sha256 {pin.archive_sha256[:12]})"
        ),
        "Upstream:",
        source_line(f"git tags at {pin.git_url}", tags),
        source_line(f"archives at {DOWNLOADS}", archives),
        status,
        stock_line(pin, stock),
    ]


def comparable(name: str, data: bytes) -> bytes:
    """Result records name the emulator's path; everything else must match exactly."""
    if not name.endswith(".json"):
        return data

    def without_emulator(value: object) -> object:
        if isinstance(value, dict):
            return {k: without_emulator(v) for k, v in value.items() if k != "emulator"}
        if isinstance(value, list):
            return [without_emulator(v) for v in value]
        return value

    return json.dumps(without_emulator(json.loads(data)), sort_keys=True).encode()


def compare(before: dict[str, bytes], after: dict[str, bytes]) -> dict[str, list[str]]:
    shared = sorted(before.keys() & after.keys())
    same = [n for n in shared if comparable(n, before[n]) == comparable(n, after[n])]
    return {
        "identical": same,
        "different": [n for n in shared if n not in same],
        "missing": sorted(before.keys() - after.keys()),
        "extra": sorted(after.keys() - before.keys()),
    }


def check_run(
    example: str,
    arguments: tuple[str, ...],
    captures: dict[str, dict[str, bytes]],
    codes: dict[str, int],
    trial: str,
) -> CheckRun:
    control = compare(captures[PINNED], captures[AGAIN])
    return CheckRun(
        example=example,
        arguments=list(arguments),
        exit_codes=codes,
        deterministic=bool(captures[PINNED]) and control["identical"] == sorted(captures[AGAIN]),
        **compare(captures[PINNED], captures[trial]),
    )


def verdict(checks: list[CheckRun]) -> Literal["identical", "different", "failed"]:
    if not all(check.passed for check in checks):
        return "failed"
    changed = any(check.different or check.missing or check.extra for check in checks)
    return "different" if changed else "identical"


def summary(trial: Trial) -> list[str]:
    lines = [
        (
            f"XRoar {trial.pin.version}: series {trial.application}; built "
            f"{trial.build.executable} (sha256 {trial.build.executable_sha256[:12]})."
        ),
        f"Archive sha256 {trial.pin.archive_sha256}; confirm it from an independent source.",
    ]
    for check in trial.checks:
        codes = ", ".join(f"{label} exit {code}" for label, code in check.exit_codes.items())
        lines.append(
            f"  {check.example} {' '.join(check.arguments)}: {codes}; "
            f"{len(check.identical)} identical, {len(check.different)} different, "
            f"{len(check.missing)} missing, {len(check.extra)} extra"
            + ("" if check.deterministic else "; the pinned build was not repeatable")
        )
        lines += [f"    differs: {name}" for name in check.different + check.missing + check.extra]
    lines.append(f"Verdict: {trial.verdict}.")
    return lines


# --- Imperative shell -----------------------------------------------------------------------


class UpstreamHost:
    """Gateway for git, downloads, the ordinary XRoar and coco.py check processes."""

    def git(self, arguments: list[str], cwd: Path | None = None) -> str:
        done = subprocess.run(
            ["git", *arguments], cwd=cwd, capture_output=True, text=True, check=True, timeout=600
        )
        return done.stdout

    def git_succeeds(self, arguments: list[str], cwd: Path) -> bool:
        done = subprocess.run(
            ["git", *arguments], cwd=cwd, capture_output=True, check=False, timeout=600
        )
        return done.returncode == 0

    def fetch_text(self, url: str) -> str:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read().decode()

    def download(self, url: str, destination: Path) -> None:
        with urllib.request.urlopen(url, timeout=120) as response:
            destination.write_bytes(response.read())

    def stock_xroar(self) -> tuple[str, str] | None:
        if not (path := tool_path("xroar")):
            return None
        done = subprocess.run(
            [path, "-version"], capture_output=True, text=True, check=False, timeout=30
        )
        return path, (done.stdout.splitlines() or ["unknown"])[0]

    def check(self, example: Path, arguments: list[str], xroar: Path, log: Path) -> int:
        command = [sys.executable, "scripts/coco.py", "check", str(example), *arguments]
        environment = os.environ | {"XROAR_INSTRUMENTED": str(xroar)}
        with log.open("w") as stream:
            done = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
            )
        return done.returncode


def report(host: UpstreamHost, say: Callable[[str], None] = print) -> int:
    pin = ix.load_pin()
    try:
        tags = tags_listed(host.git(["ls-remote", "--tags", pin.git_url]))
    except (OSError, subprocess.SubprocessError):
        tags = None
    try:
        archives = archives_listed(host.fetch_text(DOWNLOADS))
    except OSError:
        archives = None
    for line in report_lines(pin, tags, archives, host.stock_xroar()):
        say(line)
    return 1 if tags is None and archives is None else 0


def work_for(root: Path, version: str) -> Path:
    if not RELEASE.fullmatch(version):
        raise ValueError(f"{version!r} is not an XRoar release number such as 1.13.")
    return root / WORK / f"xroar-{version}"


def update_clone(root: Path, host: UpstreamHost, url: str) -> Path:
    clone = root / CLONE
    if not clone.is_dir():
        clone.parent.mkdir(parents=True, exist_ok=True)
        host.git(["clone", "--quiet", url, str(clone)])
    else:
        host.git(["fetch", "--quiet", "--tags", "origin"], clone)
    return clone


def configure_trial_clone(repository: Path, host: UpstreamHost) -> None:
    hooks = repository / ".git/no-hooks"
    hooks.mkdir(exist_ok=True)
    for key, value in {**IDENTITY, "core.hooksPath": str(hooks)}.items():
        host.git(["config", key, value], repository)


def start_rebase(
    clone: Path, repository: Path, pinned: str, tag: str, patches: Path, host: UpstreamHost
) -> bool:
    """Replay the series on the pinned tag, then rebase it onto the release; False on conflict.

    Each patch names the bytes it expects, and a later patch can expect a file an earlier one
    changed. Applying the series to its own tag first makes those intermediate versions real
    commits, so the rebase can merge every file three ways.
    """
    host.git(["clone", "--quiet", str(clone), str(repository)])
    configure_trial_clone(repository, host)
    host.git(["checkout", "--quiet", "-b", BRANCH, f"{pinned}^{{commit}}"], repository)
    files = [str(path) for path in sorted(patches.glob("*.patch"))]
    if not host.git_succeeds(["am", "--quiet", *files], repository):
        host.git(["am", "--abort"], repository)
        raise ValueError(f"The committed series does not apply to its pinned base {pinned}.")
    rebase = ["rebase", "--quiet", "--onto", f"{tag}^{{commit}}", f"{pinned}^{{commit}}", BRANCH]
    return host.git_succeeds(rebase, repository)


def rebasing(repository: Path) -> bool:
    return any((repository / ".git" / state).exists() for state in ("rebase-merge", "rebase-apply"))


def conflict_message(repository: Path, host: UpstreamHost, version: str) -> str:
    subject = host.git(["log", "-1", "--format=%s", "REBASE_HEAD"], repository).strip()
    files = host.git(["diff", "--name-only", "--diff-filter=U"], repository).split()
    return (
        f"The series does not rebase cleanly onto XRoar {version}: {subject!r} conflicts in "
        f"{', '.join(files) or 'no marked files; run git status'}. Resolve it in "
        f"{repository}, git add the files and run git rebase --continue, then rerun "
        f"uv run python scripts/xroar_upstream.py trial {version}."
    )


def rebased_series(
    work: Path, release: Upstream, pinned: Upstream, root: Path, host: UpstreamHost, fresh: bool
) -> tuple[Upstream, str]:
    """The release with its tag and base resolved to commits, and how the series applied."""
    repository = work / "xroar"
    if fresh:
        shutil.rmtree(repository, ignore_errors=True)
    state = work / "application"
    if not repository.is_dir():
        clone = update_clone(root, host, pinned.git_url)
        base = release.base_commit
        clean = start_rebase(clone, repository, pinned.base_commit, base, ix.PATCHES, host)
        state.write_text("clean" if clean else "resolved by hand")
    if rebasing(repository):
        raise ValueError(conflict_message(repository, host, release.version))

    def commit(name: str) -> str:
        return host.git(["rev-parse", f"{name}^{{commit}}"], repository).strip()

    resolved = release.model_copy(
        update={"tag_commit": commit(release.tag), "base_commit": commit(release.base_commit)}
    )
    if not host.git_succeeds(
        ["merge-base", "--is-ancestor", resolved.base_commit, BRANCH], repository
    ):
        raise ValueError(
            f"The trial branch {BRANCH} is not based on {release.base_commit}. Rebase it in "
            f"{repository} with git rebase --onto {release.base_commit} <old base> {BRANCH}."
        )
    return resolved, state.read_text()


def export_series(work: Path, base: str, host: UpstreamHost) -> Path:
    series = work / "series"
    shutil.rmtree(series, ignore_errors=True)
    host.git([*EXPORT, "-o", str(series), f"{base}..{BRANCH}"], work / "xroar")
    return series


def release_archive(work: Path, pin: Upstream, host: UpstreamHost, expected: str | None) -> Path:
    archive = work / f"{pin.tree}.tar.gz"
    if not archive.is_file():
        host.download(pin.archive_url, archive)
    found = ix.sha256(archive.read_bytes())
    if expected and found != expected:
        raise ValueError(f"{archive} has sha256 {found}, not the {expected} you gave.")
    return archive


def captured(output: Path, before: dict[str, int]) -> dict[str, bytes]:
    """Files the check wrote or rewrote in the project's build folder."""
    return {
        path.name: path.read_bytes()
        for path in sorted(output.glob("*"))
        if path.is_file() and before.get(path.name) != path.stat().st_mtime_ns
    }


def run_check(
    root: Path,
    example: str,
    arguments: tuple[str, ...],
    builds: dict[str, Path],
    host: UpstreamHost,
) -> CheckRun:
    """Run one check against each build, keeping what each run wrote under the work folder."""
    work = work_for(root, next(label for label in builds if label not in (PINNED, AGAIN)))
    output = root / "build" / Path(example).name
    captures, codes = {}, {}
    for label, xroar in builds.items():
        output.mkdir(parents=True, exist_ok=True)
        before = {p.name: p.stat().st_mtime_ns for p in output.glob("*") if p.is_file()}
        keep = work / "captures" / label / Path(example).name
        shutil.rmtree(keep, ignore_errors=True)
        keep.mkdir(parents=True)
        codes[label] = host.check(root / example, list(arguments), xroar, keep / "check.log")
        captures[label] = captured(output, before)
        for name, data in captures[label].items():
            (keep / name).write_bytes(data)
    trial = next(label for label in builds if label not in (PINNED, AGAIN))
    return check_run(example, arguments, captures, codes, trial)


def run_trial(
    root: Path,
    version: str,
    host: UpstreamHost,
    builder: BuildHost,
    *,
    fresh: bool = False,
    expected: str | None = None,
    base: str | None = None,
    say: Callable[[str], None] = print,
) -> Trial:
    """Rebase, build and compare in the work folder; the result is also written to trial.json."""
    work = work_for(root, version)
    work.mkdir(parents=True, exist_ok=True)
    pinned = ix.load_pin()
    if not (work / "NOTES.md").exists():
        (work / "NOTES.md").write_text(NOTE.format(version=version, pinned=pinned.version))
    release = Upstream(
        version=version,
        tag=version,
        tag_commit=version,
        base_commit=base or version,
        git_url=pinned.git_url,
        archive_url=f"{DOWNLOADS}xroar-{version}.tar.gz",
        archive_sha256="0" * 64,
    )
    trial_pin, application = rebased_series(work, release, pinned, root, host, fresh)
    series_dir = export_series(work, trial_pin.base_commit, host)
    archive = release_archive(work, trial_pin, host, expected)
    trial_pin = trial_pin.model_copy(update={"archive_sha256": ix.sha256(archive.read_bytes())})
    series = ix.load_series(series_dir)
    executable = ix.build_verified(builder, trial_pin, series, lambda: archive, work / "build", say)
    baseline = ix.ensure(root, builder, say)
    builds = {PINNED: baseline, AGAIN: baseline, version: executable}
    checks = [run_check(root, example, args, builds, host) for example, args in EQUIVALENCE]
    trial = Trial(
        pin=trial_pin,
        application=application,
        series=[patch.name for patch in series.patches],
        series_sha256=series.digest,
        build=ix.Provenance.model_validate_json((work / "build" / ix.RECORD).read_text()),
        checks=checks,
        verdict=verdict(checks),
    )
    (work / "trial.json").write_text(trial.model_dump_json(indent=2) + "\n")
    return trial


def adopt(
    root: Path,
    version: str,
    confirmed_sha256: str,
    accept_differences: bool,
    patches: Path = ix.PATCHES,
    say: Callable[[str], None] = print,
) -> None:
    """Write a trial's tested series and pin into the repository; nothing is committed."""
    work = work_for(root, version)
    try:
        trial = Trial.model_validate_json((work / "trial.json").read_text())
    except (FileNotFoundError, ValidationError) as error:
        raise ValueError(f"No readable trial for XRoar {version}; run trial first.") from error
    if trial.verdict == "failed":
        raise ValueError(f"The XRoar {version} trial failed; it cannot be adopted.")
    if confirmed_sha256 != trial.pin.archive_sha256:
        raise ValueError(
            f"--sha256 {confirmed_sha256} is not the trial archive's {trial.pin.archive_sha256}."
        )
    if trial.verdict == "different" and not accept_differences:
        raise ValueError(
            "The trial's captures differ from the pinned build. Explain each difference "
            "from the upstream ChangeLog, then rerun with --accept-differences."
        )
    if ix.load_series(work / "series").digest != trial.series_sha256:
        raise ValueError(f"{work / 'series'} changed after the trial; run trial again.")
    for old in patches.glob("*.patch"):
        old.unlink()
    for new in sorted((work / "series").glob("*.patch")):
        shutil.copyfile(new, patches / new.name)
    (patches / ix.PIN).write_text(trial.pin.model_dump_json(indent=2) + "\n")
    cache = root / "local/toolchain-sources" / f"{trial.pin.tree}.tar.gz"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(work / f"{trial.pin.tree}.tar.gz", cache)
    say(
        f"Wrote {len(trial.series)} patches and the XRoar {version} pin to {patches}. "
        "Rebuild with uv run python scripts/instrumented_xroar.py build, run the checks, "
        "then commit scripts/xroar_patches/ as guidance/starter/xroar-patch.md describes."
    )


def parser() -> argparse.ArgumentParser:
    parse = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parse.add_subparsers(dest="command", required=True)
    commands.add_parser("report", help="compare the pin with upstream releases")
    trial = commands.add_parser("trial", help="rebase, build and compare a release")
    trial.add_argument("version", help="an XRoar release tag, such as 1.13")
    trial.add_argument(
        "--fresh", action="store_true", help="discard the trial clone and rebase again"
    )
    trial.add_argument("--sha256", help="require the release archive to have this SHA-256")
    trial.add_argument(
        "--base",
        help="upstream commit to rebase onto instead of the tag, when the release archive "
        "was made from a later commit",
    )
    write = commands.add_parser("adopt", help="write a trial's series and pin into the repository")
    write.add_argument("version", help="the release a trial passed for")
    write.add_argument("--sha256", required=True, help="the archive SHA-256 you confirmed")
    write.add_argument(
        "--accept-differences",
        action="store_true",
        help="adopt although captures differ; record each ChangeLog explanation",
    )
    return parse


def dispatch(arguments: argparse.Namespace, host: UpstreamHost, builder: BuildHost) -> int:
    if arguments.command == "report":
        return report(host)
    if arguments.command == "adopt":
        adopt(ROOT, arguments.version, arguments.sha256, arguments.accept_differences)
        return 0
    trial = run_trial(
        ROOT,
        arguments.version,
        host,
        builder,
        fresh=arguments.fresh,
        expected=arguments.sha256,
        base=arguments.base,
    )
    for line in summary(trial):
        print(line)
    return {"identical": 0, "different": 3, "failed": 1}[trial.verdict]


def main(
    argv: list[str] | None = None,
    host: UpstreamHost | None = None,
    builder: BuildHost | None = None,
) -> int:
    arguments = parser().parse_args(argv)
    try:
        return dispatch(arguments, host or UpstreamHost(), builder or BuildHost())
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
