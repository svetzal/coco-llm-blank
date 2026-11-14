"""Consecutive software-video frames from a private, headless XRoar build."""

import argparse
import collections
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

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "experiments/display-validation")]
from coco import load_expected
from instrument import CAPTURE, instrument, replace_once
from native import tool_path
from reproduce import CONFIGURE, digest, logged, obtain_archive, provenance
from roms import verify_installed

ORACLE = "examples/moving-objects/expected.py"
MOVING = load_expected(ROOT / "examples/moving-objects")
expected_screen, verify_ram = MOVING.expected_screen, MOVING.verify_ram

DRAW = r"""static void capture_draw(void *sptr) {
    struct vo_interface *vo = sptr;
    struct vo_render *vr = vo->renderer;
    static unsigned count;
    const char *path = getenv("CADENCE_CAPTURE");
    if (!path) return;
    if (++count > 1000) { fprintf(stderr, "capture limit\n"); exit(2); }
    FILE *fp = fopen(path, "ab");
    if (!fp) { perror(path); exit(2); }
    fprintf(fp, "%u %u %d %d\n", count, (unsigned)event_current_tick,
            vr->viewport.w, vr->viewport.h);
    for (int y=0; y<vr->viewport.h; ++y) {
        uint32_t *row = (uint32_t *)vr->buffer + y*vr->buffer_pitch;
        unsigned char rgb[800*3];
        for (int x=0; x<vr->viewport.w; ++x) {
            rgb[3*x] = row[x] >> 24;
            rgb[3*x+1] = row[x] >> 16;
            rgb[3*x+2] = row[x] >> 8;
        }
        if (fwrite(rgb, 3, vr->viewport.w, fp) != (size_t)vr->viewport.w) exit(2);
    }
    if (fclose(fp)) exit(2);
}
"""


def patch(source: bytes) -> bytes:
    text = instrument(source).decode()
    old = CAPTURE[: CAPTURE.index("static void capture_viewport")]
    text = replace_once(text, old, DRAW)
    return replace_once(
        text, "#include <stdio.h>", '#include <stdio.h>\n#include "events.h"'
    ).encode()


def records(path: Path) -> list[tuple[int, bytes]]:
    result = []
    with path.open("rb") as stream:
        while header := stream.readline():
            count, tick, width, height = map(int, header.split())
            if count != len(result) + 1 or (width, height) != (512, 192):
                raise ValueError("bad frame sequence or viewport")
            pixels = stream.read(width * height * 3)
            if len(pixels) != width * height * 3:
                raise ValueError("truncated renderer frame")
            result.append((tick, pixels))
    if len(result) < 180:
        raise ValueError("missing consecutive frames")
    return result


def packed(pixels: bytes) -> bytes:
    rgb = np.frombuffer(pixels, dtype=np.uint8).reshape(192, 512, 3)
    black = np.all(rgb == (0, 31, 0), axis=2)
    green = np.all(rgb == (46, 188, 36), axis=2)
    if not np.all(black | green) or not np.array_equal(green[:, ::2], green[:, 1::2]):
        raise ValueError("unexpected palette or horizontal sample pairs")
    return np.packbits(green[:, ::2]).tobytes()


def analyze(frames: list[tuple[int, bytes]], scenes: list[bytes]) -> dict:
    # Startup is excluded only after an exact complete first-scene match.
    first = next((i for i, (_, rgb) in enumerate(frames) if safe_match(rgb, scenes[0])), None)
    if first is None or len(frames) - first < 150:
        raise ValueError("missing first scene or measurement window")
    window = frames[first : first + 150]
    ticks = [tick for tick, _ in window]
    intervals = [(b - a) & 0xFFFFFFFF for a, b in pairwise(ticks)]
    # MC6847: 262 lines * 912 quarter-VDG-clocks; EVENT_VDG_TIME is identity.
    if set(intervals) != {238944}:
        raise ValueError("draws are not consecutive NTSC video frames")
    screens = [packed(rgb) for _, rgb in window]
    matches = [scenes.index(screen) + 1 if screen in scenes else None for screen in screens]
    changes = [i for i in range(1, len(screens)) if screens[i] != screens[i - 1]]
    if len(changes) < 2:
        raise ValueError("animation did not change")
    runs = np.diff([0, *changes, len(screens)]).tolist()
    split = []
    erased = []
    backgrounds = [background(False), background(True)]
    for i, screen in enumerate(screens):
        if matches[i] is None:
            proof = row_mixture(screen, scenes)
            if proof:
                split.append({"video_index": i, **proof})
            erasure = erasure_mixture(screen, scenes)
            if erasure:
                erased.append({"video_index": i, **erasure})
    return {
        "first_capture_index": first,
        "video_frames": len(window),
        "frame_ticks": ticks,
        "frame_rgb_sha256": [hashlib.sha256(rgb).hexdigest() for _, rgb in window],
        "interval_ticks": dict(collections.Counter(intervals)),
        "span_ticks": ticks[-1] - ticks[0],
        "changed_transitions": len(changes),
        "identical_run_lengths": dict(collections.Counter(runs)),
        "complete_scene_frames": sum(m is not None for m in matches),
        "non_complete_scene_frames": sum(m is None for m in matches),
        "scene_matches": matches,
        "row_mixtures": split,
        "erasure_mixtures": erased,
        "background_only_frames": sum(s in backgrounds for s in screens),
    }


def background(inverted: bool) -> bytes:
    """Independent byte-coordinate checkerboard, with neither object present."""
    return bytes(
        255 if bool((x + y // 8) % 2) ^ inverted else 0 for y in range(192) for x in range(32)
    )


def erasure_mixture(screen: bytes, scenes: list[bytes]) -> dict | None:
    for n, scene in enumerate(scenes, 1):
        proof = row_mixture(screen, [scene, background(bool(n & 64))])
        if proof:
            return {
                "scene": n,
                "object_rows": proof["old_only_rows"],
                "erased_rows": proof["new_only_rows"],
            }
    return None


def safe_match(rgb: bytes, screen: bytes) -> bool:
    try:
        return packed(rgb) == screen
    except ValueError:
        return False


def row_mixture(screen: bytes, scenes: list[bytes]) -> dict | None:
    actual = np.frombuffer(screen, np.uint8).reshape(192, 32)
    for n, (before, after) in enumerate(pairwise(scenes), 1):
        a = np.all(actual == np.frombuffer(before, np.uint8).reshape(192, 32), axis=1)
        b = np.all(actual == np.frombuffer(after, np.uint8).reshape(192, 32), axis=1)
        if np.all(a | b) and np.any(a & ~b) and np.any(b & ~a):
            return {
                "scenes": [n, n + 1],
                "old_only_rows": np.where(a & ~b)[0].tolist(),
                "new_only_rows": np.where(b & ~a)[0].tolist(),
            }
    return None


def source_for(source: str, heavy: bool) -> str:
    if not heavy:
        return source
    return replace_once(source, "bg_byte sta ,x+", "bg_byte sta ,x+\n" + "        nop\n" * 32)


def run_case(name: str, source: str, xroar: Path, work: Path, out: Path) -> dict:
    firmware = verify_installed(ROOT, "coco1", ("bas11.rom", "extbas10.rom"))
    asm = work / f"{name}.asm"
    asm.write_text(source)
    binary, sym = out / f"{name}.bin", out / f"{name}.sym"
    assemble = [
        tool_path("lwasm", ROOT),
        "--6809",
        "--format=decb",
        f"--output={binary}",
        f"--symbol-dump={sym}",
        str(asm),
    ]
    logged(assemble, ROOT, out / f"{name}-assembly.log", 30)
    symbols = {
        k: int(v, 16)
        for k, v in re.findall(r"^(\w+)\s+EQU\s+\$([\da-fA-F]+)", sym.read_text(), re.MULTILINE)
    }
    if symbols["program_end"] >= 0x7E00:
        raise ValueError("stack overlap")
    ram, negative, capture = [
        out / f"{name}.{suffix}" for suffix in ("ram", "unreachable.ram", "frames")
    ]
    command = [
        str(xroar),
        "-c",
        os.devnull,
        "-ui",
        "null",
        "-ao",
        "null",
        "-machine",
        "cocous",
        "-machine-cpu",
        "6809",
        "-vdg-type",
        "6847",
        "-ram",
        "32",
        "-bas",
        str(firmware["bas11.rom"]),
        "-extbas",
        str(firmware["extbas10.rom"]),
        "-no-cart",
        "-tv-input",
        "svideo",
        "-ccr",
        "none",
        "-vo-picture",
        "zoomed",
        "-fskip",
        "0",
        "-ram-init",
        "set",
        "-ratelimit",
        "-timeout",
        "12",
        "-trap",
        f"pc=0x{symbols['state']:x}",
        "-trap-snap",
        str(negative),
        "-trap",
        f"pc=0x{symbols['frame_ready']:x}",
        "-trap-range",
        "1-1",
        "-trap-snap",
        str(ram),
        "-trap-timeout",
        "3",
        "-run",
        str(binary),
    ]
    (out / f"{name}-commands.json").write_text(json.dumps([assemble, command], indent=2))
    with (out / f"{name}.log").open("wb") as log:
        subprocess.run(
            command,
            env={**os.environ, "CADENCE_CAPTURE": str(capture)},
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=30,
        )
    if negative.exists():
        raise ValueError("unreachable checkpoint fired")
    verify_ram(ram.read_bytes(), symbols, 1)
    result = analyze(records(capture), [expected_screen(i) for i in range(1, 65)])
    return {
        "measurement": result,
        "source_sha256": digest(asm),
        "binary_sha256": digest(binary),
        "capture_sha256": digest(capture),
        "snapshot_sha256": digest(ram),
    }


def require_controls(results: dict) -> None:
    normal = results["normal"]["measurement"]
    heavy = results["heavy"]["measurement"]
    if normal != results["repeat"]["measurement"]:
        raise ValueError("repeat changed emulated measurements")
    normal_states = {s for s in normal["scene_matches"] if s is not None}
    heavy_states = {s for s in heavy["scene_matches"] if s is not None}
    if len(normal_states) < 5 or len(heavy_states) >= len(normal_states):
        raise ValueError("workload did not reduce complete scene progression")
    if not normal["erasure_mixtures"] or not heavy["non_complete_scene_frames"]:
        raise ValueError("partial-update evidence absent")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_-]+", args.run_id):
        parser.error("invalid run-id")
    work = ROOT / "local/research/animation-cadence" / args.run_id
    out = ROOT / "build/animation-cadence" / args.run_id
    if work.exists() or out.exists():
        parser.error("run exists; choose a fresh run-id")
    firmware = verify_installed(ROOT, "coco1", ("bas11.rom", "extbas10.rom"))
    assembler = tool_path("lwasm", ROOT)
    if not assembler:
        parser.error("LWASM missing")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = provenance(assembler, firmware)
    report["inputs_sha256"].update(
        {str(p.relative_to(ROOT)): digest(p) for p in Path(__file__).parent.glob("*.py")}
    )
    report["inputs_sha256"][ORACLE] = digest(ROOT / ORACLE)
    archive = obtain_archive(work / "xroar.tar.gz", args.archive)
    with tarfile.open(archive) as package:
        package.extractall(work, filter="data")
    tree = work / "xroar-1.12.1"
    inspected = [
        "src/null/ui_null.c",
        "src/vo.h",
        "src/vo.c",
        "src/events.h",
        "src/dragon/dragon.c",
        "src/mc6847/mc6847.c",
        "src/mc6847/mc6847.h",
        "src/xroar.c",
        "doc/xroar.texi",
    ]
    report["upstream_sources_sha256"] = {p: digest(tree / p) for p in inspected}
    target = tree / "src/null/ui_null.c"
    target.write_bytes(patch(target.read_bytes()))
    logged(CONFIGURE, tree, out / "configure.log")
    logged(["make", "-j2"], tree, out / "make.log")
    xroar = tree / "src/xroar"
    report["build"] = {
        "configure": CONFIGURE,
        "executable_sha256": digest(xroar),
        "instrumented_ui_sha256": digest(target),
    }
    source = (ROOT / "examples/moving-objects/main.asm").read_text()
    report["cases"] = {}
    for name in ("normal", "heavy", "repeat"):
        report["cases"][name] = run_case(
            name, source_for(source, name == "heavy"), xroar, work, out
        )
        measurement = report["cases"][name]["measurement"]
        print(
            name,
            measurement["changed_transitions"],
            "changed transitions;",
            measurement["non_complete_scene_frames"],
            "non-complete scenes",
            flush=True,
        )
    require_controls(report["cases"])
    report["passed"] = True
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
