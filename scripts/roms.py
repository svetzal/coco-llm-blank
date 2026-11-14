"""Download selected firmware into ignored storage, never into the template."""

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field, TypeAdapter
from references import atomic_bytes


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
