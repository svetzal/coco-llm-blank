"""Original, fixed RG6 tile-room host preparation; no target loader."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Asset(Record):
    asset_id: StrictInt = Field(ge=0, le=255)
    width: StrictInt = Field(ge=8, le=8)
    height: StrictInt = Field(ge=8, le=8)
    stride: StrictInt = Field(ge=1, le=1)
    packing: Literal["msb-first-1bpp"]
    palette: Literal["rg6-css0-black-green"]
    anchor: list[StrictInt]
    pixels: list[list[StrictInt]]

    @model_validator(mode="after")
    def validate_picture(self) -> "Asset":
        if self.anchor != [0, 0]:
            raise ValueError("terrain anchor must be top-left [0, 0]")
        if len(self.pixels) != 8 or any(len(row) != 8 for row in self.pixels):
            raise ValueError("pixels must be exactly eight rows of eight")
        if any(pixel not in (0, 1) for row in self.pixels for pixel in row):
            raise ValueError("palette indices must be 0 or 1")
        return self


class Source(Record):
    format: Literal["original-rg6-room-v1"]
    assets: list[Asset]
    terrain_to_asset: list[StrictInt]
    room: list[list[StrictInt]]

    @model_validator(mode="after")
    def validate_references(self) -> "Source":
        ids = [asset.asset_id for asset in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate asset ID")
        if len(self.terrain_to_asset) != 4:
            raise ValueError("require floor, wall, collectible, exit mappings")
        if any(asset_id not in ids for asset_id in self.terrain_to_asset):
            raise ValueError("mapping refers to missing asset ID")
        if len(self.room) != 6 or any(len(row) != 8 for row in self.room):
            raise ValueError("room must be six rows of eight terrain IDs")
        if any(cell not in range(4) for row in self.room for cell in row):
            raise ValueError("unknown terrain ID")
        return self


def pack(asset: Asset) -> bytes:
    """Pack validated rows from left bit 7 to right bit 0."""
    return bytes(sum(pixel << (7 - x) for x, pixel in enumerate(row)) for row in asset.pixels)


def prepare(raw: bytes) -> bytes:
    """Validate the entire source before constructing one canonical JSON bundle."""
    source = Source.model_validate_json(raw)
    pictures = {asset.asset_id: pack(asset) for asset in source.assets}
    screen = bytearray(6144)
    for row, cells in enumerate(source.room):
        for column, terrain in enumerate(cells):
            for y, value in enumerate(pictures[source.terrain_to_asset[terrain]]):
                screen[(row * 8 + y) * 32 + column] = value
    bundle = {
        "format": "prepared-rg6-room-v1",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "screen": {"width": 256, "height": 192, "stride": 32, "origin": [0, 0]},
        "assets": [
            {**asset.model_dump(exclude={"pixels"}), "hex": pictures[asset.asset_id].hex()}
            for asset in sorted(source.assets, key=lambda asset: asset.asset_id)
        ],
        "terrain_to_asset": source.terrain_to_asset,
        "room": source.room,
        "framebuffer_hex": screen.hex(),
    }
    return (json.dumps(bundle, sort_keys=True, separators=(",", ":")) + "\n").encode()


def publish(source: Path, output: Path) -> None:
    """Invalidate an old result, then atomically rename a fully written bundle."""
    if source.resolve() == output.resolve():
        raise ValueError("source and output must differ")
    output.unlink(missing_ok=True)
    prepared = prepare(source.read_bytes())
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=output.parent, prefix=".assets-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(prepared)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def check(source: Path, output: Path) -> None:
    """Reject missing, corrupt or stale output by recomputing the full bundle."""
    if output.read_bytes() != prepare(source.read_bytes()):
        raise ValueError("prepared output is stale or corrupt")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "check"))
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("art.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        (publish if args.action == "build" else check)(args.source, args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f"asset preparation failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
