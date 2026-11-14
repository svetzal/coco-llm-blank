"""The Collect room model and asset step: independent art, rooms and journey rules."""

from pathlib import Path

import pytest
from coco import load_expected, load_module

HERE = Path(__file__).parent
model = load_expected(HERE)
assets = load_module(HERE / "assets.py")
NAMES = (
    "map_guard_before",
    "map_guard_after",
    "asset_guard_before",
    "asset_guard_after",
    *model.FIELDS,
    "held",
    "previous",
    "sample_count",
    "sound_count",
    "room",
)
LABELS = {name: 0x6000 + index * 2 for index, name in enumerate(NAMES)}
LABELS["room"] = 0x6100


def snapshot(keys: str, state: tuple[int, ...]) -> bytearray:
    ram = bytearray(32768)
    for address in (0x3FF, 0x1C00, 0x7E00, *(LABELS[n] for n in NAMES[:4])):
        ram[address] = 0xA5
    for name, value in zip(model.FIELDS, state, strict=False):
        ram[LABELS[name]] = value
    held = sum(bit for char, bit in zip("UDLRF", (1, 2, 4, 8, 16)) if char in keys)
    ram[LABELS["held"]] = ram[LABELS["previous"]] = held
    ram[LABELS["sample_count"] : LABELS["sample_count"] + 2] = (state[6] * 32).to_bytes(2, "big")
    ram[LABELS["room"] : LABELS["room"] + 48] = model.expected_room(state[8])
    ram[0x400:0x1C00] = model.screen_for_state(state)
    return ram


class DescribeCollectRoomModel:
    def should_read_the_hand_written_journey(self) -> None:
        steps = model.journey()

        assert len(steps) == 95
        assert steps[0][1][3] == 2
        assert all(len(state) == 9 for _, state in steps)

    def should_clear_each_collected_star_independently(self) -> None:
        assert model.expected_room(0)[9] == 2 and model.expected_room(0)[37] == 2
        assert model.expected_room(1)[9] == 0 and model.expected_room(1)[37] == 2
        assert model.expected_room(2)[9] == 2 and model.expected_room(2)[37] == 0

    def should_draw_the_title_and_leave_the_border_blank(self) -> None:
        screen = model.expected_screen(1)

        assert any(screen[16 * 32 : 23 * 32])
        assert not any(screen[: 16 * 32])
        assert screen == model.screen_for_state(model.TITLE)

    def should_accept_an_idle_title_frame(self) -> None:
        model.verify_ram(snapshot("-", model.TITLE), LABELS, 7)

    @pytest.mark.parametrize("damage", ["guard", "state", "history", "room", "sound", "screen"])
    def should_reject_damaged_journey_evidence(self, damage: str) -> None:
        keys, state = model.journey()[64]
        ram = snapshot(keys, state)
        address = {
            "guard": 0x7E00,
            "state": LABELS["xpos"],
            "history": LABELS["previous"],
            "room": LABELS["room"] + 9,
            "sound": LABELS["sound_count"],
            "screen": 0x0400 + 20 * 32 + 3,
        }[damage]
        model.verify_journey_frame(ram, LABELS, keys, state)
        ram[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_journey_frame(ram, LABELS, keys, state)

    def should_reject_truncated_ram(self) -> None:
        with pytest.raises(ValueError, match="truncated"):
            model.verify_ram(b"", LABELS, 1)


class DescribeAssets:
    def should_pack_boundary_pixels_and_row_repetition(self) -> None:
        assert assets.expand(bytes.fromhex("8101")) == bytes.fromhex("c003c00300030003")
        assert assets.headers()[:4] == bytes.fromhex("00007bc7")

    def should_reject_changed_art_before_publishing_assets(self, tmp_path, monkeypatch):
        monkeypatch.setattr(model, "ART", (bytes(8),) + model.ART[1:])
        (tmp_path / "assets.inc").write_text("old")

        with pytest.raises(ValueError, match="Terrain art changed"):
            assets.prepare(tmp_path)

        assert not (tmp_path / "assets.inc").exists()

    def should_prepare_guarded_assets(self, tmp_path) -> None:
        assets.prepare(tmp_path)

        lines = (tmp_path / "assets.inc").read_text().splitlines()
        assert lines[0] == "asset_guard_before fcb $a5"
        assert lines[-1] == "asset_guard_after fcb $a5"
        assert "headers" in lines
