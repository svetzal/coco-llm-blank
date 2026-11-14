"""Fail closed when the production extraction boundary changes."""

import subprocess
from pathlib import Path

import pytest
from sudo_policy import BOUNDARY, NOTES, Experiment, absent_tools, prerequisite_prefix


class DescribePrerequisiteBoundary:
    @pytest.mark.parametrize("source", ["#!/bin/sh\nexit 0\n", BOUNDARY * 2])
    def should_reject_missing_or_ambiguous_boundary(self, source: str) -> None:
        with pytest.raises(ValueError, match="inspect before adapting"):
            prerequisite_prefix(source)

    def should_preserve_real_prefix_and_produce_valid_shell(self, tmp_path: Path) -> None:
        root = Path(__file__).resolve().parents[2]
        source = (root / "scripts/bootstrap.sh").read_text()
        output = tmp_path / "prefix.sh"

        prefix = prerequisite_prefix(source)
        output.write_text(prefix)
        result = subprocess.run(["sh", "-n", str(output)], capture_output=True, check=False)

        assert result.returncode == 0, result.stderr
        assert prefix == source[: source.index(BOUNDARY)] + "    fi\nfi\n"
        assert "apt-get install -y curl ca-certificates" in prefix
        assert "uv sync" not in prefix
        assert "Tools and firmware are ready" not in prefix


class DescribeEvidenceIntegrity:
    @pytest.mark.parametrize("present", ["uv", "xroar", "lwasm", "curl"])
    def should_reject_any_preexisting_tool(self, tmp_path, present):
        executable = tmp_path / present
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        result = subprocess.run(
            ["/bin/sh", "-ec", absent_tools("uv xroar lwasm curl")],
            env={"PATH": str(tmp_path)},
            capture_output=True,
            check=False,
        )
        assert result.returncode == 1
        assert present.encode() in result.stderr

    def should_accept_all_tools_absent(self, tmp_path):
        result = subprocess.run(
            ["/bin/sh", "-ec", absent_tools("uv xroar lwasm curl")],
            env={"PATH": str(tmp_path)},
            check=False,
        )
        assert result.returncode == 0

    def should_reject_newline_changes_and_retain_failure(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()
        monkeypatch.setattr(experiment, "capture", lambda: tmp_path)

        def altered_note(name, label, script, user="root", expected=0):
            (experiment.output / f"{label}.log").write_bytes(NOTES.replace(b"\n", b"\r\n"))
            return NOTES.decode()

        monkeypatch.setattr(experiment, "shell", altered_note)
        monkeypatch.setattr(
            experiment, "journey", lambda policy, inputs: experiment.unchanged(policy, "failed")
        )
        with pytest.raises(AssertionError, match="note bytes changed"):
            experiment.execute()
        import json

        failure = json.loads((experiment.output / "failure.json").read_text())
        assert failure["phase"] == "password"
        assert failure["type"] == "AssertionError"
        assert "Project note bytes changed" in failure["traceback"]
        assert not (experiment.output / "passed.json").exists()
        hashes = json.loads((experiment.output / "hashes.json").read_text())
        assert "failure.json" in hashes


class DescribeBoundedFailureEvidence:
    def should_keep_failed_command_stage_and_output_without_claiming_success(
        self, tmp_path, monkeypatch
    ):
        import json

        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()

        def failing_capture():
            experiment.run("firmware-recovery", ["sh", "-c", "echo 'checksum mismatch'; exit 7"])

        monkeypatch.setattr(experiment, "capture", failing_capture)
        with pytest.raises(AssertionError):
            experiment.execute()

        failure = json.loads((experiment.output / "failure.json").read_text())
        commands = json.loads((experiment.output / "commands.json").read_text())
        assert failure["stage"] == "firmware-recovery"
        assert commands[0]["exit"] == 7
        assert (experiment.output / "firmware-recovery.log").read_text() == "checksum mismatch\n"
        assert not (experiment.output / "passed.json").exists()

    def should_record_a_real_process_timeout(self, tmp_path, monkeypatch):
        import json
        import sys

        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()

        with pytest.raises(subprocess.TimeoutExpired):
            experiment.run(
                "blocked", [sys.executable, "-c", "import time; time.sleep(10)"], timeout=1
            )

        commands = json.loads((experiment.output / "commands.json").read_text())
        assert commands[0]["exit"] == "timeout"
        assert commands[0]["timeout_seconds"] == 1
        assert not (experiment.output / "passed.json").exists()

    @pytest.mark.parametrize("altered", [False, True])
    def should_compare_edited_note_bytes_with_the_preserved_original(
        self, tmp_path, monkeypatch, altered
    ):
        from sudo_policy import EDIT

        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()
        note = tmp_path / "note.md"
        expected = NOTES + EDIT
        note.write_bytes(expected + (b"unwanted rewrite\n" if altered else b""))

        def read_note(name, label, script, user="root", expected=0):
            return experiment.run(label, ["cat", str(note)])

        monkeypatch.setattr(experiment, "shell", read_note)
        if altered:
            with pytest.raises(AssertionError, match="note bytes changed"):
                experiment.notes("container", "after-rerun", expected)
        else:
            experiment.notes("container", "after-rerun", expected)
        assert (
            experiment.output / "container-after-rerun-notes.log"
        ).read_bytes() == note.read_bytes()


class DescribeProjectFixture:
    @pytest.mark.parametrize("suffix", [b"", b"\nOwner has edited this note.\n"])
    def should_survive_real_guidance_setup_without_rewriting(self, tmp_path, suffix):
        import setup
        from sudo_policy import ROOT

        (tmp_path / "local").mkdir()
        note = tmp_path / "local/PROJECT.md"
        original = NOTES + suffix
        note.write_bytes(original)
        (tmp_path / "resources.json").write_bytes((ROOT / "resources.json").read_bytes())

        assert setup.main(["--target", "coco2", "--guidance-only"], tmp_path) == 0
        assert note.read_bytes() == original
        assert (tmp_path / "local/INDEX.md").is_file()

    def should_reject_wrong_target_without_damaging_notes(self, tmp_path):
        import setup

        (tmp_path / "local").mkdir()
        note = tmp_path / "local/PROJECT.md"
        note.write_bytes(NOTES)

        assert setup.main(["--target", "coco1", "--guidance-only"], tmp_path) == 1
        assert note.read_bytes() == NOTES


class DescribeRecoveryFailure:
    @pytest.mark.parametrize("status", [0, 1])
    def should_keep_notes_and_failed_stage_without_accepting_missing_readiness(
        self, tmp_path, monkeypatch, status
    ):
        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()
        note = tmp_path / "PROJECT.md"
        note.write_bytes(NOTES)

        def shell(name, label, script, user="root", expected=0, timeout=300):
            args = (
                ["cat", str(note)] if script.startswith("cat ") else ["sh", "-c", f"exit {status}"]
            )
            return experiment.run(label, args, expected, timeout)

        monkeypatch.setattr(experiment, "shell", shell)
        with pytest.raises(AssertionError):
            experiment.bootstrap("case", "bootstrap", NOTES)

        assert experiment.stage == "case-bootstrap"
        assert (experiment.output / "case-before-bootstrap-notes.log").read_bytes() == NOTES
        assert (experiment.output / "case-failed-bootstrap-notes.log").read_bytes() == NOTES
        assert not (experiment.output / "passed.json").exists()


class DescribeOwnedCleanup:
    @pytest.mark.parametrize("cleanup_fails", [False, True])
    def should_clean_daemon_created_container_after_failed_start(
        self, tmp_path, monkeypatch, cleanup_fails
    ):
        import json
        import sys

        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()
        monkeypatch.setattr(experiment, "capture", lambda: tmp_path)
        binary = tmp_path / "docker"
        state = tmp_path / "owned"
        script = f"""#!{sys.executable}
import pathlib,sys
state=pathlib.Path({str(state)!r})
args=sys.argv[1:]
if args[0]=='run':
    state.write_text(args[args.index('--label')+1])
    print('created but start failed')
    sys.exit(23)
if args[0]=='ps':
    assert args[-1] == 'label=' + state.read_text()
    print('owned-id')
elif args[0]=='rm':
    assert args == ['rm','-f','owned-id']
    if {cleanup_fails!r}:
        print('cleanup failed')
        sys.exit(7)
    state.unlink()
else:
    raise AssertionError(args)
"""
        binary.write_text(script)
        binary.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
        with pytest.raises(AssertionError):
            experiment.execute()
        failure = json.loads((experiment.output / "failure.json").read_text())
        assert failure["stage"].endswith("-cleanup" if cleanup_fails else "-create")
        assert state.exists() is cleanup_fails
        if cleanup_fails:
            assert failure["prior_failure"]["stage"].endswith("-create")
        assert not (experiment.output / "passed.json").exists()

    def should_identify_cleanup_failure_after_successful_work(self, tmp_path, monkeypatch):
        import json

        monkeypatch.setattr("sudo_policy.ROOT", tmp_path)
        experiment = Experiment()
        monkeypatch.setattr(experiment, "capture", lambda: tmp_path)
        original = experiment.run

        def commands(label, args, expected=0, timeout=300):
            command = ["/bin/sh", "-c", "echo owned-id"]
            if label.endswith("-cleanup"):
                command = ["/bin/sh", "-c", "echo cleanup-failed; exit 7"]
            return original(label, command, expected, timeout)

        monkeypatch.setattr(experiment, "run", commands)

        def journey(policy, inputs):
            experiment.stage = "case-collect"
            experiment.cleanup_owned("case", None)

        monkeypatch.setattr(experiment, "journey", journey)
        with pytest.raises(AssertionError):
            experiment.execute()
        failure = json.loads((experiment.output / "failure.json").read_text())
        assert failure["stage"] == "case-cleanup"
        assert failure["prior_failure"] is None
        assert not (experiment.output / "passed.json").exists()
