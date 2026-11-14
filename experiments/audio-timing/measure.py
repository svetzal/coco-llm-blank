"""Reproduce the eleven bounded DAC timing cases; see guidance/techniques/validation/audio-timing.md."""

import argparse
import collections
import hashlib
import itertools
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from coco import load_expected
from native import tool_path
from roms import verify_installed

verify_frame = load_expected(ROOT / "examples/timer-sound").verify_frame

OUT = ROOT / "build/audio-timing-reproduction"
SRC = ROOT / "local/research/audio-timing-reproduction"
TICKS = 14318180


def build_case(name: str, lwasm: str, timer: bool, heavy: bool, slots: bool, control: str | None):
    source = ROOT / ("examples/sound-slots/main.asm" if slots else "examples/timer-sound/main.asm")
    text = source.read_text()
    if control == "nop":
        text = replace_once(text, "sample  sta $FF20", "        nop\nsample  sta $FF20")
    if control == "masked":
        text = replace_once(text, "redraw  sta ,x+", "        orcc #$40\nredraw  sta ,x+")
        text = replace_once(text, "        blo redraw", "        blo redraw\n        andcc #$BF")
    copied = SRC / f"{name}.asm"
    copied.write_text(text)
    binary, symfile = OUT / f"{name}.bin", OUT / f"{name}.sym"
    command = [lwasm, "--6809", "--format=decb", f"--output={binary}", f"--symbol-dump={symfile}"]
    command += [
        f"--define={flag}" for flag, enabled in [("TIMER", timer), ("HEAVY", heavy)] if enabled
    ]
    command.append(str(copied))
    (OUT / f"{name}.assemble.json").write_text(json.dumps(command, indent=2) + "\n")
    subprocess.run(command, check=True, timeout=40)
    syms = {
        k: int(v, 16)
        for k, v in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9a-fA-F]+)", symfile.read_text(), re.MULTILINE
        )
    }
    return text, binary, syms


def machine(slots: bool, revision: int):
    if slots:
        roms = verify_installed(ROOT, "coco1", ("bas11.rom", "extbas10.rom"))
        args = [
            "-machine",
            "cocous",
            "-ram",
            "32",
            "-bas",
            str(roms["bas11.rom"]),
            "-extbas",
            str(roms["extbas10.rom"]),
        ]
    else:
        roms = verify_installed(ROOT, "coco3", ("coco3.rom",))
        args = [
            "-machine",
            "coco3",
            "-ram",
            "128",
            "-vdg-type",
            f"gime{revision}",
            "-extbas",
            str(roms["coco3.rom"]),
        ]
    return roms, args


def run_case(
    name: str,
    xroar: Path,
    lwasm: str,
    timer=False,
    heavy=False,
    revision=1986,
    slots=False,
    control=None,
    ratelimit=False,
):
    text, binary, syms = build_case(name, lwasm, timer, heavy, slots, control)
    roms, args = machine(slots, revision)
    snap, negative = OUT / f"{name}.ram", OUT / f"{name}.unreachable.ram"
    snap.unlink(missing_ok=True)
    negative.unlink(missing_ok=True)
    args = (
        [str(xroar), "-c", "/dev/null"]
        + args
        + [
            "-tv-type",
            "ntsc",
            "-machine-cpu",
            "6809",
            "-no-cart",
            "-ui",
            "null",
            "-ao",
            "null",
            "-ram-init",
            "set",
            "-ratelimit" if ratelimit else "-no-ratelimit",
            "-timeout",
            "8",
            "-trap",
            f"pc=0x{syms['state']:x}",
            "-trap-snap",
            str(negative),
            "-trap",
            f"pc=0x{syms['sample']:x}",
            "-trap-range",
            "1-1",
            "-trap-timeout",
            "1",
            "-trap",
            f"pc=0x{syms['frame_ready']:x}",
            "-trap-range",
            "1-",
            "-trap-snap",
            str(snap),
            "-run",
            str(binary),
        ]
    )
    (OUT / f"{name}.command.json").write_text(json.dumps(args, indent=2))
    logfile = OUT / f"{name}.log"
    with logfile.open("w") as log:
        subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=40, check=True)
    result = analyze(logfile.read_text(), syms, snap, negative, slots)
    result.update(
        name=name,
        source_sha256=hashlib.sha256(text.encode()).hexdigest(),
        rom_sha256={k: digest(p) for k, p in roms.items()},
    )
    (OUT / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in result.items() if k not in ("histogram_ticks", "rom_sha256")}),
        flush=True,
    )
    return result


def records_from_log(log: str, sample: int) -> list[tuple[int, int]]:
    records = []
    for line in log.splitlines():
        if line.startswith("AT,"):
            _, tick, pc, value, cr, ddr = line.split(",")
            if int(pc, 16) == sample + 3:
                assert int(cr, 16) & 4 and int(ddr, 16) & 0xFC == 0xFC
                records.append((int(tick), int(value, 16)))
    assert len(records) > 256, ("missing samples", len(records))
    assert all(value & 0xFC == (i * 8) % 256 for i, (_, value) in enumerate(records, 1)), (
        "incorrect sample sequence"
    )
    return records


def analyze(log: str, syms: dict[str, int], snap: Path, negative: Path, slots: bool) -> dict:
    records = records_from_log(log, syms["sample"])
    gaps = [(b[0] - a[0]) & 0xFFFFFFFF for a, b in itertools.pairwise(records)]
    assert all(gap > 0 and gap % 16 == 0 for gap in gaps), "invalid tick intervals"
    assert not negative.exists(), "unreachable trap fired"
    assert snap.exists(), "missing completion snapshot"
    data = snap.read_bytes()
    if not slots:
        frames = verify_frame(data, syms)
    else:
        assert len(data) == 32768 and data[0x3FF] == data[0x1C00] == 0xA5
        frames = int.from_bytes(data[syms["frames"] : syms["frames"] + 2], "big")
        screen = bytearray(6144)
        screen[96 * 32 + frames % 32] = 255
        assert data[0x400:0x1C00] == screen
    histogram = dict(sorted(collections.Counter(gaps).items()))
    result = {
        "samples": len(records),
        "intervals": len(gaps),
        "frames": frames,
        "tick_rate": TICKS,
        "ticks_per_cpu_cycle": 16,
        "min_cycles": min(gaps) / 16,
        "max_cycles": max(gaps) / 16,
        "mean_cycles": sum(gaps) / len(gaps) / 16,
        "peak_to_peak_cycles": (max(gaps) - min(gaps)) / 16,
        "observed_span_ticks": sum(gaps),
        "span_seconds": sum(gaps) / TICKS,
        "span_samples_per_second": len(gaps) * TICKS / sum(gaps),
        "histogram_ticks": histogram,
    }
    return result


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Control requires exactly one source anchor: {old!r}")
    return text.replace(old, new)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--xroar",
        type=Path,
        required=True,
        help="Explicit path to the private instrumented XRoar 1.12.1 executable",
    )
    options = parser.parse_args()
    if not __debug__:
        parser.error("Validation requires assertions; do not use python -O or PYTHONOPTIMIZE")
    xroar = options.xroar.expanduser().resolve()
    if not xroar.is_file() or not os.access(xroar, os.X_OK):
        parser.error(f"Private emulator is not executable: {xroar}")
    lwasm = tool_path("lwasm")
    if not lwasm:
        parser.error("Missing lwasm; set LWASM or use the existing native toolchain")
    OUT.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").unlink(missing_ok=True)
    provenance = {
        "python": sys.version,
        "platform": platform.platform(),
        "argv": sys.argv,
        "xroar": str(xroar),
        "lwasm": lwasm,
        "versions": {
            name: subprocess.check_output(
                [str(path), "--version"], text=True, stderr=subprocess.STDOUT, timeout=10
            )
            for name, path in [("xroar", xroar), ("lwasm", lwasm)]
        },
        "sha256": {
            str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path): digest(path)
            for path in [
                Path(__file__).resolve(),
                xroar,
                Path(lwasm),
                ROOT / "uv.lock",
                ROOT / "examples/timer-sound/expected.py",
                ROOT / "scripts/roms.py",
                ROOT / "examples/sound-slots/main.asm",
                ROOT / "examples/timer-sound/main.asm",
            ]
        },
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    results = []
    for slots, timer, heavy, rev, name in [
        (True, False, False, 1986, "slots"),
        (False, False, False, 1986, "coop-light"),
        (False, False, True, 1986, "coop-heavy"),
        (False, True, False, 1986, "timer86-light"),
        (False, True, True, 1986, "timer86-heavy"),
        (False, True, False, 1987, "timer87-light"),
        (False, True, True, 1987, "timer87-heavy"),
    ]:
        results.append(run_case(name, xroar, lwasm, timer, heavy, rev, slots))
    results.append(run_case("coop-nop", xroar, lwasm, control="nop"))
    results.append(
        run_case("timer86-masked", xroar, lwasm, timer=True, heavy=True, control="masked")
    )
    results.append(run_case("timer86-heavy-repeat", xroar, lwasm, timer=True, heavy=True))
    results.append(
        run_case("timer86-heavy-realtime", xroar, lwasm, timer=True, heavy=True, ratelimit=True)
    )
    check_controls(results)
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")


def check_controls(results: list[dict]) -> None:
    assert results[7]["min_cycles"] == results[1]["min_cycles"] + 2
    assert results[7]["max_cycles"] == results[1]["max_cycles"] + 2
    assert results[8]["max_cycles"] > 100 * results[4]["max_cycles"]
    assert (
        results[4]["histogram_ticks"]
        == results[9]["histogram_ticks"]
        == results[10]["histogram_ticks"]
    )
    assert results[4]["samples"] == results[9]["samples"] == results[10]["samples"]
    assert results[4]["frames"] == results[9]["frames"] == results[10]["frames"]


if __name__ == "__main__":
    main()
