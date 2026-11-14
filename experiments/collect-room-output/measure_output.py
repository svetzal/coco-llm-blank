"""Independent output measurements for the bounded Collect room journey."""

from pathlib import Path

import numpy as np
from collect_room import expected_screen

TICKS = 14318180
RATE = 44100
FRAME_TICKS = 912 * 262
FRAME_BYTES = 512 * 192 * 3


def rows(log: str, name: str) -> list[list[int]]:
    return [
        list(map(int, line.split(",")[1:]))
        for line in log.splitlines()
        if line.startswith(name + ",")
    ]


def only(log: str, name: str) -> int:
    values = rows(log, name)
    if len(values) != 1 or len(values[0]) != 1:
        raise ValueError(f"Missing or duplicate {name}")
    return values[0][0]


def input_chronology(log: str, checkpoints: list, start: int, end: int, count: int) -> None:
    keys = rows(log, "KEY")
    if [r[0] for r in keys] != list(range(count)):
        raise ValueError("Keyboard injection sequence incomplete")
    for index, (key, checkpoint) in enumerate(zip(keys, checkpoints, strict=True)):
        following = keys[index + 1][2] if index + 1 < count else end
        if not start <= key[2] <= checkpoint[1] < following:
            raise ValueError("Input/checkpoint chronology invalid")


def timeline(raw: bytes, video_size: int, log: str, count: int) -> dict:
    start, end = only(log, "AUDIO_START"), only(log, "AUDIO_END")
    checkpoints = rows(log, "FRAME")
    if [r[0] for r in checkpoints] != list(range(count)):
        raise ValueError("Checkpoint sequence incomplete")
    input_chronology(log, checkpoints, start, end, count)
    first, last = checkpoints[0][1], checkpoints[-1][1]
    # Loader waits 2s; setup ~0.12s; 42 scans each delay >= 12000*8 cycles.
    if not (2.08 < (first - start) / TICKS < 2.2 and 4.5 < (last - first) / TICKS < 5.5):
        raise ValueError("Execution duration outside independent budget")
    if abs(end - last - TICKS * 0.05) > 256:
        raise ValueError("Completion tail missing")
    pcm = rows(log, "PCM")
    if not pcm or any(r[1] != 1024 for r in pcm) or len(raw) != len(pcm) * 2048:
        raise ValueError("PCM byte/callback count mismatch")
    for i, (tick, _) in enumerate(pcm, 1):
        if abs(tick - start - i * 1024 * TICKS / RATE) > 2 * TICKS / RATE:
            raise ValueError("PCM callback discontinuity")
    remainder = (end - start) * RATE / TICKS - len(raw) // 2
    if not -2 <= remainder < 1026:
        raise ValueError("PCM incomplete at shutdown")
    video = video_timeline(video_size, log, start, end)
    return {
        "start_tick": start,
        "end_tick": end,
        "first_checkpoint_tick": first,
        "final_checkpoint_tick": last,
        "duration_seconds": (end - start) / TICKS,
        "pcm_frames": len(raw) // 2,
        "pcm_callbacks": len(pcm),
        "pcm_unfinished_frames": remainder,
        "video_frames": len(video),
        "video_first_tick": video[0][1],
        "video_last_tick": video[-1][1],
    }


def video_timeline(video_size: int, log: str, start: int, end: int) -> list:
    video = rows(log, "VIDEO")
    if not video or video_size != len(video) * FRAME_BYTES:
        raise ValueError("Video byte/callback count mismatch")
    for i, (number, tick, width, height) in enumerate(video):
        if number != i or (width, height) != (512, 192):
            raise ValueError("Video frame sequence/dimensions differ")
        if i and tick - video[i - 1][1] != FRAME_TICKS:
            raise ValueError("Video callback discontinuity")
    if not (0 <= video[0][1] - start <= FRAME_TICKS and 0 <= end - video[-1][1] < FRAME_TICKS):
        raise ValueError("Video missing capture edge")
    return video


def video_measure(path: Path, log: str, cases: list) -> dict:
    frames = np.memmap(path, dtype=np.uint8, mode="r").reshape(-1, 192, 512, 3)
    checkpoints, video, keys = rows(log, "FRAME"), rows(log, "VIDEO"), rows(log, "KEY")
    matched = []
    for index, (_, state) in enumerate(cases):
        begin = checkpoints[index][1] + FRAME_TICKS
        end = keys[index + 1][2] if index + 1 < len(keys) else only(log, "AUDIO_END")
        eligible = [i for i, r in enumerate(video) if begin <= r[1] < end]
        if not eligible:
            raise ValueError(f"No complete stable rendered frame at checkpoint {index}")
        bits = np.unpackbits(np.frombuffer(expected_screen(state), dtype=np.uint8))
        bits = np.repeat(bits.reshape(192, 256), 2, axis=1)
        expected = np.where(bits[..., None], [46, 188, 36], [0, 31, 0])
        for frame in eligible:
            if not np.array_equal(frames[frame], expected):
                raise ValueError(f"Rendered scene differs at checkpoint {index}, frame {frame}")
        matched.append(len(eligible))
    return {
        "stable_frames_per_checkpoint": matched,
        "stable_frames_checked": sum(matched),
        "transitional_frames": "captured; not required to equal an atomic scene",
    }


def audio_measure(raw: bytes, log: str, cases: list) -> dict:
    audio = np.frombuffer(raw, dtype="<i2").astype(float) / 32768
    start = only(log, "AUDIO_START")
    keys, checkpoints = rows(log, "KEY"), rows(log, "FRAME")
    effects = []
    previous = 0
    for index, (_, state) in enumerate(cases):
        if state[6] == previous:
            continue
        previous = state[6]
        lo = int((keys[index][2] - start) * RATE / TICKS)
        hi = int((checkpoints[index][1] - start) * RATE / TICKS)
        signal = audio[lo:hi]
        # Remove the quiet post-effect redraw interval before spectral analysis.
        # A finite unipolar burst has an envelope/DC step; its full-window FFT
        # would report that envelope instead of the alternating signal.
        active = signal > signal[-1] + 0.1
        indices = np.flatnonzero(active)
        if len(indices) == 0:
            raise ValueError(f"PCM effect differs at {index}: no active samples")
        high_runs = int(np.count_nonzero(np.diff(np.r_[False, active].astype(int)) == 1))
        tone = signal[indices[0] : indices[-1] + 1]
        duration = len(tone) / RATE
        duration_low, duration_high = {1: (0.014, 0.018), 2: (0.007, 0.011), 3: (0.021, 0.025)}[
            state[7]
        ]
        if high_runs != 16 or not duration_low < duration < duration_high:
            raise ValueError(f"PCM effect differs at {index}: burst shape/duration")
        ac = tone - tone.mean()
        rms = float(np.sqrt(np.mean(ac**2)))
        # Short 16-cycle bursts: use a bounded spectral outcome, not an exact note.
        spectrum = np.abs(np.fft.rfft(ac, n=32768))
        hz = float(np.argmax(spectrum[1:]) + 1) * RATE / 32768
        low, high = {1: (900, 1100), 2: (1550, 1950), 3: (600, 800)}[state[7]]
        if not (0.02 < rms < 0.5 and low <= hz <= high):
            raise ValueError(f"PCM effect differs at {index}: rms={rms}, peak={hz}")
        effects.append(
            {
                "checkpoint": index,
                "kind": state[7],
                "rms": rms,
                "peak_hz": hz,
                "expected_hz": [low, high],
                "window_frames": len(signal),
                "tone_frames": len(tone),
                "high_runs": high_runs,
                "tone_seconds": duration,
            }
        )
    if len(effects) != 5:
        raise ValueError("Expected five lifecycle effects")
    # Quiet title interval avoids ROM boot; reject a permanently running tone.
    lo = int((checkpoints[0][1] - start) * RATE / TICKS) + 100
    hi = int((keys[4][2] - start) * RATE / TICKS) - 100
    quiet = audio[lo:hi]
    quiet_rms = float(np.std(quiet))
    if quiet_rms > 0.0001:
        raise ValueError("Title is not quiet")
    return {"effects": effects, "title_ac_rms": quiet_rms}
