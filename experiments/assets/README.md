# Prepare original RG6 room assets on the host

This small example prepares four original opaque 8×8 pictures for the layout
in [tile-room](../../examples/tile-room/README.md). It does not change or feed
that example's assembly. Its JSON bundle is a host inspection format, not a
CoCo executable, HGET buffer, disk file format or target loader.

## Run from a fresh clone

Python and development dependencies come from the repository lockfile. No ROMs,
reference downloads, assembler or emulator are needed for these host checks.
From the repository root:

```sh
uv sync --locked
mkdir -p build/assets
uv run --no-sync python experiments/assets/prepare.py build \
  --output build/assets/room.json
uv run --no-sync python experiments/assets/prepare.py check \
  --output build/assets/room.json
COVERAGE_FILE=build/assets/.coverage uv run --no-sync pytest \
  experiments/assets/prepare_spec.py --cov=prepare \
  --cov-config=experiments/assets/coverage.ini --cov-report=term-missing
uv run --no-sync ruff check experiments/assets
uv run --no-sync ruff format --check experiments/assets
markdownlint experiments/assets/README.md guidance/asset-validation.md
```

`uv sync` is for setup. The `--no-sync` checks avoid changing a shared environment
while other workers use it. `markdownlint` is the repository's separately
installed host CLI; it is not a Python dependency.

All essential code, source pixels and tests are under this directory. Generated
bundles and coverage belong in ignored `build/assets/`. The default source is
`art.json` beside the script, independent of the current directory. Use
`--source PATH` to test edits. The CLI requires an explicit output path.

## Fixed contract

`art.json` contains integer palette indices in top-to-bottom rows, with each row
ordered left to right. Every picture declares width 8, height 8, byte stride 1,
`msb-first-1bpp` packing, `rg6-css0-black-green` palette identity and top-left
anchor `[0, 0]`. Index 0 means black; index 1 means green. These are logical
indices, not calibrated RGB values or artifact-colour predictions.

Each picture occupies eight bytes. A row `10000000` becomes hex `80`, and
`00000001` becomes `01`. There is no padding, transparency, mask or compression.
The pictures are intentionally asymmetric, including their corner marks.
The floor has a single offset dot; the wall is an open, notched frame; the
collectible has an offset sparkle; the exit has a right-pointing stroke.

Terrain IDs remain floor 0, wall 1, collectible 2 and exit 3. They select asset
IDs 10, 40, 70 and 90 through an explicit four-entry translation table. Asset
list order is not identity. Duplicate IDs, missing referenced IDs and unknown
terrain IDs fail validation. Solid/passable rules and actor state are absent.
The four pictures are new art; their shapes are not collision data.

The room repeats the existing example's eight columns and six rows:

```text
..#.....
.*#..#..
..#.....
....##..
.#......
......E.
```

The host framebuffer is 256×192 pixels, 32 bytes per row, 6,144 bytes total.
The room starts at pixel `(0, 0)` and fills 64×48 pixels. Cell `(c, r)` starts
at byte offset `r * 256 + c`; each following picture row advances 32 bytes.
The rest of the buffer is zero. No actor is drawn. A nonzero source anchor
is rejected; the format does not offer general sprite positioning.

The bundle carries each picture's descriptor and packed hex, the room and
mapping, screen dimensions/stride/origin, the complete framebuffer as hex,
and SHA-256 of the exact input file bytes. Keys and assets are sorted, and
there are no timestamps or random inputs. Identical source bytes give identical
bundle bytes. Reformatting JSON changes its source digest deliberately.

## Publication and stale results

`build` rejects a source/output path collision before changing either file.
Otherwise it removes any old output first, reads and validates the entire
source, writes a temporary file in the output directory, flushes it, and
renames the completed bundle into place. Validation or input-read failure
leaves no published output. This deliberately sacrifices the old result so
it cannot masquerade as a successful new build. Use a dedicated output path.

`check` recomputes the bundle and compares every byte. It rejects missing,
truncated, changed or stale output and exits nonzero. It does not repair or
remove output. Build again after a source change, then check again.
A consumer must require successful `check` before using an existing bundle.
There is no independent success marker that can outlive the data.

This is a single-writer workflow. Concurrent writers, power-loss durability,
filesystem fault injection and hostile filesystem links are not validated.
A killed process can leave a hidden temporary file; that is never the published
bundle. There is no multi-file publication transaction or target consumer.

See [validation and provenance](../../guidance/asset-validation.md) for the
independent expectations, executed evidence and exact limits.
