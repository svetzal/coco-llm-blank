# Sound during a costly redraw

This experiment compares two ways to generate sound while drawing a moving marker.
The cooperative build writes samples from its main loop.
The timer build writes them from a GIME fast interrupt handler.
Both builds run on the same emulated CoCo 3 to separate scheduling from
machine differences.

The result is useful for games: timer sound can keep progressing during drawing,
but its handler takes CPU time away from that drawing.
This is an original experiment, not a complete music engine.

## Run it

The experiment needs the starter's downloaded CoCo 3 firmware and native tools.
Its fixed target is NTSC, 128 KiB, 6809 at the slow clock, with compatibility
256×192 graphics. It does not select the faster clock to make the test pass.
Project notes keep their existing target.

From the repository root:

```sh
uv run python scripts/timer_sound.py check
uv run python scripts/timer_sound.py run
uv run python scripts/timer_sound.py run --heavy --revision 1987
```

The run command defaults to the 1986 GIME model. Close XRoar to stop it.
It uses direct DECB loading, not a disk or a BASIC-returning routine.
The visible marker is eight pixels wide and one row high.
There are no controls in this experiment.

## What is being compared

The two builds share the same oscillator and foreground drawing code.
A 16-bit phase advances by `$0800` for each sample. Its upper six bits feed
the DAC, while the DAC port's low bits retain their initialized values.

The foreground requests a redraw when the high byte of the sample counter changes.
The light build erases one byte and draws the marker at the next position.
The heavy build clears all 6,144 framebuffer bytes before drawing the marker.
It deliberately spends much more CPU time for the same completed picture.

The timer build can miss foreground deadlines while servicing audio.
It uses the latest observed sample block instead of queuing every missed redraw.
This experiment does not synchronize drawing to vertical blanking or prevent tearing.

## Interrupt and memory contract

Read the [timer findings](../../guidance/sound-research.md#coco-3-timer-experiment)
before changing register values.

- Tepolt, **Assembly Language Programming for the CoCo3**, PDF 47–53:
  FIRQ saves CC and PC automatically. The handler saves and restores A and B.
  It reads `$FF93` to acknowledge the GIME request, checks the timer flag,
  emits one sample, and returns with `RTI`.
- Tepolt, PDF 48 and 60: the FIRQ vector reaches the primary RAM jump table
  at `$FEF4`. The experiment installs a jump there and keeps fixed FExx RAM enabled.
  The handler, stack, and state remain mapped throughout execution.
- Tepolt, PDF 55–57: firmware copies ROM into RAM and establishes the executive
  mapping. This experiment retains that mapping and explicitly selects all-RAM mode.
  It does not support an arbitrary loader or bank-switching environment.
- Tandy, **Color Computer 3 Service Manual**, PDF 10–12:
  PIA sound control, GIME interrupt enables, and the timer registers.
  PIA interrupt sources and GIME IRQ sources are disabled. Only timer FIRQ is enabled.
- The same manual, PDF 18: the compatibility 256×192 mode uses SAM `110`
  and PIA video control bits `1111`. The framebuffer setup follows the original
  first-screen example. Full-byte markers do not depend on horizontal bit order.

Initialization uses `$CE` at `$FF90`, then `$DE` for the timer build.
These select compatibility graphics, MMU, fixed FExx RAM, standard SCS, and
32 KiB internal ROM mapping. `$DE` also enables GIME FIRQ output.
`$FF91=$20` selects the fast timer clock and executive task.
`$FF93=$20` enables only the timer source. CPU IRQ remains masked.

Timer reload is 510 (`$01FE`), written low byte first, then high byte.
The high-byte write starts the timer. The handler does not restart it.
The research guide explains why the manual's timer-clock value must not be
used directly and why the GIME revision changes the prediction.

CPU framebuffer addresses are `$0400–$1BFF`, with guards at `$03FF` and `$1C00`.
Code and initialized state start at `$3000`. Symbols record their exact extent.
The reserved stack is `$7E00–$7EFF`, growing down from `$7F00`.
In the tested 128 KiB mapping, these CPU addresses occupy the upper 64 KiB
of the raw XRoar RAM dump. The runner accounts for that offset.

## Measurement and checks

The check runs six cases: cooperative light/heavy, and timer light/heavy on
both GIME revisions. Each measurement lasts one emulated second from its first
sample checkpoint. Host acceleration does not change the selected CPU clock.

The trace checks every DAC value against an independent phase sequence.
The latest completed-frame snapshot checks marker position, all framebuffer
bytes, guards, and phase/counter consistency. An unreachable checkpoint must
not produce a snapshot. Missing samples or completed frames fail the check.

The specifications also remove interrupt acknowledgement in a test-only build.
That build fails the completed-frame check. This negative control shows
why acknowledging a request is part of making progress.

The measured results are recorded in `build/timer-sound/results.json`.
Traces, symbols, and snapshots stay beside it, outside Git.
See the research guide for the recorded comparison and its interpretation.

## Limits

The test measures average sample throughput, not individual sample intervals.
It does not establish zero jitter, an exact CPU-utilization percentage, or
an optimal sample rate. Instruction boundaries still affect interrupt latency.
The counters and handler calls themselves consume CPU time.

Automated runs disable audio output. Correct DAC values do not establish
correct sound routing, audible quality, or appearance on a display.
A bounded normal-speed GUI launch exited successfully, but nobody inspected
the screen or listened to it. No physical CoCo, PAL, 6309, or faster-clock result
is claimed.
This experiment does not exercise analog joystick reads or bank switching.
