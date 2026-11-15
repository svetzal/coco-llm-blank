"""The Collect room model and asset step: independent art, rooms and journey rules."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
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

    def should_expect_the_journey_only_in_the_journey_build(self) -> None:
        keys, state = model.journey()[94]

        model.verify_ram(snapshot(keys, state), LABELS, 95, "journey")
        assert model.expected_screen(95, "journey") == model.screen_for_state(state)
        assert model.expected_screen(95, "") == model.screen_for_state(model.TITLE)
        with pytest.raises(ValueError, match="Game state differs"):
            model.verify_ram(snapshot(keys, state), LABELS, 95, "")

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


def mixer(*tones_hz: float, rate: int = 44100) -> SimpleNamespace:
    """Synthetic mixer output: 32 alternating writes per tone, with idle gaps between."""
    samples = [np.full(rate // 10, 500, np.int16)]
    for hz in tones_hz:
        half = rate / (2 * hz)
        edges = np.round(np.arange(33) * half).astype(int)
        burst = np.zeros(edges[-1], np.int16)
        for write in range(0, 32, 2):
            burst[edges[write] : edges[write + 1]] = 23000
        samples += [burst, np.full(rate // 10, 500, np.int16)]
    return SimpleNamespace(samples=np.concatenate(samples), rate=rate)


class DescribeRenderedFrame:
    def should_render_lit_pixels_green_two_samples_wide(self) -> None:
        frame = model.expected_frame(1)
        lit = next(
            x for x in range(256) if model.expected_screen(1)[16 * 32 + x // 8] & 128 >> x % 8
        )

        assert frame.shape == (192, 512, 3)
        assert frame[16, 2 * lit].tolist() == frame[16, 2 * lit + 1].tolist() == [46, 188, 36]
        assert frame[0, 0].tolist() == [0, 31, 0]


class DescribeMixerEffects:
    def should_list_every_effect_of_the_journey_in_order(self) -> None:
        assert model.expected_effects(4, "journey") == []
        assert model.expected_effects(5, "journey") == [1]
        assert model.expected_effects(95, "journey") == [1, 2, 2, 3] * 3
        assert model.expected_effects(95, "") == []

    def should_accept_each_effect_in_its_pitch_band(self) -> None:
        result = model.verify_sound(mixer(980, 1740, 1740, 680), 38, "journey")

        assert result["effects"] == 4
        assert [round(hz, -1) for hz in result["hz"]] == [980, 1740, 1740, 680]

    def should_accept_a_quiet_title(self) -> None:
        assert model.verify_sound(mixer(), 95, "")["effects"] == 0

    @pytest.mark.parametrize(
        "tones,message",
        [((), "has 0 effects, expected 1"), ((1740,), r"effect 1 has 32 steps at 17\d\d Hz")],
    )
    def should_reject_a_missing_or_wrong_effect(self, tones, message: str) -> None:
        with pytest.raises(ValueError, match=message):
            model.verify_sound(mixer(*tones), 5, "journey")

    def should_reject_an_effect_with_missing_writes(self) -> None:
        sound = mixer(980)
        sound.samples[sound.samples.argmax() : sound.samples.argmax() + 30] = 500

        with pytest.raises(ValueError, match="effect 1 has 30 steps"):
            model.verify_sound(sound, 5, "journey")


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
