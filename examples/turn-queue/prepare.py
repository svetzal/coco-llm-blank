"""Write script.inc for main.asm from the case starts and actions in turns.txt.

scripts/coco.py calls prepare(output) before assembling, because coco.toml names
this file. The expected outcomes in turns.txt are not written to the program.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTIONS = {"send": 1, "begin": 2, "end": 3}
CASE = 1
END = 0


def model():
    from coco import load_expected

    return load_expected(HERE)


def step_bytes(action: str, command: tuple[int, ...]) -> bytes:
    """Send carries player, source, destination, ships and a big-endian delay."""
    if action != "send":
        return bytes([ACTIONS[action]])
    *fields, delay = command
    return bytes([ACTIONS[action], *fields]) + delay.to_bytes(2, "big")


def script(cases: list) -> bytes:
    output = bytearray()
    for case in cases:
        output.append(CASE)
        output += case.start
        for step in case.steps:
            output += step_bytes(step.action, step.command)
        output.append(END)
    output.append(END)
    return bytes(output)


def assembly(data: bytes) -> str:
    rows = (data[i : i + 16] for i in range(0, len(data), 16))
    return "".join("        fcb " + ",".join(f"${b:02X}" for b in row) + "\n" for row in rows)


def prepare(output: Path) -> None:
    (output / "script.inc").write_text(assembly(script(model().cases())))
