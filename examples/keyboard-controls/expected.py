"""Independent model of the keyboard-controls records: matrix rows, policy and history.

The matrix positions are transcribed from the service manuals' keyboard figures
(see README.md). The CoCo 3 figure puts these four keys at the same positions. Positions and action counts come from the hand-written columns
of keys.txt. Nothing here is derived from the assembly or from captured RAM.
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
UPDATES = 16
RECORDS = 0x4000
RECORD_FIELDS = ("raw_left", "raw_right", "raw_fire", "held", "position", "shots", "previous")
# The three strobed columns, in scan order: PB5, PB6, PB7.
COLUMNS = (5, 6, 7)
# Key letter: (row bit PA, column bit PB) in the CoCo keyboard matrix.
# CoCo 2 NTSC Service Manual PDF 36, figure 4-10; CoCo 3 Service Manual PDF 40,
# figure 5-9: the same positions on both.
MATRIX = {"L": (3, 5), "R": (3, 6), "F": (3, 7), "M": (1, 5)}
# Logical held bits of the program's contract: left 1, right 2, Space 4.
HELD_BITS = {"L": 1, "R": 2, "F": 4}
# Bit 7 of $FF00 is the joystick comparator, not a keyboard row.
KEYBOARD_ROWS = 0x7F
# Writable PIA control bits; bits 7 and 6 are interrupt flags.
CONTROL_BITS = 0x3F
START_POSITION = 2
RAM_SIZES = {
    "coco1": (32768, 65536),
    "coco2": (32768, 65536),
    "coco2b": (32768, 65536),
    "coco3": (131072,),
}
# The CoCo 3 snapshot is physical memory. Under BASIC's map, logical $xxxx is
# at 0x10000 + $xxxx (Tepolt, Assembly Language Programming for the CoCo3, PDF 58).
SNAPSHOT_OFFSET = {"coco1": 0, "coco2": 0, "coco2b": 0, "coco3": 0x10000}


def script(variant: str) -> list[tuple[str, int, int]]:
    """Keys held at each scan, with the hand-written position and action count."""
    if variant != "keys":
        return [("-", START_POSITION, 0)] * (UPDATES + 1)
    return [
        (parts[0], int(parts[1]), int(parts[2]))
        for line in (HERE / "keys.txt").read_text().splitlines()
        if (parts := line.split()) and not line.startswith("#")
    ]


def rows_read(keys: str, column: int) -> int:
    """Rows a scan reads with one column low: a pressed key pulls its row low."""
    pulled = sum(1 << row for key, (row, col) in MATRIX.items() if key in keys and col == column)
    return KEYBOARD_ROWS & ~pulled


def held_bits(keys: str) -> int:
    return sum(bit for key, bit in HELD_BITS.items() if key in keys)


def expected_record(keys: str, position: int, actions: int) -> tuple[int, ...]:
    held = held_bits(keys)
    return (*(rows_read(keys, column) for column in COLUMNS), held, position, actions, held)


def actual_record(ram: bytes, offset: int, update: int) -> tuple[int, ...]:
    start = offset + RECORDS + (update - 1) * len(RECORD_FIELDS)
    record = ram[start : start + len(RECORD_FIELDS)]
    return (
        record[0] & KEYBOARD_ROWS,
        record[1] & KEYBOARD_ROWS,
        record[2] & KEYBOARD_ROWS,
        *record[3:],
    )


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str, target: str) -> None:
    """Every update record, then the update count and final PIA state."""
    if len(ram) not in RAM_SIZES[target]:
        raise ValueError("Missing or truncated RAM snapshot.")
    offset = SNAPSHOT_OFFSET[target]

    def byte(label: str) -> int:
        return ram[offset + symbols[label]]

    steps = script(variant)
    if len(steps) != UPDATES + 1:
        raise ValueError(f"keys.txt holds {len(steps)} scans, expected {UPDATES + 1}.")
    for update, step in enumerate(steps[1:], 1):
        expected, actual = expected_record(*step), actual_record(ram, offset, update)
        if actual != expected:
            fields = dict(zip(RECORD_FIELDS, actual, strict=True))
            raise ValueError(f"Update {update} ({step[0]}): expected {expected}, got {fields}.")
    if byte("count") != UPDATES:
        raise ValueError("The program did not complete 16 updates.")
    for port in ("a", "b"):
        before = byte(f"control_{port}_before") & CONTROL_BITS
        if byte(f"control_{port}_after") & CONTROL_BITS != before:
            raise ValueError(f"PIA control register {port.upper()} changed.")
    if byte("columns_after") != 0xFF:
        raise ValueError("The scan did not leave every column high.")
