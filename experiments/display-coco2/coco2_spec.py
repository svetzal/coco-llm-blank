"""Actual renderer controls and acceptance failures for the declared profile."""

import json
import sys

import coco2
import pytest
from cases import compare_capture, require_case, require_unreachable, symbol


class DescribeCoCo2Display:
    def should_capture_thirteen_cases_twice_with_independent_pixels(self, reproduction):
        _, _, report = reproduction
        assert report["passed"]
        assert len(report["cases"]) == 13
        for case in report["cases"]:
            captures = case["captures"]
            assert captures[0]["capture_sha256"] == captures[1]["capture_sha256"]
            for capture in captures:
                assert capture["ram_matches"]
                assert capture["pixel_mismatches"] == (3040 if case["name"] == "wrong-sam" else 0)
                cmd = capture["command"]
                for option, value in (
                    ("-tv-type", "ntsc"),
                    ("-vdg-type", "6847"),
                    ("-machine-cpu", "6809"),
                    ("-ram", "32"),
                ):
                    assert cmd[cmd.index(option) + 1] == value
                assert cmd[cmd.index("-bas") + 1].endswith("/coco2/bas12.rom")
                assert cmd[cmd.index("-extbas") + 1].endswith("/coco2/extbas11.rom")
        assert report["unreachable"]["capture_exists"]
        assert not report["unreachable"]["snapshot_exists"]

    @pytest.mark.parametrize(
        "name,field", [("asymmetric", None), ("tile-room-5", "step"), ("masked-objects-8", "scene")]
    )
    def should_reject_wrong_scene_identity(self, reproduction, name, field):
        _, output, _ = reproduction
        case = next(c for c in coco2.make_scenes() if c.name == name)
        symbols = (output / f"{name}.sym").read_text()
        memory = bytearray((output / f"{name}-0.5.ram").read_bytes())
        memory[symbol(symbols, field) if field else 0x2FFF] ^= 1
        with pytest.raises(ValueError):
            coco2.stationary_checkpoint(case, symbols, memory)

    def should_reject_nonstationary_checkpoint(self, reproduction):
        _, output, _ = reproduction
        case = coco2.make_scenes()[0]
        symbols = (output / "asymmetric.sym").read_text()
        memory = bytearray((output / "asymmetric-0.5.ram").read_bytes())
        memory[symbol(symbols, "ready")] = 0x12
        with pytest.raises(ValueError, match="stationary"):
            coco2.stationary_checkpoint(case, symbols, memory)

    def should_reject_wrong_mode_despite_matching_ram(self, reproduction):
        _, output, _ = reproduction
        case = coco2.make_scenes()[0]
        result = compare_capture(output / "wrong-sam-0.5.ppm", output / "wrong-sam-0.5.ram", case)
        assert result["ram_matches"]
        with pytest.raises(ValueError, match="rendered mismatch"):
            require_case(case.name, result)
        result = compare_capture(output / "asymmetric-0.5.ppm", output / "asymmetric-0.5.ram", case)
        with pytest.raises(ValueError, match="rendered mismatch"):
            require_case("wrong-sam", result)

    def should_reject_reachable_negative_trap_in_actual_emulator(self, reproduction):
        work, output, _ = reproduction
        binary = output / "masked-objects-11.bin"
        symbols = binary.with_suffix(".sym").read_text()
        roms = coco2.verify_installed(coco2.ROOT, "coco2", ("bas12.rom", "extbas11.rom"))
        cmd = coco2.command(
            work / "xroar-1.12.1/src/xroar",
            roms,
            binary,
            symbol(symbols, "frozen"),
            output / "reachable-control.ram",
        )
        code, _, ram = coco2.shared.launch(cmd, output, "reachable-control")
        with pytest.raises(ValueError, match="Unreachable"):
            require_unreachable(code, ram)

    @pytest.mark.parametrize(
        "arguments", [["--help"], ["--bad"], ["--run-id", "../escape"], ["--run-id", ""]]
    )
    def should_leave_no_directories_for_help_or_bad_arguments(
        self, tmp_path, monkeypatch, arguments
    ):
        monkeypatch.setattr(coco2, "RESEARCH", tmp_path / "research")
        monkeypatch.setattr(coco2, "OUTPUT", tmp_path / "output")
        monkeypatch.setattr(sys, "argv", ["coco2.py", *arguments])
        with pytest.raises(SystemExit) as error:
            coco2.main()
        assert error.value.code == (0 if arguments == ["--help"] else 2)
        assert list(tmp_path.iterdir()) == []

    def should_preserve_existing_run(self, reproduction, monkeypatch):
        work, output, _ = reproduction
        before = (output / "results.json").read_bytes()
        monkeypatch.setattr(sys, "argv", ["coco2.py", "--run-id", work.name])
        with pytest.raises(SystemExit):
            coco2.main()
        assert (output / "results.json").read_bytes() == before

    def should_preserve_failed_archive_control(self, tmp_path, monkeypatch):
        archive = tmp_path / "bad.tar.gz"
        archive.write_bytes(b"not the pinned source")
        monkeypatch.setattr(coco2, "RESEARCH", tmp_path / "research")
        monkeypatch.setattr(coco2, "OUTPUT", tmp_path / "output")
        monkeypatch.setattr(sys, "argv", ["coco2.py", "--archive", str(archive)])
        with pytest.raises(ValueError, match="checksum"):
            coco2.main()
        report = json.loads((tmp_path / "output/fresh/results.json").read_text())
        assert not report["passed"]
        assert "build" not in report
