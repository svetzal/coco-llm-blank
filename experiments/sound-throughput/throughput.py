"""Measure DAC throughput in one emulated second for the two sound examples.

This moved from the sound-slots and timer-sound runners. The examples' memory
checks run with scripts/coco.py; this harness adds the timing claims: samples
in one emulated second, redraw load, and the GIME revision predictions.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from coco import Host, build, emulator, load_expected, load_project

SOUND_SLOTS = ROOT / "examples/sound-slots"
TIMER_SOUND = ROOT / "examples/timer-sound"
OUTPUT = ROOT / "build/sound-throughput"
# Revision, inclusive sample bounds predicted for one emulated second of timer sound.
TIMER_PREDICTIONS = ((1986, 6990, 6994), (1987, 7004, 7008))


def window_options(symbols: dict[str, int], snapshot: Path, unreachable: bool) -> list[str]:
    """Stop one emulated second after the first sample; keep the last completed frame."""
    options = ["-ui", "null", "-ao", "null", "-ram-init", "set", "-no-ratelimit"]
    options += ["-timeout", "10"]
    if unreachable:
        options += ["-trap", f"pc=0x{symbols['state']:x}", "-trap-snap", str(snapshot) + ".bad"]
    options += ["-trap", f"pc=0x{symbols['sample']:x}", "-trap-range", "1-1"]
    options += ["-trap-timeout", "1", "-trap-trace"]
    options += ["-trap", f"pc=0x{symbols['frame_ready']:x}", "-trap-range", "1-"]
    return options + ["-trap-snap", str(snapshot)]


def sample_count(trace: str, address: int) -> int:
    """Count traced DAC writes, requiring the phase sequence of $0800 steps."""
    values = [
        int(a, 16) & 0xFC
        for a in re.findall(rf"^{address:04x}\|.*?\ba=([0-9a-f]{{2}})\b", trace, re.MULTILINE)
    ]
    if not values or any(value != (i * 8) % 256 for i, value in enumerate(values, 1)):
        raise ValueError("Missing or incorrect DAC sample sequence.")
    return len(values)


def one_second(directory: Path, host: Host, target: str | None, variant: str, defines=()):
    """Run one emulated second; return the last completed snapshot, trace and symbols."""
    project = load_project(directory)
    built = build(project, host, variant, defines)
    stem = OUTPUT / f"{project.name}-{built.binary.stem}-{target or project.default_target}"
    stem.parent.mkdir(parents=True, exist_ok=True)
    snapshot, trace = stem.with_suffix(".ram"), stem.with_suffix(".trace")
    unreachable = Path(str(snapshot) + ".bad")
    for path in (snapshot, unreachable):
        path.unlink(missing_ok=True)
    command = emulator(project, host, target)
    command += window_options(built.symbols, snapshot, True) + ["-run", str(built.binary)]
    host.run(command, trace, timeout=30)
    if unreachable.exists() or not snapshot.exists():
        raise ValueError("No completed frame or an unreachable checkpoint fired.")
    return snapshot.read_bytes(), trace.read_text(), built.symbols


def sound_slots_second(host: Host) -> dict[str, int]:
    """Bound throughput using the last complete frame in one emulated second."""
    data, _, symbols = one_second(SOUND_SLOTS, host, None, "")
    frame = int.from_bytes(data[symbols["frames"] : symbols["frames"] + 2], "big")
    if not 1 <= frame < 255:
        raise ValueError("One-second experiment did not produce a bounded frame count.")
    load_expected(SOUND_SLOTS).verify_ram(data, symbols, frame, "")
    return {
        "complete_frames_in_one_emulated_second": frame,
        "minimum_samples_per_second": frame * 256,
        "maximum_samples_per_second": (frame + 1) * 256,
    }


def timer_second(
    host: Host, timer: bool, heavy: bool, revision: int, no_ack: bool = False
) -> dict[str, int]:
    variant = "-".join(name for name, on in (("timer", timer), ("heavy", heavy)) if on)
    defines = ("NO_ACK",) if no_ack else ()
    data, trace, symbols = one_second(TIMER_SOUND, host, f"coco3-{revision}", variant, defines)
    frames = load_expected(TIMER_SOUND).verify_frame(data, symbols)
    samples = sample_count(trace, symbols["sample"])
    return {"samples_in_one_emulated_second": samples, "completed_redraws": frames}


def compare(results: dict[str, dict[str, int]]) -> None:
    for revision, minimum, maximum in TIMER_PREDICTIONS:
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


def check(host: Host) -> dict[str, object]:
    results: dict[str, dict[str, int]] = {}
    for timer, revisions in ((False, (1986,)), (True, (1986, 1987))):
        for revision in revisions:
            for heavy in (False, True):
                kind = f"{'timer' if timer else 'cooperative'}-{'heavy' if heavy else 'light'}"
                results[f"{kind}-{revision}"] = timer_second(host, timer, heavy, revision)
    compare(results)
    try:
        timer_second(host, True, False, 1986, no_ack=True)
    except ValueError as error:
        if "No completed frame" not in str(error):
            raise
        no_ack = "rejected: no completed frame"
    else:
        raise ValueError("A timer build without the GIME acknowledgement still completed.")
    report = {
        "sound_slots": sound_slots_second(host),
        "timer_sound": results,
        "timer_without_acknowledgement": no_ack,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main(argv: list[str] | None = None, host: Host | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check",))
    parser.parse_args(argv)
    print(json.dumps(check(host or Host()), indent=2))
    print("PASS: one-second throughput and timer predictions on both GIME revisions.")
    print("Average throughput is not sample jitter, audible quality or elapsed time.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
