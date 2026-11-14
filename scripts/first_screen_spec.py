"""The screen oracle rejects startup RAM and incorrect pixels."""

from pathlib import Path
from unittest.mock import Mock

import first_screen
import pytest


class DescribeFirstScreen:
    def should_check_exact_pixel_positions(self) -> None:
        screen = first_screen.expected_screen()
        assert len(screen) == 6144
        assert screen[:32] == b"\xff" * 32
        assert screen[-32:] == b"\xff" * 32
        assert screen[32:64] == b"\x80" + b"\0" * 30 + b"\x01"
        assert screen[64 * 32 + 12 : 64 * 32 + 20] == b"\xff" * 8
        assert screen[128 * 32 + 12 : 128 * 32 + 20] == b"\0" * 8
        ram = bytearray(32768)
        ram[0x2FFF] = 0xA5
        ram[0x400:0x1C00] = screen
        first_screen.verify_ram(ram)
        ram[0xC0C] = 0
        with pytest.raises(ValueError, match="screen bytes"):
            first_screen.verify_ram(ram)

    @pytest.mark.parametrize("data", [b"", bytes(32768)])
    def should_reject_startup_memory(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="initialized"):
            first_screen.verify_ram(data)

    def should_explain_missing_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(first_screen, "tool_path", lambda name: None)
        with pytest.raises(ValueError, match=r"uv run python scripts/native\.py"):
            first_screen.executable("lwasm")

    def should_explain_missing_firmware(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(first_screen, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="roms-only"):
            first_screen.emulator(tmp_path / "demo.bin")

    def should_reject_a_build_without_a_checkpoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(first_screen, "ROOT", tmp_path)
        monkeypatch.setattr(first_screen, "executable", lambda name: name)

        def assemble(command, **kwargs):
            (tmp_path / "build/first-screen/symbols.txt").write_text("no checkpoint")

        monkeypatch.setattr(first_screen.subprocess, "run", Mock(side_effect=assemble))
        with pytest.raises(ValueError, match="checkpoint"):
            first_screen.build()

    @pytest.mark.integration
    def should_build_and_check_the_real_program_in_xroar(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        if not all(first_screen.tool_path(name) for name in ("lwasm", "xroar")):
            pytest.skip("Native tools are not installed")
        if not (first_screen.ROOT / "local/roms/coco1/bas11.rom").exists():
            pytest.skip("CoCo 1 firmware is not provisioned")
        monkeypatch.setattr("sys.argv", ["first_screen.py", "check"])
        first_screen.main()
        assert "PASS: XRoar reached ready" in capsys.readouterr().out
        monkeypatch.setattr("sys.argv", ["first_screen.py", "build"])
        first_screen.main()
        assert "first-screen.bin" in capsys.readouterr().out

    def should_launch_the_built_binary_at_normal_speed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        binary = tmp_path / "screen.bin"
        monkeypatch.setattr(first_screen, "build", lambda: (binary, 0x3000))
        monkeypatch.setattr(first_screen, "emulator", lambda path: ["xroar"])
        process = Mock()
        monkeypatch.setattr(first_screen.subprocess, "run", process)
        monkeypatch.setattr("sys.argv", ["first_screen.py", "run"])
        first_screen.main()
        process.assert_called_once_with(["xroar", "-ratelimit", "-run", str(binary)], check=True)

    def should_reject_a_stale_or_unreachable_snapshot(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(first_screen, "emulator", lambda binary: ["xroar"])
        ram = bytearray(32768)
        ram[0x2FFF] = 0xA5
        ram[0x400:0x1C00] = first_screen.expected_screen()

        def snapshot(command, **kwargs):
            Path(command[command.index("-trap-snap") + 1]).write_bytes(ram)

        monkeypatch.setattr(first_screen.subprocess, "run", Mock(side_effect=snapshot))
        with pytest.raises(ValueError, match="unreachable"):
            first_screen.check(tmp_path / "demo.bin", 0x3000)
