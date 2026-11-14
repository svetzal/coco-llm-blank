"""Original nonroot onboarding experiment; run from the repository root."""

import hashlib
import io
import json
import subprocess
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = f"nonroot-{time.time_ns()}"
LOCAL = ROOT / "local/research/linux-onboarding" / RUN
BUILD = ROOT / "build/linux-onboarding" / RUN
IMAGE = "ubuntu@sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5"
COMMANDS: list[dict] = []


def run(label: str, args: list[str], expected: int = 0) -> str:
    """Retain command output and status before enforcing its expectation."""
    start = time.monotonic()
    with (BUILD / f"{label}.log").open("w") as log:
        result = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
    COMMANDS.append(
        {
            "label": label,
            "argv": args,
            "exit": result.returncode,
            "seconds": round(time.monotonic() - start, 2),
        }
    )
    (BUILD / "commands.json").write_text(json.dumps(COMMANDS, indent=2) + "\n")
    print(f"{label}: exit {result.returncode}, {COMMANDS[-1]['seconds']}s", flush=True)
    assert result.returncode == expected, f"See {BUILD / f'{label}.log'}"
    return (BUILD / f"{label}.log").read_text()


def snapshot() -> None:
    """Capture each input once; hash the exact bytes placed in the archive."""
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    paths += [
        str(p.relative_to(ROOT))
        for p in (ROOT / "experiments/linux-onboarding").glob("*")
        if p.is_file()
    ]
    hashes = {}
    with tarfile.open(LOCAL / "snapshot.tar", "w") as archive:
        for name in sorted(set(filter(None, paths))):
            if name.split("/")[0] in {"local", "build", ".venv", ".git"}:
                continue
            data = (ROOT / name).read_bytes()
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            entry.mode = (ROOT / name).stat().st_mode & 0o777
            archive.addfile(entry, io.BytesIO(data))
            hashes[name] = hashlib.sha256(data).hexdigest()
    (LOCAL / "snapshot.json").write_text(json.dumps(hashes, indent=2) + "\n")
    run("git-head", ["git", "rev-parse", "HEAD"])
    run("git-status", ["git", "status", "--short"])
    run("git-diff", ["git", "diff", "--binary", "HEAD"])
    run("image-pull", ["docker", "pull", "--platform", "linux/arm64", IMAGE])
    run("image", ["docker", "image", "inspect", IMAGE])
    run("docker-version", ["docker", "version"])
    print(
        f"snapshot: {hashlib.sha256((LOCAL / 'snapshot.tar').read_bytes()).hexdigest()}", flush=True
    )


def inside(container: str, label: str, command: str, expected: int = 0) -> str:
    return run(
        label,
        [
            "docker",
            "exec",
            "--user",
            "learner",
            "--env",
            "HOME=/home/learner",
            "--env",
            "PATH=/home/learner/.local/bin:/usr/local/bin:/usr/bin:/bin",
            container,
            "sh",
            "-ec",
            command,
        ],
        expected,
    )


def journey(container: str, sudo: bool) -> None:
    prefix = "sudo" if sudo else "no-sudo"
    admin = "useradd --create-home --shell /bin/sh learner; "
    if sudo:
        admin += (
            "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y "
            "--no-install-recommends sudo; "
            "printf 'learner ALL=(ALL) NOPASSWD: ALL\\n' > /etc/sudoers.d/learner; "
            "chmod 0440 /etc/sudoers.d/learner; visudo -cf /etc/sudoers.d/learner; "
        )
    admin += "tar xf /snapshot.tar -C /work; chown -R learner:learner /work"
    run(f"{prefix}-admin", ["docker", "exec", container, "sh", "-ec", admin])
    inside(
        container,
        f"{prefix}-preconditions",
        """
        id; cat /etc/os-release; uname -m
        test "$(id -u)" != 0
        for tool in curl uv python3 lwasm xroar; do
            if command -v "$tool"; then echo "Unexpected preinstalled tool: $tool"; exit 1; fi
        done
        test ! -e /etc/ssl/certs/ca-certificates.crt
        test ! -e .venv; test ! -e local
    """
        + ("sudo -n true; sudo -n -l" if sudo else "! command -v sudo"),
    )
    output = inside(
        container,
        f"{prefix}-bootstrap",
        "timeout 2400 sh scripts/bootstrap.sh coco2",
        0 if sudo else 1,
    )
    if not sudo:
        assert "non-interactive sudo" in output and "administrator" in output
        assert "rerun bootstrap" in output and "Tools and firmware are ready" not in output
        inside(
            container,
            "no-sudo-no-readiness",
            "test ! -e .venv; test ! -e local; test ! -e /home/learner/.local/bin/uv",
        )
        return
    assert "Tools and firmware are ready" in output
    inside(
        container,
        "moving-objects",
        "timeout 840 uv run python scripts/coco.py check examples/moving-objects --target coco2",
    )
    inside(
        container,
        "notes-before",
        """
        mkdir -p build/linux-onboarding
        mkdir -p projects/demo
        printf '# Demo\\n\\n## Owner preservation fixture\\n\\nKeep this project note exactly.\\n' > projects/demo/PROJECT.md
        cp projects/demo/PROJECT.md build/linux-onboarding/PROJECT-before.md
    """,
    )
    inside(container, "rerun", "timeout 300 sh scripts/bootstrap.sh coco2")
    inside(
        container,
        "notes-after",
        """
        cmp projects/demo/PROJECT.md build/linux-onboarding/PROJECT-before.md
        cp projects/demo/PROJECT.md build/linux-onboarding/PROJECT-after.md
        uv run python scripts/doctor.py --profile demo --target coco2
        uv --version; uv run python --version
        local/toolchain/bin/lwasm --version; local/toolchain/bin/xroar --version
        du -sh /home/learner/.cache/uv
    """,
    )
    run(
        "collect-build",
        ["docker", "cp", f"{container}:/work/build/.", str(BUILD / "container-build")],
    )
    run(
        "collect-local",
        ["docker", "cp", f"{container}:/work/local/.", str(LOCAL / "container-local")],
    )


def main() -> None:
    LOCAL.mkdir(parents=True)
    BUILD.mkdir(parents=True)
    print(f"Evidence: {BUILD}\nSources: {LOCAL}", flush=True)
    snapshot()
    for sudo in (False, True):
        container = f"coco-linux-{RUN}-{'sudo' if sudo else 'no-sudo'}"
        run(
            f"create-{sudo}",
            [
                "docker",
                "create",
                "--platform",
                "linux/arm64",
                "--name",
                container,
                "--workdir",
                "/work",
                IMAGE,
                "sleep",
                "7200",
            ],
        )
        try:
            run(
                f"copy-{sudo}",
                ["docker", "cp", str(LOCAL / "snapshot.tar"), f"{container}:/snapshot.tar"],
            )
            run(f"start-{sudo}", ["docker", "start", container])
            journey(container, sudo)
        finally:
            run(f"cleanup-{sudo}", ["docker", "rm", "-f", container])
    hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in (LOCAL, BUILD)
        for p in folder.rglob("*")
        if p.is_file()
    }
    (BUILD / "artifact-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(
        "PASS: separate no-sudo control, nonroot bootstrap, CoCo 2 check, note preservation",
        flush=True,
    )


if __name__ == "__main__":
    main()
