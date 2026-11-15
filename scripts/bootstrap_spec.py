"""Exercise bootstrap through its shell boundary without host installations."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from roms import TARGETS

SCRIPT = Path(__file__).with_name("bootstrap.sh")


@pytest.fixture
def bootstrap_workspace(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    project = tmp_path / "new project"
    (project / "scripts").mkdir(parents=True)
    shutil.copyfile(SCRIPT, project / "scripts/bootstrap.sh")
    commands = tmp_path / "commands"
    commands.mkdir()
    log = tmp_path / "calls"
    uv = commands / "uv-template"
    uv.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$BOOTSTRAP_LOG"\nexit "${UV_STATUS:-0}"\n')
    uv.chmod(0o755)
    # An allowlist prevents host curl, uv, brew, apt, or sudo leaking into tests.
    for name in ("sh", "dirname", "cp", "chmod", "mktemp", "rm"):
        executable = shutil.which(name)
        assert executable is not None
        (commands / name).symlink_to(executable)
    uname = commands / "uname"
    uname.write_text(
        '#!/bin/sh\ncase "$1" in\n'
        '-s) echo "${TEST_SYSTEM:-Linux}";;\n'
        '-m) echo "${TEST_MACHINE:-x86_64}";;\nesac\n'
    )
    uname.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "PATH": str(commands), "HOME": str(home), "BOOTSTRAP_LOG": str(log)}
    return project, env


def run_bootstrap(
    project: Path, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/sh", str(project / "scripts/bootstrap.sh"), *args],
        cwd=project.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


class DescribeBootstrap:
    @pytest.mark.parametrize("machine", ["x86_64", "i386", "unknown"])
    @pytest.mark.parametrize("uv_present", [False, True])
    def should_reject_non_arm64_macos_before_any_setup(
        self, bootstrap_workspace: tuple[Path, dict[str, str]], machine: str, uv_present: bool
    ) -> None:
        project, env = bootstrap_workspace
        env.update(TEST_SYSTEM="Darwin", TEST_MACHINE=machine)
        commands = Path(env["PATH"])
        for name in ("brew", "curl", "apt-get", "uv"):
            if name == "uv" and not uv_present:
                continue
            shutil.copyfile(commands / "uv-template", commands / name)
            (commands / name).chmod(0o755)

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 1
        assert "Intel Macs are unsupported" in result.stderr
        assert "native arm64 terminal" in result.stderr
        assert not Path(env["BOOTSTRAP_LOG"]).exists()
        assert not (project / "local").exists()
        assert not (project / ".venv").exists()

    @pytest.mark.parametrize(
        "system,machine", [("Darwin", "arm64"), ("Linux", "x86_64"), ("Linux", "aarch64")]
    )
    def should_continue_setup_on_supported_architectures(
        self, bootstrap_workspace: tuple[Path, dict[str, str]], system: str, machine: str
    ) -> None:
        project, env = bootstrap_workspace
        env.update(TEST_SYSTEM=system, TEST_MACHINE=machine)
        commands = Path(env["PATH"])
        shutil.copyfile(commands / "uv-template", commands / "uv")
        (commands / "uv").chmod(0o755)

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 0, result.stderr
        assert (
            "scripts/doctor.py --profile demo --target coco1"
            in Path(env["BOOTSTRAP_LOG"]).read_text()
        )

    @pytest.mark.parametrize("target", TARGETS)
    def should_prepare_selected_target_firmware_without_book_conversion(
        self, bootstrap_workspace: tuple[Path, dict[str, str]], target: str
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        shutil.copyfile(commands / "uv-template", commands / "uv")
        (commands / "uv").chmod(0o755)

        result = run_bootstrap(project, env, target)

        assert result.returncode == 0, result.stderr
        assert Path(env["BOOTSTRAP_LOG"]).read_text().splitlines() == [
            "sync --locked",
            f"run python scripts/setup.py --target {target} --guidance-only",
            "run python scripts/native.py",
            f"run python scripts/setup.py --target {target} --roms-only",
            f"run python scripts/doctor.py --profile demo --target {target}",
        ]

    def should_stop_before_readiness_when_firmware_preparation_fails(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        uv = commands / "uv"
        uv.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$BOOTSTRAP_LOG"\n'
            'case "$*" in *--roms-only*) echo "firmware unavailable" >&2; exit 7;; esac\n'
        )
        uv.chmod(0o755)

        result = run_bootstrap(project, env, "coco2")

        assert result.returncode == 7
        assert "firmware unavailable" in result.stderr
        assert "Tools and firmware are ready" not in result.stdout
        assert "doctor.py" not in Path(env["BOOTSTRAP_LOG"]).read_text()

    def should_stop_before_readiness_when_final_validation_fails(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        uv = commands / "uv"
        uv.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$BOOTSTRAP_LOG"\n'
            'case "$*" in *scripts/doctor.py*) echo "validation failed" >&2; exit 7;; esac\n'
        )
        uv.chmod(0o755)

        result = run_bootstrap(project, env, "coco2")

        assert result.returncode == 7
        assert "validation failed" in result.stderr
        assert "Tools and firmware are ready" not in result.stdout
        assert Path(env["BOOTSTRAP_LOG"]).read_text().splitlines()[-2:] == [
            "run python scripts/setup.py --target coco2 --roms-only",
            "run python scripts/doctor.py --profile demo --target coco2",
        ]

    def should_install_missing_uv_with_the_available_host_manager(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        brew = commands / "brew"
        brew.write_text(
            '#!/bin/sh\n[ "$*" = "install uv" ] || exit 9\n'
            'cp "$(dirname "$0")/uv-template" "$(dirname "$0")/uv"\n'
            'chmod +x "$(dirname "$0")/uv"\n'
        )
        brew.chmod(0o755)

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 0, result.stderr
        assert "Installing uv with Homebrew" in result.stdout
        assert Path(env["BOOTSTRAP_LOG"]).exists()

    def should_stop_on_environment_failure_before_setup(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        shutil.copyfile(commands / "uv-template", commands / "uv")
        (commands / "uv").chmod(0o755)
        env["UV_STATUS"] = "7"

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 7
        assert Path(env["BOOTSTRAP_LOG"]).read_text().splitlines() == ["sync --locked"]

    @pytest.mark.parametrize("args", [[], ["unknown"], ["coco1", "extra"]])
    def should_reject_invalid_choices_before_installation(
        self, bootstrap_workspace: tuple[Path, dict[str, str]], args: list[str]
    ) -> None:
        project, env = bootstrap_workspace

        result = run_bootstrap(project, env, *args)

        assert result.returncode == 2
        assert not Path(env["BOOTSTRAP_LOG"]).exists()

    def should_explain_usage_without_preparing_an_environment(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace

        result = run_bootstrap(project, env, "--help")

        assert result.returncode == 0
        assert "coco1|coco2|coco2b|coco3" in result.stdout
        assert not Path(env["BOOTSTRAP_LOG"]).exists()

    def should_use_the_official_installer_when_no_host_manager_is_available(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        curl = commands / "curl"
        installer = commands / "installer"
        env["BOOTSTRAP_BIN"] = str(commands)
        installer.write_text(
            '#!/bin/sh\ncp "$BOOTSTRAP_BIN/uv-template" "$BOOTSTRAP_BIN/uv"\n'
            'chmod +x "$BOOTSTRAP_BIN/uv"\n'
        )
        curl.write_text(
            "#!/bin/sh\n"
            '[ "$5" = "https://astral.sh/uv/install.sh" ] || exit 8\n'
            'cp "$(dirname "$0")/installer" "$7"\n'
        )
        curl.chmod(0o755)

        result = run_bootstrap(project, env, "coco3")

        assert result.returncode == 0, result.stderr
        assert "Installing uv with its official installer" in result.stdout
        assert "--target coco3" in Path(env["BOOTSTRAP_LOG"]).read_text()

    def should_stop_when_the_installer_download_fails(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        curl = commands / "curl"
        curl.write_text("#!/bin/sh\nexit 22\n")
        curl.chmod(0o755)

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 22
        assert not Path(env["BOOTSTRAP_LOG"]).exists()


@pytest.fixture
def apt_workspace(bootstrap_workspace: tuple[Path, dict[str, str]]) -> tuple[Path, dict[str, str]]:
    project, env = bootstrap_workspace
    commands = Path(env["PATH"])
    env["BOOTSTRAP_BIN"] = str(commands)
    scripts = {
        "id": '#!/bin/sh\necho "${TEST_UID:-0}"\n',
        "apt-get": (
            '#!/bin/sh\nprintf "apt %s\\n" "$*" >> "$BOOTSTRAP_LOG"\n'
            '[ "$*" != "${APT_FAIL:-}" ] || exit 42\n'
            'if [ "$*" = "install -y curl ca-certificates" ]; then\n'
            'cp "$BOOTSTRAP_BIN/curl-template" "$BOOTSTRAP_BIN/curl"\nfi\n'
        ),
        "curl-template": (
            '#!/bin/sh\n[ "$5" = "https://astral.sh/uv/install.sh" ] || exit 8\n'
            'cp "$BOOTSTRAP_BIN/installer" "$7"\n'
        ),
        "installer": (
            '#!/bin/sh\ncp "$BOOTSTRAP_BIN/uv-template" "$BOOTSTRAP_BIN/uv"\n'
            'chmod +x "$BOOTSTRAP_BIN/uv"\n'
        ),
    }
    for name, content in scripts.items():
        (commands / name).write_text(content)
        (commands / name).chmod(0o755)
    assert shutil.which("curl", path=env["PATH"]) is None
    return project, env


class DescribeAptPrerequisites:
    @pytest.mark.parametrize("use_sudo", [False, True])
    def should_provision_missing_curl_and_continue_through_uv(
        self, apt_workspace: tuple[Path, dict[str, str]], use_sudo: bool
    ) -> None:
        project, env = apt_workspace
        if use_sudo:
            env["TEST_UID"] = "1000"
            sudo = Path(env["PATH"]) / "sudo"
            sudo.write_text('#!/bin/sh\n[ "$1" = "-n" ] || exit 9\nshift\nexec "$@"\n')
            sudo.chmod(0o755)

        result = run_bootstrap(project, env, "coco2")

        assert result.returncode == 0, result.stderr
        calls = Path(env["BOOTSTRAP_LOG"]).read_text()
        assert "apt update\napt install -y curl ca-certificates\n" in calls
        assert "sync --locked" in calls
        assert "scripts/doctor.py --profile demo --target coco2" in calls
        assert "Tools and firmware are ready" in result.stdout

    @pytest.mark.parametrize("failure", ["update", "install -y curl ca-certificates"])
    def should_stop_when_apt_fails(
        self, apt_workspace: tuple[Path, dict[str, str]], failure: str
    ) -> None:
        project, env = apt_workspace
        env["APT_FAIL"] = failure

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 1
        assert "Resolve the apt error above" in result.stderr
        assert "Tools and firmware are ready" not in result.stdout
        calls = Path(env["BOOTSTRAP_LOG"]).read_text()
        assert "sync --locked" not in calls
        if failure == "update":
            assert "apt install" not in calls

    @pytest.mark.parametrize("missing", ["apt-get", "sudo", "sudo-access"])
    def should_explain_unavailable_prerequisite_installation(
        self, apt_workspace: tuple[Path, dict[str, str]], missing: str
    ) -> None:
        project, env = apt_workspace
        commands = Path(env["PATH"])
        env["TEST_UID"] = "1000"
        if missing == "apt-get":
            (commands / "apt-get").unlink()
        elif missing == "sudo-access":
            (commands / "sudo").write_text('#!/bin/sh\necho "sudo denied" >&2\nexit 1\n')
            (commands / "sudo").chmod(0o755)

        result = run_bootstrap(project, env, "coco1")

        assert result.returncode == 1
        assert "rerun bootstrap" in result.stderr
        assert (
            "system package manager" in result.stderr
            if missing == "apt-get"
            else ("non-interactive sudo" in result.stderr)
        )
        assert "Tools and firmware are ready" not in result.stdout
        assert not Path(env["BOOTSTRAP_LOG"]).exists()

    @pytest.mark.parametrize("mode", ["uv", "brew", "help"])
    def should_skip_apt_for_fast_paths_and_help(
        self, apt_workspace: tuple[Path, dict[str, str]], mode: str
    ) -> None:
        project, env = apt_workspace
        commands = Path(env["PATH"])
        if mode == "uv":
            shutil.copyfile(commands / "uv-template", commands / "uv")
            (commands / "uv").chmod(0o755)
        elif mode == "brew":
            (commands / "brew").write_text(
                '#!/bin/sh\n[ "$*" = "install uv" ] || exit 9\n'
                'cp "$BOOTSTRAP_BIN/uv-template" "$BOOTSTRAP_BIN/uv"\n'
                'chmod +x "$BOOTSTRAP_BIN/uv"\n'
            )
            (commands / "brew").chmod(0o755)

        result = run_bootstrap(project, env, "--help" if mode == "help" else "coco1")

        assert result.returncode == 0, result.stderr
        log = Path(env["BOOTSTRAP_LOG"])
        if mode == "help":
            assert not log.exists()
        else:
            assert "apt " not in log.read_text()
            assert "sync --locked" in log.read_text()
        assert not (commands / "curl").exists()


class DescribeSudoRecovery:
    """A refused sudo stops bootstrap; a corrected policy lets the rerun finish."""

    OWNER_NOTE = b"# Demo\n\nTarget: CoCo 2\nOwner note, kept byte for byte.  \n"

    @pytest.mark.parametrize(
        "refusal",
        [
            "sudo: a password is required",
            "Sorry, user learner is not allowed to execute '/usr/bin/apt-get update' as root.",
        ],
        ids=["password-required", "command-denied"],
    )
    def should_finish_after_sudo_is_corrected_and_keep_project_notes(
        self, apt_workspace: tuple[Path, dict[str, str]], refusal: str
    ) -> None:
        project, env = apt_workspace
        env["TEST_UID"] = "1000"
        notes = project / "projects/demo/README.md"
        notes.parent.mkdir(parents=True)
        notes.write_bytes(self.OWNER_NOTE)
        sudo = Path(env["PATH"]) / "sudo"
        sudo.write_text(f'#!/bin/sh\necho "{refusal}" >&2\nexit 1\n')
        sudo.chmod(0o755)

        refused = run_bootstrap(project, env, "coco2")

        assert refused.returncode == 1
        assert refusal in refused.stderr
        assert "non-interactive sudo" in refused.stderr
        assert "rerun bootstrap" in refused.stderr
        assert "Installing uv" not in refused.stdout
        assert "Tools and firmware are ready" not in refused.stdout
        assert not Path(env["BOOTSTRAP_LOG"]).exists()
        assert notes.read_bytes() == self.OWNER_NOTE

        sudo.write_text('#!/bin/sh\n[ "$1" = "-n" ] || exit 9\nshift\nexec "$@"\n')
        recovered = run_bootstrap(project, env, "coco2")
        rerun = run_bootstrap(project, env, "coco2")

        for result in (recovered, rerun):
            assert result.returncode == 0, result.stderr
            assert "Tools and firmware are ready" in result.stdout
        assert "Installing uv" not in rerun.stdout
        calls = Path(env["BOOTSTRAP_LOG"]).read_text()
        assert calls.count("apt install -y curl ca-certificates") == 1
        assert calls.count("sync --locked") == 2
        assert calls.count("scripts/doctor.py --profile demo --target coco2") == 2
        assert notes.read_bytes() == self.OWNER_NOTE
