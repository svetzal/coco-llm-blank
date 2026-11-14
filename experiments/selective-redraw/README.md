# Bounded retained-description redraw

This is original 6809 experiment code adapted from the procedure in
[selective redraw](../../guidance/techniques/selective-redraw.md). It does not port Gloom,
use its assets, or implement a game. Read the
[validation and examined sources](../../guidance/techniques/validation/selective-redraw.md)
for evidence and limits.

## Target and memory contract

The tested targets are XRoar `coco3`, NTSC, `gime1986`, 6809, with **128 KiB
and 512 KiB RAM**. The program explicitly selects the slow MPU rate with
`$FFD8`; it never selects 6309 or the fast rate. Host `-no-ratelimit` affects
how quickly the test runs on the host, not the chosen emulated CPU rate.
No performance claim follows from this test.

The runner verifies the combined NTSC `coco3.rom` against `roms.json` before
launch. It passes the absolute path with `-extbas`, disables cartridges, and
uses `-c /dev/null` to exclude personal XRoar configuration. Direct DECB
loading is tested. Disk BASIC and physical loading are not tested.

| CPU address | Use |
| --- | --- |
| `$3000` through `state_end-1` | Code, fixtures, histories, counters |
| `$3FFF`, `$4280` | A guards |
| `$4000–$427F` | A, 640-byte framebuffer window |
| `$4FFF`, `$5280` | B guards |
| `$5000–$527F` | B, 640-byte framebuffer window |
| `$7E00–$7EFF` | Reserved stack, initial S=`$7F00` |

The runner rejects code/state reaching `$4000`. IRQ and FIRQ are masked,
DP is zero, task 0 is selected, and its eight MMU pages are explicitly
`$38–$3F`. `$FF90=$4E` enables native MMU mapping with GIME IRQ/FIRQ outputs
disabled and constant FExx RAM. No interrupt handlers or ROM calls are used.
A fresh boot and direct loader are prerequisites; this is not a callable BASIC
extension and does not return to BASIC.

Both tested capacities map these executive pages to their top 64 KiB.
The raw snapshot reader therefore takes the final 65,536 bytes after checking
that the snapshot has the requested RAM capacity. This mapping was tested
independently for both sizes, not inferred as compatibility from one run.

The windows represent eight rows of a 160-pixel, 16-colour packed layout:
80 bytes per row, two pixels per byte. They are **not complete 192-line
screens**. No video base, resolution, palette or buffer-presentation registers
are configured. Each window owns regions x=0–7 and x=16–23, y=0–7; all other
bytes retain the allocation pattern `$A5`. This isolates framebuffer writes
from display setup. RAM checks cannot establish rendered output.

## Adaptation and API

`render` accepts X pointing to two current records, Y to that destination's
history, and U to its window. Each five-byte record contains valid, top,
bottom-exclusive, foreground index and background index. The fixed fixture
contract is `0 <= top <= bottom <= 8`, colours 0–15, and current valid=1.
The assembly trusts this bounded caller; it is not an untrusted-data API.
Each history initially has valid=0 even though its other fields are zero.

For each changed record, `paint` repaints the complete 8×8 region, including
background exposed by shrinkage. It publishes the description after painting.
It skips equal valid descriptions. Each buffer owns ten history bytes.
External writes require the owner to clear the affected region's valid byte.
Unowned gaps are not restored; invalidation applies only to the two regions.

The Python oracle creates all 1,280 pixels from the frame specification,
then packs adjacent pixels. It does not invoke assembly painting or compare
retained records. The host oracle checks both windows and their guards at
all checkpoints. A second assembly build always redraws both owned regions;
that build is also checked against the independent oracle.

## Reproduce

From the repository root, with the repository's locked environment and native
LWTOOLS/XRoar available:

```sh
uv sync --locked
uv run python scripts/setup.py --target coco3 --roms-only
uv run python scripts/doctor.py --profile demo --target coco3
uv run python experiments/selective-redraw/selective_redraw.py
COVERAGE_FILE=build/selective-redraw/.coverage \
uv run pytest experiments/selective-redraw \
  --cov=experiments/selective-redraw \
  --cov-config=experiments/selective-redraw/coverage.ini
uv run ruff check experiments/selective-redraw
uv run ruff format --check experiments/selective-redraw
markdownlint experiments/selective-redraw/README.md \
  guidance/techniques/validation/selective-redraw.md
```

`--help` and argument rejection have no build or emulator side effects.
`--output build/selective-redraw/another-run` keeps another local run.
The default rerun replaces its own generated files and deletes every expected
snapshot before launching. Specifications use unique directories under
`build/selective-redraw/`. No GUI launches or installs occur in the runner.

All essential source, driver generation, fixtures, oracle and assertions are
tracked here. Generated `.bin`, `.sym`, `.ram`, logs, and `results.json` stay
under ignored `build/selective-redraw/`. Examined reference-page renders stay
under ignored `local/research/selective-redraw/`; no downloaded source or ROM
is included in the experiment.

## Failure controls

`shared-history` deliberately compares both destinations against A's history.
It fails when first switching to B. `missing-invalidation` performs an external
`$EE` write without clearing the valid byte. It leaves one wrong byte after
the redraw and on the following unchanged frame. Both failures must occur for
the experiment to pass. Their snapshots and logs are retained beside good runs.
Every run also attaches a snapshot to the unreachable `state` data label;
creating that snapshot is a failure. Missing checkpoints and wrong RAM sizes
also fail the run.

`writes` counts each `STA` in the pixel loop. It excludes allocation poisoning,
external writes, history updates, stack traffic, comparisons and other CPU
work. These software counters are checked against fixed region-size outcomes.
They are not independent bus instrumentation or measurements of elapsed cost.
Do not use them to claim a speedup.
