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
        if command[0] == "/tools/decb":
            if command[1] == "dskini":
                (cwd / command[2]).write_bytes(b"DISK")
            return
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

    @pytest.mark.parametrize(
        "variant,message",
        [
            ('defines = ["BIG"]\ntargets = ["coco3"]', r"targets \['coco3'\] are not declared"),
            ('defines = ["BIG"]\ntargets = []', "at least 1 item"),
            ('targets = ["coco2"]', "a variant needs defines"),
        ],
    )
    def should_reject_unusable_variant_targets(
        self, folder: Path, variant: str, message: str
    ) -> None:
        (folder / "coco.toml").write_text(f"{SETTINGS}\n[variants.big]\n{variant}\n")

        with pytest.raises(ProjectError, match=message):
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
        assert coco.model_call(project, lambda frame: frame, 3, variant="", target="coco1") == 3
        (folder / "coco.toml").write_text(SETTINGS + '\n[variants.fast]\ndefines = ["FAST"]\n')
        with_variants = coco.load_project(folder)

        result = coco.model_call(
            with_variants, lambda f, v: (f, v), 3, variant="fast", target="coco1"
        )

        assert result == (3, "fast")

    def should_pass_the_target_only_to_functions_that_declare_it(
        self, folder: Path, project: coco.Project
    ) -> None:
        (folder / "coco.toml").write_text(SETTINGS + '\n[variants.fast]\ndefines = ["FAST"]\n')
        with_variants = coco.load_project(folder)

        def by_keyword(frame, target):
            return frame, target

        def by_kwargs(frame, variant, **options):
            return frame, variant, options

        assert coco.model_call(project, by_keyword, 3, variant="", target="coco2") == (3, "coco2")
        assert coco.model_call(with_variants, by_kwargs, 3, variant="fast", target="coco2") == (
            3,
            "fast",
            {"target": "coco2"},
        )
        assert coco.model_call(project, len, b"ab", variant="", target="coco2") == 2

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

    def should_load_both_basic_roms_when_a_target_names_extended_basic(self) -> None:
        machine = coco.Machine(
            machine="cocous", ram_kib=32, basic="bas11.rom", extended="extbas11.rom"
        )
        roms = {"bas11.rom": Path("/r/b"), "extbas11.rom": Path("/r/e")}

        command = coco.xroar_command("xroar", machine, roms)

        assert coco.firmware_names(machine) == ("bas11.rom", "extbas11.rom")
        assert command == [
            "xroar",
            "-no-c",
            "-machine",
            "cocous",
            "-ram",
            "32",
            "-bas",
            "/r/b",
            "-extbas",
            "/r/e",
            "-no-cart",
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


def with_disk(folder: Path, extra: str = "") -> Path:
    """The fixture folder with a Disk BASIC ROM on coco1 only."""
    text = (folder / "coco.toml").read_text()
    text = text.replace('basic = "bas11.rom"\n', 'basic = "bas11.rom"\ndisk = "disk11.rom"\n')
    (folder / "coco.toml").write_text(text + extra)
    return folder


class DescribeDiskImages:
    @pytest.mark.parametrize(
        "folder_name,declared,expected",
        [("arena-blaster", None, "ARENABLA"), ("demo", "GAME1", "GAME1"), ("---", None, "PROGRAM")],
    )
    def should_name_the_program_from_settings_or_the_folder(
        self, tmp_path: Path, folder_name: str, declared: str | None, expected: str
    ) -> None:
        directory = tmp_path / folder_name
        directory.mkdir()
        disk = f'\n[disk]\nname = "{declared}"\n' if declared else ""
        (directory / "coco.toml").write_text(SETTINGS + disk)

        assert coco.load_project(directory).disk_name == expected

    @pytest.mark.parametrize("name", ["game", "TOOLONGNAME", "A.B", ""])
    def should_reject_a_name_disk_basic_cannot_hold(self, folder: Path, name: str) -> None:
        (folder / "coco.toml").write_text(SETTINGS + f'\n[disk]\nname = "{name}"\n')

        with pytest.raises(ProjectError, match="disk"):
            coco.load_project(folder)

    def should_put_the_disk_rom_in_the_controller_cartridge(self) -> None:
        machine = coco.Machine(machine="cocous", ram_kib=32, basic="b.rom", disk="d.rom")
        roms = {"b.rom": Path("/r/b"), "d.rom": Path("/r/d")}

        command = coco.xroar_command("xroar", machine, roms, disk=True)

        assert command[-4:] == ["-cart", "rsdos", "-cart-rom", "/r/d"]
        assert "-no-cart" not in command

    def should_format_then_copy_a_machine_language_file(self) -> None:
        commands = coco.disk_commands("decb", "main.bin", "main.dsk", "GAME")

        assert commands == [
            ["decb", "dskini", "main.dsk"],
            ["decb", "copy", "-2", "-b", "main.bin", "main.dsk,GAME.BIN"],
        ]

    def should_type_the_load_and_start_commands(self) -> None:
        options = coco.disk_options(Path("/b/main.dsk"), "GAME", write_back=False)

        assert options == [
            "-load-fd0",
            "/b/main.dsk",
            "-no-disk-write-back",
            "-type",
            'LOADM"GAME":EXEC\\r',
        ]

    def should_print_a_fresh_image_path(self, folder: Path, project, capsys) -> None:
        stale = project.output / "main.dsk"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"old")
        host = emulated()

        assert coco.main(["disk", str(folder)], host) == 0

        assert capsys.readouterr().out.splitlines() == [str(stale)]
        assert stale.read_bytes() == b"DISK"
        copy = host.run.call_args_list[-1]
        assert copy.args[0][-1] == "main.dsk,DEMO.BIN"
        assert copy.kwargs["cwd"] == project.output

    def should_fail_when_decb_writes_no_image(self, folder: Path, project, capsys) -> None:
        host = emulated()
        assemble = host.run.side_effect
        host.run.side_effect = lambda command, *args, **kwargs: (
            None if command[1] == "dskini" else assemble(command, *args, **kwargs)
        )

        assert coco.main(["disk", str(folder)], host) == 1

        assert "decb did not write" in capsys.readouterr().err

    def should_launch_the_disk_at_normal_speed(self, folder: Path, project) -> None:
        host = emulated()

        assert coco.main(["disk", str(with_disk(folder)), "--run"], host) == 0

        command = host.launch.call_args.args[0]
        cartridge = command.index("-cart")
        assert command[cartridge : cartridge + 4] == [
            "-cart",
            "rsdos",
            "-cart-rom",
            "/roms/disk11.rom",
        ]
        assert command[-5:] == [
            "-ratelimit",
            "-load-fd0",
            str(project.output / "main.dsk"),
            "-type",
            'LOADM"DEMO":EXEC\\r',
        ]

    def should_refuse_a_target_without_a_disk_rom_before_launching(
        self, folder: Path, capsys
    ) -> None:
        host = emulated()

        assert coco.main(["disk", str(folder), "--run", "--target", "coco2"], host) == 1

        assert not host.run.called
        assert not host.launch.called
        assert "[targets.coco2] names no Disk BASIC ROM" in capsys.readouterr().err

    def should_run_the_first_target_that_names_a_disk_rom(self, folder: Path) -> None:
        text = (folder / "coco.toml").read_text()
        text = text.replace('basic = "bas12.rom"\n', 'basic = "bas12.rom"\ndisk = "disk11.rom"\n')
        (folder / "coco.toml").write_text(text)
        host = emulated()

        assert coco.main(["disk", str(folder), "--run"], host) == 0

        assert host.launch.call_args.args[0][3] == "coco2bus"

    def should_make_an_image_for_a_target_without_a_disk_rom(self, folder: Path, project):
        assert coco.main(["disk", str(folder), "--target", "coco2"], emulated()) == 0

        assert (project.output / "main.dsk").exists()

    def should_check_every_disk_target_from_the_image(self, folder: Path, project, capsys):
        host = emulated(ram=bytes(32768))

        assert coco.main(["disk", str(with_disk(folder)), "--check"], host) == 0

        output = capsys.readouterr().out
        assert "Disk: coco1 booted Disk BASIC with disk11.rom" in output
        assert "coco2" not in output
        boot = host.run.call_args_list[-1]
        command = boot.args[0]
        assert command[-5:] == [
            "-load-fd0",
            str(project.output / "main.dsk"),
            "-no-disk-write-back",
            "-type",
            'LOADM"DEMO":EXEC\\r',
        ]
        assert "-run" not in command
        assert command[command.index("-timeout") + 1] == "70"
        assert boot.args[1] == project.output / "main-coco1-disk-1.log"
        record = json.loads((project.output / "coco1-main-disk-results.json").read_text())
        assert record["typed"] == 'LOADM"DEMO":EXEC'
        assert record["memory"].startswith("not compared")

    def should_fail_a_disk_that_never_reaches_the_checkpoint(self, folder: Path, project, capsys):
        assert coco.main(["disk", str(with_disk(folder)), "--check"], emulated()) == 1

        assert "after LOADM from the disk" in capsys.readouterr().err
        assert not (project.output / "coco1-main-disk-results.json").exists()

    def should_explain_a_disk_check_without_disk_targets(self, folder: Path, capsys) -> None:
        host = emulated()

        assert coco.main(["disk", str(folder), "--check"], host) == 1

        assert "No target names a Disk BASIC ROM" in capsys.readouterr().err
        assert not host.run.called

    def should_keep_a_record_for_each_variant(self, folder: Path, project) -> None:
        with_disk(folder, '\n[variants.wide]\ndefines = ["WIDE"]\n')
        host = emulated(ram=bytes(32768))

        assert coco.main(["disk", str(folder), "--check"], host) == 0
        assert coco.main(["disk", str(folder), "--check", "--variant", "wide"], host) == 0

        main = json.loads((project.output / "coco1-main-disk-results.json").read_text())
        wide = json.loads((project.output / "coco1-wide-disk-results.json").read_text())
        assert (main["build"], wide["build"]) == ("main", "wide")
        assert main["disk_image"] != wide["disk_image"]

    def should_skip_disk_targets_the_variant_does_not_allow(self, folder: Path, capsys) -> None:
        with_disk(folder, '\n[variants.wide]\ndefines = ["WIDE"]\ntargets = ["coco2"]\n')

        assert coco.main(["disk", str(folder), "--check", "--variant", "wide"], emulated()) == 1

        assert "No target names a Disk BASIC ROM" in capsys.readouterr().err

    def should_require_a_check_section_before_building(self, folder: Path, capsys) -> None:
        text = (with_disk(folder) / "coco.toml").read_text()
        (folder / "coco.toml").write_text(text.split("[check]")[0])
        host = emulated()

        assert coco.main(["disk", str(folder), "--check", "--target", "coco1"], host) == 1

        assert "has no [check] section" in capsys.readouterr().err
        assert not host.run.called


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


FIELD = 238944  # ticks in one NTSC field


def recording_host(frames: int = 120, fault: bool = False) -> Mock:
    """A host whose emulator streams frames and sound, and whose encoder writes the video."""
    host = emulated()
    host.encoder.return_value = "/tools/ffmpeg"
    assemble = host.run.side_effect

    def run(command, log, timeout, cwd=None, env=None):
        if command[0] == "/tools/ffmpeg":
            Path(command[-1]).write_bytes(b"HEVC")
            return
        assemble(command, log, timeout, cwd, env)

    def record(command, log, timeout, env, stream, encoder, encoder_log):
        if fault:
            Path(command[command.index("-trap-snap") + 1]).write_bytes(b"")
        lines = [f"COCO_FRAMES_START,{FIELD},{TICKS},512,192", "COCO_AUDIO_START,0,44100,1024"]
        lines += [f"COCO_FRAME,{FIELD * n}" for n in range(1, frames + 1)]
        buffers = 86
        lines += [f"COCO_AUDIO,{round(n * 1024 * TICKS / 44100)}" for n in range(1, buffers + 1)]
        log.write_text("\n".join(lines) + "\n")
        Path(env["COCO_AUDIO"]).write_bytes(bytes(buffers * 1024 * 2))
        Path(encoder[-1]).write_bytes(b"FFV1")

    host.run.side_effect = run
    host.record.side_effect = record
    return host


class DescribeRecording:
    def should_scale_by_whole_numbers_to_a_four_by_three_picture(self) -> None:
        assert coco.video_size(512, 192) == (1024, 768)
        assert coco.video_size(256, 192) == (1024, 768)
        assert coco.video_size(640, 240) == (1280, 960)

    def should_render_every_frame_for_the_seconds_asked(self, project: coco.Project) -> None:
        symbols = coco.parse_symbols(SYMBOLS)

        options = coco.record_options(
            symbols, 12.5, Path("/x.ram"), project.settings.check, coco.NO_EQUIPMENT, None
        )

        assert options[: len(coco.VIDEO_OPTIONS)] == coco.VIDEO_OPTIONS
        assert "-fskip" in options and options[options.index("-fskip") + 1] == "0"
        assert options[options.index("-timeout") + 1] == "12.5"
        assert options[options.index("-trap") + 1] == "pc=0x3020"
        assert "pc=0x3010" not in options  # no checkpoint: the run ends on time

    def should_encode_at_the_measured_rate_with_the_sound(
        self, folder: Path, project: coco.Project, capsys
    ) -> None:
        host = recording_host()

        assert coco.main(["record", str(folder), "--seconds", "2"], host) == 0

        video = project.output / "main-coco1-record.mp4"
        assert capsys.readouterr().out.splitlines() == [str(video)]
        command, _, _, env, stream, encoder, _ = host.record.call_args.args
        assert command[1:4] == ["-no-c", "-machine", "cocous"]
        assert command[0] == "/tools/xroar-instrumented"
        assert env["COCO_FRAMES"] == str(stream) and stream.suffix == ".frames"
        assert encoder[encoder.index("-i") + 1] == str(stream)
        final = host.run.call_args.args[0]
        filters = final[final.index("-vf") + 1]
        assert filters.startswith("setpts=N/(59.922743*TB)+0.000000/TB,")
        assert "scale=1024:768:flags=neighbor,setdar=4/3" in filters
        assert final[final.index("-c:v") + 1] == "libx265"
        assert final[final.index("-tag:v") + 1] == "hvc1"
        assert (project.output / "main-coco1-record.wav").stat().st_size == 86 * 1024 * 2 + 44
        assert not (project.output / "main-coco1-record.mkv").exists()
        assert not (project.output / "main-coco1-record.pcm").exists()

    def should_pass_the_key_script_to_the_emulator(self, folder: Path, project, capsys) -> None:
        (folder / "coco.toml").write_text(SETTINGS + KEYS)
        (folder / "play.txt").write_text("L\nF\n")
        host = recording_host()

        assert coco.main(["record", str(folder), "--variant", "play", "--seconds", "1"], host) == 0

        env = host.record.call_args.args[3]
        assert Path(env["COCO_KEYS"]).read_text() == "left\nspace\n"
        assert env["COCO_KEYS_AT"] == "pc=0x3000"

    @pytest.mark.parametrize(
        "host,message",
        [
            (recording_host(fault=True), "unreachable checkpoint 'state' fired"),
            (recording_host(frames=1), "fewer than two frames"),
        ],
    )
    def should_not_encode_a_failed_recording(self, folder: Path, host, message, capsys) -> None:
        assert coco.main(["record", str(folder), "--seconds", "1"], host) == 1

        assert message in capsys.readouterr().err
        assert all(call.args[0][0] != "/tools/ffmpeg" for call in host.run.call_args_list)

    def should_blame_an_emulator_that_streams_no_frames(self, folder: Path, capsys) -> None:
        host = recording_host()

        def silent(command, log, timeout, env, stream, encoder, encoder_log):
            log.write_text("COCO_AUDIO_START,0,44100,1024\n")
            raise ProjectError("ffmpeg could not read the frames")

        host.record.side_effect = silent

        assert coco.main(["record", str(folder), "--seconds", "1"], host) == 1

        assert "XRoar wrote no frames to the stream" in capsys.readouterr().err

    @pytest.mark.parametrize("seconds", ["0", "-1", "3601", "soon"])
    def should_reject_seconds_it_cannot_record(self, folder: Path, seconds: str) -> None:
        host = Mock(spec=Host)

        with pytest.raises(SystemExit):
            coco.main(["record", str(folder), "--seconds", seconds], host)

        assert not host.method_calls


ONLY_COCO2 = '\n[variants.wide]\ndefines = ["WIDE"]\ntargets = ["coco2"]\n'


MAPPED_SCREEN = "[targets.coco2]\nscreen = 0x10400\n"


class DescribeTargetScreens:
    @pytest.mark.parametrize(
        "check_screen,expected",
        [
            ("screen = 0x0400", {"coco1": 0x0400, "coco2": 0x10400}),
            ("", {"coco1": None, "coco2": 0x10400}),
        ],
    )
    def should_let_a_target_replace_the_check_screen(
        self, folder: Path, check_screen: str, expected: dict
    ) -> None:
        settings = SETTINGS.replace("screen = 0x0400", check_screen)
        (folder / "coco.toml").write_text(settings.replace("[targets.coco2]\n", MAPPED_SCREEN))
        project = coco.load_project(folder)

        offsets = {target: coco.screen_offset(project, target) for target in expected}

        assert offsets == expected

    def should_compare_the_screen_at_the_target_offset(
        self, folder: Path, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setattr(coco, "ROOT", tmp_path)
        settings = SETTINGS.replace("screen = 0x0400", "").replace('[1, "3-4"]', "[1]")
        (folder / "coco.toml").write_text(settings.replace("[targets.coco2]\n", MAPPED_SCREEN))
        (folder / "expected.py").write_text(
            "def expected_screen(frame, target):\n    calls.append(target)\n    return bytes([frame]) * 4\n\n"
            "calls = []\n"
        )
        project = coco.load_project(folder)
        ram = bytearray(0x20000)
        ram[0x10400:0x10404] = bytes([1]) * 4

        coco1 = coco.check_target(project, emulated(ram=bytes(ram)), "coco1")
        coco2 = coco.check_target(project, emulated(ram=bytes(ram)), "coco2")

        assert coco1["screen"] is None and coco1["variants"]["main"]["screen_bytes_each"] == 0
        assert coco2["screen"] == 0x10400 and coco2["variants"]["main"]["screen_bytes_each"] == 4
        assert set(coco.load_expected(folder).calls) == {"coco2"}
        assert "all 4 screen bytes at snapshot offset $10400" in coco.report(project, coco2)[1]
        ram[0x10402] = 9
        with pytest.raises(ProjectError, match=r"first at \$10402"):
            coco.check_target(project, emulated(ram=bytes(ram)), "coco2")


class DescribeVariantTargets:
    @pytest.fixture
    def restricted(self, folder: Path, tmp_path: Path, monkeypatch) -> coco.Project:
        monkeypatch.setattr(coco, "ROOT", tmp_path)
        (folder / "coco.toml").write_text(
            SETTINGS + ONLY_COCO2 + '\n[variants.fast]\ndefines = ["FAST"]\n'
        )
        return coco.load_project(folder)

    def should_select_only_the_variants_that_apply_to_a_target(
        self, restricted: coco.Project
    ) -> None:
        assert coco.variants_for(restricted, "coco1") == ("", "fast")
        assert coco.variants_for(restricted, "coco2") == ("", "wide", "fast")

    def should_choose_the_first_target_the_variant_allows(self, restricted: coco.Project) -> None:
        assert coco.variant_target(restricted, "wide", None) == "coco2"
        assert coco.variant_target(restricted, "fast", None) == "coco1"
        assert coco.variant_target(restricted, "", "coco2") == "coco2"
        with pytest.raises(ProjectError, match=r"'wide' applies only to targets \['coco2'\]"):
            coco.variant_target(restricted, "wide", "coco1")

    def should_skip_a_variant_on_targets_it_does_not_name(self, restricted: coco.Project) -> None:
        (restricted.directory / "expected.py").write_text(
            "def verify_ram(ram, symbols, frame, variant, target):\n"
            "    seen.append((variant, target))\n\nseen = []\n"
        )
        host = emulated(ram=bytes(32768))

        coco1 = coco.check_target(restricted, host, "coco1")
        coco2 = coco.check_target(restricted, host, "coco2")

        assembled = [c.args[0] for c in host.run.call_args_list if "--6809" in c.args[0]]
        assert sum("--define=WIDE" in command for command in assembled) == 1
        assert list(coco1["variants"]) == ["main", "fast"]
        assert coco1["variants_for_other_targets"] == {"wide": ["coco2"]}
        assert list(coco2["variants"]) == ["main", "wide", "fast"]
        assert coco2["variants_for_other_targets"] == {}
        seen = coco.load_expected(restricted.directory).seen
        assert ("wide", "coco2") in seen and ("wide", "coco1") not in seen
        assert ("main", "coco1") not in seen and ("", "coco1") in seen
        lines = coco.report(restricted, coco1)
        assert "in build(s) main, fast;" in lines[0]
        assert lines[1] == "Variant wide: not built for coco1; it applies only to coco2."

    def should_snapshot_a_variant_on_its_first_allowed_target(
        self, restricted: coco.Project, capsys
    ) -> None:
        host = emulated(ram=bytes(32768))

        assert coco.main(["snapshot", str(restricted.directory), "--variant", "wide"], host) == 0

        assert capsys.readouterr().out.splitlines() == [str(restricted.output / "wide-coco2-1.ram")]

    def should_refuse_a_target_the_variant_does_not_allow_before_building(
        self, restricted: coco.Project, capsys
    ) -> None:
        host = emulated()
        arguments = ["run", str(restricted.directory), "--variant", "wide", "--target", "coco1"]

        assert coco.main(arguments, host) == 1

        assert not host.run.called and not host.launch.called
        assert "applies only to targets ['coco2'], not 'coco1'" in capsys.readouterr().err


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

    def should_explain_a_missing_encoder(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(coco.shutil, "which", lambda name: None)

        with pytest.raises(ProjectError, match="brew install ffmpeg"):
            Host().encoder()

    def should_stream_frames_from_the_emulator_to_the_encoder(self, tmp_path: Path) -> None:
        stream, copy = tmp_path / "out.frames", tmp_path / "copy"
        emulator = ["sh", "-c", 'printf frames > "$COCO_FRAMES"']
        encoder = ["sh", "-c", f'cat "{stream}" > "{copy}"']

        Host().record(
            emulator,
            tmp_path / "x.log",
            10,
            {"COCO_FRAMES": str(stream), "PATH": "/usr/bin:/bin"},
            stream,
            encoder,
            tmp_path / "e.log",
        )

        assert copy.read_text() == "frames"
        assert not stream.exists()

    def should_release_the_encoder_when_the_emulator_writes_nothing(self, tmp_path: Path) -> None:
        stream = tmp_path / "out.frames"
        encoder = ["sh", "-c", f'cat "{stream}" > /dev/null; exit 1']

        with pytest.raises(ProjectError, match="ffmpeg could not read the frames"):
            Host().record(["true"], tmp_path / "x.log", 10, {}, stream, encoder, tmp_path / "e")

        assert not stream.exists()

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
        if not native_ready(*firmware_profiles(ROOT / "examples/first-screen")):
            pytest.skip("Native tools or first-screen firmware are not installed")
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

    @pytest.mark.parametrize("target", ["coco1", "coco2b"])
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
        if not native_ready(target):
            pytest.skip(f"Native tools or {target} firmware are not installed")
        example = ROOT / "examples/turn-queue"
        project = coco.load_project(example)
        built = coco.build(project, Host(), extra_defines=(control,))
        evidence = coco.capture(project, Host(), built, target, 1)

        with pytest.raises(ValueError, match=f"First, queue-lifecycle step {step}:"):
            coco.load_expected(example).verify_ram(evidence.ram, built.symbols, 1, target)


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
        if not instrumented_ready(*firmware_profiles(ROOT / "examples/first-screen")):
            pytest.skip("Native tools, first-screen firmware or instrumented tools are missing")
        directory = tmp_path / "first-screen-copy"
        shutil.copytree(ROOT / "examples/first-screen", directory)
        return directory

    def should_match_the_rendered_first_screen(self, first_screen: Path, capsys) -> None:
        assert coco.main(["check", str(first_screen), "--video"]) == 0

        output = capsys.readouterr().out
        assert "all 98304 samples of the 512x192 frame matched expected_frame" in output
        assert (ROOT / "build/first-screen-copy/main-coco1-1.png").is_file()

    @pytest.mark.parametrize("target", ["coco1", "coco3"])
    def should_record_every_frame_with_its_sound(self, first_screen: Path, target, capsys) -> None:
        if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
            pytest.skip("ffmpeg is missing")

        assert coco.main(["record", str(first_screen), "--target", target, "--seconds", "2"]) == 0

        video = Path(capsys.readouterr().out.strip())
        streams = json.loads(
            subprocess.run(
                ["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", video],
                capture_output=True,
                check=True,
                text=True,
            ).stdout
        )["streams"]
        picture, sound = streams
        assert (picture["codec_name"], picture["codec_tag_string"]) == ("hevc", "hvc1")
        assert (picture["width"], picture["height"]) == (1024, 768)
        assert 115 <= int(picture["nb_read_frames"]) <= 120  # 2 s of 59.92 Hz fields
        assert sound["codec_name"] == "aac"
        assert float(sound["duration"]) == pytest.approx(2, abs=0.05)

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
        single = settings.read_text().replace(
            "frames = [1, 2, 3, 4, 32, 33, 64, 65]", "frames = [1]"
        )

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
        directory = tmp_path / "page-flip-copy"
        shutil.copytree(ROOT / "examples/page-flip", directory)
        source = directory / "main.asm"
        source.write_text(
            source.read_text().replace("show    sta $FF9D", "show    inca\n        sta $FF9D")
        )
        settings = directory / "coco.toml"
        shown = settings.read_text().replace(
            "frames = [1, 2, 3, 4, 32, 33, 64, 65]", "frames = [1]"
        )
        arguments = ["check", str(directory), "--target", "coco3"]

        settings.write_text(shown.replace("video = true", "video = false"))
        assert coco.main(arguments) == 0
        settings.write_text(shown)
        assert coco.main(arguments) == 1

        assert "Frame 1: rendered display:" in capsys.readouterr().err

    @pytest.mark.parametrize(
        "line, wrong, error",
        [
            ("PAGE    equ SCREEN/$2000", "PAGE    equ $36", "screen bytes differ"),
            ("BASEHI  equ (SCREEN/$800)&$FF", "BASEHI  equ $D8", "rendered display:"),
        ],
    )
    def should_reject_a_coco3_text_screen_that_only_the_128k_alias_accepts(
        self, tmp_path: Path, capsys, line: str, wrong: str, error: str
    ) -> None:
        if not instrumented_ready("coco3"):
            pytest.skip("Native tools, CoCo 3 firmware or instrumented build tools are missing")
        directory = tmp_path / "text-addressing-copy"
        shutil.copytree(ROOT / "examples/text-addressing", directory)
        source = directory / "main.asm"
        source.write_text(source.read_text().replace(line, wrong))

        assert coco.main(["check", str(directory), "--target", "coco3-128"]) == 0
        assert coco.main(["check", str(directory), "--target", "coco3-512"]) == 1

        assert error in capsys.readouterr().err

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

    @pytest.mark.parametrize("target", ["coco1", "coco2", "coco2b", "coco3"])
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
        if not instrumented_ready("coco1", "coco2", "coco2b", "coco3"):
            pytest.skip("Native tools, CoCo 1/2/3 firmware or instrumented build tools are missing")
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
        if not instrumented_ready("coco1", "coco2", "coco2b", "coco3"):
            pytest.skip("Native tools, CoCo 1/2/3 firmware or instrumented build tools are missing")
        return ROOT / "examples/keyboard-controls"

    @pytest.mark.parametrize("target", ["coco1", "coco2", "coco2b", "coco3"])
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
        # WRONG_SELECT masks IRQ with the DDR selected, so on every target the
        # fault shows in the records instead of as a hang in BASIC's handler.

        with pytest.raises(ValueError, match=f"Update {update} "):
            coco.check_variant(broken, Host(), model, target, "keys", equipment)

    @pytest.fixture
    def sound_slots(self, tmp_path: Path) -> Path:
        if not instrumented_ready("coco1", "coco2", "coco2b", "coco3"):
            pytest.skip("Native tools, CoCo firmware or instrumented build tools are missing")
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
        source = timer_sound / "main.asm"
        acknowledge = "handler pshs a,b\n        lda $FF93"
        source.write_text(
            source.read_text().replace(acknowledge, "handler pshs a,b\n        lda #$20")
        )
        settings = timer_sound / "coco.toml"
        text = settings.read_text()
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


@pytest.mark.integration
class DescribeDisksInXRoar:
    """A real ToolShed image, booted by real Disk BASIC firmware in XRoar."""

    @pytest.fixture
    def template(self, tmp_path: Path) -> Path:
        if not (native_ready("coco1") and tool_path("decb")):
            pytest.skip("Native tools, ToolShed or firmware are not installed")
        directory = tmp_path / "disk-demo"
        shutil.copytree(ROOT / "template", directory)
        return directory

    def should_load_the_template_from_its_disk_and_reach_the_checkpoint(
        self, template: Path, capsys
    ) -> None:
        assert coco.main(["disk", str(template), "--check"]) == 0

        output = capsys.readouterr().out
        assert "Disk: coco1 booted Disk BASIC with disk11.rom" in output
        listing = subprocess.run(
            [tool_path("decb"), "dir", str(ROOT / "build/disk-demo/main.dsk")],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert re.search(r"DISKDEMO\s+BIN\s+2\s+B", listing)

    @pytest.mark.parametrize(
        "target,table",
        [
            ("coco2", 'machine = "cocous"\nbasic = "bas12.rom"\nextended = "extbas11.rom"'),
            ("coco2b", 'machine = "coco2bus"\nbasic = "bas13.rom"\nextended = "extbas11.rom"'),
            ("coco3", 'machine = "coco3"\nextended = "coco3.rom"'),
        ],
    )
    def should_load_the_template_from_a_disk_on_each_other_target(
        self, template: Path, target: str, table: str
    ) -> None:
        if not native_ready(target):
            pytest.skip(f"{target} firmware is not installed")
        ram = 128 if target == "coco3" else 32
        settings = template / "coco.toml"
        settings.write_text(
            settings.read_text()
            + f'\n[targets.{target}]\n{table}\nram_kib = {ram}\ndisk = "disk11.rom"\n'
        )

        assert coco.main(["disk", str(template), "--check", "--target", target]) == 0

    def should_not_reach_the_program_without_extended_basic(self, template: Path, capsys) -> None:
        # Measured: Disk BASIC 1.1 on a CoCo 1 with only Color BASIC never runs the typed LOADM.
        settings = template / "coco.toml"
        settings.write_text(settings.read_text().replace('extended = "extbas11.rom"\n', ""))

        assert coco.main(["disk", str(template), "--check"]) == 1

        assert "after LOADM from the disk" in capsys.readouterr().err
