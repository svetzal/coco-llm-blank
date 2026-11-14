"""Play the Collect room journey with injected keys in an instrumented XRoar.

The example's own check (scripts/coco.py check examples/collect-room) uses stock
XRoar, so it cannot press keys. This harness builds a pinned XRoar with the
example's keyboard and audio hooks, replays journey.txt, checks every frame with
the example's independent model, and requires four deliberate game mutations to
be rejected.
"""

import argparse
import hashlib
import itertools
import json
import os
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from coco import Host, build, emulator, load_expected, load_project

EXAMPLE = ROOT / "examples/collect-room"
OUTPUT = ROOT / "build/collect-room-journey"
URL = "https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz"
SHA256 = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
MUTATIONS = ("WRONG_COLUMN", "STALE_HISTORY", "HELD_SPACE", "SILENT")
# Failures that show the model rejected a mutation, not a broken tool or build.
REJECTIONS = ("Game state differs", "Keyboard/history differs", "Actual DAC values differ")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model():
    return load_expected(EXAMPLE)


def patch_once(path: Path, anchor: str, replacement: str) -> None:
    text = path.read_text()
    if text.count(anchor) != 1:
        raise ValueError(f"Instrumentation anchor differs: {path.name}")
    path.write_text(text.replace(anchor, replacement))


def manifest(binary: Path) -> dict[str, str]:
    return {
        "source_sha256": SHA256,
        "keyboard_hook": digest(EXAMPLE / "key_hook.c"),
        "audio_hook": digest(EXAMPLE / "audio_hook.c"),
        "binary_sha256": digest(binary),
    }


def prepare_emulator(host: Host) -> Path:
    """Build pinned headless XRoar locally. No install or shared source mutation."""
    work = OUTPUT / "instrumented"
    work.mkdir(parents=True, exist_ok=True)
    archive = work / "xroar-1.12.1.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive.write_bytes(response.read())
    if digest(archive) != SHA256:
        raise ValueError("XRoar source checksum differs")
    source = work / "xroar-1.12.1"
    if source.exists():
        shutil.rmtree(source)
    with tarfile.open(archive) as package:
        package.extractall(work, filter="data")
    anchor = "static void handle_trap(void *sptr) {\n\tstruct trap_def *trap = sptr;"
    patch_once(
        source / "src/xroar.c",
        anchor,
        (EXAMPLE / "key_hook.c").read_text() + "\n" + anchor + "\n\tcollect_keyboard(trap->cond);",
    )
    anchor = "static void pia1a_data_postwrite_coco(void *sptr) {\n\tstruct dragon *md = sptr;"
    patch_once(
        source / "src/dragon/coco.c", anchor, anchor + "\n" + (EXAMPLE / "audio_hook.c").read_text()
    )
    configure = ["./configure"] + [f"--without-{name}" for name in ("gtk2", "gtk3", "sdl3", "sdl2")]
    for name, command in (("configure", configure), ("make", ["make", "-j2"])):
        host.run(command, work / f"{name}.log", timeout=240, cwd=source)
    binary = source / "src/xroar"
    (work / "build.json").write_text(json.dumps(manifest(binary), indent=2) + "\n")
    return binary


def checked_emulator() -> Path:
    work = OUTPUT / "instrumented"
    binary = work / "xroar-1.12.1/src/xroar"
    if json.loads((work / "build.json").read_text()) != manifest(binary):
        raise ValueError("Instrumented emulator changed; run prepare again")
    return binary


def capture_command(
    host: Host,
    target: str,
    emulator_path: Path,
    binary: Path,
    labels: dict[str, int],
    output: Path,
    count: int,
    unreachable: bool,
) -> list[str]:
    project = load_project(EXAMPLE)
    command = emulator(project, host, target, str(emulator_path)) + [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "15",
        "-trap",
        f"pc=0x{labels['sample']:04x}",
        "-trap-range",
        f"1-{count}",
        "-trap",
        f"pc=0x{labels['room']:04x}",
        "-trap-snap",
        str(output / "unreachable.ram"),
    ]
    address = labels["room"] if unreachable else labels["frame_ready"]
    command += ["-trap", f"pc=0x{address:04x}", "-trap-range", f"1-{count}"]
    return command + ["-run", str(binary)]


def audio_evidence(log: str, labels: dict[str, int], expected_effects: int) -> dict:
    rows = [line.split(",")[1:] for line in log.splitlines() if line.startswith("DAC,")]
    samples = [
        (int(r[0]), *[int(value, 16) for value in r[1:]])
        for r in rows
        if int(r[1], 16) == labels["dac_write"] + 3
    ]
    if [r[2] & 0xFC for r in samples] != [252, 0] * (16 * expected_effects):
        raise ValueError("Actual DAC values differ")
    for _, _, _, cr, ddr, mux_a, mux_b, enable in samples:
        if not (cr & 4 and ddr & 252 == 252 and not (mux_a & 8 or mux_b & 8) and enable & 8):
            raise ValueError("DAC direction or routing differs")
    ticks = [r[0] for r in samples]
    gaps = [b - a for i, (a, b) in enumerate(itertools.pairwise(ticks)) if (i + 1) % 32]
    return {
        "dac_writes": len(samples),
        "within_burst_tick_range": [min(gaps), max(gaps)] if gaps else [],
        "listening": "not performed",
    }


def capture_environment(labels: dict[str, int], output: Path, count: int, inject: bool) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("COLLECT_EVENTS", "COLLECT_KEY_TRAP")}
    env.update(
        COLLECT_FRAME_TRAP=f"pc=0x{labels['frame_ready']:04x}",
        COLLECT_OUTPUT=str(output),
        COLLECT_FRAME_COUNT=str(count),
    )
    if inject:
        env.update(
            COLLECT_EVENTS=str(output / "events.txt"),
            COLLECT_KEY_TRAP=f"pc=0x{labels['sample']:04x}",
        )
    return env


def verify_capture(output: Path, labels: dict[str, int], cases: list, inject: bool) -> dict:
    log = (output / "xroar.log").read_text()
    if log.count("KEY,") != (len(cases) if inject else 0):
        raise ValueError("Keyboard event count differs")
    for index, (keys, state) in enumerate(cases):
        if not inject:
            keys, state = "-", model().TITLE
        model().verify_journey_frame(
            (output / f"frame-{index}.ram").read_bytes(), labels, keys, state
        )
    audio = audio_evidence(log, labels, cases[-1][1][6] if inject else 0)
    ticks = [int(line.split(",")[3]) for line in log.splitlines() if line.startswith("KEY,")]
    gaps = [b - a for a, b in itertools.pairwise(ticks)]
    return {"audio": audio, "scan_interval_ticks": [min(gaps), max(gaps)] if gaps else []}


def execute_case(
    host: Host, target: str, mutation: str, inject: bool, unreachable: bool, output: Path
) -> dict:
    if mutation and mutation not in MUTATIONS:
        raise ValueError("Unknown mutation")
    project = load_project(EXAMPLE)
    built = build(project, host, "", (mutation,) if mutation else ())
    emu = checked_emulator()
    cases = model().journey()
    (output / "events.txt").write_text("\n".join(keys for keys, _ in cases) + "\n")
    command = capture_command(
        host, target, emu, built.binary, built.symbols, output, len(cases), unreachable
    )
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    environment = capture_environment(built.symbols, output, len(cases), inject)
    host.run(command, output / "xroar.log", timeout=45, cwd=output, env=environment)
    if (output / "unreachable.ram").exists():
        raise ValueError("Unreachable trap fired")
    if unreachable:
        if list(output.glob("frame-*.ram")):
            raise ValueError("False checkpoint created RAM")
        return {"status": "passed", "unreachable": "no snapshot"}
    evidence = verify_capture(output, built.symbols, cases, inject)
    machine = project.settings.targets[target]
    roms = host.firmware(machine.firmware or target, (machine.basic, machine.extended))
    return {
        "status": "passed",
        "target": target,
        "machine": machine.machine,
        "ram_kib": machine.ram_kib,
        "cpu": machine.cpu,
        "video": f"{machine.tv.upper()} {machine.vdg}",
        "clock": "normal",
        "checkpoints": len(cases),
        "framebuffer_bytes_each": 6144,
        "input": "XRoar keyboard API to PIA to scanner" if inject else "no injected keys",
        "binary_sha256": digest(built.binary),
        "emulator_sha256": digest(emu),
        "rom_sha256": {name: digest(path) for name, path in roms.items()},
        "program_end": built.symbols["program_end"],
        **evidence,
        "tick_rate_hz": 14318180,
        "renderer": "not captured or inspected",
        "physical": "not tested",
    }


def run_case(
    host: Host, target: str, mutation: str = "", inject: bool = True, unreachable: bool = False
) -> dict:
    """Invalidate previous evidence before build/ROM validation, including failed reruns."""
    name = f"{target}-{mutation or 'normal'}-{'keys' if inject else 'idle'}"
    if unreachable:
        name += "-unreachable"
    output = OUTPUT / name
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    report = output / "result.json"
    report.write_text('{"status":"incomplete"}\n')
    try:
        result = execute_case(host, target, mutation, inject, unreachable, output)
    except BaseException as error:
        report.write_text(json.dumps({"status": "failed", "error": str(error)}, indent=2) + "\n")
        raise
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def check(host: Host, target: str) -> dict:
    report = OUTPUT / f"{target}-check.json"
    report.unlink(missing_ok=True)
    result = run_case(host, target)
    run_case(host, target, inject=False)
    run_case(host, target, inject=False, unreachable=True)
    rejected = []
    for mutation in MUTATIONS:
        try:
            run_case(host, target, mutation)
        except ValueError as error:
            # A failed build, missing snapshot or tool failure is not a killed mutation.
            if not any(message in str(error) for message in REJECTIONS):
                raise
            rejected.append(mutation)
        else:
            raise ValueError(f"False control was accepted: {mutation}")
    result["rejected_mutations"] = rejected
    result["controls"] = ["no input stays at title", "unreachable has no snapshot"]
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main(argv: list[str] | None = None, host: Host | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "check"))
    parser.add_argument("--target", choices=("coco1", "coco2"), default="coco1")
    args = parser.parse_args(argv)
    host = host or Host()
    if args.action == "prepare":
        print(prepare_emulator(host))
    else:
        print(json.dumps(check(host, args.target), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
