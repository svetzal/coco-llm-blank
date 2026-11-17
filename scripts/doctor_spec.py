"""Executable discovery uses real files and never runs the discovered programs."""

import subprocess
import sys
from pathlib import Path

import doctor
import pytest


@pytest.fixture
def tool_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PATH", str(tmp_path))
    variables = {command: doctor.VARIABLES[command] for command in doctor.TOOLS}
    for command, variable in (variables | {"xroar": "XROAR"}).items():
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

    def should_fail_target_check_until_firmware_is_verified(
        self, tool_directory: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        import hashlib
        import json

        monkeypatch.setattr(doctor, "ROOT", tool_directory)
        data = b"original firmware fixture"
        profile = {
            "url": "https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/test.zip",
            "sha256": "0" * 64,
            "members": [
                {"name": "basic.rom", "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            ],
        }
        (tool_directory / "roms.json").write_text(json.dumps({"coco2": profile}))
        assert doctor.main(["--profile", "demo", "--target", "coco2"]) == 1
        assert "--target coco2 --roms-only" in capsys.readouterr().out
        rom = tool_directory / "local/roms/coco2/basic.rom"
        rom.parent.mkdir(parents=True)
        rom.write_bytes(data)

        assert doctor.main(["--profile", "demo", "--target", "coco2"]) == 0
        assert "Firmware verified" in capsys.readouterr().out
        rom.write_bytes(b"x" * len(data))
        assert doctor.main(["--profile", "demo", "--target", "coco2"]) == 1
        assert "checksum mismatch" in capsys.readouterr().out

    def should_require_the_xroar_build(
        self, tool_directory: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        monkeypatch.setattr(doctor, "ROOT", tool_directory)
        monkeypatch.delenv("XROAR")

        assert doctor.main(["--profile", "demo"]) == 1

        output = capsys.readouterr().out
        line = next(text for text in output.splitlines() if text.startswith("xroar:"))
        assert "not built yet" in line and "missing cc" in line
        assert "scripts/instrumented_xroar.py build" in line
        assert "Setup is incomplete. Ask your agent to install: xroar" in output

    def should_report_an_xroar_named_by_the_override(
        self, tool_directory: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert doctor.main(["--profile", "demo"]) == 0

        assert f"xroar: {tool_directory / 'xroar'} (named by XROAR" in capsys.readouterr().out

        (tool_directory / "xroar").unlink()

        assert doctor.main(["--profile", "demo"]) == 1
