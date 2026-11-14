"""Timer audio keeps its throughput under real emulated redraw work."""

import json

import pytest
import timer_sound
from native import ROOT, tool_path


class DescribeTimerSound:
    @pytest.mark.integration
    def should_measure_both_revisions_and_detect_a_missing_acknowledgement(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        if not all(tool_path(name) for name in ("lwasm", "xroar")):
            pytest.skip("Native tools are not installed")
        if not (ROOT / "local/roms/coco3/coco3.rom").exists():
            pytest.skip("CoCo 3 firmware is not provisioned")
        monkeypatch.setattr("sys.argv", ["timer_sound.py", "check"])

        timer_sound.main()

        assert "PASS: timer throughput" in capsys.readouterr().out
        results = json.loads((ROOT / "build/timer-sound/results.json").read_text())
        assert len(results) == 6
        with pytest.raises(ValueError, match="completed frame"):
            timer_sound.measure(True, False, 1986, no_ack=True)
        binary, symbols = timer_sound.build(True, True)
        data = binary.with_name("timer-heavy-1986.ram").read_bytes()
        for address in (0x3FF, 0x1C00, 0x1000, symbols["samples"] + 1, symbols["position"]):
            broken = bytearray(data)
            broken[timer_sound.RAM_BASE + address] ^= 1
            with pytest.raises(ValueError):
                timer_sound.verify_frame(broken, symbols)

    @pytest.mark.parametrize("trace", ["", "3000| STA $ff20 a=10 b=00"])
    def should_reject_a_missing_or_wrong_sample(self, trace: str) -> None:
        with pytest.raises(ValueError, match="DAC"):
            timer_sound.sample_count(trace, 0x3000)

    def should_reject_incomplete_memory(self) -> None:
        with pytest.raises(ValueError, match="128 KiB"):
            timer_sound.verify_frame(bytes(32768), {})

    def should_explain_missing_firmware(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(timer_sound, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="firmware"):
            timer_sound.emulator(1986)

    @pytest.mark.parametrize("fault", ["clock", "foreground", "cooperative"])
    def should_reject_a_comparison_without_the_claimed_behaviour(self, fault: str) -> None:
        results = {
            "timer-light-1986": {"samples_in_one_emulated_second": 6992, "completed_redraws": 27},
            "timer-heavy-1986": {"samples_in_one_emulated_second": 6992, "completed_redraws": 2},
            "timer-light-1987": {"samples_in_one_emulated_second": 7005, "completed_redraws": 27},
            "timer-heavy-1987": {"samples_in_one_emulated_second": 7005, "completed_redraws": 2},
            "cooperative-light-1986": {"samples_in_one_emulated_second": 12746},
            "cooperative-heavy-1986": {"samples_in_one_emulated_second": 2508},
        }
        if fault == "clock":
            results["timer-heavy-1986"]["samples_in_one_emulated_second"] *= 4
        elif fault == "foreground":
            results["timer-heavy-1987"]["completed_redraws"] = 27
        else:
            results["cooperative-heavy-1986"]["samples_in_one_emulated_second"] = 12000

        with pytest.raises(ValueError):
            timer_sound.compare(results)
