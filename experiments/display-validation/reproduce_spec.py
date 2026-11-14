"""Real rebuild and controls which must reject plausible false successes."""

import json
import sys
import tarfile

import pytest
import reproduce
from cases import (
    compare_capture,
    make_cases,
    require_case,
    require_unreachable,
    symbol,
)
from first_screen import expected_screen
from instrument import instrument, replace_once
from PIL import Image


def cases():
    return make_cases(
        (reproduce.ROOT / "examples/first-screen/main.asm").read_text(),
        (reproduce.ROOT / "examples/moving-objects/main.asm").read_text(),
        expected_screen(),
    )


class DescribeReproduction:
    def should_rebuild_and_match_the_reviewed_baseline(self, reproduction):
        work, output, report = reproduction
        assert report["passed"]
        assert [c["pixel_mismatches"] for c in report["cases"]] == [0, 0, 3040, 0, 0, 0]
        assert all(c["ram_matches"] for c in report["cases"])
        assert report["unreachable"]["capture_exists"]
        assert not report["unreachable"]["snapshot_exists"]
        assert report["unreachable"]["checkpoint"]["address"] == symbol(
            (output / "moving-frozen-65.sym").read_text(), "state"
        )
        assert (work / "xroar-1.12.1/src/xroar").is_file()

    def should_accept_verified_offline_archive_and_reject_damage(self, reproduction, tmp_path):
        work, _, _ = reproduction
        source = work / "xroar-1.12.1.tar.gz"
        copied = reproduce.obtain_archive(tmp_path / "copy.tar.gz", source)
        assert reproduce.digest(copied) == reproduce.ARCHIVE_SHA256
        copied.write_bytes(copied.read_bytes() + b"damage")

        with pytest.raises(ValueError, match="checksum mismatch"):
            reproduce.obtain_archive(tmp_path / "bad.tar.gz", copied)
        assert not (tmp_path / "bad.tar.gz").exists()

    def should_reject_modified_or_already_instrumented_source(self, reproduction):
        work, _, _ = reproduction
        with tarfile.open(work / "xroar-1.12.1.tar.gz") as archive:
            pristine = archive.extractfile("xroar-1.12.1/src/null/ui_null.c").read()
        patched = instrument(pristine)

        for source in (pristine + b"\n", patched):
            with pytest.raises(ValueError, match="not the pristine"):
                instrument(source)
        assert patched == (work / "xroar-1.12.1/src/null/ui_null.c").read_bytes()

    @pytest.mark.parametrize("source", ["missing", "needle needle"])
    def should_reject_missing_or_ambiguous_replacement(self, source):
        with pytest.raises(ValueError, match="exactly one"):
            replace_once(source, "needle", "replacement")

    @pytest.mark.parametrize("symbols", ["", "ready EQU $3000\nready EQU $3002\n"])
    def should_reject_missing_or_ambiguous_symbols(self, symbols):
        with pytest.raises(ValueError, match="one assembler symbol"):
            symbol(symbols, "ready")

    def should_reject_wrong_sam_with_wrong_framebuffer(self, reproduction, tmp_path):
        _, output, _ = reproduction
        case = cases()[2]
        memory = bytearray((output / "wrong-sam.ram").read_bytes())
        memory[0x400] ^= 1
        ram = tmp_path / "wrong.ram"
        ram.write_bytes(memory)

        result = compare_capture(output / "wrong-sam.ppm", ram, case)
        assert result["pixel_mismatches"] == 3040
        with pytest.raises(ValueError, match="framebuffer mismatch"):
            require_case(case.name, result)

    def should_reject_wrong_sam_if_mode_mutation_is_removed(self, reproduction):
        _, output, _ = reproduction
        case = cases()[2]
        result = compare_capture(output / "asymmetric.ppm", output / "asymmetric.ram", case)

        assert result["ram_matches"]
        with pytest.raises(ValueError, match="unexpected rendered mismatch"):
            require_case("wrong-sam", result)

    def should_reject_a_positive_case_with_a_display_error(self, reproduction):
        _, output, _ = reproduction
        result = compare_capture(output / "wrong-sam.ppm", output / "wrong-sam.ram", cases()[1])

        with pytest.raises(ValueError, match="unexpected rendered mismatch"):
            require_case("asymmetric", result)

    @pytest.mark.parametrize("mutation", ["dimension", "palette", "mode", "ram-size"])
    def should_reject_invalid_capture_contract(self, reproduction, tmp_path, mutation):
        _, output, _ = reproduction
        ppm, ram = tmp_path / "image.ppm", tmp_path / "memory.ram"
        ram.write_bytes((output / "asymmetric.ram").read_bytes())
        with Image.open(output / "asymmetric.ppm") as original:
            image = original.copy()
        if mutation == "dimension":
            image = image.crop((0, 0, 256, 192))
        elif mutation == "palette":
            image.putpixel((0, 0), (255, 0, 0))
        elif mutation == "mode":
            image = image.convert("L")
        else:
            ram.write_bytes(ram.read_bytes()[:-1])
        image.save(ppm)

        with pytest.raises(ValueError, match="dimensions|palette|32 KiB"):
            compare_capture(ppm, ram, cases()[1])

    def should_reject_a_reachable_checkpoint_as_the_negative_control(self, reproduction, tmp_path):
        _, output, report = reproduction
        command = report["unreachable"]["command"].copy()
        ready = symbol((output / "moving-frozen-65.sym").read_text(), "frozen")
        command[command.index("-trap") + 1] = f"pc=0x{ready:04x}"
        command[command.index("-trap-snap") + 1] = str(tmp_path / "reachable.ram")
        code, _, ram = reproduce.launch(command, tmp_path, "reachable")

        assert code == 0 and ram.exists()
        with pytest.raises(ValueError, match="Unreachable PC control failed"):
            require_unreachable(code, ram)

    def should_reject_process_failure_without_a_checkpoint(self, tmp_path):
        with pytest.raises(ValueError, match="Unreachable PC control failed"):
            require_unreachable(1, tmp_path / "absent.ram")

    @pytest.mark.parametrize("arguments", [["--help"], ["--invalid"], ["--run-id", "../escape"]])
    def should_parse_before_creating_any_inputs(self, monkeypatch, tmp_path, arguments):
        monkeypatch.setattr(sys, "argv", ["reproduce.py", *arguments])
        monkeypatch.setattr(reproduce, "RESEARCH", tmp_path / "research")
        monkeypatch.setattr(reproduce, "OUTPUT", tmp_path / "output")

        with pytest.raises(SystemExit) as error:
            reproduce.main()
        assert error.value.code == (0 if arguments == ["--help"] else 2)
        assert list(tmp_path.iterdir()) == []

    def should_refuse_stale_run_directories(self, reproduction, monkeypatch):
        work, _, _ = reproduction
        monkeypatch.setattr(sys, "argv", ["reproduce.py", "--run-id", work.name])

        with pytest.raises(SystemExit) as error:
            reproduce.main()
        assert error.value.code == 2

    def should_refuse_invalid_assembler_override(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LWASM", str(tmp_path / "nonexistent"))
        monkeypatch.setattr(sys, "argv", ["reproduce.py", "--run-id", "missing-assembler"])

        with pytest.raises(SystemExit) as error:
            reproduce.main()
        assert error.value.code == 2

    def should_keep_a_failed_report_for_a_corrupt_archive(self, monkeypatch, tmp_path):
        archive = tmp_path / "bad.tar.gz"
        archive.write_bytes(b"not the pinned release")
        monkeypatch.setattr(sys, "argv", ["reproduce.py", "--archive", str(archive)])
        monkeypatch.setattr(reproduce, "RESEARCH", tmp_path / "research")
        monkeypatch.setattr(reproduce, "OUTPUT", tmp_path / "output")

        with pytest.raises(ValueError, match="checksum mismatch"):
            reproduce.main()
        report = json.loads((tmp_path / "output/fresh/results.json").read_text())
        assert not report["passed"]
        assert not (tmp_path / "research/fresh/xroar-1.12.1").exists()

    @pytest.mark.parametrize("damage", ["missing", "corrupt"])
    def should_reject_unverified_firmware_before_build(self, monkeypatch, tmp_path, damage):
        root = tmp_path / "checkout"
        directory = root / "local/roms/coco1"
        directory.mkdir(parents=True)
        (root / "roms.json").write_bytes((reproduce.ROOT / "roms.json").read_bytes())
        for name in ("bas11.rom", "extbas10.rom"):
            data = (reproduce.ROOT / "local/roms/coco1" / name).read_bytes()
            (directory / name).write_bytes(data)
        ext = directory / "extbas10.rom"
        if damage == "missing":
            ext.unlink()
        else:
            data = bytearray(ext.read_bytes())
            data[0] ^= 1
            ext.write_bytes(data)
        monkeypatch.setattr(reproduce, "ROOT", root)
        monkeypatch.setattr(reproduce, "RESEARCH", tmp_path / "research")
        monkeypatch.setattr(reproduce, "OUTPUT", tmp_path / "output")
        monkeypatch.setattr(sys, "argv", ["reproduce.py"])

        with pytest.raises(ValueError, match="Cannot use coco1 firmware"):
            reproduce.main()
        assert not (tmp_path / "research").exists()
        assert not (tmp_path / "output").exists()
