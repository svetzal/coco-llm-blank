"""Build and measure an original hidden-screen renderer without a GUI."""

import argparse
import collections
import json
import os
import re
import subprocess
import sys
import tarfile
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "experiments/animation-cadence")]
import cadence
from coco import load_expected, load_project
from native import tool_path
from roms import verify_installed
from timing import publication_phases

MOVING_PROJECT = ROOT / "examples/moving-objects"
MOVING = load_expected(MOVING_PROJECT)
expected_screen, position, verify_ram = MOVING.expected_screen, MOVING.position, MOVING.verify_ram
ROM_NAMES = {
    name: (machine.basic, machine.extended)
    for name, machine in load_project(MOVING_PROJECT).settings.targets.items()
}

PERIOD = 238944
CHECKS = (1, 2, 16, 32, 64, 65, 185, 186, 369, 370)
WRITE_LOG = r"""
    if (!md->clock_inhibit && md->CPU->reg_pc >= 0x4000
        && md->CPU->reg_pc < 0x7e00 && A >= 0x3f00 && A <= 0x3f03) {
        const char *path = getenv("CLEAN_EVENTS");
        if (path) {
            FILE *fp = fopen(path, "a");
            if (!fp) { perror(path); exit(2); }
            fprintf(fp, "%u %u\n", (unsigned)event_current_tick, A - 0x3f00);
            if (fclose(fp)) exit(2);
        }
    }
"""


def build_emulator(work: Path, out: Path, archive: Path | None) -> tuple[Path, dict]:
    archive = cadence.obtain_archive(work / "xroar.tar.gz", archive)
    with tarfile.open(archive) as package:
        package.extractall(work, filter="data")
    tree = work / "xroar-1.12.1"
    names = (
        "src/null/ui_null.c",
        "src/dragon/dragon.c",
        "src/mc6821.c",
        "src/mc6883.c",
        "src/mc6847/mc6847.c",
        "src/mc6847/mc6847.h",
        "src/events.h",
    )
    before = {name: cadence.digest(tree / name) for name in names}
    ui = tree / names[0]
    ui.write_bytes(cadence.patch(ui.read_bytes()))
    dragon = tree / names[1]
    dragon.write_text(
        cadence.replace_once(
            dragon.read_text(),
            "static void write_byte(struct dragon *md, unsigned A) {",
            "static void write_byte(struct dragon *md, unsigned A) {" + WRITE_LOG,
        )
    )
    cadence.logged(cadence.CONFIGURE, tree, out / "configure.log")
    cadence.logged(["make", "-j2"], tree, out / "make.log")
    exe = tree / "src/xroar"
    return exe, {
        "archive_sha256": cadence.digest(archive),
        "upstream_sha256": before,
        "patched_ui_sha256": cadence.digest(ui),
        "patched_dragon_sha256": cadence.digest(dragon),
        "executable_sha256": cadence.digest(exe),
        "configure": cadence.CONFIGURE,
    }


def assemble(source: str, out: Path) -> tuple[Path, dict]:
    asm, binary, sym = (out / f"program.{ext}" for ext in ("asm", "bin", "sym"))
    asm.write_text(source)
    command = [
        tool_path("lwasm", ROOT),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={sym}",
        str(asm),
    ]
    cadence.logged(command, ROOT, out / "assembly.log", 30)
    (out / "assembly-command.json").write_text(json.dumps(command))
    symbols = {
        k: int(v, 16)
        for k, v in re.findall(r"^(\w+)\s+EQU\s+\$([\da-fA-F]+)", sym.read_text(), re.MULTILINE)
    }
    if symbols["program_end"] >= 0x7E00:
        raise ValueError("stack overlap")
    return binary, symbols


def command(exe: Path, target: str, binary: Path) -> tuple[list[str], dict]:
    basic, extended = ROM_NAMES[target]
    firmware = verify_installed(ROOT, target, (basic, extended))
    cmd = [
        str(exe),
        "-c",
        os.devnull,
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        "cocous",
        "-machine-cpu",
        "6809",
        "-vdg-type",
        "6847",
        "-ram",
        "32",
        "-bas",
        str(firmware[basic]),
        "-extbas",
        str(firmware[extended]),
        "-no-cart",
        "-tv-input",
        "svideo",
        "-ccr",
        "none",
        "-vo-picture",
        "zoomed",
        "-fskip",
        "0",
        "-ram-init",
        "set",
        "-ratelimit",
        "-timeout",
        "120",
    ]
    return cmd, {name: cadence.digest(path) for name, path in firmware.items()}


def launch(cmd: list[str], out: Path, name: str, capture: bool) -> None:
    env = {k: v for k, v in os.environ.items() if k not in ("CADENCE_CAPTURE", "CLEAN_EVENTS")}
    if capture:
        env.update(CADENCE_CAPTURE=str(out / "video.frames"), CLEAN_EVENTS=str(out / "events.txt"))
    (out / f"{name}-command.json").write_text(json.dumps(cmd, indent=2))
    with (out / f"{name}.log").open("wb") as log:
        subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=40)


def verify_hidden(data: bytes, symbols: dict, frame: int) -> None:
    if len(data) != 32768 or any(data[a] != 0xA5 for a in (0x3FF, 0x1C00, 0x23FF, 0x3C00)):
        raise ValueError("RAM size or screen guards")
    at = symbols["frames"]
    if int.from_bytes(data[at : at + 2], "big") != frame:
        raise ValueError("scene count")
    if (data[symbols["xpos"]], data[symbols["ypos"]]) != position(frame):
        raise ValueError("motion state")
    at = symbols["drawing"]
    base = int.from_bytes(data[at : at + 2], "big")
    if base != (0x2400 if frame % 2 else 0x400):
        raise ValueError("hidden screen identity")
    if data[base : base + 6144] != expected_screen(frame):
        raise ValueError("hidden scene")
    other = base ^ 0x2000
    if frame > 1 and data[other : other + 6144] != expected_screen(frame - 1):
        raise ValueError("previous complete scene was modified")


def require_clean(measurement: dict) -> None:
    matches = measurement["scene_matches"]
    if any(scene is None for scene in matches):
        raise ValueError("intermediate scene reached renderer")
    transitions = [b - a for a, b in pairwise(matches) if b != a]
    if len(transitions) < 2 or set(transitions) != {1}:
        raise ValueError("missing, reversed or frozen scene progression")


def costs(path: Path, renderer_ticks: list[int]) -> dict:
    events = [tuple(map(int, line.split())) for line in path.read_text().splitlines()]
    # The final started or completed draw can be cut off by the bounded run.
    if any(kind != i % 4 for i, (_, kind) in enumerate(events)):
        raise ValueError("missing cost markers")
    if any(b[0] < a[0] for a, b in pairwise(events)):
        raise ValueError("invalid event chronology across draw and reuse boundaries")
    completed = []
    for i in range(0, len(events) - 3, 4):
        group = events[i : i + 4]
        completed.append([tick for tick, _ in group])
    if len(completed) < 3:
        raise ValueError("missing completed-scene costs")
    draw = [b - a for a, b, _, _ in completed]
    wait = [c - b for _, b, c, _ in completed]
    publish = [b[2] - a[2] for a, b in pairwise(completed)]
    if min(draw + wait + publish) <= 0:
        raise ValueError("invalid event chronology")
    return {
        "phases": publication_phases(completed, renderer_ticks),
        "completed_scenes": len(completed),
        "draw_ticks": dict(collections.Counter(draw)),
        "wait_and_publish_ticks": dict(collections.Counter(wait)),
        "publication_interval_ticks": dict(collections.Counter(publish)),
        "completed_scene_hz": 14318180
        * (len(completed) - 1)
        / (completed[-1][2] - completed[0][2]),
    }


def run_case(exe: Path, target: str, variant: str, out: Path, scenes: list[bytes]) -> dict:
    out.mkdir()
    source = (HERE / "main.asm").read_text()
    if variant == "single":
        source = (ROOT / "examples/moving-objects/main.asm").read_text()
    elif variant == "heavy":
        source = cadence.source_for(source, True)
    binary, symbols = assemble(source, out)
    cmd, firmware = command(exe, target, binary)
    unreachable = out / "unreachable.ram"
    traps = ["-trap", f"pc=0x{symbols['state']:x}", "-trap-snap", str(unreachable)]
    traps += [
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        "1-1",
        "-trap-snap",
        str(out / "scene-1.ram"),
        "-trap-timeout",
        "3.5",
    ]
    launch(cmd + traps + ["-run", str(binary)], out, "continuous", True)
    if unreachable.exists():
        raise ValueError("unreachable checkpoint fired")
    verify = verify_ram if variant == "single" else verify_hidden
    verify((out / "scene-1.ram").read_bytes(), symbols, 1)
    frames = cadence.records(out / "video.frames")
    measurement = cadence.analyze(frames, scenes)
    if variant != "single":
        require_clean(measurement)
    result = {
        "rom_sha256": firmware,
        "measurement": measurement,
        "binary_sha256": cadence.digest(binary),
        "source_sha256": cadence.digest(out / "program.asm"),
        "capture_sha256": cadence.digest(out / "video.frames"),
        "program_end": symbols["program_end"],
    }
    if variant != "single":
        result["costs"] = costs(out / "events.txt", [tick for tick, _ in frames])
    if variant == "normal":
        ram_checks(exe, target, binary, symbols, out, unreachable)
        result["ram_scenes"] = list(CHECKS)
    return result


def ram_checks(
    exe: Path, target: str, binary: Path, symbols: dict, out: Path, negative: Path
) -> None:
    # XRoar has a bounded breakpoint list: use one counted checkpoint per run.
    for frame in CHECKS:
        cmd, _ = command(exe, target, binary)
        cmd = [("-no-ratelimit" if arg == "-ratelimit" else arg) for arg in cmd]
        cmd += [
            "-trap",
            f"pc=0x{symbols['state']:x}",
            "-trap-snap",
            str(negative),
            "-trap",
            f"pc=0x{symbols['frame_ready']:x}",
            "-trap-range",
            f"{frame}-{frame}",
            "-trap-snap",
            str(out / f"check-{frame}.ram"),
            "-trap-timeout",
            "0",
            "-run",
            str(binary),
        ]
        launch(cmd, out, f"ram-{frame}", False)
        if negative.exists():
            raise ValueError("unreachable checkpoint fired")
        verify_hidden((out / f"check-{frame}.ram").read_bytes(), symbols, frame)


def require_controls(cases: dict) -> None:
    for target in ROM_NAMES:
        normal, heavy, single, repeat = (
            cases[f"{target}-{v}"] for v in ("normal", "heavy", "single", "repeat")
        )
        if normal["measurement"] != repeat["measurement"] or normal["costs"] != repeat["costs"]:
            raise ValueError("repeat differs")
        if not single["measurement"]["non_complete_scene_frames"]:
            raise ValueError("single-buffer failure control did not fail")
        if heavy["costs"]["completed_scene_hz"] >= normal["costs"]["completed_scene_hz"]:
            raise ValueError("workload did not reduce completed-scene cadence")
        if min(map(int, normal["costs"]["draw_ticks"])) <= PERIOD:
            raise ValueError("overlong draw premise not demonstrated")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]+", args.run_id):
        parser.error("invalid run-id")
    work = ROOT / "local/research/clean-animation" / args.run_id
    out = ROOT / "build/clean-animation" / args.run_id
    if work.exists() or out.exists():
        parser.error("run exists")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    exe, build = build_emulator(work, out, args.archive)
    report = {
        "build": build,
        "inputs_sha256": {
            str(p.relative_to(ROOT)): cadence.digest(p)
            for p in [
                *HERE.glob("*.py"),
                HERE / "main.asm",
                Path(cadence.__file__),
                MOVING_PROJECT / "expected.py",
                MOVING_PROJECT / "coco.toml",
                ROOT / "examples/moving-objects/main.asm",
                ROOT / "experiments/display-validation/instrument.py",
                ROOT / "experiments/display-validation/reproduce.py",
            ]
        },
        "cases": {},
    }
    scenes = [expected_screen(i) for i in range(1, 65)]
    for target in ROM_NAMES:
        for variant in ("normal", "heavy", "single", "repeat"):
            name = f"{target}-{variant}"
            report["cases"][name] = run_case(exe, target, variant, out / name, scenes)
            print(name, report["cases"][name].get("costs", {}), flush=True)
    require_controls(report["cases"])
    report["passed"] = True
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
