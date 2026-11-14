"""Build, play, or check Collect room with isolated firmware and keyboard evidence."""

import argparse
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

from coco import Host
from native import ROOT
from roms import verify_installed

executable = Host().executable

HERE = ROOT / "examples/collect-room"
OUTPUT = ROOT / "build/collect-room"
PROFILES = {
    "coco1": ("cocous", "bas11.rom", "extbas10.rom"),
    "coco2": ("coco2bus", "bas12.rom", "extbas11.rom"),
}
URL = "https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz"
SHA256 = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
MESSAGES = ("SPACE TO START", "COLLECT BOTH THEN EXIT", "YOU WIN SPACE RESTART")
ACTOR = bytes.fromhex("183c7edbff242466")
# Hand-transcribed original art rows, independent of converter/assembly output.
ART = tuple(
    bytes.fromhex(s)
    for s in ("0000200000000000", "ff80b8a0ae8280fd", "2070f87020000200", "e080a0a4be8480c1")
) + (ACTOR,)
ROOM = ("..#.....", ".*#..#..", "..#.....", "....##..", ".#...*..", "......E.")
FIELDS = ("phase", "xpos", "ypos", "remaining", "accepted", "starts", "effects", "last_effect")
MUTATIONS = ("WRONG_COLUMN", "STALE_HISTORY", "HELD_SPACE", "SILENT")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def journey() -> list[tuple[str, tuple[int, ...]]]:
    """Read hand-authored expectations, never derive them from observed RAM."""
    return [
        (parts[0], tuple(map(int, parts[1:])))
        for line in (HERE / "journey.txt").read_text().splitlines()
        if (parts := line.split()) and not line.startswith("#")
    ]


def headers() -> bytes:
    """Prepare original 5x7 lettering into three eight-scanline strips."""
    font = json.loads((HERE / "letters.json").read_text())
    output = bytearray()
    for message in MESSAGES:
        rows = [0] * 8
        for column, char in enumerate(message):
            for y, bits in enumerate(font[char]):
                rows[y] |= bits << (251 - (column * 6 + 16))
        output.extend(b"".join(row.to_bytes(32, "big") for row in rows))
    return bytes(output)


def expand(picture: bytes) -> bytes:
    """Duplicate each source pixel horizontally and each row vertically."""
    return b"".join(
        int("".join(bit * 2 for bit in f"{row:08b}"), 2).to_bytes(2, "big") * 2 for row in picture
    )


def prepare_assets(output: Path) -> None:
    """Use the existing validated asset preparer; map terrain IDs explicitly."""
    bundle = output / "prepared.json"
    bundle.unlink(missing_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "experiments/assets/prepare.py"),
            "build",
            "--output",
            str(bundle),
        ],
        check=True,
        timeout=30,
    )
    data = json.loads(bundle.read_text())
    pictures = {a["asset_id"]: bytes.fromhex(a["hex"]) for a in data["assets"]}
    packed = [pictures[i] for i in data["terrain_to_asset"]]
    if tuple(packed) != ART[:4]:
        raise ValueError("Terrain art changed: review the independent expected pixels first")
    values = b"".join(expand(picture) for picture in (*packed, ACTOR))
    lines = ["asset_guard_before fcb $a5", "art"]
    for label, block in (("", values), ("headers", headers())):
        if label:
            lines.append(label)
        lines.extend(
            "        fcb " + ",".join(f"${n:02x}" for n in block[i : i + 16])
            for i in range(0, len(block), 16)
        )
    lines.append("asset_guard_after fcb $a5")
    (output / "assets.inc").write_text("\n".join(lines) + "\n")


def build(output: Path, mutation: str = "") -> tuple[Path, dict[str, int]]:
    """Build fresh artifacts and reject overlap with the reserved stack."""
    output.mkdir(parents=True, exist_ok=True)
    for name in ("game.bin", "game.sym", "assets.inc"):
        (output / name).unlink(missing_ok=True)
    prepare_assets(output)
    binary, symbols = output / "game.bin", output / "game.sym"
    command = [
        executable("lwasm"),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
        f"--includedir={output}",
    ]
    if mutation:
        if mutation not in MUTATIONS:
            raise ValueError("Unknown mutation")
        command.append(f"--define={mutation}")
    subprocess.run([*command, str(HERE / "main.asm")], check=True, timeout=30)
    labels = {
        name: int(value, 16)
        for name, value in re.findall(r"(\w+) EQU \$([0-9A-Fa-f]+)", symbols.read_text())
    }
    if labels["start"] != 0x3000 or labels["program_end"] >= 0x7E00:
        raise ValueError("Code/state overlap memory reservations")
    return binary, labels


def emulator(target: str, path: str) -> list[str]:
    """Validate actual ROM bytes before producing any launch command."""
    machine, basic, extended = PROFILES[target]
    roms = verify_installed(ROOT, target, (basic, extended))
    return [
        path,
        "-no-c",
        "-machine",
        machine,
        "-machine-cpu",
        "6809",
        "-machine-keyboard",
        "coco",
        "-tv-type",
        "ntsc",
        "-vdg-type",
        "6847",
        "-ram",
        "32",
        "-bas",
        str(roms[basic]),
        "-extbas",
        str(roms[extended]),
        "-no-cart",
    ]


def patch_once(path: Path, anchor: str, replacement: str) -> None:
    text = path.read_text()
    if text.count(anchor) != 1:
        raise ValueError(f"Instrumentation anchor differs: {path.name}")
    path.write_text(text.replace(anchor, replacement))


def prepare_emulator() -> Path:
    """Build pinned headless XRoar locally. No install or shared source mutation."""
    work = OUTPUT / "instrumented"
    work.mkdir(parents=True, exist_ok=True)
    archive = work / "xroar-1.12.1.tar.gz"
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive.write_bytes(response.read())
    if digest(archive) != SHA256:
        raise ValueError("XRoar source checksum differs")
    source = work / "xroar-1.12.1"
    if source.exists():
        shutil.rmtree(source)
    with tarfile.open(archive) as package:
        package.extractall(work, filter="data")
    anchor = "static void handle_trap(void *sptr) {\n\tstruct trap_def *trap = sptr;"
    patch_once(
        source / "src/xroar.c",
        anchor,
        (HERE / "key_hook.c").read_text() + "\n" + anchor + "\n\tcollect_keyboard(trap->cond);",
    )
    anchor = "static void pia1a_data_postwrite_coco(void *sptr) {\n\tstruct dragon *md = sptr;"
    patch_once(
        source / "src/dragon/coco.c", anchor, anchor + "\n" + (HERE / "audio_hook.c").read_text()
    )
    for name, command in (
        (
            "configure",
            ["./configure", "--without-gtk2", "--without-gtk3", "--without-sdl3", "--without-sdl2"],
        ),
        ("make", ["make", "-j2"]),
    ):
        with (work / f"{name}.log").open("w") as log:
            subprocess.run(
                command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240
            )
    binary = source / "src/xroar"
    (work / "build.json").write_text(
        json.dumps(
            {
                "source_sha256": SHA256,
                "keyboard_hook": digest(HERE / "key_hook.c"),
                "audio_hook": digest(HERE / "audio_hook.c"),
                "binary_sha256": digest(binary),
            },
            indent=2,
        )
        + "\n"
    )
    return binary


def checked_emulator() -> Path:
    work = OUTPUT / "instrumented"
    binary = work / "xroar-1.12.1/src/xroar"
    manifest = json.loads((work / "build.json").read_text())
    expected = {
        "source_sha256": SHA256,
        "keyboard_hook": digest(HERE / "key_hook.c"),
        "audio_hook": digest(HERE / "audio_hook.c"),
        "binary_sha256": digest(binary),
    }
    if manifest != expected:
        raise ValueError("Instrumented emulator changed; run prepare-check again")
    return binary


def expected_room(collected: int) -> bytes:
    cells = bytearray(".#*E".index(c) for row in ROOM for c in row)
    if collected & 1:
        cells[9] = 0
    if collected & 2:
        cells[37] = 0
    return bytes(cells)


def expected_screen(state: tuple[int, ...]) -> bytes:
    """Independent per-pixel oracle, without expanded assets or packed headers."""
    phase, actor_x, actor_y, *_ = state
    cells = expected_room(state[8])
    font = json.loads((HERE / "letters.json").read_text())
    screen = bytearray(6144)
    for y in range(192):
        for x in range(256):
            bit = expected_pixel(x, y, cells, (actor_x, actor_y))
            column, subpixel = divmod(x - 16, 6)
            if 16 <= y < 23 and 0 <= column < len(MESSAGES[phase]) and subpixel < 5:
                bit = font[MESSAGES[phase][column]][y - 16] & (16 >> subpixel)
            if bit:
                screen[y * 32 + x // 8] |= 128 >> (x % 8)
    return bytes(screen)


def expected_pixel(x: int, y: int, cells: bytes, actor: tuple[int, int]) -> int:
    if not (64 <= x < 192 and 48 <= y < 144):
        return 0
    cx, cy = (x - 64) // 16, (y - 48) // 16
    tile = 4 if (cx, cy) == actor else cells[cy * 8 + cx]
    return ART[tile][((y - 48) % 16) // 2] & (128 >> (((x - 64) % 16) // 2))


def verify_ram(ram: bytes, labels: dict[str, int], keys: str, state: tuple[int, ...]) -> None:
    if len(ram) not in (32768, 65536):
        raise ValueError("Missing/truncated RAM")
    guards = [0x3FF, 0x1C00, 0x7E00] + [
        labels[n]
        for n in ("map_guard_before", "map_guard_after", "asset_guard_before", "asset_guard_after")
    ]
    if any(ram[a] != 0xA5 for a in guards):
        raise ValueError("Memory guard damaged")
    if tuple(ram[labels[n]] for n in FIELDS) != state[:8]:
        raise ValueError(f"Game state differs: {tuple(ram[labels[n]] for n in FIELDS)} != {state}")
    held = sum(bit for char, bit in zip("UDLRF", (1, 2, 4, 8, 16)) if char in keys)
    if ram[labels["held"]] != held or ram[labels["previous"]] != held:
        raise ValueError("Keyboard/history differs")
    if ram[labels["room"] : labels["room"] + 48] != expected_room(state[8]):
        raise ValueError("Room lifecycle differs")
    samples = int.from_bytes(ram[labels["sample_count"] : labels["sample_count"] + 2], "big")
    if samples != state[6] * 32 or ram[labels["sound_count"]] != 0:
        raise ValueError("Sound burst did not finish")
    if ram[0x400:0x1C00] != expected_screen(state):
        raise ValueError("Complete framebuffer differs")


def capture_command(
    target: str,
    emulator_path: Path,
    binary: Path,
    labels: dict[str, int],
    output: Path,
    count: int,
    unreachable: bool,
) -> list[str]:
    command = emulator(target, str(emulator_path)) + [
        "-ui",
        "null",
        "-ao",
        "null",
        "-ram-init",
        "set",
        "-no-ratelimit",
        "-timeout",
        "15",
        "-trap",
        f"pc=0x{labels['sample']:04x}",
        "-trap-range",
        f"1-{count}",
        "-trap",
        f"pc=0x{labels['room']:04x}",
        "-trap-snap",
        str(output / "unreachable.ram"),
    ]
    address = labels["room"] if unreachable else labels["frame_ready"]
    command += ["-trap", f"pc=0x{address:04x}", "-trap-range", f"1-{count}"]
    return command + ["-run", str(binary)]


def audio_evidence(log: str, labels: dict[str, int], expected_effects: int) -> dict:
    rows = [line.split(",")[1:] for line in log.splitlines() if line.startswith("DAC,")]
    samples = [
        (int(r[0]), *[int(value, 16) for value in r[1:]])
        for r in rows
        if int(r[1], 16) == labels["dac_write"] + 3
    ]
    if [r[2] & 0xFC for r in samples] != [252, 0] * (16 * expected_effects):
        raise ValueError("Actual DAC values differ")
    for _, _, _, cr, ddr, mux_a, mux_b, enable in samples:
        if not (cr & 4 and ddr & 252 == 252 and not (mux_a & 8 or mux_b & 8) and enable & 8):
            raise ValueError("DAC direction or routing differs")
    ticks = [r[0] for r in samples]
    gaps = [b - a for i, (a, b) in enumerate(itertools.pairwise(ticks)) if (i + 1) % 32]
    return {
        "dac_writes": len(samples),
        "within_burst_tick_range": [min(gaps), max(gaps)] if gaps else [],
        "listening": "not performed",
    }


def execute_case(target: str, mutation: str, inject: bool, unreachable: bool, output: Path) -> dict:
    binary, labels = build(output, mutation)
    emu = checked_emulator()
    cases = journey()
    events = output / "events.txt"
    events.write_text("\n".join(keys for keys, _ in cases) + "\n")
    command = capture_command(target, emu, binary, labels, output, len(cases), unreachable)
    env = dict(os.environ)
    env.pop("COLLECT_EVENTS", None)
    env.pop("COLLECT_KEY_TRAP", None)
    env.update(
        COLLECT_FRAME_TRAP=f"pc=0x{labels['frame_ready']:04x}",
        COLLECT_OUTPUT=str(output),
        COLLECT_FRAME_COUNT=str(len(cases)),
    )
    if inject:
        env.update(COLLECT_EVENTS=str(events), COLLECT_KEY_TRAP=f"pc=0x{labels['sample']:04x}")
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (output / "xroar.log").open("w") as log:
        subprocess.run(
            command,
            cwd=output,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=45,
        )
    if (output / "unreachable.ram").exists():
        raise ValueError("Unreachable trap fired")
    snapshots = sorted(output.glob("frame-*.ram"))
    if unreachable:
        if snapshots:
            raise ValueError("False checkpoint created RAM")
        return {"status": "passed", "unreachable": "no snapshot"}
    log = (output / "xroar.log").read_text()
    if log.count("KEY,") != (len(cases) if inject else 0):
        raise ValueError("Keyboard event count differs")
    for index, (keys, state) in enumerate(cases):
        if not inject:
            keys, state = "-", (0, 0, 0, 2, 0, 0, 0, 0, 0)
        verify_ram((output / f"frame-{index}.ram").read_bytes(), labels, keys, state)
    audio = audio_evidence(log, labels, cases[-1][1][6] if inject else 0)
    ticks = [int(line.split(",")[3]) for line in log.splitlines() if line.startswith("KEY,")]
    gaps = [b - a for a, b in itertools.pairwise(ticks)]
    _, basic, extended = PROFILES[target]
    roms = verify_installed(ROOT, target, (basic, extended))
    return {
        "status": "passed",
        "target": target,
        "machine": PROFILES[target][0],
        "ram_kib": 32,
        "cpu": "6809",
        "video": "NTSC 6847",
        "clock": "normal",
        "checkpoints": len(cases),
        "framebuffer_bytes_each": 6144,
        "input": "XRoar keyboard API to PIA to scanner" if inject else "no injected keys",
        "binary_sha256": digest(binary),
        "emulator_sha256": digest(emu),
        "rom_sha256": {name: digest(path) for name, path in roms.items()},
        "program_end": labels["program_end"],
        "audio": audio,
        "scan_interval_ticks": [min(gaps), max(gaps)] if gaps else [],
        "tick_rate_hz": 14318180,
        "renderer": "not captured or inspected",
        "physical": "not tested",
    }


def run_case(
    target: str, mutation: str = "", inject: bool = True, unreachable: bool = False
) -> dict:
    """Invalidate previous evidence before build/ROM validation, including failed reruns."""
    name = f"{target}-{mutation or 'normal'}-{'keys' if inject else 'idle'}"
    if unreachable:
        name += "-unreachable"
    output = OUTPUT / name
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    report = output / "result.json"
    report.write_text('{"status":"incomplete"}\n')
    try:
        result = execute_case(target, mutation, inject, unreachable, output)
    except BaseException as error:
        report.write_text(json.dumps({"status": "failed", "error": str(error)}, indent=2) + "\n")
        raise
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def check(target: str) -> dict:
    report = OUTPUT / f"{target}-check.json"
    report.unlink(missing_ok=True)
    result = run_case(target)
    run_case(target, inject=False)
    run_case(target, inject=False, unreachable=True)
    rejected = []
    for mutation in MUTATIONS:
        try:
            run_case(target, mutation)
        except ValueError as error:
            # A failed build, missing snapshot or tool failure is not a killed mutation.
            if not any(
                message in str(error)
                for message in (
                    "Game state differs",
                    "Keyboard/history differs",
                    "Actual DAC values differ",
                )
            ):
                raise
            rejected.append(mutation)
        else:
            raise ValueError(f"False control was accepted: {mutation}")
    result["rejected_mutations"] = rejected
    result["controls"] = ["no input stays at title", "unreachable has no snapshot"]
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "prepare-check", "check", "run"))
    parser.add_argument("--target", choices=PROFILES, default="coco1")
    args = parser.parse_args()
    if args.action == "prepare-check":
        print(prepare_emulator())
    elif args.action == "check":
        print(json.dumps(check(args.target), indent=2))
    else:
        binary, _ = build(OUTPUT / "play")
        if args.action == "run":
            subprocess.run(
                emulator(args.target, executable("xroar")) + ["-ratelimit", "-run", str(binary)],
                check=True,
            )
        else:
            print(binary)


if __name__ == "__main__":
    main()
