"""The cooperative experiment has reproducible machine-level evidence."""

from pathlib import Path

import pytest
import sound_slots


class DescribeSoundSlots:
    @pytest.mark.integration
    def should_run_both_input_paths_and_check_native_machine_evidence(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        from native import tool_path

        if not all(tool_path(name) for name in ("lwasm", "xroar")):
            pytest.skip("Native tools are not installed")
        if not (sound_slots.ROOT / "local/roms/coco1/bas11.rom").exists():
            pytest.skip("CoCo 1 firmware is not provisioned")
        monkeypatch.setattr("sys.argv", ["sound_slots.py", "check"])

        sound_slots.main()

        assert "PASS: exact DAC sequence" in capsys.readouterr().out
        binary, symbols = sound_slots.build(True)
        snapshot = binary.with_name("scripted-64.ram").read_bytes()
        for address in (0x03FF, 0x1C00, 0x1000, symbols["frames"], symbols["button"]):
            broken = bytearray(snapshot)
            broken[address] ^= 1
            with pytest.raises(ValueError):
                sound_slots.verify_ram(broken, symbols, 64, True)
        trace = binary.with_suffix(".trace").read_text()
        with pytest.raises(ValueError, match="DAC"):
            sound_slots.verify_trace(trace[: len(trace) // 2], symbols["sample"], True)

    def should_reject_missing_machine_evidence(self) -> None:
        with pytest.raises(ValueError, match="RAM"):
            sound_slots.verify_ram(b"", {}, 1, False)
        with pytest.raises(ValueError, match="DAC"):
            sound_slots.verify_trace("", 0x3000, False)

    def should_preserve_launch_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Missing firmware must fail before an interactive emulator launch.
        monkeypatch.setattr("sys.argv", ["sound_slots.py", "run"])
        monkeypatch.setattr(sound_slots, "build", lambda: (Path("missing.bin"), {}))

        def unavailable(binary: Path) -> list[str]:
            raise ValueError("Missing firmware")

        monkeypatch.setattr(sound_slots, "emulator", unavailable)
        with pytest.raises(ValueError, match="Missing firmware"):
            sound_slots.main()
