"""The keyboard-controls model: matrix rows, the policy table and its negative controls."""

from pathlib import Path

import pytest
from coco import load_expected

model = load_expected(Path(__file__).parent)
SYMBOLS = {
    "count": 0x3100,
    "complete": 0x3101,
    "control_a_before": 0x3102,
    "control_b_before": 0x3103,
    "control_a_after": 0x3104,
    "control_b_after": 0x3105,
    "columns_after": 0x3106,
}


def snapshot(records: list[tuple[int, ...]]) -> bytearray:
    ram = bytearray(32768)
    for update, record in enumerate(records, 1):
        start = model.RECORDS + (update - 1) * len(model.RECORD_FIELDS)
        ram[start : start + len(record)] = bytes(record)
    ram[SYMBOLS["count"]], ram[SYMBOLS["complete"]] = model.UPDATES, model.COMPLETE
    for name in ("control_a_before", "control_a_after", "control_b_before", "control_b_after"):
        ram[SYMBOLS[name]] = 0x34
    ram[SYMBOLS["columns_after"]] = 0xFF
    return ram


def recorded(variant: str) -> list[tuple[int, ...]]:
    return [model.expected_record(*step) for step in model.script(variant)[1:]]


def follow_policy(keys: list[str]) -> list[tuple[int, int]]:
    """A second statement of the README policy, to cross-check the hand-written table."""
    position, actions, previous, result = model.START_POSITION, 0, keys[0], []
    for held in keys[1:]:
        actions += "F" in held and "F" not in previous
        step = ("R" in held) - ("L" in held)
        position = min(max(position + step, 0), 4)
        previous = held
        result.append((position, actions))
    return result


class DescribeKeyboardControls:
    def should_read_seventeen_scans_from_the_key_script(self) -> None:
        steps = model.script("keys")

        assert len(steps) == 17
        assert steps[0] == ("F", 2, 0)
        assert steps[-1] == ("R", 1, 3)

    def should_hand_write_the_outcomes_the_policy_gives(self) -> None:
        steps = model.script("keys")

        assert follow_policy([keys for keys, _, _ in steps]) == [s[1:] for s in steps[1:]]

    def should_pull_only_the_pressed_keys_row_low_in_its_column(self) -> None:
        assert model.rows_read("LRF", 5) == 0x77
        assert model.rows_read("M", 5) == 0x7D
        assert model.rows_read("M", 6) == 0x7F
        assert model.rows_read("LM", 5) == 0x75

    def should_not_count_m_as_left(self) -> None:
        assert model.held_bits("RFM") == model.held_bits("RF") == 6

    @pytest.mark.parametrize("variant", ["", "keys"])
    def should_accept_the_specified_records(self, variant: str) -> None:
        model.verify_ram(snapshot(recorded(variant)), SYMBOLS, 1, variant)

    def should_ignore_the_joystick_comparator_bit(self) -> None:
        records = [(raw | 0x80, *rest) for raw, *rest in recorded("keys")]

        model.verify_ram(snapshot(records), SYMBOLS, 1, "keys")

    def should_accept_a_64_kib_snapshot(self) -> None:
        model.verify_ram(snapshot(recorded("keys")) + bytes(32768), SYMBOLS, 1, "keys")

    def should_reject_idle_records_when_keys_were_pressed(self) -> None:
        with pytest.raises(ValueError, match=r"Update 1 \(F\)"):
            model.verify_ram(snapshot(recorded("")), SYMBOLS, 1, "keys")

    @pytest.mark.parametrize(
        "control,update,field,value",
        [
            ("wrong column: left never reads", 9, "position", 4),
            ("held Space counts every scan", 1, "shots", 1),
            ("history kept stale after a blocked move", 7, "shots", 1),
            ("unrelated M read as left", 4, "position", 3),
        ],
    )
    def should_reject_each_broken_policy(self, control, update, field, value) -> None:
        records = [list(record) for record in recorded("keys")]
        records[update - 1][model.RECORD_FIELDS.index(field)] = value

        with pytest.raises(ValueError, match=f"Update {update} "):
            model.verify_ram(snapshot([tuple(r) for r in records]), SYMBOLS, 1, "keys")

    @pytest.mark.parametrize(
        "name,value,message",
        [
            ("count", 15, "did not complete"),
            ("complete", 0, "did not complete"),
            ("control_b_after", 0x30, "control register B changed"),
            ("columns_after", 0x7F, "every column high"),
        ],
    )
    def should_reject_an_unfinished_or_unrestored_scan(self, name, value, message) -> None:
        ram = snapshot(recorded("keys"))
        ram[SYMBOLS[name]] = value

        with pytest.raises(ValueError, match=message):
            model.verify_ram(ram, SYMBOLS, 1, "keys")

    def should_reject_missing_ram(self) -> None:
        with pytest.raises(ValueError, match="truncated"):
            model.verify_ram(b"", SYMBOLS, 1, "keys")

    def should_reject_a_script_of_the_wrong_length(self, monkeypatch) -> None:
        monkeypatch.setattr(model, "script", lambda variant: [("-", 2, 0)] * 3)

        with pytest.raises(ValueError, match="holds 3 scans"):
            model.verify_ram(snapshot(recorded("")), SYMBOLS, 1, "keys")
