# Collect room

## Contract

An original small game for CoCo 1 (`cocous`) and CoCo 2B (`coco2bus`).
The prototype selects 32 KiB, NTSC, normal-clock 6809, a non-T1 MC6847,
no cartridge and direct DECB loading. These are implementation choices.

- Arrow keys move one tile per update while held. Multiple arrows cancel.
- Space starts at the title or restarts after winning, on a rising edge.
  Startup-held Space is suppressed. Space during play does nothing.
- Collect both stars, then enter the exit. The exit blocks entry until then.
- Walls and room boundaries reject motion. Every sample still updates input
  history, including rejected moves. Winning freezes movement until restart.
- Restart restores both stars and the starting position (0, 0).

The 8-by-6 room uses prepared original art from `experiments/assets/art.json`,
enlarged twofold to 16-by-16 tiles, plus an original actor and lettering.
The renderer redraws the room after accepted movement or a phase change.
It does not erase the whole framebuffer between steps. This is a tile-step
baseline, with no claim of smooth animation, tear-free presentation or constant
frame rate. Short original DAC effects block input briefly; no music player,
ROM calls, interrupt handler, joystick conversion or disk loader is included.

## Verified source facts

The following primary pages were read as images before implementation.
PDF pages are one-based positions in the linked files.

- Inman, [Assembly Language Graphics][graphics], PDF 106: mode 6R is
  256 by 192 and occupies `$0400..$1BFF`. Derived layout: 32 bytes per line,
  6,144 bytes, one bit per pixel.
- Motorola, [MC6847 datasheet][vdg], PDF 21, figure 22: RG6 uses eight
  pixels per byte, bit 7 at the left. CSS=0 selects black and green.
- Tandy, [Color Computer Technical Reference Manual][c1], PDF 13–15, 31:
  PIA data/DDR selection uses control bit 2; keyboard rows are `$FF00`,
  columns `$FF02`; RG6 has SAM V=110 and `$FF22` upper nibble `$F0`.
  Preserve its low three bits. Display offset is in 512-byte units;
  `$0400` means offset 2. Clear both SAM rate bits for the normal clock.
  DAC output is `$FF20` bits 7–2; preserve bits 1–0.
- Tandy, the same manual, PDF 38: enable sound and select mux 00 for DAC.
- Tandy, [Color Computer 2 NTSC Service Manual][c2], PDF 36–37:
  keyboard columns are active low. Up/down/left/right/Space are PA3 with
  PB3/PB4/PB5/PB6/PB7 respectively. Derived column strobes are
  `$F7/$EF/$DF/$BF/$7F`. M occupies PA1/PB5 and must not act as Left.
  Mux select 00 routes the six-bit DAC on this machine too.
- Motorola, [MC6821 datasheet][pia], PDF 7: DDR zero selects input and
  one selects output. The scanner initializes rows as inputs and columns
  as outputs, then restores all columns high after every sample.

The repository's [controls guide](../../guidance/techniques/controls-and-collision.md),
[assets guide](../../guidance/techniques/assets.md) and
[sound guide](../../guidance/techniques/sound.md) informed the separation of input, state,
art and output. Game rules, assembly, actor, lettering and effects are original
adaptations. No historical game listing, artwork or music is copied.

[graphics]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf
[c1]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[c2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20%2826-3134%20%26%2026-3136%29%20%28Tandy%29.pdf
[vdg]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf
[pia]: https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Motorola/Motorola%206821.pdf

## Build and play

Run these commands from the repository root after the starter's setup has
prepared `uv`, LWTOOLS, XRoar and the selected firmware. `scripts/coco.py` verifies
both ROM files before launch and ignores personal XRoar configuration.

To use or check both targets, provision both firmware profiles without changing
`local/PROJECT.md`. Do not rerun project setup with a different target.
This is the [complete validation environment procedure](../../guidance/starter/python.md#complete-starter-validation-environment),
limited to the two targets this example uses:

```sh
uv run python - <<'PYROM'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import provision, verify_installed

root = Path.cwd()
for target in ("coco1", "coco2"):
    provision(root, target)
    verify_installed(root, target)
PYROM
```

Stop if provisioning fails. Then build or launch:

```sh
uv run python scripts/coco.py build examples/collect-room
uv run python scripts/coco.py run examples/collect-room --target coco1
uv run python scripts/coco.py run examples/collect-room --target coco2
```

The last two commands open XRoar for play. Close that window to stop.
The game does not return to BASIC. Before assembling, the tool runs
[assets.py](assets.py), named in [coco.toml](coco.toml), to write the art
include. The output is `build/collect-room/main.bin`, a DECB binary with entry
`$3000`.
It is not a disk image. Do not infer a tested disk-loading path from it.

Press and release Space, then use the arrows. The solid character is yours;
stars are collectibles; the arrow-shaped door is the exit. Walls block entry.
The title, play instructions and winning message appear above the room.
There is no time limit. One route from the start is Down, Right (first star),
Down twice, Right twice, Down, Right twice (second star), Down, Right (exit).

## Repeat the checks without opening a window

```sh
uv run python scripts/coco.py check examples/collect-room
uv run python experiments/collect-room-journey/journey.py prepare
uv run python experiments/collect-room-journey/journey.py check --target coco1
uv run python experiments/collect-room-journey/journey.py check --target coco2
uv run --locked --no-sync python scripts/validate_repository.py run \
  collect-room-journey --heavy
markdownlint --fix examples/collect-room/README.md
markdownlint examples/collect-room/README.md
```

The first command uses stock XRoar, which cannot press keys. It checks that,
with no input, the game stays on its title screen: every screen byte, the
state, the room and the guards, against [expected.py](expected.py). The
keyboard journey, audio and mutation controls need an instrumented emulator
and live in [the journey experiment](../../experiments/collect-room-journey/README.md).

`prepare` downloads the SHA-256-pinned XRoar 1.12.1 release and builds
an isolated headless executable under `build/collect-room-journey/instrumented`.
A C compiler and `make` are needed; this command installs nothing globally.
The archive digest is
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
The [upstream release archive][xroar] is the emulator source.
Rerunning preparation starts with that archive, not previously patched source.
Checks reject an executable whose recorded digest or instrumentation changed.
The normal `run` command uses the installed XRoar, without the test hooks.

The original `key_hook.c` injects named keys through XRoar's keyboard API at
the scanner entry. It snapshots RAM at the completed-frame checkpoint.
It does not write CPU, PIA or game state. `audio_hook.c` records actual PIA
output values and routing at XRoar's existing output callback. Neither hook
is needed by the game. There is no dependency on the animation experiment.

`journey.txt` contains hand-authored input and expected outcomes for 95
checkpoints, including startup-held Space, release/repress, unrelated M,
blocked movement with Space held or released, arrows held at boundaries,
multiple-arrow cancellation, the locked exit, three wins and three starts.
The fixture records collected locations explicitly, independently of the
remaining count. The third game collects the lower-right star first, checks
the still-locked exit, returns for the upper-left star and wins.
Every checkpoint checks the state, complete room, 6,144 framebuffer bytes,
input history, completed sound bursts and seven guards. A separate pixel
oracle uses literal source-art rows, not the assembler's packed tables.
The lettering oracle shares the original font specification, but uses a
separate per-pixel placement algorithm.

No-input and unreachable-checkpoint controls must leave the game at its title
and produce no false checkpoint respectively. Mutations deliberately break
the Up column, blocked-move history, Space edge detection and DAC output.
Each must fail the corresponding outcome check; a build/tool error does not
count as detecting a mutation. Host checks also damage RAM evidence, firmware,
asset expectations and cached emulator provenance. A failed rerun replaces
its result status and removes the previous case's snapshots first.

Generated commands, binaries, symbols, logs, RAM and result JSON files stay
under ignored `build/collect-room` and `build/collect-room-journey`. Game
source, artwork specifications, instrumentation, expectations and reproduction
commands remain tracked. No downloads or generated evidence belong in Git.

## Memory and scheduling

| Region | Use |
| --- | --- |
| `$0400..$1BFF` | RG6 framebuffer |
| `$03FF`, `$1C00` | Framebuffer guards |
| `$3000..program_end-1` | Code, prepared art, headers, initialized game state |
| `$7E00` | Stack guard |
| `$7E01..$7EFF` | Reserved downward-growing stack; initial S=`$7F00` |

The build rejects code/state reaching `$7E00`. Symbols come from the same
assembly as the binary. Startup initializes state even with nonzero RAM.
Room and asset tables have guard bytes on both sides. The test checks guards
but is not a proof against every possible stack usage or memory corruption.

Each loop has a 12,000-iteration busy delay before scanning. Held arrows step
once per loop, with no separate repeat acceleration. Redrawing and effects
extend the interval. A pickup plays 32 alternating high/low DAC writes with
short delays; start and win use different delays. Output returns to zero DAC
level after each burst. Input is sampled between bursts, so a sufficiently
short key tap can be missed. There is no interrupt-driven sound or debounce.
IRQ and FIRQ remain masked. The keyboard and DAC setup owns the shared mux;
this code is not a transparent addition to a BASIC interrupt/audio routine.

## Evidence and limits

Result JSON records exact binary/emulator/ROM hashes, configured target,
checkpoint count, DAC writes, scan intervals and within-burst intervals.
Intervals are XRoar ticks (14,318,180 per second in XRoar 1.12.1 `src/events.h`),
not wall-clock measurements or physical timing. `-no-ratelimit` removes host
pacing without changing the selected normal emulated CPU rate.

RAM and DAC callback evidence are distinct from the renderer and speaker.
No GUI was launched or inspected during implementation. No renderer frames
were captured, no audio was listened to, and no physical CoCo was tested.
The completed-frame RAM checks do not rule out tearing between checkpoints,
composite colour differences, host keyboard focus issues or audible clicks.
The CoCo 2B emulator result does not establish every CoCo 2 board revision.

[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz

Code and state end at `$36C0` (exclusive), below the reserved stack.
The measurements below describe emulator scheduling, not perceived sound
quality or physical responsiveness. They are not worst-case bounds for other
code. Current reports are replaced when the checks run again.

### Review corrections

The checker now takes explicit collected-location bits from the hand-authored
fixture. It no longer guesses the missing star from the remaining count.
The added third game collects (5, 4) first, checks the locked exit, returns
for (1, 1), and wins. A regression deliberately supplies the wrong missing-star
location with the same remaining count; both machine runs reject it.

The revised macOS run passed 33 tests with 94.17% combined statement/branch
coverage. Both targets passed all 95 checkpoints, three wins, and the original
four mutation controls. Each positive journey produced 384 DAC writes in 12
effects. Exact measurements are in `build/collect-room-journey/coco1-check.json`
and `coco2-check.json`; this still establishes RAM and DAC callback behavior,
not renderer output, listening quality or physical hardware.

The documented two-profile provisioning commands were executed successfully.
`local/PROJECT.md` remained byte-identical. Scoped Ruff check/format and
Markdown fix/check passed.
