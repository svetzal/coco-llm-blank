"""CLI contracts against real child processes and retained files."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest
import validate_repository as validation


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text("[tool.coverage.report]\nfail_under = 90\n")
    modules = tmp_path / "child_modules"
    modules.mkdir()
    # Real executable boundary: record arguments, write both streams, and fail
    # with an independently selected status. No pytest or Ruff internals mocked.
    source = """import json, os, sys
print(json.dumps(sys.argv[1:]), flush=True)
print("child stderr sentinel", file=sys.stderr, flush=True)
if os.environ.get("CHILD_SIGNAL"):
    os.kill(os.getpid(), int(os.environ["CHILD_SIGNAL"]))
sys.exit(int(os.environ.get("CHILD_STATUS", "0")))
"""
    for name in ("pytest", "ruff"):
        (modules / f"{name}.py").write_text(source)
    monkeypatch.setenv("PYTHONPATH", str(modules))
    monkeypatch.setattr(validation, "ROOT", root)
    return root


def records(root):
    return sorted((root / "build/validation").glob("run-*/*/*.json"))


class DescribeValidationCLI:
    def should_list_every_experiment_without_work(self, checkout, capsys):
        assert validation.main(["list"]) == 0

        text = capsys.readouterr().out
        actual = Path(validation.__file__).resolve().parents[1] / "experiments"
        names = {p.name for p in actual.iterdir() if list(p.glob("*_spec.py"))}
        assert {line.split(":")[0] for line in text.splitlines()[:-1]} == names | {"root"}
        assert "macos-onboarding: no coverage gate; installed lwasm" in text
        assert not (checkout / "build").exists()

    @pytest.mark.parametrize(
        "args", [[], ["run", "typo"], ["run", "sudo-policy", "all"], ["run", "root"]]
    )
    def should_reject_invalid_or_unapproved_work_before_running(self, checkout, args):
        with pytest.raises(SystemExit) as error:
            validation.main(args)

        assert error.value.code == 2
        assert not (checkout / "build").exists()

    def should_select_deduplicate_and_keep_separate_scope_logs(self, checkout):
        config = checkout / "scripts/coverage.ini"
        config.parent.mkdir(parents=True)
        config.write_text("[report]\nfail_under = 90\n")

        assert validation.main(["run", "root", "sudo-policy", "root", "--heavy"]) == 0

        saved = records(checkout)
        assert len(saved) == 6
        covered = json.loads(next(p for p in saved if p.parent.name == "root").read_text())
        assert "--cov=scripts" in covered["command"]
        assert f"--cov-config={config}" in covered["command"]
        policy = json.loads(next(p for p in saved if p.parent.name == "sudo-policy").read_text())
        assert not any(arg.startswith("--cov") for arg in policy["command"])
        assert "child stderr sentinel" in Path(covered["log"]).read_text()
        assert covered["returncode"] == 0

    def should_run_complete_root_integrations_with_opt_in(self, checkout):
        assert validation.main(["run", "root", "--heavy"]) == 0

        command = json.loads(records(checkout)[0].read_text())["command"]
        assert "-m" not in command[3:]
        assert not any(arg.startswith("--ignore") for arg in command)
        assert "--cov=scripts" in command and "--cov=examples" in command
        assert command[3:5] == ["scripts", "examples"]
        assert f"--cov-config={checkout / 'pyproject.toml'}" in command

    def should_run_all_experiments_separately_when_opted_in(self, checkout):
        assert validation.main(["run", "all", "--heavy"]) == 0

        saved = records(checkout)
        assert len(saved) == 3 * 3
        assert "root" not in {p.parent.name for p in saved}
        commands = [json.loads(p.read_text())["command"] for p in saved if p.name == "1.json"]
        assert all(len([a for a in c if a.startswith("experiments/")]) == 1 for c in commands)
        assert not any(a.startswith("--cov") for c in commands for a in c)

    def should_preserve_failure_stop_and_keep_evidence_on_successful_retry(
        self, checkout, monkeypatch
    ):
        monkeypatch.setenv("CHILD_STATUS", "23")

        assert validation.main(["run", "linux-onboarding", "sudo-policy"]) == 23

        failed = records(checkout)
        assert len(failed) == 1
        result = json.loads(failed[0].read_text())
        assert result["returncode"] == 23
        original = Path(result["log"]).read_text()
        assert "child stderr sentinel" in original
        assert "experiments/linux-onboarding" in original
        monkeypatch.setenv("CHILD_STATUS", "0")

        assert validation.main(["run", "linux-onboarding"]) == 0
        assert len(records(checkout)) == 4
        assert Path(result["log"]).read_text() == original

    def should_retain_signal_status_and_return_shell_exit_code(self, checkout, monkeypatch):
        monkeypatch.setenv("CHILD_SIGNAL", str(signal.SIGTERM))

        assert validation.main(["run", "sudo-policy"]) == 128 + signal.SIGTERM

        result = json.loads(records(checkout)[0].read_text())
        assert result["returncode"] == -signal.SIGTERM
        assert "child stderr sentinel" in Path(result["log"]).read_text()

    def should_record_missing_executable(self, checkout, monkeypatch):
        monkeypatch.setattr(validation.sys, "executable", str(checkout / "absent"))

        assert validation.main(["run", "root", "--heavy"]) == 127

        result = json.loads(records(checkout)[0].read_text())
        assert result["returncode"] == 127
        assert "absent" in Path(result["log"]).read_text()

    def should_propagate_failure_through_the_executable_entry_point(self, checkout, monkeypatch):
        script = checkout / "scripts/validate_repository.py"
        script.parent.mkdir()
        script.write_bytes(Path(validation.__file__).read_bytes())
        monkeypatch.setenv("CHILD_STATUS", "19")

        result = subprocess.run(
            [sys.executable, str(script), "run", "sudo-policy"],
            cwd=checkout,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 19
        assert "sudo-policy: exit 19" in result.stdout
        assert json.loads(records(checkout)[0].read_text())["returncode"] == 19
