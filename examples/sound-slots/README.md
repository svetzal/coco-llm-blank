# A tone, a moving marker, and a button

This example asks a small question: can one CoCo loop keep sound, graphics,
and controls progressing together?

It generates a sawtooth tone and moves an eight-pixel marker across the screen.
The fire button of the right joystick selects a higher pitch.
The marker is deliberately small: eight pixels wide and one row high.
This is a scheduling probe, not a complete music engine or game.

## Run it

Use the starter's CoCo 1 setup first. From the repository root, run:

```sh
uv run python scripts/coco.py run examples/sound-slots
```

Close XRoar to stop it. The command rebuilds before each launch. Add
`--variant scripted` to launch the test-only input fixture instead.
Add `--target coco2` to run it on the CoCo 2 target.

The program runs on two targets, both NTSC with a normal-clock 6809 and direct
DECB loading:

- `coco1` (the default): 32 KiB, Color BASIC 1.1.
- `coco2`: the named 26-3134/26-3136 boards with the 64 KiB upgrade, an
  explicit non-T1 MC6847, Color BASIC 1.2.

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

The [sound guide](../../guidance/techniques/sound.md) links the archive
sources and separates the three machines.

- Tandy, **Color Computer Technical Reference Manual**, PDF 13–14:
  keyboard/joystick PIA registers, data-direction selection, DAC bits, and
  sound enable. The example sets keyboard rows as inputs and columns as outputs.

- The same manual, PDF 37–38: active-low fire buttons, shared keyboard rows,
  and audio mux selection. All columns are high when the loop reads the button.
  Both selection bits are clear for DAC audio. Sound enable is set.

- The same manual, PDF 14–15 and 30–31: video controls, SAM display base,
  normal clock, and display-mode table.

- Tandy, **Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)**,
  PDF/printed 8, 11–14 and 35–38: the 64K upgrade, the same register
  addresses and bits, and the custom IC3 that combines the DAC and the mux.
  Selection `00` chooses the DAC.

- Inman, **Assembly Language Graphics**, PDF 106–108: 256×192 two-colour
  graphics. The example reuses the starter's original first-screen setup.
  A full `$FF` byte avoids a new assumption about horizontal pixel-bit order.

- Nee, **And the Music Played On**, The Rainbow, June 1989, PDF 77–78:
  a software player repeatedly supplies DAC values and uses explicit delays.
  This motivated the scheduling question.
  The example does not copy its code.

The framebuffer occupies `$0400–$1BFF`. Guards occupy `$03FF` and `$1C00`.
Code and initialized state start at `$3000`. The build emits their exact symbols.
The reserved stack is `$7E00–$7EFF`. It grows down from `$7F00`.

The CPU writes samples to `$FF20` while preserving its two low bits.
Setup preserves unrelated PIA control fields.

## Repeat the checks

```sh
uv run python scripts/coco.py check examples/sound-slots
```

[coco.toml](coco.toml) declares:

- the two targets
- the checkpoint frames
- the `scripted` variant
- the trace
- `[capture] audio`

The audio capture needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
`check` builds it once with the build tools listed there. Each checkpoint
saves XRoar's mixer output as a WAV in `build/sound-slots/`.

[expected.py](expected.py) is the independent model of phase, input, marker
and tone. [sound_slots_spec.py](sound_slots_spec.py) specifies it.

The check assembles two binaries: normal input and a test-only input fixture.
Both run real 6809 code in XRoar with nonzero startup RAM, on both targets.
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
- the mixer output

An unreachable checkpoint must not create a snapshot.

For each binary, the instruction trace checks 16,384 consecutive DAC writes
against the independent phase model. The trace also counts the instructions
between writes. The model sets a budget of 40 instructions for the frame work.

The measured counts are 11–30 for normal input and 11–38 for the fixture.
These are instruction counts, not cycle counts.

`verify_sound` measures the pitch of each WAV against the tone that the cycle
count predicts: 57 cycles per sample at 894,886.25 Hz. The measured pitch
must be within 15 Hz of that tone. The signal level must be nonzero.

On the pinned XRoar, both targets give 486.7 Hz for the low pitch and 973.3 Hz
for the high pitch.

## Failure controls

`scripts/coco_spec.py` runs these changed copies. Each one passes the memory
check and fails the full check:

- A muted mux (sound enable cleared) fails at frame 1 with "no tone".
- A constant DAC value (`lda #$80` before the sample store) fails the same way.
- A delay loop of 1,000 iterations after each 256 samples, on the CoCo 2 target,
  fails the instruction budget. Correct memory does not show timely samples.

## Limits

The mixer WAV shows that the emulated mux routes the DAC to XRoar's output at
the expected pitch. It does not prove host playback, audibility, distortion,
or audio quality on a real CoCo. The pitch check also does not prove evenly
spaced samples.

A bounded normal-speed GUI launch exited successfully, but nobody inspected
the display or listened to its output. A physical fire button remains untested.
No physical CoCo, CoCo 3, PAL, T1 VDG, or faster-clock result is claimed.

This example reproduces cooperative progress with a deliberately uneven schedule.
It does not reproduce the magazine's six-voice player.
