"""Run explicitly selected validation scopes, each in its own process."""

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# name: (coverage targets; None means no coverage gate, prerequisites/heavy reason)
SCOPES = {
    "root": (
        ("scripts", "examples"),
        "full integrations, Docling models, native tools/all ROM profiles",
    ),
    "asset-loading": (("loading",), "native tools, CoCo 1/2 ROMs, headless execution"),
    "assets": (("prepare",), ""),
    "collect-room-journey": (
        ("experiments/collect-room-journey",),
        "pinned XRoar download and C build, CoCo 1/2 ROMs",
    ),
    "collect-room-output": (
        ("experiments/collect-room-output",),
        "cached COLLECT_ARCHIVE, C build, CoCo 1/2 ROMs",
    ),
    "game-state": (("experiments/game-state",), ""),
    "game-state-coco3": (("validate", "vectors"), "native tools, CoCo 3 ROM, headless execution"),
    "linux-onboarding": (None, ""),
    "macos-onboarding": (None, "installed lwasm; current-host boundary tests only"),
    "sudo-policy": (None, ""),
}


def commands(scope: str, output: Path) -> list[list[str]]:
    """Use each scope's coverage configuration without merging collections."""
    paths = ["scripts", "examples"] if scope == "root" else [f"experiments/{scope}"]
    config = ROOT / paths[0] / "coverage.ini"
    targets = SCOPES[scope][0]
    pytest = [
        sys.executable,
        "-m",
        "pytest",
        *paths,
        "-ra",
        "-p",
        "no:cacheprovider",
        f"--basetemp={output / 'tmp'}",
        f"--junitxml={output / 'results.xml'}",
    ]
    if targets is not None:
        pytest += [f"--cov={target}" for target in targets]
        pytest += [
            f"--cov-config={config if config.exists() else ROOT / 'pyproject.toml'}",
            "--cov-branch",
            "--cov-report=term-missing",
            f"--cov-report=json:{output / 'coverage.json'}",
        ]
    return [
        pytest,
        [sys.executable, "-m", "ruff", "check", *paths],
        [sys.executable, "-m", "ruff", "format", "--check", *paths],
    ]


def run_scope(scope: str, output: Path) -> int:
    """Retain merged stdout/stderr and the exact child status; stop on failure."""
    output.mkdir()
    env = {**os.environ, "COVERAGE_FILE": str(output / ".coverage"), "PYTHONDONTWRITEBYTECODE": "1"}
    for index, command in enumerate(commands(scope, output), 1):
        log = output / f"{index}.log"
        print(f"{scope}: {shlex.join(command)}\nLog: {log}", flush=True)
        with log.open("w") as stream:
            try:
                status = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    check=False,
                ).returncode
            except OSError as error:
                stream.write(f"{error}\n")
                status = 127
        (output / f"{index}.json").write_text(
            json.dumps({"command": command, "returncode": status, "log": str(log)}, indent=2) + "\n"
        )
        print(f"{scope}: exit {status}", flush=True)
        if status:
            return status if status > 0 else 128 - status
    return 0


def main(argv: list[str] | None = None) -> int:
    """List scopes or run a validated selection without provisioning anything."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("list", help="list scopes and prerequisites")
    run = subparsers.add_parser("run", help="run tests, Ruff, and format checks sequentially")
    run.add_argument("scopes", nargs="+", help="root, experiment names, or all (experiments only)")
    run.add_argument(
        "--heavy", action="store_true", help="allow heavy scopes and root integrations"
    )
    args = parser.parse_args(argv)
    if args.action == "list":
        for name, (targets, reason) in SCOPES.items():
            gate = "coverage 90%" if targets is not None else "no coverage gate"
            print(f"{name}: {gate}; {reason or 'light host tests'}")
        print("root --heavy: full integrations, Docling models and native tools/all ROM profiles")
        return 0
    selected = list(
        dict.fromkeys(
            name
            for scope in args.scopes
            for name in (list(SCOPES)[1:] if scope == "all" else [scope])
        )
    )
    unknown = [name for name in selected if name not in SCOPES]
    if unknown:
        parser.error(f"unknown scopes: {', '.join(unknown)}")
    heavy = [name for name in selected if SCOPES[name][1]]
    if heavy and not args.heavy:
        parser.error(f"requires --heavy (see list for prerequisites): {', '.join(heavy)}")
    parent = ROOT / "build/validation"
    parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    print(f"Evidence: {output}", flush=True)
    for scope in selected:
        status = run_scope(scope, output / scope)
        if status:
            return status
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
