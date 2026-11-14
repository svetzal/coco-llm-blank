"""Independent expected bytes, actual machine integration, and CLI boundaries."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import selective_redraw as renderer


class DescribeSelectiveRedraw:
    def should_match_every_checkpoint_on_both_ram_capacities(self, evidence):
        runs = [run for run in evidence["runs"] if run["variant"] in ("selective", "full")]
        assert len(runs) == 4
        assert {run["ram_kib"] for run in runs} == {128, 512}
        assert all(row["differing_bytes"] == 0 for run in runs for row in run["frames"])

    def should_count_only_whole_changed_regions(self, evidence):
        # Each region is 4 bytes * 8 rows. Fixed expected outcomes, no
        # reconstruction of the renderer's history-comparison implementation.
        expected = [64, 0, 32, 32, 32, 32, 64, 0, 64, 0, 32, 0]
        for run in evidence["runs"]:
            if run["variant"] == "selective":
                assert [row["renderer_stores"] for row in run["frames"]] == expected
            if run["variant"] == "full":
                assert [row["renderer_stores"] for row in run["frames"]] == [64] * 12

    def should_detect_shared_history_and_missing_invalidation(self, evidence):
        for run in evidence["runs"]:
            failures = {row["frame"]: row["differing_bytes"] for row in run["frames"]}
            if run["variant"] == "shared-history":
                assert failures["alternate-first-use"] == 64
            if run["variant"] == "missing-invalidation":
                assert failures["external-invalidated"] == 1
                assert failures["after-invalidation"] == 1

    def should_restore_exposed_background_and_keep_unowned_pixels(self):
        empty = renderer.Region(top=0, bottom=0, colour=15, background=2)
        full = renderer.Region(top=0, bottom=8, colour=15, background=0)
        expected_row = bytes([0x22] * 4 + [0xA5] * 4 + [0xFF] * 4 + [0xA5] * 68)
        assert renderer.oracle((empty, full)) == expected_row * 8

    def should_reject_wrong_snapshot_capacity(self):
        with pytest.raises(ValueError, match="snapshot size"):
            renderer.assess([b""], {}, renderer.fixtures()[:1], 128)

    def should_reject_overwritten_guard(self):
        with pytest.raises(ValueError, match="guard damaged"):
            renderer.assess([bytes(131072)], {}, renderer.fixtures()[:1], 128)

    @pytest.mark.parametrize("argument,code", [("--help", 0), ("--unknown", 2)])
    def should_parse_cli_without_build_or_launch(self, tmp_path, argument, code):
        destination = tmp_path / "absent"
        result = subprocess.run(
            [sys.executable, str(Path(renderer.__file__)), argument, "--output", str(destination)],
            capture_output=True,
            check=False,
            timeout=15,
        )
        assert result.returncode == code
        assert not destination.exists()

    def should_invalidate_previous_success_before_preflight_failure(self, tmp_path, monkeypatch):
        report = tmp_path / "results.json"
        report.write_text('{"passed": true}')

        def fail(*args):
            raise ValueError("firmware failure")

        monkeypatch.setattr(renderer, "verify_installed", fail)
        with pytest.raises(ValueError, match="firmware failure"):
            renderer.check(tmp_path)
        assert json.loads(report.read_text()) == {"passed": False, "status": "incomplete"}

    @pytest.mark.parametrize("timeout", [False, True])
    def should_replace_old_log_with_failed_process_output(self, tmp_path, monkeypatch, timeout):
        fake = tmp_path / "emulator"
        fake.write_text(
            "#!/bin/sh\necho new-diagnostic >&2\n" + ("exec sleep 10\n" if timeout else "exit 23\n")
        )
        fake.chmod(0o755)
        directory = tmp_path / "selective"
        directory.mkdir()
        log = directory / "128.log"
        log.write_text("old-success")
        monkeypatch.setattr(renderer, "tool_path", lambda *args: str(fake))
        real_run = subprocess.run

        def bounded(*args, **kwargs):
            kwargs["timeout"] = 2
            return real_run(*args, **kwargs)

        monkeypatch.setattr(renderer.subprocess, "run", bounded)
        error = subprocess.TimeoutExpired if timeout else subprocess.CalledProcessError
        with pytest.raises(error):
            renderer.capture(
                tmp_path,
                "selective",
                128,
                tmp_path / "test.bin",
                {"state": 0x3000, "finished": 0x3010},
                tmp_path / "rom",
                [],
            )
        assert log.read_text() == "new-diagnostic\n"
