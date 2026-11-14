# Measure intervals between DAC writes

Read this when average sample throughput is insufficient to assess the
[sound experiments](../sound.md). This is an emulator timing experiment,
not a listening test. The timer keeps its average rate under the tested redraw
load, but individual DAC writes are not evenly spaced.

## Target and measurement boundary

Measured with a private, instrumented XRoar 1.12.1 build on Apple Silicon macOS.
The installed emulator was not replaced. All runs selected 6809, NTSC,
nonzero initial RAM, no cartridge, null UI and null audio. Sound slots used
`cocous`, 32 KiB, Color BASIC 1.1 and Extended BASIC 1.0. The timer/cooperative
comparison used `coco3`, 128 KiB, the combined CoCo 3 ROM, and an explicit
`gime1986` or `gime1987` selection.

The existing examples select the slow clock. For these runs that means
14,318,180 / 16 = 894,886.25 emulated CPU cycles per second. This is a frequency
in the emulator model, not a measured physical oscillator frequency.
Sound slots has no GIME. Its SAM slow cycles also take 16 event ticks.

Before launching each case, the research script called the current
`roms.verify_installed(ROOT, target, names)` API and passed the returned absolute
paths to `-bas` and `-extbas`. Both target-specific doctor checks also passed;
ToolShed was absent but is optional for these direct DECB loads. Neither ROM
filenames nor the emulator exit status served as validation.

The logger sits immediately before `sound_set_dac_level` in the PIA1 port-A
output callback. At this point the emulated bus cycle has advanced the event
clock and the PIA output state has changed. It records `event_current_tick`,
CPU PC, port value, control register and direction register. It records writes
with unchanged values too. This is a timestamp at the modeled DAC update,
not an instruction count, audio-buffer timestamp or host clock reading.

Relevant inspected source in the pinned archive:

- `src/events.h`: `EVENT_TICK_RATE=14318180`, unsigned 32-bit event ticks.
- `src/coco3.c`, `cpu_cycle`: advances the machine event queue before the write.
- `src/tcc1014/tcc1014.c`, `tcc1014_mem_cycle`: slow cycle is 16 ticks;
  fast cycle is 8. `schedule_timer` uses four ticks per fast-timer decrement.
  Revision offsets are two for 1986 and one for 1987.
- `src/dragon/dragon.c`, `cpu_cycle`, and `src/mc6883.c`, `mc6883_mem_cycle`:
  SAM timing advances before the PIA write; a continuing slow cycle is 16 ticks.
- `src/mc6821.c`: port-A writes update output state before the callback.
  DDR writes can invoke it too, so filtering is necessary.
- `src/dragon/coco.c`: CoCo overrides the common Dragon DAC callback.
  Instrumenting only `dragon.c` produced no CoCo records. That probe was rejected.

## Results

Each window ends one emulated second after reaching the first `sample`
instruction. Only completed DAC writes and intervals between them are counted.
The first-to-last-write span is slightly shorter than one second. No interval
is inferred across either edge of the window.

All interval values below are slow CPU cycles, calculated as tick difference
modulo 2^32, divided by 16. Every observed difference was a positive multiple
of 16. The spread is maximum minus minimum, not deviation from the mean.

| Case | Writes | Intervals | Min | Max | Mean | Spread |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CoCo 1 sound slots | 15,615 | 15,614 | 57 | 138 | 57.311259 | 81 |
| Cooperative, light, 1986 | 12,746 | 12,745 | 70 | 125 | 70.211455 | 55 |
| Cooperative, heavy, 1986 | 2,508 | 2,507 | 70 | 80,002 | 356.951735 | 79,932 |
| Timer, light, 1986 | 6,992 | 6,991 | 123 | 134 | 128.000143 | 11 |
| Timer, heavy, 1986 | 6,992 | 6,991 | 123 | 133 | 127.999857 | 10 |
| Timer, light, 1987 | 7,005 | 7,004 | 123 | 134 | 127.750286 | 11 |
| Timer, heavy, 1987 | 7,005 | 7,004 | 123 | 133 | 127.749857 | 10 |

The heavy cooperative case has 2,498 gaps of 70 cycles and nine gaps of
80,002 cycles. The long gaps are about 89.399 ms of emulated time.
The light 1986 timer case has this complete distribution:

| Cycles | Interval count |
| ---: | ---: |
| 123 | 2 |
| 124 | 6 |
| 125 | 10 |
| 127 | 5,339 |
| 129 | 6 |
| 130 | 559 |
| 132 | 1,067 |
| 134 | 2 |

Thus an average near 128 cycles conceals an 11-cycle observed spread, about
12.292 microseconds. For reload 510, the source predicts timer expirations
2048 ticks apart on 1986 and 2044 on 1987, equivalent to 128 and 127.75 slow
CPU cycles. Those are timer periods; instruction boundaries and interrupt
service affect when the DAC write occurs. This experiment does not separately
attribute each interval to an interrupt-latency component.

Completed redraw counts were 60 for sound slots, 49/9 for cooperative
light/heavy, and 27/2 for timer light/heavy on either revision. These are
foreground throughput measurements. The previously reported 11–30 instructions
between sound-slots writes remain instruction counts; this measurement does
not reinterpret them as CPU cycles. Neither count establishes CPU utilization.

## Controls and checks

The experiment assembled copies of the existing examples under the ignored
research folder. Original example files were not edited.

- Calibration: one `NOP` immediately before `sample` in cooperative light
  shifted both gap sizes from 70/125 to 72/127 cycles, exactly 32 event ticks.
  XRoar's 6809 NOP path fetches the opcode and performs one extra bus cycle.
  This checks the time-unit conversion against the emulator's execution path.
- Negative control: the heavy timer copy executes `ORCC #$40` immediately
  before its redraw loop and `ANDCC #$BF` immediately after it. Its maximum
  measured gap grows to 80,002 cycles, versus 133 in the unmodified heavy case.
  The detector therefore exposes deferred DAC servicing despite a running timer.
  This copy emits 2,049 writes and completes seven redraws. Its last write
  precedes the window end by a substantial gap: first-to-last span is only
  0.917710 seconds. Do not call its span-based rate a one-second throughput.
- Repeatability: the unmodified heavy 1986 timer run, a second accelerated run,
  and a rate-limited run have identical complete interval histograms and counts.
  Host elapsed time is not an input to any timing calculation.
- Each run validates every six-bit sample against `(sample_index * 8) % 256`,
  requires the PIA data register selected and DAC bits configured as outputs,
  and checks a completed-frame RAM snapshot, framebuffer guards and marker.
  CoCo 3 also uses the existing `verify_frame` state and phase checks.
- A trap at the non-executable `state` label must not create a snapshot.
  Missing sample records, missing completion snapshots, invalid sample values,
  and an unexpected negative snapshot fail the measurement.

## Reproduce the instrumentation

The original archive is
<https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz>.
Its SHA-256 is
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
This experiment reused the local archive with that digest, extracted a separate
copy, and retained its original license files. No downloaded source is tracked.

Apply these additions to that archive. They only log state; they do not advance
the emulator clock or inject CPU instructions. The existing headers supply
`fprintf`, `stderr` and event declarations in this build.

<!-- markdownlint-disable MD010 -->

```diff
--- a/src/coco3.c
+++ b/src/coco3.c
@@ -1421,6 +1421,12 @@
 
 static void pia1a_data_postwrite(void *sptr) {
 	struct coco3 *mcc3 = sptr;
+	/* Research only: emulated ticks at the PIA output update. */
+	if (mcc3->CPU->reg_pc >= 0x3000 && mcc3->CPU->reg_pc < 0x4000)
+		fprintf(stderr, "AT,%u,%04x,%02x,%02x,%02x\n",
+		        (unsigned)event_current_tick, mcc3->CPU->reg_pc,
+		        PIA_VALUE_A(mcc3->PIA1), mcc3->PIA1->a.control_register,
+		        mcc3->PIA1->a.direction_register);
 	sound_set_dac_level(mcc3->snd, (float)(PIA_VALUE_A(mcc3->PIA1) & 0xfc) / 252.);
 	tape_update_output(mcc3->tape_interface, mcc3->PIA1->a.out_sink & 0xfc);
 }
--- a/src/dragon/coco.c
+++ b/src/dragon/coco.c
@@ -237,6 +237,12 @@
 
 static void pia1a_data_postwrite_coco(void *sptr) {
 	struct dragon *md = sptr;
+	/* Research only: emulated ticks at the PIA output update. */
+	if (md->CPU->reg_pc >= 0x3000 && md->CPU->reg_pc < 0x4000)
+		fprintf(stderr, "AT,%u,%04x,%02x,%02x,%02x\n",
+		        (unsigned)event_current_tick, md->CPU->reg_pc,
+		        PIA_VALUE_A(md->PIA1), md->PIA1->a.control_register,
+		        md->PIA1->a.direction_register);
 	sound_set_dac_level(md->snd, (float)(PIA_VALUE_A(md->PIA1) & 0xfc) / 252.);
 	tape_update_output(md->tape_interface, md->PIA1->a.out_sink & 0xfc);
 }
```

<!-- markdownlint-enable MD010 -->

## Reproduce from a fresh clone

The tracked [measurement script](../../../experiments/audio-timing/measure.py) preserves
all eleven cases from the original ignored script. It is a bounded research
experiment, not a game runner or a general timing framework. It resolves the
repository from its own location, creates its output directories, and uses
`native.tool_path("lwasm")` (the `LWASM` override, local toolchain, then PATH).
`--xroar` is required; it never selects the installed emulator implicitly.
Do not use Python optimization: the experiment's assertions are validation.

From the repository root, prepare the locked Python environment:

```sh
uv sync --locked
```

Use an existing C compiler, make, patch, tar and LWTOOLS installation. See
[toolchain](../../starter/toolchain.md) if they are missing. No global Python install, emulator
installation, or GUI launch is part of this procedure. Provision and verify the
two firmware profiles without running setup or changing `local/PROJECT.md`:

```sh
uv run --no-sync python - <<'PYCODE'
import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts").resolve()))
from roms import provision, verify_installed

for target in ("coco1", "coco3"):
    provision(Path.cwd(), target)
    verify_installed(Path.cwd(), target)
PYCODE
uv run --no-sync python scripts/doctor.py --profile demo --target coco1
uv run --no-sync python scripts/doctor.py --profile demo --target coco3
```

Stop on any firmware failure. ToolShed is optional for these direct binary
loads. The script also verifies the required ROM bytes before each case and
passes the verified absolute paths to XRoar.

Download the pinned archive into the private reproduction folder, then check
its digest **before** extracting. An existing archive with the same digest can
be copied to this location instead of downloaded. Use a fresh source directory;
do not apply the patch twice.

```sh
mkdir -p local/research/audio-timing-reproduction
curl --fail --location \
  https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz \
  --output local/research/audio-timing-reproduction/xroar-1.12.1.tar.gz
uv run --no-sync python - <<'PYCODE'
import hashlib
from pathlib import Path

private = Path("local/research/audio-timing-reproduction")
archive = private / "xroar-1.12.1.tar.gz"
expected = "ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88"
if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
    raise SystemExit("Archive checksum mismatch; stop before extraction")
note = Path("guidance/techniques/validation/audio-timing.md").read_text()
patch = note.split("```diff\n", 1)[1].split("\n```", 1)[0] + "\n"
(private / "dac-timestamps.patch").write_text(patch)
PYCODE
tar -xzf local/research/audio-timing-reproduction/xroar-1.12.1.tar.gz \
  -C local/research/audio-timing-reproduction
patch -d local/research/audio-timing-reproduction/xroar-1.12.1 -p1 \
  < local/research/audio-timing-reproduction/dac-timestamps.patch
(
  cd local/research/audio-timing-reproduction/xroar-1.12.1
  ./configure --without-gtk3 --without-gtk2 --without-sdl3 --without-sdl2 \
    --without-cocoa --without-coreaudio --without-alsa --without-oss \
    --without-pulse > ../configure.log 2>&1 &&
  make -j4 > ../make.log 2>&1
)
```

Stop if patching, configuration or compilation fails. Keep the archive's
license files with the private source. Do not run `make install`. Run the
tracked experiment with the private executable:

```sh
uv run --no-sync python experiments/audio-timing/measure.py \
  --xroar local/research/audio-timing-reproduction/xroar-1.12.1/src/xroar
```

A fresh clone has no `build/audio-timing-reproduction/` directory; the script
creates it. Later runs replace each case's snapshots and logs, and remove the
aggregate result before starting. A successful run writes `results.json` only
after all cases and cross-case assertions pass. Do not interpret leftover
individual JSON files from an interrupted run as a completed experiment.
Copied assembly stays under ignored `local/research/audio-timing-reproduction/`.
Binaries, symbols, exact assembly and emulator commands, logs, snapshots,
per-case JSON, aggregate results and runtime provenance stay under ignored
`build/audio-timing-reproduction/`. Nothing reads the old ignored `measure.py`.

### Case matrix and acceptance checks

| Case | Source | Defines | GIME | Modification |
| --- | --- | --- | --- | --- |
| slots | sound-slots | none | none | none |
| coop-light | timer-sound | none | 1986 | none |
| coop-heavy | timer-sound | HEAVY | 1986 | none |
| timer86-light | timer-sound | TIMER | 1986 | none |
| timer86-heavy | timer-sound | TIMER, HEAVY | 1986 | none |
| timer87-light | timer-sound | TIMER | 1987 | none |
| timer87-heavy | timer-sound | TIMER, HEAVY | 1987 | none |
| coop-nop | timer-sound | none | 1986 | NOP before sample |
| timer86-masked | timer-sound | TIMER, HEAVY | 1986 | Mask FIRQ during redraw |
| timer86-heavy-repeat | timer-sound | TIMER, HEAVY | 1986 | Repeat run |
| timer86-heavy-realtime | timer-sound | TIMER, HEAVY | 1986 | Rate limited |

Sources are `examples/<source>/main.asm`; only ignored copies are modified.
The NOP control replaces `sample  sta $FF20` with `nop` followed by that
original labeled instruction. The masked control inserts `orcc #$40` before
`redraw  sta ,x+` and `andcc #$BF` after `blo redraw`. Each substitution requires
exactly one matching anchor; source drift cannot silently remove a control.

Each assembly uses `--6809 --format=decb` and a symbol dump from that build.
Each emulator command uses the machine settings specified above and starts with
an eight-second emulated timeout. The unreachable `state` trap must never
produce a snapshot. The first `sample` trap starts a one-second window;
`frame_ready` saves completed-frame RAM throughout that window. A 40-second
host subprocess timeout bounds each launch; host time never enters statistics.

The filter accepts only `AT` records at `sample + 3`, after the extended
`STA $FF20` fetch. Every accepted record must select the PIA data register,
configure DAC bits as outputs, and match the complete six-bit sample sequence.
There must be more than 256 writes. Adjacent unsigned 32-bit tick differences
must be positive multiples of 16. No interval is inferred at a window edge.
The CoCo 1 snapshot checks size, framebuffer guards and marker. CoCo 3 reuses
`timer_sound.verify_frame`, including completed-frame, phase and state checks.

The NOP control must shift both minimum and maximum by two slow cycles. The
masked maximum must exceed the unmodified heavy timer maximum by more than
100 times. The three heavy 1986 runs must match complete histograms, sample
counts and frame counts. These are the original controls, with explicit count
checks added to the repeatability comparison.

After a successful run, execute the co-located fault checks and scoped lint:

```sh
PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest \
  experiments/audio-timing/measure_spec.py -p no:cacheprovider \
  --basetemp=build/audio-timing-reproduction/test-tmp
uv run --no-sync ruff check experiments/audio-timing
uv run --no-sync ruff format --check experiments/audio-timing
markdownlint guidance/techniques/validation/audio-timing.md
```

The tests require the freshly generated evidence; absent evidence fails instead
of skipping. They reanalyze real logs and snapshots, then damage copies to
exercise missing samples, bad values, wrong PIA state, fractional-cycle gaps,
missing or impossible snapshots, truncated RAM, damaged guards and markers.
They also check tick wraparound, filtering unrelated callbacks, failed controls,
source-anchor drift, argument parsing from another working directory and
rejection of optimized Python. These checks do not establish analog audio or
physical hardware behavior.

### Reproduction evidence

On 2026-11-14, the tracked script completed all eleven cases from `/tmp`,
with absolute script and `--xroar` paths and
`uv run --project /Users/svetzal/Work/Projects/Personal/coco-llm-blank --no-sync`.
`PYTHONDONTWRITEBYTECODE=1` prevented shared Python cache writes. The entire
experiment output directory was absent at launch; the script created it.
This run reused the existing project virtual environment and verified firmware.
It did not rerun setup, synchronize the shared environment, change the project
target or install global tools. The fresh-clone setup commands above are
instructions; this was an empty-output reproduction in the existing checkout,
not a claim that a second clone was provisioned.

The private emulator was rebuilt from the checksum-verified cached release
archive using the patch and configure flags above. Both doctor checks exited
zero (ToolShed absent and optional). Host was macOS 27.2 arm64, Python 3.13.12,
LWTOOLS 4.25 and XRoar 1.12.1. The native discovery API selected
`/opt/homebrew/bin/lwasm` on this host; that path is recorded evidence, not a
script default.

All eleven decoded result objects exactly equaled the original
`build/audio-timing/results.json`, including full histograms, ROM and source
hashes, counts, spans and floating-point statistics. The seven primary cases
therefore retain the exact values in the Results section. The remaining cases
were:

<!-- markdownlint-disable MD013 -->

| Case | Writes | Intervals | Frames | Min | Max | Mean cycles | Span ticks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| coop-nop | 12,393 | 12,392 | 48 | 72 | 127 | 72.2130406714009 | 14,317,824 |
| timer86-masked | 2,049 | 2,048 | 7 | 125 | 80,002 | 400.9990234375 | 13,139,936 |
| timer86-heavy-repeat | 6,992 | 6,991 | 2 | 123 | 133 | 127.99985695894722 | 14,317,552 |
| timer86-heavy-realtime | 6,992 | 6,991 | 2 | 123 | 133 | 127.99985695894722 | 14,317,552 |

<!-- markdownlint-enable MD013 -->

The 37 scoped tests passed. Ruff check (also with explicit
`--config pyproject.toml`), Ruff format check and Markdown lint passed.
The whole starter suite was not run for this isolated experiment. An additional
real negative run used the installed, uninstrumented emulator with the heavy
1986 command and separate output files. It exited zero and saved a completion
snapshot, but the measurement rejected it with `missing samples`, count zero.
A successful emulator exit and valid framebuffer cannot substitute for DAC logs.

Runtime provenance is in `build/audio-timing-reproduction/provenance.json`;
per-case JSON contains verified ROM and copied-source digests. The ignored
`local/research/audio-timing-reproduction/validation.json` records equality with
the original results and SHA-256 hashes of generated evidence, command files,
archive, patch and build logs. The uninstrumented probe's command, log and
outcome are in `build/audio-timing-reproduction/uninstrumented-control/`.
These generated files are not part of the tracked package.

Key SHA-256 provenance for this run:

- Original ignored measurement script:
  `9fa9403a1dd065d975522bd444ffe85fdb4a95a24100d3eb9db10b57f054ec0a`
- Tracked measurement script:
  `c631ea4d107c1725a7aa88c292ac28072b351bca56afd228d28b2d0fda1ec407`
- Instrumentation patch extracted from this note (unchanged):
  `ca0d9861170d237e8d2e26c94448a87c47c2ad77fd4de2e1268cd1599a6b4df7`
- Rebuilt private executable:
  `b258f4062c189e90de14ba80931b4f8c8f1fd6dec5e0dcecfb8d2e10d874eff6`
- Project lockfile:
  `a7203eb44883bbee9776ffd5eda312c918c30c55fc1f664b997a9c72b662d975`

The archive digest is pinned above. Executable digests identify this build;
they are not portable build-reproducibility claims across compilers or hosts.
No third-party source bodies, downloads, firmware or generated measurement
files are included in the tracked reproduction package.

## Limits

These are finite-window observations on XRoar 1.12.1, not worst-case timing
bounds for a game. The source itself notes CoCo 3 timer emulation limitations.
The experiment does not validate physical GIME accuracy, PAL, 6309, fast CPU
clock, analog joystick interactions, changing memory mappings or other code.
It does not test sound routing, audio quality, display appearance or physical
hardware. A stable average rate is not zero jitter, and a small observed spread
is not a guarantee that a larger workload cannot interrupt playback.
