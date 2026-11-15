# Page flip on CoCo 3

This original example uses the native CoCo 3 graphics of the GIME. It draws
each scene into a buffer that is not shown. Then one write to `$FF9D` shows the
finished scene.

The scene is a white outline and an 8x8 square on a black
256x192 bitmap. The square moves right in five steps, then starts again. It is
not a game.

Ask your agent to run these steps. Commands start in the project folder:

```sh
sh scripts/bootstrap.sh coco3
uv run python scripts/coco.py check examples/page-flip-coco3
uv run python scripts/coco.py run examples/page-flip-coco3
```

The `run` command opens XRoar. Close the window to stop it. There are no
controls and no return to BASIC.

## How it works

The display start address is `$FF9D` x 2048 + `$FF9E` x 8.
[Tandy CoCo 3 service manual, PDF 13][service] Buffer A starts at physical
address `$04100` and buffer B at `$06100`. Both have `$20` in `$FF9E`, so only
`$FF9D` changes at a flip: `$08` for A and `$0C` for B.

The program sets these registers once. The service manual gives each bit:

- `$FF90=$6E`: native mode, MMU on, GIME IRQ output on, 32 KiB internal ROM.
  [Tandy, PDF 11][service-11]
- `$FF92=$08`: the vertical border (VBORD) is the only GIME IRQ source. The CPU
  keeps IRQ and FIRQ masked. [Tandy, PDF 11][service-11]
- `$FF98=$80`, `$FF99=$08`: 256x192 with one bit for each pixel.
  [Tandy, PDF 12 and 18][service-12]
- Palette entry 0 is `$00` (black) and entry 1 is `$3F` (white), for RGB
  output. [Tandy, PDF 17][service-17]
- MMU entries `$FFA2` and `$FFA3` map physical pages 2 and 3 to CPU
  `$4000-$7FFF`. [Tandy, PDF 15-16][service-15]

For each scene, the program does these steps:

1. Draw the scene into the buffer that is not shown.
2. Read `$FF92` to clear an old VBORD. Then wait until bit 3 of `$FF92` is set.
   [Tepolt, PDF 50][tepolt]
3. Write `$FF9D` to show the new buffer. This is the `published` label.
4. Wait for the next VBORD. Then draw the next scene into the other buffer.

## What the check proves

The `[capture]` table in [coco.toml](coco.toml) turns on the rendered check, so
`check` always uses the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
It runs six checkpoints on each target: scenes 0 to 4 and the return to scene
0. Each checkpoint is one hit of `published`. It compares:

- The scene number and the six guard bytes.
- The buffer that was just drawn: it must be the other buffer each time, and
  all 6144 bytes must match `expected_screen` in [expected.py](expected.py).
- All 512x192 samples of the rendered frame with `expected_frame`.

The rendered frame is the second frame that XRoar completes after the
checkpoint. So the check proves that the display shows the new scene complete.

An integration test in `scripts/coco_spec.py` is the negative control. It adds
one to the value written to `$FF9D`, so the GIME shows memory 2 KiB past the
buffer. The memory check still passes. The rendered check fails.

The spec, [page_flip_coco3_spec.py](page_flip_coco3_spec.py), checks the model.
It rejects damaged guards and state, a scene drawn into the shown buffer, and
the previous scene.

## Limits

The black and white RGB values in `expected.py` come from the capture of the
pinned XRoar with the renderer settings of `coco.py`. They are not a monitor
measurement.

The check sees one rendered frame for each checkpoint. A program that draws
into the shown buffer after the next VBORD still passes this check, because
that drawing starts after the captured frame. Use the CoCo 1/2
[page flip](../page-flip/README.md) control to see partial erasure.

The sources that we read do not give the instant at which the real GIME loads
`$FF9D`, or a safe delay after VBORD. So this example writes only one register,
and it waits one more VBORD before it uses the old buffer again. Physical
timing, PAL, GIME 1987, 6309 and disk loading are not tested.

## Target and memory

There are two targets: XRoar `coco3`, NTSC, a 6809 at the normal rate
(`$FFD8`), GIME 1986, and the combined `coco3.rom`. `coco3-128` has 128 KiB
RAM and `coco3-512` has 512 KiB. [Tepolt, PDF 62][tepolt-62]

| Purpose | CPU address | Physical address |
| --- | --- | --- |
| Code and state | `$3000-$3FFF` | Executive page `$39` |
| Buffer A | `$4100-$58FF` | `$04100-$058FF` |
| Buffer B | `$6100-$78FF` | `$06100-$078FF` |
| Guards | `$40FF`, `$5900`, `$60FF`, `$7900`, `$7DFF`, `$7F00` | Same, low |
| Stack | `$7E00-$7EFF`, top `$7F00` | Same, low |

The display reads physical memory. It does not use the CPU map.
[Tepolt, PDF 28-30][tepolt-28]

[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=13>
[service-11]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=11>
[service-12]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=12>
[service-15]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=15>
[service-17]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=17>
[tepolt]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=50>
[tepolt-62]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=62>
[tepolt-28]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=28>
