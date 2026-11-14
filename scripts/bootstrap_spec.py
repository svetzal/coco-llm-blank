"""Exercise bootstrap through its shell boundary without host installations."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

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
    env = {**os.environ, "PATH": f"{commands}:/usr/bin:/bin", "BOOTSTRAP_LOG": str(log)}
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
    def should_prepare_only_the_selected_project_without_downloads(
        self, bootstrap_workspace: tuple[Path, dict[str, str]]
    ) -> None:
        project, env = bootstrap_workspace
        commands = Path(env["PATH"].split(":")[0])
        shutil.copyfile(commands / "uv-template", commands / "uv")
        (commands / "uv").chmod(0o755)

        result = run_bootstrap(project, env, "coco2")

        assert result.returncode == 0, result.stderr
        assert Path(env["BOOTSTRAP_LOG"]).read_text().splitlines() == [
            "sync --locked",
            "run python scripts/setup.py --target coco2 --guidance-only",
            "run python scripts/native.py",
            "run python scripts/doctor.py --profile demo",
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
        assert "coco1|coco2|coco3" in result.stdout
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
