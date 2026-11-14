# Sound throughput in one emulated second

This harness measures how many DAC samples the two sound examples produce in
one emulated second. It holds the timing claims that used to live in the
sound-slots and timer-sound runners. Their memory checks now run with
`scripts/coco.py check`; this harness adds what a frame snapshot cannot show.

## Run it

It needs the native tools and verified CoCo 1 and CoCo 3 firmware. From the
repository root:

```sh
uv run python experiments/sound-throughput/throughput.py check
uv run --locked --no-sync python scripts/validate_repository.py run \
  sound-throughput --heavy
```

## What it measures

Each case starts from nonzero RAM, begins an instruction trace at the first
`sample` checkpoint and stops XRoar one emulated second later. Every completed
`frame_ready` overwrites one snapshot, so the last completed frame remains.
A data label that must never execute adds an unreachable-checkpoint control.

- [Sound slots](../../examples/sound-slots/README.md), CoCo 1: the last
  completed frame bounds throughput between `frames x 256` and
  `(frames + 1) x 256` samples. The example's independent model checks that
  frame's memory.
- [Timer sound](../../examples/timer-sound/README.md), CoCo 3: cooperative
  light and heavy builds on the 1986 GIME, and timer light and heavy builds on
  both GIME revisions. The trace must contain the exact phase sequence. Timer
  throughput must stay within the revision's predicted range under both loads,
  the heavy build must complete fewer redraws, and the heavy cooperative build
  must lose more than half its samples.
- A timer build without the GIME acknowledgement must complete no frame.

Results are written to ignored `build/sound-throughput/results.json`.
Averages over one second do not measure sample jitter, audible quality,
elapsed host time or physical hardware.
