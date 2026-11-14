"""Firmware acquisition with original fixture bytes, never copyrighted ROMs."""

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
import setup
from roms import RomDownloadGateway, provision, verify_installed


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
        assert setup.main(["--roms-only"], project, rom_downloads=gateway) == 0

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

    @pytest.mark.parametrize("name", ["../escape.rom", "/absolute.rom", "dir/nested.rom"])
    def should_reject_unsafe_member_names(self, project: Path, name: str) -> None:
        gateway = fixture_archive(project, name=name)
        with pytest.raises(ValueError):
            provision(project, "coco1", gateway)
        assert not (project / "local").exists()

    def should_explain_unknown_profiles_and_target_notes(self, project: Path) -> None:
        gateway = fixture_archive(project)
        with pytest.raises(ValueError, match="No ROM profile"):
            provision(project, "coco2", gateway)
        notes = project / "local/PROJECT.md"
        notes.parent.mkdir()
        notes.write_text("My notes without a target")
        assert setup.main(["--roms-only"], project, rom_downloads=gateway) == 1
        assert notes.read_text() == "My notes without a target"


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

    @pytest.mark.parametrize(
        ("runner", "target", "rom_name"),
        [
            ("first_screen", "coco1", "bas11.rom"),
            ("first_screen", "coco1", "extbas10.rom"),
            ("moving_objects", "coco1", "bas11.rom"),
            ("moving_objects", "coco1", "extbas10.rom"),
            ("moving_objects", "coco2", "bas12.rom"),
            ("moving_objects", "coco2", "extbas11.rom"),
            ("timer_sound", "coco3", "coco3.rom"),
            ("masked_objects", "coco1", "bas11.rom"),
            ("masked_objects", "coco1", "extbas10.rom"),
            ("masked_objects", "coco2", "bas12.rom"),
            ("masked_objects", "coco2", "extbas11.rom"),
        ],
    )
    @pytest.mark.parametrize("damage", ["missing", "empty", "wrong-target", "directory", "valid"])
    def should_refuse_invalid_firmware_at_the_launch_boundary(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        runner: str,
        target: str,
        rom_name: str,
        damage: str,
    ) -> None:
        import first_screen
        import masked_objects
        import moving_objects
        import timer_sound

        module = {
            "first_screen": first_screen,
            "moving_objects": moving_objects,
            "masked_objects": masked_objects,
            "timer_sound": timer_sound,
        }[runner]
        tmp_path = tmp_path / "project with spaces"
        tmp_path.mkdir()
        names = {
            "coco1": ("bas11.rom", "extbas10.rom"),
            "coco2": ("bas12.rom", "extbas11.rom"),
            "coco3": ("coco3.rom",),
        }[target]
        members = []
        for name in names:
            data = (target + name).encode()
            path = tmp_path / "local/roms" / target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            members.append(
                {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            )
        profile = {
            "url": "https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/test.zip",
            "sha256": "0" * 64,
            "members": members,
        }
        (tmp_path / "roms.json").write_text(json.dumps({target: profile}))
        path = tmp_path / "local/roms" / target / rom_name
        if damage == "missing":
            path.unlink()
        elif damage == "empty":
            path.write_bytes(b"")
        elif damage == "wrong-target":
            path.write_bytes(b"x" * len(path.read_bytes()))
        elif damage == "directory":
            path.unlink()
            path.mkdir()
        marker = tmp_path / "launched"
        executable = tmp_path / "xroar"
        executable.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$LAUNCH_MARKER"\n')
        executable.chmod(0o755)
        monkeypatch.setenv("XROAR", str(executable))
        monkeypatch.setenv("LAUNCH_MARKER", str(marker))
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "build", lambda *args: (tmp_path / "test.bin", 0))
        argv = ["demo.py", "run"] + (
            ["--target", target] if runner in ("moving_objects", "masked_objects") else []
        )
        monkeypatch.setattr("sys.argv", argv)

        if damage == "valid":
            module.main()
            command = marker.read_text()
            for name in names:
                assert str((tmp_path / "local/roms" / target / name).resolve()) in command
        else:
            with pytest.raises(ValueError, match="firmware"):
                module.main()
            assert not marker.exists()
