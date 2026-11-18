"""Prepare assets.inc for main.asm: pre-shifted, masked CG6 sprites from sprites.txt.

scripts/coco.py calls prepare(output) before it assembles, because coco.toml names
this file.

CG6 packs four pixels in a byte, leftmost pixel in bits 7 and 6 (MC6847 PDF 19
Table 3). A sprite at pixel x starts in byte x // 4 at pixel x % 4 of that byte.
So each sprite gets four copies, one for each shift 0-3.

Each copy is code, not data. X holds the screen byte of the sprite's top-left
corner. The draw routine handles each byte that the sprite uses:

- a byte that the sprite fills: store the picture (LDA #, STA; or LDD #, STD for
  two neighbours);
- an edge byte: keep the screen bits where the mask is 1 and add the picture:
  screen = (screen AND mask) OR picture;
- a byte that the sprite does not use: no code.

The erase routine stores the floor in each byte that the draw routine changes,
and in no other byte, such as the wall. FLOOR comes from main.asm.

Output for a sprite NAME:

    NAME     fdb NAME_draw_0,NAME_erase_0, ... (the same for shifts 1, 2 and 3)
    NAME_draw_0
             lda 0,x ...
             rts
"""

from pathlib import Path

HERE = Path(__file__).resolve().parent
CODES = {"G": 0, "Y": 1, "B": 2, "R": 3}


def read_sprites(path: Path) -> dict[str, list[str]]:
    sprites: dict[str, list[str]] = {}
    name = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            name = line.strip("[]")
            sprites[name] = []
        elif name is None:
            raise ValueError(f"Art before a [name] line: {line!r}")
        else:
            sprites[name].append(line)
    for name, rows in sprites.items():
        if len({len(row) for row in rows}) != 1:
            raise ValueError(f"Sprite {name}: rows have different widths")
        if any(c not in ".GYBR" for row in rows for c in row):
            raise ValueError(f"Sprite {name}: unknown character")
    return sprites


def shifted(rows: list[str], shift: int, nbytes: int) -> bytes:
    out = bytearray()
    for row in rows:
        mask = [0xFF] * nbytes
        picture = [0] * nbytes
        for column, char in enumerate(row):
            if char == ".":
                continue
            x = shift + column
            bit = 6 - 2 * (x % 4)
            mask[x // 4] &= ~(3 << bit) & 0xFF
            picture[x // 4] |= CODES[char] << bit
        for m, p in zip(mask, picture):
            out += bytes((m, p))
    return bytes(out)


def cells(rows: list[str], shift: int) -> list[tuple[int, int, int]]:
    """(offset from the first byte, mask, picture) of each byte that the sprite uses."""
    nbytes = (shift + len(rows[0]) + 3) // 4
    data = shifted(rows, shift, nbytes)
    out = []
    for r in range(len(rows)):
        for c in range(nbytes):
            i = 2 * (r * nbytes + c)
            mask, picture = data[i], data[i + 1]
            if mask != 0xFF:
                out.append((r * 32 + c, mask, picture))
    return out


class Code:
    """Lines of one routine. X holds the first byte. Each access uses an 8-bit
    offset from X; when an offset gets too large, X moves on."""

    def __init__(self, label: str) -> None:
        self.lines = [label]
        self.base = 0

    def offset(self, at: int) -> int:
        if at - self.base > 127:
            new = at + 128
            self.lines.append(f"        leax {new - self.base},x")
            self.base = new
        return at - self.base

    def add(self, op: str, at: int | None = None) -> None:
        if at is None:
            self.lines.append(f"        {op}")
        else:
            self.lines.append(f"        {op} {self.offset(at)},x")


def pairs(used: list[tuple[int, int, int]]) -> list[list[tuple[int, int, int]]]:
    """Groups of one byte, or of two neighbours in one row (one 16-bit store)."""
    groups: list[list[tuple[int, int, int]]] = []
    for cell in used:
        last = groups[-1] if groups else None
        if (
            last
            and len(last) == 1
            and last[0][0] + 1 == cell[0]
            and last[0][0] // 32 == cell[0] // 32
            and (last[0][1] == 0) == (cell[1] == 0)
        ):
            last.append(cell)
        else:
            groups.append([cell])
    return groups


def draw_code(name: str, used: list[tuple[int, int, int]]) -> list[str]:
    code = Code(name)
    for group in pairs(used):
        at = group[0][0]
        if group[0][1] == 0 and len(group) == 2:  # two full bytes
            code.add(f"ldd #${group[0][2]:02x}{group[1][2]:02x}")
            code.add("std", at)
        elif group[0][1] == 0:  # one full byte
            code.add(f"lda #${group[0][2]:02x}")
            code.add("sta", at)
        else:  # edge bytes: keep the floor
            for i, (_, mask, picture) in enumerate(group):
                code.add("lda", at + i)
                code.add(f"anda #${mask:02x}")
                if picture:  # green (code 0) needs no OR
                    code.add(f"ora #${picture:02x}")
                code.add("sta", at + i)
    code.add("rts")
    return code.lines


def erase_code(name: str, used: list[tuple[int, int, int]]) -> list[str]:
    code = Code(name)
    code.add("ldd #FLOOR*257")
    groups: list[list[int]] = []
    for at, _, _ in used:
        if groups and len(groups[-1]) == 1 and groups[-1][0] + 1 == at and at % 32:
            groups[-1].append(at)
        else:
            groups.append([at])
    for group in groups:
        code.add("std" if len(group) == 2 else "sta", group[0])
    code.add("rts")
    return code.lines


# Sprites that main.asm always places at a pixel x that is a multiple of 4.
# They get only the shift-0 routines; the descriptor repeats them.
ALIGNED = ("pk_",)


def assembly(sprites: dict[str, list[str]]) -> str:
    lines = []
    for name, rows in sprites.items():
        shifts = [0] if name.startswith(ALIGNED) else list(range(4))
        lines.append(
            f"{name} fdb "
            + ",".join(
                f"{name}_draw_{s if s in shifts else 0},{name}_erase_{s if s in shifts else 0}"
                for s in range(4)
            )
        )
        for shift in shifts:
            used = cells(rows, shift)
            lines += draw_code(f"{name}_draw_{shift}", used)
            lines += erase_code(f"{name}_erase_{shift}", used)
    return "\n".join(lines) + "\n"


def glyph_bytes(rows: list[str]) -> list[int]:
    """One byte for each row of a 4-pixel glyph, leftmost pixel in bits 7-6."""
    out = []
    for row in rows:
        if len(row) != 4 or any(c not in "GYBR" for c in row):
            raise ValueError(f"Glyph row {row!r}: 4 pixels of G, Y, B or R")
        value = 0
        for char in row:
            value = value << 2 | CODES[char]
        out.append(value)
    return out


def font_assembly(glyphs: dict[str, list[str]]) -> str:
    """font: 5 bytes for each character from space (32) to Z (90). A character
    without a glyph is a space. digits: the glyphs of 0-9 in font. life_icon: 5
    bytes. double: for each pair of pixels (4 bits), the byte that shows each
    pixel two times, for big text."""
    blank = ["BBBB"] * 5
    lines = ["font"]
    for code in range(32, 91):
        rows = glyphs.get(chr(code), blank)
        lines.append("        fcb " + ",".join(f"${b:02x}" for b in glyph_bytes(rows)))
    lines.append(f"digits equ font+{(ord('0') - 32) * 5}")
    lines.append("life_icon")
    lines.append("        fcb " + ",".join(f"${b:02x}" for b in glyph_bytes(glyphs["life"])))
    pairs = [(n >> 2) * 0x50 | (n & 3) * 0x05 for n in range(16)]
    lines.append("double  fcb " + ",".join(f"${b:02x}" for b in pairs))
    return "\n".join(lines) + "\n"


def prepare(output: Path) -> None:
    include = output / "assets.inc"
    include.write_text(
        assembly(read_sprites(HERE / "sprites.txt"))
        + font_assembly(read_sprites(HERE / "font.txt"))
    )
