"""What the instrumented XRoar recorded is accepted only when it is complete and consistent."""

import wave
from pathlib import Path

import numpy as np
import pytest
import recording
from recording import Log, RecordingError

TICKS = 14318180
START = 1000
LETTERS = {"U": "up", "F": "space", "M": "m"}


def buffer_tick(number: int) -> int:
    return round(START + number * 1024 * TICKS / 44100)


def audio_log(checkpoint: int, buffers: int) -> Log:
    return Log(
        checkpoint_tick=checkpoint,
        tick_rate=TICKS,
        audio_start=(START, 44100, 1024),
        audio_buffers=tuple(buffer_tick(n) for n in range(1, buffers + 1)),
    )


def ppm(width: int, height: int, pixels: bytes | None = None) -> bytes:
    body = pixels if pixels is not None else bytes(range(width * height * 3))
    return f"P6\n{width} {height}\n255\n".encode() + body


class DescribeLog:
    def should_read_every_recorded_line(self) -> None:
        text = "\n".join(
            [
                "noise from XRoar",
                "COCO_AUDIO_START,7,44100,1024",
                "COCO_KEYS,0,10",
                "COCO_AUDIO,23000",
                "COCO_KEYS,1,20",
                f"COCO_CHECKPOINT,30,{TICKS}",
                "COCO_KEYS_END,2,40",
                "COCO_VIDEO,50,512,192",
            ]
        )

        log = recording.parse_log(text)

        assert log == Log(
            checkpoint_tick=30,
            tick_rate=TICKS,
            video=(50, 512, 192),
            audio_start=(7, 44100, 1024),
            audio_buffers=(23000,),
            key_steps=(10, 20),
            keys_ended=40,
        )
        assert recording.keys_before_checkpoint(log) == 2

    @pytest.mark.parametrize(
        "text,message",
        [
            ("COCO_CHECKPOINT,1,2\nCOCO_CHECKPOINT,3,4\n", "2 COCO_CHECKPOINT lines"),
            ("COCO_KEYS_UNKNOWN,spacebar\n", "does not know the key 'spacebar'"),
            ("COCO_VIDEO_TOO_LARGE,2000,900\n", "2000x900 is too large"),
            ("COCO_FRAMES_SIZE,640,240\n", "size changed to 640x240"),
        ],
    )
    def should_reject_inconsistent_logs(self, text: str, message: str) -> None:
        with pytest.raises(RecordingError, match=message):
            recording.parse_log(text)

    def should_require_the_checkpoint(self) -> None:
        with pytest.raises(RecordingError, match="does not record the checkpoint"):
            recording.keys_before_checkpoint(Log())


class DescribeRenderedFrame:
    def should_decode_the_frame_written_after_the_checkpoint(self) -> None:
        log = Log(checkpoint_tick=10, tick_rate=TICKS, video=(11, 2, 1))

        pixels = recording.rendered_frame(log, ppm(2, 1))

        assert pixels.shape == (1, 2, 3)
        assert pixels[0, 1].tolist() == [3, 4, 5]

    @pytest.mark.parametrize(
        "video,data,message",
        [
            (None, None, "rendered no complete frame"),
            ((9, 2, 1), ppm(2, 1), "written before the checkpoint"),
            ((11, 3, 1), ppm(2, 1), "size differs"),
            ((11, 2, 1), ppm(2, 1, b"\0" * 5), "holds 5 bytes, expected 6"),
            ((11, 2, 1), b"P3\n2 1\n255\n", "not an 8-bit binary PPM"),
        ],
    )
    def should_reject_missing_early_or_damaged_frames(self, video, data, message: str) -> None:
        log = Log(checkpoint_tick=10, tick_rate=TICKS, video=video)

        with pytest.raises(RecordingError, match=message):
            recording.rendered_frame(log, data)

    def should_describe_the_first_differing_sample(self) -> None:
        expected = np.zeros((2, 3, 3), dtype=np.uint8)
        actual = expected.copy()
        actual[1, 2] = (46, 188, 36)
        actual[1, 0] = (1, 2, 3)

        assert recording.frame_difference(expected, expected.copy()) is None
        assert recording.frame_difference(expected, actual) == (
            "2 of 6 rendered samples differ; first at x=0, y=1: "
            "expected RGB (0, 0, 0), found (1, 2, 3)"
        )

    @pytest.mark.parametrize("shape,size", [((2, 4, 3), "4x2"), ((6,), "(6,) array")])
    def should_report_a_frame_of_another_size(self, shape: tuple, size: str) -> None:
        actual = np.zeros((2, 3, 3), dtype=np.uint8)

        difference = recording.frame_difference(np.zeros(shape, dtype=np.uint8), actual)

        assert difference == f"expected a {size} frame, XRoar rendered 3x2"


class DescribeSound:
    def should_keep_samples_from_audio_start_to_the_checkpoint(self) -> None:
        raw = np.arange(3 * 1024, dtype="<i2").tobytes()
        checkpoint = START + round(2500 * TICKS / 44100)

        rate, samples = recording.sound_until_checkpoint(audio_log(checkpoint, 3), raw)

        assert rate == 44100
        assert samples.tolist() == list(range(2500))

    def should_reject_audio_with_a_missing_buffer(self) -> None:
        log = audio_log(START + TICKS // 10, 3)
        late = log.model_copy(
            update={"audio_buffers": (*log.audio_buffers[:1], log.audio_buffers[2])}
        )

        with pytest.raises(RecordingError, match="Audio buffer 2 is out of time"):
            recording.sound_until_checkpoint(late, bytes(2 * 1024 * 2))

    @pytest.mark.parametrize(
        "log,raw,message",
        [
            (Log(checkpoint_tick=1, tick_rate=TICKS), b"", "start of audio capture"),
            (audio_log(START + 100, 2), bytes(1024 * 2), "does not match the buffers"),
            (audio_log(START + TICKS, 1), bytes(1024 * 2), "stops before the checkpoint"),
        ],
    )
    def should_reject_incomplete_audio(self, log: Log, raw: bytes, message: str) -> None:
        with pytest.raises(RecordingError, match=message):
            recording.sound_until_checkpoint(log, raw)

    def should_write_a_mono_sixteen_bit_wav(self, tmp_path: Path) -> None:
        path = tmp_path / "out.wav"
        samples = np.array([0, -32768, 32767, 5], dtype=np.int16)

        recording.write_wav(path, 44100, samples)

        with wave.open(str(path)) as result:
            assert (result.getnchannels(), result.getsampwidth()) == (1, 2)
            assert result.getframerate() == 44100
            assert np.frombuffer(result.readframes(4), dtype="<i2").tolist() == samples.tolist()

    def should_report_duration(self, tmp_path: Path) -> None:
        sound = recording.Sound(path=tmp_path, rate=4, samples=np.zeros(6, dtype=np.int16))

        assert sound.seconds == 1.5


FIELD = 238944  # ticks in one NTSC field: 14318180 / 59.9227


def stream_log(ticks: tuple[int, ...], audio: int = 0) -> Log:
    return Log(
        frames_start=(ticks[0], TICKS, 512, 192),
        frame_ticks=ticks,
        audio_start=(audio, 44100, 1024),
    )


class DescribeFrameStream:
    def should_read_the_stream_lines(self) -> None:
        text = f"COCO_FRAMES_START,{FIELD},{TICKS},512,192\nCOCO_FRAME,{FIELD}\nCOCO_FRAME,9\n"

        log = recording.parse_log(text)

        assert log.frames_start == (FIELD, TICKS, 512, 192)
        assert log.frame_ticks == (FIELD, 9)

    def should_continue_ticks_across_each_32_bit_wrap(self) -> None:
        wrap = recording.TICK_WRAP

        assert recording.unwrap((wrap - 10, 5, 20, 3), after=wrap - 20) == (
            wrap - 10,
            wrap + 5,
            wrap + 20,
            2 * wrap + 3,
        )

    def should_time_frames_with_the_emulator_clock(self) -> None:
        ticks = tuple(FIELD * n for n in range(1, 601))

        timing = recording.frame_timing(stream_log(ticks))

        assert timing.frames == 600
        assert timing.rate == pytest.approx(59.923, abs=0.001)
        assert timing.offset == 0
        assert (timing.width, timing.height) == (512, 192)

    def should_measure_the_offset_from_the_start_of_audio(self) -> None:
        ticks = tuple(FIELD * n for n in range(3, 6))

        timing = recording.frame_timing(stream_log(ticks, audio=FIELD))

        assert timing.offset == pytest.approx(FIELD / TICKS)

    def should_time_a_recording_longer_than_one_tick_wrap(self) -> None:
        ticks = tuple(FIELD * n % recording.TICK_WRAP for n in range(1, 20001))

        assert recording.frame_timing(stream_log(ticks)).rate == pytest.approx(59.923, abs=0.001)

    @pytest.mark.parametrize(
        "ticks,message",
        [
            ((FIELD,), "fewer than two frames"),
            ((FIELD, 2 * FIELD, 4 * FIELD, 5 * FIELD), "skipped frames"),
        ],
    )
    def should_reject_a_stream_it_cannot_time(self, ticks: tuple[int, ...], message: str) -> None:
        with pytest.raises(RecordingError, match=message):
            recording.frame_timing(stream_log(ticks))

    def should_keep_every_complete_audio_buffer(self) -> None:
        log = audio_log(START, 3).model_copy(update={"frames_start": (FIELD, TICKS, 512, 192)})

        rate, samples = recording.whole_sound(log, np.arange(3 * 1024, dtype="<i2").tobytes())

        assert rate == 44100
        assert samples.tolist() == list(range(3 * 1024))

    @pytest.mark.parametrize(
        "log,message",
        [
            (Log(audio_start=(0, 44100, 1024)), "start of the frame stream"),
            (Log(frames_start=(FIELD, TICKS, 512, 192)), "start of audio capture"),
        ],
    )
    def should_require_both_streams_for_the_sound(self, log: Log, message: str) -> None:
        with pytest.raises(RecordingError, match=message):
            recording.whole_sound(log, b"")


class DescribeKeyScript:
    def should_read_the_first_word_of_each_step(self) -> None:
        script = "# keys  outcome\nF 0 0\n\n-    1 2\nUFU trailing words\nM\n"

        steps = recording.parse_key_script(script, LETTERS)

        assert steps == (("space",), (), ("up", "space"), ("m",))
        assert recording.key_lines(steps) == "space\n\nup space\nm\n"

    @pytest.mark.parametrize(
        "script,message",
        [
            ("F\nX 1\n", "line 2: X is not a declared letter"),
            ("-F\n", "line 1: - is not a declared letter"),
            ("# only comments\n\n", "has no steps"),
        ],
    )
    def should_reject_scripts_it_cannot_play(self, script: str, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            recording.parse_key_script(script, LETTERS)
