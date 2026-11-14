"""The keyboard journey runs real game code through an instrumented emulator boundary."""

import json
import shutil
import subprocess
from unittest.mock import Mock

import journey as game
import pytest
from coco import Host, load_expected, parse_symbols
from native import ROOT, tool_path

model = load_expected(game.EXAMPLE)


def ready() -> bool:
    tools = all(tool_path(name) for name in ("lwasm", "xroar"))
    return tools and all((ROOT / "local/roms" / p).is_dir() for p in ("coco1", "coco2"))


@pytest.fixture(scope="module")
def ready_emulator():
    if not ready():
        pytest.skip("Native tools or CoCo 1/2 firmware are not installed")
    return game.prepare_emulator(Host())


@pytest.fixture(scope="module", params=("coco1", "coco2"))
def checked_game(request, ready_emulator):
    return request.param, game.check(Host(), request.param)


def labels() -> dict[str, int]:
    return parse_symbols((ROOT / "build/collect-room/main.sym").read_text())


@pytest.mark.integration
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
        keys, state = model.journey()[75]
        ram = (game.OUTPUT / f"{target}-normal-keys/frame-75.ram").read_bytes()
        symbols = labels()

        assert state[3] == 1 and state[8] == 2
        assert ram[symbols["room"] + 9] == 2
        assert ram[symbols["room"] + 37] == 0
        model.verify_journey_frame(ram, symbols, keys, state)
        with pytest.raises(ValueError, match="Room lifecycle"):
            model.verify_journey_frame(ram, symbols, keys, (*state[:8], 1))

    @pytest.mark.parametrize("damage", ["length", "guard", "map", "screen", "samples", "history"])
    def should_reject_corrupt_evidence(self, checked_game, damage):
        target, _ = checked_game
        symbols = labels()
        ram = bytearray((game.OUTPUT / f"{target}-normal-keys/frame-64.ram").read_bytes())
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
        keys, state = model.journey()[64]

        with pytest.raises(ValueError):
            model.verify_journey_frame(bytes(ram), symbols, keys, state)

    def should_invalidate_a_success_before_a_failed_rerun(
        self, ready_emulator, monkeypatch, tmp_path
    ):
        (tmp_path / "instrumented").symlink_to(
            game.OUTPUT / "instrumented", target_is_directory=True
        )
        monkeypatch.setattr(game, "OUTPUT", tmp_path)
        game.run_case(Host(), "coco1", inject=False)
        output = tmp_path / "coco1-normal-idle"
        assert json.loads((output / "result.json").read_text())["status"] == "passed"
        monkeypatch.setenv("LWASM", "/nonexistent/collect-room-assembler")

        with pytest.raises((OSError, ValueError, subprocess.CalledProcessError)):
            game.run_case(Host(), "coco1", inject=False)

        assert json.loads((output / "result.json").read_text())["status"] == "failed"
        assert not list(output.glob("frame-*.ram"))

    def should_reject_changed_instrumentation(self, tmp_path, monkeypatch, ready_emulator):
        work = tmp_path / "instrumented"
        (work / "xroar-1.12.1/src").mkdir(parents=True)
        (work / "xroar-1.12.1/src/xroar").write_bytes(b"wrong")
        shutil.copy(game.OUTPUT / "instrumented/build.json", work / "build.json")
        monkeypatch.setattr(game, "OUTPUT", tmp_path)

        with pytest.raises(ValueError, match="emulator changed"):
            game.checked_emulator()


class DescribeHarnessBoundaries:
    def should_reject_broken_audio_routing(self):
        log = "\n".join(f"DAC,{i},3103,{v:02x},04,fc,0c,04,0c" for i, v in enumerate([252, 0] * 16))

        with pytest.raises(ValueError, match="routing"):
            game.audio_evidence(log, {"dac_write": 0x3100}, 1)

    def should_reject_wrong_dac_values(self):
        with pytest.raises(ValueError, match="DAC values"):
            game.audio_evidence("DAC,1,3103,fc,04,fc,00,00,08", {"dac_write": 0x3100}, 1)

    def should_measure_routed_bursts(self):
        log = "\n".join(
            f"DAC,{i * 10},3103,{v:02x},04,fc,00,00,08" for i, v in enumerate([252, 0] * 16)
        )

        result = game.audio_evidence(log, {"dac_write": 0x3100}, 1)

        assert result["dac_writes"] == 32
        assert result["within_burst_tick_range"] == [10, 10]

    def should_fail_closed_on_an_unrecognized_source_anchor(self, tmp_path):
        path = tmp_path / "source.c"
        path.write_text("original\n")

        with pytest.raises(ValueError, match="anchor"):
            game.patch_once(path, "missing", "replacement")

        assert path.read_text() == "original\n"

    def should_reject_corrupt_downloads_without_extracting(self, tmp_path, monkeypatch):
        work = tmp_path / "instrumented"
        work.mkdir()
        (work / "xroar-1.12.1.tar.gz").write_bytes(b"wrong archive")
        monkeypatch.setattr(game, "OUTPUT", tmp_path)

        with pytest.raises(ValueError, match="checksum"):
            game.prepare_emulator(Mock(spec=Host))

        assert not (work / "xroar-1.12.1").exists()

    def should_reject_an_unknown_mutation_before_building(self, tmp_path):
        host = Mock(spec=Host)

        with pytest.raises(ValueError, match="Unknown mutation"):
            game.execute_case(host, "coco1", "typo", True, False, tmp_path)

        assert not host.run.called

    def should_inject_keys_only_when_asked(self, tmp_path):
        symbols = {"frame_ready": 0x3010, "sample": 0x3020}

        idle = game.capture_environment(symbols, tmp_path, 5, False)
        keys = game.capture_environment(symbols, tmp_path, 5, True)

        assert "COLLECT_EVENTS" not in idle and idle["COLLECT_FRAME_COUNT"] == "5"
        assert keys["COLLECT_KEY_TRAP"] == "pc=0x3020"

    @pytest.mark.parametrize("args, code", [(["--help"], 0), (["typo"], 2)])
    def should_parse_before_any_process_or_download(self, args, code):
        host = Mock(spec=Host)

        with pytest.raises(SystemExit) as result:
            game.main(args, host)

        assert result.value.code == code
        assert not host.method_calls
