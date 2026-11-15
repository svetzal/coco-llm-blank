"""Download selected firmware into ignored storage, never into the template."""

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter
from references import atomic_bytes

# The firmware profiles in roms.json that setup, doctor and bootstrap offer.
TARGETS = ("coco1", "coco2", "coco2b", "coco3")


class RomMember(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]+\.rom$")
    size: int = Field(gt=0, le=65536)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RomArchive(BaseModel):
    url: str = Field(pattern=r"^https://colorcomputerarchive\.com/repo/ROMs/MAME-MESS/[^/]+\.zip$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    members: list[RomMember] = Field(min_length=1)


class RomDownloadGateway:
    def fetch(self, url: str) -> bytes:
        with urllib.request.urlopen(url, timeout=60) as response:
            return response.read()


def checked(data: bytes, checksum: str, label: str) -> bytes:
    if hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError(f"{label}: checksum mismatch; inspect the source or damaged cache")
    return data


def verify_installed(
    root: Path, target: str, names: tuple[str, ...] | None = None
) -> dict[str, Path]:
    """Check installed bytes before launch, without downloads or replacements."""
    recovery = f"uv run python scripts/setup.py --target {target} --roms-only"
    try:
        profiles = TypeAdapter(dict[str, RomArchive]).validate_json(
            (root / "roms.json").read_text()
        )
        if target not in profiles:
            raise ValueError(f"No ROM profile for {target}")
        members = {member.name: member for member in profiles[target].members}
        selected = tuple(members) if names is None else names
        paths = {}
        for name in selected:
            if name not in members:
                raise ValueError(f"{name}: not listed in the {target} ROM profile")
            member = members[name]
            path = (root / "local/roms" / target / name).resolve()
            data = path.read_bytes()
            if len(data) != member.size:
                raise ValueError(f"{path}: expected {member.size} bytes, found {len(data)}")
            checked(data, member.sha256, str(path))
            paths[name] = path
        return paths
    except (OSError, ValueError) as error:
        raise ValueError(
            f"Cannot use {target} firmware: {error}. "
            f"Run {recovery}. If a file differs, inspect it before replacing it; "
            "do not launch XRoar until validation passes."
        ) from error


def provision(root: Path, target: str, downloads: RomDownloadGateway | None = None) -> None:
    """Validate the whole selection before publishing allowlisted members."""
    profiles = TypeAdapter(dict[str, RomArchive]).validate_json((root / "roms.json").read_text())
    if target not in profiles:
        raise ValueError(f"No ROM profile for {target}")
    profile = profiles[target]
    directory = root / "local/roms" / target
    cache = directory / "source.zip"
    data = (
        cache.read_bytes()
        if cache.exists()
        else (downloads or RomDownloadGateway()).fetch(profile.url)
    )
    checked(data, profile.sha256, profile.url)
    extracted = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in profile.members:
                info = archive.getinfo(member.name)
                if info.file_size != member.size:
                    raise ValueError(f"{member.name}: unexpected ROM size")
                extracted[member.name] = checked(archive.read(info), member.sha256, member.name)
    except (zipfile.BadZipFile, KeyError) as error:
        raise ValueError(f"Invalid ROM archive: {error}") from error
    for name, content in extracted.items():
        path = directory / name
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f"{path}: existing ROM differs; inspect before replacing")
    atomic_bytes(cache, data)
    for name, content in extracted.items():
        atomic_bytes(directory / name, content)
    print(f"Verified firmware: local/roms/{target}/")
