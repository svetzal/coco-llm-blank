# Art direction for CoCo colours

Read this before you write a contract or a spec. It tells how to ask an image
generator for pictures that keep their shape and colour when the converter
reduces them to a CoCo mode.

## What the reduction does to a picture

The converter makes the picture smaller, to the mode's grid. Then it gives
each target pixel one palette colour. Thus:

- A detail smaller than one target pixel disappears. A thin line can break.
- A gradient becomes bands of colour, or a dither pattern.
- A colour that is not in the palette becomes the nearest palette colour. A
  skin tone can become orange, and a soft grey can become white.
- A pixel that is not square changes the shape. The tool corrects for it, but
  the generator must leave room for the correction.

The prompt tells the generator the grid, the pixel shape and the minimum
feature size (3 target pixels). Do not remove these lines.

## Ask for art that reduces well

- **Flat colour.** Each area is one palette colour. Shade with a darker
  colour of the same family, as one hard-edged step.
- **The palette by name and hex.** The contract lists the colours. Give each
  one a use, such as "outlines" or "water". Then the generator puts the right
  colour in the right place.
- **Large, simple shapes.** Size the main shapes in target pixels, not in
  words. A 32×32 sprite has room for two eyes, a mouth and an outline, and
  little more.
- **A dark outline** when the palette has a dark colour to spare. It keeps
  the shape clear on any background.
- **Hard edges.** Anti-aliasing makes colours between two areas. The
  converter maps them to a third colour, and the edge becomes a ragged line.
- **A plain background**: one palette colour, or `transparent` for a sprite.
- **No text.** The program draws words and numbers.

Do not ask for a "pixel art" style. A generator draws false pixels that do
not line up with the grid. The reduction then makes them ragged. Ask for flat
cartoon art at a large size, and let the converter make the pixels.

## The CoCo 1 and 2

The colours are fixed by the colour set. The four-colour modes have green,
yellow, blue and red (CSS 0), or buff, cyan, magenta and orange (CSS 1). The
two-colour modes have black and green, or black and buff.

- Plan the picture in those colours. Do not ask for a colour the set does not
  have, such as brown or skin.
- In CG6, a pixel is almost twice as wide as it is tall. A shape needs about
  twice the height in target pixels to look round.
- The low-resolution modes suit very large shapes and mosaic reduction.

## The CoCo 3

A 16-colour GIME mode shows any 16 of 64 codes. The composite colours (a
television) are bright and saturated. They have few soft colours. For example, the
composite table has only one dark grey, and its browns are dark and red.

- Choose the 16 codes before you generate. Use `graphics.py palettes` to see
  the measured colours. Group them in families: for each family, one dark,
  one middle and one light colour.
- Keep black for outlines and white for highlights and eyes.
- Share the 16 registers between the background and the sprites. A sprite
  that uses its own colours needs registers that the background does not use
  (`--registers`).
- In the 4-colour GIME modes, choose the 4 codes for the scene, then ask for
  art in those 4 colours, as for the CoCo 1 and 2.

## Keep a set the same

- Put everything that all pictures share in the contract. Put only the
  subject and its differences in each item.
- Give every item of a set the same `Target.grid`, `Canvas.size` and
  `Composition`. Then the scale and the baseline are the same.
- After the first good picture, add it to `ApprovedSamples` with a note on
  what to match, for example "outline weight and face style". Generate the
  rest of the set with it.
- Generate one item with `--only` and convert it before you generate the
  whole set.

## When a picture fails

| Problem after reduction | Change |
| --- | --- |
| A detail is lost | Make it larger in the spec, or remove it. Use a larger grid. |
| Colours are wrong | Give the colour's use in the palette. Name the colour in the subject description. |
| Ragged edges | Ask for hard edges and a thicker outline. Use `--resample nearest` only for art drawn on the grid. |
| Banding in a sky or a shadow | Ask for flat areas, or use `--dither bayer`. |
| Noise on flat areas | Remove `--dither`. |
| A set does not match | Add an approved sample. Move shared text into the contract. |
| A sprite has a fringe | Ask again for hard edges with no glow. Raise `--alpha-threshold`. |
