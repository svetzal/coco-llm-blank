"""Firmware acquisition with original fixture bytes, never copyrighted ROMs."""

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
import setup
from pydantic import TypeAdapter
from roms import TARGETS, RomArchive, RomDownloadGateway, provision, verify_installed

MANIFEST = Path(__file__).resolve().parents[1] / "roms.json"


def fixture_archive(root: Path, *, name: str = "basic.rom", size: int = 8) -> Mock:
    content = b"test ROM"
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("basic.rom", content)
        archive.writestr("../escape.rom", b"never extract unrelated members")
    data = stream.getvalue()
    profile = {
        "url": "https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/test.zip",
        "sha256": hashlib.sha256(data).hexdigest(),
        "members": [{"name": name, "size": size, "sha256": hashlib.sha256(content).hexdigest()}],
    }
    (root / "roms.json").write_text(json.dumps({"coco1": profile}))
    gateway = Mock(spec=RomDownloadGateway)
    gateway.fetch.return_value = data
    return gateway


class DescribeFirmwareSetup:
    def should_download_selected_roms_without_loading_document_models(self, project: Path) -> None:
        gateway = fixture_archive(project)
        assert setup.main(["--target", "coco1", "--roms-only"], project, rom_downloads=gateway) == 0
        assert (project / "local/roms/coco1/basic.rom").read_bytes() == b"test ROM"
        assert not (project / "local/references").exists()
        assert not (project / "local/roms/escape.rom").exists()
        gateway.fetch.side_effect = AssertionError("cache must work offline")
        assert setup.main(["--target", "coco1", "--roms-only"], project, rom_downloads=gateway) == 0

    @pytest.mark.parametrize("damage", ["download", "cache", "member", "size", "missing", "zip"])
    def should_reject_bad_firmware_without_publishing_roms(
        self, project: Path, damage: str
    ) -> None:
        gateway = fixture_archive(project)
        manifest = json.loads((project / "roms.json").read_text())
        profile = manifest["coco1"]
        if damage == "download":
            gateway.fetch.return_value = b"server error"
        elif damage == "cache":
            cache = project / "local/roms/coco1/source.zip"
            cache.parent.mkdir(parents=True)
            cache.write_bytes(b"damaged")
        elif damage == "member":
            profile["members"][0]["sha256"] = "0" * 64
        elif damage == "size":
            profile["members"][0]["size"] = 9
        elif damage == "missing":
            profile["members"][0]["name"] = "missing.rom"
        else:
            gateway.fetch.return_value = b"not a zip"
            profile["sha256"] = hashlib.sha256(b"not a zip").hexdigest()
        (project / "roms.json").write_text(json.dumps(manifest))
        assert setup.main(["--target", "coco1", "--roms-only"], project, rom_downloads=gateway) == 1
        assert not list(project.glob("local/roms/**/*.rom"))

    def should_preserve_an_existing_different_rom(self, project: Path) -> None:
        gateway = fixture_archive(project)
        path = project / "local/roms/coco1/basic.rom"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"owner firmware")
        with pytest.raises(ValueError, match="existing ROM differs"):
            provision(project, "coco1", gateway)
        assert path.read_bytes() == b"owner firmware"

    def should_restore_a_missing_rom_from_the_verified_cache_offline(self, project: Path) -> None:
        gateway = fixture_archive(project)
        provision(project, "coco1", gateway)
        rom = project / "local/roms/coco1/basic.rom"
        rom.unlink()
        gateway.fetch.side_effect = AssertionError("the verified cache must be enough")

        provision(project, "coco1", gateway)

        assert rom.read_bytes() == b"test ROM"

    def should_keep_a_damaged_cache_until_it_is_removed(self, project: Path) -> None:
        gateway = fixture_archive(project)
        cache = project / "local/roms/coco1/source.zip"
        cache.parent.mkdir(parents=True)
        cache.write_bytes(b"interrupted download")

        with pytest.raises(ValueError, match="checksum mismatch; inspect the source or damaged"):
            provision(project, "coco1", gateway)

        assert cache.read_bytes() == b"interrupted download"
        assert list(cache.parent.iterdir()) == [cache]
        gateway.fetch.assert_not_called()
        cache.unlink()
        provision(project, "coco1", gateway)
        assert (project / "local/roms/coco1/basic.rom").read_bytes() == b"test ROM"

    @pytest.mark.parametrize("name", ["../escape.rom", "/absolute.rom", "dir/nested.rom"])
    def should_reject_unsafe_member_names(self, project: Path, name: str) -> None:
        gateway = fixture_archive(project, name=name)
        with pytest.raises(ValueError):
            provision(project, "coco1", gateway)
        assert not (project / "local").exists()

    def should_explain_unknown_profiles_and_a_missing_target(self, project: Path) -> None:
        gateway = fixture_archive(project)
        with pytest.raises(ValueError, match="No ROM profile"):
            provision(project, "coco2", gateway)
        console = Mock(spec=setup.ConsoleGateway)
        console.choose_target.side_effect = ValueError("Choose a target with --target")
        assert setup.main(["--roms-only"], project, console=console, rom_downloads=gateway) == 1
        assert not (project / "local/roms").exists()


class DescribeRomTransport:
    def should_fetch_bytes_through_http(self, pdf_server: str, pdf_bytes: bytes) -> None:
        assert RomDownloadGateway().fetch(pdf_server) == pdf_bytes

    def should_propagate_http_failure(self, pdf_server: str) -> None:
        with pytest.raises(OSError):
            RomDownloadGateway().fetch(pdf_server + "/missing")


class DescribeInstalledFirmware:
    def should_validate_selected_bytes_without_network_or_archive(self, project: Path) -> None:
        gateway = fixture_archive(project)
        provision(project, "coco1", gateway)
        (project / "local/roms/coco1/source.zip").unlink()

        paths = verify_installed(project, "coco1", ("basic.rom",))

        assert paths == {"basic.rom": (project / "local/roms/coco1/basic.rom").resolve()}

    @pytest.mark.parametrize("damage", ["missing", "empty", "wrong-target", "unlisted", "profile"])
    def should_reject_unusable_installed_firmware(self, project: Path, damage: str) -> None:
        gateway = fixture_archive(project)
        provision(project, "coco1", gateway)
        rom = project / "local/roms/coco1/basic.rom"
        if damage == "missing":
            rom.unlink()
        elif damage == "empty":
            rom.write_bytes(b"")
        elif damage == "wrong-target":
            rom.write_bytes(b"otherROM")
        names = ("unlisted.rom",) if damage == "unlisted" else None
        target = "coco2" if damage == "profile" else "coco1"

        with pytest.raises(ValueError, match=f"Cannot use {target} firmware") as error:
            verify_installed(project, target, names)

        assert f"--target {target} --roms-only" in str(error.value)
        assert "do not launch XRoar" in str(error.value)


class DescribeCommittedFirmwareRecords:
    @pytest.fixture
    def profiles(self) -> dict[str, RomArchive]:
        return TypeAdapter(dict[str, RomArchive]).validate_json(MANIFEST.read_text())

    def should_record_one_profile_for_each_offered_target(
        self, profiles: dict[str, RomArchive]
    ) -> None:
        assert tuple(profiles) == TARGETS

    def should_record_the_same_bytes_wherever_a_rom_name_appears(
        self, profiles: dict[str, RomArchive]
    ) -> None:
        checksums: dict[str, set[tuple[int, str]]] = {}
        for profile in profiles.values():
            for member in profile.members:
                checksums.setdefault(member.name, set()).add((member.size, member.sha256))

        assert {name: len(found) for name, found in checksums.items() if len(found) > 1} == {}

    @pytest.mark.parametrize("target", TARGETS)
    def should_name_each_rom_only_once_in_a_profile(
        self, profiles: dict[str, RomArchive], target: str
    ) -> None:
        names = [member.name for member in profiles[target].members]

        assert len(names) == len(set(names))
