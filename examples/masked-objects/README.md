# Draw an object with transparent pixels

This example draws an object over scenery with a software mask. Each screen
byte under the object becomes `(screen AND mask) OR ink`. A mask bit of 1
keeps the scenery pixel. A mask bit of 0 replaces that pixel with the ink bit.

Thus an object can have transparent pixels and opaque black pixels.

The example does not erase or restore the scenery. It does not clip, place
objects at a pixel position inside a byte, detect collisions or time the
frames.

The context redraws the full background before each scene. The
[moving-objects guide](../../guidance/techniques/moving-objects.md) compares
the methods that restore scenery.

## Choose a draw method

The mask method is the default. Use it when an object has holes or an
irregular outline, and when it must show black over lit scenery.

| Method | Variant | Byte becomes | Clear | Black | Order | Data | Steps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Mask | (none) | `(screen AND mask) OR ink` | Yes | Yes | Yes | 2 | 6 |
| Opaque | `opaque` | `ink` | No | Yes | Yes | 1 | 3 |
| XOR | `xor` | `screen XOR ink` | Black ink | No | No | 1 | 5 |

- Clear: the object can have transparent pixels.
- Black: the object can show opaque black over lit scenery.
- Order: the last object drawn hides the objects below it.
- Data: the bytes of shape data for each screen byte.
- Steps: the instructions for each row of two bytes in this example.

- Opaque is the fastest method. It replaces the full box, so use it for a
  solid rectangle.

  The
  [moving-objects example](../moving-objects/README.md) draws this way.
- XOR inverts the scenery under each lit ink bit. A second XOR draw at the
  same position removes the object. Black ink has no effect, so an XOR object
  cannot show black.

- The step counts include one step in each XOR and opaque row. This step skips
  the unused mask word.

The example uses RG6, one bit for each pixel. In a four-colour (CG) mode, each
pixel has two bits, so each pixel's mask has two bits. That is our derivation.
This example does not check it.

Other ways that this example does not show:

- Keep shifted copies of the shape and mask to place an object at any pixel.
- Make the mask from a key colour in the shape when the program draws.
- Write the shape as code, with one store instruction for each byte.

## Draw the object

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm):

1. At `place`, find the screen byte of the top-left corner:
   `$0400 + 32 × row + column`. RG6 has 32 bytes in each row.

   The column is a byte column, 0 to 30. The row is a pixel row, 0 to 182. The
   full 16×10 object must be on the screen.

2. At `draw_row`, change two screen bytes with the selected method. Then add
   32 to step to the next row. Do this for each of the 10 rows.

3. At `shape_a` and `shape_b`, keep the shape data. Each row has a 16-bit mask
   and a 16-bit ink word, in that order. Bit 15 is the leftmost pixel.

   Ink must be 0 under each mask bit of 1. Otherwise the ink sets that scenery
   pixel.

The `--- CONTEXT` blocks are not part of the practice:

- They set up RG6 at `$0400` with colour set 0, as in
  [first-screen](../first-screen/README.md).
- They redraw an 8×8 checker background for each scene.
- They draw two hollow objects in the order that the scene table gives.

Object A has a green top and left edge and a black bottom and right edge.
Object B has the opposite colours. The top row, the bottom row and the centre
of each object are transparent.

The program keeps the interrupts, stack, direct page and CPU clock that BASIC
sets. The `state` label is data. The check fails if the CPU runs it.

## See and check each method

Open a terminal in the starter folder. Copy one line and paste it to see that
method in XRoar. The 12 scenes repeat until you close the window.

```sh
uv run python scripts/coco.py run examples/masked-objects                   # mask
uv run python scripts/coco.py run examples/masked-objects --variant opaque  # opaque
uv run python scripts/coco.py run examples/masked-objects --variant xor     # xor
```

To check all three methods, paste this line:

```sh
uv run python scripts/coco.py check examples/masked-objects --video
```

The `--video` option needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check takes a snapshot after each of the 12 scenes. It compares all 6,144
screen bytes and XRoar's rendered picture with [expected.py](expected.py). The
model in `expected.py` draws each object pixel by pixel from the ring shape and
the rule for each method.

The model does not read the mask data in `main.asm`.

The scenes include these cases:

- Objects in all four corners.
- Partial overlap and full overlap, in both draw orders.
- Objects that are apart.
- Scenes with no objects, after scenes with objects.
- Objects over the inverted background.

The check uses the CoCo 1 target in [coco.toml](coco.toml): NTSC, 32 KiB,
normal clock, the non-T1 MC6847 and Color BASIC 1.1. It does not prove the
result on a television, a physical CoCo, PAL, the MC6847T1 or the CoCo 3.

The program draws into the screen that the VDG shows, with no vertical sync.
A real game can show tearing or a half-drawn object. Read
[show only finished frames](../../guidance/techniques/animation.md#show-only-finished-frames).

## Sources

Read these pages before you change the screen setup or the bit order. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Inman, Inman and Dymax, *Assembly Language Graphics for the TRS-80 Color
  Computer*, PDF 106–107: mode 6R is 256×192, has eight pixels in each byte
  and uses 6 KiB. With colour set 0, a 0 bit shows black and a 1 bit shows
  green.

- Motorola, *MC6847 Video Display Generator* datasheet, PDF 19, Table 3: in
  RG6, bit 7 is the leftmost pixel of a byte.

- Tandy, *Color Computer Technical Reference Manual*, PDF 14–15: the `$FF22`
  bits, and the SAM offset and mode bits. PDF 31: RG6 uses SAM V=`110` and
  `$FF22` bits 7 to 4 `1111`.

The mask format, the shapes and the scenes are our own design. We found no
examined listing of a CoCo masked renderer to compare with.
