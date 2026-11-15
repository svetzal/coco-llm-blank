# Page flip on CoCo 1 and CoCo 2

This original example draws each frame into a screen that is not shown. Then
one SAM write shows the finished frame. The display never shows a frame that is
not complete.

The scene is the scene of
[moving objects](../moving-objects/README.md): two rectangles over a checker
pattern that changes. It is not a game.

Ask your agent to run these steps. Commands start in the project folder:

```sh
sh scripts/bootstrap.sh coco1
uv run python scripts/setup.py --target coco2 --roms-only
uv run python scripts/coco.py check examples/page-flip
uv run python scripts/coco.py run examples/page-flip
```

The `run` command opens XRoar. Close the window to stop it. There are no
controls and no return to BASIC.

## How it works

The two screens are at `$0400` and `$2400`. Their start addresses differ only
in SAM display offset bit F4. So one write to `$FFCE` (clear F4) or `$FFCF`
(set F4) changes the screen that the display shows. [Tandy, PDF 15][sam]

For each frame, the program does these steps:

1. Draw the background and both rectangles into the screen that is not shown.
2. Read `$FF02` to clear an old field-sync flag. Then wait until bit 7 of
   `$FF03` is set. [Tandy, PDF 13][pia] [MC6821, PDF 10][mc6821]
3. Write `$FFCE` or `$FFCF` to show the new screen. This is the `published`
   label.
4. Wait for the next rising edge of field sync. Then draw the next frame into
   the other screen.

The flag in step 2 is set by the falling edge of field sync, at the end of the
active display. [MC6847, PDF 22][vdg] The program selects the falling edge
with bit 1 of `$FF03`, and it keeps the PIA interrupt output off.

The program can need more than one video frame to draw a frame. That does not
matter, because the display does not show the screen that the program draws.

## What the check proves

The `[capture]` table in [coco.toml](coco.toml) turns on the rendered check, so
`check` always uses the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
It runs 14 checkpoints on each target, from frame 1 to frame 370.

Each checkpoint is one hit of `published`. It compares:

- The frame counter, both positions, and the four guard bytes.
- All 6144 bytes of the screen that was just drawn, with `expected_screen` in
  [expected.py](expected.py).
- All 512x192 samples of the rendered frame with `expected_frame`.

The rendered frame is the second frame that XRoar completes after the
checkpoint. So the check proves that the display shows the new frame complete,
while the program draws the next frame.

An integration test in `scripts/coco_spec.py` is the negative control. It
changes `eora #$20` to `eora #0`, so that the program draws into the screen
that the display shows. The memory check still passes.

The rendered check fails at frame 1. The next background has erased the top
rows of the object before the captured frame.

The spec, [page_flip_spec.py](page_flip_spec.py), checks the model. It rejects
damaged guards, positions and screen bytes, and a picture that mixes two frames.

## Limits

The check sees one rendered frame for each checkpoint. It does not see every
video frame. A fault that shows only in a later video frame can pass.

In the pinned XRoar, the SAM loads the new display offset at the rising edge of
field sync. The sources that we read do not give that instant for the real SAM.
So step 2 waits for the falling edge, and step 4 waits for the rising edge.

Physical timing, PAL, T1 and CoCo 3 are not tested. Sound and keyboard input
are not part of this example.

## Target and memory

The targets are the same as [moving objects](../moving-objects/README.md):
`cocous`, NTSC, 32 KiB, a stock-clock 6809, and a non-T1 MC6847. The `coco1`
target uses BASIC 1.1 and Extended BASIC 1.0. The `coco2` target uses BASIC 1.2
and Extended BASIC 1.1.

| Purpose | Address range |
| --- | --- |
| Screen A (even frames) | `$0400-$1BFF` |
| Screen B (odd frames) | `$2400-$3BFF` |
| Guards | `$03FF`, `$1C00`, `$23FF`, `$3C00` |
| Code and state | `$4000` to `program_end - 1` |
| Stack | `$7E00-$7EFF`, top `$7F00` |

The two screens use 12,288 bytes, twice the size of one screen. The program
needs 32 KiB.

[sam]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=15>
[pia]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[mc6821]: <https://sowerbutts.com/replica1-serial/6821.pdf#page=10>
[vdg]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>
