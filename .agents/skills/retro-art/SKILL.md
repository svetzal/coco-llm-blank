---
name: retro-art
description: >
  Design and make artwork for a CoCo 1, 2 or 3 game: sprites, tiles,
  backgrounds, title pictures and concept art. Generate pictures with the
  OpenAI image API from structured JSON specs (scripts/art.py), then reduce
  them to a CoCo mode with palette selection, mosaic or dithering
  (scripts/graphics.py). Use this skill whenever a project needs pictures,
  a sprite set, a consistent art style, a palette for the CoCo 3 GIME, or
  conversion of an image to screen bytes, even if the owner does not ask for
  generated art by name.
---

# Retro art for the CoCo

This skill takes a game from an art idea to screen bytes:

1. Choose the target: the mode, the grid and the colours.
2. Write one visual system contract for the game.
3. Write an image spec or a set spec for each group of pictures.
4. Show the plan to the owner. Generate only after the owner agrees.
5. Reduce each picture to the CoCo mode, and look at the result.
6. Show the result in XRoar.

Read [the art direction reference](references/art-direction.md) before you
write a contract. It tells how to ask for art that reduces well to a few
colours.

## Rules

- **Ask before you spend.** Each generated image costs money on the owner's
  OpenAI account. Run `generate` without `--spend` first. It lists every
  image and sends nothing. Show the list to the owner. Run it again with
  `--spend` only after the owner agrees to that list. An agreement covers
  only the images that you showed.
- The API key comes from `OPENAI_API_KEY`. The owner supplies it. Do not ask
  for the key in a chat, and do not print it.
- Use the model that the owner selects. `--model sunburst` (the default)
  gives high quality. `--model flare` costs less and gives lower quality.
  Use `flare` for drafts when the owner agrees.
- Do not let the generator draw words, numbers or scores. The program draws
  them from data.
- Keep the contract, the specs, the generated PNGs and their JSON records in
  the project, for example in `projects/<name>/art/`. Keep the conversion
  commands in the project too, so that a build makes the same bytes again.
- A generated picture is a source, not a result. The reduced picture and the
  XRoar check are the result.
- Do not copy an existing game's characters, art or look. Describe original
  subjects.

## 1. Choose the target

Get the mode, its grid and its pixel shape from the converter:

```sh
uv run python scripts/graphics.py modes
uv run python scripts/graphics.py palettes
```

Read the guide for the machine before you choose:
[VDG graphics](../../../guidance/techniques/graphics.md) for the CoCo 1 and 2,
[GIME graphics](../../../guidance/techniques/gime-graphics.md) for the CoCo 3.

- **CoCo 1 and 2.** The colours are fixed. A four-colour mode has green,
  yellow, blue and red, or buff, cyan, magenta and orange. Put exactly those
  colours in the contract.
- **CoCo 3.** The 16 palette registers hold any 16 of 64 colour codes. Choose
  the 16 codes first, as the art direction. Put their measured colours in the
  contract. Then convert with the same codes, in the same order
  (`--codes`). The picture then uses the colours that the generator was told
  to use.
- Choose `gime-composite` colours for a television or the starter's checks.
  Choose `gime-rgb` colours for an RGB monitor. The same code shows a
  different colour on each.

## 2. Write the contract

Copy a template from [templates/](templates/) into the project:

- `coco3-gime16.contract.json`: CoCo 3, 320×192, 16 colours, with a general
  set of 16 composite codes.
- `coco12-cg6.contract.json`: CoCo 1 or 2, CG6, four colours.

Change it for the game:

- `Palette.colours`: the colours, each with a name, the hex value and a use.
  Put the CoCo code in the name, for example `green $12`.
- `Target`: the machine, the mode, the grid of the picture in target pixels,
  the pixel aspect from `graphics.py modes` (`ntsc` column) and the
  background.
- `VisualLanguage`, `LineAndShape`, `CompositionPolicy` and the rules.

The contract holds what all pictures of the game share. An image spec
overrides it with its own values.

## 3. Write the image specs

Copy `templates/sprite.spec.json` for one picture or `templates/set.spec.json`
for a set. A set makes one image for each item, with the same style. Use a
set for a group that must match, such as all the creatures of a game.

- `Role`: screen, background, sprite, sprite-sheet, tile, tile-set, title,
  icon or concept. It selects the contract's composition rule.
- `Target.grid`: the size of this picture in target pixels.
- `Target.background`: a palette colour, or `transparent` for a sprite. A
  transparent picture comes back with an alpha channel. The converter makes
  the sprite mask from it.
- `Subject` or `Items`: what to draw. Describe shapes and colours, not
  feelings.
- `Context`: why the picture exists. The generator does not draw it.
- A key that ends in `+`, such as `must+`, adds to the contract's list.

Read the exact prompt. It costs nothing:

```sh
uv run python scripts/art.py prompt projects/<name>/art/creatures.spec.json
```

To keep a style or a character the same, add approved pictures as
`ApprovedSamples` in the contract, or `reference` on an item. The tool sends
them as reference images.

## 4. Generate

Plan first. This sends nothing:

```sh
uv run python scripts/art.py generate projects/<name>/art/creatures.spec.json --out projects/<name>/art/creatures
```

Show the owner the list of images, the model and the size. After the owner
agrees, run the same command with `--spend`. Use `--only SLUG` to make one
item. The tool skips images that exist. Use `--force` to make one again.

Each image has a JSON record beside it, and a line in `manifest.jsonl`. They
hold the exact prompt, the model and the resolved spec.

## 5. Reduce to the CoCo mode

Run `uv run python scripts/graphics.py convert --help`. Then choose a
reduction:

| Reduction | Option | Use it for |
| --- | --- | --- |
| Nearest colour | (none) | Flat art that uses the palette colours. The default. |
| Mosaic | `--mosaic WxH` | Large blocks of one colour, for a chunky look or a low-detail mode. |
| Ordered dither | `--dither bayer` | Smooth shading with a regular pattern. Steady when the picture moves. |
| Error diffusion | `--dither floyd-steinberg` | Photographic or painted shading. The pattern can shimmer when the picture moves. |

Do not dither flat art. It adds noise to areas that are near, but not equal
to, a palette colour.

For the CoCo 3, give the palette:

- `--codes 00,10,20,...`: the contract's codes, in register order. Use this
  when the art was drawn with the contract's colours.
- `--lock 0=00`: keep a register at a code, and let the converter choose the
  others.
- `--registers 8-15`: let a picture use only some registers, so that sprites
  and the background can share the 16.
- `graphics.py palette A.png B.png ...`: choose one shared palette for
  several pictures. Use its `-palette.json` with `--palette-file` for each
  conversion.

Examples:

```sh
uv run python scripts/graphics.py convert art/frog.png --mode gime-320x16 --size 32x32 --codes 00,10,20,30,05,15,25,24,0E,12,21,0B,1C,2D,07,16 --mask --out build/frog
uv run python scripts/graphics.py convert art/title.png --mode cg6 --auto-css --dither bayer --out build/title
```

Look at the preview PNG. It is drawn from the packed bytes. If a shape is
lost, change the spec (larger shapes, fewer details) and generate again. Do
not correct the generated picture by hand unless the owner asks.

## 6. Check in XRoar

Include the `.asm` output in the program. For the CoCo 3, write the
`-palette.asm` codes to `$FFB0-$FFBF`. Then run the project and check it, as
[development practice](../../../guidance/starter/development.md) tells. A
preview is not evidence that the program shows the picture.
