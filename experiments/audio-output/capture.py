"""Capture actual XRoar mixer output for bounded original sound programs."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from build_capture import verify_build

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from coco import load_expected
from native import tool_path
from roms import verify_installed

ORACLE = ROOT / "examples/sound-slots/expected.py"
SOUND_SLOTS = load_expected(ORACLE.parent)

RATE = 44100
TICK_RATE = 14318180
FRAGMENT = 1024
# sound.c rounds frame conversion; allow two sample periods at callback dispatch.
TICK_SLOP = 2 * TICK_RATE / RATE


def timing(raw: bytes, log: str) -> dict:
    """Validate full capture coverage against independent emulator checkpoints."""

    def marker(name: str) -> int:
        values = re.findall(rf"^{name},(\d+)$", log, re.MULTILINE)
        if len(values) != 1:
            raise ValueError(f"Missing or duplicate {name}")
        return int(values[0])

    start, end = marker("AUDIO_START"), marker("AUDIO_END")
    points = re.findall(r"^CHECKPOINT,(\d+),(.+)$", log, re.MULTILINE)
    if [Path(path).name for _, path in points] != ["start.ram", "final.ram"]:
        raise ValueError("Missing or invalid execution checkpoints")
    first, complete = [int(tick) for tick, _ in points]
    # Loader waits 2 seconds; clearing 6144 bytes costs ~0.09 s.
    # 16384 samples * 57 cycles / 894886.25 Hz = 1.044 s,
    # plus bounded foreground work and constant-control LDA overhead (~0.037 s).
    if not (
        2.08 <= (first - start) / TICK_RATE <= 2.12
        and 1.04 <= (complete - first) / TICK_RATE <= 1.10
    ):
        raise ValueError("Independent execution duration bounds failed")
    if not 0 <= end - complete <= 256:
        raise ValueError("Audio end is not aligned with completion checkpoint")
    ticks = [int(t) for t in re.findall(r"^PCM,(\d+),1024$", log, re.MULTILINE)]
    if not ticks or len(ticks) * FRAGMENT * 2 != len(raw):
        raise ValueError("PCM callback provenance mismatch")
    for index, tick in enumerate(ticks, 1):
        expected = start + index * FRAGMENT * TICK_RATE / RATE
        if abs(tick - expected) > TICK_SLOP:
            raise ValueError("PCM callback continuity failed")
    # Allow only the unfinished fragment at shutdown, plus conversion rounding.
    remaining = (complete - start) * RATE / TICK_RATE - len(raw) // 2
    if not -2 <= remaining < FRAGMENT + 2 or ticks[-1] > complete + TICK_SLOP:
        raise ValueError("PCM duration does not reach completion checkpoint")
    return {
        "audio_start_tick": start,
        "audio_end_tick": end,
        "first_sample_tick": first,
        "completion_tick": complete,
        "callback_first_tick": ticks[0],
        "callback_last_tick": ticks[-1],
        "uncaptured_frames_at_completion": remaining,
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(raw: bytes, expected_hz: float | None, log: str) -> dict:
    if len(raw) < RATE * 2 or len(raw) % 2048:
        raise ValueError("Missing/truncated complete audio fragments")
    timeline = timing(raw, log)
    # Last 150 ms is wholly inside the final stable pitch block, excludes boot.
    tail = np.frombuffer(raw, dtype="<i2")[-6615:].astype(float) / 32768
    ac = tail - tail.mean()
    rms = float(np.sqrt(np.mean(ac**2)))
    spectrum = np.abs(np.fft.rfft(ac * np.hanning(len(ac))))
    peak = int(np.argmax(spectrum[1:]) + 1)
    hz = peak * RATE / len(ac)
    if expected_hz is None:
        if rms > 0.0001:
            raise ValueError("Control has unexpected alternating signal")
    elif rms < 0.01 or abs(hz - expected_hz) > 15:
        raise ValueError(f"Missing tone or wrong pitch: rms={rms}, hz={hz}")
    return {
        **timeline,
        "ac_rms_full_scale": rms,
        "peak_hz": hz if rms > 0.0001 else None,
        "dc_mean_full_scale": float(tail.mean()),
        "expected_hz": expected_hz,
        "frames": len(raw) // 2,
        "tail_frames": len(tail),
    }


def run_case(xroar: Path, output: Path, target: str, mode: str) -> dict:
    provenance = verify_build(xroar)
    output.mkdir(parents=True, exist_ok=False)
    source = ROOT / (
        "examples/sound-slots/main.asm" if target == "coco1" else "experiments/sound-coco2/main.asm"
    )
    text = source.read_text()
    if mode == "muted":
        text = text.replace(
            "        ora #8\n        sta $FF23", "        anda #$F7\n        sta $FF23"
        )
    if mode == "constant":
        text = text.replace("sample  sta $FF20", "        lda #$80\nsample  sta $FF20")
    asm, binary, symbols = [output / name for name in ("main.asm", "main.bin", "main.sym")]
    asm.write_text(text)
    build = [
        tool_path("lwasm"),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
    ]
    if mode == "scripted":
        build += ["--define=SCRIPTED"]
    build += [str(asm)]
    subprocess.run(build, check=True, timeout=30)
    syms = {
        k: int(v, 16)
        for k, v in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9a-fA-F]+)", symbols.read_text(), re.MULTILINE
        )
    }
    names = ("bas11.rom", "extbas10.rom") if target == "coco1" else ("bas12.rom", "extbas11.rom")
    roms = verify_installed(ROOT, target, names)
    command = [
        str(xroar),
        "-c",
        "/dev/null",
        "-machine",
        "cocous",
        "-ram",
        "32" if target == "coco1" else "64",
        "-tv-type",
        "ntsc",
        "-vdg-type",
        "6847",
        "-machine-cpu",
        "6809",
        "-bas",
        str(roms[names[0]]),
        "-extbas",
        str(roms[names[1]]),
        "-no-cart",
        "-ui",
        "null",
        "-ao",
        "null",
        "-ao-gain",
        "-3",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "20",
        "-trap",
        f"pc=0x{syms['state']:x}",
        "-trap-snap",
        str(output / "negative.ram"),
        "-trap",
        f"pc=0x{syms['sample']:x}",
        "-trap-range",
        "1-1",
        "-trap-snap",
        str(output / "start.ram"),
        "-trap",
        f"pc=0x{syms['frame_ready']:x}",
        "-trap-range",
        "64",
        "-trap-snap",
        str(output / "final.ram"),
        "-trap-timeout",
        "0",
        "-run",
        str(binary),
    ]
    contract = {
        "command": command,
        "assemble": build,
        "target": target,
        "mode": mode,
        "rom_sha256": {k: digest(v) for k, v in roms.items()},
        "xroar_sha256": digest(xroar),
        "original_assembly_sha256": digest(source),
        "assembly_sha256": digest(asm),
        "runner_sha256": digest(Path(__file__)),
        "instrumentation_sha256": digest(Path(__file__).with_name("instrument.py")),
        "verified_build": provenance,
        "ram_oracle_sha256": digest(ORACLE),
        "gain_db": -3,
        "rate": RATE,
        "format": "S16_LE mono",
        "fragment_frames": 1024,
    }
    (output / "contract.json").write_text(json.dumps(contract, indent=2))
    env = dict(os.environ, AUDIO_CAPTURE=str(output / "output.pcm"))
    with (output / "xroar.log").open("w") as log:
        subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=40
        )
    if (output / "negative.ram").exists():
        raise ValueError("Unreachable trap fired")
    ram = (output / "final.ram").read_bytes()
    if len(ram) != (32768 if target == "coco1" else 65536):
        raise ValueError("RAM size mismatch")
    SOUND_SLOTS.verify_ram(ram[:32768], syms, 64, "scripted" if mode == "scripted" else "")
    raw = (output / "output.pcm").read_bytes()
    # 32 phase steps per low-pitch cycle; 16 at doubled pitch. Inner loop
    # costs 57 slow cycles, plus amortized foreground work. Independent of PCM.
    expected = None if mode in ("constant", "muted") else (976 if mode == "scripted" else 488)
    result = analyze(raw, expected, (output / "xroar.log").read_text())
    with wave.open(str(output / "output.wav"), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(raw)
    result.update(
        wav_sha256=digest(output / "output.wav"),
    )
    (output / "result.json").write_text(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xroar", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not __debug__:
        parser.error("RAM oracle requires assertions enabled")
    results = {
        f"{target}-{mode}": run_case(
            args.xroar.resolve(), args.output.resolve() / f"{target}-{mode}", target, mode
        )
        for target in ("coco1", "coco2")
        for mode in ("released", "scripted", "muted", "constant")
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
