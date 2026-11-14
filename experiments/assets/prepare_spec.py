"""Independent byte and pixel expectations for the original host example."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from prepare import check, main, prepare, publish

ART = Path(__file__).with_name("art.json")
# Hand-calculated literals: each row's leftmost pixel has weight 128.
EXPECTED = {
    10: bytes.fromhex("00 00 20 00 00 00 00 00"),
    40: bytes.fromhex("ff 80 b8 a0 ae 82 80 fd"),
    70: bytes.fromhex("20 70 f8 70 20 00 02 00"),
    90: bytes.fromhex("e0 80 a0 a4 be 84 80 c1"),
}


def decode(data: bytes, width: int) -> list[list[int]]:
    # String expansion deliberately avoids the production shift/sum packing.
    bits = "".join(f"{value:08b}" for value in data)
    return [[int(p) for p in bits[start : start + width]] for start in range(0, len(bits), width)]


def expected_screen(source: dict) -> list[list[int]]:
    pixels = [[0] * 256 for _ in range(192)]
    drawings = {a["asset_id"]: a["pixels"] for a in source["assets"]}
    # Literal terrain positions and IDs, independent of the input map/mapping.
    walls = {(2, 0), (2, 1), (5, 1), (2, 2), (4, 3), (5, 3), (1, 4)}
    for cy in range(6):
        for cx in range(8):
            asset_id = 40 if (cx, cy) in walls else 10
            if (cx, cy) == (1, 1):
                asset_id = 70
            if (cx, cy) == (6, 5):
                asset_id = 90
            for y, row in enumerate(drawings[asset_id]):
                pixels[cy * 8 + y][cx * 8 : cx * 8 + 8] = row
    return pixels


@pytest.fixture
def source():
    return json.loads(ART.read_bytes())


class DescribePreparation:
    def should_match_literal_bytes_and_decode_every_original_pixel(self, source):
        bundle = json.loads(prepare(ART.read_bytes()))
        original = {asset["asset_id"]: asset for asset in source["assets"]}

        for asset in bundle["assets"]:
            packed = bytes.fromhex(asset["hex"])
            assert packed == EXPECTED[asset["asset_id"]]
            assert decode(packed, 8) == original[asset["asset_id"]]["pixels"]
        screen = bytes.fromhex(bundle["framebuffer_hex"])
        assert len(screen) == 6144
        assert decode(screen, 256) == expected_screen(source)
        # Lower-right cell's dot, exit's last row, and next row outside the room.
        assert screen[42 * 32 + 7] == 0x20
        assert screen[47 * 32 + 6] == 0xC1
        assert screen[48 * 32 :] == bytes(144 * 32)

    def should_expose_reversed_bits_rows_and_palette(self, source):
        expected = expected_screen(source)
        bundle = json.loads(prepare(ART.read_bytes()))
        screen = bytes.fromhex(bundle["framebuffer_hex"])

        reversed_bits = bytes(int(f"{b:08b}"[::-1], 2) for b in screen)
        assert decode(reversed_bits, 256) != expected
        for asset in bundle["assets"]:
            packed = bytes.fromhex(asset["hex"])
            assert packed[::-1] != EXPECTED[asset["asset_id"]]
            assert bytes(b ^ 255 for b in packed) != EXPECTED[asset["asset_id"]]

    def should_expose_valid_but_wrong_mapping_and_displaced_anchor(self, source):
        expected = expected_screen(source)
        source["terrain_to_asset"][0:2] = [40, 10]
        wrong = bytes.fromhex(json.loads(prepare(json.dumps(source).encode()))["framebuffer_hex"])
        assert decode(wrong, 256) != expected

        right = bytes.fromhex(json.loads(prepare(ART.read_bytes()))["framebuffer_hex"])
        shifted = bytes(32) + right[:-32]
        assert decode(shifted, 256) != expected
        shifted = b"".join(b"\0" + right[y : y + 31] for y in range(0, 6144, 32))
        assert decode(shifted, 256) != expected

    def should_publish_identical_bytes_on_rerun_and_detect_staleness(self, tmp_path, source):
        input_path, output = tmp_path / "art.json", tmp_path / "nested/bundle.json"
        input_path.write_bytes(ART.read_bytes())
        publish(input_path, output)
        first = output.read_bytes()
        publish(input_path, output)
        assert output.read_bytes() == first
        check(input_path, output)

        source["assets"][0]["pixels"][0][0] = 1
        input_path.write_text(json.dumps(source))
        with pytest.raises(ValueError, match="stale"):
            check(input_path, output)
        publish(input_path, output)
        assert output.read_bytes() != first
        check(input_path, output)
        output.write_bytes(first[:-1])
        with pytest.raises(ValueError, match="stale"):
            check(input_path, output)
        output.unlink()
        with pytest.raises(FileNotFoundError):
            check(input_path, output)

    @pytest.mark.parametrize(
        "fault",
        [
            "missing_asset",
            "duplicate_asset",
            "missing_mapping",
            "terrain_negative",
            "terrain_large",
            "asset_negative",
            "width",
            "height",
            "stride",
            "short_row",
            "short_picture",
            "room_width",
            "room_height",
            "pixel_negative",
            "pixel_large",
            "pixel_bool",
            "pixel_float",
            "anchor",
            "packing",
            "palette",
            "unknown_field",
        ],
    )
    def should_reject_invalid_source_without_publishing(self, tmp_path, source, fault):
        bad = copy.deepcopy(source)
        asset = bad["assets"][0]
        mutations = {
            "missing_asset": lambda: bad["terrain_to_asset"].__setitem__(0, 255),
            "duplicate_asset": lambda: bad["assets"].append(asset),
            "missing_mapping": lambda: bad["terrain_to_asset"].pop(),
            "terrain_negative": lambda: bad["room"][0].__setitem__(0, -1),
            "terrain_large": lambda: bad["room"][0].__setitem__(0, 4),
            "asset_negative": lambda: asset.__setitem__("asset_id", -1),
            "width": lambda: asset.__setitem__("width", 16),
            "height": lambda: asset.__setitem__("height", 7),
            "stride": lambda: asset.__setitem__("stride", 2),
            "short_row": lambda: asset["pixels"][0].pop(),
            "short_picture": lambda: asset["pixels"].pop(),
            "room_width": lambda: bad["room"][0].pop(),
            "room_height": lambda: bad["room"].pop(),
            "pixel_negative": lambda: asset["pixels"][0].__setitem__(0, -1),
            "pixel_large": lambda: asset["pixels"][0].__setitem__(0, 2),
            "pixel_bool": lambda: asset["pixels"][0].__setitem__(0, True),
            "pixel_float": lambda: asset["pixels"][0].__setitem__(0, 1.0),
            "anchor": lambda: asset.__setitem__("anchor", [1, 0]),
            "packing": lambda: asset.__setitem__("packing", "lsb-first-1bpp"),
            "palette": lambda: asset.__setitem__("palette", "rg6-css1-black-buff"),
            "unknown_field": lambda: asset.__setitem__("mask", []),
        }
        mutations[fault]()
        input_path, output = tmp_path / "art.json", tmp_path / "bundle.json"
        input_path.write_text(json.dumps(bad))

        for previous in (None, b"old successful bundle"):
            if previous is not None:
                output.write_bytes(previous)
            with pytest.raises(ValueError):
                publish(input_path, output)
            assert not output.exists()
            assert sorted(p.name for p in tmp_path.iterdir()) == ["art.json"]

    def should_reject_unreadable_or_malformed_input_and_preserve_source(self, tmp_path):
        source, output = tmp_path / "art.json", tmp_path / "bundle.json"
        output.write_bytes(b"stale")
        with pytest.raises(FileNotFoundError):
            publish(source, output)
        assert not output.exists()
        source.write_bytes(b"{")
        with pytest.raises(ValueError):
            publish(source, output)
        assert not output.exists()
        with pytest.raises(ValueError, match="must differ"):
            publish(source, source)
        assert source.read_bytes() == b"{"

    def should_run_cli_build_check_help_and_failures(self, tmp_path, monkeypatch):
        output = tmp_path / "bundle.json"
        for action in ("build", "check"):
            monkeypatch.setattr("sys.argv", ["prepare.py", action, "--output", str(output)])
            assert main() == 0
        for arguments, code in [
            (["--help"], 0),
            (["unknown"], 2),
            (["check", "--output", str(tmp_path / "missing")], 1),
        ]:
            monkeypatch.setattr("sys.argv", ["prepare.py", *arguments])
            with pytest.raises(SystemExit) as result:
                main()
            assert result.value.code == code


class DescribeStrictGeometry:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("width", 8.0),
            ("height", 8.0),
            ("stride", 1.0),
            ("width", True),
            ("height", True),
            ("stride", True),
        ],
    )
    def should_reject_noninteger_geometry_through_cli(self, tmp_path, source, field, value):
        input_path, output = tmp_path / "art.json", tmp_path / "bundle.json"
        source["assets"][0][field] = value
        input_path.write_text(json.dumps(source))
        script = Path(__file__).with_name("prepare.py")
        for action in ("check", "build"):
            publish(ART, output)
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    action,
                    "--source",
                    str(input_path),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 1
            assert field in result.stderr
            assert "valid integer" in result.stderr
            assert output.exists() is (action == "check")
