"""Current-host boundary recovery, never a clean-host installation claim."""

import hashlib
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest
from native import tool_path
from references import Resource
from setup import DownloadGateway

ROOT = Path(__file__).resolve().parents[2]
ROM_BYTES = {"bas11.rom": b"original BASIC fixture", "extbas10.rom": b"original extended fixture"}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "new project with spaces"
    shutil.copytree(
        ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(ROOT / "examples/first-screen", root / "examples/first-screen")
    shutil.copyfile(ROOT / "resources.json", root / "resources.json")
    directory = root / "local/roms/coco1"
    directory.mkdir(parents=True)
    archive = directory / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for name, data in ROM_BYTES.items():
            output.writestr(name, data)
        output.writestr("../escape.rom", b"must never be extracted")
    profile = {
        "url": "https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/fixture.zip",
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "members": [
            {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in ROM_BYTES.items()
        ],
    }
    (root / "roms.json").write_text(json.dumps({"coco1": profile}))
    return root


def run(root: Path, script: str, *args: str, env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / script), *args],
        cwd=root.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def prepare(root: Path) -> None:
    result = run(root, "setup.py", "--target", "coco1", "--roms-only")
    assert result.returncode == 0, result.stderr
    for name, expected in ROM_BYTES.items():
        assert (root / "local/roms/coco1" / name).read_bytes() == expected
    assert not (root / "local/roms/escape.rom").exists()


class DescribeCurrentHostRecovery:
    def should_preserve_owner_projects_across_setup_and_recovery(self, workspace: Path) -> None:
        notes = workspace / "projects/demo/PROJECT.md"
        notes.parent.mkdir(parents=True)
        original = b"# Demo\nTarget: CoCo 1\nOwner fixture: keep this exact note.\n"
        notes.write_bytes(original)

        result = run(workspace, "setup.py", "--target", "coco1", "--guidance-only")
        assert result.returncode == 0, result.stderr
        assert notes.read_bytes() == original
        assert not (workspace / "local/PROJECT.md").exists()
        prepare(workspace)
        assert notes.read_bytes() == original
        assert not (workspace / "local/references").exists()

    def should_restore_partial_firmware_and_preserve_corruption_until_removed(
        self, workspace: Path
    ) -> None:
        prepare(workspace)
        basic = workspace / "local/roms/coco1/bas11.rom"
        extended = workspace / "local/roms/coco1/extbas10.rom"
        extended.unlink()
        prepare(workspace)
        basic.write_bytes(b"owner supplied different bytes")
        extended.unlink()

        result = run(workspace, "setup.py", "--target", "coco1", "--roms-only")
        assert result.returncode == 1
        assert "existing ROM differs" in result.stderr
        assert basic.read_bytes() == b"owner supplied different bytes"
        assert not extended.exists()
        basic.unlink()  # Deliberate removal of our damaged fixture, not user firmware.
        prepare(workspace)

    def should_recover_from_a_damaged_archive_without_publishing_members(
        self, workspace: Path
    ) -> None:
        archive = workspace / "local/roms/coco1/source.zip"
        good = archive.read_bytes()
        archive.write_bytes(b"interrupted cache")

        result = run(workspace, "setup.py", "--target", "coco1", "--roms-only")
        assert result.returncode == 1
        assert "checksum mismatch" in result.stderr
        assert archive.read_bytes() == b"interrupted cache"
        assert list(archive.parent.iterdir()) == [archive]
        archive.write_bytes(good)
        prepare(workspace)

    def should_gate_real_launcher_then_resume_with_absolute_firmware_paths(
        self, workspace: Path
    ) -> None:
        assembler = tool_path("lwasm", workspace)
        assert assembler, "This boundary check requires an already installed lwasm"
        recorder = workspace / "record-xroar"
        marker = workspace / "launched"
        recorder.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$LAUNCH_MARKER"\n')
        recorder.chmod(0o755)
        env = {
            **os.environ,
            "LWASM": assembler,
            "XROAR": str(recorder),
            "LAUNCH_MARKER": str(marker),
        }
        project = str(workspace / "examples/first-screen")
        for args, status in ((["--help"], 0), (["unknown"], 2), (["run", project, "--x"], 2)):
            result = run(workspace, "coco.py", *args, env=env)
            assert result.returncode == status
            assert not marker.exists()
            assert not (workspace / "build").exists()
        prepare(workspace)
        extended = workspace / "local/roms/coco1/extbas10.rom"
        for damage in (None, b"x" * len(ROM_BYTES["extbas10.rom"])):
            if damage is None:
                extended.unlink()
            else:
                extended.write_bytes(damage)
            result = run(workspace, "coco.py", "run", project, env=env)
            assert result.returncode != 0
            assert "do not launch XRoar" in result.stderr
            assert not marker.exists()
        extended.unlink()
        prepare(workspace)
        result = run(workspace, "coco.py", "run", project, env=env)
        assert result.returncode == 0, result.stderr
        args = marker.read_text().splitlines()
        for flag, name in (("-bas", "bas11.rom"), ("-extbas", "extbas10.rom")):
            assert args[args.index(flag) + 1] == str(workspace / "local/roms/coco1" / name)
        assert args[args.index("-machine") + 1] == "cocous"
        assert args[args.index("-ram") + 1] == "32"

    def should_retry_a_bad_http_download_and_reuse_verified_bytes_offline(
        self, tmp_path: Path
    ) -> None:
        good = b"%PDF-1.4\nOriginal transport fixture, not a parseable reference.\n"
        payload = [b"truncated wrong bytes"]

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(payload[0])

            def log_message(self, format: str, *args: object) -> None:
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever)
        worker.start()
        resource = Resource(
            id="transport-fixture",
            title="Original transport fixture",
            url=f"http://127.0.0.1:{server.server_port}/fixture.pdf",
            sha256=hashlib.sha256(good).hexdigest(),
        )
        destination = tmp_path / "download/source.pdf"
        gateway = DownloadGateway()
        try:
            with pytest.raises(ValueError, match="checksum"):
                gateway.fetch(resource, destination)
            assert list(destination.parent.iterdir()) == []
            payload[0] = good
            gateway.fetch(resource, destination)
        finally:
            server.shutdown()
            worker.join()
            server.server_close()
        gateway.fetch(resource, destination)
        assert destination.read_bytes() == good
