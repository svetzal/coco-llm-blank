"""The project tool builds, launches and checks folders described only by their own files."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import coco
import instrumented_xroar
import numpy as np
import pytest
from coco import Host, ProjectError
from native import ROOT, tool_path
from PIL import Image

SETTINGS = """
source = "main.asm"

[targets.coco1]
machine = "cocous"
cpu = "6809"
tv = "ntsc"
ram_kib = 32
basic = "bas11.rom"

[targets.coco2]
machine = "coco2bus"
ram_kib = 32
basic = "bas12.rom"
options = ["-machine-arch", "coco"]

[memory]
at = { start = 0x3000 }
below = { program_end = 0x7E00 }

[check]
checkpoint = "ready"
frames = [1, "3-4"]
unreachable = "state"
screen = 0x0400
"""
MODEL = """
def expected_screen(frame):
    return bytes([frame]) * 4


def verify_ram(ram, symbols, frame):
    if ram[symbols["state"]] != frame:
        raise ValueError("state differs from the model")
"""
CAPTURE_MODEL = """
import numpy as np


def expected_frame(frame):
    return np.full((2, 3, 3), frame, dtype=np.uint8)


def verify_sound(sound, frame):
    if not sound.samples.any():
        raise ValueError("silent")
    return {"frame": frame, "samples": len(sound.samples)}
"""
KEYS = """
[keys]
at = "start"
letters = { L = "left", F = "space" }

[variants.play]
keys = "play.txt"
"""
SYMBOLS = "start EQU $3000\nready EQU $3010\nstate EQU $3020\nprogram_end EQU $3030\n"
TICKS = 14318180
CHECKPOINT_TICK = TICKS  # one emulated second after audio starts: 44,100 samples
EXAMPLES = sorted(path.parent for path in (ROOT / "examples").glob("*/coco.toml"))


def ram_for(frame: int) -> bytes:
    ram = bytearray(32768)
    ram[0x400:0x404] = bytes([frame]) * 4
    ram[0x3020] = frame
    return bytes(ram)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    directory = tmp_path / "demo"
    directory.mkdir()
    (directory / "coco.toml").write_text(SETTINGS)
    (directory / "expected.py").write_text(MODEL)
    return directory


@pytest.fixture
def project(folder: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> coco.Project:
    monkeypatch.setattr(coco, "ROOT", tmp_path)
    return coco.load_project(folder)


def recorded(env: dict[str, str], frame: int, picture: np.ndarray | None) -> str:
    """What the instrumented emulator's hooks write: raw files and their log lines."""
    lines = [f"COCO_CHECKPOINT,{CHECKPOINT_TICK},{TICKS}"]
    if "COCO_VIDEO" in env:
        pixels = np.full((2, 3, 3), frame, dtype=np.uint8) if picture is None else picture
        height, width, _ = pixels.shape
        Path(env["COCO_VIDEO"]).write_bytes(
            f"P6\n{width} {height}\n255\n".encode() + pixels.tobytes()
        )
        lines.append(f"COCO_VIDEO,{CHECKPOINT_TICK + 300000},{width},{height}")
    if "COCO_AUDIO" in env:
        buffers = 44
        samples = (np.arange(buffers * 1024) % 90 * 300).astype("<i2")
        Path(env["COCO_AUDIO"]).write_bytes(samples.tobytes())
        lines.append("COCO_AUDIO_START,0,44100,1024")
        lines += [f"COCO_AUDIO,{round(n * 1024 * TICKS / 44100)}" for n in range(1, buffers + 1)]
    if "COCO_KEYS" in env:
        steps = Path(env["COCO_KEYS"]).read_text().splitlines()
        lines += [f"COCO_KEYS,{n},{n * 1000}" for n in range(len(steps))]
    return "\n".join(lines) + "\n"


def emulated(
    ram: bytes | None = None,
    unreachable: bool = False,
    trace: str = "",
    picture: np.ndarray | None = None,
) -> Mock:
    """A host whose assembler writes symbols and whose emulator writes snapshots."""
    host = Mock(spec=Host)
    host.executable.side_effect = lambda name: f"/tools/{name}"
    host.instrumented.return_value = "/tools/xroar-instrumented"
    host.firmware.side_effect = lambda profile, names: {n: Path("/roms") / n for n in names}

    def run(command, log, timeout, cwd=None, env=None):
        log.write_text(trace)
        if "--6809" in command:
            symbols = next(arg for arg in command if arg.startswith("--symbol-dump="))
            Path(symbols.split("=", 1)[1]).write_text(SYMBOLS)
            binary = next(arg for arg in command if arg.startswith("--output="))
            Path(binary.split("=", 1)[1]).write_bytes(b"DECB")
            return
        snaps = [i + 1 for i, arg in enumerate(command) if arg == "-trap-snap"]
        if unreachable:
            Path(command[snaps[0]]).write_bytes(b"")
        frame = int(command[snaps[-1] - 2].split("-")[0])
        if ram is not None:
            Path(command[snaps[-1]]).write_bytes(ram if len(ram) != 32768 else ram_for(frame))
            if env:
                log.write_text(trace + recorded(env, frame, picture))

    host.run.side_effect = run
    return host


class DescribeSettings:
    def should_expand_frame_ranges_and_keep_target_order(self, project: coco.Project) -> None:
        assert project.settings.check.frames == (1, 3, 4)
        assert project.default_target == "coco1"
        assert project.output.name == "demo"

    @pytest.mark.parametrize(
        "change,message",
        [
            ('frames = [1, "3-4"]', "frames = [0]"),
            ('source = "main.asm"', 'sourse = "main.asm"'),
            ('ram_kib = 32\nbasic = "bas11.rom"', 'ram_kib = 0\nbasic = "bas11.rom"'),
            ("[check]", "[check"),
        ],
    )
    def should_reject_invalid_settings(self, folder: Path, change: str, message: str) -> None:
        (folder / "coco.toml").write_text(SETTINGS.replace(change, message))

        with pytest.raises(ProjectError, match="is invalid"):
            coco.load_project(folder)

    def should_explain_a_folder_without_settings(self, tmp_path: Path) -> None:
        with pytest.raises(ProjectError, match="needs coco.toml"):
            coco.load_project(tmp_path)


class DescribeModels:
    def should_load_the_folder_model_once(self, folder: Path) -> None:
        assert coco.load_expected(folder) is coco.load_expected(folder)
        assert coco.load_expected(folder.parent) is None

    def should_not_cache_a_model_that_fails_to_import(self, folder: Path) -> None:
        (folder / "expected.py").write_text("raise ValueError('broken model')\n")

        for _ in range(2):
            with pytest.raises(ValueError, match="broken model"):
                coco.load_expected(folder)

    def should_pass_the_variant_only_when_variants_are_declared(
        self, folder: Path, project: coco.Project
    ) -> None:
        assert coco.model_call(project, lambda frame: frame, 3, variant="") == 3
        (folder / "coco.toml").write_text(SETTINGS + '\n[variants.fast]\ndefines = ["FAST"]\n')
        with_variants = coco.load_project(folder)

        result = coco.model_call(with_variants, lambda f, v: (f, v), 3, variant="fast")

        assert result == (3, "fast")

    def should_compare_every_screen_byte_and_then_the_state_model(
        self, project: coco.Project
    ) -> None:
        model = coco.load_expected(project.directory)
        symbols = coco.parse_symbols(SYMBOLS)

        assert coco.verify_snapshot(project, model, ram_for(3), symbols, 3) == 4
        damaged = bytearray(ram_for(3))
        damaged[0x402] ^= 0x10
        with pytest.raises(ProjectError, match=r"1 of 4 screen bytes differ; first at \$0402"):
            coco.verify_snapshot(project, model, damaged, symbols, 3)
        wrong_state = bytearray(ram_for(3))
        wrong_state[0x3020] = 4
        with pytest.raises(ValueError, match="state differs"):
            coco.verify_snapshot(project, model, wrong_state, symbols, 3)

    def should_report_a_short_screen(self) -> None:
        assert "holds 1 screen bytes" in coco.screen_difference(b"ab", b"a", 0x400)
        assert coco.screen_difference(b"ab", b"ab", 0x400) is None


class DescribeSymbolsAndLayout:
    def should_resolve_labels_and_offsets(self) -> None:
        symbols = coco.parse_symbols(SYMBOLS)

        assert coco.address(symbols, "ready") == 0x3010
        assert coco.address(symbols, "ready+1") == 0x3011
        with pytest.raises(ProjectError, match="'missing' is not in the assembled symbols"):
            coco.address(symbols, "missing")

    @pytest.mark.parametrize(
        "symbols,message",
        [
            ({"start": 0x3001, "program_end": 0x4000}, r"start must be at \$3000"),
            ({"start": 0x3000, "program_end": 0x7E00}, r"program_end must be below \$7E00"),
        ],
    )
    def should_enforce_the_declared_memory_layout(
        self, project: coco.Project, symbols: dict[str, int], message: str
    ) -> None:
        with pytest.raises(ProjectError, match=message):
            coco.check_memory(project.settings.memory, symbols)


class DescribeCommands:
    def should_translate_a_target_into_explicit_xroar_options(self, project: coco.Project) -> None:
        machine = project.settings.targets["coco2"]
        roms = {"bas12.rom": Path("/r/b")}

        command = coco.xroar_command("xroar", machine, roms)

        assert command == [
            "xroar",
            "-no-c",
            "-machine",
            "coco2bus",
            "-ram",
            "32",
            "-bas",
            "/r/b",
            "-no-extbas",
            "-no-cart",
            "-machine-arch",
            "coco",
        ]

    def should_capture_from_nonzero_ram_with_an_unreachable_control(
        self, project: coco.Project
    ) -> None:
        symbols = coco.parse_symbols(SYMBOLS)

        options = coco.capture_options(
            project.settings.check, symbols, 4, Path("s.ram"), Path("u.ram")
        )

        joined = " ".join(options)
        assert "-ram-init set" in joined and "-no-ratelimit" in joined
        assert "-trap pc=0x3020 -trap-snap u.ram" in joined
        assert "-trap pc=0x3010 -trap-range 4-4 -trap-snap s.ram" in joined
        assert "-trap-trace" not in joined
        assert options[-2:] == ["-trap-timeout", "0"]
        assert "-fskip" not in options

    def should_trace_from_a_label_until_the_checkpoint(self, project: coco.Project) -> None:
        check = project.settings.check.model_copy(update={"trace_from": "start"})

        options = coco.capture_options(check, coco.parse_symbols(SYMBOLS), 2, Path("s"), Path("u"))

        joined = " ".join(options)
        assert "-trap pc=0x3000 -trap-range 1-1 -trap-trace" in joined
        assert joined.index("-trap-no-trace") > joined.index("-trap-snap s")

    def should_assemble_with_defines_and_the_build_folder_for_includes(self) -> None:
        command = coco.assemble_command(
            "lwasm", Path("/p/main.asm"), Path("/b/x.bin"), Path("/b/x.sym"), ("A", "B")
        )

        assert command[1:3] == ["--6809", "--format=decb"]
        assert "--includedir=/b" in command
        assert command[-3:] == ["--define=A", "--define=B", "/p/main.asm"]


class DescribeBuild:
    def should_assemble_fresh_output_and_return_symbols(self, project: coco.Project) -> None:
        stale = project.output / "main.bin"
        stale.parent.mkdir(parents=True)
        stale.write_text("stale")
        host = emulated()

        built = coco.build(project, host)

        assert built.symbols["ready"] == 0x3010
        assert stale.read_bytes() == b"DECB"
        assert host.run.call_args.args[0][0] == "/tools/lwasm"

    def should_run_the_project_prepare_step_first(
        self, folder: Path, project: coco.Project
    ) -> None:
        (folder / "assets.py").write_text(
            "def prepare(output):\n    (output / 'assets.inc').write_text('art fcb 1')\n"
        )
        (folder / "coco.toml").write_text('prepare = "assets.py"\n' + SETTINGS)

        coco.build(coco.load_project(folder), emulated())

        assert (project.output / "assets.inc").read_text() == "art fcb 1"

    def should_require_a_prepare_function(self, folder: Path) -> None:
        (folder / "assets.py").write_text("ART = 1\n")
        (folder / "coco.toml").write_text('prepare = "assets.py"\n' + SETTINGS)

        with pytest.raises(ProjectError, match="must define prepare"):
            coco.build(coco.load_project(folder), emulated())

    def should_name_builds_after_variants_and_defines(self, folder: Path) -> None:
        (folder / "coco.toml").write_text(SETTINGS + '\n[variants.fast]\ndefines = ["FAST"]\n')
        project = coco.load_project(folder)
        host = emulated()

        built = coco.build(project, host, "fast", ("EXTRA",))

        assert built.binary.name == "fast-extra.bin"
        assert "--define=FAST" in host.run.call_args.args[0]
        with pytest.raises(ProjectError, match="Unknown variant 'slow'"):
            coco.build(project, host, "slow")


class DescribeCapture:
    def should_return_the_snapshot_of_the_requested_frame(self, project: coco.Project) -> None:
        host = emulated(ram=bytes(32768))
        built = coco.build(project, host)

        evidence = coco.capture(project, host, built, "coco1", 3)

        assert evidence.ram == ram_for(3)
        assert evidence.log.name == "main-coco1-3.log"
        assert evidence.picture is None and evidence.sound is None
        assert host.run.call_args.kwargs["env"] is None
        assert not host.instrumented.called
        command = host.run.call_args.args[0]
        assert command[:4] == ["/tools/xroar", "-no-c", "-machine", "cocous"]
        assert command[-2:] == ["-run", str(built.binary)]

    def should_reject_an_unreachable_checkpoint_that_fires(self, project: coco.Project) -> None:
        host = emulated(ram=bytes(32768), unreachable=True)

        with pytest.raises(ProjectError, match="unreachable checkpoint 'state' fired"):
            coco.capture(project, host, coco.build(project, host), "coco1", 1)

    def should_reject_a_checkpoint_that_was_never_reached(self, project: coco.Project) -> None:
        host = emulated()

        with pytest.raises(ProjectError, match="did not reach 'ready' 1 times"):
            coco.capture(project, host, coco.build(project, host), "coco1", 1)

    def should_require_a_check_section(self, folder: Path) -> None:
        (folder / "coco.toml").write_text(SETTINGS.split("[check]")[0])
        project = coco.load_project(folder)
        host = emulated()

        with pytest.raises(ProjectError, match="no \\[check\\] section"):
            coco.capture(project, host, coco.build(project, host), "coco1", 1)


class DescribeCheck:
    def should_record_success_only_after_every_frame_matches(self, project: coco.Project) -> None:
        record = coco.check_target(project, emulated(ram=bytes(32768)), "coco2")

        saved = json.loads((project.output / "coco2-results.json").read_text())
        assert saved == record
        assert record["frames"] == [1, 3, 4]
        assert record["variants"]["main"]["screen_bytes_each"] == 4
        assert record["unreachable_checkpoint"] == "no snapshot"
        assert record["visual"] == "not inspected by a person"
        assert record["rendered_display"] == record["sound"] == "not captured"
        lines = coco.report(project, record)
        assert "Memory: all 4 screen bytes" in lines[1]
        assert lines[-3].startswith("Rendered display: not captured; add --video")
        assert lines[-2].startswith("Sound: not captured; add --audio")
        assert lines[-1].startswith("Visual: not inspected by a person")

    def should_remove_a_previous_pass_before_a_failing_attempt(self, project: coco.Project) -> None:
        previous = project.output / "coco1-results.json"
        previous.parent.mkdir(parents=True)
        previous.write_text("{}")

        with pytest.raises(ProjectError, match="did not reach"):
            coco.check_target(project, emulated(), "coco1")

        assert not previous.exists()

    def should_say_memory_was_not_compared_without_a_model(
        self, folder: Path, project: coco.Project
    ) -> None:
        (folder / "expected.py").unlink()

        record = coco.check_target(project, emulated(ram=bytes(32768)), "coco1")

        assert record["model"].startswith("none")
        assert "Memory: not compared" in coco.report(project, record)[1]

    def should_verify_the_trace_of_each_variant(self, folder: Path) -> None:
        settings = SETTINGS.replace("screen = 0x0400", 'trace_from = "start"')
        (folder / "coco.toml").write_text(settings + '\n[variants.fast]\ndefines = ["FAST"]\n')
        (folder / "expected.py").write_text(
            "def verify_ram(ram, symbols, frame, variant):\n    pass\n\n"
            "def verify_trace(trace, symbols, variant):\n"
            "    return {'lines': len(trace.splitlines()), 'variant': variant}\n"
        )
        project = coco.load_project(folder)

        record = coco.check_target(project, emulated(ram=bytes(32768), trace="a\nb\n"), "coco1")

        assert record["variants"]["fast"]["trace"] == {"lines": 2, "variant": "fast"}
        assert "Trace (fast)" in "\n".join(coco.report(project, record))
        assert record["variants"]["main"]["screen_bytes_each"] == 0


class DescribeCommandLine:
    @pytest.mark.parametrize(
        "arguments,code",
        [(["--help"], 0), (["check", "--help"], 0), ([], 2), (["check", "x", "--bogus"], 2)],
    )
    def should_parse_before_any_side_effect(self, arguments: list[str], code: int) -> None:
        host = Mock(spec=Host)

        with pytest.raises(SystemExit) as error:
            coco.main(arguments, host)

        assert error.value.code == code
        assert not host.method_calls

    def should_launch_the_built_program_at_normal_speed(
        self, folder: Path, project: coco.Project
    ) -> None:
        host = emulated()

        assert coco.main(["run", str(folder), "--target", "coco2"], host) == 0

        command = host.launch.call_args.args[0]
        assert command[3] == "coco2bus"
        assert command[-3:] == ["-ratelimit", "-run", str(project.output / "main.bin")]

    def should_not_launch_when_firmware_is_invalid(self, folder: Path, project, capsys) -> None:
        host = emulated()
        host.firmware.side_effect = ValueError("Cannot use coco1 firmware")

        assert coco.main(["run", str(folder)], host) == 1

        assert not host.launch.called
        assert "FAIL: Cannot use coco1 firmware" in capsys.readouterr().err

    def should_reject_an_unknown_target_before_building(self, folder: Path, capsys) -> None:
        host = emulated()

        assert coco.main(["build", str(folder), "--target", "coco3"], host) == 1

        assert not host.run.called
        assert "Unknown target 'coco3'" in capsys.readouterr().err

    def should_print_build_and_snapshot_paths(self, folder: Path, project, capsys) -> None:
        host = emulated(ram=bytes(32768))

        coco.main(["build", str(folder)], host)
        coco.main(["snapshot", str(folder), "--frame", "3"], host)

        lines = capsys.readouterr().out.splitlines()
        assert lines == [str(project.output / "main.bin"), str(project.output / "main-coco1-3.ram")]

    def should_check_every_target_unless_one_is_named(self, folder: Path, project, capsys):
        assert coco.main(["check", str(folder)], emulated(ram=bytes(32768))) == 0

        output = capsys.readouterr().out
        assert "Execution: coco1" in output and "Execution: coco2" in output
        assert output.rstrip().endswith(f"evidence in {project.output}")
        assert coco.main(["check", str(folder), "--target", "coco2"], emulated()) == 1


class DescribeEquipmentSettings:
    def should_read_keys_capture_and_key_variants(self, folder: Path) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS + "\n[capture]\nvideo = true\n")

        settings = coco.load_project(folder).settings

        assert settings.keys.letters == {"L": "left", "F": "space"}
        assert settings.variants["play"] == coco.Variant(keys="play.txt")
        assert settings.capture == coco.Capture(video=True)

    @pytest.mark.parametrize(
        "change,message",
        [
            ('F = "space"', 'F = "spacebar"'),
            ('F = "space"', '"-" = "space"'),
            ('keys = "play.txt"', "defines = []"),
            ("[keys]", "[ignored]"),
        ],
    )
    def should_reject_unusable_key_settings(self, folder: Path, change: str, message: str):
        (folder / "coco.toml").write_text(SETTINGS + KEYS.replace(change, message))

        with pytest.raises(ProjectError, match="is invalid"):
            coco.load_project(folder)

    def should_combine_capture_settings_flags_and_the_variant_script(self, folder: Path) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS + "\n[capture]\naudio = true\n")
        (folder / "play.txt").write_text("# held keys, then notes\nF  start\n-\nLF\n")
        project = coco.load_project(folder)

        plain = coco.equipment_for(project, "", video=True)
        played = coco.equipment_for(project, "play")

        assert (plain.video, plain.audio, plain.keys) == (True, True, None)
        assert played.keys == (("space",), (), ("left", "space"))
        assert played.script == "play.txt" and played.instrumented

    def should_let_a_command_line_script_replace_the_variant_script(
        self, folder: Path, tmp_path: Path
    ) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        other = tmp_path / "other.txt"
        other.write_text("L\n")

        equipment = coco.equipment_for(coco.load_project(folder), "play", script=other)

        assert equipment.keys == (("left",),)

    def should_explain_key_scripts_it_cannot_use(self, folder: Path, tmp_path: Path) -> None:
        script = tmp_path / "keys.txt"
        script.write_text("X\n")
        project = coco.load_project(folder)

        with pytest.raises(ProjectError, match="needs \\[keys\\]"):
            coco.equipment_for(project, script=script)
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        with pytest.raises(ProjectError, match="Cannot read the key script"):
            coco.equipment_for(coco.load_project(folder), "play")
        with pytest.raises(ValueError, match="X is not a declared letter"):
            coco.equipment_for(coco.load_project(folder), script=script)


class DescribeEquipmentRuns:
    def should_record_frames_and_audio_then_run_on_after_the_checkpoint(
        self, project: coco.Project
    ) -> None:
        equipment = coco.Equipment(video=True, audio=True)

        options = coco.capture_options(
            project.settings.check,
            coco.parse_symbols(SYMBOLS),
            2,
            Path("s.ram"),
            Path("u.ram"),
            equipment,
        )

        assert options[: len(coco.VIDEO_OPTIONS)] == coco.VIDEO_OPTIONS
        assert options[-2:] == ["-trap-timeout", "0.06"]

    def should_act_on_keys_at_every_hit_of_the_key_label(self, folder: Path) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        project = coco.load_project(folder)
        symbols = coco.parse_symbols(SYMBOLS)
        equipment = coco.Equipment(keys=(("left",),))
        paths = {"ram": Path("s.ram"), "keys": Path("k.keys")}

        options = coco.capture_options(
            project.settings.check,
            symbols,
            2,
            Path("s.ram"),
            Path("u.ram"),
            equipment,
            project.settings.keys,
        )
        variables = coco.recording_environment(equipment, symbols, project.settings.keys, paths)

        assert "-trap pc=0x3000 -trap-range 1-" in " ".join(options)
        assert options[-2:] == ["-trap-timeout", "0"]
        assert variables == {
            "COCO_CHECKPOINT": "s.ram",
            "COCO_KEYS": "k.keys",
            "COCO_KEYS_AT": "pc=0x3000",
        }

    def should_capture_with_the_instrumented_emulator(
        self, folder: Path, project: coco.Project, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COCO_VIDEO", "/stale/from/the/shell.ppm")
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        (folder / "play.txt").write_text("F\nL\n")
        project = coco.load_project(folder)
        host = emulated(ram=bytes(32768))
        built = coco.build(project, host, "play")
        equipment = coco.equipment_for(project, "play", video=True, audio=True)

        evidence = coco.capture(project, host, built, "coco1", 3, equipment)

        command = host.run.call_args.args[0]
        env = host.run.call_args.kwargs["env"]
        assert command[0] == "/tools/xroar-instrumented"
        assert env["COCO_VIDEO"].endswith("play-coco1-3.ppm") and "PATH" in env
        assert (project.output / "play-coco1-3.keys").read_text() == "space\nleft\n"
        assert evidence.picture.pixels.shape == (2, 3, 3)
        assert evidence.picture.path.name == "play-coco1-3.png" and evidence.picture.path.exists()
        assert evidence.sound.rate == 44100 and len(evidence.sound.samples) == 44100
        assert evidence.sound.path.name == "play-coco1-3.wav" and evidence.sound.path.exists()
        assert evidence.keys_delivered == 2
        assert not list(project.output.glob("*.ppm")) and not list(project.output.glob("*.pcm"))

    def should_fail_when_the_emulator_rendered_no_frame(self, project: coco.Project) -> None:
        host = emulated(ram=bytes(32768))
        host.run.side_effect = lambda command, log, timeout, cwd=None, env=None: (
            Path(env["COCO_CHECKPOINT"]).write_bytes(ram_for(1)),
            log.write_text(f"COCO_CHECKPOINT,5,{TICKS}\n"),
        )
        built = coco.Build(binary=project.output / "main.bin", symbols=coco.parse_symbols(SYMBOLS))
        project.output.mkdir(parents=True)

        with pytest.raises(ValueError, match="rendered no complete frame"):
            coco.capture(project, host, built, "coco1", 1, coco.Equipment(video=True))


class DescribeRenderedAndSoundChecks:
    @pytest.fixture
    def capturing(self, folder: Path) -> coco.Project:
        (folder / "expected.py").write_text(MODEL + CAPTURE_MODEL)
        return coco.load_project(folder)

    def should_compare_every_rendered_sample(self, capturing: coco.Project) -> None:
        model = coco.load_expected(capturing.directory)
        picture = coco.Picture(path=Path("f.png"), pixels=np.full((2, 3, 3), 4, dtype=np.uint8))

        assert coco.verify_picture(capturing, model, picture, 4) == 6
        assert coco.verify_picture(capturing, model, None, 4) == 0
        with pytest.raises(ProjectError, match=r"Frame 3: rendered display: 6 of 6 .* x=0, y=0"):
            coco.verify_picture(capturing, model, picture, 3)

    def should_record_matched_frames_and_accepted_sound(self, capturing: coco.Project) -> None:
        record = coco.check_target(
            capturing, emulated(ram=bytes(32768)), "coco1", video=True, audio=True
        )

        main = record["variants"]["main"]
        assert main["rendered"]["compared_samples_each"] == 6
        assert main["rendered"]["images"] == [f"main-coco1-{f}.png" for f in (1, 3, 4)]
        assert main["sound"]["model"][0] == {"frame": 1, "samples": 44100}
        assert main["emulator"] == "/tools/xroar-instrumented"
        assert record["rendered_display"] == "matched expected_frame"
        assert record["sound"] == "accepted by verify_sound"
        lines = coco.report(capturing, record)
        assert "all 6 samples of the 3x2 frame matched expected_frame" in lines[-3]
        assert lines[-2].startswith("Sound: verify_sound accepted the mixer output")

    def should_reject_a_rendered_frame_that_differs(self, capturing: coco.Project) -> None:
        wrong = np.zeros((2, 3, 3), dtype=np.uint8)
        host = emulated(ram=bytes(32768), picture=wrong)

        with pytest.raises(ProjectError, match="Frame 1: rendered display"):
            coco.check_target(capturing, host, "coco1", video=True)

        assert not (capturing.output / "coco1-results.json").exists()

    def should_say_what_was_captured_but_not_compared(self, project: coco.Project) -> None:
        record = coco.check_target(
            project, emulated(ram=bytes(32768)), "coco1", video=True, audio=True
        )

        assert record["rendered_display"] == "captured; no expected_frame"
        lines = coco.report(project, record)
        assert "captured, not compared (no expected_frame)" in lines[-3]
        assert "captured, not checked (no verify_sound)" in lines[-2]

    def should_point_out_expectations_that_were_not_run(self, capturing: coco.Project) -> None:
        record = coco.check_target(capturing, emulated(ram=bytes(32768)), "coco1")

        lines = coco.report(capturing, record)
        assert "so expected_frame was not compared; add --video" in lines[-3]
        assert "verify_sound was not run" in lines[-2]

    def should_report_keys_per_variant(self, folder: Path) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        (folder / "play.txt").write_text("F\nL\n-\n")
        (folder / "expected.py").write_text(
            "def verify_ram(ram, symbols, frame, variant):\n    pass\n"
        )
        project = coco.load_project(folder)

        record = coco.check_target(project, emulated(ram=bytes(32768)), "coco1")

        keys = record["variants"]["play"]["keys"]
        assert keys == {
            "script": "play.txt",
            "at": "start",
            "steps": 3,
            "delivered_by_checkpoint": [3, 3, 3],
        }
        assert "keys" not in record["variants"]["main"]
        assert "Keys (play): 3 steps of play.txt" in coco.report(project, record)[1]


class DescribeEquipmentCommandLine:
    def should_check_with_video_and_audio(self, folder: Path, project, capsys) -> None:
        host = emulated(ram=bytes(32768))

        code = coco.main(["check", str(folder), "--target", "coco1", "--video", "--audio"], host)

        assert code == 0

        output = capsys.readouterr().out
        assert "Rendered display: captured" in output and "Sound: captured" in output

    def should_print_every_recorded_path_from_a_snapshot(
        self, folder: Path, project, tmp_path: Path, capsys
    ) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        script = tmp_path / "keys.txt"
        script.write_text("L\n")

        code = coco.main(
            ["snapshot", str(folder), "--video", "--audio", "--keys", str(script)],
            emulated(ram=bytes(32768)),
        )

        assert code == 0
        assert capsys.readouterr().out.splitlines() == [
            str(project.output / f"main-coco1-1.{kind}") for kind in ("ram", "png", "wav")
        ]

    @pytest.mark.parametrize(
        "arguments",
        [["run", "x", "--video"], ["build", "x", "--keys", "k"], ["check", "x", "--keys", "k"]],
    )
    def should_reject_equipment_where_it_does_not_apply(self, arguments: list[str]) -> None:
        host = Mock(spec=Host)

        with pytest.raises(SystemExit) as error:
            coco.main(arguments, host)

        assert error.value.code == 2
        assert not host.method_calls


class DescribeHost:
    def should_explain_missing_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(coco, "tool_path", lambda name: None)

        with pytest.raises(ProjectError, match=r"uv run python scripts/native\.py"):
            Host().executable("lwasm")

    def should_build_the_instrumented_emulator_on_demand(
        self, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        def ensure(say):
            say("Building the instrumented XRoar once")
            return Path("/local/xroar")

        monkeypatch.delenv("XROAR_INSTRUMENTED", raising=False)
        monkeypatch.setattr(coco.instrumented_xroar, "ensure", ensure)

        assert Host().instrumented() == "/local/xroar"
        assert "Building" in capsys.readouterr().err

    def should_use_an_explicitly_named_instrumented_emulator(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("XROAR_INSTRUMENTED", "/lab/xroar")
        monkeypatch.setattr(coco.instrumented_xroar, "ensure", Mock(side_effect=AssertionError))

        assert Host().instrumented() == "/lab/xroar"

    def should_log_process_output(self, tmp_path: Path) -> None:
        log = tmp_path / "out.log"

        Host().run(["sh", "-c", "echo evidence"], log, timeout=10)

        assert log.read_text() == "evidence\n"


def native_ready(*profiles: str) -> bool:
    tools = all(tool_path(name) for name in ("lwasm", "xroar"))
    return tools and all((ROOT / "local/roms" / p).is_dir() for p in profiles)


def firmware_profiles(directory: Path) -> set[str]:
    project = coco.load_project(directory)
    return {m.firmware or name for name, m in project.settings.targets.items()}


def uses_equipment(directory: Path) -> bool:
    settings = coco.load_project(directory).settings
    capture = settings.capture.video or settings.capture.audio
    return capture or any(variant.keys for variant in settings.variants.values())


def instrumented_ready(*profiles: str) -> bool:
    build_tools = not instrumented_xroar.missing_prerequisites(instrumented_xroar.BuildHost())
    return native_ready(*profiles) and build_tools


@pytest.mark.integration
class DescribeExamplesInXRoar:
    @pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
    def should_pass_the_real_check(self, example: Path, capsys) -> None:
        if not native_ready(*firmware_profiles(example)):
            pytest.skip("Native tools or firmware are not installed")
        if uses_equipment(example) and not instrumented_ready():
            pytest.skip("Build tools are needed for the instrumented XRoar")

        assert coco.main(["check", str(example)]) == 0

        assert "PASS" in capsys.readouterr().out

    @pytest.fixture
    def copy(self, tmp_path: Path) -> Path:
        if not native_ready("coco1"):
            pytest.skip("Native tools or CoCo 1 firmware are not installed")
        directory = tmp_path / "first-screen-copy"
        shutil.copytree(ROOT / "examples/first-screen", directory)
        return directory

    def should_reject_a_real_picture_that_differs(self, copy: Path, capsys) -> None:
        source = copy / "main.asm"
        source.write_text(source.read_text().replace("fcb $55,$AA,$FF,$00", "fcb $55,$AA,$FE,$00"))

        assert coco.main(["check", str(copy)]) == 1

        assert "screen bytes differ" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "change,message",
        [
            ('unreachable = "ready+1"', 'unreachable = "ready"'),
            ("frames = [1]", "frames = [2]"),
        ],
    )
    def should_fail_real_negative_controls(self, copy: Path, change, message, capsys) -> None:
        settings = copy / "coco.toml"
        settings.write_text(settings.read_text().replace(change, message).replace("= 10", "= 0.5"))

        assert coco.main(["check", str(copy)]) == 1

        error = capsys.readouterr().err
        assert "unreachable checkpoint 'ready' fired" in error or "did not reach" in error

    def should_enforce_ntsc_despite_conflicting_user_configuration(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        if not native_ready("coco1"):
            pytest.skip("Native tools or CoCo 1 firmware are not installed")
        (tmp_path / "xroar.conf").write_text("machine cocous\n tv-type pal\n")
        monkeypatch.setenv("XROAR_CONF_PATH", str(tmp_path))
        project = coco.load_project(ROOT / "examples/first-screen")

        printed = subprocess.run(
            coco.emulator(project, Host(), None) + ["-config-print"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout

        machine = re.search(r"^machine cocous\n((?:[ \t].*\n)*)", printed, re.MULTILINE)
        assert machine and "tv-type ntsc" in machine.group(1)

    @pytest.mark.parametrize("target", ["coco3-128", "coco3-512"])
    @pytest.mark.parametrize(
        "control,step",
        [
            ("BAD_REJECT", 3),
            ("BAD_FULL", 3),
            ("BAD_REPEAT", 5),
            ("BAD_LAST", 8),
            ("BAD_WRAP", 12),
        ],
    )
    def should_reject_each_broken_turn_queue(self, target: str, control: str, step: int) -> None:
        if not native_ready("coco3"):
            pytest.skip("Native tools or CoCo 3 firmware are not installed")
        example = ROOT / "examples/turn-queue"
        project = coco.load_project(example)
        built = coco.build(project, Host(), extra_defines=(control,))
        evidence = coco.capture(project, Host(), built, target, 1)

        with pytest.raises(ValueError, match=f"First, queue-lifecycle step {step}:"):
            coco.load_expected(example).verify_ram(evidence.ram, built.symbols, 1)


class DescribeFirmwareBoundary:
    @pytest.mark.parametrize(
        "example,target",
        [(path, name) for path in EXAMPLES for name in coco.load_project(path).settings.targets],
        ids=lambda value: value.name if isinstance(value, Path) else value,
    )
    @pytest.mark.parametrize("damage", ["missing", "empty", "wrong-bytes", "directory", "valid"])
    def should_launch_only_with_every_verified_rom(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        example: Path,
        target: str,
        damage: str,
    ) -> None:
        root = tmp_path / "project with spaces"
        machine = coco.load_project(example).settings.targets[target]
        profile = machine.firmware or target
        members = []
        for name in coco.firmware_names(machine):
            data = (profile + name).encode()
            path = root / "local/roms" / profile / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            members.append(
                {"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            )
        archive = "https://colorcomputerarchive.com/repo/ROMs/MAME-MESS/test.zip"
        (root / "roms.json").write_text(
            json.dumps({profile: {"url": archive, "sha256": "0" * 64, "members": members}})
        )
        damaged = root / "local/roms" / profile / members[-1]["name"]
        if damage == "missing":
            damaged.unlink()
        elif damage == "empty":
            damaged.write_bytes(b"")
        elif damage == "wrong-bytes":
            damaged.write_bytes(b"x" * members[-1]["size"])
        elif damage == "directory":
            damaged.unlink()
            damaged.mkdir()
        monkeypatch.setattr(coco, "ROOT", root)
        monkeypatch.setattr(
            coco, "build", lambda *args: coco.Build(binary=root / "x.bin", symbols={})
        )
        host = Host()
        monkeypatch.setattr(host, "executable", lambda name: name)
        launched = []
        monkeypatch.setattr(host, "launch", launched.append)

        code = coco.main(["run", str(example), "--target", target], host)

        if damage == "valid":
            assert code == 0
            for member in members:
                assert (
                    str((root / "local/roms" / profile / member["name"]).resolve()) in launched[0]
                )
        else:
            assert code == 1
            assert not launched


@pytest.mark.integration
class DescribeEquipmentInXRoar:
    @pytest.fixture
    def first_screen(self, tmp_path: Path) -> Path:
        if not instrumented_ready("coco1"):
            pytest.skip("Native tools, CoCo 1 firmware or instrumented build tools are missing")
        directory = tmp_path / "first-screen-copy"
        shutil.copytree(ROOT / "examples/first-screen", directory)
        return directory

    def should_match_the_rendered_first_screen(self, first_screen: Path, capsys) -> None:
        assert coco.main(["check", str(first_screen), "--video"]) == 0

        output = capsys.readouterr().out
        assert "all 98304 samples of the 512x192 frame matched expected_frame" in output
        assert (ROOT / "build/first-screen-copy/main-coco1-1.png").is_file()

    def should_reject_a_wrong_display_mode_that_memory_accepts(
        self, first_screen: Path, capsys
    ) -> None:
        source = first_screen / "main.asm"
        source.write_text(
            source.read_text().replace(
                "ifndef MODESET\nSAMV    equ %110", "ifndef MODESET\nSAMV    equ %010"
            )
        )

        assert coco.main(["check", str(first_screen)]) == 0
        assert coco.main(["check", str(first_screen), "--video"]) == 1

        assert "Frame 1: rendered display:" in capsys.readouterr().err

    def should_reject_a_wrong_coco2_display_mode_that_memory_accepts(
        self, tmp_path: Path, capsys
    ) -> None:
        if not instrumented_ready("coco2"):
            pytest.skip("Native tools, CoCo 2 firmware or instrumented build tools are missing")
        directory = tmp_path / "palette-swatches-copy"
        shutil.copytree(ROOT / "examples/palette-swatches", directory)
        source = directory / "main.asm"
        source.write_text(source.read_text().replace("sta $FFC5", "sta $FFC4"))

        assert coco.main(["check", str(directory), "--target", "coco2"]) == 0
        assert coco.main(["check", str(directory), "--target", "coco2", "--video"]) == 1

        assert "Frame 1: rendered display:" in capsys.readouterr().err

    def should_show_partial_erasure_when_the_shown_screen_is_redrawn(
        self, tmp_path: Path, capsys
    ) -> None:
        if not instrumented_ready("coco1"):
            pytest.skip("Native tools, CoCo 1 firmware or instrumented build tools are missing")
        directory = tmp_path / "page-flip-copy"
        shutil.copytree(ROOT / "examples/page-flip", directory)
        source = directory / "main.asm"
        source.write_text(source.read_text().replace("eora #$20", "eora #0"))
        settings = directory / "coco.toml"
        single = settings.read_text().replace("frames = [1, 2, 15,", "frames = [1] # ")

        settings.write_text(single.replace("video = true", "video = false"))
        assert coco.main(["check", str(directory), "--target", "coco1"]) == 0
        settings.write_text(single)
        assert coco.main(["check", str(directory), "--target", "coco1"]) == 1

        assert "Frame 1: rendered display:" in capsys.readouterr().err

    def should_reject_a_wrong_coco3_display_base_that_memory_accepts(
        self, tmp_path: Path, capsys
    ) -> None:
        if not instrumented_ready("coco3"):
            pytest.skip("Native tools, CoCo 3 firmware or instrumented build tools are missing")
        directory = tmp_path / "page-flip-coco3-copy"
        shutil.copytree(ROOT / "examples/page-flip-coco3", directory)
        source = directory / "main.asm"
        source.write_text(source.read_text().replace(" sta $FF9D", " inca\n sta $FF9D"))
        settings = directory / "coco.toml"
        shown = settings.read_text().replace('frames = ["1-6"]', "frames = [1]")
        arguments = ["check", str(directory), "--target", "coco3-128"]

        settings.write_text(shown.replace("video = true", "video = false"))
        assert coco.main(arguments) == 0
        settings.write_text(shown)
        assert coco.main(arguments) == 1

        assert "Frame 1: rendered display:" in capsys.readouterr().err

    def should_reject_an_expected_frame_with_reversed_bit_order(
        self, first_screen: Path, capsys
    ) -> None:
        model = first_screen / "expected.py"
        model.write_text(
            model.read_text().replace("pixel(s // across, line", "pixel((s // across) ^ 3, line")
        )

        assert coco.main(["check", str(first_screen), "--video"]) == 1

        assert "first at x=0, y=1" in capsys.readouterr().err

    def should_reject_a_journey_with_a_wrong_key(self, tmp_path: Path) -> None:
        if not instrumented_ready("coco1"):
            pytest.skip("Native tools, CoCo 1 firmware or instrumented build tools are missing")
        example = ROOT / "examples/collect-room"
        project = coco.load_project(example)
        lines = (example / "journey.txt").read_text().splitlines()
        step = next(i for i, line in enumerate(lines) if line.startswith("D    1 1 1"))
        lines[step] = "L" + lines[step][1:]
        script = tmp_path / "wrong-key.txt"
        script.write_text("\n".join(lines) + "\n")
        equipment = coco.equipment_for(project, "journey", script=script)
        model = coco.load_expected(example)

        with pytest.raises(ProjectError, match="Frame 15: .* screen bytes differ"):
            coco.check_variant(project, Host(), model, "coco1", "journey", equipment)

    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    @pytest.mark.parametrize(
        "control,message",
        [
            ("WRONG_COLUMN", "Keyboard/history differs"),
            ("STALE_HISTORY", "Keyboard/history differs"),
            ("HELD_SPACE", "Frame 2: .* screen bytes differ"),
            ("SILENT", "Frame 5: the mixer output has 0 effects, expected 1"),
        ],
    )
    def should_reject_each_broken_collect_room_build(
        self, target: str, control: str, message: str
    ) -> None:
        if not instrumented_ready("coco1", "coco2"):
            pytest.skip("Native tools, CoCo 1/2 firmware or instrumented build tools are missing")
        example = ROOT / "examples/collect-room"
        project = coco.load_project(example)
        variants = {"journey": coco.Variant(defines=(control,), keys="journey.txt")}
        broken = project.model_copy(
            update={"settings": project.settings.model_copy(update={"variants": variants})}
        )
        equipment = coco.equipment_for(broken, "journey")

        with pytest.raises(ValueError, match=message):
            coco.check_variant(
                broken, Host(), coco.load_expected(example), target, "journey", equipment
            )

    def should_reject_a_wrong_collect_room_display_mode_that_memory_accepts(
        self, tmp_path: Path, capsys
    ) -> None:
        if not instrumented_ready("coco1"):
            pytest.skip("Native tools, CoCo 1 firmware or instrumented build tools are missing")
        directory = tmp_path / "collect-room-copy"
        shutil.copytree(ROOT / "examples/collect-room", directory)
        source = directory / "main.asm"
        source.write_text(source.read_text().replace("sta $ffc5", "sta $ffc4"))
        settings = directory / "coco.toml"
        single = settings.read_text().replace('frames = ["1-95"]', "frames = [1]")
        arguments = ["check", str(directory), "--target", "coco1"]

        settings.write_text(single.replace("video = true", "video = false"))
        assert coco.main(arguments) == 0
        settings.write_text(single)
        assert coco.main(arguments) == 1

        assert "Frame 1: rendered display:" in capsys.readouterr().err

    @pytest.fixture
    def keyboard_controls(self) -> Path:
        if not instrumented_ready("coco1", "coco2"):
            pytest.skip("Native tools, CoCo 1/2 firmware or instrumented build tools are missing")
        return ROOT / "examples/keyboard-controls"

    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    @pytest.mark.parametrize(
        "control,update",
        [("WRONG_COLUMN", 4), ("WRONG_SELECT", 1), ("HELD_FIRE", 1), ("STALE_HISTORY", 6)],
    )
    def should_reject_each_broken_scanner_through_the_keyboard(
        self, keyboard_controls: Path, target: str, control: str, update: int
    ) -> None:
        project = coco.load_project(keyboard_controls)
        variants = {"keys": coco.Variant(defines=(control,), keys="keys.txt")}
        broken = project.model_copy(
            update={"settings": project.settings.model_copy(update={"variants": variants})}
        )
        equipment = coco.equipment_for(broken, "keys")
        model = coco.load_expected(keyboard_controls)

        with pytest.raises(ValueError, match=f"Update {update} "):
            coco.check_variant(broken, Host(), model, target, "keys", equipment)

    @pytest.fixture
    def sound_slots(self, tmp_path: Path) -> Path:
        if not instrumented_ready("coco1", "coco2"):
            pytest.skip("Native tools, CoCo 1/2 firmware or instrumented build tools are missing")
        directory = tmp_path / "sound-slots-copy"
        shutil.copytree(ROOT / "examples/sound-slots", directory)
        settings = directory / "coco.toml"
        settings.write_text(
            settings.read_text().replace(
                "frames = [1, 16, 17, 32, 33, 63, 64]", "frames = [1, 16, 64]"
            )
        )
        return directory

    @pytest.mark.parametrize(
        "silenced,replacement",
        [
            ("ora #8\n        sta $FF23", "anda #$F7\n        sta $FF23"),
            ("sample  sta $FF20", "        lda #$80\nsample  sta $FF20"),
        ],
        ids=["muted mux", "constant DAC"],
    )
    def should_reject_silence_that_memory_accepts(
        self, sound_slots: Path, silenced: str, replacement: str, capsys
    ) -> None:
        source = sound_slots / "main.asm"
        source.write_text(source.read_text().replace(silenced, replacement))
        settings = sound_slots / "coco.toml"
        untraced = settings.read_text().replace('trace_from = "sample"', "")

        settings.write_text(untraced.replace("audio = true", "audio = false"))
        assert coco.main(["check", str(sound_slots)]) == 0
        settings.write_text(untraced)
        assert coco.main(["check", str(sound_slots)]) == 1

        assert "Frame 1: no tone in the mixer output" in capsys.readouterr().err

    def should_reject_slow_foreground_work_on_coco2_that_memory_accepts(
        self, sound_slots: Path, capsys
    ) -> None:
        source = sound_slots / "main.asm"
        delay = "        bne tick\n        ldx #1000\ndelay   leax -1,x\n        bne delay\n"
        source.write_text(source.read_text().replace("        bne tick\n", delay))
        settings = sound_slots / "coco.toml"
        silent = settings.read_text().replace("audio = true", "audio = false")
        arguments = ["check", str(sound_slots), "--target", "coco2"]

        settings.write_text(silent.replace('trace_from = "sample"', ""))
        assert coco.main(arguments) == 0
        settings.write_text(silent)
        assert coco.main(arguments) == 1

        assert "between DAC writes; the budget is 40" in capsys.readouterr().err

    @pytest.fixture
    def timer_sound(self, tmp_path: Path) -> Path:
        if not instrumented_ready("coco3"):
            pytest.skip("Native tools, CoCo 3 firmware or instrumented build tools are missing")
        directory = tmp_path / "timer-sound-copy"
        shutil.copytree(ROOT / "examples/timer-sound", directory)
        return directory

    def should_reject_a_timer_masked_during_the_clear(self, timer_sound: Path, capsys) -> None:
        source = timer_sound / "main.asm"
        text = source.read_text().replace("redraw  sta ,x+", "        orcc #$40\nredraw  sta ,x+")
        source.write_text(text.replace("blo redraw\n", "blo redraw\n        andcc #$BF\n"))
        settings = timer_sound / "coco.toml"
        audible = settings.read_text()
        arguments = ["check", str(timer_sound), "--target", "coco3-1986"]

        settings.write_text(audible.replace("audio = true", "audio = false"))
        assert coco.main(arguments) == 0
        settings.write_text(audible)
        assert coco.main(arguments) == 1

        assert "Frame 1: no tone in the mixer output" in capsys.readouterr().err

    def should_stop_the_foreground_without_an_acknowledgement(
        self, timer_sound: Path, capsys
    ) -> None:
        settings = timer_sound / "coco.toml"
        text = settings.read_text().replace('defines = ["TIMER"]', 'defines = ["TIMER", "NO_ACK"]')
        settings.write_text(text.replace("emulated_seconds = 8", "emulated_seconds = 4"))

        assert coco.main(["check", str(timer_sound), "--target", "coco3-1986"]) == 1

        assert "coco3-1986 did not reach 'frame_ready' 1 times" in capsys.readouterr().err

    @pytest.fixture
    def tile_room(self, tmp_path: Path) -> Path:
        if not instrumented_ready("coco1"):
            pytest.skip("Native tools, CoCo 1 firmware or instrumented build tools are missing")
        directory = tmp_path / "tile-room-copy"
        shutil.copytree(ROOT / "examples/tile-room", directory)
        return directory

    def should_reject_a_changed_pixel_in_the_source_picture(self, tile_room: Path, capsys) -> None:
        drawing = tile_room / "tiles.png"
        with Image.open(drawing) as image:
            changed = image.convert("RGB")
        changed.putpixel((9, 1), (46, 188, 36))  # the wall's second row, second pixel
        changed.save(drawing)

        assert coco.main(["check", str(tile_room), "--target", "coco1"]) == 1

        assert "screen bytes differ" in capsys.readouterr().err

    def should_reject_a_write_past_the_screen(self, tile_room: Path, capsys) -> None:
        source = tile_room / "main.asm"
        clear = "clear   clr ,x+\n        cmpx #$1C00"
        source.write_text(source.read_text().replace(clear, clear.replace("1C00", "1C01")))

        assert coco.main(["check", str(tile_room), "--target", "coco1"]) == 1

        assert "damaged guards" in capsys.readouterr().err


@pytest.mark.integration
class DescribeRealAssembler:
    def should_reject_a_program_assembled_at_the_wrong_address(self, tmp_path: Path) -> None:
        if not tool_path("lwasm"):
            pytest.skip("LWASM is not installed")
        directory = tmp_path / "tile-room-copy"
        shutil.copytree(ROOT / "examples/tile-room", directory)
        source = directory / "main.asm"
        source.write_text(source.read_text().replace("org $3000", "org $3001"))

        with pytest.raises(ProjectError, match=r"start must be at \$3000"):
            coco.build(coco.load_project(directory), Host())

    @pytest.fixture
    def tile_room(self, tmp_path: Path) -> Path:
        if not tool_path("lwasm"):
            pytest.skip("LWASM is not installed")
        directory = tmp_path / "tile-room-copy"
        shutil.copytree(ROOT / "examples/tile-room", directory)
        return directory

    def assembler_log(self, directory: Path) -> str:
        project = coco.load_project(directory)
        with pytest.raises(subprocess.CalledProcessError):
            coco.build(project, Host())
        return (project.output / "main.assemble.log").read_text()

    def should_refuse_a_picture_table_that_names_a_missing_picture(self, tile_room: Path) -> None:
        drawing = tile_room / "tiles.png"
        with Image.open(drawing) as image:
            image.crop((0, 0, 32, 8)).save(drawing)  # the actor's cell is gone

        assert "Undefined symbol tiles_r0c4" in self.assembler_log(tile_room)

    def should_refuse_pictures_of_another_size(self, tile_room: Path) -> None:
        prepare = tile_room / "prepare.py"
        prepare.write_text(prepare.read_text().replace('"--size", "8x8"', '"--size", "16x16"'))

        assert "each picture row must be 1 byte" in self.assembler_log(tile_room)
