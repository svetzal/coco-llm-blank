# Sound during a costly redraw

This example compares two ways to generate sound while the program draws a
moving marker.
The cooperative build writes samples from its main loop.
The timer build writes them from a handler for the GIME fast interrupt.
Both builds run on the same emulated CoCo 3 to separate scheduling from
machine differences.

The result is useful for games. Timer sound can keep progressing during drawing,
but its handler takes CPU time away from that drawing.
This is an original example. It is not a complete music engine.

## Run it

The example needs the starter's downloaded CoCo 3 firmware and native tools.
Its fixed target is NTSC, 128 KiB, 6809 at the slow clock, with compatibility
256×192 graphics. It does not select the faster clock to make the test pass.
Project notes keep their existing target.

From the repository root:

```sh
uv run python scripts/coco.py run examples/timer-sound --variant timer
uv run python scripts/coco.py run examples/timer-sound --variant timer-heavy \
  --target coco3-1987
```

The run command defaults to the 1986 GIME model, the first target in
[coco.toml](coco.toml).
Without `--variant` it runs the cooperative light build.
Close XRoar to stop it.
It uses direct DECB loading, not a disk or a BASIC-returning routine.

The visible marker is eight pixels wide and one row high.
There are no controls in this example.

## What is being compared

The two builds share the same oscillator and foreground drawing code.
A 16-bit phase advances by `$0800` for each sample.
Its upper six bits feed the DAC.
The low bits of the DAC port keep their initialized values.

The foreground requests a redraw when the high byte of the sample counter changes.
The light build erases one byte and draws the marker at the next position.
The heavy build clears all 6,144 framebuffer bytes before it draws the marker.
It deliberately spends much more CPU time for the same completed picture.

The timer build can miss foreground deadlines while it services audio.
It uses the latest sample block that it observed instead of queuing every
missed redraw.
This example does not synchronize drawing to vertical blanking or prevent tearing.

## Interrupt and memory contract

Read the [timer-clock conflict](../../guidance/techniques/sound.md#resolve-the-timer-clock-conflict)
before you change register values.

- Tepolt, **Assembly Language Programming for the CoCo3**, PDF 47–53:
  FIRQ saves CC and PC automatically. The handler saves and restores A and B.
  It reads `$FF93` to acknowledge the GIME request.
  It checks the timer flag, emits one sample, and returns with `RTI`.

- Tepolt, PDF 48 and 60: the FIRQ vector reaches the primary RAM jump table
  at `$FEF4`. The example installs a jump there and keeps fixed FExx RAM enabled.
  The handler, stack, and state remain mapped throughout execution.

- Tepolt, PDF 55–57: firmware copies ROM into RAM and establishes the executive
  mapping. This example keeps that mapping and explicitly selects all-RAM mode.
  It does not support an arbitrary loader or bank-switching environment.

- Tandy, **Color Computer 3 Service Manual**, PDF 10–12:
  PIA sound control, GIME interrupt enables, and the timer registers.
  PIA interrupt sources and GIME IRQ sources are disabled. Only timer FIRQ is enabled.

- The same manual, PDF 18: the compatibility 256×192 mode uses SAM `110`
  and PIA video control bits `1111`. The framebuffer setup follows the original
  first-screen example. Full-byte markers do not depend on horizontal bit order.

Initialization uses `$CE` at `$FF90`, then `$DE` for the timer build.
These values select:

- compatibility graphics
- MMU
- fixed FExx RAM
- standard SCS
- 32 KiB internal ROM mapping

`$DE` also enables GIME FIRQ output.
`$FF91=$20` selects the fast timer clock and executive task.
`$FF93=$20` enables only the timer source. CPU IRQ remains masked.

Timer reload is 510 (`$01FE`).
The example writes the low byte first, then the high byte.
The high-byte write starts the timer. The handler does not restart it.

The sound guide explains why you must not use the manual's timer-clock value
directly. It also explains why the GIME revision changes the prediction.

CPU framebuffer addresses are `$0400–$1BFF`, with guards at `$03FF` and `$1C00`.
Code and initialized state start at `$3000`. Symbols record their exact extent.
The reserved stack is `$7E00–$7EFF`. It grows down from `$7F00`.

In the tested 128 KiB mapping, these CPU addresses occupy the upper 64 KiB
of the raw RAM dump from XRoar. The `screen = 0x10400` setting in `coco.toml` and
the model in `expected.py` account for that offset.

## Measurement and checks

```sh
uv run python scripts/coco.py check examples/timer-sound
```

The check assembles all four builds and runs each on both GIME revisions.
It compares completed redraws 1–3 with the independent model in
[expected.py](expected.py). The comparison covers marker position, all
framebuffer bytes, guards, and phase/counter consistency.
An unreachable checkpoint must not produce a snapshot.

`[capture] audio` in [coco.toml](coco.toml) also records XRoar's mixer output
at each checkpoint. This needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
`verify_sound` analyses only the program's own sound: at most the last 150 ms,
and never more than the least time the program can have run.

The model predicts the sound from cycle counts and the timer period, not from
a capture:

- Cooperative builds: 70 cycles for each sample (`JSR emit` 8, `emit` 49,
  loop test 13), a 399.5 Hz tone. [Leventhal, Appendix C, PDF 553–555][leventhal]
- Timer builds: one sample for each timer expiry, a 218.5 Hz tone. The timer
  counts the reload value plus 2 (1986) or plus 1 (1987), at 279.365 ns for
  each count. [Kowalski][kowalski]
- The heavy clear: 13 cycles for each of 6,144 bytes (`STA ,X+` 6, `CMPX #` 4,
  `BLO` 3), 79,872 cycles or 89.3 ms. [Leventhal, PDF 552–555][leventhal]

`verify_sound` then requires these results:

- Cooperative light, timer and timer-heavy builds: no pause longer than 1 ms.
  Where at least 50 ms of sound is available, the pitch is within 15 Hz of
  the predicted tone.
- Cooperative heavy build: the sound stops for at least 95% of the clear.

On the pinned XRoar, both revisions measure 403.1 Hz for the cooperative light
build and 215.6–220.4 Hz for the timer builds. The longest pause is 0.16 ms.
The cooperative heavy build stops for 89.4 ms at every checkpoint. The timer
keeps the tone through the clear, but the clear itself still takes CPU time.

`scripts/coco_spec.py` runs two changed copies as failure controls:

- Masking FIRQ during the heavy clear passes the memory check. It fails the
  sound check, because the tone stops.
- A handler that does not read `$FF93` (`NO_ACK`) never completes redraw 1.
  Acknowledging the request is part of making progress.

## Limits

The check does not measure individual sample intervals, CPU utilization, or
an optimal sample rate. The pitch check does not prove evenly spaced samples.
Instruction boundaries still affect interrupt latency. The counters and
handler calls themselves consume CPU time.

The mixer WAV is XRoar's digital output before any host audio driver. It does
not establish host playback, audible quality, or appearance on a display.

A bounded normal-speed GUI launch exited successfully, but nobody inspected
the screen or listened to it. No physical CoCo, PAL, 6309, or faster-clock result
is claimed.

This example does not exercise analog joystick reads or bank switching.

[leventhal]: https://colorcomputerarchive.com/repo/Documents/Books/6809%20Assembly%20Language%20Programming%20%28Lance%20Leventhal%29.pdf#page=553
[kowalski]: https://www.6809.org.uk/twilight/sock/gime.html
