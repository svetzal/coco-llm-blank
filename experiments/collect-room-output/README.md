# Collect room output experiment

Read [the findings](../../guidance/techniques/validation/collect-room-output.md) for the
measurement boundary and limitations. Run from the repository root with its
existing Python environment, compiler, make, LWASM and verified firmware.
Nothing is installed globally. All generated artifacts stay in ignored `.work/`.

```sh
uv run --no-sync python scripts/doctor.py --profile demo --target coco1
uv run --no-sync python scripts/doctor.py --profile demo --target coco2
uv run --no-sync python experiments/collect-room-output/prepare_output.py \
  --archive local/research/audio-timing/xroar-1.12.1.tar.gz \
  --output experiments/collect-room-output/.work/reproduce-build
```

Stop on a failed doctor check. ToolShed is optional for this direct binary load.
Supply another cached archive path if needed. Obtain XRoar 1.12.1 from the
[upstream release](https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz) into
ignored storage. The builder verifies SHA-256
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`,
extracts fresh source with its license files and applies tracked instrumentation.
It refuses an existing build destination. Configure and make logs remain there.

```sh
COLLECT_XROAR=experiments/collect-room-output/.work/reproduce-build
COLLECT_XROAR="$COLLECT_XROAR/xroar-1.12.1/src/xroar"
uv run --no-sync python experiments/collect-room-output/run_output.py \
  --xroar "$COLLECT_XROAR" \
  --output experiments/collect-room-output/.work/reproduce-coco1 --target coco1
uv run --no-sync python experiments/collect-room-output/run_output.py \
  --xroar "$COLLECT_XROAR" \
  --output experiments/collect-room-output/.work/reproduce-coco2 --target coco2
```

Both runs use explicit NTSC, 32 KiB, 6809, non-T1 6847, CoCo keyboard and no
cartridge. The profiles are `cocous` and `coco2bus`, with their respective
checksum-verified BASIC and Extended BASIC ROMs. This experiment's contract is
explicit; the unfinished generic `local/PROJECT.md` is not evidence of an owner
choice. The runner does not alter it.

Use `--control video`, `--control audio` or `--control input` and a fresh output
folder for a deliberately failing run. These respectively replace captured
renderer RGB with black, lower mixer gain to -100 dB, and omit keyboard API
injection. Each must exit nonzero with the corresponding output/input rejection,
not a compiler or missing-tool error. The game binary is unchanged in controls.

Each run retains `contract.json`, `result.json`, symbols, binary, generated art,
43 RAM snapshots, input events, XRoar log, raw RGB and raw PCM. The RGB stream is
concatenated 512-by-192 RGB8 frames in logged callback order.
PCM is mono 44,100 Hz
signed 16-bit little-endian, captured in complete 1,024-frame mixer callbacks.
Input timestamps must be at or before their checkpoints; checkpoints
must precede the next input, all within the audio capture boundaries.
Both include boot. No normalization, resynthesis, host playback or window is
involved. Final incomplete audio fragments are reported explicitly.

Existing output folders are refused, preserving earlier failures and preventing
stale evidence reuse. New runs write `incomplete` before work, `failed` on an
exception, and `passed` only after every check. The contract hashes the game,
scene fixture, art, font, runner, analyzer, binary, symbols, ROMs and build.
The builder also hashes reused hooks and verifies actual source inputs against
the pinned archive plus the current exact instrumentation before each run.

## Tests and lint

The test suite builds another private executable and runs both targets and all
three controls on each. It retains all evidence, including failed controls.
Choose a fresh `--basetemp` on reruns to preserve prior results.

```sh
COVERAGE_FILE=experiments/collect-room-output/.work/.coverage \
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest \
  experiments/collect-room-output -p no:cacheprovider \
  --basetemp=experiments/collect-room-output/.work/reproduce-tests \
  --cov=experiments/collect-room-output \
  --cov-config=experiments/collect-room-output/coverage.ini --cov-report=term-missing
uv run --no-sync ruff check experiments/collect-room-output
uv run --no-sync ruff format --check experiments/collect-room-output
markdownlint --fix experiments/collect-room-output/README.md \
  guidance/techniques/validation/collect-room-output.md
markdownlint experiments/collect-room-output/README.md \
  guidance/techniques/validation/collect-room-output.md
```

Set `COLLECT_ARCHIVE` to use another verified archive path for tests.
The suite also rejects whole-fragment/frame loss at either edge or in the
middle, matching-row deletion, renumbered video rows, partial bytes, missing
checkpoints, duplicate timing markers, silence, a wrong effect expectation,
the wrong collected-star location and build tampering. These are independent
negative outcomes, not tests of private call order.
