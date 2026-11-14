"""Real mixer captures and deliberately invalid output evidence."""

import json
import os
import shutil
from pathlib import Path

import pytest
from build_capture import build, source_inputs, verify_build
from capture import analyze, main, run_case
from instrument import instrument
from native import tool_path


class DescribeOutputCapture:
    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    @pytest.mark.parametrize("mode", ["released", "scripted", "muted", "constant"])
    def should_capture_real_output_and_check_ram(self, tmp_path, target, mode):
        xroar = Path(os.environ["AUDIO_XROAR"]).resolve()
        result = run_case(xroar, tmp_path / f"{target}-{mode}", target, mode)
        assert result["frames"] > 44100
        raw = (tmp_path / f"{target}-{mode}" / "output.pcm").read_bytes()
        log = (tmp_path / f"{target}-{mode}" / "xroar.log").read_text()
        wrong = 488 if mode in ("muted", "constant") else None
        with pytest.raises(ValueError):
            analyze(raw, wrong, log)
        if mode == "scripted":
            with pytest.raises(ValueError, match="wrong pitch"):
                analyze(raw, 488, log)

    @pytest.mark.parametrize("raw", [b"", b"\0" * 100000, b"\0" * 90112])
    def should_reject_missing_truncated_or_silent_tone(self, raw):
        with pytest.raises(ValueError):
            analyze(raw, 488, "")

    def should_reject_uninstrumented_emulator(self, tmp_path):
        with pytest.raises(ValueError, match="build provenance"):
            run_case(Path(tool_path("xroar")), tmp_path / "plain", "coco1", "released")

    def should_refuse_existing_evidence(self, tmp_path):
        with pytest.raises(FileExistsError):
            run_case(Path(os.environ["AUDIO_XROAR"]), tmp_path, "coco1", "released")

    def should_reject_drift_and_double_instrumentation(self):
        import tarfile

        with tarfile.open(Path(os.environ["AUDIO_ARCHIVE"])) as archive:
            source = archive.extractfile("xroar-1.12.1/src/null/ao_null.c").read()
        patched = instrument(source)
        assert b"SOUND_FMT_S16_LE" in patched
        for bad in (source + b"\n", patched):
            with pytest.raises(ValueError, match="pristine"):
                instrument(bad)

    def should_run_cli_contract(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["capture.py", "--xroar", os.environ["AUDIO_XROAR"], "--output", str(tmp_path / "cli")],
        )
        main()
        assert (tmp_path / "cli/coco2-scripted/output.wav").stat().st_size > 100000


class DescribeCaptureBoundaries:
    @pytest.fixture
    def captured(self, tmp_path):
        output = tmp_path / "real"
        run_case(Path(os.environ["AUDIO_XROAR"]), output, "coco1", "released")
        return (output / "output.pcm").read_bytes(), (output / "xroar.log").read_text()

    @pytest.mark.parametrize("cut", ["last", "first", "middle", "tail46080"])
    def should_reject_whole_fragment_loss_with_matching_callback_removal(self, captured, cut):
        raw, log = captured
        lines = log.splitlines()
        rows = [i for i, line in enumerate(lines) if line.startswith("PCM,")]
        count = len(rows)
        remove = {
            "last": {count - 1},
            "first": {0},
            "middle": {count // 2},
            "tail46080": set(range(count - 45)),
        }[cut]
        shortened = b"".join(
            raw[i * 2048 : (i + 1) * 2048] for i in range(count) if i not in remove
        )
        removed_rows = {rows[i] for i in remove}
        log = "\n".join(line for i, line in enumerate(lines) if i not in removed_rows)
        with pytest.raises(ValueError, match="continuity|completion"):
            analyze(shortened, 488, log)

    @pytest.mark.parametrize("change", ["missing", "duplicate", "early", "late", "end", "row"])
    def should_reject_invalid_timing_evidence(self, captured, change):
        raw, log = captured
        lines = log.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("CHECKPOINT,") and line.endswith("final.ram"):
                fields = line.split(",")
                fields[1] = str(int(fields[1]) + (14318180 if change == "late" else -14318180))
                if change in ("early", "late"):
                    lines[index] = ",".join(fields)
            if line.startswith("AUDIO_END,"):
                if change == "missing":
                    lines[index] = ""
                elif change == "duplicate":
                    lines[index] += "\n" + line
                elif change == "end":
                    lines[index] = "AUDIO_END,99999999"
        if change == "row":
            lines = [line for line in lines if not line.startswith("PCM,")]
        with pytest.raises(ValueError):
            analyze(raw, 488, "\n".join(lines))

    def should_reject_archive_mismatch(self, tmp_path):
        archive = tmp_path / "wrong.tar.gz"
        archive.write_bytes(b"not the pinned archive")
        with pytest.raises(ValueError, match="archive mismatch"):
            source_inputs(archive)

    @pytest.mark.parametrize("change", ["executable", "source", "instrumenter", "oracle"])
    def should_reject_mismatched_build_before_capture(self, tmp_path, change):
        executable = Path(os.environ["AUDIO_XROAR"]).resolve()
        source = executable.parent.parent
        copy = tmp_path / "copy"
        # Hard links keep this test small. Replace files, never mutate shared inodes.
        shutil.copytree(source, copy, copy_function=os.link)
        candidate = copy / "src/xroar"
        if change == "executable":
            candidate.unlink()
            shutil.copy2(tool_path("xroar"), candidate)
        elif change == "source":
            path = copy / "src/sound.c"
            content = path.read_bytes()
            path.unlink()
            path.write_bytes(content + b"\n")
            # Even an edited manifest cannot authorize drift from archive+patch.
            path = copy / "capture-build.json"
            manifest = json.loads(path.read_text())
            import hashlib

            manifest["source_sha256"]["src/sound.c"] = hashlib.sha256(content + b"\n").hexdigest()
            path.unlink()
            path.write_text(json.dumps(manifest))
        else:
            path = copy / "capture-build.json"
            manifest = json.loads(path.read_text())
            key = "instrumentation_sha256" if change == "instrumenter" else "ram_oracle_sha256"
            manifest[key] = "0" * 64
            path.unlink()
            path.write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="mismatch"):
            run_case(candidate, tmp_path / "output", "coco1", "released")
        assert not (tmp_path / "output").exists()

    def should_build_from_archive_and_capture(self, tmp_path):
        executable = build(Path(os.environ["AUDIO_ARCHIVE"]).resolve(), tmp_path / "fresh")
        assert verify_build(executable)["archive_sha256"]
        result = run_case(executable, tmp_path / "capture", "coco2", "scripted")
        assert result["peak_hz"] == pytest.approx(973.3333333333)

    def should_reject_plain_runtime_even_with_rewritten_executable_claim(self, tmp_path):
        import hashlib

        source = Path(os.environ["AUDIO_XROAR"]).resolve().parent.parent
        copy = tmp_path / "forged"
        shutil.copytree(source, copy, copy_function=os.link)
        executable = copy / "src/xroar"
        executable.unlink()
        shutil.copy2(tool_path("xroar"), executable)
        path = copy / "capture-build.json"
        manifest = json.loads(path.read_text())
        manifest["executable_sha256"] = hashlib.sha256(executable.read_bytes()).hexdigest()
        path.unlink()
        path.write_text(json.dumps(manifest))
        with pytest.raises(FileNotFoundError, match="output.pcm"):
            run_case(executable, tmp_path / "plain-runtime", "coco1", "released")

    def should_reject_missing_checkpoint_and_zeroed_pcm(self, captured):
        raw, log = captured
        incomplete = "\n".join(
            line for line in log.splitlines() if not line.startswith("CHECKPOINT,")
        )
        with pytest.raises(ValueError, match="checkpoints"):
            analyze(raw, 488, incomplete)
        with pytest.raises(ValueError, match="Missing tone"):
            analyze(bytes(len(raw)), 488, log)
