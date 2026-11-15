"""Run real keyboard, renderer and mixer capture without changing the game."""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "experiments/collect-room-journey"))
from coco import Host, build, load_expected, load_project
from journey import EXAMPLE, audio_evidence, capture_command
from measure_output import audio_measure, rows, timeline, video_measure
from prepare_output import digest, verify

MODEL = load_expected(EXAMPLE)


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def inspect(output: Path, labels: dict, cases: list) -> dict:
    log = (output / "xroar.log").read_text()
    raw = (output / "output.pcm").read_bytes()
    result = timeline(raw, (output / "output.rgb").stat().st_size, log, len(cases))
    keys = rows(log, "KEY")
    expected = [sum(1 << i for i, name in enumerate("UDLRFM") if name in k) for k, _ in cases]
    if [(r[0], r[1]) for r in keys] != list(enumerate(expected)):
        raise ValueError("Keyboard injection sequence missing or different")
    for i, (key, state) in enumerate(cases):
        MODEL.verify_journey_frame((output / f"frame-{i}.ram").read_bytes(), labels, key, state)
    result["routing"] = audio_evidence(log, labels, 5)
    result["video"] = video_measure(output / "output.rgb", log, cases)
    result["audio"] = audio_measure(raw, log, cases)
    result["capture_sha256"] = {
        n: digest(output / n) for n in ("output.rgb", "output.pcm", "xroar.log")
    }
    return result


def execute(xroar: Path, output: Path, target: str, control: str) -> dict:
    provenance = verify(xroar)
    built = build(load_project(EXAMPLE), Host())
    binary, labels = built.binary, built.symbols
    cases = MODEL.journey()[:43]
    (output / "events.txt").write_text("\n".join(k for k, _ in cases) + "\n")
    write(output / "labels.json", labels)
    command = capture_command(Host(), target, xroar, binary, labels, output, len(cases), False)
    command[command.index("-no-ratelimit")] = "-ratelimit"
    command += [
        "-tv-input",
        "svideo",
        "-ccr",
        "none",
        "-vo-picture",
        "zoomed",
        "-fskip",
        "0",
        "-ao-gain",
        "-100" if control == "audio" else "-3",
    ]
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("COLLECT_", "AUDIO_CAPTURE", "VIDEO_CAPTURE", "BROKEN_VIDEO"))
    }
    env.update(
        COLLECT_FRAME_TRAP=f"pc=0x{labels['frame_ready']:04x}",
        COLLECT_OUTPUT=str(output),
        COLLECT_FRAME_COUNT=str(len(cases)),
        AUDIO_CAPTURE=str(output / "output.pcm"),
        VIDEO_CAPTURE=str(output / "output.rgb"),
    )
    if control != "input":
        env.update(
            COLLECT_EVENTS=str(output / "events.txt"),
            COLLECT_KEY_TRAP=f"pc=0x{labels['sample']:04x}",
        )
    if control == "video":
        env["BROKEN_VIDEO"] = "1"
    inputs = [
        "scripts/coco.py",
        "examples/collect-room/coco.toml",
        "examples/collect-room/expected.py",
        "examples/collect-room/assets.py",
        "experiments/collect-room-journey/journey.py",
        "examples/collect-room/main.asm",
        "examples/collect-room/journey.txt",
        "examples/collect-room/letters.json",
        "examples/collect-room/terrain.png",
        "scripts/graphics.py",
        "roms.json",
    ]
    inputs += [str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob("*.py")]
    rom_paths = [Path(command[command.index(flag) + 1]) for flag in ("-bas", "-extbas")]
    write(
        output / "contract.json",
        {
            "command": command,
            "target": target,
            "control": control,
            "host": platform.platform(),
            "machine": platform.machine(),
            "verified_build": provenance,
            "input_sha256": {p: digest(ROOT / p) for p in inputs},
            "rom_sha256": {p.name: digest(p) for p in rom_paths},
            "binary_sha256": digest(binary),
            "symbols_sha256": digest(binary.with_suffix(".sym")),
            "checkpoints": 43,
            "capture_environment": {
                k: v
                for k, v in env.items()
                if k.startswith(("COLLECT_", "AUDIO_", "VIDEO_", "BROKEN_"))
            },
        },
    )
    with (output / "xroar.log").open("w") as log:
        subprocess.run(
            command,
            cwd=output,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=60,
        )
    if (output / "unreachable.ram").exists():
        raise ValueError("Unreachable trap fired")
    return inspect(output, labels, cases)


def run(xroar: Path, output: Path, target: str, control: str = "none") -> dict:
    output.mkdir(parents=True, exist_ok=False)
    write(output / "result.json", {"status": "incomplete"})
    try:
        result = execute(xroar, output, target, control)
    except BaseException as error:
        write(output / "result.json", {"status": "failed", "error": str(error), "control": control})
        raise
    result["status"] = "passed"
    write(output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xroar", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target", choices=("coco1", "coco2"), required=True)
    parser.add_argument("--control", choices=("none", "audio", "video", "input"), default="none")
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.xroar.resolve(), args.output.resolve(), args.target, args.control), indent=2
        )
    )
