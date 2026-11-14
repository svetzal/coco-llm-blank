"""Private GIME renderer experiment. No GUI, installation, or shared-file mutation."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
from itertools import pairwise
from pathlib import Path

import numpy as np
from oracle import rgb, scene

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "experiments/display-validation")]
from instrument import CAPTURE, instrument, replace_once
from native import tool_path
from reproduce import CONFIGURE, digest, logged, obtain_archive
from roms import verify_installed

GIME_HASH = "fc6d038e022908cc4cf939a5a41ffdf7802bfeb9ae6f8f055cc64649f458c102"
VARIANTS = {"normal": None, "wrong-base": "WRONG_BASE", "unsafe": "UNSAFE"}


def patch_ui(source: bytes) -> bytes:
    text = instrument(source).decode()
    text = replace_once(
        text,
        CAPTURE[: CAPTURE.index("static void capture_viewport")],
        (HERE / "capture.c").read_text(),
    )
    return replace_once(
        text, "#include <stdio.h>", '#include <stdio.h>\n#include "events.h"'
    ).encode()


def patch_gime(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != GIME_HASH:
        raise ValueError("GIME source drift")
    text = source.decode()
    helper = r"""
static void clean_trace(struct TCC1014_private *gime, const char *kind) {
    const char *path = getenv("CLEAN_TRACE");
    if (!path) return;
    FILE *fp = fopen(path, "a");
    if (!fp) exit(2);
    fprintf(fp, "%s %u %u %u %u %u %u %u\n", kind,
            (unsigned)event_current_tick, gime->scanline, (unsigned)(event_current_tick - gime->scanline_start),
            gime->vertical.active_area, gime->Y, gime->B, gime->R1);
    if (fclose(fp)) exit(2);
}
"""
    text = replace_once(text, "#include <stdlib.h>", "#include <stdlib.h>\n#include <stdio.h>")
    marker = "static inline unsigned l_dt(struct TCC1014_private *gime) { return event_current_tick - gime->scanline_start; }"
    text = replace_once(text, marker + "\n#endif", marker + "\n#endif" + helper)
    for line, call in [
        ("gime->Y = (val << 11) | (gime->registers[0xe] << 3);", 'clean_trace(gime, "write");'),
        ("gime->B = gime->Y;", 'clean_trace(gime, "latch");'),
        ("SET_INTERRUPT(gime, INT_VBORD);", 'clean_trace(gime, "vb");'),
        (
            "uint16_t data = DELEGATE_CALL(gime->public.fetch_vram, gime->B + (gime->Xoff & 0xff));",
            'if (!gime->Xoff) clean_trace(gime, "fetch");',
        ),
    ]:
        text = replace_once(text, line, line + "\n" + call)
    return text.encode()


def build(work: Path, archive: Path | None) -> Path:
    work.mkdir(parents=True)
    package = obtain_archive(work / "xroar.tar.gz", archive)
    with tarfile.open(package) as stream:
        stream.extractall(work, filter="data")
    tree = work / "xroar-1.12.1"
    for name, patch in [("null/ui_null.c", patch_ui), ("tcc1014/tcc1014.c", patch_gime)]:
        target = tree / "src" / name
        target.write_bytes(patch(target.read_bytes()))
    logged(CONFIGURE, tree, work / "configure.log")
    logged(["make", "-j2"], tree, work / "make.log")
    return tree / "src/xroar"


def assemble(out: Path, variant: str) -> tuple[Path, dict[str, int]]:
    binary, symbols = out / "scene.bin", out / "scene.sym"
    command = [
        tool_path("lwasm", ROOT),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={symbols}",
    ]
    if VARIANTS[variant]:
        command.append(f"--define={VARIANTS[variant]}")
    command.append(str(HERE / "main.asm"))
    logged(command, ROOT, out / "assembly.log", 30)
    (out / "assembly-command.json").write_text(json.dumps(command))
    table = {
        n: int(v, 16)
        for n, v in re.findall(r"^(\w+) EQU \$([0-9A-Fa-f]+)", symbols.read_text(), re.MULTILINE)
    }
    if table["code_end"] > 0x4000:
        raise ValueError("Code exceeds allocation")
    return binary, table


def records(path: Path) -> list[tuple[int, bytes]]:
    frames = []
    with path.open("rb") as stream:
        while header := stream.readline():
            count, tick, width, height = map(int, header.split())
            if count != len(frames) + 1 or (width, height) != (512, 192):
                raise ValueError("Frame sequence or viewport")
            pixels = stream.read(width * height * 3)
            if len(pixels) != width * height * 3:
                raise ValueError("Truncated frame")
            frames.append((tick, pixels))
    if not frames:
        raise ValueError("No renderer frames")
    return frames


def check_ram(data: bytes, capacity: int, symbols: dict[str, int]) -> None:
    if len(data) != capacity * 1024:
        raise ValueError("RAM size")
    for address in (0x40FF, 0x5900, 0x60FF, 0x7900, 0x7DFF, 0x7F00):
        if data[address] != 0xA5:
            raise ValueError("RAM guard")
    if data[0x4100:0x5900] != scene(4) or data[0x6100:0x7900] != scene(3):
        raise ValueError("Complete RAM scenes")
    if data[-65536 + symbols["complete"]] != 0x5A:
        raise ValueError("Completion marker")


def check_publication(data: bytes, capacity: int, number: int) -> None:
    if len(data) != capacity * 1024:
        raise ValueError("Publication RAM size")
    for address in (0x40FF, 0x5900, 0x60FF, 0x7900, 0x7DFF, 0x7F00):
        if data[address] != 0xA5:
            raise ValueError("Publication guard")
    first, second = (number, number - 1) if number % 2 == 0 else (number - 1, number)
    if data[0x4100:0x5900] != scene(first) or data[0x6100:0x7900] != scene(second):
        raise ValueError("Publication complete scenes")


def analyze(frames: list[tuple[int, bytes]]) -> dict:
    expected = [rgb(n) for n in range(5)]
    first = next((i for i, (_, p) in enumerate(frames) if p == expected[0]), None)
    if first is None:
        raise ValueError("Initial scene absent")
    window = frames[first:]
    ticks = [t for t, _ in window]
    if any(b - a != 263 * 912 for a, b in pairwise(ticks)):
        raise ValueError("Nonconsecutive GIME fields")
    matches = [expected.index(p) if p in expected else None for _, p in window]
    return {
        "first_index": first,
        "ticks": ticks,
        "matches": matches,
        "rgb_sha256": [hashlib.sha256(p).hexdigest() for _, p in window],
        "incomplete": matches.count(None),
    }


def erasure_proofs(frames: list[tuple[int, bytes]], start: int = 0) -> list[dict]:
    proofs = []
    blank = bytes([2]) * 1536
    for index, (_, pixels) in enumerate(frames[start:], start):
        rows = [pixels[y * 1536 : (y + 1) * 1536] for y in range(192)]
        for number in range(5):
            complete = rgb(number)
            a = [row == complete[y * 1536 : (y + 1) * 1536] for y, row in enumerate(rows)]
            b = [row == blank for row in rows]
            if all(x or y for x, y in zip(a, b, strict=True)) and any(a) and any(b):
                proofs.append(
                    {
                        "capture_index": index,
                        "scene": number,
                        "retained_rows": [i for i, v in enumerate(a) if v],
                        "cleared_rows": [i for i, v in enumerate(b) if v],
                    }
                )
                break
    return proofs


def trace_records(path: Path) -> list[dict]:
    result = []
    for line in path.read_text().splitlines():
        kind, *values = line.split()
        result.append(
            dict(
                zip(
                    ("kind", "tick", "line", "offset", "active", "base", "scan", "fast"),
                    [kind, *map(int, values)],
                    strict=True,
                )
            )
        )
    return result


def timing(events: list[dict], variant: str) -> list[dict]:
    writes = [
        e for e in events if e["kind"] == "write" and e["base"] in (0x4100, 0x6100, 0x4900, 0x6900)
    ]
    if len(writes) != 5:
        raise ValueError("Missing display publications")
    if any(e["fast"] for e in events if e["tick"] >= writes[0]["tick"]):
        raise ValueError("Accelerated CPU clock")
    proof = []
    for write in writes[1:]:
        latch = next(e for e in events if e["kind"] == "latch" and e["tick"] > write["tick"])
        fetch = next(e for e in events if e["kind"] == "fetch" and e["tick"] > latch["tick"])
        if latch["scan"] != write["base"] or fetch["scan"] != write["base"]:
            raise ValueError("GIME did not fetch published base")
        if variant != "unsafe" and write["active"]:
            raise ValueError("Publication in active area")
        last_vb = [e for e in events if e["kind"] == "vb" and e["tick"] < write["tick"]][-1]
        if variant != "unsafe" and not 0 < write["tick"] - last_vb["tick"] < 912:
            raise ValueError("Publication missed bottom-border window")
        end = next(e for e in events if e["kind"] == "latch" and e["tick"] > latch["tick"])
        rows = [
            e["scan"]
            for e in events
            if e["kind"] == "fetch" and latch["tick"] < e["tick"] < end["tick"]
        ]
        if rows != list(range(write["base"], write["base"] + 6144, 32)):
            raise ValueError("GIME row fetch sequence")
        proof.append(
            {
                "write": write,
                "bottom_border": last_vb,
                "row_fetches": len(rows),
                "latch": latch,
                "first_fetch": fetch,
                "margin_ticks": latch["tick"] - write["tick"],
            }
        )
    return proof


def require_measurement(measurement: dict, variant: str) -> None:
    if variant == "normal":
        matches = measurement["matches"]
        transitions = [
            value for i, value in enumerate(matches) if i == 0 or value != matches[i - 1]
        ]
        if measurement["incomplete"] or len(matches) != 42 or transitions != list(range(5)):
            raise ValueError("Normal renderer not complete/progressing")
    elif not measurement["incomplete"]:
        raise ValueError("Faulty publication escaped renderer detection")
    if variant == "unsafe" and not measurement["erasure_proofs"]:
        raise ValueError("Unsafe control lacks specific partial-erasure witness")


def run(xroar: Path, out: Path, capacity: int, variant: str) -> dict:
    out.mkdir(parents=True)
    binary, symbols = assemble(out, variant)
    rom = verify_installed(ROOT, "coco3", ("coco3.rom",))["coco3.rom"]
    command = [
        str(xroar),
        "-c",
        "/dev/null",
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        "coco3",
        "-machine-cpu",
        "6809",
        "-tv-type",
        "ntsc",
        "-vdg-type",
        "gime1986",
        "-ram",
        str(capacity),
        "-extbas",
        str(rom),
        "-no-cart",
        "-tv-input",
        "rgb",
        "-vo-picture",
        "zoomed",
        "-fskip",
        "0",
        "-ram-init",
        "set",
        "-ratelimit",
        "-vo-brightness",
        "52",
        "-vo-contrast",
        "52",
        "-timeout",
        "10",
        "-trap",
        f"pc=0x{symbols['unreachable']:x}",
        "-trap-snap",
        str(out / "unreachable.ram"),
        "-trap",
        f"pc=0x{symbols['finished']:x}",
        "-trap-range",
        "1-1",
        "-trap-snap",
        str(out / "final.ram"),
        "-trap-timeout",
        "0.1",
        "-run",
        str(binary),
    ]
    for n in range(1, 5):
        command[-2:-2] = [
            "-trap",
            f"pc=0x{symbols[f'pub{n}']:x}",
            "-trap-range",
            "1-1",
            "-trap-snap",
            str(out / f"publication-{n}.ram"),
        ]
    (out / "command.json").write_text(json.dumps(command, indent=2))
    with (out / "run.log").open("wb") as log:
        subprocess.run(
            command,
            env={
                **os.environ,
                "CLEAN_CAPTURE": str(out / "frames.rgb"),
                "CLEAN_TRACE": str(out / "gime.txt"),
            },
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=45,
        )
    if (out / "unreachable.ram").exists():
        raise ValueError("Unreachable trap")
    check_ram((out / "final.ram").read_bytes(), capacity, symbols)
    for n in range(1, 5):
        check_publication((out / f"publication-{n}.ram").read_bytes(), capacity, n)
    frames = records(out / "frames.rgb")
    measurement = analyze(frames)
    measurement["erasure_proofs"] = erasure_proofs(frames, measurement["first_index"])
    proof = timing(trace_records(out / "gime.txt"), variant)
    require_measurement(measurement, variant)
    return {
        "capacity": capacity,
        "variant": variant,
        "measurement": measurement,
        "timing": proof,
        "rom_sha256": digest(rom),
        "code_end": symbols["code_end"],
        "artifacts_sha256": {p.name: digest(p) for p in out.iterdir() if p.is_file()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]+", args.run_id):
        parser.error("invalid run-id")
    out = ROOT / "build/clean-animation-coco3" / args.run_id
    if out.exists():
        parser.error("run exists; use a fresh run-id")
    out.mkdir(parents=True)
    report = {
        "passed": False,
        "runs": [],
        "source_sha256": {p.name: digest(p) for p in HERE.iterdir() if p.is_file()},
    }
    try:
        report["python_environment"] = {
            "python": sys.version,
            "numpy": np.__version__,
            "uv_lock_sha256": digest(ROOT / "uv.lock"),
            "pyproject_sha256": digest(ROOT / "pyproject.toml"),
        }
        verify_installed(ROOT, "coco3", ("coco3.rom",))
        xroar = build(out / "private", args.archive)
        report["executable_sha256"] = digest(xroar)
        report["tool_versions"] = {
            name: subprocess.check_output([str(path), "--version"], text=True).strip()
            for name, path in [("xroar", xroar), ("lwasm", tool_path("lwasm", ROOT))]
        }
        report["assembler_sha256"] = digest(Path(tool_path("lwasm", ROOT)))
        report["build_sha256"] = {
            str(p.relative_to(out / "private")): digest(p)
            for p in [
                out / "private/xroar.tar.gz",
                xroar.parents[1] / "config.h",
                xroar.parents[1] / "config.log",
                xroar.parents[1] / "config.status",
                *[
                    xroar.parent / name
                    for name in [
                        "null/ui_null.c",
                        "tcc1014/tcc1014.c",
                        "coco3.c",
                        "vo.c",
                        "vo_render.c",
                        "vo_render_tmpl.c",
                        "colourspace.c",
                        "events.h",
                        "tcc1014/tcc1014.h",
                    ]
                ],
            ]
        }
        report["shared_helpers_sha256"] = {
            str(p.relative_to(ROOT)): digest(p)
            for p in [
                ROOT / "experiments/display-validation/instrument.py",
                ROOT / "experiments/display-validation/reproduce.py",
                ROOT / "scripts/native.py",
                ROOT / "scripts/roms.py",
                ROOT / "roms.json",
            ]
        }

        for capacity in (128, 512):
            for variant in VARIANTS:
                result = run(xroar, out / f"{capacity}-{variant}", capacity, variant)
                report["runs"].append(result)
                print(capacity, variant, result["measurement"]["incomplete"], flush=True)
        report["passed"] = True
    finally:
        (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
