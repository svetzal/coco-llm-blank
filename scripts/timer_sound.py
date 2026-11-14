"""Compare cooperative and GIME timer sound under light and heavy redraw loads."""

import argparse
import json
import re
import subprocess
from pathlib import Path

from first_screen import executable
from native import ROOT

# Executive pages $38-$3F occupy the upper 64 KiB of this 128 KiB machine.
RAM_BASE = 0x10000


def build(timer: bool, heavy: bool, no_ack: bool = False) -> tuple[Path, dict[str, int]]:
    output = ROOT / "build/timer-sound"
    output.mkdir(parents=True, exist_ok=True)
    name = f"{'timer' if timer else 'cooperative'}-{'heavy' if heavy else 'light'}"
    if no_ack:
        name += "-no-ack"
    binary = output / f"{name}.bin"
    symbols = output / f"{name}.sym"
    flags = [
        flag
        for flag, enabled in (("TIMER", timer), ("HEAVY", heavy), ("NO_ACK", no_ack))
        if enabled
    ]
    subprocess.run(
        [
            executable("lwasm"),
            "--6809",
            "--format=decb",
            f"--output={binary}",
            f"--symbol-dump={symbols}",
        ]
        + [f"--define={flag}" for flag in flags]
        + [str(ROOT / "examples/timer-sound/main.asm")],
        check=True,
    )
    return binary, {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE
        )
    }


def emulator(revision: int) -> list[str]:
    rom = ROOT / "local/roms/coco3/coco3.rom"
    if not rom.exists():
        raise ValueError(
            "Missing CoCo 3 firmware; provision it with setup.py --target coco3 --roms-only."
        )
    return [
        executable("xroar"),
        "-machine",
        "coco3",
        "-machine-cpu",
        "6809",
        "-ram",
        "128",
        "-vdg-type",
        f"gime{revision}",
        "-extbas",
        str(rom),
        "-no-cart",
    ]


def verify_frame(data: bytes, symbols: dict[str, int]) -> int:
    if len(data) != 131072:
        raise ValueError("Expected a complete 128 KiB RAM snapshot.")
    ram = data[RAM_BASE:]

    def word(name: str) -> int:
        return int.from_bytes(ram[symbols[name] : symbols[name] + 2], "big")

    frames, samples = word("frames"), word("samples")
    if not frames or samples < 256 or word("phase") != (samples * 0x0800) % 65536:
        raise ValueError("Frame/audio state is inconsistent.")
    if ram[0x3FF] != 0xA5 or ram[0x1C00] != 0xA5:
        raise ValueError("Framebuffer guards were damaged.")
    screen = bytearray(6144)
    screen[96 * 32 + frames % 32] = 0xFF
    if ram[0x400:0x1C00] != screen or ram[symbols["position"]] != frames % 32:
        raise ValueError("Completed redraw differs from the marker specification.")
    return frames


def sample_count(trace: str, address: int) -> int:
    values = [
        int(a, 16) & 0xFC
        for a in re.findall(rf"^{address:04x}\|.*?\ba=([0-9a-f]{{2}})\b", trace, re.MULTILINE)
    ]
    if not values or any(value != (i * 8) % 256 for i, value in enumerate(values, 1)):
        raise ValueError("Missing or incorrect DAC sample sequence.")
    return len(values)


def measure(timer: bool, heavy: bool, revision: int, no_ack: bool = False) -> dict[str, int]:
    binary, symbols = build(timer, heavy, no_ack)
    stem = binary.with_name(f"{binary.stem}-{revision}")
    snapshot = stem.with_suffix(".ram")
    negative = stem.with_suffix(".unreachable.ram")
    snapshot.unlink(missing_ok=True)
    negative.unlink(missing_ok=True)
    command = emulator(revision) + [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "8",
        "-trap",
        f"pc=0x{symbols['state']:x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['sample']:x}",
        "-trap-range",
        "1-1",
        "-trap-timeout",
        "1",
        "-trap-trace",
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        "1-",
        "-trap-snap",
        str(snapshot),
        "-run",
        str(binary),
    ]
    trace_path = stem.with_suffix(".trace")
    with trace_path.open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
    if negative.exists() or not snapshot.exists():
        raise ValueError("No completed frame or an unreachable checkpoint fired.")
    frames = verify_frame(snapshot.read_bytes(), symbols)
    samples = sample_count(trace_path.read_text(), symbols["sample"])
    return {"samples_in_one_emulated_second": samples, "completed_redraws": frames}


def compare(results: dict[str, dict[str, int]]) -> None:
    for revision, minimum, maximum in ((1986, 6990, 6994), (1987, 7004, 7008)):
        light = results[f"timer-light-{revision}"]
        heavy = results[f"timer-heavy-{revision}"]
        for result in (light, heavy):
            if not minimum <= result["samples_in_one_emulated_second"] <= maximum:
                raise ValueError("Timer throughput differs from the revision-specific prediction.")
        if heavy["completed_redraws"] >= light["completed_redraws"]:
            raise ValueError("The heavy renderer did not exercise the foreground budget.")
    light = results["cooperative-light-1986"]["samples_in_one_emulated_second"]
    heavy = results["cooperative-heavy-1986"]["samples_in_one_emulated_second"]
    if heavy >= light // 2:
        raise ValueError("The cooperative load comparison did not expose blocking redraw work.")


def check() -> dict[str, dict[str, int]]:
    results = {}
    for timer, revisions in ((False, (1986,)), (True, (1986, 1987))):
        for revision in revisions:
            for heavy in (False, True):
                name = f"{'timer' if timer else 'cooperative'}-{'heavy' if heavy else 'light'}-{revision}"
                results[name] = measure(timer, heavy, revision)
    compare(results)
    path = ROOT / "build/timer-sound/results.json"
    path.write_text(json.dumps(results, indent=2) + "\n")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "run"))
    parser.add_argument("--revision", type=int, choices=(1986, 1987), default=1986)
    parser.add_argument("--heavy", action="store_true")
    args = parser.parse_args()
    if args.action == "run":
        binary, _ = build(True, args.heavy)
        subprocess.run(emulator(args.revision) + ["-ratelimit", "-run", str(binary)], check=True)
    else:
        print(json.dumps(check(), indent=2))
        print("PASS: timer throughput survived redraw load on both emulated GIME revisions.")
        print("Average throughput is not a measurement of sample jitter or audible quality.")


if __name__ == "__main__":
    main()
