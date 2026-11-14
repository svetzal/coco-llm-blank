"""The assembled room obeys independent map rules on both defined machines."""

import json
import re
import shutil
import subprocess

import pytest
import tile_room


@pytest.fixture(scope="module")
def assembled():
    return tile_room.build()


class DescribeTileRoom:
    @pytest.mark.integration
    def should_check_every_move_and_pixel_on_both_targets(self, assembled, capsys):
        binary, symbols = assembled
        # Same build serves both targets so both evidence records survive.
        for target in tile_room.ROM_NAMES:
            tile_room.check(binary, symbols, target)
            result = json.loads(binary.with_name(f"{target}-results.json").read_text())
            assert result["checkpoints"] == list(range(42))
            ram = binary.with_name(f"{target}-40.ram").read_bytes()
            assert ram[symbols["room"] + 9] == 0  # Collected tile remains floor.
            for address in (
                0x03FF,
                0x1C00,
                0x400,
                0x1BFF,
                symbols["map_guard_before"],
                symbols["map_guard_after"],
                symbols["room"] + 9,
                symbols["room"] + 47,
                symbols["step"],
                symbols["accepted"],
                symbols["xpos"],
                symbols["ypos"],
            ):
                damaged = bytearray(ram)
                damaged[address] ^= 1
                with pytest.raises(ValueError):
                    tile_room.verify_ram(damaged, symbols, 40)
            with pytest.raises(ValueError, match="RAM"):
                tile_room.verify_ram(b"", symbols, 0)
        assert "PASS: coco2" in capsys.readouterr().out

    def should_specify_rejections_returns_and_persistent_collection(self):
        # Literal requirements, independently chosen checkpoints.
        for step, position, accepted in (
            (1, (0, 0), 0),
            (2, (0, 0), 0),
            (4, (1, 0), 0),
            (5, (1, 1), 1),
            (6, (1, 2), 1),
            (9, (2, 3), 0),
            (17, (5, 0), 0),
            (20, (7, 0), 0),
            (25, (7, 5), 1),
            (26, (7, 5), 0),
            (27, (6, 5), 1),
            (28, (7, 5), 1),
            (29, (6, 5), 1),
            (35, (2, 4), 0),
            (39, (1, 1), 1),
            (40, (1, 2), 1),
            (41, (1, 1), 1),
        ):
            actual_position, room, actual_acceptance = tile_room.expected_state(step)
            assert (actual_position, actual_acceptance) == (position, accepted)
            assert room[9] == (2 if step < 5 else 0)
        # The old actor cell is restored to the changed map, never to the item.
        screen = tile_room.expected_screen(40)
        assert all(screen[y * 32 + 1] == 0 for y in range(8, 16))
        # Distinctive last-room-row exit and first-row wall, with empty outer screen.
        assert tile_room.expected_screen(0)[40 * 32 + 6] == 0x7E
        assert tile_room.expected_screen(0)[2] == 255
        assert screen[-1] == 0
        for step in (-1, 42):
            with pytest.raises(ValueError, match="Checkpoint"):
                tile_room.expected_state(step)

    @pytest.mark.parametrize(
        "arguments,code", [(["--help"], 0), (["oops"], 2), (["check", "--unknown"], 2)]
    )
    def should_parse_before_any_side_effect(self, arguments, code, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(tile_room.subprocess, "run", lambda *a, **k: calls.append(a))
        monkeypatch.setattr(tile_room, "OUTPUT", tmp_path / "untouched")
        monkeypatch.setattr("sys.argv", ["tile_room.py", *arguments])
        with pytest.raises(SystemExit) as error:
            tile_room.main()
        assert error.value.code == code
        assert not calls and not tile_room.OUTPUT.exists()

    @pytest.mark.parametrize("state", ["missing", "partial", "corrupt"])
    def should_refuse_unverified_firmware(self, state, tmp_path, monkeypatch):
        root = tile_room.ROOT
        shutil.copyfile(root / "roms.json", tmp_path / "roms.json")
        directory = tmp_path / "local/roms/coco1"
        directory.mkdir(parents=True)
        if state != "missing":
            shutil.copyfile(root / "local/roms/coco1/bas11.rom", directory / "bas11.rom")
        if state == "corrupt":
            (directory / "extbas10.rom").write_bytes(b"wrong")
        monkeypatch.setattr(tile_room, "ROOT", tmp_path)
        with pytest.raises(ValueError, match="firmware"):
            tile_room.emulator("coco1")

    def should_invalidate_evidence_before_assembler_failure(self, tmp_path, monkeypatch):
        for name in ("coco1-results.json", "coco2-4.ram", "tile-room.bin", "symbols.txt"):
            (tmp_path / name).write_text("stale")
        monkeypatch.setattr(tile_room, "OUTPUT", tmp_path)
        monkeypatch.setattr(tile_room, "executable", lambda name: "/usr/bin/false")
        with pytest.raises(subprocess.CalledProcessError):
            tile_room.build()
        assert not list(tmp_path.iterdir())

    @pytest.mark.integration
    def should_reject_wrong_memory_placement(self, tmp_path, monkeypatch):
        source = tile_room.ROOT / "examples/tile-room/main.asm"
        destination = tmp_path / "examples/tile-room/main.asm"
        destination.parent.mkdir(parents=True)
        destination.write_text(source.read_text().replace("org $3000", "org $3001"))
        monkeypatch.setattr(tile_room, "ROOT", tmp_path)
        monkeypatch.setattr(tile_room, "OUTPUT", tmp_path / "build")
        with pytest.raises(ValueError, match="reservation"):
            tile_room.build()

    @pytest.mark.integration
    def should_reject_unreachable_or_unexpected_checkpoints(self, tmp_path, assembled):
        # Reuse the existing build; copies keep failure evidence away from success runs.
        binary = tmp_path / "tile-room.bin"
        original, symbols = assembled
        shutil.copyfile(original, binary)
        result = binary.with_name("coco1-results.json")
        result.write_text("stale success")
        stale = binary.with_name("coco1-0.ram")
        stale.write_bytes(bytes(32768))
        later = binary.with_name("coco1-41.ram")
        later.write_bytes(bytes(32768))
        with pytest.raises(ValueError, match="did not reach"):
            tile_room.check(binary, {**symbols, "frame_ready": 0x7D00}, "coco1")
        assert not result.exists() and not stale.exists() and not later.exists()
        with pytest.raises(ValueError, match="Unreachable"):
            tile_room.capture(binary, {**symbols, "room": symbols["start"]}, "coco1", 0)

    def should_route_check_and_normal_speed_run(self, monkeypatch, tmp_path):
        binary = tmp_path / "room.bin"
        monkeypatch.setattr(tile_room, "build", lambda: (binary, {}))
        checks, launches = [], []
        monkeypatch.setattr(tile_room, "check", lambda *args: checks.append(args))
        monkeypatch.setattr("sys.argv", ["tile_room.py", "check", "--target", "coco2"])
        tile_room.main()
        assert checks == [(binary, {}, "coco2")]
        monkeypatch.setattr(
            tile_room.subprocess, "run", lambda command, **kw: launches.append(command)
        )
        monkeypatch.setattr("sys.argv", ["tile_room.py", "run"])
        tile_room.main()
        assert launches[0][-3:] == ["-ratelimit", "-run", str(binary)]
        assert "-bas" in launches[0] and "-extbas" in launches[0]

    @pytest.mark.parametrize("target", ["coco1", "coco2"])
    def should_enforce_ntsc_despite_conflicting_user_configuration(
        self, target, tmp_path, monkeypatch
    ):
        config = tmp_path / "xroar.conf"
        config.write_text("machine cocous\n tv-type pal\n")
        monkeypatch.setenv("XROAR_CONF_PATH", str(tmp_path))
        executable = tile_room.executable("xroar")
        control = subprocess.run(
            [executable, "-c", str(config), "-machine", "cocous", "-config-print"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        control_machine = re.search(
            r"^machine cocous\n((?:[ \t].*\n)*)", control.stdout, re.MULTILINE
        )
        assert control_machine and "tv-type pal" in control_machine.group(1)
        actual = subprocess.run(
            tile_room.emulator(target) + ["-config-print"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        actual_machine = re.search(
            r"^machine cocous\n((?:[ \t].*\n)*)", actual.stdout, re.MULTILINE
        )
        assert actual_machine and "tv-type ntsc" in actual_machine.group(1)
        assert "tv-type pal" not in actual_machine.group(1)
