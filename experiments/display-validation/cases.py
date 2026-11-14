"""Retained probe, frozen-frame transformations and independent pixel oracles."""

import re
from pathlib import Path

import numpy as np
from instrument import replace_once
from PIL import Image
from pydantic import BaseModel, ConfigDict


class Case(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    source: str
    checkpoint: str
    expected: bytes


def probe_bytes() -> bytes:
    pixels = bytearray(6144)
    points = [(0, 0), (7, 1), (8, 2), (255, 191), (31, 117)]
    points += [(x, y) for y in range(23, 36) for x in range(17, 46)]
    for x, y in points:
        pixels[y * 32 + x // 8] |= 128 >> (x % 8)
    return bytes(pixels)


def moving_bytes(frame: int) -> bytes:
    x = (frame - 1) % 60
    x = x if x <= 30 else 60 - x
    y = frame - 1
    memory = bytearray(
        255 if bool(yy & 8) ^ bool(xx & 1) ^ bool(frame & 64) else 0
        for yy in range(192)
        for xx in range(32)
    )
    order = [(x, 255), (30 - x, 0)] if not frame & 32 else [(30 - x, 0), (x, 255)]
    for column, ink in order:
        for yy in range(y, y + 8):
            memory[yy * 32 + column : yy * 32 + column + 2] = bytes([ink, ink])
    return bytes(memory)


def make_cases(first: str, moving: str, expected_first: bytes) -> list[Case]:
    probe = replace_once(
        first,
        "        lda #$A5\n        sta $2FFF\nready   bra ready\n        end start\n",
        """        ldx #probe_data
        ldy #$0400
probe_copy lda ,x+
        sta ,y+
        cmpy #$1C00
        blo probe_copy
        lda #$A5
        sta $2FFF
ready   bra ready
probe_data
        includebin "probe.raw"
        end start
""",
    )
    cases = [
        Case(name="first-screen", source=first, checkpoint="ready", expected=expected_first),
        Case(name="asymmetric", source=probe, checkpoint="ready", expected=probe_bytes()),
        Case(
            name="wrong-sam",
            source=replace_once(probe, "sta $FFC5", "sta $FFC4"),
            checkpoint="ready",
            expected=probe_bytes(),
        ),
    ]
    for frame in (1, 35, 65):
        frozen = replace_once(
            moving,
            "frame_ready\n*",
            f"""frame_ready
        ldd frames
        cmpd #{frame}
        bne continue_frame
frozen  bra frozen
continue_frame
*""",
        )
        cases.append(
            Case(
                name=f"moving-frozen-{frame}",
                source=frozen,
                checkpoint="frozen",
                expected=moving_bytes(frame),
            )
        )
    return cases


def symbol(symbols: str, name: str) -> int:
    matches = re.findall(rf"^{re.escape(name)}\s+EQU\s+\$([0-9A-Fa-f]+)$", symbols, re.MULTILINE)
    if len(matches) != 1:
        raise ValueError(f"Expected one assembler symbol: {name}")
    return int(matches[0], 16)


def compare_capture(ppm: Path, ram: Path, case: Case) -> dict:
    memory = ram.read_bytes()
    if len(memory) != 32768:
        raise ValueError("Checkpoint is not a 32 KiB RAM dump")
    with Image.open(ppm) as image:
        if image.size != (512, 192) or image.mode != "RGB":
            raise ValueError("Unexpected renderer dimensions or format")
        pixels = np.asarray(image)
        image.save(ppm.with_suffix(".png"))
    colours = np.unique(pixels.reshape(-1, 3), axis=0).tolist()
    if colours != [[0, 31, 0], [46, 188, 36]]:
        raise ValueError("Unexpected renderer palette")
    bits = np.unpackbits(np.frombuffer(case.expected, dtype=np.uint8)).reshape(192, 256)
    actual = np.all(pixels == [46, 188, 36], axis=2)
    return {
        "size": [512, 192],
        "colours": colours,
        "ram_matches": memory[0x400:0x1C00] == case.expected,
        "pixel_mismatches": int(np.count_nonzero(actual != np.repeat(bits, 2, axis=1))),
    }


def require_case(name: str, result: dict) -> None:
    if not result["ram_matches"]:
        raise ValueError(f"{name}: framebuffer mismatch, including in negative control")
    mismatches = result["pixel_mismatches"]
    if (name == "wrong-sam" and mismatches <= 0) or (name != "wrong-sam" and mismatches != 0):
        raise ValueError(f"{name}: unexpected rendered mismatch count {mismatches}")


def require_unreachable(returncode: int, snapshot: Path) -> None:
    if returncode != 0 or snapshot.exists():
        raise ValueError("Unreachable PC control failed")
