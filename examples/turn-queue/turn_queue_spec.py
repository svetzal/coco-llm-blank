"""The turn-queue model and script: the hand-written outcomes, the layout and the checks."""

from pathlib import Path

import pytest
from coco import load_expected, load_module

HERE = Path(__file__).parent
model = load_expected(HERE)
prepare = load_module(HERE / "prepare.py")
SYMBOLS = {"world": 0x4100, "command": 0x4200, "complete": 0x420B, "cursor": 0x420C}
SYMBOLS["results"] = 0x5000


def follow_rules(world: bytes, action: str, command: tuple[int, ...]) -> bytes:
    """A second statement of the README rules, to cross-check the hand-written outcomes."""
    turn, limit = int.from_bytes(world[0:2], "big"), int.from_bytes(world[2:4], "big")
    phase, ships = world[4], list(world[5:7])
    slots = [bytearray(world[7:12]), bytearray(world[12:17])]
    status, mask = 1, 0
    if action == "send":
        player, source, destination, count, delay = command
        free = [i for i, slot in enumerate(slots) if not slot[0]]
        valid = phase == 1 and player == 1 and source < 2 and destination < 2
        valid = valid and source != destination and 0 < count <= ships[source]
        if valid and delay and turn + delay <= limit and free:
            ships[source] -= count
            slots[free[0]][:] = bytes([1, destination, count]) + (turn + delay).to_bytes(2, "big")
            status = 0
    elif action == "begin" and phase == 0 and turn < limit:
        turn, phase, status = turn + 1, 1, 0
        for index, slot in enumerate(slots):
            if slot[0] and int.from_bytes(slot[3:5], "big") <= turn:
                ships[slot[1]] = min(255, ships[slot[1]] + slot[2])
                slot[:] = bytes(5)
                mask |= 1 << index
    elif action == "end" and phase == 1:
        phase, status = (2 if turn == limit else 0), 0
    header = turn.to_bytes(2, "big") + limit.to_bytes(2, "big") + bytes([phase, *ships])
    return header + bytes(slots[0] + slots[1]) + bytes([status, mask])


def snapshot(records: list[bytes], size: int = 128 * 1024) -> bytearray:
    ram = bytearray(size)
    memory = len(ram) - model.EXECUTIVE
    for address in model.guards(SYMBOLS, len(records)):
        ram[memory + address] = model.FILL
    start = memory + SYMBOLS["results"]
    for index, record in enumerate(records):
        ram[start + index * model.RECORD_BYTES : start + (index + 1) * model.RECORD_BYTES] = record
    ram[memory + SYMBOLS["complete"]] = model.COMPLETE
    return ram


def specified() -> list[bytes]:
    return [record for _, record in model.checkpoints(model.cases())]


class DescribeTheCases:
    def should_hold_nineteen_cases_and_forty_four_steps(self) -> None:
        cases = model.cases()

        assert len(cases) == 19
        assert len(model.checkpoints(cases)) == 44

    def should_encode_a_world_in_the_documented_layout(self) -> None:
        world = model.world_bytes("65534/65535 commands 17,5 1:3@65535 -")

        assert world.hex(" ") == "ff fe ff ff 01 11 05 01 01 03 ff ff 00 00 00 00 00"

    def should_reject_a_world_without_two_slots(self) -> None:
        with pytest.raises(ValueError, match="two planets and two slots"):
            model.world_bytes("1/4 commands 20,5 -")

    def should_hand_write_the_outcomes_the_rules_give(self) -> None:
        for case in model.cases():
            world = case.start
            for number, step in enumerate(case.steps, 1):
                result = follow_rules(world, step.action, step.command)

                assert result == model.expected_record(step), f"{case.name} step {number}"
                world = result[: model.WORLD_BYTES]

    def should_catch_a_hand_written_outcome_that_breaks_the_rules(self) -> None:
        case = model.parse(
            "case wrong\nstart => 1/4 commands 20,5 - -\n"
            "send 1 0 1 3 1 => accepted - 1/4 commands 20,5 1:3@2 -\n"
        )[0]

        assert follow_rules(case.start, "send", (1, 0, 1, 3, 1)) != model.expected_record(
            case.steps[0]
        )


class DescribeTheScript:
    def should_mark_each_case_and_end_the_script(self) -> None:
        data = prepare.script(model.cases())

        assert data[0] == prepare.CASE
        assert data[1:18] == model.cases()[0].start
        assert data[-2:] == bytes([prepare.END, prepare.END])

    def should_send_the_delay_big_endian_and_omit_outcomes(self) -> None:
        assert prepare.step_bytes("send", (1, 0, 1, 3, 65535)) == bytes([1, 1, 0, 1, 3, 255, 255])
        assert prepare.step_bytes("begin", ()) == bytes([2])
        assert prepare.step_bytes("end", ()) == bytes([3])

    def should_write_the_script_as_assembler_bytes(self, tmp_path: Path) -> None:
        prepare.prepare(tmp_path)

        lines = (tmp_path / "script.inc").read_text().splitlines()
        assert lines[0].startswith("        fcb $01,$00,$01,$00,$04,$01,$14,$05")
        assert all(line.count("$") <= 16 for line in lines)


class DescribeTheCheck:
    @pytest.mark.parametrize("size", model.RAM_SIZES)
    def should_accept_the_specified_records(self, size: int) -> None:
        model.verify_ram(snapshot(specified(), size), SYMBOLS, 1)

    def should_reject_missing_ram(self) -> None:
        with pytest.raises(ValueError, match="truncated"):
            model.verify_ram(b"", SYMBOLS, 1)

    def should_reject_a_run_that_did_not_finish(self) -> None:
        ram = snapshot(specified())
        ram[len(ram) - model.EXECUTIVE + SYMBOLS["complete"]] = 0

        with pytest.raises(ValueError, match="did not run every case"):
            model.verify_ram(ram, SYMBOLS, 1)

    @pytest.mark.parametrize(
        "address", [0x40FF, 0x4111, 0x41FF, 0x420E, 0x4FFF, 0x5344, 0x7DFF, 0x7F00]
    )
    def should_reject_a_changed_guard(self, address: int) -> None:
        ram = snapshot(specified())
        ram[len(ram) - model.EXECUTIVE + address] ^= 1

        with pytest.raises(ValueError, match=f"\\${address:04X}"):
            model.verify_ram(ram, SYMBOLS, 1)

    @pytest.mark.parametrize(
        "control,index,offset,value,first",
        [
            ("rejected send still deducts", 2, 5, 10, "queue-lifecycle step 3"),
            ("full queue overwrites slot 0", 2, 17, 0, "queue-lifecycle step 3"),
            ("landed journey stays active", 4, 7, 1, "queue-lifecycle step 5"),
            ("last slot never scanned", 7, 6, 6, "queue-lifecycle step 8"),
            ("turn passes the limit", 11, 1, 5, "queue-lifecycle step 12"),
        ],
    )
    def should_name_the_first_record_a_broken_rule_changes(
        self, control: str, index: int, offset: int, value: int, first: str
    ) -> None:
        records = [bytearray(record) for record in specified()]
        records[index][offset] = value

        with pytest.raises(ValueError, match=f"1 of 44 records differ. First, {first}:"):
            model.verify_ram(snapshot([bytes(r) for r in records]), SYMBOLS, 1)
