"""Exercise missing-image acquisition through the snapshot's process boundary."""

import os
import subprocess

import pytest
import validate


@pytest.mark.parametrize("pull_fails", [False, True])
def should_acquire_missing_image_or_stop_with_retained_failure(tmp_path, monkeypatch, pull_fails):
    root = tmp_path / "checkout"
    root.mkdir()
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        check=True,
        capture_output=True,
    )
    local, build, bin_dir = (tmp_path / name for name in ("local", "build", "bin"))
    for folder in (local, build, bin_dir):
        folder.mkdir()
    docker = bin_dir / "docker"
    docker.write_text("""#!/bin/sh
case "$1" in
pull)
    if [ "$FAIL_PULL" = 1 ]; then echo 'registry unavailable' >&2; exit 23; fi
    touch "$IMAGE_STATE";;
image)
    test -f "$IMAGE_STATE" || exit 24
    echo 'pinned image metadata';;
version) echo 'fixture docker';;
*) exit 25;;
esac
""")
    docker.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("IMAGE_STATE", str(tmp_path / "image-present"))
    monkeypatch.setenv("FAIL_PULL", str(int(pull_fails)))
    for name, value in (("ROOT", root), ("LOCAL", local), ("BUILD", build), ("COMMANDS", [])):
        monkeypatch.setattr(validate, name, value)

    if pull_fails:
        with pytest.raises(AssertionError):
            validate.snapshot()
        assert "registry unavailable" in (build / "image-pull.log").read_text()
        assert not (build / "image.log").exists()
    else:
        validate.snapshot()
        assert "pinned image metadata" in (build / "image.log").read_text()
    assert (local / "snapshot.tar").exists()
