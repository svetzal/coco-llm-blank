"""The tile-room model obeys independent map rules: rejections, returns and collection."""

import subprocess
from pathlib import Path

import pytest
from coco import load_expected, load_module

HERE = Path(__file__).parent
model = load_expected(HERE)
pictures = load_module(HERE / "prepare.py")
SYMBOLS = {
    "map_guard_before": 0x3EFF,
    "room": 0x3F00,
    "map_guard_after": 0x3F30,
    "xpos": 0x3F40,
    "ypos": 0x3F41,
    "accepted": 0x3F42,
    "step": 0x3F43,
}


def snapshot(frame: int) -> bytearray:
    position, room, accepted = model.expected_state(frame - 1)
    ram = bytearray(32768)
    for guard in (0x03FF, 0x1C00, 0x3EFF, 0x3F30):
        ram[guard] = 0xA5
    ram[0x400:0x1C00] = model.expected_screen(frame)
    ram[0x3F00:0x3F30] = room
    ram[0x3F40:0x3F44] = bytes((*position, accepted, frame - 1))
    return ram


class DescribeTileRoom:
    @pytest.mark.parametrize(
        "step,position,accepted",
        [
            (1, (0, 0), 0),
            (2, (0, 0), 0),
            (4, (1, 0), 0),
            (5, (1, 1), 1),
            (6, (1, 2), 1),
            (9, (2, 3), 0),
            (17, (5, 0), 0),
            (20, (7, 0), 0),
            (25, (7, 5), 1),
            (26, (7, 5), 0),
            (27, (6, 5), 1),
            (28, (7, 5), 1),
            (29, (6, 5), 1),
            (35, (2, 4), 0),
            (39, (1, 1), 1),
            (40, (1, 2), 1),
            (41, (1, 1), 1),
        ],
    )
    def should_specify_rejections_returns_and_persistent_collection(
        self, step: int, position: tuple[int, int], accepted: int
    ) -> None:
        actual_position, room, actual_acceptance = model.expected_state(step)

        assert (actual_position, actual_acceptance) == (position, accepted)
        assert room[9] == (2 if step < 5 else 0)

    def should_restore_the_changed_map_under_the_old_actor_cell(self) -> None:
        screen = model.expected_screen(41)

        assert all(screen[y * 32 + 1] == 0 for y in range(8, 16))
        # Distinctive last-room-row exit and first-row wall, with empty outer screen.
        assert model.expected_screen(1)[40 * 32 + 6] == 0x7E
        assert model.expected_screen(1)[2] == 255
        assert screen[-1] == 0

    @pytest.mark.parametrize("step", [-1, 42])
    def should_refuse_checkpoints_outside_the_script(self, step: int) -> None:
        with pytest.raises(ValueError, match="Checkpoint"):
            model.expected_state(step)

    def should_accept_the_specified_memory(self) -> None:
        model.verify_ram(snapshot(41), SYMBOLS, 41)

    @pytest.mark.parametrize(
        "address",
        [0x03FF, 0x1C00, 0x400, 0x1BFF, 0x3EFF, 0x3F30, 0x3F09, 0x3F2F]
        + list(range(0x3F40, 0x3F44)),
    )
    def should_reject_any_damaged_byte(self, address: int) -> None:
        damaged = snapshot(41)
        damaged[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_ram(damaged, SYMBOLS, 41)

    def should_reject_missing_ram(self) -> None:
        with pytest.raises(ValueError, match="RAM"):
            model.verify_ram(b"", SYMBOLS, 1)

    def should_show_the_screen_in_the_rendered_colours(self) -> None:
        frame = model.expected_frame(1)

        assert frame.shape == (192, 512, 3)
        # Two samples per pixel: the first wall's top row is lit, the floor below it is not.
        assert frame[0, 2 * 16].tolist() == [46, 188, 36]
        assert frame[8, 0].tolist() == [0, 31, 0]


class DescribeTilePictures:
    def should_convert_the_drawing_to_the_independent_art(self, tmp_path: Path) -> None:
        pictures.prepare(tmp_path)

        drawn = b"".join(
            bytes(int(row.replace("#", "1").replace(".", "0"), 2) for row in art)
            for art in model.ART
        )
        assert (tmp_path / "tiles.bin").read_bytes() == drawn
        assert "tiles_r0c4_rows equ 8" in (tmp_path / "tiles.asm").read_text()

    def should_leave_no_include_when_the_conversion_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / "tiles.asm").write_text("stale pictures")
        monkeypatch.setattr(pictures, "SOURCE", tmp_path / "missing.png")

        with pytest.raises(subprocess.CalledProcessError):
            pictures.prepare(tmp_path)

        assert not (tmp_path / "tiles.asm").exists()
