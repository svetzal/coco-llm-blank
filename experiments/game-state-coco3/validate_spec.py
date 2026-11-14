"""Behavior at the assembly/emulator and capture-verification boundaries."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import validate
from vectors import fixtures, require_host_agreement


class DescribeMachineExecution:
    @pytest.mark.parametrize("capacity", (128, 512))
    def should_match_every_literal_checkpoint(self, evidence, capacity):
        run = next(
            r for r in evidence["runs"] if r["variant"] == "correct" and r["ram_kib"] == capacity
        )

        assert run["mismatches"] == []
        assert evidence["checkpoints"] == 44
        assert evidence["cases"] == 19

    @pytest.mark.parametrize("variant", tuple(validate.WITNESSES))
    def should_detect_each_executed_fault_on_both_machines(self, evidence, variant):
        runs = [r for r in evidence["runs"] if r["variant"] == variant]

        assert {r["ram_kib"] for r in runs} == {128, 512}
        for run in runs:
            assert any(f.startswith(validate.WITNESSES[variant]) for f in run["mismatches"])

    def should_cross_check_literal_values_with_existing_host_model(self):
        require_host_agreement(fixtures())

    def should_reject_a_literal_expectation_changed_to_match_a_fault(self):
        cases = fixtures()
        cases[0].steps[0].expected = cases[0].initial

        with pytest.raises(AssertionError, match="queue-lifecycle"):
            require_host_agreement(cases)


class DescribeEvidenceValidation:
    @pytest.mark.parametrize(
        "address", (0x40FF, 0x4111, 0x41FF, 0x420C, 0x4FFF, 0x5000 + 44 * 19, 0x7DFF, 0x7F00)
    )
    def should_reject_corrupted_guards(self, good_capture, address):
        capture = bytearray(good_capture)
        capture[len(capture) - 65536 + address] ^= 1

        with pytest.raises(ValueError, match="guard damaged"):
            validate.assess(bytes(capture), 128, fixtures())

    def should_reject_startup_memory(self, good_capture):
        capture = bytearray(good_capture)
        capture[len(capture) - 65536 + 0x420B] = 0

        with pytest.raises(ValueError, match="Completion marker"):
            validate.assess(bytes(capture), 128, fixtures())

    def should_reject_wrong_capture_size(self, good_capture):
        with pytest.raises(ValueError, match="capture size"):
            validate.assess(good_capture[:-1], 128, fixtures())

    def should_reject_good_build_with_bad_state(self, good_capture):
        capture = bytearray(good_capture)
        capture[len(capture) - 65536 + 0x5005] ^= 1
        failures = validate.assess(bytes(capture), 128, fixtures())

        with pytest.raises(ValueError, match="queue-lifecycle:0"):
            validate.require_result("correct", failures)

    @pytest.mark.parametrize("variant", tuple(validate.WITNESSES))
    def should_fail_when_faulty_control_is_not_detected(self, variant):
        with pytest.raises(ValueError, match="escaped detection"):
            validate.require_result(variant, [])

    @pytest.mark.parametrize("mode", ("missing", "short", "corrupt"))
    def should_refuse_unverified_firmware_before_emulation(self, tmp_path, monkeypatch, mode):
        (tmp_path / "roms.json").write_bytes((validate.ROOT / "roms.json").read_bytes())
        rom = tmp_path / "local/roms/coco3/coco3.rom"
        rom.parent.mkdir(parents=True)
        if mode != "missing":
            rom.write_bytes(bytes(32768 if mode == "corrupt" else 1))
        monkeypatch.setattr(validate, "ROOT", tmp_path)

        with pytest.raises(ValueError, match="Cannot use coco3 firmware"):
            validate.capture(tmp_path, 128, tmp_path / "never.bin", {})
        assert not list(tmp_path.glob("*.log"))

    def should_detect_a_reachable_negative_trap(self, tmp_path, evidence):
        run = evidence["runs"][0]
        binary = Path(run["snapshot"]).parent / "state.bin"
        # Deliberately attach the forbidden trap to actual entry.
        with pytest.raises(ValueError, match="Unreachable data trap fired"):
            validate.capture(tmp_path, 128, binary, {"unreachable": 0x3000, "finished": 0x3000})

    @pytest.mark.parametrize("args,code", ((["--help"], 0), (["--unknown"], 2)))
    def should_parse_cli_without_native_tools_or_output(self, tmp_path, args, code):
        env = dict(os.environ, LWASM="/missing/lwasm", XROAR="/missing/xroar")
        result = subprocess.run(
            [
                sys.executable,
                str(validate.HERE / "validate.py"),
                "--output",
                str(tmp_path / "unused"),
                *args,
            ],
            check=False,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

        assert result.returncode == code
        assert not (tmp_path / "unused").exists()

    def should_leave_incomplete_report_if_oracle_validation_fails(self, tmp_path, monkeypatch):
        cases = fixtures()
        cases[0].steps[0].expected = cases[0].initial
        monkeypatch.setattr(validate, "fixtures", lambda: cases)

        with pytest.raises(AssertionError):
            validate.check(tmp_path)
        assert json.loads((tmp_path / "results.json").read_text())["passed"] is False

    def should_fail_with_missing_assembler(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LWASM", str(tmp_path / "absent-lwasm"))

        with pytest.raises(RuntimeError, match="Missing required native tool: lwasm"):
            validate.assemble(tmp_path, "correct", fixtures())
        assert not (tmp_path / "state.bin").exists()

    def should_refuse_fixture_growth_past_evidence_allocation(self, tmp_path):
        from vectors import Case, State, Step

        case = Case(
            name="oversized",
            initial=State(),
            steps=tuple(Step(action="end_commands", expected=State()) for _ in range(220)),
        )

        with pytest.raises(ValueError, match="allocated memory"):
            validate.assemble(tmp_path, "correct", [case])
        assert not list(tmp_path.glob("*.ram"))


class DescribePartialEvidence:
    def should_retain_actual_capture_and_mismatch_before_raising(self, tmp_path, monkeypatch):
        original = validate.assess

        def mismatching_capture(raw, capacity, cases):
            original(raw, capacity, cases)
            return ["injected checkpoint mismatch"]

        monkeypatch.setattr(validate, "assess", mismatching_capture)
        with pytest.raises(ValueError, match="injected checkpoint mismatch"):
            validate.check(tmp_path)
        report = json.loads((tmp_path / "results.json").read_text())
        assert report["passed"] is False
        assert report["status"] == "failed"
        assert report["runs"][0]["mismatches"] == ["injected checkpoint mismatch"]
        assert Path(report["runs"][0]["snapshot"]).is_file()
        assert report["tools"] and report["source_sha256"]
        assert "injected checkpoint mismatch" in report["failure"]["traceback"]
