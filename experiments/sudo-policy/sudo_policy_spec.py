"""Fail closed when the production extraction boundary changes."""

import subprocess
from pathlib import Path

import pytest
from sudo_policy import BOUNDARY, NOTES, Experiment, absent_tools, prerequisite_prefix


class DescribePrerequisiteBoundary:
    @pytest.mark.parametrize("source", ["#!/bin/sh\nexit 0\n", BOUNDARY * 2])
    def should_reject_missing_or_ambiguous_boundary(self, source: str) -> None:
        with pytest.raises(ValueError, match="inspect before adapting"):
            prerequisite_prefix(source)

    def should_preserve_real_prefix_and_produce_valid_shell(self, tmp_path: Path) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "scripts/bootstrap.sh").read_text()
        output = tmp_path / "prefix.sh"

        prefix = prerequisite_prefix(source)
        output.write_text(prefix)
        result = subprocess.run(["sh", "-n", str(output)], capture_output=True, check=False)

        assert result.returncode == 0, result.stderr
        assert prefix == source[: source.index(BOUNDARY)] + "    fi\nfi\n"
        assert "apt-get install -y curl ca-certificates" in prefix
        assert "uv sync" not in prefix
        assert "Tools and firmware are ready" not in prefix


class DescribeEvidenceIntegrity:
    @pytest.mark.parametrize("present", ["uv", "xroar", "lwasm", "curl"])
    def should_reject_any_preexisting_tool(self, tmp_path, present):
        executable = tmp_path / present
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        result = subprocess.run(
            ["/bin/sh", "-ec", absent_tools("uv xroar lwasm curl")],
            env={"PATH": str(tmp_path)},
            capture_output=True,
            check=False,
        )
        assert result.returncode == 1
        assert present.encode() in result.stderr

    def should_accept_all_tools_absent(self, tmp_path):
        result = subprocess.run(
            ["/bin/sh", "-ec", absent_tools("uv xroar lwasm curl")],
            env={"PATH": str(tmp_path)},
            check=False,
        )
        assert result.returncode == 0

    def should_reject_newline_changes_and_retain_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()
        monkeypatch.setattr(experiment, "capture", lambda: tmp_path)

        def altered_note(name, label, script, user="root", expected=0):
            (experiment.output / f"{label}.log").write_bytes(NOTES.replace(b"\n", b"\r\n"))
            return NOTES.decode()

        monkeypatch.setattr(experiment, "shell", altered_note)
        monkeypatch.setattr(
            experiment, "journey", lambda policy, inputs: experiment.unchanged(policy, "failed")
        )
        with pytest.raises(AssertionError, match="note bytes changed"):
            experiment.execute()
        import json

        failure = json.loads((experiment.output / "failure.json").read_text())
        assert failure["phase"] == "password"
        assert failure["type"] == "AssertionError"
        assert "Project note bytes changed" in failure["traceback"]
        assert not (experiment.output / "passed.json").exists()
        hashes = json.loads((experiment.output / "hashes.json").read_text())
        assert "failure.json" in hashes
