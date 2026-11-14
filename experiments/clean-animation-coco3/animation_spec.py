"""Independent scene, capture corruption, firmware, and real emulator controls."""

import subprocess
import sys

import pytest
from animation import HERE, ROOT, analyze, check_ram, patch_gime, patch_ui, records
from oracle import rgb, scene


class DescribeOracle:
    def should_match_literal_edge_and_object_bytes(self):
        image = scene(0)
        assert len(image) == 6144
        assert image[:32] == image[-32:] == b"\xff" * 32
        assert image[32:64] == b"\x80" + b"\0" * 30 + b"\x01"
        assert image[2560:2592] == b"\x80\0\0\0\xff" + b"\0" * 26 + b"\x01"
        assert image[2816:2848] == b"\x80" + b"\0" * 30 + b"\x01"
        assert len(rgb(0)) == 512 * 192 * 3

    def should_reject_outside_scene_range(self):
        with pytest.raises(ValueError, match="bounded"):
            scene(5)


class DescribeCapture:
    def should_classify_exact_scenes_and_pixel_corruption(self):
        frames = [(i * 239856, rgb(i)) for i in range(5)]
        assert analyze(frames)["matches"] == list(range(5))
        bad = bytearray(rgb(2))
        bad[100] ^= 1
        frames[2] = (frames[2][0], bytes(bad))
        assert analyze(frames)["incomplete"] == 1

    def should_reject_missing_initial_scene(self):
        with pytest.raises(ValueError, match="Initial"):
            analyze([(0, rgb(1))])

    def should_reject_skipped_field(self):
        with pytest.raises(ValueError, match="Nonconsecutive"):
            analyze([(0, rgb(0)), (479712, rgb(1))])

    @pytest.mark.parametrize(
        "content, message",
        [
            (b"", "No renderer"),
            (b"2 0 512 192\n", "sequence"),
            (b"1 0 640 192\n", "viewport"),
            (b"1 0 512 192\nabc", "Truncated"),
        ],
    )
    def should_reject_broken_capture(self, tmp_path, content, message):
        capture = tmp_path / "frames"
        capture.write_bytes(content)
        with pytest.raises(ValueError, match=message):
            records(capture)

    def should_read_real_format(self, tmp_path):
        capture = tmp_path / "frames"
        capture.write_bytes(b"1 239856 512 192\n" + rgb(0))
        assert records(capture) == [(239856, rgb(0))]


class DescribeRam:
    @pytest.mark.parametrize("capacity", [128, 512])
    def should_require_full_scenes_and_guards(self, capacity):
        data = bytearray(capacity * 1024)
        for a in (0x40FF, 0x5900, 0x60FF, 0x7900, 0x7DFF, 0x7F00):
            data[a] = 0xA5
        data[0x4100:0x5900] = scene(4)
        data[0x6100:0x7900] = scene(3)
        data[-65536 + 0x3100] = 0x5A
        check_ram(data, capacity, {"complete": 0x3100})
        for address, message in [
            (0x5900, "guard"),
            (0x4100, "scenes"),
            (len(data) - 65536 + 0x3100, "marker"),
        ]:
            damaged = data.copy()
            damaged[address] ^= 1
            with pytest.raises(ValueError, match=message):
                check_ram(damaged, capacity, {"complete": 0x3100})
        with pytest.raises(ValueError, match="RAM size"):
            check_ram(data[:-1], capacity, {"complete": 0x3100})


class DescribeInstrumentation:
    @pytest.mark.parametrize("patch", [patch_ui, patch_gime])
    def should_refuse_source_drift(self, patch):
        with pytest.raises(ValueError):
            patch(b"wrong source")


class DescribeCli:
    @pytest.mark.parametrize(
        "args, code", [(["--help"], 0), (["--unknown"], 2), (["--run-id", "../escape"], 2)]
    )
    def should_parse_before_native_work(self, args, code):
        result = subprocess.run(
            [sys.executable, str(HERE / "animation.py"), *args],
            check=False,
            cwd=ROOT,
            capture_output=True,
            timeout=10,
        )
        assert result.returncode == code


@pytest.fixture(scope="module")
def reproduction():
    import json
    import uuid

    from animation import main

    run_id = "spec-" + uuid.uuid4().hex[:12]
    old = sys.argv
    sys.argv = ["animation.py", "--run-id", run_id]
    try:
        main()
    finally:
        sys.argv = old
    out = ROOT / "build/clean-animation-coco3" / run_id
    return out, json.loads((out / "results.json").read_text())


class DescribeRealGime:
    def should_render_complete_progressing_scenes_and_detect_faults(self, reproduction):
        _, report = reproduction
        assert report["passed"]
        assert len(report["runs"]) == 6
        for run in report["runs"]:
            if run["variant"] == "normal":
                assert run["measurement"]["incomplete"] == 0
                assert set(run["measurement"]["matches"]) == {0, 1, 2, 3, 4}
                assert all(p["row_fetches"] == 192 for p in run["timing"])
            else:
                assert run["measurement"]["incomplete"] > 0

    def should_repeat_identical_frames_and_timing(self, reproduction):
        from animation import run

        out, report = reproduction
        again = run(out / "private/xroar-1.12.1/src/xroar", out / "repeat", 128, "normal")
        assert again["measurement"] == report["runs"][0]["measurement"]
        assert again["timing"] == report["runs"][0]["timing"]

    def should_reject_missing_instrumentation_despite_good_ram(self, reproduction):
        from pathlib import Path

        from animation import run, tool_path

        out, _ = reproduction
        with pytest.raises(FileNotFoundError):
            run(Path(tool_path("xroar", ROOT)), out / "uninstrumented", 128, "normal")
        assert (out / "uninstrumented/final.ram").stat().st_size == 131072

    def should_reject_changed_fetch_clock_and_phase_evidence(self, reproduction):
        from copy import deepcopy

        from animation import timing, trace_records

        out, _ = reproduction
        events = trace_records(out / "128-normal/gime.txt")
        publications = [e for e in events if e["kind"] == "write" and e["base"] in (0x4100, 0x6100)]
        for key, value, message in [("active", 1, "active"), ("fast", 1, "Accelerated")]:
            damaged = deepcopy(events)
            next(e for e in damaged if e["tick"] == publications[1]["tick"])[key] = value
            with pytest.raises(ValueError, match=message):
                timing(damaged, "normal")
        damaged = deepcopy(events)
        first = next(
            e for e in damaged if e["kind"] == "fetch" and e["tick"] > publications[1]["tick"]
        )
        first["scan"] += 8
        with pytest.raises(ValueError, match="fetch"):
            timing(damaged, "normal")
        with pytest.raises(ValueError, match="publications"):
            timing([], "normal")


class DescribeFailureControls:
    def should_reject_frozen_front_and_undetected_controls(self):
        from animation import require_measurement

        with pytest.raises(ValueError, match="progressing"):
            require_measurement({"incomplete": 0, "matches": [0] * 50}, "normal")
        with pytest.raises(ValueError, match="escaped"):
            require_measurement({"incomplete": 0}, "wrong-base")
        with pytest.raises(ValueError, match="witness"):
            require_measurement({"incomplete": 2, "erasure_proofs": []}, "unsafe")


class DescribeFirmwareBoundary:
    @pytest.mark.parametrize("damage", ["missing", "short", "corrupt"])
    def should_stop_before_private_build_or_launch(self, tmp_path, monkeypatch, damage):
        import animation

        (tmp_path / "roms.json").write_bytes((ROOT / "roms.json").read_bytes())
        firmware = tmp_path / "local/roms/coco3/coco3.rom"
        firmware.parent.mkdir(parents=True)
        if damage != "missing":
            data = bytearray((ROOT / "local/roms/coco3/coco3.rom").read_bytes())
            if damage == "short":
                data = data[:-1]
            else:
                data[100] ^= 1
            firmware.write_bytes(data)
        monkeypatch.setattr(animation, "ROOT", tmp_path)
        monkeypatch.setattr(sys, "argv", ["animation.py", "--run-id", "bad-rom"])

        with pytest.raises((ValueError, FileNotFoundError)):
            animation.main()

        out = tmp_path / "build/clean-animation-coco3/bad-rom"
        assert not (out / "private").exists()
        assert '"passed": false' in (out / "results.json").read_text()


class DescribeCompleteWindow:
    @pytest.mark.parametrize("fault", ["tail", "reorder"])
    def should_reject_whole_frame_loss_or_wrong_order(self, fault):
        from animation import require_measurement

        matches = [0] * 8 + [1] * 8 + [2] * 8 + [3] * 8 + [4] * 10
        require_measurement({"incomplete": 0, "matches": matches}, "normal")
        if fault == "tail":
            matches = matches[:-6]
        else:
            matches = [0 if n == 0 else 5 - n for n in matches]
        with pytest.raises(ValueError, match="progressing"):
            require_measurement({"incomplete": 0, "matches": matches}, "normal")

    def should_record_oracle_environment(self, reproduction):
        import numpy as np
        from animation import digest

        environment = reproduction[1]["python_environment"]
        assert environment["python"] == sys.version
        assert environment["numpy"] == np.__version__
        assert environment["uv_lock_sha256"] == digest(ROOT / "uv.lock")
        assert environment["pyproject_sha256"] == digest(ROOT / "pyproject.toml")
