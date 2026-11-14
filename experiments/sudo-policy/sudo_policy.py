"""Original bounded tests of real Ubuntu sudo policy and bootstrap prerequisites."""

import hashlib
import json
import subprocess
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "ubuntu@sha256:2198e4c65076e9cb0b3d695219df667c0e3b0072da64ca3c2648aca17dcecaf5"
BOUNDARY = "        echo 'Installing uv with its official installer.'\n"
NOTES = b"# Existing project\n\nOwner fixture: preserve these exact bytes.\nTarget: coco2\n"


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

    def run(self, label: str, args: list[str], expected: int = 0) -> str:
        start = time.monotonic()
        log = self.output / f"{label}.log"
        status: int | str = "timeout"
        try:
            with log.open("w") as stream:
                result = subprocess.run(
                    args,
                    cwd=ROOT,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    timeout=300,
                    check=False,
                )
            status = result.returncode
        finally:
            self.commands.append(
                {
                    "label": label,
                    "argv": args,
                    "exit": status,
                    "seconds": round(time.monotonic() - start, 2),
                }
            )
            (self.output / "commands.json").write_text(json.dumps(self.commands, indent=2) + "\n")
            print(f"{label}: {status} ({self.commands[-1]['seconds']}s)", flush=True)
        assert status == expected, f"See {log}"
        return log.read_text()

    def shell(
        self, name: str, label: str, script: str, user: str = "root", expected: int = 0
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
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                name,
                "sh",
                "-ec",
                script,
            ],
            expected,
        )

    def capture(self) -> Path:
        source = (ROOT / "scripts/bootstrap.sh").read_bytes()
        inputs = self.output / "input"
        (inputs / "scripts").mkdir(parents=True)
        (inputs / "local").mkdir()
        (inputs / "scripts/bootstrap.sh").write_bytes(source)
        (inputs / "scripts/prerequisites.sh").write_text(prerequisite_prefix(source.decode()))
        (inputs / "local/PROJECT.md").write_bytes(NOTES)
        (self.output / "validate.py").write_bytes(Path(__file__).read_bytes())
        self.run("git-head", ["git", "rev-parse", "HEAD"])
        self.run("git-status", ["git", "status", "--short"])
        self.run("image-pull", ["docker", "pull", "--platform", "linux/arm64", IMAGE])
        self.run("image-inspect", ["docker", "image", "inspect", IMAGE])
        self.run("docker-version", ["docker", "version"])
        return inputs

    def unchanged(self, name: str, phase: str) -> None:
        label = f"{name}-{phase}-notes"
        self.shell(name, label, "cat /work/local/PROJECT.md", "learner")
        assert (self.output / f"{label}.log").read_bytes() == NOTES, "Project note bytes changed"
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
                    "--platform",
                    "linux/arm64",
                    "--workdir",
                    "/work",
                    IMAGE,
                    "sleep",
                    "1800",
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
        finally:
            self.run(f"{name}-cleanup", ["docker", "rm", "-f", name])

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
                        "scope": "curl/CA prerequisite only",
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
                        "error": str(error),
                        "type": type(error).__name__,
                        "traceback": traceback.format_exc(),
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
