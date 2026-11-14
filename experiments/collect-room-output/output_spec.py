"""Exercise actual combined output and reject independent damaged evidence."""

import json
import os
import shutil
from pathlib import Path

import pytest
from measure_output import FRAME_BYTES, audio_measure, only, rows, timeline, video_measure
from prepare_output import ROOT, build, patched, replace, verify
from run_output import MODEL, run


@pytest.fixture(scope="module")
def captures(tmp_path_factory):
    root = tmp_path_factory.mktemp("captures")
    archive = Path(
        os.environ.get("COLLECT_ARCHIVE", ROOT / "local/research/audio-timing/xroar-1.12.1.tar.gz")
    )
    xroar = build(archive, root / "build")
    positives = {}
    for target in ("coco1", "coco2"):
        output = root / target
        result = run(xroar, output, target)
        positives[target] = (output, result)
    return root, xroar, positives


class DescribeLifecycleOutput:
    @pytest.mark.parametrize("target", ("coco1", "coco2"))
    def should_render_play_pickups_win_and_restart_with_real_pcm(self, captures, target):
        _, _, positives = captures
        _, result = positives[target]
        assert result["status"] == "passed"
        assert len(result["video"]["stable_frames_per_checkpoint"]) == 43
        assert [r["kind"] for r in result["audio"]["effects"]] == [1, 2, 2, 3, 1]
        assert result["routing"]["dac_writes"] == 160

    @pytest.mark.parametrize("target", ("coco1", "coco2"))
    @pytest.mark.parametrize(
        "control,reason",
        [
            ("video", "Rendered scene differs"),
            ("audio", "PCM effect differs"),
            ("input", "Keyboard injection sequence"),
        ],
    )
    def should_reject_broken_output_or_missing_input(self, captures, target, control, reason):
        root, xroar, _ = captures
        output = root / f"{target}-{control}"
        with pytest.raises(ValueError, match=reason):
            run(xroar, output, target, control)
        report = json.loads((output / "result.json").read_text())
        assert report["status"] == "failed"
        assert reason in report["error"]
        assert (output / "output.rgb").is_file()
        assert (output / "output.pcm").is_file()

    def should_refuse_existing_evidence(self, captures):
        _, xroar, positives = captures
        output, _ = positives["coco1"]
        before = (output / "result.json").read_bytes()
        with pytest.raises(FileExistsError):
            run(xroar, output, "coco1")
        assert (output / "result.json").read_bytes() == before


@pytest.fixture
def evidence(captures):
    output, _ = captures[2]["coco1"]
    return output, (output / "output.pcm").read_bytes(), (output / "xroar.log").read_text()


class DescribeCompleteness:
    @pytest.mark.parametrize(
        "damage", ("before-start", "after-end", "after-frame", "next-key", "final-frame")
    )
    def should_reject_impossible_input_checkpoint_times(self, evidence, damage):
        output, raw, log = evidence
        keys, frames = rows(log, "KEY"), rows(log, "FRAME")
        if damage == "final-frame":
            old = "FRAME," + ",".join(map(str, frames[-1]))
            new = f"FRAME,{frames[-1][0]},{only(log, 'AUDIO_END')}"
        else:
            index = 1 if damage == "next-key" else 0
            old = "KEY," + ",".join(map(str, keys[index]))
            tick = {
                "before-start": only(log, "AUDIO_START") - 1,
                "after-end": only(log, "AUDIO_END") + 1,
                "after-frame": frames[0][1] + 1,
                "next-key": frames[0][1],
            }[damage]
            new = f"KEY,{keys[index][0]},{keys[index][1]},{tick}"
        assert old in log
        with pytest.raises(ValueError, match="chronology"):
            timeline(raw, (output / "output.rgb").stat().st_size, log.replace(old, new), 43)

    @pytest.mark.parametrize("edge", (0, 100, -1))
    def should_reject_whole_pcm_fragment_loss_even_with_matching_log(self, evidence, edge):
        output, raw, log = evidence
        records = rows(log, "PCM")
        index = edge % len(records)
        altered = log.replace(f"PCM,{records[index][0]},1024\n", "")
        raw = raw[: index * 2048] + raw[(index + 1) * 2048 :]
        with pytest.raises(ValueError, match="PCM"):
            timeline(raw, (output / "output.rgb").stat().st_size, altered, 43)

    @pytest.mark.parametrize("edge", (0, 100, -1))
    def should_reject_whole_video_frame_loss_even_with_renumbered_log(self, evidence, edge):
        output, raw, log = evidence
        records = rows(log, "VIDEO")
        records.pop(edge)
        replacement = iter(f"VIDEO,{i},{r[1]},{r[2]},{r[3]}" for i, r in enumerate(records))
        lines = [line for line in log.splitlines() if not line.startswith("VIDEO,")]
        altered = "\n".join(lines + list(replacement))
        with pytest.raises(ValueError, match="Video"):
            timeline(raw, (output / "output.rgb").stat().st_size - FRAME_BYTES, altered, 43)

    @pytest.mark.parametrize("marker", ("AUDIO_START", "AUDIO_END"))
    def should_require_unique_audio_boundaries(self, evidence, marker):
        _, _, log = evidence
        with pytest.raises(ValueError, match=marker):
            only(log + f"\n{marker},0\n", marker)
        with pytest.raises(ValueError, match=marker):
            only("", marker)

    def should_reject_partial_data_and_checkpoints(self, evidence):
        output, raw, log = evidence
        size = (output / "output.rgb").stat().st_size
        for data, video_size, text, reason in [
            (raw[:-1], size, log, "PCM"),
            (raw, size - 1, log, "Video"),
            (raw, size, log.replace("FRAME,42,", "FRAME,43,"), "Checkpoint"),
        ]:
            with pytest.raises(ValueError, match=reason):
                timeline(data, video_size, text, 43)

    def should_reject_silent_and_wrong_pitch_pcm(self, evidence):
        _, raw, log = evidence
        with pytest.raises(ValueError, match="PCM effect"):
            audio_measure(bytes(len(raw)), log, MODEL.journey()[:43])
        wrong = MODEL.journey()[:43]
        key, state = wrong[4]
        wrong[4] = key, (*state[:7], 2, state[8])
        with pytest.raises(ValueError, match="PCM effect"):
            audio_measure(raw, log, wrong)

    def should_reject_wrong_scene_independent_of_remaining_count(self, evidence):
        output, _, log = evidence
        wrong = MODEL.journey()[:43]
        key, state = wrong[14]
        wrong[14] = key, (*state[:8], 2)
        with pytest.raises(ValueError, match="Rendered scene differs"):
            video_measure(output / "output.rgb", log, wrong)


class DescribeBuildProvenance:
    def should_reject_bad_archive_and_ambiguous_patch(self, tmp_path):
        bad = tmp_path / "bad.tar.gz"
        bad.write_bytes(b"wrong source")
        with pytest.raises(ValueError, match="archive"):
            patched(bad)
        with pytest.raises(ValueError, match="anchor"):
            replace("absent", "needle", "new")

    @pytest.mark.parametrize("damage", ("source", "binary", "tools"))
    def should_reject_tampered_build(self, captures, tmp_path, damage):
        _, xroar, _ = captures
        tree = tmp_path / "source"
        shutil.copytree(xroar.parent.parent, tree)
        manifest_path = tree / "output-build.json"
        manifest = json.loads(manifest_path.read_text())
        if damage == "source":
            with (tree / "src/null/ui_null.c").open("a") as stream:
                stream.write("\n/* modified */\n")
        elif damage == "binary":
            (tree / "src/xroar").write_bytes(b"not the executable")
        else:
            manifest["tools"] = {}
            manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(ValueError, match="mismatch"):
            verify(tree / "src/xroar")
