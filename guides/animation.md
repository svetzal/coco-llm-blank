# Plan animation storage

Read this when planning moving objects, a short animation cycle, or a title screen.
The published examples use PMODE and Extended Color BASIC.
Their ideas inform assembly design, but their array formats and delays do not
become assembly contracts. No new renderer has been tested for this guide.

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
We examined printed/PDF 44 and 46. The listing continues on page 47, which
has not been examined. The article labels its example 16K ECB. [Matthews][matthews]

The distinction between the picture being drawn and the picture being shown
is useful for short cycles and transitions. The examined example does not
establish a general game renderer, tear-free switching, or collision handling.

Our design advice is to budget complete pictures before choosing this approach.
For example, two 256×192 one-bit buffers require 12,288 bytes of pixel storage.
That derived figure excludes alignment, program code, stack, and assets.
It does not imply that a whole program fits in 16 KiB.
The starter's [first-screen example](../examples/first-screen/README.md)
provides a sourced CoCo 1 mode setup and a single-buffer memory check.

## Check the result before expanding it

The following checks are proposed work, not completed animation evidence:

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
  October 1987, printed/PDF 44, 46–47. Examined 44 and 46 only.
  Resource `rainbow-1987-10`. [Archive][matthews]

The format calculations and proposed checks are original guidance.
Neither article's listing has been reproduced here. See the
[research notes](../guidance/game-research.md#coco-1-and-coco-2-animation)
for selection limits.

[polsz]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2006%20No.%2003%20-%20October%201986.pdf#page=118>

[matthews]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf#page=44>
