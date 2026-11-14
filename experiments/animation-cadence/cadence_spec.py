"""Real capture controls and corrupt-evidence rejection."""

import copy
import json
import sys

import cadence
import numpy as np
import pytest


@pytest.fixture(scope="module")
def scenes():
    return [cadence.expected_screen(i) for i in range(1, 65)]


def rgb(screen):
    pixels = np.unpackbits(np.frombuffer(screen, np.uint8)).reshape(192, 256)
    palette = np.array([(0, 31, 0), (46, 188, 36)], dtype=np.uint8)
    return np.repeat(palette[pixels], 2, axis=1).tobytes()


class DescribeCadence:
    def should_measure_real_consecutive_video_and_workload(self, reproduction):
        _, _, report = reproduction
        cadence.require_controls(report["cases"])
        assert report["passed"]
        assert report["cases"]["normal"]["source_sha256"] == cadence.digest(
            cadence.ROOT / "examples/moving-objects/main.asm"
        )

    def should_reject_real_frozen_program(self, reproduction, tmp_path):
        work, _, _ = reproduction
        source = (cadence.ROOT / "examples/moving-objects/main.asm").read_text()
        source = cadence.replace_once(
            source, "frame_ready\n*", "frame_ready\n        bra frame_ready\n*"
        )
        with pytest.raises(ValueError, match="animation did not change"):
            cadence.run_case("frozen", source, work / "xroar-1.12.1/src/xroar", tmp_path, tmp_path)

    def should_reject_missing_renderer_instrumentation(self, reproduction, tmp_path):
        source = (cadence.ROOT / "examples/moving-objects/main.asm").read_text()
        xroar = cadence.tool_path("xroar", cadence.ROOT)
        with pytest.raises(FileNotFoundError):
            cadence.run_case("uncaptured", source, xroar, tmp_path, tmp_path)
        assert (tmp_path / "uncaptured.ram").exists()

    def should_reanalyze_real_evidence(self, reproduction, scenes):
        _, out, report = reproduction
        measured = cadence.analyze(cadence.records(out / "normal.frames"), scenes)
        assert json.loads(json.dumps(measured)) == report["cases"]["normal"]["measurement"]

    @pytest.mark.parametrize("mutation", ["truncate", "sequence", "viewport", "empty"])
    def should_reject_broken_capture(self, reproduction, tmp_path, mutation):
        _, out, _ = reproduction
        data = (out / "normal.frames").read_bytes()
        if mutation == "truncate":
            data = data[:-1]
        elif mutation == "sequence":
            data = b"2" + data[1:]
        elif mutation == "viewport":
            data = data.replace(b"512 192", b"511 192", 1)
        else:
            data = b""
        path = tmp_path / "bad.frames"
        path.write_bytes(data)
        with pytest.raises(ValueError):
            cadence.records(path)

    @pytest.mark.parametrize(
        "mutation", ["no_first", "short", "skip", "frozen", "palette", "pairs"]
    )
    def should_reject_false_cadence(self, scenes, mutation):
        frames = [(i * 238944, rgb(scenes[(i // 10) % 2])) for i in range(180)]
        if mutation == "no_first":
            frames = [(tick, rgb(scenes[1])) for tick, _ in frames]
        elif mutation == "short":
            frames = frames[:149]
        elif mutation == "skip":
            frames[10] = (frames[10][0] + 238944, frames[10][1])
        elif mutation == "frozen":
            frames = [(tick, rgb(scenes[0])) for tick, _ in frames]
        else:
            bad = bytearray(frames[10][1])
            bad[:3] = b"\x01\x02\x03" if mutation == "palette" else b"\x2e\xbc\x24"
            frames[10] = (frames[10][0], bytes(bad))
        with pytest.raises(ValueError):
            cadence.analyze(frames, scenes)

    def should_identify_rows_from_two_states_independently(self):
        old, new = bytes(6144), bytes([255]) * 6144
        split = old[: 32 * 100] + new[32 * 100 :]
        proof = cadence.row_mixture(split, [old, new])
        assert proof == {
            "scenes": [1, 2],
            "old_only_rows": list(range(100)),
            "new_only_rows": list(range(100, 192)),
        }
        assert cadence.row_mixture(old, [old, new]) is None

    @pytest.mark.parametrize("mutation", ["repeat", "workload", "partial"])
    def should_reject_failed_controls(self, reproduction, mutation):
        cases = copy.deepcopy(reproduction[2]["cases"])
        if mutation == "repeat":
            cases["repeat"]["measurement"]["changed_transitions"] += 1
        elif mutation == "workload":
            cases["heavy"] = copy.deepcopy(cases["normal"])
        else:
            for name in ("normal", "repeat"):
                cases[name]["measurement"]["erasure_mixtures"] = []
        with pytest.raises(ValueError):
            cadence.require_controls(cases)

    def should_reject_source_drift(self):
        with pytest.raises(ValueError):
            cadence.patch(b"not pinned upstream")
        with pytest.raises(ValueError):
            cadence.source_for("missing anchor", True)

    @pytest.mark.parametrize("argument", ["../escape", "", "UPPER"])
    def should_reject_unsafe_run_names(self, monkeypatch, argument):
        monkeypatch.setattr(sys, "argv", ["cadence.py", "--run-id", argument])
        with pytest.raises(SystemExit) as result:
            cadence.main()
        assert result.value.code == 2

    def should_refuse_stale_output(self, reproduction, monkeypatch):
        work, _, _ = reproduction
        monkeypatch.setattr(sys, "argv", ["cadence.py", "--run-id", work.name])
        with pytest.raises(SystemExit) as result:
            cadence.main()
        assert result.value.code == 2

    def should_show_help_without_setup(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["cadence.py", "--help"])
        with pytest.raises(SystemExit) as result:
            cadence.main()
        assert result.value.code == 0


class DescribeExactRepeat:
    @pytest.mark.parametrize("index", [26, 83])
    def should_reject_changed_pixels_in_an_unclassified_frame(self, reproduction, scenes, index):
        _, out, report = reproduction
        cases = copy.deepcopy(report["cases"])
        frames = cadence.records(out / "repeat.frames")
        offset = cases["repeat"]["measurement"]["first_capture_index"] + index
        tick, pixels = frames[offset]
        altered = bytearray(pixels)
        altered[:6] = (b"\x2e\xbc\x24" if pixels[:3] == b"\x00\x1f\x00" else b"\x00\x1f\x00") * 2
        frames[offset] = (tick, bytes(altered))
        cases["repeat"]["measurement"] = cadence.analyze(frames, scenes)
        with pytest.raises(ValueError, match="repeat changed"):
            cadence.require_controls(cases)

    def should_record_the_independent_oracle_hash(self, reproduction):
        report = reproduction[2]
        assert report["inputs_sha256"][cadence.ORACLE] == cadence.digest(
            cadence.ROOT / cadence.ORACLE
        )
