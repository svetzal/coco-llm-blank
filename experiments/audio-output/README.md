# Capture XRoar mixer output

Read [the findings](../../guidance/techniques/validation/audio-output.md) for the boundary,
primary sources, expectations and limits. This original instrumentation captures
real XRoar output buffers. It never constructs samples from the phase oracle or
DAC timestamps. Existing assembly and production runners remain unchanged.

## Prepare a private build

Use the project's existing locked Python environment, C compiler, make and
LWTOOLS. See [toolchain](../../guidance/starter/toolchain.md) for first-time setup.
Do not synchronize a shared environment or run `make install` for this experiment.
Run the target-specific doctor checks before launching:

```sh
uv run --no-sync python scripts/doctor.py --profile demo --target coco1
uv run --no-sync python scripts/doctor.py --profile demo --target coco2
```

Stop on firmware failure. ToolShed is optional for these direct binary loads.
Every launch also verifies both ROMs against the repository's firmware manifest.

Use a fresh ignored directory under this experiment. A cached archive is valid
only if its bytes match the pinned SHA-256. The tracked builder verifies that
hash, extracts fresh source, applies the exact two-file instrumentation, runs
configure and make, and writes `capture-build.json` beside the source. It never
installs the executable globally. Keep the upstream license files there.

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python \
  experiments/audio-output/build_capture.py \
  --archive local/research/audio-timing/xroar-1.12.1.tar.gz \
  --output experiments/audio-output/.work/build
```

The archive's upstream URL and checksum are in the findings. Supply another
cached path with `--archive` if needed. The builder refuses an existing output
directory. Configure and make logs remain beside the private source.

Before each capture, verification compares the actual C/header/build-template
inputs with the pinned archive plus the current exact patch, and checks the
executable, builder, instrumenter and reused `examples/sound-slots/expected.py`
oracle hashes against the build record. Thus changing a source file and its
manifest hash together still fails. An ordinary executable has no valid build
record, and a substituted executable fails its hash check before capture starts.

This is local provenance, not a signed or hermetic attestation. The compiler,
linked system libraries, generated configure outputs and host are trusted.
Someone who can replace both executable and manifest can forge that association;
the manifest does not mathematically prove how an arbitrary executable was
compiled. Runtime checks still require the timing instrumentation and real PCM.

## Capture and verify

Use a new output directory for each run. The runner refuses existing case
folders to prevent stale evidence. Run Python without optimization because the
reused RAM oracle includes assertions.

```sh
uv run --no-sync python experiments/audio-output/capture.py \
  --xroar experiments/audio-output/.work/build/xroar-1.12.1/src/xroar \
  --output experiments/audio-output/.work/measured-checked
COVERAGE_FILE=experiments/audio-output/.work/.coverage \
AUDIO_ARCHIVE=local/research/audio-timing/xroar-1.12.1.tar.gz \
AUDIO_XROAR=experiments/audio-output/.work/build/xroar-1.12.1/src/xroar \
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest experiments/audio-output \
  -p no:cacheprovider --basetemp=experiments/audio-output/.work/pytest \
  --cov=experiments/audio-output \
  --cov-config=experiments/audio-output/coverage.ini --cov-report=term-missing
uv run --no-sync ruff check experiments/audio-output
uv run --no-sync ruff format --check experiments/audio-output
markdownlint --fix experiments/audio-output/README.md guidance/techniques/validation/audio-output.md
markdownlint experiments/audio-output/README.md guidance/techniques/validation/audio-output.md
```

`AUDIO_ARCHIVE` must identify the pinned archive used for the build.
The uninstrumented-emulator negative test resolves the ordinary XRoar through
`native.tool_path`, including its `XROAR` override. Point that override at an
ordinary build, not this capture build.

Each case keeps the copied assembly, same-build symbols, binary, commands,
ROM/executable/source digests, final RAM, callback event ticks, raw PCM, WAV and
measurement JSON under the ignored experiment `.work/` directory. `output.wav`
includes ROM boot and all
completed output fragments. Analysis uses only its last 150 ms. The private
backend uses 44,100 Hz, mono, signed 16-bit little-endian, 1,024-frame fragments.
The WAV wrapper copies those bytes without resynthesis or normalization.

The analyzer requires start/end markers, first-sample and completion checkpoint
ticks, and every callback row. It checks an independent execution-duration
budget, each callback's expected position in the 44,100 Hz timeline, and coverage
through completion, allowing the final incomplete fragment. Removing a whole
fragment and its callback row is not accepted, including removal at either edge
or retention of only the last 46,080 frames. These checks apply to controls too.
