# A tone, a moving marker, and a button

This experiment asks a small question: can one CoCo loop keep sound, graphics,
and controls progressing together?

It generates a sawtooth tone and moves an eight-pixel marker across the screen.
The fire button of the right joystick selects a higher pitch.
The marker is deliberately small: eight pixels wide and one row high.
This is a scheduling experiment, not a complete music engine or game.

## Run it

Use the starter's CoCo 1 setup first. From the repository root, run:

```sh
uv run python scripts/coco.py run examples/sound-slots
```

Close XRoar to stop it. The command rebuilds before each launch. Add
`--variant scripted` to launch the test-only input fixture instead.

The target is CoCo 1, NTSC, 32 KiB, normal-clock 6809, and direct DECB loading.
It uses Color BASIC 1.1 and Extended Color BASIC 1.0 firmware.
It does not return to BASIC or provide a disk loader.

## What the loop does

Each iteration advances a 16-bit phase and sends its upper six bits to the DAC.
After 256 samples, the loop reads the fire button and updates the marker.
It erases the old marker before it draws the next position.
The marker wraps after 32 byte positions across the 256-pixel screen.

This design leaves longer gaps between samples when it handles a frame.
Adding work changes playback timing. Do not treat the example as a
constant-rate oscillator. A game with larger drawing tasks needs another
budget or scheduling design.

Interrupts remain masked. The example does not use ROM sound calls.
It does not read analog joystick axes. The fire button is a digital input.

## Source facts

The [sound research guide](../../guidance/techniques/research/sound.md) links the archive
sources and separates the three machines.

- Tandy, **Color Computer Technical Reference Manual**, PDF 13–14:
  keyboard/joystick PIA registers, data-direction selection, DAC bits, and
  sound enable. The example sets keyboard rows as inputs and columns as outputs.

- The same manual, PDF 37–38: active-low fire buttons, shared keyboard rows,
  and audio mux selection. All columns are high when the loop reads the button.
  Both selection bits are clear for DAC audio. Sound enable is set.

- The same manual, PDF 14–15 and 30–31: video controls, SAM display base,
  normal clock, and display-mode table.

- Inman, **Assembly Language Graphics**, PDF 106–108: 256×192 two-colour
  graphics. The example reuses the starter's original first-screen setup.
  A full `$FF` byte avoids a new assumption about horizontal pixel-bit order.

- Nee, **And the Music Played On**, The Rainbow, June 1989, PDF 77–78:
  a software player repeatedly supplies DAC values and uses explicit delays.
  This motivated the scheduling question.
  The experiment does not copy its code.

The framebuffer occupies `$0400–$1BFF`. Guards occupy `$03FF` and `$1C00`.
Code and initialized state start at `$3000`. The build emits their exact symbols.
The reserved stack is `$7E00–$7EFF`. It grows down from `$7F00`.

The CPU writes samples to `$FF20` while preserving its two low bits.
Setup preserves unrelated PIA control fields.

## Repeat the checks

```sh
uv run python scripts/coco.py check examples/sound-slots
uv run python experiments/sound-throughput/throughput.py check
```

[coco.toml](coco.toml) declares:

- the machine
- the checkpoint frames
- the `scripted` variant
- the trace
- `[capture] audio`

The audio capture needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
`check` builds it once with the build tools listed there. Each checkpoint
saves XRoar's mixer output as a WAV in `build/sound-slots/`.

`verify_sound` in expected.py measures the pitch of that WAV against the tone
that the cycle count predicts.
The measured pitch must be within 15 Hz of that tone.
The signal level must be nonzero.
A muted mux fails at frame 1 with "no tone", even though its memory check passes.

[expected.py](expected.py) is the independent model of phase, input and marker.
[sound_slots_spec.py](sound_slots_spec.py) specifies it.

The second command is the one-second throughput measurement in
[the sound-throughput experiment](../../experiments/sound-throughput/README.md).

The check assembles two binaries: normal input and a test-only input fixture.
Both run real 6809 code in XRoar with nonzero startup RAM.
The fixture substitutes released/pressed input after the actual PIA read.
It holds each value for sixteen frames. It does not simulate a physical button.

The check snapshots frames 1, 16, 17, 32, 33, 63, and 64.
These cover movement, wrap, press, hold, and release.
Each checkpoint checks:

- all 6,144 screen bytes
- framebuffer guards
- sample count
- pitch
- input state

An unreachable checkpoint must not create a snapshot.

For each binary, the instruction trace checks 16,384 consecutive DAC writes
against an independent phase model in Python. The trace also measures the number
of instructions between writes. This is a work count, not a cycle count.

A separate measurement stops one emulated second after the first sample checkpoint.
It saves each completed frame and uses the last snapshot to bound throughput.
The incomplete final frame accounts for the 256-sample uncertainty.
Host acceleration changes test duration, not the selected CoCo clock.

Results on XRoar 1.12.1 on Apple Silicon macOS. On 2026-11-14 the
`coco.py check` also passed on XRoar 1.13, and the patch trial for 1.13 gave
identical sound captures. We did not measure these counts again on 1.13.

- Normal input: 11–30 instructions between DAC writes.
- Scripted input: 11–38 instructions. The extra instructions belong to the fixture.
- Normal input: 60 complete marker updates in one emulated second.
- Normal input: 15,360–15,616 samples in that second.

Generated binaries, symbols, RAM snapshots, traces, and `coco1-results.json`
remain under ignored `build/sound-slots/`.
The throughput result is in `build/sound-throughput/results.json`.

Each checkpoint run keeps its own log. The frame-64 log holds the verified trace.
The check stops on missing or inconsistent evidence.

## Limits

The mixer WAV shows that the emulated mux routes the DAC to XRoar's output at
the expected pitch. It does not prove host playback, audibility, distortion,
or audio quality on a real CoCo.

A bounded normal-speed GUI launch exited successfully, but nobody inspected
the display or listened to its output. A physical fire button remains untested.
No physical CoCo, CoCo 2, CoCo 3, PAL, or faster-clock result is claimed.

This example reproduces cooperative progress with a deliberately uneven schedule.
It does not reproduce the magazine's six-voice player.
