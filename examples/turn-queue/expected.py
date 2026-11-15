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
COMPLETE = 0x5A
FILL = 0xA5
STACK_GUARDS = (0x7DFF, 0x7F00)
RAM_SIZES = (128 * 1024, 512 * 1024)
# The program maps executive pages $38-$3F, the top 64 KiB of physical RAM.
EXECUTIVE = 0x10000


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


def guards(symbols: dict[str, int], records: int) -> tuple[int, ...]:
    """Fill bytes just outside the world, the scratch area and the records."""
    world, scratch, results = symbols["world"], symbols["command"], symbols["results"]
    after_scratch = symbols["cursor"] + 2
    after_records = results + records * RECORD_BYTES
    edges = (world - 1, world + WORLD_BYTES, scratch - 1, after_scratch, results - 1)
    return (*edges, after_records, *STACK_GUARDS)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    """Completion, untouched guards, then every record in order."""
    if len(ram) not in RAM_SIZES:
        raise ValueError("Missing or truncated RAM snapshot.")
    memory = ram[-EXECUTIVE:]
    expected = checkpoints(cases())
    if memory[symbols["complete"]] != COMPLETE:
        raise ValueError("The program did not run every case.")
    damaged = [f"${a:04X}" for a in guards(symbols, len(expected)) if memory[a] != FILL]
    if damaged:
        raise ValueError(f"Guard bytes changed at {', '.join(damaged)}.")
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
