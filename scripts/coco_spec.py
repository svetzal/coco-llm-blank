"""The project tool builds, launches and checks folders described only by their own files."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import coco
import pytest
from coco import Host, ProjectError
from native import ROOT, tool_path

SETTINGS = """
source = "main.asm"

[targets.coco1]
machine = "cocous"
cpu = "6809"
tv = "ntsc"
ram_kib = 32
basic = "bas11.rom"
extended = "extbas10.rom"

[targets.coco2]
machine = "coco2bus"
ram_kib = 32
basic = "bas12.rom"
extended = "extbas11.rom"
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
SYMBOLS = "start EQU $3000\nready EQU $3010\nstate EQU $3020\nprogram_end EQU $3030\n"
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


def emulated(ram: bytes | None = None, unreachable: bool = False, trace: str = "") -> Mock:
    """A host whose assembler writes symbols and whose emulator writes snapshots."""
    host = Mock(spec=Host)
    host.executable.side_effect = lambda name: f"/tools/{name}"
    host.firmware.side_effect = lambda profile, names: {n: Path("/roms") / n for n in names}

    def run(command, log, timeout, cwd=None):
        log.write_text(trace)
        if "--6809" in command:
            symbols = next(arg for arg in command if arg.startswith("--symbol-dump="))
            Path(symbols.split("=", 1)[1]).write_text(SYMBOLS)
            binary = next(arg for arg in command if arg.startswith("--output="))
            Path(binary.split("=", 1)[1]).write_bytes(b"DECB")
            return
        snaps = [command[i + 1] for i, arg in enumerate(command) if arg == "-trap-snap"]
        if unreachable:
            Path(snaps[0]).write_bytes(b"")
        frame = int(command[command.index("-trap-range") + 1])
        if ram is not None:
            Path(snaps[-1]).write_bytes(ram if len(ram) != 32768 else ram_for(frame))

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
        roms = {"bas12.rom": Path("/r/b"), "extbas11.rom": Path("/r/e")}

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
            "-extbas",
            "/r/e",
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
        assert "-trap pc=0x3010 -trap-range 4 -trap-snap s.ram" in joined
        assert "-trap-trace" not in joined

    def should_trace_from_a_label_until_the_checkpoint(self, project: coco.Project) -> None:
        check = project.settings.check.model_copy(update={"trace_from": "start"})

        options = coco.capture_options(check, coco.parse_symbols(SYMBOLS), 2, Path("s"), Path("u"))

        joined = " ".join(options)
        assert "-trap pc=0x3000 -trap-range 1 -trap-trace" in joined
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

        ram, log = coco.capture(project, host, built, "coco1", 3)

        assert ram == ram_for(3)
        assert log.name == "main-coco1-3.log"
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
        assert record["visual"] == "not inspected"
        assert "Memory: all 4 screen bytes" in coco.report(project, record)[1]

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


class DescribeHost:
    def should_explain_missing_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(coco, "tool_path", lambda name: None)

        with pytest.raises(ProjectError, match=r"uv run python scripts/native\.py"):
            Host().executable("lwasm")

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


@pytest.mark.integration
class DescribeExamplesInXRoar:
    @pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.name)
    def should_pass_the_real_check(self, example: Path, capsys) -> None:
        if not native_ready(*firmware_profiles(example)):
            pytest.skip("Native tools or firmware are not installed")

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
        source.write_text(re.sub(r"(square\s+lda\s+#)\$FF", r"\1$FE", source.read_text()))

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
