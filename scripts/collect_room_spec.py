"""Outcome checks for the original game and its real emulator/firmware boundary."""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import collect_room as game
import pytest


@pytest.fixture(scope="module")
def ready_emulator():
    return game.prepare_emulator()


@pytest.fixture(scope="module", params=("coco1", "coco2"))
def checked_game(request, ready_emulator):
    return request.param, game.check(request.param)


class DescribePlayableRoom:
    def should_complete_three_wins_in_both_collection_orders_on_both_machines(self, checked_game):
        target, result = checked_game
        assert result["status"] == "passed"
        assert result["checkpoints"] == 95
        assert result["audio"]["dac_writes"] == 384
        assert result["rejected_mutations"] == list(game.MUTATIONS)
        assert result["program_end"] < 0x7E00
        assert result["target"] == target
        assert result["scan_interval_ticks"][0] > 0

    def should_distinguish_rooms_with_the_same_remaining_count(self, checked_game):
        target, _ = checked_game
        output = game.OUTPUT / f"{target}-normal-keys"
        import re

        labels = {
            name: int(value, 16)
            for name, value in re.findall(
                r"(\w+) EQU \$([0-9A-Fa-f]+)", (output / "game.sym").read_text()
            )
        }
        keys, state = game.journey()[75]
        ram = (output / "frame-75.ram").read_bytes()
        assert state[3] == 1
        assert state[8] == 2
        assert ram[labels["room"] + 9] == 2
        assert ram[labels["room"] + 37] == 0
        game.verify_ram(ram, labels, keys, state)

        with pytest.raises(ValueError, match="Room lifecycle"):
            game.verify_ram(ram, labels, keys, (*state[:8], 1))

    @pytest.mark.parametrize("damage", ["length", "guard", "map", "screen", "samples", "history"])
    def should_reject_corrupt_evidence(self, checked_game, damage):
        target, _ = checked_game
        output = game.OUTPUT / f"{target}-normal-keys"
        import re

        symbols = {
            name: int(value, 16)
            for name, value in re.findall(
                r"(\w+) EQU \$([0-9A-Fa-f]+)", (output / "game.sym").read_text()
            )
        }
        ram = bytearray((output / "frame-64.ram").read_bytes())
        if damage == "length":
            ram = ram[:100]
        else:
            address = {
                "guard": 0x7E00,
                "map": symbols["room"],
                "screen": 0x400,
                "samples": symbols["sample_count"],
                "history": symbols["previous"],
            }[damage]
            ram[address] ^= 1
        keys, state = game.journey()[64]

        with pytest.raises(ValueError):
            game.verify_ram(bytes(ram), symbols, keys, state)

    def should_invalidate_a_success_before_a_failed_rerun(
        self, ready_emulator, monkeypatch, tmp_path
    ):
        (tmp_path / "instrumented").symlink_to(
            game.OUTPUT / "instrumented", target_is_directory=True
        )
        monkeypatch.setattr(game, "OUTPUT", tmp_path)
        game.run_case("coco1", inject=False)
        output = game.OUTPUT / "coco1-normal-idle"
        assert json.loads((output / "result.json").read_text())["status"] == "passed"
        monkeypatch.setenv("LWASM", "/nonexistent/collect-room-assembler")

        with pytest.raises((OSError, ValueError, subprocess.CalledProcessError)):
            game.run_case("coco1", inject=False)

        assert json.loads((output / "result.json").read_text())["status"] == "failed"
        assert not list(output.glob("frame-*.ram"))
        assert not (output / "game.bin").exists()

    def should_reject_broken_audio_routing(self):
        log = "\n".join(f"DAC,{i},3103,{v:02x},04,fc,0c,04,0c" for i, v in enumerate([252, 0] * 16))
        with pytest.raises(ValueError, match="routing"):
            game.audio_evidence(log, {"dac_write": 0x3100}, 1)


class DescribeAssetsAndBuild:
    def should_pack_boundary_pixels_and_row_repetition(self):
        assert game.expand(bytes.fromhex("8101")) == bytes.fromhex("c003c00300030003")
        assert game.headers()[:4] == bytes.fromhex("00007bc7")

    def should_reject_changed_art_before_publishing_a_binary(self, tmp_path, monkeypatch):
        monkeypatch.setattr(game, "ART", (bytes(8),) + game.ART[1:])
        (tmp_path / "game.bin").write_bytes(b"old")
        with pytest.raises(ValueError, match="Terrain art changed"):
            game.build(tmp_path)
        assert not (tmp_path / "game.bin").exists()

    def should_reject_an_unknown_mutation(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown mutation"):
            game.build(tmp_path, "typo")

    def should_fail_closed_on_an_unrecognized_source_anchor(self, tmp_path):
        path = tmp_path / "source.c"
        path.write_text("original\n")
        with pytest.raises(ValueError, match="anchor"):
            game.patch_once(path, "missing", "replacement")
        assert path.read_text() == "original\n"

    def should_reject_changed_instrumentation(self, tmp_path, monkeypatch, ready_emulator):
        work = tmp_path / "instrumented"
        (work / "xroar-1.12.1/src").mkdir(parents=True)
        (work / "xroar-1.12.1/src/xroar").write_bytes(b"wrong")
        shutil.copy(game.OUTPUT / "instrumented/build.json", work / "build.json")
        monkeypatch.setattr(game, "OUTPUT", tmp_path)
        with pytest.raises(ValueError, match="emulator changed"):
            game.checked_emulator()

    def should_reject_corrupt_downloads_without_extracting(self, tmp_path, monkeypatch):
        work = tmp_path / "instrumented"
        work.mkdir()
        (work / "xroar-1.12.1.tar.gz").write_bytes(b"wrong archive")
        monkeypatch.setattr(game, "OUTPUT", tmp_path)
        with pytest.raises(ValueError, match="checksum"):
            game.prepare_emulator()
        assert not (work / "xroar-1.12.1").exists()


class DescribeLaunchBoundary:
    @pytest.mark.parametrize(
        "args, code", [(["--help"], 0), (["typo"], 2), (["run", "--target", "coco3"], 2)]
    )
    def should_parse_before_any_process_or_download(self, monkeypatch, args, code):
        process = Mock(side_effect=AssertionError("unexpected process"))
        download = Mock(side_effect=AssertionError("unexpected download"))
        monkeypatch.setattr(game.subprocess, "run", process)
        monkeypatch.setattr(game.urllib.request, "urlopen", download)
        monkeypatch.setattr(sys, "argv", ["collect_room.py", *args])
        with pytest.raises(SystemExit) as result:
            game.main()
        assert result.value.code == code
        process.assert_not_called()
        download.assert_not_called()

    @pytest.mark.parametrize("condition", ["missing", "partial", "corrupt"])
    def should_reject_unusable_firmware(self, tmp_path, monkeypatch, condition):
        shutil.copy(game.ROOT / "roms.json", tmp_path / "roms.json")
        firmware = tmp_path / "local/roms/coco1"
        firmware.mkdir(parents=True)
        if condition != "missing":
            shutil.copy(game.ROOT / "local/roms/coco1/bas11.rom", firmware)
        if condition == "corrupt":
            source = (game.ROOT / "local/roms/coco1/extbas10.rom").read_bytes()
            (firmware / "extbas10.rom").write_bytes(bytes(len(source)))
        monkeypatch.setattr(game, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="Cannot use coco1 firmware"):
            game.emulator("coco1", "unused-xroar")

    def should_supply_isolated_explicit_configuration(self):
        command = game.emulator("coco2", "chosen-xroar")
        assert command[:4] == ["chosen-xroar", "-no-c", "-machine", "coco2bus"]
        for option, value in (
            ("-ram", "32"),
            ("-machine-cpu", "6809"),
            ("-tv-type", "ntsc"),
            ("-vdg-type", "6847"),
        ):
            assert command[command.index(option) + 1] == value
        assert Path(command[command.index("-bas") + 1]).is_absolute()
        assert Path(command[command.index("-extbas") + 1]).is_absolute()

    @pytest.mark.parametrize("action", ["build", "run"])
    def should_build_and_use_a_recording_launcher_without_a_gui(
        self, tmp_path, monkeypatch, action
    ):
        launcher = tmp_path / "xroar-recorder"
        record = tmp_path / "arguments.txt"
        launcher.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{record}"\n')
        launcher.chmod(0o755)
        monkeypatch.setenv("XROAR", str(launcher))
        monkeypatch.setattr(game, "OUTPUT", tmp_path / "output")
        monkeypatch.setattr(sys, "argv", ["collect_room.py", action, "--target", "coco1"])

        game.main()

        assert (game.OUTPUT / "play/game.bin").stat().st_size > 1000
        if action == "run":
            arguments = record.read_text().splitlines()
            assert "-ratelimit" in arguments
            assert "-no-c" in arguments
            assert arguments[-2:] == ["-run", str(game.OUTPUT / "play/game.bin")]
        else:
            assert not record.exists()
