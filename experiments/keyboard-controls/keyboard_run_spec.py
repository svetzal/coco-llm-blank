"""Integration assertions over real 6809 execution, not mocked keyboard state."""

import json
import subprocess
import sys
import tarfile

import keyboard_run as experiment
import pytest


class DescribeKeyboardPath:
    def should_keep_the_upstream_keyboard_matrix_and_pia_implementation(self):
        work = experiment.WORK
        with tarfile.open(work / "xroar-1.12.1.tar.gz") as archive:
            for name in ("keyboard.h", "keyboard.c", "mc6821.c", "dragon/dragon.c"):
                original = archive.extractfile("xroar-1.12.1/src/" + name).read()
                assert original == (work / "xroar-1.12.1/src" / name).read_bytes()
            source = archive.extractfile("xroar-1.12.1/src/xroar.c").read().decode()
        anchor = "static void handle_trap(void *sptr) {\n\tstruct trap_def *trap = sptr;"
        helper = (experiment.HERE / "key_hook.c").read_text()
        expected = source.replace(
            anchor, helper + "\n" + anchor + "\n\texperiment_keyboard(trap->cond);"
        )

        assert expected == (work / "xroar-1.12.1/src/xroar.c").read_text()

    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    def should_scan_held_edges_and_return_after_blocking(self, target):
        result = experiment.run(target)

        assert result["records"] == experiment.EXPECTED
        a_before, b_before, a_after, b_after, columns = result["control"]
        assert (a_after & 0x3F) == ((a_before & 0x3F) | 4)
        assert (b_after & 0x3F) == ((b_before & 0x3F) | 4)
        assert columns == 255
        # M occupies another row in the left-arrow column. It must not move left.
        assert result["raw_records"][3][0] & 2 == 0
        assert result["raw_records"][2][0] & 2 == 2

    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    @pytest.mark.parametrize(
        "variant", ["WRONG_COLUMN", "WRONG_SELECT", "HELD_FIRE", "STALE_HISTORY"]
    )
    def should_reject_broken_scanner_and_policy_controls(self, target, variant):
        result = experiment.run(target, variant)

        assert not result["matches_expected"]
        if variant == "WRONG_COLUMN":
            assert result["records"][9][4] == 4  # Left cannot return from wall.
        elif variant == "WRONG_SELECT":
            assert result["control"][3] & 4 == 0
        elif variant == "HELD_FIRE":
            assert result["records"][0][5] == 1  # Startup hold incorrectly fires.
        else:
            assert result["records"][6][5] == 1  # Blocked release was forgotten.

    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    def should_observe_idle_without_key_injection(self, target):
        result = experiment.run(target, inject=False)

        assert result["records"] == [[8, 8, 8, 0, 2, 0, 0]] * 16
        assert not result["matches_expected"]

    def should_not_accept_an_unreachable_checkpoint(self):
        assert experiment.run("coco1", unreachable=True) == {"unreachable_trap": "no snapshot"}

    def should_run_the_public_check_command(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["keyboard_run.py", "--target", "coco2"])

        experiment.main()

        assert json.loads(capsys.readouterr().out)["matches_expected"]

    @pytest.mark.parametrize("script", ["prepare.py", "keyboard_run.py"])
    @pytest.mark.parametrize("option,code", [("--help", 0), ("--unknown", 2)])
    def should_parse_before_external_work(self, tmp_path, script, option, code):
        # Empty PATH makes accidental assembler/configure/emulator startup fail.
        result = subprocess.run(
            [sys.executable, str(experiment.HERE / script), option],
            cwd=tmp_path,
            env={"PATH": ""},
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == code
        assert not list(tmp_path.iterdir())


class DescribeFailedReruns:
    @pytest.mark.parametrize("failure", ["assembly", "events"])
    def should_replace_success_before_a_failed_attempt(self, tmp_path, monkeypatch, failure):
        assert experiment.run("coco1")["matches_expected"]
        output = experiment.WORK / "coco1-normal-keys-hit"
        if failure == "assembly":
            monkeypatch.setattr(experiment, "tool_path", lambda *args: None)
        else:
            (tmp_path / "main.asm").write_bytes((experiment.HERE / "main.asm").read_bytes())
            (tmp_path / "events.txt").write_text("")
            monkeypatch.setattr(experiment, "HERE", tmp_path)
        with pytest.raises((RuntimeError, subprocess.CalledProcessError, AssertionError)):
            experiment.run("coco1")
        report = json.loads((output / "result.json").read_text())
        assert report["status"] == "failed"
        assert report["matches_expected"] is False
        assert report["type"] and report["error"]
        assert not (output / "result.ram").exists()
