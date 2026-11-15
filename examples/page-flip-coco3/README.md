# Show only finished frames on CoCo 3

This example uses two buffers in the native graphics of the CoCo 3 GIME to
show only finished frames. This is a page flip.

The program draws each scene into the buffer that the display does not show.
When the scene is complete, one write to `$FF9D` shows that buffer. Then the
program draws the next scene into the other buffer.

The example does not use an interrupt handler. It does not read input, play
sound or keep a constant frame rate. It does not use the CoCo 1/2 modes of the
CoCo 3. The program does not return to BASIC.

For the CoCo 1 and CoCo 2, read
[page flip on CoCo 1 and CoCo 2](../page-flip/README.md).

## Choose the two buffers

The GIME shows the buffer at the physical address `$FF9D` x 2048 + `$FF9E` x 8.
[Tandy CoCo 3, PDF 13][coco3-13] Give the two buffers the same `$FF9E`. Then
one write to `$FF9D` shows the other buffer.

| Buffer | Physical address | MMU page | CPU address | `$FF9D` | `$FF9E` |
| --- | --- | --- | --- | --- | --- |
| A | `$04000-$057FF` | 2 | `$4000-$57FF` | `$08` | `$00` |
| B | `$06000-$077FF` | 3 | `$6000-$77FF` | `$0C` | `$00` |

- The display reads physical memory, not CPU addresses. Each MMU page is 8 KiB.
  [Tandy CoCo 3, PDF 15-16][coco3-15]
- A 256x192 two-colour buffer uses 6144 bytes. A buffer with more colours or
  more pixels needs more memory. [Tandy CoCo 3, PDF 18][coco3-18]
- A 128 KiB CoCo 3 has the same RAM in each group of 128 KiB.
  [Tepolt, PDF 29][tepolt-29] So pages 2 and 3 exist at 128 and 512 KiB.

| Machine | Write to show a buffer | Wait for | Example |
| --- | --- | --- | --- |
| CoCo 3, native modes | `$FF9D` (and `$FF9E`) | VBORD flag, `$FF92` bit 3 | This one |
| CoCo 1, CoCo 2 | One SAM offset bit | FS flag, `$FF03` bit 7 | [Page flip](../page-flip/README.md) |

Other ways that this example does not show:

- An IRQ handler for VBORD. The handler reads `$FF92` and does the flip.
- Two buffers that differ in `$FF9E` too. Then the program writes two
  registers. The sources that we read do not say if the GIME uses both writes
  in the same field.
- Three buffers. The program can start the next scene before the display uses
  the new buffer.

## Flip the buffers

The example is the four `>>> EXAMPLE` parts of [main.asm](main.asm):

1. `BUFFER_A` and `BUFFER_B`: the CPU addresses of the two buffers.
2. At `start`, map the buffers and turn on the VBORD flag:
   1. Write 2 to `$FFA2` and 3 to `$FFA3`. In task set 0, these write-only
      MMU registers map CPU `$4000-$7FFF`. [Tandy CoCo 3, PDF 15-16][coco3-15]
   2. Mask IRQ in the CPU.
   3. Write `$6E` to `$FF90`: native video, MMU on, GIME IRQ output on.
      [Tandy CoCo 3, PDF 11][coco3-11]
   4. Write `$08` to `$FF92`. VBORD is then the only GIME IRQ source.
3. After `render`, show the finished buffer and change buffers:
   1. Wait for a new VBORD.
   2. Write `$08` or `$0C` to `$FF9D`. The `published` label follows this
      write.
   3. Wait for one more VBORD. Then change `back` to the other buffer.
4. `waitvb`: read `$FF92` to clear an old request. Then wait until bit 3 of
   `$FF92` is set. [Tepolt, PDF 50][tepolt-50]

The `$FF92` flag sets only when `$FF90` bit 5 sends the GIME IRQ to the CPU.
[Tepolt, PDF 50][tepolt-50] The program masks IRQ, so no interrupt handler
reads `$FF92` and takes the flag.

The sources that we read do not give the instant at which the GIME uses a new
`$FF9D`. So step 3.3 waits one more VBORD before the program draws into the
old buffer.

The `--- CONTEXT` blocks are not part of the practice:

- They set up 256x192 with one bit for each pixel, a black border, black for
  0 and white for 1. [Tandy CoCo 3, PDF 12, 17 and 18][coco3-12]
- They clear the buffer and draw a one-pixel white outline.
- They draw an 8x8 white square at row 80. The square starts at pixel 32 and
  moves 16 pixels right in each scene. After five scenes it starts again.

The program keeps the stack, the direct page and the CPU clock that BASIC sets.
BASIC uses task set 0. The `state` label is data. The check fails if the CPU
runs it.

## See and check the page flip

Open a terminal in the starter folder. Paste this line to see the page flip in
XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/page-flip-coco3    # 128 KiB CoCo 3
```

To check the page flip at 128 and 512 KiB, paste this line:

```sh
uv run python scripts/coco.py check examples/page-flip-coco3
```

The `[capture]` table in [coco.toml](coco.toml) turns on the rendered check,
so `check` needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check takes a snapshot at `published` after scenes 0 to 4 and the next
scene 0. It compares these items with [expected.py](expected.py):

- The buffer that the display shows holds the new scene, all 6144 bytes.
- The other buffer still holds the scene before it.
- XRoar's rendered picture is the new scene, complete.

The model in `expected.py` draws each scene pixel by pixel from the scene
description above. It does not read the assembly. Its black and white RGB
values come from a capture of the pinned XRoar, not from a source or a monitor.

A negative control in `scripts/coco_spec.py` adds 1 to the value for `$FF9D`.
The GIME then shows memory 2 KiB after the buffer. The memory check still
passes. The rendered check fails.

The check uses an NTSC CoCo 3 with the GIME 1986 and the 6809. It sees one
rendered frame for each checkpoint, not every field. It does not prove the
result on a monitor, a physical CoCo 3, PAL, the GIME 1987 or the 6309.

## Sources

Read these pages before you change the buffers or the wait. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Tandy, *Color Computer 3 Service Manual*, PDF 11: the `$FF90` bits and the
  `$FF92` bits. Bit 3 of `$FF92` is VBORD. [Link][coco3-11]

- The same manual, PDF 12 and 13: `$FF98`, `$FF99`, `$FF9A` and `$FF9C`.
  `$FF9D` holds address bits Y18 to Y11, and `$FF9E` holds Y10 to Y3.
  [Link][coco3-12]

- The same manual, PDF 15 and 16: the MMU registers `$FFA0` to `$FFAF`. They
  are write only. [Link][coco3-15]

- The same manual, PDF 17 and 18: the palette bits and the table of
  resolutions. [Link][coco3-18]

- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 29: a 128 KiB CoCo 3 has the same RAM in each group of pages.
  [Link][tepolt-29]

- The same book, PDF 50: the `$FF92` flag needs `$FF90` bit 5. A read of
  `$FF92` clears the request. [Link][tepolt-50]

[coco3-11]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=11>
[coco3-12]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=12>
[coco3-13]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=13>
[coco3-15]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=15>
[coco3-18]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=18>

[tepolt-29]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=29>
[tepolt-50]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=50>
