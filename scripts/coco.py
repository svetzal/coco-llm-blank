"""Build, run, snapshot, or check a CoCo project folder described by its coco.toml.

A project folder holds main.asm, coco.toml and, optionally, expected.py: an
independent model of what each checkpoint must show in memory, on the rendered
screen and in sound. All CoCo facts (machine, firmware, memory layout, labels,
pictures, keys) live in those project files. This tool only assembles with
LWTOOLS and drives XRoar.

check runs the main build on every [targets.<name>] table. A [variants.<name>]
table with targets = [...] runs only on those targets; without targets it runs
on every target. run, build and snapshot with --variant use the variant's first
allowed target unless --target names one. expected.py functions receive the
variant name last when coco.toml declares variants, and target=<name> when
their signature declares a target parameter.

Rendered frames (--video), mixer sound (--audio) and scripted keys ([keys] in
coco.toml) need the instrumented XRoar, which is built once into local/ on
first use; it needs a C compiler, make and autotools. Everything else uses
the installed XRoar.
"""

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType

import instrumented_xroar
import numpy as np
import recording
from native import ROOT, tool_path
from PIL import Image
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from recording import Picture, Sound
from roms import verify_installed

SETTINGS = "coco.toml"
MODEL = "expected.py"
MODEL_FUNCTIONS = (
    "expected_screen",
    "verify_ram",
    "verify_trace",
    "expected_frame",
    "verify_sound",
)
# Rendered frames: S-video palette without cross-colour, active area only.
VIDEO_OPTIONS = ["-tv-input", "svideo", "-ccr", "none", "-vo-picture", "zoomed", "-fskip", "0"]
# Emulated seconds after the checkpoint: two complete video frames and a full audio buffer.
RUN_ON_SECONDS = 0.06


class ProjectError(ValueError):
    """A project cannot be built, launched or checked as configured."""


class Machine(BaseModel):
    """One [targets.<name>] table: an XRoar machine and its validated firmware.

    screen, when set, replaces [check].screen for this target: an offset into its snapshot.
    """

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
    screen: int | None = None


class Variant(BaseModel):
    """A [variants.<name>] table: assembler defines, a key script, or both.

    targets names the [targets.<name>] tables the build applies to; omitted means every one.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    defines: tuple[str, ...] = ()
    keys: str | None = None
    targets: tuple[str, ...] | None = Field(default=None, min_length=1)

    def applies_to(self, target: str) -> bool:
        return self.targets is None or target in self.targets

    @model_validator(mode="after")
    def needs_defines_or_keys(self) -> "Variant":
        if not self.defines and not self.keys:
            raise ValueError("a variant needs defines, a keys script, or both")
        return self


class Keys(BaseModel):
    """[keys]: the label where each key-script step takes effect, and the script's letters."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    at: str
    letters: dict[str, str] = Field(min_length=1)

    @field_validator("letters")
    @classmethod
    def known_keys(cls, letters: dict[str, str]) -> dict[str, str]:
        names = instrumented_xroar.key_names(instrumented_xroar.load_series())
        for letter, key in letters.items():
            if len(letter) != 1 or letter in "-#" or letter.isspace():
                raise ValueError(f"letter {letter!r} must be one character other than - or #")
            if key not in names:
                raise ValueError(f"{key!r} is not an XRoar key; use one of {', '.join(names)}")
        return letters


class Capture(BaseModel):
    """[capture]: equipment every check uses, as if --video or --audio were given."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    video: bool = False
    audio: bool = False


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
    keys: Keys | None = None
    capture: Capture = Capture()

    @model_validator(mode="after")
    def keys_declared(self) -> "Settings":
        if self.keys is None and any(v.keys for v in self.variants.values()):
            raise ValueError("a variant names a key script, so [keys] must declare at and letters")
        return self

    @model_validator(mode="after")
    def variant_targets_declared(self) -> "Settings":
        for name, variant in self.variants.items():
            unknown = [t for t in variant.targets or () if t not in self.targets]
            if unknown:
                raise ValueError(
                    f"[variants.{name}] targets {unknown} are not declared; "
                    f"coco.toml declares {list(self.targets)}"
                )
        return self


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


class Equipment(BaseModel):
    """What one emulator run records besides RAM; none of it means the installed XRoar."""

    model_config = ConfigDict(frozen=True)

    video: bool = False
    audio: bool = False
    keys: tuple[tuple[str, ...], ...] | None = None
    script: str = ""

    @property
    def instrumented(self) -> bool:
        return self.video or self.audio or self.keys is not None


NO_EQUIPMENT = Equipment()


class Evidence(BaseModel):
    """One checkpoint: RAM, the emulator log and whatever the equipment recorded."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    ram: bytes
    log: Path
    picture: Picture | None = None
    sound: Sound | None = None
    keys_delivered: int | None = None


class Host:
    """Gateway for executables, processes and installed firmware."""

    def executable(self, name: str) -> str:
        path = tool_path(name)
        if not path:
            raise ProjectError(f"Missing {name}; run uv run python scripts/native.py first.")
        return path

    def instrumented(self) -> str:
        """XROAR_INSTRUMENTED if set, else the verified instrumented XRoar, built on first use."""
        if override := os.environ.get("XROAR_INSTRUMENTED"):
            return override
        return str(instrumented_xroar.ensure(say=lambda text: print(text, file=sys.stderr)))

    def firmware(self, profile: str, names: tuple[str, ...]) -> dict[str, Path]:
        return verify_installed(ROOT, profile, names)

    def run(
        self,
        command: list[str],
        log: Path,
        timeout: float,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        with log.open("w") as stream:
            subprocess.run(
                command,
                cwd=cwd,
                env=env,
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
    if machine.basic:
        command += ["-bas", str(roms[machine.basic])]
    # XRoar's built-in profiles name an Extended BASIC ROM. Disable it unless the
    # target names one: the CoCo 3 loads its single ROM image this way.
    if machine.extended:
        command += ["-extbas", str(roms[machine.extended])]
    else:
        command += ["-no-extbas"]
    return command + ["-no-cart", *machine.options]


def trap_condition(symbols: dict[str, int], expression: str) -> str:
    return f"pc=0x{address(symbols, expression):04x}"


def capture_options(
    check: Check,
    symbols: dict[str, int],
    frame: int,
    snapshot: Path,
    unreachable: Path,
    equipment: Equipment = NO_EQUIPMENT,
    keys: Keys | None = None,
) -> list[str]:
    """Headless, accelerated run from nonzero RAM that snapshots the Nth checkpoint hit.

    Each range names one hit exactly ("N-N"); a bare "N" would repeat from N onward.

    With a key script, the keyboard hook acts at every hit of the [keys] label. With
    video or audio, the run continues briefly after the snapshot so that a complete
    frame and the audio up to the checkpoint are recorded.
    """
    options = VIDEO_OPTIONS.copy() if equipment.video else []
    options += [
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
    if equipment.keys is not None:
        options += ["-trap", trap_condition(symbols, keys.at), "-trap-range", "1-"]
    if check.trace_from:
        options += [
            "-trap",
            f"pc=0x{address(symbols, check.trace_from):04x}",
            "-trap-range",
            "1-1",
            "-trap-trace",
        ]
    options += [
        "-trap",
        f"pc=0x{address(symbols, check.checkpoint):04x}",
        "-trap-range",
        f"{frame}-{frame}",
        "-trap-snap",
        str(snapshot),
    ]
    if check.trace_from:
        options.append("-trap-no-trace")
    run_on = RUN_ON_SECONDS if equipment.video or equipment.audio else 0
    return options + ["-trap-timeout", f"{run_on:g}"]


def recording_environment(
    equipment: Equipment, symbols: dict[str, int], keys: Keys | None, paths: dict[str, Path]
) -> dict[str, str]:
    """Variables the hooks read; a hook without its variable records nothing."""
    variables = {"COCO_CHECKPOINT": str(paths["ram"])}
    if equipment.video:
        variables["COCO_VIDEO"] = str(paths["ppm"])
    if equipment.audio:
        variables["COCO_AUDIO"] = str(paths["pcm"])
    if equipment.keys is not None:
        variables["COCO_KEYS"] = str(paths["keys"])
        variables["COCO_KEYS_AT"] = trap_condition(symbols, keys.at)
    return variables


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


def accepts_target(function: Callable) -> bool:
    """True when the signature declares a target parameter or **kwargs."""
    try:
        parameters = inspect.signature(function).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(p.name == "target" or p.kind is p.VAR_KEYWORD for p in parameters)


def model_call(
    project: Project, function: Callable, *args: object, variant: str, target: str
) -> object:
    """Call a model function in the convention its signature declares.

    The variant name follows the arguments only when coco.toml declares variants. The
    target name is passed as target= only to a function that declares it (or **kwargs).
    """
    positional = (*args, variant) if project.settings.variants else args
    keywords = {"target": target} if accepts_target(function) else {}
    return function(*positional, **keywords)


def verify_snapshot(
    project: Project,
    model: ModuleType,
    ram: bytes,
    symbols: dict[str, int],
    frame: int,
    variant: str = "",
    target: str = "",
) -> int:
    """Compare the screen, then the model's state checks; returns screen bytes compared."""
    screen = screen_offset(project, target)
    compared = 0
    if screen is not None and hasattr(model, "expected_screen"):
        expected = model_call(project, model.expected_screen, frame, variant=variant, target=target)
        actual = ram[screen : screen + len(expected)]
        if difference := screen_difference(expected, actual, screen):
            raise ProjectError(f"Frame {frame}: {difference}.")
        compared = len(expected)
    if hasattr(model, "verify_ram"):
        model_call(project, model.verify_ram, ram, symbols, frame, variant=variant, target=target)
    return compared


def screen_offset(project: Project, target: str) -> int | None:
    """The snapshot offset of the screen: the target's own screen, else [check].screen."""
    machine = project.settings.targets.get(target)
    if machine and machine.screen is not None:
        return machine.screen
    return project.settings.check.screen


def verify_picture(
    project: Project,
    model: ModuleType,
    picture: Picture | None,
    frame: int,
    variant: str = "",
    target: str = "",
) -> int:
    """Compare XRoar's rendered frame with expected_frame(); returns samples compared."""
    if picture is None or not hasattr(model, "expected_frame"):
        return 0
    expected = np.asarray(
        model_call(project, model.expected_frame, frame, variant=variant, target=target),
        dtype=np.uint8,
    )
    if difference := recording.frame_difference(expected, picture.pixels):
        raise ProjectError(f"Frame {frame}: rendered display: {difference}.")
    return expected.shape[0] * expected.shape[1]


def verify_sound(
    project: Project,
    model: ModuleType,
    sound: Sound | None,
    frame: int,
    variant: str = "",
    target: str = "",
) -> object:
    """Let the model judge XRoar's mixer output; its return value is recorded."""
    if sound is None or not hasattr(model, "verify_sound"):
        return None
    return model_call(project, model.verify_sound, sound, frame, variant=variant, target=target)


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


def variant_target(project: Project, variant: str, target: str | None) -> str:
    """The target one build runs on: the named one, else the first the variant allows."""
    declared = project.settings.variants.get(variant)
    allowed = declared.targets if declared and declared.targets else None
    if target is None:
        return allowed[0] if allowed else project.default_target
    name, _ = target_machine(project, target)
    if allowed and name not in allowed:
        raise ProjectError(
            f"Variant {variant!r} applies only to targets {list(allowed)}, not {name!r}."
        )
    return name


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


def equipment_for(
    project: Project,
    variant: str = "",
    video: bool = False,
    audio: bool = False,
    script: Path | None = None,
) -> Equipment:
    """Combine [capture], the command line and the key script for one build."""
    declared = project.settings.variants.get(variant)
    if script is None and declared and declared.keys:
        script = project.directory / declared.keys
    keys = None
    if script is not None:
        if project.settings.keys is None:
            raise ProjectError(f"{project.directory / SETTINGS} needs [keys] for a key script.")
        try:
            text = script.read_text()
        except OSError as error:
            raise ProjectError(f"Cannot read the key script {script}: {error}") from error
        keys = recording.parse_key_script(text, project.settings.keys.letters)
    return Equipment(
        video=video or project.settings.capture.video,
        audio=audio or project.settings.capture.audio,
        keys=keys,
        script=script.name if script else "",
    )


def recording_paths(built: Build, target: str, frame: int) -> dict[str, Path]:
    stem = built.binary.with_name(f"{built.binary.stem}-{target}-{frame}")
    return {
        kind: stem.with_suffix(f".{kind}")
        for kind in ("ram", "log", "ppm", "png", "pcm", "wav", "keys")
    }


def collect(
    paths: dict[str, Path], equipment: Equipment
) -> tuple[Picture | None, Sound | None, int | None]:
    """Turn the hooks' raw files into a PNG, a WAV and the number of key steps."""
    log = recording.parse_log(paths["log"].read_text())
    picture = sound = delivered = None
    if equipment.video:
        data = paths["ppm"].read_bytes() if paths["ppm"].exists() else None
        pixels = recording.rendered_frame(log, data)
        Image.fromarray(pixels).save(paths["png"])
        paths["ppm"].unlink()
        picture = Picture(path=paths["png"], pixels=pixels)
    if equipment.audio:
        raw = paths["pcm"].read_bytes() if paths["pcm"].exists() else b""
        rate, samples = recording.sound_until_checkpoint(log, raw)
        recording.write_wav(paths["wav"], rate, samples)
        paths["pcm"].unlink()
        sound = Sound(path=paths["wav"], rate=rate, samples=samples)
    if equipment.keys is not None:
        delivered = recording.keys_before_checkpoint(log)
    return picture, sound, delivered


def capture(
    project: Project,
    host: Host,
    built: Build,
    target: str,
    frame: int,
    equipment: Equipment = NO_EQUIPMENT,
) -> Evidence:
    """Snapshot the Nth checkpoint hit; an unreachable checkpoint must leave no snapshot."""
    check = require_check(project)
    paths = recording_paths(built, target, frame)
    unreachable = built.binary.with_name(f"{built.binary.stem}-{target}-unreachable.ram")
    for path in (*paths.values(), unreachable):
        path.unlink(missing_ok=True)
    keys = project.settings.keys
    xroar = host.instrumented() if equipment.instrumented else None
    command = emulator(project, host, target, xroar) + capture_options(
        check, built.symbols, frame, paths["ram"], unreachable, equipment, keys
    )
    command += ["-run", str(built.binary)]
    environment = None
    if equipment.instrumented:
        if equipment.keys is not None:
            paths["keys"].write_text(recording.key_lines(equipment.keys))
        inherited = {k: v for k, v in os.environ.items() if not k.startswith("COCO_")}
        environment = inherited | recording_environment(equipment, built.symbols, keys, paths)
    host.run(command, paths["log"], timeout=max(30.0, check.emulated_seconds), env=environment)
    if unreachable.exists():
        raise ProjectError(f"The unreachable checkpoint {check.unreachable!r} fired.")
    if not paths["ram"].exists():
        raise ProjectError(
            f"{target} did not reach {check.checkpoint!r} {frame} times within "
            f"{check.emulated_seconds:g} emulated seconds."
        )
    picture, sound, delivered = collect(paths, equipment) if equipment.instrumented else (None,) * 3
    return Evidence(
        ram=paths["ram"].read_bytes(),
        log=paths["log"],
        picture=picture,
        sound=sound,
        keys_delivered=delivered,
    )


def require_check(project: Project) -> Check:
    if project.settings.check is None:
        raise ProjectError(f"{project.directory / SETTINGS} has no [check] section.")
    return project.settings.check


def equipment_record(
    project: Project, equipment: Equipment, evidence: list[Evidence], rendered: int, sounds: list
) -> dict[str, object]:
    record: dict[str, object] = {}
    if equipment.keys is not None:
        record["keys"] = {
            "script": equipment.script,
            "at": project.settings.keys.at,
            "steps": len(equipment.keys),
            "delivered_by_checkpoint": [e.keys_delivered for e in evidence],
        }
    if equipment.video:
        height, width, _ = evidence[0].picture.pixels.shape
        record["rendered"] = {
            "images": [e.picture.path.name for e in evidence],
            "size": [width, height],
            "compared_samples_each": rendered,
        }
    if equipment.audio:
        record["sound"] = {
            "recordings": [e.sound.path.name for e in evidence],
            "seconds": [round(e.sound.seconds, 4) for e in evidence],
            "model": sounds,
        }
    return record


def check_variant(
    project: Project,
    host: Host,
    model: ModuleType | None,
    target: str,
    variant: str,
    equipment: Equipment = NO_EQUIPMENT,
) -> dict[str, object]:
    check = require_check(project)
    built = build(project, host, variant)
    screen_bytes = rendered = 0
    evidence, sounds = [], []
    for frame in check.frames:
        evidence.append(capture(project, host, built, target, frame, equipment))
        if model:
            current = evidence[-1]
            screen_bytes = verify_snapshot(
                project, model, current.ram, built.symbols, frame, variant, target
            )
            rendered = verify_picture(project, model, current.picture, frame, variant, target)
            sounds.append(verify_sound(project, model, current.sound, frame, variant, target))
    record: dict[str, object] = {
        "binary_sha256": digest(built.binary),
        "screen_bytes_each": screen_bytes,
        **equipment_record(project, equipment, evidence, rendered, sounds),
    }
    if equipment.instrumented:
        record["emulator"] = host.instrumented()
    if check.trace_from and model and hasattr(model, "verify_trace"):
        trace = evidence[-1].log.read_text()
        record["trace"] = model_call(
            project, model.verify_trace, trace, built.symbols, variant=variant, target=target
        )
    return record


def evidence_summary(model: ModuleType | None, captured: bool, function: str, checked: str) -> str:
    if not captured:
        return "not captured"
    return checked if model and hasattr(model, function) else f"captured; no {function}"


def check_target(
    project: Project, host: Host, target: str, video: bool = False, audio: bool = False
) -> dict[str, object]:
    """Write a success record only after every variant for this target and frame passes."""
    check = require_check(project)
    result = project.output / f"{target}-results.json"
    result.unlink(missing_ok=True)
    name, machine = target_machine(project, target)
    model = load_expected(project.directory)
    builds = {
        variant: equipment_for(project, variant, video, audio)
        for variant in variants_for(project, name)
    }
    record = {
        "target": name,
        "machine": machine.model_dump(mode="json", exclude_defaults=True),
        "checkpoint": check.checkpoint,
        "frames": list(check.frames),
        "screen": screen_offset(project, name),
        "variants": {
            variant or "main": check_variant(project, host, model, name, variant, equipment)
            for variant, equipment in builds.items()
        },
        "variants_for_other_targets": {
            variant: list(declared.targets)
            for variant, declared in project.settings.variants.items()
            if not declared.applies_to(name)
        },
        "ram_init": "set (nonzero)",
        "unreachable_checkpoint": "no snapshot",
        "model": MODEL if model else "none: memory not compared",
        "model_functions": [f for f in MODEL_FUNCTIONS if model and hasattr(model, f)],
        "rendered_display": evidence_summary(
            model, any(e.video for e in builds.values()), "expected_frame", "matched expected_frame"
        ),
        "sound": evidence_summary(
            model, any(e.audio for e in builds.values()), "verify_sound", "accepted by verify_sound"
        ),
        "visual": "not inspected by a person",
        "physical_hardware": "not tested",
    }
    project.output.mkdir(parents=True, exist_ok=True)
    result.write_text(json.dumps(record, indent=2) + "\n")
    return record


def variants_for(project: Project, target: str) -> tuple[str, ...]:
    """The main build, then each declared variant that applies to the target."""
    declared = project.settings.variants.items()
    return ("", *(name for name, variant in declared if variant.applies_to(target)))


def other_target_lines(record: dict[str, object]) -> list[str]:
    return [
        f"Variant {variant}: not built for {record['target']}; it applies only to "
        f"{', '.join(targets)}."
        for variant, targets in record.get("variants_for_other_targets", {}).items()
    ]


def keys_lines(record: dict[str, object]) -> list[str]:
    lines = []
    for variant, evidence in record["variants"].items():
        if keys := evidence.get("keys"):
            lines.append(
                f"Keys ({variant}): {keys['steps']} steps of {keys['script']} pressed and "
                f"released through XRoar's keyboard matrix at each {keys['at']!r}; "
                f"{keys['delivered_by_checkpoint'][-1]} had taken effect by the last checkpoint."
            )
    return lines


def rendered_line(project: Project, record: dict[str, object]) -> str:
    rendered = next((v["rendered"] for v in record["variants"].values() if "rendered" in v), None)
    if rendered is None:
        if "expected_frame" in record["model_functions"]:
            return (
                "Rendered display: not captured, so expected_frame was not compared; "
                "add --video or set [capture] video = true."
            )
        return "Rendered display: not captured; add --video to save XRoar's rendered frames."
    width, height = rendered["size"]
    where = f"PNGs of XRoar's renderer output are in {project.output}"
    if rendered["compared_samples_each"]:
        return (
            f"Rendered display: all {rendered['compared_samples_each']} samples of the "
            f"{width}x{height} frame matched expected_frame at every checkpoint; {where}."
        )
    return f"Rendered display: captured, not compared (no expected_frame); {where}."


def sound_line(project: Project, record: dict[str, object]) -> str:
    captured = any("sound" in v for v in record["variants"].values())
    if not captured:
        hint = " verify_sound was not run;" if "verify_sound" in record["model_functions"] else ""
        return f"Sound: not captured;{hint} add --audio to record XRoar's mixer output."
    where = f"WAVs of XRoar's mixer output are in {project.output}"
    if "verify_sound" in record["model_functions"]:
        return f"Sound: verify_sound accepted the mixer output at every checkpoint; {where}."
    return f"Sound: captured, not checked (no verify_sound); {where}."


def report(project: Project, record: dict[str, object]) -> list[str]:
    check = require_check(project)
    frames = len(check.frames)
    builds = ", ".join(record["variants"])
    execution = (
        f"Execution: {record['target']} reached {check.checkpoint!r} at {frames} "
        f"checkpoint(s) in build(s) {builds}; the unreachable checkpoint left no snapshot."
    )
    lines = [execution, *other_target_lines(record), *keys_lines(record)]
    if record["model"] == MODEL:
        screen = next(iter(record["variants"].values()))["screen_bytes_each"]
        offset = record.get("screen")
        where = f" at snapshot offset ${offset:04X}" if offset is not None else ""
        detail = f"all {screen} screen bytes{where} and " if screen else ""
        lines.append(f"Memory: {detail}the model's state checks matched at every checkpoint.")
    else:
        lines.append(f"Memory: not compared; add {MODEL} with an independent model.")
    for variant, evidence in record["variants"].items():
        if "trace" in evidence:
            lines.append(f"Trace ({variant}): the model accepted it: {evidence['trace']}")
    lines += [rendered_line(project, record), sound_line(project, record)]
    lines.append(
        "Visual: not inspected by a person. A rendered capture is XRoar's frame buffer, "
        "not a window, a television or a physical CoCo; use the run command and look."
    )
    return lines


# --- Command line ---------------------------------------------------------------------------


COMMANDS = {
    "build": "assemble the project and print the binary path",
    "run": "assemble and open XRoar at normal speed",
    "snapshot": "save RAM (and any captures) at the Nth checkpoint hit and print the paths",
    "check": "compare each checkpoint with expected.py and report the evidence",
}


def add_equipment(command: argparse.ArgumentParser, name: str) -> None:
    command.add_argument(
        "--video", action="store_true", help="save XRoar's rendered frame as PNG (instrumented)"
    )
    command.add_argument(
        "--audio", action="store_true", help="record XRoar's mixer output as WAV (instrumented)"
    )
    if name == "snapshot":
        command.add_argument(
            "--keys",
            type=Path,
            metavar="SCRIPT",
            help="key script to inject at the [keys] label (instrumented)",
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="coco.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = result.add_subparsers(dest="command", required=True)
    for name, text in COMMANDS.items():
        command = commands.add_parser(name, help=text, description=text)
        command.add_argument("project", type=Path, help="folder holding coco.toml")
        default = "every target" if name == "check" else "the variant's first allowed target"
        command.add_argument("--target", help=f"a [targets.<name>] table; default: {default}")
        if name != "check":
            command.add_argument("--variant", default="", help="a [variants.<name>] build")
        if name == "snapshot":
            command.add_argument("--frame", type=int, default=1, help="checkpoint hit (from 1)")
        if name in ("snapshot", "check"):
            add_equipment(command, name)
    return result


def check_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    targets = [arguments.target] if arguments.target else list(project.settings.targets)
    for target in targets:
        record = check_target(project, host, target, arguments.video, arguments.audio)
        for line in report(project, record):
            print(line)
    print(f"PASS: {project.name}; evidence in {project.output}")


def snapshot_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    target = variant_target(project, arguments.variant, arguments.target)
    equipment = equipment_for(
        project, arguments.variant, arguments.video, arguments.audio, arguments.keys
    )
    built = build(project, host, arguments.variant)
    evidence = capture(project, host, built, target, arguments.frame, equipment)
    print(evidence.log.with_suffix(".ram"))
    for recorded in (evidence.picture, evidence.sound):
        if recorded:
            print(recorded.path)


def execute(arguments: argparse.Namespace, host: Host) -> None:
    project = load_project(arguments.project)
    if arguments.command == "check":
        check_command(project, arguments, host)
        return
    if arguments.command == "snapshot":
        snapshot_command(project, arguments, host)
        return
    target = variant_target(project, arguments.variant, arguments.target)
    built = build(project, host, arguments.variant)
    if arguments.command == "build":
        print(built.binary)
    else:
        host.launch(emulator(project, host, target) + ["-ratelimit", "-run", str(built.binary)])


def main(argv: list[str] | None = None, host: Host | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        execute(arguments, host or Host())
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
