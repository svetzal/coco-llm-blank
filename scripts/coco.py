"""Build, run, snapshot, or check a CoCo project folder described by its coco.toml.

A project folder holds main.asm, coco.toml and, optionally, expected.py: an
independent model of the memory each checkpoint must contain. All CoCo facts
(machine, firmware, memory layout, labels) live in those project files. This
tool only assembles with LWTOOLS and drives XRoar.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType

from native import ROOT, tool_path
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from roms import verify_installed

SETTINGS = "coco.toml"
MODEL = "expected.py"


class ProjectError(ValueError):
    """A project cannot be built, launched or checked as configured."""


class Machine(BaseModel):
    """One [targets.<name>] table: an XRoar machine and its validated firmware."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    firmware: str | None = None
    machine: str
    ram_kib: int = Field(gt=0)
    cpu: str | None = None
    vdg: str | None = None
    tv: str | None = None
    keyboard: str | None = None
    basic: str | None = None
    extended: str | None = None
    options: tuple[str, ...] = ()


class Variant(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    defines: tuple[str, ...] = Field(min_length=1)


class Memory(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    at: dict[str, int] = {}
    below: dict[str, int] = {}


class Check(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    checkpoint: str
    frames: tuple[int, ...] = Field(min_length=1)
    unreachable: str
    screen: int | None = None
    trace_from: str | None = None
    emulated_seconds: float = Field(default=60, gt=0)

    @field_validator("frames", mode="before")
    @classmethod
    def expand_ranges(cls, value: object) -> object:
        """Accept 1, 15 or "1-42" entries; a range includes both ends."""
        if not isinstance(value, list):
            return value
        frames: list[object] = []
        for item in value:
            if isinstance(item, str) and (match := re.fullmatch(r"(\d+)-(\d+)", item)):
                frames.extend(range(int(match[1]), int(match[2]) + 1))
            else:
                frames.append(item)
        return frames

    @field_validator("frames")
    @classmethod
    def positive_frames(cls, frames: tuple[int, ...]) -> tuple[int, ...]:
        if min(frames) < 1:
            raise ValueError("frames count checkpoint hits and start at 1")
        return frames


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str = "main.asm"
    prepare: str | None = None
    targets: dict[str, Machine] = Field(min_length=1)
    variants: dict[str, Variant] = {}
    memory: Memory = Memory()
    check: Check | None = None


class Project(BaseModel):
    model_config = ConfigDict(frozen=True)

    directory: Path
    settings: Settings

    @property
    def name(self) -> str:
        return self.directory.name

    @property
    def output(self) -> Path:
        return ROOT / "build" / self.name

    @property
    def default_target(self) -> str:
        return next(iter(self.settings.targets))


class Build(BaseModel):
    model_config = ConfigDict(frozen=True)

    binary: Path
    symbols: dict[str, int]
    variant: str = ""


class Host:
    """Gateway for executables, processes and installed firmware."""

    def executable(self, name: str) -> str:
        path = tool_path(name)
        if not path:
            raise ProjectError(f"Missing {name}; run uv run python scripts/native.py first.")
        return path

    def firmware(self, profile: str, names: tuple[str, ...]) -> dict[str, Path]:
        return verify_installed(ROOT, profile, names)

    def run(self, command: list[str], log: Path, timeout: float, cwd: Path | None = None) -> None:
        with log.open("w") as stream:
            subprocess.run(
                command,
                cwd=cwd,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=timeout,
            )

    def launch(self, command: list[str]) -> None:
        subprocess.run(command, check=True)


# --- Pure decisions -------------------------------------------------------------------------


def load_project(directory: Path) -> Project:
    """Read and validate coco.toml; every relative path is inside the project folder."""
    directory = directory.resolve()
    path = directory / SETTINGS
    try:
        settings = Settings.model_validate(tomllib.loads(path.read_text()))
    except FileNotFoundError as error:
        raise ProjectError(f"{path} is missing; a project folder needs {SETTINGS}.") from error
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise ProjectError(f"{path} is invalid: {error}") from error
    return Project(directory=directory, settings=settings)


def load_module(path: Path) -> ModuleType:
    """Import a project Python file once, under a name unique to its path."""
    path = path.resolve()
    name = "coco_project_" + re.sub(r"\W", "_", str(path.with_suffix("")))
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
    return sys.modules[name]


def load_expected(directory: Path) -> ModuleType | None:
    """Load the folder's independent expected.py model, if it has one."""
    path = Path(directory) / MODEL
    return load_module(path) if path.exists() else None


def parse_symbols(text: str) -> dict[str, int]:
    return {
        name: int(value, 16)
        for name, value in re.findall(r"^(\w+)\s+EQU\s+\$([0-9A-Fa-f]+)", text, re.MULTILINE)
    }


def address(symbols: dict[str, int], expression: str) -> int:
    """Resolve "label" or "label+N" against the assembler's symbol dump."""
    label, _, offset = expression.partition("+")
    if label not in symbols:
        raise ProjectError(f"Label {label!r} is not in the assembled symbols.")
    return symbols[label] + (int(offset, 0) if offset else 0)


def check_memory(memory: Memory, symbols: dict[str, int]) -> None:
    for label, required in memory.at.items():
        if address(symbols, label) != required:
            raise ProjectError(f"{label} must be at ${required:04X}; check the memory layout.")
    for label, limit in memory.below.items():
        if address(symbols, label) >= limit:
            raise ProjectError(f"{label} must be below ${limit:04X}; it overlaps a reservation.")


def assemble_command(
    lwasm: str, source: Path, binary: Path, symbols: Path, defines: Sequence[str]
) -> list[str]:
    return [
        lwasm,
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
        f"--includedir={binary.parent}",
        *(f"--define={name}" for name in defines),
        str(source),
    ]


def firmware_names(machine: Machine) -> tuple[str, ...]:
    return tuple(name for name in (machine.basic, machine.extended) if name)


def xroar_command(xroar: str, machine: Machine, roms: dict[str, Path]) -> list[str]:
    """Translate one target table into explicit XRoar options; user config is ignored."""
    command = [xroar, "-no-c", "-machine", machine.machine]
    for option, value in (
        ("-machine-cpu", machine.cpu),
        ("-machine-keyboard", machine.keyboard),
        ("-tv-type", machine.tv),
        ("-vdg-type", machine.vdg),
    ):
        if value:
            command += [option, value]
    command += ["-ram", str(machine.ram_kib)]
    for option, name in (("-bas", machine.basic), ("-extbas", machine.extended)):
        if name:
            command += [option, str(roms[name])]
    return command + ["-no-cart", *machine.options]


def capture_options(
    check: Check, symbols: dict[str, int], frame: int, snapshot: Path, unreachable: Path
) -> list[str]:
    """Headless, accelerated run from nonzero RAM that snapshots the Nth checkpoint hit."""
    options = [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        f"{check.emulated_seconds:g}",
        "-trap",
        f"pc=0x{address(symbols, check.unreachable):04x}",
        "-trap-snap",
        str(unreachable),
    ]
    if check.trace_from:
        options += [
            "-trap",
            f"pc=0x{address(symbols, check.trace_from):04x}",
            "-trap-range",
            "1",
            "-trap-trace",
        ]
    options += [
        "-trap",
        f"pc=0x{address(symbols, check.checkpoint):04x}",
        "-trap-range",
        str(frame),
        "-trap-snap",
        str(snapshot),
    ]
    if check.trace_from:
        options.append("-trap-no-trace")
    return options + ["-trap-timeout", "0"]


def screen_difference(expected: bytes, actual: bytes, start: int) -> str | None:
    """Describe the first differing screen byte, or None when every byte matches."""
    if len(actual) != len(expected):
        return f"snapshot holds {len(actual)} screen bytes, expected {len(expected)}"
    wrong = [i for i, (a, b) in enumerate(zip(expected, actual, strict=True)) if a != b]
    if not wrong:
        return None
    first = wrong[0]
    return (
        f"{len(wrong)} of {len(expected)} screen bytes differ; first at "
        f"${start + first:04X}: expected ${expected[first]:02X}, found ${actual[first]:02X}"
    )


def model_call(project: Project, function: Callable, *args: object, variant: str) -> object:
    """Model functions receive the variant name only when coco.toml declares variants."""
    return function(*args, variant) if project.settings.variants else function(*args)


def verify_snapshot(
    project: Project,
    model: ModuleType,
    ram: bytes,
    symbols: dict[str, int],
    frame: int,
    variant: str = "",
) -> int:
    """Compare one snapshot with the model; returns the number of screen bytes compared."""
    check = project.settings.check
    if hasattr(model, "verify_ram"):
        model_call(project, model.verify_ram, ram, symbols, frame, variant=variant)
    if check.screen is None or not hasattr(model, "expected_screen"):
        return 0
    expected = model_call(project, model.expected_screen, frame, variant=variant)
    actual = ram[check.screen : check.screen + len(expected)]
    if difference := screen_difference(expected, actual, check.screen):
        raise ProjectError(f"Frame {frame}: {difference}.")
    return len(expected)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Imperative shell -----------------------------------------------------------------------


def defines_for(project: Project, variant: str) -> tuple[str, ...]:
    if not variant:
        return ()
    if variant not in project.settings.variants:
        raise ProjectError(
            f"Unknown variant {variant!r}; coco.toml declares {variant_names(project)}."
        )
    return project.settings.variants[variant].defines


def variant_names(project: Project) -> list[str]:
    return list(project.settings.variants)


def build(
    project: Project, host: Host, variant: str = "", extra_defines: Sequence[str] = ()
) -> Build:
    """Assemble fresh DECB output and symbols, then enforce the declared memory layout."""
    defines = (*defines_for(project, variant), *extra_defines)
    output = project.output
    output.mkdir(parents=True, exist_ok=True)
    stem = "-".join((variant or "main", *extra_defines)).lower()
    binary, symbols = output / f"{stem}.bin", output / f"{stem}.sym"
    for path in (binary, symbols):
        path.unlink(missing_ok=True)
    if project.settings.prepare:
        module = load_module(project.directory / project.settings.prepare)
        if not hasattr(module, "prepare"):
            raise ProjectError(f"{project.settings.prepare} must define prepare(output).")
        module.prepare(output)
    command = assemble_command(
        host.executable("lwasm"),
        project.directory / project.settings.source,
        binary,
        symbols,
        defines,
    )
    host.run(command, output / f"{stem}.assemble.log", timeout=60)
    labels = parse_symbols(symbols.read_text())
    check_memory(project.settings.memory, labels)
    return Build(binary=binary, symbols=labels, variant=variant)


def target_machine(project: Project, target: str | None) -> tuple[str, Machine]:
    name = target or project.default_target
    if name not in project.settings.targets:
        raise ProjectError(
            f"Unknown target {name!r}; coco.toml declares {list(project.settings.targets)}."
        )
    return name, project.settings.targets[name]


def emulator(
    project: Project, host: Host, target: str | None, xroar: str | None = None
) -> list[str]:
    """Validate the actual firmware bytes before producing any launch command."""
    name, machine = target_machine(project, target)
    roms = host.firmware(machine.firmware or name, firmware_names(machine))
    return xroar_command(xroar or host.executable("xroar"), machine, roms)


def capture(
    project: Project, host: Host, built: Build, target: str, frame: int
) -> tuple[bytes, Path]:
    """Snapshot the Nth checkpoint hit; an unreachable checkpoint must leave no snapshot."""
    check = require_check(project)
    stem = built.binary.with_name(f"{built.binary.stem}-{target}-{frame}")
    snapshot, log = stem.with_suffix(".ram"), stem.with_suffix(".log")
    unreachable = built.binary.with_name(f"{built.binary.stem}-{target}-unreachable.ram")
    for path in (snapshot, unreachable):
        path.unlink(missing_ok=True)
    command = emulator(project, host, target) + capture_options(
        check, built.symbols, frame, snapshot, unreachable
    )
    command += ["-run", str(built.binary)]
    host.run(command, log, timeout=max(30.0, check.emulated_seconds))
    if unreachable.exists():
        raise ProjectError(f"The unreachable checkpoint {check.unreachable!r} fired.")
    if not snapshot.exists():
        raise ProjectError(
            f"{target} did not reach {check.checkpoint!r} {frame} times within "
            f"{check.emulated_seconds:g} emulated seconds."
        )
    return snapshot.read_bytes(), log


def require_check(project: Project) -> Check:
    if project.settings.check is None:
        raise ProjectError(f"{project.directory / SETTINGS} has no [check] section.")
    return project.settings.check


def check_variant(
    project: Project, host: Host, model: ModuleType | None, target: str, variant: str
) -> dict[str, object]:
    check = require_check(project)
    built = build(project, host, variant)
    screen_bytes, log = 0, None
    for frame in check.frames:
        ram, log = capture(project, host, built, target, frame)
        if model:
            screen_bytes = verify_snapshot(project, model, ram, built.symbols, frame, variant)
    record: dict[str, object] = {
        "binary_sha256": digest(built.binary),
        "screen_bytes_each": screen_bytes,
    }
    if check.trace_from and model and hasattr(model, "verify_trace"):
        trace = log.read_text()
        record["trace"] = model_call(
            project, model.verify_trace, trace, built.symbols, variant=variant
        )
    return record


def check_target(project: Project, host: Host, target: str) -> dict[str, object]:
    """Write a success record only after every variant and frame passes."""
    check = require_check(project)
    result = project.output / f"{target}-results.json"
    result.unlink(missing_ok=True)
    name, machine = target_machine(project, target)
    model = load_expected(project.directory)
    variants = {
        variant or "main": check_variant(project, host, model, name, variant)
        for variant in ("", *project.settings.variants)
    }
    record = {
        "target": name,
        "machine": machine.model_dump(mode="json", exclude_defaults=True),
        "checkpoint": check.checkpoint,
        "frames": list(check.frames),
        "variants": variants,
        "ram_init": "set (nonzero)",
        "unreachable_checkpoint": "no snapshot",
        "model": MODEL if model else "none: memory not compared",
        "visual": "not inspected",
        "physical_hardware": "not tested",
    }
    project.output.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(record, indent=2) + "\n")
    return record


def report(project: Project, record: dict[str, object]) -> list[str]:
    check = require_check(project)
    frames = len(check.frames)
    builds = len(record["variants"])
    execution = (
        f"Execution: {record['target']} reached {check.checkpoint!r} at {frames} "
        f"checkpoint(s) in {builds} build(s); the unreachable checkpoint left no snapshot."
    )
    lines = [execution]
    if record["model"] == MODEL:
        screen = next(iter(record["variants"].values()))["screen_bytes_each"]
        detail = f"all {screen} screen bytes and " if screen else ""
        lines.append(f"Memory: {detail}the model's state checks matched at every checkpoint.")
    else:
        lines.append(f"Memory: not compared; add {MODEL} with an independent model.")
    lines.append("Visual: not inspected. Use the run command and look at the XRoar window.")
    return lines


# --- Command line ---------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="coco.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = result.add_subparsers(dest="command", required=True)
    for name, text in (
        ("build", "assemble the project and print the binary path"),
        ("run", "assemble and open XRoar at normal speed"),
        ("snapshot", "save RAM at the Nth checkpoint hit and print its path"),
        ("check", "compare RAM at each checkpoint with expected.py"),
    ):
        command = commands.add_parser(name, help=text, description=text)
        command.add_argument("project", type=Path, help="folder holding coco.toml")
        command.add_argument("--target", help="a [targets.<name>] table; default: the first")
        if name != "check":
            command.add_argument("--variant", default="", help="a [variants.<name>] build")
        if name == "snapshot":
            command.add_argument("--frame", type=int, default=1, help="checkpoint hit (from 1)")
    return result


def execute(arguments: argparse.Namespace, host: Host) -> None:
    project = load_project(arguments.project)
    if arguments.command == "check":
        targets = [arguments.target] if arguments.target else list(project.settings.targets)
        for target in targets:
            for line in report(project, check_target(project, host, target)):
                print(line)
        print(f"PASS: {project.name}; evidence in {project.output}")
        return
    target, _ = target_machine(project, arguments.target)
    built = build(project, host, arguments.variant)
    if arguments.command == "build":
        print(built.binary)
    elif arguments.command == "snapshot":
        _, log = capture(project, host, built, target, arguments.frame)
        print(log.with_suffix(".ram"))
    else:
        host.launch(emulator(project, host, target) + ["-ratelimit", "-run", str(built.binary)])


def main(argv: list[str] | None = None, host: Host | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        execute(arguments, host or Host())
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
