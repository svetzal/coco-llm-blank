# Collect room keyboard journey

This harness plays the [Collect room](../../examples/collect-room/README.md)
journey with injected keys. Stock XRoar cannot press keys, so the example's own
`scripts/coco.py check` covers only the idle title screen. This harness holds
what used to be the collect-room runner's keyboard, audio and mutation checks.

## Run it

It needs a C compiler, `make`, the native tools and verified CoCo 1 and CoCo 2
firmware. From the repository root:

```sh
uv run python experiments/collect-room-journey/journey.py prepare
uv run python experiments/collect-room-journey/journey.py check --target coco1
uv run python experiments/collect-room-journey/journey.py check --target coco2
uv run --locked --no-sync python scripts/validate_repository.py run \
  collect-room-journey --heavy
```

`prepare` downloads the SHA-256-pinned XRoar 1.12.1 release and builds a
headless copy with the example's `key_hook.c` and `audio_hook.c` under ignored
`build/collect-room-journey/instrumented`. It installs nothing globally.
A check refuses an executable whose recorded digest or hooks changed.

## What it checks

For each target, the game is built with `scripts/coco.py` and replays the 95
hand-written steps of `journey.txt`. Every frame is compared with the
example's independent model in `expected.py`: guards, game state, keyboard
history, room, finished sound bursts and all 6,144 screen bytes. DAC writes
must match the expected bursts and audio routing.

Controls: with no keys the game stays on its title; an unreachable checkpoint
leaves no snapshot; four deliberate mutations (`WRONG_COLUMN`, `STALE_HISTORY`,
`HELD_SPACE`, `SILENT`) must each be rejected by an outcome check. A build or
tool failure never counts as a rejected mutation. A failed rerun replaces the
previous result status and snapshots.

Results are written to ignored `build/collect-room-journey/<target>-check.json`.
They establish RAM and DAC callback behaviour, not rendered output, listening
quality or physical hardware.
