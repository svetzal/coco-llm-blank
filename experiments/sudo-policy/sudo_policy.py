"""Original bounded tests of real Ubuntu sudo policy and bootstrap recovery through CoCo 2 checkpoints."""

import hashlib
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "ubuntu@sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5"
BOUNDARY = "        echo 'Installing uv with its official installer.'\n"
NOTES = (
    b"# Existing project\n\nOwner fixture: preserve these exact bytes.\nTarget: CoCo 2\n"
    b"Experiment configuration: cocous, 6847, 6809, 32 KiB, NTSC, stock clock.\n"
    b"Direct DECB loading; no controls. Agent-selected test configuration.\n"
)
EDIT = b"\n## Edited after recovery\n\nPreserve this later owner-note fixture too.\n"


def absent_tools(names: str) -> str:
    """Fail explicitly for each unexpected executable, independent of errexit."""
    return f'for tool in {names}; do if command -v "$tool"; then echo "Unexpected tool: $tool" >&2; exit 1; fi; done'


def prerequisite_prefix(source: str) -> str:
    """Keep production bytes through apt; close the two outer conditionals only."""
    if source.count(BOUNDARY) != 1:
        raise ValueError("Bootstrap boundary changed; inspect before adapting the experiment")
    return source.split(BOUNDARY)[0] + "    fi\nfi\n"


class Experiment:
    """Record commands and bounded Docker processes in one unique evidence directory."""

    def __init__(self) -> None:
        self.name = f"sudo-policy-{time.time_ns()}"
        self.output = ROOT / "build/sudo-policy" / self.name
        self.output.mkdir(parents=True)
        self.commands: list[dict] = []
        self.stage = "capture"
        self.prior_failure = None

    def run(self, label: str, args: list[str], expected: int = 0, timeout: int = 300) -> str:
        self.stage = label
        start = time.monotonic()
        log = self.output / f"{label}.log"
        status: int | str = "interrupted"
        try:
            with log.open("w") as stream:
                result = subprocess.run(
                    args,
                    cwd=ROOT,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
            status = result.returncode
        except subprocess.TimeoutExpired:
            status = "timeout"
            raise
        finally:
            self.commands.append(
                {
                    "label": label,
                    "argv": args,
                    "exit": status,
                    "timeout_seconds": timeout,
                    "seconds": round(time.monotonic() - start, 2),
                }
            )
            (self.output / "commands.json").write_text(json.dumps(self.commands, indent=2) + "\n")
            print(f"{label}: {status} ({self.commands[-1]['seconds']}s)", flush=True)
        assert status == expected, f"See {log}"
        return log.read_text()

    def shell(
        self,
        name: str,
        label: str,
        script: str,
        user: str = "root",
        expected: int = 0,
        timeout: int = 300,
    ) -> str:
        return self.run(
            label,
            [
                "docker",
                "exec",
                "--user",
                user,
                "--env",
                "HOME=/home/learner",
                "--env",
                "PATH=/home/learner/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                name,
                "sh",
                "-ec",
                script,
            ],
            expected,
            timeout,
        )

    def capture(self) -> Path:
        source = (ROOT / "scripts/bootstrap.sh").read_bytes()
        inputs = self.output / "input"
        inputs.mkdir()
        paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
        for name in filter(None, paths):
            if Path(name).parts[0] in {"local", "build", ".venv", ".git"}:
                continue
            original = ROOT / name
            destination = inputs / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(original.read_bytes())
            destination.chmod(original.stat().st_mode & 0o777)
        (inputs / "local").mkdir()
        (inputs / "scripts/bootstrap.sh").write_bytes(source)
        (inputs / "scripts/prerequisites.sh").write_text(prerequisite_prefix(source.decode()))
        (inputs / "projects/demo").mkdir(parents=True, exist_ok=True)
        (inputs / "projects/demo/PROJECT.md").write_bytes(NOTES)
        (self.output / "validate.py").write_bytes(Path(__file__).read_bytes())
        self.run("git-head", ["git", "rev-parse", "HEAD"])
        self.run("git-status", ["git", "status", "--short"])
        self.run("image-pull", ["docker", "pull", "--platform", "linux/arm64", IMAGE])
        self.run("image-inspect", ["docker", "image", "inspect", IMAGE])
        self.run("docker-version", ["docker", "version"])
        return inputs

    def notes(self, name: str, phase: str, expected: bytes = NOTES) -> None:
        label = f"{name}-{phase}-notes"
        self.shell(name, label, "cat /work/projects/demo/PROJECT.md", "learner")
        assert (self.output / f"{label}.log").read_bytes() == expected, "Project note bytes changed"

    def unchanged(self, name: str, phase: str) -> None:
        self.notes(name, phase)
        self.shell(
            name,
            f"{name}-{phase}-no-readiness",
            """
            test ! -e /work/.venv
            test ! -e /work/local/roms
            test ! -e /work/local/toolchain
        """
            + absent_tools("uv xroar lwasm"),
            "learner",
        )

    def journey(self, policy: str, inputs: Path) -> None:
        name = f"{self.name}-{policy}"
        try:
            self.run(
                f"{name}-create",
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    name,
                    "--label",
                    f"coco.sudo-policy.owner={name}",
                    "--platform",
                    "linux/arm64",
                    "--workdir",
                    "/work",
                    IMAGE,
                    "sleep",
                    "7200",
                ],
            )
            self.run(f"{name}-copy", ["docker", "cp", f"{inputs}/.", f"{name}:/work"])
            rule = "PASSWD: ALL" if policy == "password" else "NOPASSWD: !ALL"
            self.shell(
                name,
                f"{name}-admin-prepare",
                f"""
                apt-get update
                DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends sudo
                useradd --create-home --shell /bin/sh learner
                chown -R learner:learner /work
                printf 'learner ALL=(ALL) {rule}\\n' > /etc/sudoers.d/learner
                chmod 0440 /etc/sudoers.d/learner
                visudo -cf /etc/sudoers
                cat /etc/sudoers.d/learner
            """,
            )
            self.shell(
                name,
                f"{name}-preflight",
                """
                test "$(id -u)" -ne 0
                id; uname -m; cat /etc/os-release
                command -v sudo
                test ! -e /etc/ssl/certs/ca-certificates.crt
                sudo -k
            """
                + absent_tools("curl uv"),
                "learner",
            )
            self.shell(name, f"{name}-policy", "sudo -l -U learner")
            failure = self.shell(
                name, f"{name}-failure", "sh /work/scripts/bootstrap.sh coco2", "learner", 1
            )
            for message in (
                "Could not install curl and ca-certificates",
                "non-interactive sudo",
                "rerun bootstrap",
            ):
                assert message in failure
            assert "Tools and firmware are ready" not in failure
            assert "Installing uv" not in failure
            self.unchanged(name, "failed")
            self.shell(
                name,
                f"{name}-admin-correct",
                """
                printf 'learner ALL=(ALL) NOPASSWD: ALL\\n' > /etc/sudoers.d/learner
                visudo -cf /etc/sudoers
                cat /etc/sudoers.d/learner
            """,
            )
            recovery = self.shell(
                name, f"{name}-recovery", "sh /work/scripts/prerequisites.sh coco2", "learner"
            )
            assert "Installing curl and CA certificates with apt" in recovery
            assert "Tools and firmware are ready" not in recovery
            self.shell(
                name,
                f"{name}-installed",
                """
                curl --version
                dpkg-query -W -f='${Package} ${Status} ${Version}\\n' curl ca-certificates sudo
                test -s /etc/ssl/certs/ca-certificates.crt
                curl --fail --location --silent --show-error https://astral.sh/uv/install.sh \
                    -o /tmp/uv-installer-not-executed.sh
                test -s /tmp/uv-installer-not-executed.sh
                sha256sum /tmp/uv-installer-not-executed.sh
            """,
                "learner",
            )
            self.unchanged(name, "recovered")
            self.shell(name, f"{name}-sudo-help", "sudo --version; sudo --help")
            self.complete(name)
        finally:
            self.cleanup_owned(name, sys.exception())

    def cleanup_owned(self, name: str, preceding: BaseException | None) -> None:
        """Find owned containers even when create/start did not return success."""
        prior_stage = self.stage
        try:
            identities = self.run(
                f"{name}-cleanup-discover",
                ["docker", "ps", "-aq", "--filter", f"label=coco.sudo-policy.owner={name}"],
            ).split()
            for identity in identities:
                self.run(f"{name}-cleanup", ["docker", "rm", "-f", identity])
        except BaseException:
            if preceding is not None:
                self.prior_failure = {
                    "stage": prior_stage,
                    "type": type(preceding).__name__,
                    "error": str(preceding),
                }
            raise
        else:
            if preceding is not None:
                self.stage = prior_stage

    def bootstrap(self, name: str, phase: str, expected_notes: bytes, timeout: int = 300) -> None:
        """Retain note bytes on failure as well as success, without losing the failed stage."""
        self.notes(name, f"before-{phase}", expected_notes)
        try:
            output = self.shell(
                name, f"{name}-{phase}", "sh scripts/bootstrap.sh coco2", "learner", timeout=timeout
            )
            assert "Tools and firmware are ready" in output, "Bootstrap omitted readiness"
        except BaseException:
            failed_stage = self.stage
            try:
                self.notes(name, f"failed-{phase}", expected_notes)
            finally:
                self.stage = failed_stage
            raise
        self.notes(name, f"after-{phase}", expected_notes)

    def complete(self, name: str) -> None:
        """Run production setup and independent existing scene checks after correction."""
        self.bootstrap(name, "bootstrap", NOTES, timeout=2400)
        self.shell(
            name,
            f"{name}-firmware",
            "uv run python scripts/doctor.py --profile demo --target coco2",
            "learner",
        )
        self.shell(
            name,
            f"{name}-moving-objects",
            "uv run python scripts/coco.py check examples/moving-objects --target coco2",
            "learner",
            timeout=840,
        )
        self.shell(
            name,
            f"{name}-game-check",
            "uv run python scripts/coco.py check examples/collect-room --target coco2",
            "learner",
            timeout=1800,
        )
        self.shell(
            name,
            f"{name}-edit-notes",
            "printf '\\n## Edited after recovery\\n\\nPreserve this later owner-note fixture too.\\n' >> projects/demo/PROJECT.md",
            "learner",
        )
        self.bootstrap(name, "rerun", NOTES + EDIT)
        self.shell(
            name,
            f"{name}-versions",
            "uv --version; uv run python --version; local/toolchain/bin/lwasm --version; "
            "local/toolchain/bin/xroar --version; "
            "uv run python scripts/doctor.py --profile demo --target coco2",
            "learner",
        )
        self.run(
            f"{name}-collect-game",
            [
                "docker",
                "cp",
                f"{name}:/work/build/collect-room",
                str(self.output / f"{name}-collect-room"),
            ],
        )
        self.run(
            f"{name}-collect",
            [
                "docker",
                "cp",
                f"{name}:/work/build/moving-objects",
                str(self.output / f"{name}-moving-objects"),
            ],
        )

    def execute(self) -> None:
        phase = "capture"
        try:
            inputs = self.capture()
            for policy in ("password", "denied"):
                phase = policy
                self.journey(policy, inputs)
            (self.output / "passed.json").write_text(
                json.dumps(
                    {
                        "policies": ["password", "denied"],
                        "scope": "sudo recovery, complete bootstrap, CoCo 2 checkpoints, edited-note rerun",
                    },
                    indent=2,
                )
                + "\n"
            )
        except BaseException as error:
            (self.output / "failure.json").write_text(
                json.dumps(
                    {
                        "phase": phase,
                        "stage": self.stage,
                        "error": str(error),
                        "type": type(error).__name__,
                        "traceback": traceback.format_exc(),
                        "prior_failure": self.prior_failure,
                    },
                    indent=2,
                )
                + "\n"
            )
            raise
        finally:
            hashes = {
                str(p.relative_to(self.output)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(self.output.rglob("*"))
                if p.is_file()
            }
            (self.output / "hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
            print(self.output, flush=True)


if __name__ == "__main__":
    Experiment().execute()
