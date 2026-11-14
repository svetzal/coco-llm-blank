# Small CoCo 3 game-state experiment

## Subset fixed before implementation

This original 6809 experiment implements only bounded sending and friendly
scheduled arrivals from the existing host game-state contract. It is not a
port of that model's 60 specifications or a complete game.

- Two planets, both permanently owned by player 1; zero production.
- Two queue slots, scanned in slot order. Sending uses the first free slot.
- Ship counts are unsigned bytes. Reinforcement saturates at 255.
- Turns, positive delays, and the configured limit are unsigned 16-bit values.
  Reject addition overflow and arrivals after the limit before changing state.
- A send requires the command phase, player 1, distinct planet indices 0/1,
  a positive available ship count, a valid delay, and a free slot.
  Every rejected send leaves all 17 world bytes identical.
- Starting a turn requires the complete phase and turn below the limit. Increment
  first, resolve all due or overdue arrivals once, then enter commands. Clear
  every byte of each retired slot. Ending commands enters complete, or finished
  at the limit. No victory rule is implemented.
- The driver supplies valid initial worlds. It does not expose a save-file
  parser, arbitrary ownership, combat, production, elimination, input or menus.

Targets are explicitly CoCo 3, 128 and 512 KiB, 6809, NTSC, GIME 1986, slow
MPU rate, direct DECB loading, no cartridge, headless UI and null audio.
These are experiment selections. The unrelated local project contract is not
changed. IRQ/FIRQ remain masked throughout this single-threaded experiment;
there is no asynchronous observer or NMI source. Rejection is atomic at the
API boundary. This does not establish safe integration with live interrupts.

## Reproduce

Run from the repository root after its documented bootstrap has prepared the
native tools and verified CoCo 3 firmware. No new global install is needed.
In a shared environment retain `--no-sync`; a fresh clone first needs
`uv sync --locked` and the repository's toolchain/ROM setup.

```sh
uv run --no-sync python scripts/doctor.py --profile demo --target coco3
uv run --no-sync python experiments/game-state-coco3/validate.py
COVERAGE_FILE=build/game-state-coco3/.coverage uv run --no-sync pytest \
  experiments/game-state-coco3 --cov=validate --cov=vectors \
  --cov-config=experiments/game-state-coco3/coverage.ini \
  --cov-report=term-missing \
  --cov-report=json:build/game-state-coco3/coverage.json
uv run --no-sync ruff check experiments/game-state-coco3
uv run --no-sync ruff format --check experiments/game-state-coco3
markdownlint --fix experiments/game-state-coco3/README.md \
  guidance/game-state-coco3-validation.md
markdownlint experiments/game-state-coco3/README.md \
  guidance/game-state-coco3-validation.md
```

The runner verifies the installed ROM immediately before launch, uses its
absolute path and `-c /dev/null`, creates isolated files under ignored
`build/game-state-coco3/`, removes stale captures, and bounds emulator runtime.
It never starts a GUI. See the [validation note](../../guidance/game-state-coco3-validation.md)
for sources, byte layout, evidence and limitations.
