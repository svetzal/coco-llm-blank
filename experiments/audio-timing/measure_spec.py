"""Fault checks against fresh real emulator evidence, not mocked emulator calls."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import measure
import pytest


@pytest.fixture(params=["slots", "timer86-heavy"])
def evidence(request, tmp_path):
    name = request.param
    log = (measure.OUT / f"{name}.log").read_text()
    symbols = {
        k: int(v, 16)
        for k, v in re.findall(
            r"^(\w+)\s+EQU\s+\$([0-9a-fA-F]+)",
            (measure.OUT / f"{name}.sym").read_text(),
            re.MULTILINE,
        )
    }
    snap = tmp_path / "frame.ram"
    snap.write_bytes((measure.OUT / f"{name}.ram").read_bytes())
    return log, symbols, snap, tmp_path / "unreachable.ram", name == "slots"


def change_record(log, sample, field, value):
    lines = log.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("AT,"):
            parts = line.split(",")
            if int(parts[2], 16) == sample + 3:
                parts[field] = value
                lines[index] = ",".join(parts)
                return "\n".join(lines)
    raise AssertionError("Fixture has no selected DAC record")


class DescribeMeasurement:
    def should_reanalyze_real_evidence(self, evidence):
        result = measure.analyze(*evidence)
        name = "slots" if evidence[-1] else "timer86-heavy"
        expected = json.loads((measure.OUT / f"{name}.json").read_text())
        # JSON object keys are strings; normalize the in-memory histogram.
        assert json.loads(json.dumps(result)) == {key: expected[key] for key in result}

    @pytest.mark.parametrize("field,value", [(3, "fc"), (4, "00"), (5, "00")])
    def should_reject_sample_or_pia_corruption(self, evidence, field, value):
        log, syms, *rest = evidence
        damaged = change_record(log, syms["sample"], field, value)
        with pytest.raises(AssertionError):
            measure.analyze(damaged, syms, *rest)

    def should_reject_missing_samples(self, evidence):
        _, *rest = evidence
        with pytest.raises(AssertionError, match="missing samples"):
            measure.analyze("emulator exited successfully\n", *rest)

    def should_ignore_unrelated_callback_records(self, evidence):
        log, syms, *rest = evidence
        assert measure.analyze("AT,1,0000,ff,00,00\n" + log, syms, *rest) == measure.analyze(
            *evidence
        )

    def should_reject_missing_completion(self, evidence):
        evidence[2].unlink()
        with pytest.raises(AssertionError, match="missing completion snapshot"):
            measure.analyze(*evidence)

    def should_reject_unreachable_snapshot(self, evidence):
        evidence[3].write_bytes(b"unexpected")
        with pytest.raises(AssertionError, match="unreachable trap"):
            measure.analyze(*evidence)

    @pytest.mark.parametrize("damage", ["short", "guard", "marker"])
    def should_reject_damaged_snapshot(self, evidence, damage):
        snap = evidence[2]
        data = bytearray(snap.read_bytes())
        base = 0 if evidence[-1] else 0x10000
        if damage == "short":
            data = data[:100]
        else:
            data[base + (0x3FF if damage == "guard" else 0x400)] ^= 0xFF
        snap.write_bytes(data)
        with pytest.raises((AssertionError, ValueError)):
            measure.analyze(*evidence)

    def should_preserve_histogram_across_unsigned_tick_wrap(self, evidence):
        log, syms, *rest = evidence
        records = measure.records_from_log(log, syms["sample"])
        offset = 0xFFFFFFF0 - records[0][0]
        lines = []
        for line in log.splitlines():
            if line.startswith("AT,"):
                parts = line.split(",")
                parts[1] = str((int(parts[1]) + offset) & 0xFFFFFFFF)
                line = ",".join(parts)
            lines.append(line)
        assert measure.analyze("\n".join(lines), syms, *rest) == measure.analyze(*evidence)

    def should_reject_fractional_cycle_interval(self, evidence):
        log, syms, *rest = evidence
        tick = measure.records_from_log(log, syms["sample"])[0][0]
        damaged = change_record(log, syms["sample"], 1, str(tick + 1))
        with pytest.raises(AssertionError, match="invalid tick intervals"):
            measure.analyze(damaged, syms, *rest)

    def should_check_original_controls_and_repeatability(self):
        measure.check_controls(json.loads((measure.OUT / "results.json").read_text()))

    @pytest.mark.parametrize("index,field", [(7, "min_cycles"), (8, "max_cycles"), (9, "samples")])
    def should_reject_failed_controls(self, index, field):
        results = json.loads((measure.OUT / "results.json").read_text())
        results[index][field] = 0
        with pytest.raises(AssertionError):
            measure.check_controls(results)

    @pytest.mark.parametrize("source", ["missing", "anchor anchor"])
    def should_reject_missing_or_ambiguous_control_anchor(self, source):
        with pytest.raises(ValueError, match="exactly one"):
            measure.replace_once(source, "anchor", "modified")


class DescribeCommandLine:
    @pytest.mark.parametrize(
        "arguments,code,message",
        [
            (["--help"], 0, "--xroar"),
            ([], 2, "required"),
            (["--unknown"], 2, "error"),
            (["--xroar", "/nonexistent/private-xroar"], 2, "not executable"),
        ],
    )
    def should_parse_before_running_any_case(self, tmp_path, arguments, code, message):
        result = subprocess.run(
            [sys.executable, str(Path(measure.__file__).resolve()), *arguments],
            cwd=tmp_path,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == code
        assert message in result.stdout + result.stderr
        assert not list(tmp_path.iterdir())

    def should_reject_optimized_python(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-O", str(Path(measure.__file__).resolve()), "--xroar", "unused"],
            cwd=tmp_path,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 2
        assert "requires assertions" in result.stderr
