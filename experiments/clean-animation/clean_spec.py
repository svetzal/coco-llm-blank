"""Actual machine outcomes, independent scene expectations and failure controls."""

import copy
import json
import sys

import clean
import numpy as np
import pytest


def rgb(screen):
    pixels = np.unpackbits(np.frombuffer(screen, np.uint8)).reshape(192, 256)
    colors = np.array([(0, 31, 0), (46, 188, 36)], dtype=np.uint8)
    return np.repeat(colors[pixels], 2, axis=1).tobytes()


@pytest.fixture(scope="module")
def scenes():
    return [clean.expected_screen(i) for i in range(1, 65)]


class DescribeCleanAnimation:
    def should_reproduce_complete_scenes_on_both_targets(self, reproduction, scenes):
        _, out, report = reproduction
        assert report["passed"]
        clean.require_controls(report["cases"])
        for target in clean.ROM_NAMES:
            normal = report["cases"][f"{target}-normal"]
            assert normal["ram_scenes"] == list(clean.CHECKS)
            for variant in ("normal", "heavy", "repeat"):
                measured = clean.cadence.analyze(
                    clean.cadence.records(out / f"{target}-{variant}/video.frames"), scenes
                )
                clean.require_clean(measured)
                assert measured["complete_scene_frames"] == 150
                assert measured["background_only_frames"] == 0
            single = report["cases"][f"{target}-single"]
            assert single["source_sha256"] == clean.cadence.digest(
                clean.ROOT / "examples/moving-objects/main.asm"
            )
            with pytest.raises(ValueError, match="intermediate"):
                clean.require_clean(single["measurement"])

    @pytest.mark.parametrize(
        "mutation", ["blank", "background", "partial", "skip", "reverse", "frozen"]
    )
    def should_reject_bad_continuous_scenes(self, scenes, mutation):
        images = [scenes[min(i // 6, 29)] for i in range(180)]
        if mutation == "blank":
            images[70] = bytes(6144)
        elif mutation == "background":
            images[70] = clean.cadence.background(False)
        elif mutation == "partial":
            images[70] = scenes[11][: 32 * 14] + clean.cadence.background(False)[32 * 14 :]
        elif mutation == "skip":
            images[70] = scenes[14]
        elif mutation == "reverse":
            images[70] = scenes[1]
        else:
            images = [scenes[0]] * 180
        frames = [(i * clean.PERIOD, rgb(screen)) for i, screen in enumerate(images)]
        with pytest.raises(ValueError):
            clean.require_clean(clean.cadence.analyze(frames, scenes))

    @pytest.mark.parametrize(
        "mutation", ["size", "guard", "count", "position", "pointer", "hidden", "visible"]
    )
    def should_reject_bad_ram(self, reproduction, mutation):
        _, out, _ = reproduction
        folder = out / "coco1-normal"
        symbols = {
            k: int(v, 16)
            for k, v in clean.re.findall(
                r"^(\w+)\s+EQU\s+\$([\da-fA-F]+)",
                (folder / "program.sym").read_text(),
                clean.re.MULTILINE,
            )
        }
        data = bytearray((folder / "check-2.ram").read_bytes())
        addresses = {
            "guard": 0x3C00,
            "count": symbols["frames"],
            "position": symbols["xpos"],
            "pointer": symbols["drawing"],
            "hidden": 0x400,
            "visible": 0x2400,
        }
        if mutation == "size":
            data.pop()
        else:
            data[addresses[mutation]] ^= 1
        with pytest.raises(ValueError):
            clean.verify_hidden(data, symbols, 2)

    @pytest.mark.parametrize("mutation", ["repeat", "single", "heavy", "short"])
    def should_reject_failed_cross_case_controls(self, reproduction, mutation):
        cases = copy.deepcopy(reproduction[2]["cases"])
        if mutation == "repeat":
            cases["coco1-repeat"]["measurement"]["frame_rgb_sha256"][75] = "bad"
        elif mutation == "single":
            cases["coco1-single"]["measurement"]["non_complete_scene_frames"] = 0
        elif mutation == "heavy":
            cases["coco1-heavy"]["costs"] = cases["coco1-normal"]["costs"]
        else:
            for variant in ("normal", "repeat"):
                cases[f"coco1-{variant}"]["costs"]["draw_ticks"] = {"100": 1}
        with pytest.raises(ValueError):
            clean.require_controls(cases)

    @pytest.mark.parametrize(
        "text", ["1 0\n2 2\n", "", "1 0\n2 1\n3 2\n", "3 0\n2 1\n1 2\n4 3\n" * 3]
    )
    def should_reject_invalid_cost_events(self, tmp_path, text):
        path = tmp_path / "events"
        path.write_text(text)
        with pytest.raises(ValueError):
            clean.costs(path, [30000, 60000, 90000])

    def should_reject_drawing_before_previous_buffer_reuse(self, tmp_path):
        path = tmp_path / "events"
        path.write_text(
            "0 0\n10 1\n1000 2\n30000 3\n"
            "29984 0\n30010 1\n31000 2\n60000 3\n"
            "60000 0\n60010 1\n61000 2\n90000 3\n"
        )
        with pytest.raises(ValueError, match="chronology"):
            clean.costs(path, [30000, 60000, 90000])

    def should_measure_ticks_without_using_host_time(self, tmp_path):
        path = tmp_path / "events"
        path.write_text(
            "0 0\n10 1\n1000 2\n30000 3\n"
            "30000 0\n30010 1\n31000 2\n60000 3\n"
            "60000 0\n60010 1\n61000 2\n90000 3\n90000 0\n"
        )
        result = clean.costs(path, [30000, 60000, 90000])
        assert result["draw_ticks"] == {10: 3}
        assert result["wait_and_publish_ticks"] == {990: 3}
        assert result["publication_interval_ticks"] == {30000: 2}
        assert result["completed_scene_hz"] == pytest.approx(14318180 / 30000)

    def should_stop_with_missing_capture_on_real_uninstrumented_emulator(self, tmp_path, scenes):
        with pytest.raises(FileNotFoundError):
            clean.run_case(
                clean.tool_path("xroar", clean.ROOT), "coco1", "repeat", tmp_path / "plain", scenes
            )
        assert (tmp_path / "plain/scene-1.ram").exists()

    def should_reject_code_overlapping_stack(self, tmp_path):
        with pytest.raises(ValueError, match="stack overlap"):
            clean.assemble(" org $7E00\nstart nop\nprogram_end\n end start\n", tmp_path)

    @pytest.mark.parametrize(
        "args,code", [(["--help"], 0), (["--run-id", "../bad"], 2), (["--unknown"], 2)]
    )
    def should_parse_before_building(self, monkeypatch, args, code):
        monkeypatch.setattr(sys, "argv", ["clean.py", *args])
        with pytest.raises(SystemExit) as result:
            clean.main()
        assert result.value.code == code

    def should_refuse_overwriting_evidence(self, reproduction, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["clean.py", "--run-id", reproduction[0].name])
        with pytest.raises(SystemExit) as result:
            clean.main()
        assert result.value.code == 2

    def should_record_commands_and_verified_firmware(self, reproduction):
        _, out, report = reproduction
        for name, case in report["cases"].items():
            cmd = json.loads((out / name / "continuous-command.json").read_text())
            assert cmd[cmd.index("-c") + 1] == clean.os.devnull
            assert cmd[cmd.index("-machine-cpu") + 1] == "6809"
            assert cmd[cmd.index("-ram") + 1] == "32"
            assert cmd[cmd.index("-ui") + 1] == "null"
            assert len(case["rom_sha256"]) == 2
