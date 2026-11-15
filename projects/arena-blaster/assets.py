"""Prepare assets.inc for main.asm: pre-shifted, masked CG6 sprites from sprites.txt.

scripts/coco.py calls prepare(output) before it assembles, because coco.toml names
this file.

CG6 packs four pixels in a byte, leftmost pixel in bits 7 and 6 (MC6847 PDF 19
Table 3). A sprite at pixel x starts in byte x // 4 at pixel x % 4 of that byte.
So each sprite gets four copies, one for each shift 0-3. All four copies have the
same width in bytes: ceil((width + 3) / 4).

Each copy is rows x bytes pairs of (mask, picture). The draw keeps the screen bits
where the mask is 1 and adds the picture: screen = (screen AND mask) OR picture.

Output for a sprite NAME:

    NAME     fcb rows,bytes
             fdb NAME_0,NAME_1,NAME_2,NAME_3
    NAME_0   fcb mask,picture,...
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


def assembly(sprites: dict[str, list[str]]) -> str:
    lines = []
    for name, rows in sprites.items():
        nbytes = (len(rows[0]) + 3 + 3) // 4
        lines.append(f"{name} fcb {len(rows)},{nbytes}")
        lines.append("        fdb " + ",".join(f"{name}_{s}" for s in range(4)))
        for shift in range(4):
            data = shifted(rows, shift, nbytes)
            lines.append(f"{name}_{shift}")
            lines.extend(
                "        fcb " + ",".join(f"${b:02x}" for b in data[i : i + 16])
                for i in range(0, len(data), 16)
            )
    return "\n".join(lines) + "\n"


def prepare(output: Path) -> None:
    include = output / "assets.inc"
    include.write_text(assembly(read_sprites(HERE / "sprites.txt")))
