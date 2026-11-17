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

disk puts the build on a Disk BASIC disk image made with ToolShed's decb. With
--run it opens XRoar with the target's disk ROM and types LOADM and EXEC; with
--check it does the same headless and requires the [check] checkpoint. The
target names its Disk BASIC ROM with disk = "<name>.rom".

A target's cpu = "6309" assembles the build for the Hitachi 6309: LWASM accepts
its instructions, the build defines H6309 and its files end in -6309. Any other
target assembles for the 6809, so a 6309 instruction there fails to assemble.

record runs a build from power-on for a number of emulated seconds and writes
every rendered frame and the mixer sound as an HEVC video. The frame rate and
the sound's alignment come from the emulator's clock. It needs ffmpeg with
libx265 (FFMPEG names another executable).

Every command that starts XRoar uses one XRoar: the pinned release with the
patch series in scripts/xroar_patches/, built into local/ by bootstrap or on
first use (XROAR names a substitute). Its patches add rendered frames (--video,
record), mixer sound (--audio, record) and scripted keys ([keys] in coco.toml).
Runs for evidence have no window, no host sound and no joystick, so a gamepad
plugged into the host cannot change them; run keeps XRoar's default joystick.
"""

import argparse
import hashlib
import importlib.util
import inspect
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Literal

import instrumented_xroar
import numpy as np
import recording
from native import HOMEBREW_BIN, ROOT, tool_path
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
# Evidence runs: no window, no host sound, and both joystick ports on an empty profile, which
# reads as centred with no button pressed whatever the host has plugged in.
HEADLESS_OPTIONS = ["-ui", "null", "-ao", "null"]
JOYSTICK_OPTIONS = ["-joy", "none", "-joy-right", "none", "-joy-left", "none"]
# Rendered frames: S-video palette without cross-colour, active area only.
VIDEO_OPTIONS = ["-tv-input", "svideo", "-ccr", "none", "-vo-picture", "zoomed", "-fskip", "0"]


def video_options(tv_input: str | None = None) -> list[str]:
    """VIDEO_OPTIONS, with the target's TV input in place of svideo when it names one."""
    options = VIDEO_OPTIONS.copy()
    if tv_input:
        options[options.index("-tv-input") + 1] = tv_input
    return options


# Emulated seconds after the checkpoint: two complete video frames and a full audio buffer.
RUN_ON_SECONDS = 0.06
# A recorded video is scaled by whole numbers to at least this many lines, and shown at 4:3.
VIDEO_LINES = 768
# Wall-clock seconds allowed for each emulated or encoded second of a recording.
RECORD_PACE = 10
FFMPEG_HINT = (
    "Install ffmpeg with libx265: on macOS run `brew install ffmpeg`; on Ubuntu 24.04 run "
    "`sudo apt-get install ffmpeg`. Set FFMPEG to use another executable."
)
# Emulated seconds a disk check adds to [check].emulated_seconds for the boot, the typed
# command and the load. The template needs 3 to 4; this is an allowance, not a limit.
DISK_SECONDS = 10
# XRoar's cartridge profile for the Disk BASIC controller (xroar -cart help).
DISK_CARTRIDGE = "rsdos"


class ProjectError(ValueError):
    """A project cannot be built, launched or checked as configured."""


class Machine(BaseModel):
    """One [targets.<name>] table: an XRoar machine and its validated firmware.

    screen, when set, replaces [check].screen for this target: an offset into its snapshot.
    tv_input, when set, is XRoar's -tv-input for this target (xroar -tv-input help lists
    the inputs). It also replaces the svideo input of rendered captures and recordings.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    firmware: str | None = None
    machine: str
    ram_kib: int = Field(gt=0)
    cpu: Literal["6809", "6309"] | None = None
    vdg: str | None = None
    tv: str | None = None
    tv_input: str | None = None
    keyboard: str | None = None
    basic: str | None = None
    extended: str | None = None
    disk: str | None = None
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


class Disk(BaseModel):
    """[disk]: the program's name on the disk image, without the .BIN extension."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str | None = Field(default=None, pattern=r"^[A-Z0-9]{1,8}$")


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
    disk: Disk = Disk()

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

    @property
    def disk_name(self) -> str:
        """[disk].name, else the folder name's first eight letters and digits."""
        derived = re.sub(r"[^A-Z0-9]", "", self.name.upper())[:8]
        return self.settings.disk.name or derived or "PROGRAM"


class Build(BaseModel):
    model_config = ConfigDict(frozen=True)

    binary: Path
    symbols: dict[str, int]
    variant: str = ""


class Equipment(BaseModel):
    """What one emulator run records besides RAM through the patch series' hooks."""

    model_config = ConfigDict(frozen=True)

    video: bool = False
    audio: bool = False
    keys: tuple[tuple[str, ...], ...] | None = None
    script: str = ""

    @property
    def uses_hooks(self) -> bool:
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

    def xroar(self) -> str:
        """XROAR if set, else the verified instrumented XRoar, built on first use."""
        if override := os.environ.get(instrumented_xroar.OVERRIDE):
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

    def encoder(self) -> str:
        """FFMPEG if set, else ffmpeg on PATH or in Apple Silicon Homebrew."""
        name = os.environ.get("FFMPEG", "ffmpeg")
        path = shutil.which(name) or shutil.which(str(HOMEBREW_BIN / name))
        if not path:
            raise ProjectError(f"Missing {name}, which record needs. {FFMPEG_HINT}")
        return path

    def record(
        self,
        command: list[str],
        log: Path,
        timeout: float,
        env: dict[str, str],
        stream: Path,
        encoder: list[str],
        encoder_log: Path,
    ) -> None:
        """Run the emulator while the encoder reads its frames from the named pipe stream."""
        stream.unlink(missing_ok=True)
        os.mkfifo(stream)
        try:
            with encoder_log.open("w") as output:
                reader = subprocess.Popen(
                    encoder, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT
                )
                try:
                    self.run(command, log, timeout, env=env)
                finally:
                    code = release(reader, stream, timeout)
        finally:
            stream.unlink(missing_ok=True)
        if code:
            raise ProjectError(f"ffmpeg could not read the frames; read {encoder_log}.")


def release(reader: subprocess.Popen, stream: Path, timeout: float) -> int:
    """Wait for the encoder after the emulator has ended, and return its exit code.

    An emulator that never opened the pipe leaves the encoder waiting to open it. Opening and
    closing the write end gives the encoder an end of stream. The encoder can reach its open
    after the emulator ends, so keep trying until the encoder exits.
    """
    deadline = time.monotonic() + timeout
    while (code := reader.poll()) is None:
        if time.monotonic() > deadline:
            reader.kill()
            raise subprocess.TimeoutExpired(reader.args, timeout)
        try:
            os.close(os.open(stream, os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass
        time.sleep(0.05)
    return code


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
    lwasm: str,
    source: Path,
    binary: Path,
    symbols: Path,
    defines: Sequence[str],
    cpu: str = "6809",
) -> list[str]:
    return [
        lwasm,
        f"--{cpu}",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
        f"--includedir={binary.parent}",
        *(f"--define={name}" for name in defines),
        str(source),
    ]


def firmware_names(machine: Machine) -> tuple[str, ...]:
    return tuple(name for name in (machine.basic, machine.extended) if name)


def xroar_command(
    xroar: str, machine: Machine, roms: dict[str, Path], disk: bool = False
) -> list[str]:
    """Translate one target table into explicit XRoar options; user config is ignored.

    With disk, the target's Disk BASIC ROM goes in the disk controller cartridge.
    """
    command = [xroar, "-no-c", "-machine", machine.machine]
    for option, value in (
        ("-machine-cpu", machine.cpu),
        ("-machine-keyboard", machine.keyboard),
        ("-tv-type", machine.tv),
        ("-tv-input", machine.tv_input),
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
    if disk:
        command += ["-cart", DISK_CARTRIDGE, "-cart-rom", str(roms[machine.disk])]
    else:
        command += ["-no-cart"]
    return [*command, *machine.options]


def disk_commands(decb: str, binary: str, image: str, name: str) -> list[list[str]]:
    """Format a blank image, then copy the DECB binary as a machine-language file (-2 -b).

    decb reads "image,file" as a file on an image, so pass names in the working folder:
    a comma in a full path would split it.
    """
    return [
        [decb, "dskini", image],
        [decb, "copy", "-2", "-b", binary, f"{image},{name}.BIN"],
    ]


def disk_options(image: Path, name: str, write_back: bool = True) -> list[str]:
    """Insert the image in drive 0 and type the commands that load and start the program."""
    options = ["-load-fd0", str(image)]
    if not write_back:
        options.append("-no-disk-write-back")
    # XRoar's -type reads \r as RETURN.
    return options + ["-type", f'LOADM"{name}":EXEC\\r']


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
    extra_seconds: float = 0,
    tv_input: str | None = None,
) -> list[str]:
    """Headless, accelerated run from nonzero RAM that snapshots the Nth checkpoint hit.

    Each range names one hit exactly ("N-N"); a bare "N" would repeat from N onward.

    With a key script, the keyboard hook acts at every hit of the [keys] label. With
    video or audio, the run continues briefly after the snapshot so that a complete
    frame and the audio up to the checkpoint are recorded.
    """
    options = video_options(tv_input) if equipment.video else []
    options += [
        *HEADLESS_OPTIONS,
        *JOYSTICK_OPTIONS,
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        f"{check.emulated_seconds + extra_seconds:g}",
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


def record_options(
    symbols: dict[str, int],
    seconds: float,
    unreachable: Path,
    check: Check | None,
    equipment: Equipment,
    keys: Keys | None,
    tv_input: str | None = None,
) -> list[str]:
    """Headless, accelerated run from power-on for a number of emulated seconds.

    Every frame is rendered (no frame skip). A declared unreachable label still ends the run.
    """
    options = [
        *video_options(tv_input),
        *HEADLESS_OPTIONS,
        *JOYSTICK_OPTIONS,
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        f"{seconds:g}",
    ]
    if check is not None:
        options += [
            "-trap",
            f"pc=0x{address(symbols, check.unreachable):04x}",
            "-trap-snap",
            str(unreachable),
        ]
    if equipment.keys is not None:
        options += ["-trap", trap_condition(symbols, keys.at), "-trap-range", "1-"]
    return options + ["-trap-timeout", "0"]


def video_size(width: int, height: int) -> tuple[int, int]:
    """Whole-number scale factors that reach VIDEO_LINES and come closest to 4:3."""
    lines = math.ceil(VIDEO_LINES / height)
    columns = max(1, round(lines * height * 4 / (3 * width)))
    return width * columns, height * lines


def stream_command(ffmpeg: str, stream: Path, lossless: Path) -> list[str]:
    """Read the stream of PPM frames into a lossless file; the rate is set later."""
    return [
        ffmpeg,
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "image2pipe",
        "-c:v",
        "ppm",
        "-framerate",
        "60",
        "-i",
        str(stream),
        "-c:v",
        "ffv1",
        str(lossless),
    ]


def video_command(
    ffmpeg: str, lossless: Path, sound: Path, video: Path, timing: recording.Timing
) -> list[str]:
    """HEVC at the measured frame rate, delayed by its offset from the sound, with AAC sound."""
    width, height = video_size(timing.width, timing.height)
    rate = f"{timing.rate:.6f}"
    filters = (
        f"setpts=N/({rate}*TB)+{timing.offset:.6f}/TB,"
        f"scale={width}:{height}:flags=neighbor,setdar=4/3"
    )
    return [
        ffmpeg,
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(lossless),
        "-i",
        str(sound),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-vf",
        filters,
        "-r",
        rate,
        "-c:v",
        "libx265",
        "-crf",
        "16",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-tag:v",
        "hvc1",
        "-x265-params",
        "log-level=error",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(video),
    ]


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


def instruction_set(project: Project, target: str) -> str:
    """The CPU that LWASM assembles for: the target's cpu, else the 6809."""
    return project.settings.targets[target].cpu or "6809"


def build(
    project: Project,
    host: Host,
    variant: str = "",
    extra_defines: Sequence[str] = (),
    cpu: str = "6809",
) -> Build:
    """Assemble fresh DECB output and symbols, then enforce the declared memory layout."""
    native = ("H6309",) if cpu == "6309" else ()
    defines = (*defines_for(project, variant), *extra_defines, *native)
    output = project.output
    output.mkdir(parents=True, exist_ok=True)
    suffix = ("6309",) if cpu == "6309" else ()
    stem = "-".join((variant or "main", *extra_defines, *suffix)).lower()
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
        cpu,
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


def emulator(project: Project, host: Host, target: str | None, disk: bool = False) -> list[str]:
    """Validate the actual firmware bytes before producing any launch command."""
    name, machine = target_machine(project, target)
    names = firmware_names(machine)
    if disk:
        if not machine.disk:
            raise ProjectError(
                f'[targets.{name}] names no Disk BASIC ROM; add disk = "<name>.rom" from '
                "the target tables in guidance/starter/toolchain.md."
            )
        names += (machine.disk,)
    roms = host.firmware(machine.firmware or name, names)
    return xroar_command(host.xroar(), machine, roms, disk)


def make_disk(project: Project, host: Host, built: Build) -> Path:
    """Write a fresh disk image beside the binary that holds only the program."""
    image = built.binary.with_suffix(".dsk")
    image.unlink(missing_ok=True)
    decb = host.executable("decb")
    for step, command in zip(
        ("dskini", "copy"),
        disk_commands(decb, built.binary.name, image.name, project.disk_name),
        strict=True,
    ):
        log = built.binary.with_suffix(f".{step}.log")
        host.run(command, log, timeout=30, cwd=image.parent)
    if not image.exists():
        raise ProjectError(f"decb did not write {image}; read the logs beside it.")
    return image


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
    disk: Path | None = None,
) -> Evidence:
    """Snapshot the Nth checkpoint hit; an unreachable checkpoint must leave no snapshot.

    With a disk image, Disk BASIC loads the program from drive 0 instead of XRoar's -run.
    """
    check = require_check(project)
    run = f"{target}-disk" if disk else target
    paths = recording_paths(built, run, frame)
    unreachable = built.binary.with_name(f"{built.binary.stem}-{run}-unreachable.ram")
    for path in (*paths.values(), unreachable):
        path.unlink(missing_ok=True)
    keys = project.settings.keys
    extra = DISK_SECONDS if disk else 0
    tv_input = target_machine(project, target)[1].tv_input
    command = emulator(project, host, target, disk=disk is not None) + capture_options(
        check, built.symbols, frame, paths["ram"], unreachable, equipment, keys, extra, tv_input
    )
    if disk:
        command += disk_options(disk, project.disk_name, write_back=False)
    else:
        command += ["-run", str(built.binary)]
    environment = None
    if equipment.uses_hooks:
        if equipment.keys is not None:
            paths["keys"].write_text(recording.key_lines(equipment.keys))
        inherited = {k: v for k, v in os.environ.items() if not k.startswith("COCO_")}
        environment = inherited | recording_environment(equipment, built.symbols, keys, paths)
    host.run(
        command, paths["log"], timeout=max(30.0, check.emulated_seconds + extra), env=environment
    )
    if unreachable.exists():
        raise ProjectError(f"The unreachable checkpoint {check.unreachable!r} fired.")
    if not paths["ram"].exists():
        loaded = " after LOADM from the disk" if disk else ""
        raise ProjectError(
            f"{target} did not reach {check.checkpoint!r} {frame} times{loaded} within "
            f"{check.emulated_seconds + extra:g} emulated seconds."
        )
    picture, sound, delivered = collect(paths, equipment) if equipment.uses_hooks else (None,) * 3
    return Evidence(
        ram=paths["ram"].read_bytes(),
        log=paths["log"],
        picture=picture,
        sound=sound,
        keys_delivered=delivered,
    )


def record(
    project: Project,
    host: Host,
    built: Build,
    target: str,
    seconds: float,
    equipment: Equipment,
) -> Path:
    """Record every frame and the mixer sound from power-on; return the video's path."""
    ffmpeg = host.encoder()
    stem = built.binary.with_name(f"{built.binary.stem}-{target}-record")
    paths = {
        kind: stem.with_suffix(f".{kind}")
        for kind in ("log", "frames", "mkv", "pcm", "wav", "mp4", "keys")
    }
    encoder_log = stem.with_suffix(".encode.log")
    unreachable = stem.with_name(f"{stem.name}-unreachable.ram")
    for path in (*paths.values(), encoder_log, unreachable):
        path.unlink(missing_ok=True)
    keys = project.settings.keys
    check = project.settings.check
    tv_input = target_machine(project, target)[1].tv_input
    command = emulator(project, host, target) + record_options(
        built.symbols, seconds, unreachable, check, equipment, keys, tv_input
    )
    command += ["-run", str(built.binary)]
    environment = {k: v for k, v in os.environ.items() if not k.startswith("COCO_")}
    environment |= {"COCO_FRAMES": str(paths["frames"]), "COCO_AUDIO": str(paths["pcm"])}
    if equipment.keys is not None:
        paths["keys"].write_text(recording.key_lines(equipment.keys))
        environment |= {
            "COCO_KEYS": str(paths["keys"]),
            "COCO_KEYS_AT": trap_condition(built.symbols, keys.at),
        }
    try:
        host.record(
            command,
            paths["log"],
            max(60.0, RECORD_PACE * seconds),
            environment,
            paths["frames"],
            stream_command(ffmpeg, paths["frames"], paths["mkv"]),
            encoder_log,
        )
    except ProjectError:
        log = paths["log"].read_text() if paths["log"].exists() else ""
        if "COCO_FRAMES_START" not in log:
            raise ProjectError(
                f"XRoar wrote no frames to the stream; read {paths['log']}. An emulator named "
                "by XROAR must include every patch in scripts/xroar_patches/."
            ) from None
        raise
    if unreachable.exists():
        raise ProjectError(f"The unreachable checkpoint {check.unreachable!r} fired.")
    log = recording.parse_log(paths["log"].read_text())
    timing = recording.frame_timing(log)
    raw = paths["pcm"].read_bytes() if paths["pcm"].exists() else b""
    rate, samples = recording.whole_sound(log, raw)
    recording.write_wav(paths["wav"], rate, samples)
    host.run(
        video_command(ffmpeg, paths["mkv"], paths["wav"], paths["mp4"], timing),
        encoder_log,
        max(120.0, RECORD_PACE * seconds),
    )
    for kind in ("mkv", "pcm"):
        paths[kind].unlink(missing_ok=True)
    return paths["mp4"]


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
    built = build(project, host, variant, cpu=instruction_set(project, target))
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
        "emulator": host.xroar(),
    }
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


def disk_check(
    project: Project, host: Host, built: Build, image: Path, target: str
) -> dict[str, object]:
    """Boot Disk BASIC, load the program from the image and require its first checkpoint hit.

    Only execution is checked: the typed command is on the screen, so expected.py does not
    describe it.
    """
    check = require_check(project)
    name, machine = target_machine(project, target)
    result = project.output / f"{name}-{built.variant or 'main'}-disk-results.json"
    result.unlink(missing_ok=True)
    frame = check.frames[0]
    capture(project, host, built, name, frame, disk=image)
    record = {
        "target": name,
        "machine": machine.model_dump(mode="json", exclude_defaults=True),
        "build": built.variant or "main",
        "disk_rom": machine.disk,
        "disk_image": str(image),
        "disk_image_sha256": digest(image),
        "program": f"{project.disk_name}.BIN",
        "typed": f'LOADM"{project.disk_name}":EXEC',
        "checkpoint": check.checkpoint,
        "frame": frame,
        "ram_init": "set (nonzero)",
        "unreachable_checkpoint": "no snapshot",
        "memory": "not compared: the typed command changes the screen",
        "visual": "not inspected by a person",
        "physical_hardware": "not tested",
    }
    result.write_text(json.dumps(record, indent=2) + "\n")
    return record


def disk_report(record: dict[str, object]) -> list[str]:
    return [
        (
            f"Disk: {record['target']} booted Disk BASIC with {record['disk_rom']}, typed "
            f"{record['typed']} and reached {record['checkpoint']!r} (hit {record['frame']}) in "
            f"build {record['build']}; the unreachable checkpoint left no snapshot."
        ),
        (
            "Memory: not compared on the disk boot; the typed command changes the screen. "
            "Run check for the screen and the model."
        ),
        "Visual: not inspected by a person; use disk --run and look.",
    ]


# --- Command line ---------------------------------------------------------------------------


COMMANDS = {
    "build": "assemble the project and print the binary path",
    "run": "assemble and open XRoar at normal speed",
    "snapshot": "save RAM (and any captures) at the Nth checkpoint hit and print the paths",
    "check": "compare each checkpoint with expected.py and report the evidence",
    "disk": "assemble the project onto a Disk BASIC disk image and print its path",
    "record": "record every frame and the sound from power-on as an HEVC video; print its path",
}


def add_equipment(command: argparse.ArgumentParser, name: str) -> None:
    command.add_argument("--video", action="store_true", help="save XRoar's rendered frame as PNG")
    command.add_argument("--audio", action="store_true", help="record XRoar's mixer output as WAV")
    if name == "snapshot":
        add_keys(command)


def add_keys(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--keys",
        type=Path,
        metavar="SCRIPT",
        help="key script to inject at the [keys] label",
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
        default = {
            "check": "every target",
            "disk": "the variant's first allowed target; with --check, every disk target",
        }.get(name, "the variant's first allowed target")
        command.add_argument("--target", help=f"a [targets.<name>] table; default: {default}")
        if name != "check":
            command.add_argument("--variant", default="", help="a [variants.<name>] build")
        if name == "disk":
            action = command.add_mutually_exclusive_group()
            action.add_argument(
                "--run", action="store_true", help="open XRoar and load the program from the disk"
            )
            action.add_argument(
                "--check",
                action="store_true",
                help=(
                    "boot the disk headless and require the first [check] checkpoint hit; "
                    "a variant's key script is not used"
                ),
            )
        if name == "snapshot":
            command.add_argument("--frame", type=int, default=1, help="checkpoint hit (from 1)")
        if name in ("snapshot", "check"):
            add_equipment(command, name)
        if name == "record":
            command.add_argument(
                "--seconds",
                type=positive_seconds,
                required=True,
                help="emulated seconds to record from power-on",
            )
            add_keys(command)
    return result


def positive_seconds(text: str) -> float:
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number of seconds") from error
    if not 0 < value <= 3600:
        raise argparse.ArgumentTypeError("give between 0 and 3600 seconds")
    return value


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
    built = build(project, host, arguments.variant, cpu=instruction_set(project, target))
    evidence = capture(project, host, built, target, arguments.frame, equipment)
    print(evidence.log.with_suffix(".ram"))
    for recorded in (evidence.picture, evidence.sound):
        if recorded:
            print(recorded.path)


def record_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    target = variant_target(project, arguments.variant, arguments.target)
    equipment = equipment_for(project, arguments.variant, script=arguments.keys)
    built = build(project, host, arguments.variant, cpu=instruction_set(project, target))
    print(record(project, host, built, target, arguments.seconds, equipment))


def disk_targets(project: Project, arguments: argparse.Namespace) -> list[str]:
    """The named target, else every target the variant allows; each must name a disk ROM."""
    if arguments.target:
        name = variant_target(project, arguments.variant, arguments.target)
        if not project.settings.targets[name].disk:
            raise ProjectError(
                f'[targets.{name}] names no Disk BASIC ROM; add disk = "<name>.rom" from '
                "the target tables in guidance/starter/toolchain.md."
            )
        return [name]
    declared = project.settings.variants.get(arguments.variant)
    targets = [
        name
        for name, machine in project.settings.targets.items()
        if machine.disk and (declared is None or declared.applies_to(name))
    ]
    if not targets:
        raise ProjectError(
            'No target names a Disk BASIC ROM; add disk = "<name>.rom" to a target table.'
        )
    return targets


def disk_instruction_set(
    project: Project, arguments: argparse.Namespace, targets: list[str]
) -> str:
    """One disk image serves every disk target, so they must share an instruction set."""
    names = targets or [variant_target(project, arguments.variant, arguments.target)]
    cpus = {instruction_set(project, name) for name in names}
    if len(cpus) > 1:
        raise ProjectError(
            f"The disk targets {names} use different CPUs ({', '.join(sorted(cpus))}); "
            "name one with --target."
        )
    return cpus.pop()


def disk_command(project: Project, arguments: argparse.Namespace, host: Host) -> None:
    """Make the image; --run opens the first disk target, --check boots every one."""
    targets = disk_targets(project, arguments) if arguments.run or arguments.check else []
    if arguments.check:
        require_check(project)
    built = build(
        project, host, arguments.variant, cpu=disk_instruction_set(project, arguments, targets)
    )
    image = make_disk(project, host, built)
    if arguments.run:
        host.launch(
            emulator(project, host, targets[0], disk=True)
            + ["-ratelimit", *disk_options(image, project.disk_name)]
        )
        return
    if arguments.check:
        for target in targets:
            for line in disk_report(disk_check(project, host, built, image, target)):
                print(line)
        print(f"PASS: {project.name} disk; evidence in {project.output}")
        return
    print(image)


def execute(arguments: argparse.Namespace, host: Host) -> None:
    project = load_project(arguments.project)
    if arguments.command == "check":
        check_command(project, arguments, host)
        return
    if arguments.command == "snapshot":
        snapshot_command(project, arguments, host)
        return
    if arguments.command == "disk":
        disk_command(project, arguments, host)
        return
    if arguments.command == "record":
        record_command(project, arguments, host)
        return
    target = variant_target(project, arguments.variant, arguments.target)
    built = build(project, host, arguments.variant, cpu=instruction_set(project, target))
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
