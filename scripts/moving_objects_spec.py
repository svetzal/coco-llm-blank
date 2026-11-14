"""Moving objects restore scenery and remain bounded on real emulated machines."""

from pathlib import Path

import moving_objects
import pytest


class DescribeMovingObjects:
    @pytest.mark.parametrize("target", ("coco1", "coco2"))
    @pytest.mark.integration
    def should_render_overlap_edges_and_changed_scenery_in_xroar(
        self, target: str, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        from native import tool_path

        if not all(tool_path(name) for name in ("lwasm", "xroar")):
            pytest.skip("Native tools are not installed")
        if not (
            moving_objects.ROOT / "local/roms" / target / moving_objects.ROM_NAMES[target][0]
        ).exists():
            pytest.skip(f"{target} firmware is not provisioned")
        monkeypatch.setattr("sys.argv", ["moving_objects.py", "check", "--target", target])

        moving_objects.main()

        assert f"PASS: {target}" in capsys.readouterr().out
        _, symbols = moving_objects.build()
        ram = (moving_objects.ROOT / f"build/moving-objects/{target}-16.ram").read_bytes()
        for address in (
            0x03FF,
            0x1C00,
            0x0400,
            symbols["frames"],
            symbols["xpos"],
            symbols["ypos"],
        ):
            damaged = bytearray(ram)
            damaged[address] ^= 1
            with pytest.raises(ValueError):
                moving_objects.verify_ram(damaged, symbols, 16)

    def should_specify_both_overlap_orders_and_background_change(self) -> None:
        # Frame 16: both occupy x=120..135, B (black) in front at y=15.
        black_overlap = moving_objects.expected_screen(16)
        assert black_overlap[15 * 32 + 15 : 15 * 32 + 17] == b"\0\0"
        # Frame 46: same x position, A (white) in front at y=45.
        white_overlap = moving_objects.expected_screen(46)
        assert white_overlap[45 * 32 + 15 : 45 * 32 + 17] == b"\xff\xff"
        # Scenery not covered by either object flips at frame 64.
        assert moving_objects.expected_screen(63)[0] == 0
        assert moving_objects.expected_screen(64)[0] == 255
        # Every possible motion tick is bounded, not just the selected snapshots.
        assert {moving_objects.position(frame)[0] for frame in range(1, 61)} == set(range(31))
        assert {moving_objects.position(frame)[1] for frame in range(1, 369)} == set(range(185))

    @pytest.mark.parametrize("data", [b"", bytes(32768)])
    def should_reject_startup_or_missing_ram(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="RAM"):
            moving_objects.verify_ram(data, {}, 1)

    def should_explain_missing_firmware(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(moving_objects, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="coco2 firmware"):
            moving_objects.emulator("coco2")

    def should_preserve_missing_firmware_error_before_launch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(moving_objects, "ROOT", tmp_path)
        monkeypatch.setattr(moving_objects, "build", lambda: (tmp_path / "demo.bin", {}))
        monkeypatch.setattr("sys.argv", ["moving_objects.py", "run"])
        with pytest.raises(ValueError, match="firmware"):
            moving_objects.main()
