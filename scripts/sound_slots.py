"""Build, check, or run the CoCo 1 cooperative sound experiment."""

import argparse
import itertools
import json
import re
import subprocess
from pathlib import Path

from coco import Host, load_project
from coco import emulator as project_emulator
from native import ROOT

executable = Host().executable


def emulator(binary: Path) -> list[str]:
    """Transitional: the CoCo 1 profile declared by the first-screen project."""
    return project_emulator(load_project(ROOT / "examples/first-screen"), Host(), None)


CHECK_FRAMES = (1, 16, 17, 32, 33, 63, 64)


def build(scripted: bool = False) -> tuple[Path, dict[str, int]]:
    output = ROOT / "build/sound-slots"
    output.mkdir(parents=True, exist_ok=True)
    stem = "scripted" if scripted else "live"
    binary = output / f"{stem}.bin"
    symbols = output / f"{stem}.sym"
    subprocess.run(
        [
            executable("lwasm"),
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
        ]
        + (["--define=SCRIPTED"] if scripted else [])
        + [str(ROOT / "examples/sound-slots/main.asm")],
        check=True,
    )
    addresses = {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }
    return binary, addresses


def expected_button(frame: int, scripted: bool) -> int:
    """The fixture holds released/pressed for alternating blocks of sixteen frames."""
    return 1 - ((frame - 1) // 16 % 2) if scripted else 1


def expected_samples(scripted: bool) -> list[int]:
    phase = 0
    pitch = 0x0800
    result = []
    for frame in range(1, 65):
        for _ in range(256):
            phase = (phase + pitch) % 65536
            result.append((phase >> 8) & 0xFC)
        pitch = 0x0800 if expected_button(frame, scripted) else 0x1000
    return result


def verify_ram(data: bytes, symbols: dict[str, int], frame: int, scripted: bool) -> None:
    def word(name: str) -> int:
        return int.from_bytes(data[symbols[name] : symbols[name] + 2], "big")

    if len(data) != 32768 or data[0x03FF] != 0xA5 or data[0x1C00] != 0xA5:
        raise ValueError("Missing initialized RAM or damaged framebuffer guards.")
    button = expected_button(frame, scripted)
    if (word("frames"), word("samples"), word("pitch"), word("phase")) != (
        frame,
        frame * 256,
        0x0800 if button else 0x1000,
        0,
    ) or data[symbols["button"]] != button:
        raise ValueError("Sound/input state differs from the frame specification.")
    screen = bytearray(6144)
    screen[96 * 32 + frame % 32] = 0xFF
    if data[0x400:0x1C00] != screen or data[symbols["position"]] != frame % 32:
        raise ValueError("Moving marker or background differs from the screen specification.")


def verify_trace(trace: str, sample_address: int, scripted: bool) -> dict[str, int]:
    instructions = re.findall(r"^([0-9a-f]{4})\|.*$", trace, re.MULTILINE)
    records = re.findall(r"^([0-9a-f]{4})\|.*?\ba=([0-9a-f]{2})\b.*$", trace, re.MULTILINE)
    writes = [
        (i, int(a, 16) & 0xFC) for i, (pc, a) in enumerate(records) if int(pc, 16) == sample_address
    ]
    if len(records) != len(instructions) or [a for _, a in writes] != expected_samples(scripted):
        raise ValueError("DAC instruction trace differs from the independent phase model.")
    gaps = [right[0] - left[0] for left, right in itertools.pairwise(writes)]
    if max(gaps) <= min(gaps):
        raise ValueError("Trace did not exercise the extra input/graphics work.")
    return {
        "dac_writes": len(writes),
        "minimum_instructions_between_writes": min(gaps),
        "maximum_instructions_between_writes": max(gaps),
    }


def run_frame(binary: Path, symbols: dict[str, int], frame: int) -> bytes:
    snapshot = binary.with_name(f"{binary.stem}-{frame}.ram")
    snapshot.unlink(missing_ok=True)
    negative = binary.with_suffix(".unreachable.ram")
    negative.unlink(missing_ok=True)
    command = emulator(binary) + [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "10",
        "-trap",
        f"pc=0x{symbols['state']:x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['sample']:x}",
        "-trap-range",
        "1",
        "-trap-trace",
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        str(frame),
        "-trap-snap",
        str(snapshot),
        "-trap-no-trace",
        "-trap-timeout",
        "0",
        "-run",
        str(binary),
    ]
    with binary.with_suffix(".trace").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    if negative.exists():
        raise ValueError("Unreachable checkpoint fired.")
    return snapshot.read_bytes()


def check(scripted: bool) -> dict[str, int]:
    binary, symbols = build(scripted)
    for frame in CHECK_FRAMES:
        verify_ram(run_frame(binary, symbols, frame), symbols, frame, scripted)
    return verify_trace(binary.with_suffix(".trace").read_text(), symbols["sample"], scripted)


def measure_second() -> dict[str, int]:
    """Bound throughput using the last complete frame in one emulated second."""
    binary, symbols = build()
    snapshot = binary.with_name("one-second.ram")
    snapshot.unlink(missing_ok=True)
    command = emulator(binary) + [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "10",
        "-trap",
        f"pc=0x{symbols['sample']:x}",
        "-trap-range",
        "1",
        "-trap-timeout",
        "1",
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        "1-",
        "-trap-snap",
        str(snapshot),
        "-run",
        str(binary),
    ]
    subprocess.run(command, capture_output=True, check=True, timeout=30)
    data = snapshot.read_bytes()
    frame = int.from_bytes(data[symbols["frames"] : symbols["frames"] + 2], "big")
    if not 1 <= frame < 255:
        raise ValueError("One-second experiment did not produce a bounded frame count.")
    verify_ram(data, symbols, frame, False)
    return {
        "complete_frames_in_one_emulated_second": frame,
        "minimum_samples_per_second": frame * 256,
        "maximum_samples_per_second": (frame + 1) * 256,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    action = parser.parse_args().action
    if action == "run":
        binary, _ = build()
        subprocess.run(emulator(binary) + ["-ratelimit", "-run", str(binary)], check=True)
        return
    results = {
        "released_input": check(False),
        "scripted_input": check(True),
        "throughput": measure_second(),
    }
    path = ROOT / "build/sound-slots/results.json"
    path.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
    print("PASS: exact DAC sequence, moving marker, input fixture, and negative controls.")
    print(
        "Instruction counts are not elapsed time. Audio, display, and physical input are unverified."
    )


if __name__ == "__main__":
    main()
