"""Masked pixels preserve scenery, clear opaque black, and respect draw order."""

import json
from pathlib import Path

import masked_objects as masked
import pytest
from native import tool_path


class DescribeMaskedObjects:
    @pytest.mark.parametrize("target", ("coco1", "coco2"))
    @pytest.mark.integration
    def should_execute_all_scenes_and_reject_false_checkpoints(
        self, target: str, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        if not all(tool_path(name) for name in ("lwasm", "xroar")):
            pytest.skip("Native tools are not installed")
        if not (masked.ROOT / "local/roms" / target / masked.ROM_NAMES[target][0]).exists():
            pytest.skip(f"{target} firmware is not provisioned")
        monkeypatch.setattr("sys.argv", ["masked_objects.py", "check", "--target", target])

        masked.main()

        assert f"PASS: {target}" in capsys.readouterr().out
        binary, symbols = masked.build()
        evidence = json.loads(binary.with_name(f"{target}-results.json").read_text())
        assert evidence["scenes"] == 12
        assert evidence["visual"] == "not inspected"
        ram = binary.with_name(f"{target}-2.ram").read_bytes()
        for address in (0x3FF, 0x1C00, 0x400, 0x1BFF, symbols["scene"]):
            damaged = bytearray(ram)
            damaged[address] ^= 1
            with pytest.raises(ValueError):
                masked.verify_ram(damaged, symbols, 2)
        # Real XRoar controls, not mocked success/failure or recycled snapshots.
        # Use scene 0: scene 2 remains intact for inspection of its overlap.
        with pytest.raises(ValueError, match="Unreachable"):
            masked.capture(binary, {**symbols, "state": symbols["frame_ready"]}, target, 0)
        with pytest.raises(ValueError, match="did not reach"):
            masked.capture(binary, {**symbols, "frame_ready": symbols["state"]}, target, 0)
        assert not binary.with_name(f"{target}-0.ram").exists()
        masked.verify_ram(masked.capture(binary, symbols, target, 0), symbols, 0)

    @pytest.mark.parametrize(
        "x,y,a,b",
        [
            (0, 1, 1, 0),
            (15, 8, 0, 1),
            (0, 4, 1, 0),
            (15, 4, 0, 1),
            (7, 4, None, None),
            (0, 0, None, None),
            (15, 9, None, None),
            (-1, 2, None, None),
            (16, 2, None, None),
        ],
    )
    def should_distinguish_transparent_holes_from_both_opaque_inks(self, x, y, a, b):
        assert masked.ring_pixel(x, y, "a") == a
        assert masked.ring_pixel(x, y, "b") == b

    def should_specify_byte_order_overlap_and_restored_background(self) -> None:
        first = masked.expected_screen(0)
        # A's green left / black right edges in row 4 over alternating 00/FF.
        assert first[4 * 32 : 4 * 32 + 2] == bytes((0x80, 0xFE))
        # Transparent entire first row and centre retain the underlying pattern.
        assert first[:2] == bytes((0, 255))
        assert first[5 * 32 : 5 * 32 + 2] == bytes((0x80, 0xFE))
        # Complete overlap: the last ring wins at its opaque top edge.
        assert masked.expected_screen(4)[89 * 32 + 14 : 89 * 32 + 16] == bytes((0, 0))
        assert masked.expected_screen(5)[89 * 32 + 14 : 89 * 32 + 16] == bytes((255, 255))
        assert masked.expected_screen(2) != masked.expected_screen(3)
        plain = masked.expected_screen(7)
        inverted = masked.expected_screen(10)
        assert all(a ^ b == 255 for a, b in zip(plain, inverted, strict=True))
        assert plain[:32] == bytes((0, 255)) * 16
        assert plain[8 * 32 : 9 * 32] == bytes((255, 0)) * 16

    @pytest.mark.parametrize("data", [b"", bytes(32767), bytes(32769)])
    def should_reject_wrong_snapshot_size(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="32 KiB"):
            masked.verify_ram(data, {}, 0)

    def should_reject_uninitialized_guards(self) -> None:
        with pytest.raises(ValueError, match="guards"):
            masked.verify_ram(bytes(32768), {}, 0)

    def should_reject_missing_firmware_before_launch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(masked, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="firmware"):
            masked.emulator("coco2")

    def should_refuse_a_build_that_overlaps_stack(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Real assembler boundary with an oversized source, no simulated tool output.
        source = tmp_path / "examples/masked-objects/main.asm"
        source.parent.mkdir(parents=True)
        source.write_text(
            "        org $3000\nstart   nop\n        rmb $4E00\nprogram_end\n        end start\n"
        )
        monkeypatch.setattr(masked, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="stack"):
            masked.build()

    @pytest.mark.parametrize("failure", ["build", "check"])
    def should_remove_previous_pass_before_a_failed_attempt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
    ) -> None:
        output = tmp_path / "build/masked-objects"
        output.mkdir(parents=True)
        evidence = output / "coco1-results.json"
        evidence.write_text('{"scenes": 12}')
        monkeypatch.setattr(masked, "ROOT", tmp_path)
        monkeypatch.setattr("sys.argv", ["masked_objects.py", "check"])
        monkeypatch.setattr(masked, "build", lambda: (output / "demo.bin", {}))

        def fail(*args):
            raise ValueError("attempt failed")

        monkeypatch.setattr(masked, failure, fail)
        with pytest.raises(ValueError, match="attempt failed"):
            masked.main()
        assert not evidence.exists()
