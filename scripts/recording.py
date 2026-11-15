"""Read what the instrumented XRoar recorded in one run: key steps, rendered frame and sound.

Pure decoding and checks only. The patch series in scripts/xroar_patches/ makes
XRoar write the raw files and log lines; nothing here makes pixels or samples.
"""

import re
import wave
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict


class RecordingError(ValueError):
    """The instrumented emulator's output is missing, incomplete or inconsistent."""


class Log(BaseModel):
    """The COCO_* lines one instrumented run wrote to its log."""

    model_config = ConfigDict(frozen=True)

    checkpoint_tick: int | None = None
    tick_rate: int | None = None
    video: tuple[int, int, int] | None = None
    audio_start: tuple[int, int, int] | None = None
    audio_buffers: tuple[int, ...] = ()
    key_steps: tuple[int, ...] = ()
    keys_ended: int | None = None


class Picture(BaseModel):
    """One frame from XRoar's software renderer: height x width x RGB, 8 bits each."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    path: Path
    pixels: np.ndarray


class Sound(BaseModel):
    """XRoar's mixer output from audio start, including ROM boot, up to the checkpoint.

    samples is a mono numpy int16 array at rate samples per second.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    path: Path
    rate: int
    samples: np.ndarray

    @property
    def seconds(self) -> float:
        return len(self.samples) / self.rate


def _numbers(text: str, name: str) -> list[tuple[int, ...]]:
    return [
        tuple(int(value) for value in match.split(","))
        for match in re.findall(rf"^{name},([\d,]+)$", text, re.MULTILINE)
    ]


def _single(text: str, name: str) -> tuple[int, ...] | None:
    found = _numbers(text, name)
    if len(found) > 1:
        raise RecordingError(f"The emulator log has {len(found)} {name} lines, expected one.")
    return found[0] if found else None


def parse_log(text: str) -> Log:
    if unknown := re.findall(r"^COCO_KEYS_UNKNOWN,(.*)$", text, re.MULTILINE):
        raise RecordingError(f"The instrumented XRoar does not know the key {unknown[0]!r}.")
    if size := re.findall(r"^COCO_VIDEO_TOO_LARGE,(\d+),(\d+)$", text, re.MULTILINE):
        raise RecordingError(f"The rendered frame {size[0][0]}x{size[0][1]} is too large.")
    checkpoint = _single(text, "COCO_CHECKPOINT")
    ended = _single(text, "COCO_KEYS_END")
    return Log(
        checkpoint_tick=checkpoint[0] if checkpoint else None,
        tick_rate=checkpoint[1] if checkpoint else None,
        video=_single(text, "COCO_VIDEO"),
        audio_start=_single(text, "COCO_AUDIO_START"),
        audio_buffers=tuple(tick for tick, *_ in _numbers(text, "COCO_AUDIO")),
        key_steps=tuple(tick for _, tick in _numbers(text, "COCO_KEYS")),
        keys_ended=ended[1] if ended else None,
    )


def require_checkpoint(log: Log) -> tuple[int, int]:
    if log.checkpoint_tick is None or not log.tick_rate:
        raise RecordingError("The emulator log does not record the checkpoint.")
    return log.checkpoint_tick, log.tick_rate


def decode_ppm(data: bytes) -> np.ndarray:
    """Binary PPM (P6, 8-bit) to a height x width x 3 array."""
    match = re.match(rb"P6\s+(\d+)\s+(\d+)\s+255\s", data)
    if not match:
        raise RecordingError("The rendered frame is not an 8-bit binary PPM.")
    width, height = int(match[1]), int(match[2])
    pixels = data[match.end() :]
    if len(pixels) != width * height * 3:
        raise RecordingError(
            f"The rendered frame holds {len(pixels)} bytes, expected {width * height * 3}."
        )
    return np.frombuffer(pixels, dtype=np.uint8).reshape(height, width, 3)


def rendered_frame(log: Log, data: bytes | None) -> np.ndarray:
    """The frame written after the checkpoint, checked against its log line."""
    checkpoint, _ = require_checkpoint(log)
    if data is None or log.video is None:
        raise RecordingError("XRoar rendered no complete frame after the checkpoint.")
    tick, width, height = log.video
    if tick <= checkpoint:
        raise RecordingError("The rendered frame was written before the checkpoint.")
    pixels = decode_ppm(data)
    if pixels.shape != (height, width, 3):
        raise RecordingError("The rendered frame's size differs from the emulator log.")
    return pixels


def frame_difference(expected: np.ndarray, actual: np.ndarray) -> str | None:
    """Describe the first differing renderer sample, or None when every sample matches."""
    if expected.shape != actual.shape:
        return f"expected a {_size(expected)} frame, XRoar rendered {_size(actual)}"
    wrong = np.argwhere(np.any(expected != actual, axis=2))
    if not len(wrong):
        return None
    y, x = (int(value) for value in wrong[0])
    return (
        f"{len(wrong)} of {actual.shape[0] * actual.shape[1]} rendered samples differ; "
        f"first at x={x}, y={y}: expected RGB {tuple(int(v) for v in expected[y, x])}, "
        f"found {tuple(int(v) for v in actual[y, x])}"
    )


def _size(pixels: np.ndarray) -> str:
    shape = pixels.shape
    return f"{shape[1]}x{shape[0]}" if pixels.ndim == 3 and shape[2] == 3 else f"{shape} array"


def sound_until_checkpoint(log: Log, raw: bytes) -> tuple[int, np.ndarray]:
    """Mixer samples from audio start to the checkpoint; every buffer must be present."""
    checkpoint, tick_rate = require_checkpoint(log)
    if log.audio_start is None:
        raise RecordingError("The emulator log does not record the start of audio capture.")
    start, rate, frames = log.audio_start
    if len(raw) != len(log.audio_buffers) * frames * 2:
        raise RecordingError("The captured audio does not match the buffers the mixer delivered.")
    slack = 2 * tick_rate / rate
    for number, tick in enumerate(log.audio_buffers, 1):
        if abs(tick - (start + number * frames * tick_rate / rate)) > slack:
            raise RecordingError(f"Audio buffer {number} is out of time; samples are missing.")
    needed = round((checkpoint - start) * rate / tick_rate)
    samples = np.frombuffer(raw, dtype="<i2")
    if len(samples) < needed:
        raise RecordingError("The captured audio stops before the checkpoint.")
    return rate, samples[:needed].astype(np.int16)


def keys_before_checkpoint(log: Log) -> int:
    checkpoint, _ = require_checkpoint(log)
    return sum(1 for tick in log.key_steps if tick <= checkpoint)


def parse_key_script(text: str, letters: dict[str, str]) -> tuple[tuple[str, ...], ...]:
    """One step per line: its first word lists the held keys' letters, or '-' for none.

    Blank lines and lines starting with '#' are skipped; later words are ignored,
    so a script can carry the project's own expected outcomes beside each step.
    """
    steps = []
    for number, line in enumerate(text.splitlines(), 1):
        words = line.split()
        if not words or line.startswith("#"):
            continue
        held = words[0]
        unknown = sorted(set(held) - set(letters))
        if held != "-" and unknown:
            raise ValueError(
                f"Key script line {number}: {', '.join(unknown)} is not a declared letter; "
                f"[keys] letters declares {', '.join(letters)}."
            )
        steps.append(() if held == "-" else tuple(letters[c] for c in dict.fromkeys(held)))
    if not steps:
        raise ValueError("The key script has no steps.")
    return tuple(steps)


def key_lines(steps: tuple[tuple[str, ...], ...]) -> str:
    """The file the keyboard hook reads: XRoar key names held at each step."""
    return "".join(" ".join(step) + "\n" for step in steps)


def write_wav(path: Path, rate: int, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(samples.astype("<i2").tobytes())
