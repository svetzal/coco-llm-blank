"""Executable discovery uses real files and never runs the discovered programs."""

import subprocess
import sys
from pathlib import Path

import doctor
import pytest


@pytest.fixture
def tool_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PATH", str(tmp_path))
    for command, (variable, _) in doctor.TOOLS.items():
        monkeypatch.setenv(variable, str(tmp_path / command))
        executable = tmp_path / command
        executable.write_text("#!/bin/sh\nexit 99\n")
        executable.chmod(0o755)
    return tmp_path


class DescribeToolchainDoctor:
    def should_report_available_executables(
        self, tool_directory: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert doctor.main([]) == 0
        assert str(tool_directory / "lwasm") in capsys.readouterr().out

    def should_report_a_missing_tool(
        self, tool_directory: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tool_directory / "decb").unlink()

        assert doctor.main([]) == 1
        assert "decb: missing" in capsys.readouterr().out

    def should_respect_an_explicit_executable_override(
        self, tool_directory: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        alternate = tool_directory / "alternate-decb"
        (tool_directory / "decb").rename(alternate)
        monkeypatch.setenv("DECB", str(alternate))

        assert doctor.main([]) == 0

        alternate.chmod(0o644)

        assert doctor.main([]) == 1

    def should_run_the_script_entry_point(self, tool_directory: Path) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(doctor.__file__))],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert str(tool_directory / "xroar") in result.stdout

    def should_not_require_disk_tools_for_a_direct_demo(
        self, tool_directory: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tool_directory / "decb").unlink()

        assert doctor.main(["--profile", "demo"]) == 0
        assert "Optional for this demo" in capsys.readouterr().out

    def should_explain_missing_required_demo_tools(
        self, tool_directory: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tool_directory / "lwasm").unlink()

        assert doctor.main(["--profile", "demo"]) == 1
        assert "Setup is incomplete. Ask your agent to install: lwasm" in capsys.readouterr().out
