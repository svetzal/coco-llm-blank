"""Throughput claims come from real emulated seconds and reject false controls."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import throughput
from coco import Host
from native import ROOT, tool_path

TIMER_RESULTS = {
    "timer-light-1986": {"samples_in_one_emulated_second": 6992, "completed_redraws": 27},
    "timer-heavy-1986": {"samples_in_one_emulated_second": 6992, "completed_redraws": 2},
    "timer-light-1987": {"samples_in_one_emulated_second": 7005, "completed_redraws": 27},
    "timer-heavy-1987": {"samples_in_one_emulated_second": 7005, "completed_redraws": 2},
    "cooperative-light-1986": {"samples_in_one_emulated_second": 12746},
    "cooperative-heavy-1986": {"samples_in_one_emulated_second": 2508},
}


def ready() -> bool:
    tools = all(tool_path(name) for name in ("lwasm", "xroar"))
    return tools and all((ROOT / "local/roms" / p).is_dir() for p in ("coco1", "coco3"))


class DescribeThroughput:
    @pytest.mark.parametrize("trace", ["", "3000| STA $ff20 a=10 b=00"])
    def should_reject_a_missing_or_wrong_sample(self, trace: str) -> None:
        with pytest.raises(ValueError, match="DAC"):
            throughput.sample_count(trace, 0x3000)

    def should_count_a_correct_phase_sequence(self) -> None:
        trace = "3000| STA $ff20 a=08 b=00\n3000| STA $ff20 a=10 b=00\n"

        assert throughput.sample_count(trace, 0x3000) == 2

    def should_accept_the_predicted_comparison(self) -> None:
        throughput.compare(json.loads(json.dumps(TIMER_RESULTS)))

    @pytest.mark.parametrize("fault", ["clock", "foreground", "cooperative"])
    def should_reject_a_comparison_without_the_claimed_behaviour(self, fault: str) -> None:
        results = json.loads(json.dumps(TIMER_RESULTS))
        if fault == "clock":
            results["timer-heavy-1986"]["samples_in_one_emulated_second"] *= 4
        elif fault == "foreground":
            results["timer-heavy-1987"]["completed_redraws"] = 27
        else:
            results["cooperative-heavy-1986"]["samples_in_one_emulated_second"] = 12000

        with pytest.raises(ValueError):
            throughput.compare(results)

    def should_trace_one_second_after_the_first_sample(self) -> None:
        symbols = {"state": 0x3100, "sample": 0x3050, "frame_ready": 0x3080}

        options = " ".join(throughput.window_options(symbols, Path("s.ram"), True))

        assert "-ram-init set" in options
        assert "-trap pc=0x3100 -trap-snap s.ram.bad" in options
        assert "-trap pc=0x3050 -trap-range 1-1 -trap-timeout 1 -trap-trace" in options
        assert options.endswith("-trap pc=0x3080 -trap-range 1- -trap-snap s.ram")

    def should_stop_when_the_emulator_cannot_run(self) -> None:
        host = Mock(spec=Host)
        host.executable.return_value = "/usr/bin/false"
        host.firmware.side_effect = lambda profile, names: {n: Path(n) for n in names}
        host.run.side_effect = ValueError("assembler unavailable")

        with pytest.raises(ValueError, match="assembler unavailable"):
            throughput.sound_slots_second(host)

    @pytest.mark.integration
    def should_measure_both_examples_and_reject_a_missing_acknowledgement(self, capsys) -> None:
        if not ready():
            pytest.skip("Native tools or CoCo 1/3 firmware are not installed")

        assert throughput.main(["check"]) == 0

        report = json.loads((throughput.OUTPUT / "results.json").read_text())
        assert report["sound_slots"]["complete_frames_in_one_emulated_second"] == 60
        assert len(report["timer_sound"]) == 6
        assert report["timer_without_acknowledgement"].startswith("rejected")
        assert "PASS" in capsys.readouterr().out

    @pytest.mark.integration
    def should_reject_a_damaged_real_snapshot(self) -> None:
        if not ready():
            pytest.skip("Native tools or CoCo 3 firmware are not installed")
        data, _, symbols = throughput.one_second(throughput.TIMER_SOUND, Host(), None, "timer")
        model = throughput.load_expected(throughput.TIMER_SOUND)
        base = model.RAM_BASE

        for address in (0x3FF, 0x1C00, 0x1000, symbols["samples"] + 1, symbols["position"]):
            broken = bytearray(data)
            broken[base + address] ^= 1
            with pytest.raises(ValueError):
                model.verify_frame(broken, symbols)
