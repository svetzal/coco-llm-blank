# Changelog

This file lists the changes to the starter in each release. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version
is in `pyproject.toml`. Each SYSTEM session adds its changes here before it
ends. [The system guide](guidance/starter/system.md) gives the procedure.

## [Unreleased]

## [0.3.0] - 2026-11-16

### Added

- The `retro-art` skill in `.agents/skills/retro-art/`. It takes a game from
  an art idea to screen bytes. Its steps are a visual system contract for the
  game, image and set specs, generation, reduction and the XRoar check. It has
  templates for a CoCo 3 16-colour game and a CoCo 1/2 CG6 game.
- `scripts/art.py`: generates concept art with the OpenAI image API from
  structured JSON specs. A contract holds what a game's pictures share. A set
  spec makes a group of pictures in one style. `prompt` shows the exact
  prompt for free. `generate` sends nothing without `--spend`, and an agent
  must get the owner's agreement first. `--model sunburst` (the default) or
  `--model flare` selects the quality. A transparent background uses
  OpenAI's own transparency. Each image has a JSON record and a manifest
  line. The owner supplies `OPENAI_API_KEY`.
- `scripts/graphics.py` converts to the twenty CoCo 3 GIME graphics modes,
  with 192, 200 or 225 rows.
- Two measured 64-code CoCo 3 palettes: `gime-composite` (a television, the
  default) and `gime-rgb` (an RGB monitor).
- Palette selection for the CoCo 3: the converter chooses the codes for the
  palette registers, or uses the codes you give (`--codes`, `--lock`,
  `--registers`). The new `palette` command chooses one palette for several
  pictures. A GIME conversion writes `-palette.asm` and `-palette.json`.
- Mosaic reduction, `--mosaic WxH`, for the VDG and GIME modes.
- A target key, `tv_input`. `tv_input = "rgb"` captures XRoar's RGB monitor
  picture.

### Changed

- The `openai` package is a dependency. Run `uv sync --locked`.
- The shared pixel code of `graphics.py` is in `scripts/raster.py`.

## [0.2.0] - 2026-11-16

This is the first release. The git history has the changes before it.

### Added

- SYSTEM mode, for changes to the starter itself. It starts only when the
  owner asks for it by name. Read `guidance/starter/system.md`.
- `coco.py record`: an HEVC video with sound of a build from power-on, made
  from every frame that XRoar draws. Patch 0005 of the XRoar series sends the
  frames to ffmpeg.
- 6309 targets: a target with `cpu = "6309"` assembles with LWASM `--6309`,
  defines `H6309` and names its files `*-6309`. A test runs a 6309 program
  on a CoCo 3, with a 6809 control.
- Two 6309 references: the *HD63B09EP Technical Reference Guide* and *The
  6309 Book*.
- `scripts/release.py`: makes sure that the version in `pyproject.toml`,
  `uv.lock` and this file is the same, and prints the notes of a release.

### Changed

- XRoar is pinned to 1.13.1. The five patches apply without change, and the
  comparison checks are byte-identical. `first-screen` now checks RG1, RG2
  and RG3 on the CoCo 3, because XRoar 1.13.1 shows these modes with normal
  pixels.
- One XRoar runs every command on every host: the pinned release with the
  patch series, with its window and sound modules. Bootstrap builds it.
  Evidence runs connect no joystick, so a gamepad cannot change a check.
- The environment variable `XROAR` names a substitute for the one XRoar.
- A lab answers CoCo programming questions only. Changes to tools and
  equipment are SYSTEM work.
- The XRoar version trial works in `local/system/xroar-<version>/`.
- The starter's name is `retro-explorer-coco`.

### Removed

- Homebrew's XRoar and the separate Ubuntu XRoar build. Nothing uses them.
- `XROAR_INSTRUMENTED`. Use `XROAR`.
- The check of the repository size.
