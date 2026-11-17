---
name: retro-art
description: >
  Design and make artwork for a CoCo 1, 2 or 3 game: sprites, tiles,
  backgrounds, title pictures and concept art. Start from the owner's own
  drawing, sketch, photo or model whenever possible: convert it directly, or
  polish it with the OpenAI image API (scripts/art.py, as a sketch input), then
  reduce it to a CoCo mode with palette selection, mosaic or dithering
  (scripts/graphics.py). Use this skill whenever a project needs pictures,
  a sprite set, a consistent art style, a palette for the CoCo 3 GIME, or
  conversion of an image to screen bytes, even if the owner does not ask for
  art by name.
---

# Retro art for the CoCo

This skill takes a game from the owner's idea to screen bytes:

1. Ask the owner for their own art: a drawing, a sketch or anything they
   make. Read [the owner's art comes first](#the-owners-art-comes-first).
2. Choose the target: the mode, the grid and the colours.
3. Write one visual system contract for the game.
4. Write an image spec or a set spec for each group of pictures, with the
   owner's drawings as sketches.
5. Show the plan to the owner. Generate only after the owner agrees.
6. Reduce each picture to the CoCo mode. Show it to the owner beside their
   drawing, and refine it with them.
7. Show the result in XRoar.

Read [the art direction reference](references/art-direction.md) before you
write a contract. It tells how to ask for art that reduces well to a few
colours.

## The owner's art comes first

The game belongs to the owner, and so does its look. Their own hand in the
art is more important than a polished picture. A generator can draw a clean
frog. Only the owner can draw *their* frog. Thus ask for their art before you
write a spec, and treat a generator as a tool that polishes their design.

### Ask for it

Before the first spec, ask the owner for a picture of each thing that the game
shows. Say clearly that skill does not matter. A rough sketch is enough, and
a stick figure is a good start. Give examples of what they can send:

- a pencil or pen drawing on paper, photographed with a phone
- a drawing in any paint app, on a tablet or on a computer
- squares coloured in on graph paper, one square for each CoCo pixel
- a photo of a model of clay, building bricks or cut paper
- a picture of a thing from their own life that the art must look like
- a drawn layout of a screen: where the board, the score and the title go

Ask what each picture must keep: "the big eyes", "the curl in its tail".
Write those words in the spec, as the owner said them.

If the owner prefers not to draw, do not insist. Ask them to describe each
thing in their own words. Then offer to make a quick, low-cost draft that
they can draw over. Ask again at the next picture: an owner who saw one
result often wants to draw the next one.

### Choose the path

Use the path that keeps the most of the owner's work.

| The owner's picture | Path | Cost |
| --- | --- | --- |
| Drawn on the target grid: graph paper, or a paint app at the sprite size | Convert it directly with `graphics.py convert --resample nearest`. Do not generate. | None |
| A sketch, a drawing in any style, or a photo of a model | Polish it: give it to the generator as a sketch (`Items[].sketch` or `--sketch`). The generator keeps the design, the pose and the features. The contract gives the style and the colours. | One image for each picture |
| Words only | Write the owner's words in the spec. Make one draft with `--model flare`. Invite the owner to draw over it. | One draft, then as above |

A drawing on the grid is already game art. Polish it only if the owner asks.
To convert a drawing on graph paper, crop the photo to the grid
(`--box`). Then convert it at the grid size with `--resample nearest`.

### Keep the originals

Put each picture from the owner in `art/owner/` in the project. Name it for
its subject, for example `art/owner/frog-sketch.jpg`. Do not
change these files. A spec names them as sketches, so each generated record
names the owner's drawing as its source. In the project README, say which
pictures come from the owner's drawings.

### Refine it together

After each conversion, show the owner three pictures side by side: their
drawing, the polished picture and the CoCo picture. Ask what is right and
what is wrong. Ask them to point at things, not to name art terms.

- Write each change in the spec, in the owner's words. Then generate again.
- Invite the owner to draw on the result. Enlarge the CoCo preview with
  nearest-neighbour scaling (for example 8 times), so that each pixel is a
  square that they can colour. Their changed picture is the next sketch, or,
  on the grid, the next direct conversion.
- If the generator loses something that the owner drew, the result is wrong,
  even if it looks better. Say so, and try again with that feature named in
  the spec.

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
- The owner's drawing is the design. Ask for it first. Do not replace it with
  your own idea of the subject. Do not change the owner's files.
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

To polish the owner's drawing, give it as `sketch` on the item of a set, or
as `Sketch` in a spec for one picture. The path is relative to the spec. The tool sends it as a reference image. It tells the
generator that the drawing is the design. The generator keeps its shapes,
proportions, pose and features. It redraws them in the contract's style and
colours.

The generator does not copy pencil marks, paper or handwriting. A photo from
a phone is accepted.

To keep a style or a character the same, add approved pictures as
`ApprovedSamples` in the contract, or `reference` on an item. The tool sends
them as reference images. A `reference` is a finished picture: the generator
keeps its appearance and colours exactly, and takes the pose from the spec.

## 4. Generate

Plan first. This sends nothing:

```sh
uv run python scripts/art.py generate projects/<name>/art/creatures.spec.json --out projects/<name>/art/creatures
```

Show the owner the list of images, the model and the size. After the owner
agrees, run the same command with `--spend`. Use `--only SLUG` to make one
item. The tool skips images that exist. Use `--force` to make one again.

For one picture from one drawing, give the drawing with `--sketch`:

```sh
uv run python scripts/art.py generate projects/<name>/art/hero.spec.json --sketch projects/<name>/art/owner/hero-sketch.jpg --out projects/<name>/art/hero.png
```

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

Look at the preview PNG. It is drawn from the packed bytes. Then show it to
the owner beside their drawing, as
[refine it together](#refine-it-together) tells. If a shape is lost, change
the spec (larger shapes, fewer details) and generate again. Do not correct
the picture by hand yourself. The owner can draw on it.

## 6. Check in XRoar

Include the `.asm` output in the program. For the CoCo 3, write the
`-palette.asm` codes to `$FFB0-$FFBF`. Then run the project and check it, as
[development practice](../../../guidance/starter/development.md) tells. A
preview is not evidence that the program shows the picture.
