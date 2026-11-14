"""Exercise real converter, filesystem, assembler and emulator boundaries."""

import json
import shutil
import subprocess
import sys

import loading
import pytest


class DescribeBundleConsumer:
    def should_match_original_pixels_and_hand_calculated_rows(self, inputs):
        source, bundle = inputs
        original = json.loads(source.read_bytes())
        prepared = json.loads(bundle.read_bytes())

        for asset in original["assets"]:
            literal = loading.LITERALS[asset["asset_id"]]
            assert [[int(bit) for bit in f"{row:08b}"] for row in literal] == asset["pixels"]
        assert bytes.fromhex(prepared["framebuffer_hex"]) == loading.expected_screen()
        screen = loading.expected_screen()
        assert screen[42 * 32 + 7] == 0x20
        assert screen[47 * 32 + 6] == 0xC1
        assert screen[48 * 32 :] == bytes(144 * 32)

    def should_build_identical_include_binary_and_symbols(self, inputs, tmp_path):
        source, bundle = inputs
        a, sa = loading.build(source, bundle, tmp_path / "a")
        b, sb = loading.build(source, bundle, tmp_path / "b")

        assert a.read_bytes() == b.read_bytes()
        assert sa == sb
        assert a.with_name("assets.inc").read_bytes() == b.with_name("assets.inc").read_bytes()
        data = a.read_bytes()
        assert data[0] == 0 and int.from_bytes(data[3:5], "big") == 0x3000
        assert data[-5:] == bytes.fromhex("ff00003000")
        assert sa["program_end"] < 0x7E00

    @pytest.mark.parametrize(
        "field,value",
        [
            ("width", 7),
            ("height", True),
            ("stride", 1.0),
            ("anchor", [1, 0]),
            ("packing", "lsb-first-1bpp"),
            ("palette", "other"),
            ("asset_id", 999),
            ("hex", "00"),
            ("hex", "ff" * 8),
        ],
    )
    def should_reject_changed_descriptors_and_payload_before_assembly(
        self, inputs, tmp_path, field, value
    ):
        source, bundle = inputs
        output = tmp_path / "build"
        loading.build(source, bundle, output)
        data = json.loads(bundle.read_bytes())
        data["assets"][0][field] = value
        bundle.write_text(json.dumps(data))

        with pytest.raises(ValueError, match="stale or corrupt"):
            loading.build(source, bundle, output)
        assert list(output.iterdir()) == []

    @pytest.mark.parametrize("damage", ["truncated", "missing", "stale", "screen", "mapping"])
    def should_reject_bad_bundle_then_recover(self, inputs, tmp_path, damage):
        source, bundle = inputs
        if damage == "truncated":
            bundle.write_bytes(bundle.read_bytes()[:-20])
        elif damage == "missing":
            bundle.unlink()
        elif damage == "stale":
            source.write_bytes(source.read_bytes() + b"\n")
        else:
            data = json.loads(bundle.read_bytes())
            if damage == "screen":
                data["screen"]["stride"] = 16
            else:
                data["terrain_to_asset"][0] = 90
            bundle.write_text(json.dumps(data))

        with pytest.raises((ValueError, OSError)):
            loading.build(source, bundle, tmp_path / "build")
        loading.prepare.publish(source, bundle)
        binary, _ = loading.build(source, bundle, tmp_path / "build")
        assert binary.stat().st_size > 100

    @pytest.mark.parametrize("field,value", [("width", True), ("height", 8.0), ("stride", 2)])
    def should_reject_invalid_source_even_with_old_valid_bundle(
        self, inputs, tmp_path, field, value
    ):
        source, bundle = inputs
        data = json.loads(source.read_bytes())
        data["assets"][0][field] = value
        source.write_text(json.dumps(data))

        with pytest.raises(ValueError):
            loading.build(source, bundle, tmp_path / "build")
        assert not (tmp_path / "build/assets.inc").exists()


class DescribeTargetExecution:
    def should_check_both_targets_and_detect_actual_bad_programs(self, evidence):
        output, report = evidence
        assert report["passed"]
        assert len(report["runs"]) == 6
        for run in report["runs"]:
            assert run["unreachable_absent"]
            if run["mutation"] == "WRONG_BITS":
                assert "framebuffer" in run["detected"]
            elif run["mutation"] == "OVERFLOW":
                assert run["detected"] == "guard damaged"
            else:
                assert run["checked_framebuffer_bytes"] == 6144
                assert (output / "valid" / run["target"] / "ready.ram").stat().st_size == 32768

    @pytest.mark.parametrize("damage", ["size", "completion", "screen", "guard", "art", "room"])
    def should_reject_corrupted_captured_state(self, evidence, damage):
        output, report = evidence
        symbols = report["runs"][0]["symbols"]
        memory = bytearray((output / "valid/coco1/ready.ram").read_bytes())
        if damage == "size":
            memory.pop()
        else:
            address = {
                "completion": symbols["completed"],
                "screen": 0x1BFF,
                "guard": symbols["asset_guard_after"],
                "art": symbols["asset_40"],
                "room": symbols["room"],
            }[damage]
            memory[address] ^= 1

        with pytest.raises(ValueError):
            loading.assess(bytes(memory), symbols)

    def should_detect_valid_but_wrong_art_assignment_on_target(self, inputs, tmp_path):
        source, bundle = inputs
        data = json.loads(source.read_bytes())
        data["terrain_to_asset"][0:2] = [40, 10]
        source.write_text(json.dumps(data))
        loading.prepare.publish(source, bundle)
        binary, symbols = loading.build(source, bundle, tmp_path / "build")
        memory, _ = loading.capture("coco1", binary, symbols, tmp_path / "capture")

        with pytest.raises(ValueError, match="framebuffer"):
            loading.assess(memory, symbols)

    def should_remove_stale_capture_when_checkpoint_is_unreachable(self, evidence, tmp_path):
        output, report = evidence
        symbols = dict(report["runs"][0]["symbols"])
        symbols["ready"] = symbols["asset_guard_after"]
        (tmp_path / "ready.ram").write_bytes((output / "valid/coco1/ready.ram").read_bytes())

        with pytest.raises(FileNotFoundError):
            loading.capture("coco1", output / "valid/room.bin", symbols, tmp_path)
        assert not (tmp_path / "ready.ram").exists()

    @pytest.mark.parametrize("failure", ["missing", "partial", "corrupt"])
    def should_fail_closed_on_unverified_firmware(self, evidence, tmp_path, monkeypatch, failure):
        output, report = evidence
        shutil.copy(loading.ROOT / "roms.json", tmp_path / "roms.json")
        directory = tmp_path / "local/roms/coco1"
        directory.mkdir(parents=True)
        if failure != "missing":
            shutil.copy(loading.ROOT / "local/roms/coco1/bas11.rom", directory)
        if failure == "corrupt":
            (directory / "extbas10.rom").write_bytes(bytes(8192))
        monkeypatch.setattr(loading, "ROOT", tmp_path)

        with pytest.raises(ValueError, match="Cannot use coco1 firmware"):
            loading.capture(
                "coco1",
                output / "valid/room.bin",
                report["runs"][0]["symbols"],
                tmp_path / "capture",
            )
        assert not (tmp_path / "capture").exists()

    def should_support_help_without_building_or_launching(self, tmp_path):
        result = subprocess.run(
            [sys.executable, str(loading.HERE / "loading.py"), "--help"],
            check=False,
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        bad = subprocess.run(
            [sys.executable, str(loading.HERE / "loading.py"), "--unknown"],
            check=False,
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0 and "--output" in result.stdout
        assert bad.returncode == 2
        assert list(tmp_path.iterdir()) == []

    def should_run_cli_with_isolated_output(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["loading.py", "--output", str(tmp_path)])
        loading.main()
        assert "PASS" in capsys.readouterr().out
        assert json.loads((tmp_path / "results.json").read_bytes())["passed"]


class DescribePublication:
    def should_keep_identity_when_source_asset_order_changes(self, inputs):
        source, bundle = inputs
        before = loading.assembly_data(source, bundle)
        data = json.loads(source.read_bytes())
        data["assets"].reverse()
        source.write_text(json.dumps(data))
        loading.prepare.publish(source, bundle)

        assert loading.assembly_data(source, bundle) == before

    def should_invalidate_success_report_on_failed_rerun(self, tmp_path, monkeypatch):
        output = tmp_path / "output"
        output.mkdir()
        (output / "results.json").write_text('{"passed":true}')
        source = tmp_path / "invalid.json"
        source.write_text("truncated {")
        monkeypatch.setattr(loading, "SOURCE", source)

        with pytest.raises(ValueError):
            loading.check(output)
        assert not json.loads((output / "results.json").read_bytes())["passed"]
