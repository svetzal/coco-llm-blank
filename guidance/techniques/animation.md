# Plan animation storage

Read this when planning moving objects, a short animation cycle, or a title screen.
The published examples use PMODE and Extended Color BASIC.
Their ideas inform assembly design, but their array formats and delays do not
become assembly contracts.

The [continuous-renderer experiment](validation/animation-cadence.md)
checks 150 consecutive frames from the original CoCo 1 moving-object example.
It finds two partial-erasure frames and many object-free backgrounds despite
correct completed-frame RAM. A correct redraw checkpoint does not establish
clean animation. Measure consecutive output before choosing a redraw strategy;
these results do not measure host smoothness or physical tearing.

The [frame-publication source research](research/frame-publication.md)
is published. It distinguishes preparing a hidden image, publishing its base,
and waiting for adoption before reusing the old buffer. Its SAM/PIA and native
GIME findings retain unresolved latch and timing contracts; source reading
alone does not prove tear-free output.

Original hidden-buffer implementations are published on `main` for
[CoCo 1/2](../../experiments/clean-animation/README.md) and
[native CoCo 3](../../experiments/clean-animation-coco3/README.md). The
[CoCo 1/2 validation](validation/clean-animation.md) passes
38 tests with 97.01% scoped coverage and a 150-frame acceptance window on each
target. Cross-sequence chronology checks reject premature buffer reuse.
The [CoCo 3 validation](validation/clean-animation-coco3.md)
passes 28 tests with 93.51% coverage and all 42 complete frames with ordered
scenes 0–4 on both RAM capacities. These bounded emulator results establish
neither host smoothness nor physical safe-switch timing.

## Store the picture, not an oversized container

Steven R. Polsz compares oversized BASIC arrays with compact storage for an
example object in **"Optimum Animation," The Rainbow, October 1986**.
The examined text and diagram occupy printed 116–117, PDF 118–119.
The useful lesson is to distinguish packed pixels from their language container.
His example's saving is not a universal compression ratio. [Polsz][polsz]

Our adaptation for an assembly project is to define an explicit asset format
before writing a drawing routine. Specify pixel width, height, bits per pixel,
row padding, and any mask or header. Do not borrow a BASIC GET/PUT allocation
formula for that format.

For an original format that pads each row to a whole byte, the calculation is:

```text
row_bytes = ceil(width * bits_per_pixel / 8)
picture_bytes = row_bytes * height
```

This is our arithmetic, not Polsz's BASIC storage rule. A 13×8 one-bit picture
uses 16 bytes in this format. A same-sized one-bit mask would need another
16 bytes. Neither number includes headers, saved backgrounds, or shifted copies.
A mask is a possible design extension. The examined article does not establish
a tested masked renderer.

Before implementing the format:

1. Check the target mode's pixel packing in its hardware reference.
2. Draw a tiny asymmetric asset whose byte representation you can check by hand.
3. Calculate storage for every frame, mask, and working buffer.
4. Reserve code, stack, and game state separately.

## Prepare frames when the sequence is small

Becky F. Matthews explains two prepared pictures and alternating displays in
**"Electrifying Graphics Using PMODE Power," The Rainbow, October 1987**.
We examined printed/PDF 44 and 46–47, including the complete listing.
The article labels its example 16K ECB. [Matthews][matthews]

The three examples prepare two PMODE 1 pictures, then alternate their display.
The hydroelectric example copies its shared mountains and sky before adding
the different moving parts. The final page completes that example and the
solar sequence. [Matthews, PDF 46–47][matthews-ending]

The distinction between the picture being drawn and the picture being shown
is useful for short cycles and transitions. The examined example does not
establish a general game renderer, tear-free switching, or collision handling.

Our design advice is to budget complete pictures before choosing this approach.
For example, two 256×192 one-bit buffers require 12,288 bytes of pixel storage.
That derived figure excludes alignment, program code, stack, and assets.
It does not imply that a whole program fits in 16 KiB.
The starter's [first-screen example](../../examples/first-screen/README.md)
provides a sourced CoCo 1 mode setup and a single-buffer memory check.

## Precompute geometry when pictures cost too much memory

Joseph Pendell's **"Zippy Animation in BASIC?"**, *The Rainbow*, October 1992,
printed/PDF 3, calculates rotated endpoints before drawing the animation.
The playback loop uses those stored coordinates. This is a useful alternative
to storing every complete picture. [Pendell][pendell]

Our proposed assembly adaptation is to generate a coordinate table during asset
preparation. Keep the asset generator's precision and the target's integer
rounding explicit. The article uses BASIC arrays; it does not establish a
packed assembly format or a cycle budget.

For our own format with two one-byte coordinates per point, storage would be
`2 * point_count * frame_count` bytes. This excludes connectivity, headers,
and any erase data. Wider or signed coordinates change that calculation.
Line drawing still happens during playback, so precomputation does not remove
all frame work.

Before adopting the approach, check every point against the intended bounds.
Check the last-to-first transition and the erase policy. Pendell's drawing
choices are not proof of clean background restoration in a game.
Read [moving objects](moving-objects.md) before combining the effect with scenery.

The page labels the listing CoCo 3 and discusses CoCo 1/2 speed changes.
We have not run it on any model. Its speed suggestions do not establish
normal-clock performance and are not part of our recommended setup.

## Let an accumulating picture retain its history

Richard Ramella's "Summer Frippery", *Undercolor*, volume 1, issue 11,
June 30, 1985, printed 16, PDF 18, includes *Flower Fantasy*. It adds circle
segments without clearing between passes and rejects a colour matching the
existing centre pixel. The page specifies 16K Extended Color BASIC and makes
its speed POKE conditional. This is no CoCo 3 compatibility or normal-clock
performance evidence. [Ramella][ramella]

For an accumulating garden, trail or paint demo, our untested adaptation keeps
past marks in the framebuffer instead of a growing shape list:

```text
add_mark():
    centre = choose_valid_centre()
    choices = allowed_colours minus read_logical_colour(centre)
    if choices is empty: return
    draw_clipped_mark(centre, choose(choices))
```

Choosing from the remaining colours replaces the source's retry loop with a
bounded selection step. Clipping and the empty-set exit are our additions.
Use the target renderer's logical colours, not the listing's colour offset or
POKEs. This saves shape-history storage but loses independent reconstruction
and undo unless more state is retained. Later choices depend on earlier pixels;
a centre-pixel check does not detect overlap across the whole mark.

Before adopting it, check empty choices, edge clipping, repeatability from a
fixed seed, and a reset of both the drawing and random-generator state. No such
checks were run here. The [Undercolor research record](research/undercolor-game.md)
records source images, hashes and limits; this source has no manifest resource ID.

## Check the result before expanding it

For a new adaptation, use these checks. The published experiments above supply
bounded evidence for their own configurations, not acceptance for a new workload:

- Compare each prepared picture with an independent expected bitmap.
- Check memory guards around every picture and asset.
- Exercise odd widths and the last row or column of the chosen format.
- Inspect screen changes in XRoar for tearing and unintended intermediate pictures.
- Measure drawing and switching time under the intended game load.

Begin reproduction on the article's documented configuration.
Check CoCo 1 and CoCo 2 separately before claiming both.
CoCo 3 compatibility mode needs a separate run. Native CoCo 3 graphics need
another storage and display contract.

## Sources and provenance

- Polsz, Steven R. "Optimum Animation." *The Rainbow*, October 1986,
  printed 116–117, PDF 118–119. Resource `rainbow-1986-10`. [Archive][polsz]
- Matthews, Becky F. "Electrifying Graphics Using PMODE Power." *The Rainbow*,
  October 1987, printed/PDF 44, 46–47. Explanation and complete listing examined.
  Resource `rainbow-1987-10`. [Archive][matthews]

- Pendell, Joseph. "Zippy Animation in BASIC?" *The Rainbow*, October 1992,
  printed/PDF 3. Resource `rainbow-1992-10`. Explanation and listing examined.
  [Archive][pendell]

The format calculations and proposed checks are original guidance.
None of these article listings has been reproduced here. See the
[research notes](research/README.md#coco-1-and-coco-2-animation)
for selection limits.

[polsz]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2006%20No.%2003%20-%20October%201986.pdf#page=118>

[matthews]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf#page=44>

[pendell]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf#page=3>

[matthews-ending]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf#page=47>

[ramella]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n11%20%281985%29%28ColorPlus%20Inc%29.pdf#page=18>
