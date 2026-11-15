"""Independent expectations for turn-queue: the hand-written outcomes in turns.txt.

The program appends one 19-byte record per step: the 17-byte world, the status
and the mask of slots that landed. Every expected record is the outcome written
in turns.txt, encoded with the world layout in README.md. Nothing here is
derived from the assembly or from captured RAM.
"""

from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
PHASES = ("complete", "commands", "finished")
STATUSES = ("accepted", "rejected")
WORLD_BYTES = 17
RECORD_BYTES = WORLD_BYTES + 2
# Where CPU address $0000 is in each target's snapshot, and the snapshot size.
# CoCo 1 and CoCo 2: 32 KiB of RAM at $0000-$7FFF (Color Computer Technical
# Reference Manual, PDF 12). CoCo 3: BASIC's reset sets the executive map to
# physical pages $38-$3F, the top 64 KiB of 128 KiB (Tepolt, Assembly Language
# Programming for the CoCo3, PDF 56 step 6, PDF 57 step 31, PDF 58 Fig. 7-2).
LAYOUTS = {
    "coco1": (32 * 1024, 0),
    "coco2": (32 * 1024, 0),
    "coco3": (128 * 1024, 0x10000),
}


class Step(NamedTuple):
    action: str
    command: tuple[int, ...]
    status: str
    resolved: tuple[int, ...]
    world: bytes


class Case(NamedTuple):
    name: str
    start: bytes
    steps: tuple[Step, ...]


def slot_bytes(text: str) -> bytes:
    """'-' is a free slot; '1:3@2' is 3 ships to planet 1, landing on turn 2."""
    if text == "-":
        return bytes(5)
    destination, rest = text.split(":")
    ships, arrival = rest.split("@")
    return bytes([1, int(destination), int(ships)]) + int(arrival).to_bytes(2, "big")


def world_bytes(text: str) -> bytes:
    """'<turn>/<limit> <phase> <ships>,<ships> <slot> <slot>' in the program's layout."""
    clock, phase, ships, *slots = text.split()
    turn, limit = (int(value) for value in clock.split("/"))
    planets = bytes(int(value) for value in ships.split(","))
    header = turn.to_bytes(2, "big") + limit.to_bytes(2, "big") + bytes([PHASES.index(phase)])
    world = header + planets + b"".join(slot_bytes(slot) for slot in slots)
    if len(world) != WORLD_BYTES:
        raise ValueError(f"A world needs two planets and two slots: {text!r}")
    return world


def parse_step(line: str) -> Step:
    action, outcome = (part.split() for part in line.split("=>"))
    status, resolved, *world = outcome
    slots = () if resolved == "-" else tuple(int(slot) for slot in resolved.split(","))
    command = tuple(int(value) for value in action[1:])
    return Step(action[0], command, status, slots, world_bytes(" ".join(world)))


def parse(text: str) -> list[Case]:
    cases: list[Case] = []
    for line in text.splitlines():
        words = line.split()
        if not words or words[0].startswith("#"):
            continue
        if words[0] == "case":
            cases.append(Case(words[1], b"", ()))
        elif words[0] == "start":
            cases[-1] = cases[-1]._replace(start=world_bytes(line.split("=>")[1]))
        else:
            cases[-1] = cases[-1]._replace(steps=(*cases[-1].steps, parse_step(line)))
    return cases


def cases() -> list[Case]:
    return parse((HERE / "turns.txt").read_text())


def expected_record(step: Step) -> bytes:
    mask = sum(1 << slot for slot in step.resolved)
    return step.world + bytes([STATUSES.index(step.status), mask])


def checkpoints(script: list[Case]) -> list[tuple[str, bytes]]:
    return [
        (f"{case.name} step {number}", expected_record(step))
        for case in script
        for number, step in enumerate(case.steps, 1)
    ]


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, target: str) -> None:
    """Every record, in order, against the hand-written outcome."""
    size, offset = LAYOUTS[target]
    if len(ram) != size:
        raise ValueError(f"Missing or truncated RAM snapshot: {len(ram)} bytes, not {size}.")
    memory = ram[offset:]
    expected = checkpoints(cases())
    start = symbols["results"]
    differ = []
    for index, (name, record) in enumerate(expected):
        actual = memory[start + index * RECORD_BYTES : start + (index + 1) * RECORD_BYTES]
        if actual != record:
            differ.append((name, record, actual))
    if differ:
        name, record, actual = differ[0]
        raise ValueError(
            f"{len(differ)} of {len(expected)} records differ. First, {name}: "
            f"expected {record.hex(' ')}, got {actual.hex(' ')}."
        )
