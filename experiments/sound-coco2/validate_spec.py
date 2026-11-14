"""Real headless experiment and damaged-evidence rejection checks."""

import json
import re
import sys
from pathlib import Path

import pytest
import validate


@pytest.fixture(scope="module")
def evidence(tmp_path_factory):
    output = tmp_path_factory.mktemp("sound") / "run"
    xroar = validate.ROOT / "local/research/sound-coco2/xroar-1.12.1/src/xroar"
    old = sys.argv
    sys.argv = ["validate", "--xroar", str(xroar), "--output", str(output)]
    try:
        validate.main()
    finally:
        sys.argv = old
    return output


def saved(output, name="scripted", frame=64):
    folder = output / name
    syms = {
        k: int(v, 16)
        for k, v in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9a-fA-F]+)", (folder / "program.sym").read_text(), re.MULTILINE
        )
    }
    return (folder / f"{frame}.log").read_text(), (folder / f"{frame}.ram").read_bytes(), syms


class DescribeCoCo2:
    def should_complete_real_sample_input_and_drawing_runs(self, evidence):
        results = json.loads((evidence / "results.json").read_text())
        validate.controls(results)
        assert results["released"]["samples"] == 16384
        assert results["scripted"]["frames"] == 64

    @pytest.mark.parametrize(
        "damage",
        [
            "empty",
            "value",
            "pia",
            "ticks",
            "ram",
            "guard",
            "button",
            "pitch",
            "screen",
            "frame",
            "negative",
        ],
    )
    def should_reject_damaged_evidence(self, evidence, damage):
        log, original, syms = saved(evidence)
        ram = bytearray(original)
        if damage in ("empty", "value", "pia", "ticks"):
            lines = log.splitlines()
            rows = [
                i
                for i, line in enumerate(lines)
                if line.startswith("AT,") and int(line.split(",")[2], 16) == syms["sample"] + 3
            ]
            if damage == "empty":
                lines = [line for line in lines if not line.startswith("AT,")]
            else:
                row = lines[rows[1]].split(",")
                if damage == "value":
                    row[3] = "fc"
                elif damage == "pia":
                    row[4] = "00"
                else:
                    row[1] = str(int(row[1]) + 1)
                lines[rows[1]] = ",".join(row)
            log = "\n".join(lines)
        elif damage == "ram":
            ram = ram[:32768]
        elif damage != "negative":
            address = {
                "guard": 0x3FF,
                "button": syms["button"],
                "pitch": syms["pitch"],
                "screen": 0x400,
                "frame": syms["frames"],
            }[damage]
            ram[address] ^= 1

        with pytest.raises((AssertionError, ValueError)):
            validate.analyze(log, bytes(ram), syms, 64, True, damage == "negative")

    def should_reject_missing_delay(self, evidence):
        results = json.loads((evidence / "results.json").read_text())
        results["delayed"] = results["scripted"]

        with pytest.raises(AssertionError, match="delayed-work"):
            validate.controls(results)

    def should_refuse_existing_output(self, evidence):
        with pytest.raises(FileExistsError):
            validate.run(Path("/unused"), evidence)

    def should_handle_tick_wrap_and_ignore_other_callbacks(self, evidence):
        log, ram, syms = saved(evidence)
        first = validate.samples(log, syms["sample"])[0][0]
        lines = []
        for line in log.splitlines():
            if line.startswith("AT,"):
                row = line.split(",")
                row[1] = str((int(row[1]) - first - 16) & 0xFFFFFFFF)
                line = ",".join(row)
            lines.append(line)
        lines.append("AT,0,1000,00,00,00")

        before = validate.analyze(log, ram, syms, 64, True, False)
        after = validate.analyze("\n".join(lines), ram, syms, 64, True, False)
        assert after == before

    def should_reject_uninstrumented_emulator(self, tmp_path):
        emulator = validate.tool_path("xroar")
        assert emulator, "installed XRoar required for missing-instrumentation control"
        with pytest.raises(AssertionError, match="DAC sequence"):
            validate.run_case(Path(emulator), tmp_path / "uninstrumented", False, False)

    def should_report_missing_assembler(self, tmp_path, monkeypatch):
        monkeypatch.setattr(validate, "tool_path", lambda name: None)
        with pytest.raises(ValueError, match="LWASM"):
            validate.assemble(tmp_path, False, False)

    def should_print_help_without_creating_output(self, tmp_path, monkeypatch, capsys):
        output = tmp_path / "absent"
        monkeypatch.setattr(sys, "argv", ["validate", "--output", str(output), "--help"])
        with pytest.raises(SystemExit) as result:
            validate.main()
        assert result.value.code == 0
        assert "Private DAC-instrumented" in capsys.readouterr().out
        assert not output.exists()


class DescribeBoundaryTiming:
    def should_reject_offsetting_errors_at_adjacent_boundaries(self, evidence):
        results = json.loads((evidence / "results.json").read_text())
        log, ram, syms = saved(evidence, "delayed")
        lines = log.splitlines()
        rows = [
            i
            for i, line in enumerate(lines)
            if line.startswith("AT,") and int(line.split(",")[2], 16) == syms["sample"] + 3
        ]
        for index in rows[256:512]:
            row = lines[index].split(",")
            row[1] = str(int(row[1]) + 16)
            lines[index] = ",".join(row)
        changed = validate.analyze("\n".join(lines), ram, syms, 64, True, False)
        assert changed["span_ticks"] == results["delayed"]["span_ticks"]
        results["delayed"] = changed
        with pytest.raises(AssertionError, match="boundary delay budget"):
            validate.controls(results)
