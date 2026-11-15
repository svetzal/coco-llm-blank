# Play sound from a timer interrupt

This example writes DAC samples from the timer interrupt of the CoCo 3 GIME.
The timer interrupts the main loop at a fixed rate. The FIRQ handler writes one
sample and returns. The main loop is free to draw, and the sound continues
while it draws.

The example does not do these things:

- run on a CoCo 1 or CoCo 2, which have no GIME timer
- read input
- play music, or change the note
- use the IRQ, bank switching or the faster CPU clock
- return to BASIC

The context shows a 256×192 screen and moves a marker after each block of 256
samples. Two variants clear the full screen before each move, to make the
redraw costly. Two variants write the samples from the main loop, for
comparison.

## Choose who writes the next sample

| Variant | Writer of the samples | Redraw | Sample rate | Tone | Sound during the redraw |
| --- | --- | --- | --- | --- | --- |
| (default) | Timer FIRQ | Move the marker | 6,991 Hz | 218.5 Hz | Continues |
| `heavy` | Timer FIRQ | Clear 6,144 bytes, then move | 6,991 Hz | 218.5 Hz | Continues |
| `cooperative` | Main loop | Move the marker | 12,784 Hz | 399.5 Hz | Stops for the move |
| `cooperative-heavy` | Main loop | Clear 6,144 bytes, then move | 12,784 Hz | 399.5 Hz | Stops for 89.3 ms |

- Use the timer when a redraw can take longer than the gap between two
  samples. The default build is the practice.
- The handler takes CPU time from the main loop. A costly redraw still takes
  the same cycles, and fewer redraws complete.
- Use the main loop when the work between two samples is short and known.
  The [sound slots](../sound-slots/README.md) example shows that practice on
  the CoCo 1/2.

Each tone is the sample rate divided by 32. The phase step is `$0800`, so the
sawtooth repeats every 32 samples.

The timer reload value sets the sample rate. The example uses 510 (`$01FE`).
With the fast timer input, one count is 279.365 ns. A period is the reload
value plus 2 counts on the 1986 GIME, or plus 1 count on the 1987 GIME:

```text
sample rate in Hz = 14,318,180 / 4 / (reload + 2)
```

A smaller reload value gives a higher sample rate and more handler calls. Read
the [timer-clock conflict](../../guidance/techniques/sound.md#resolve-the-timer-clock-conflict)
before you change it. The Tandy manual gives a different timer clock.

The main loop writes a sample every 70 cycles at 894,886.25 Hz: `JSR emit` 8,
`emit` 49, and the loop test 13. The full clear takes 13 cycles for each of
6,144 bytes: 79,872 cycles, or 89.3 ms.

## Start the timer and write the samples

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm):

1. At `start`, mask the interrupts. `ORCC #$50` sets both I (IRQ) and F
   (FIRQ). IRQ stays masked for the full run.

2. Start the timer interrupt. The `COOPERATIVE` builds leave out this part.
   1. Turn off the PIA FIRQ sources: clear `$FF21` bit 0 (CD) and `$FF23`
      bit 0 (cartridge). Read `$FF20` and `$FF22` to clear their flags.
   2. Write `JMP handler` to the FIRQ jump-table entry at `$FEF4`.
   3. Write `$DE` to `$FF90`. This is BASIC's value `$CE` with FEN (bit 4)
      set.
   4. Write `$20` to `$FF91` to select the fast timer input and keep the
      executive task.
   5. Write `$20` to `$FF93` to make the timer the only FIRQ source. Read
      `$FF93` to release a request that waits.
   6. Write the reload value: `$FE` to `$FF95`, then `$01` to `$FF94`. The
      write to `$FF94` starts the timer.
   7. Unmask FIRQ with `ANDCC #$BF`.

3. At `handler`, save A and B, because FIRQ saves only CC and PC. Read `$FF93`
   to release the request. If bit 5 (timer) is set, call `emit`. Restore A
   and B, then return with `RTI`. The timer reloads itself.

The `--- CONTEXT` blocks do these things:

- clear the screen and the state, and show the screen with the RG6 setup of
  [first screen](../first-screen/README.md)
- set up the DAC as in [sound slots](../sound-slots/README.md)
- in the main loop, redraw after each new block of 256 samples
- at `emit`, write one sample of a sawtooth wave to `$FF20`

The check takes its snapshot at `frame_ready`. [expected.py](expected.py) is
only check context.

The program keeps the memory map that BASIC sets: the executive task, all-RAM
mode and the jump table in RAM at `$FEEE`–`$FEFF`.
It does not support a loader that changes that map.

In this 128 KiB map, CPU address `$0000` is at offset `$10000` of XRoar's RAM
snapshot. The `screen = 0x10400` setting in [coco.toml](coco.toml) uses that
offset.

Both targets are an NTSC CoCo 3 with 128 KiB and a 6809 at the slow clock:

| Target | GIME | Timer period |
| --- | --- | --- |
| `coco3-1986` (default) | 1986 | Reload value plus 2 counts |
| `coco3-1987` | 1987 | Reload value plus 1 count |

## Hear and check each variation

Start the commands in the starter folder. Close XRoar to stop the program.

```sh
# Timer FIRQ, light redraw
uv run python scripts/coco.py run examples/timer-sound
# Timer FIRQ, costly redraw
uv run python scripts/coco.py run examples/timer-sound --variant heavy
# Main loop, light redraw
uv run python scripts/coco.py run examples/timer-sound --variant cooperative
# Main loop, costly redraw
uv run python scripts/coco.py run examples/timer-sound \
  --variant cooperative-heavy
```

Add `--target coco3-1987` to a command to use the 1987 GIME.

To check all four variations on both GIME revisions, use this command:

```sh
uv run python scripts/coco.py check examples/timer-sound
```

The check needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
`[capture] audio` in [coco.toml](coco.toml) records XRoar's mixer output at
redraws 1, 2 and 3. The check compares these items with
[expected.py](expected.py):

- The tone. The model calculates the pitch from the cycle counts and the timer
  period. Where at least 50 ms of sound is available, the pitch must be within
  15 Hz.
- The pauses. In the timer builds and the `cooperative` build, the tone must
  not pause for longer than 1 ms. In the `cooperative-heavy` build, the tone
  must stop for at least 95% of the clear.
- The phase and the sample count, which must agree.
- All 6,144 screen bytes, for the context.

The check writes the measured pitch and pauses to
`build/timer-sound/<target>-results.json`.

Two negative controls in `scripts/coco_spec.py` change a copy of the example:

| Change | Result |
| --- | --- |
| Mask FIRQ during the clear | The screen check passes. The sound check fails: no tone. |
| The handler does not read `$FF93` | Redraw 1 never completes. |

The check does not measure the time between two samples or the CPU time of
the handler. The pitch check does not prove that the samples are evenly
spaced.

The mixer output is XRoar's digital signal before the host audio driver.
The check does not prove the sound on a television or a physical CoCo.

## Sources

Read these pages before you change a register value.
Use [reference lookup](../../guidance/starter/references.md) to get them.
The [sound guide](../../guidance/techniques/sound.md) gives the source links.

- Tepolt, *Assembly Language Programming for the CoCo3*:
  - PDF 47: FIRQ pushes only CC and PC.
  - PDF 48: the FIRQ vector leads to the jump-table entry at `$FEF4`.
  - PDF 49–51: the bits that enable GIME FIRQ (Init0 bit 4), select the
    timer input (Init1 bit 5) and enable the timer source (FIRQEN bit 5). A
    read of FIRQEN releases the request.
  - PDF 52–53: the order of the setup steps and of the handler.
  - PDF 55–57: BASIC's map, all-RAM mode, the jump table in RAM, and Init0
    `$CE`.

- Tandy, *Color Computer 3 Service Manual*:
  - PDF 9–10: the PIA bits, including the FIRQ enables and sound enable.
  - PDF 11: `$FF90` to `$FF93`.
  - PDF 12: the 12-bit timer starts on the write to `$FF94` and reloads.

- Leventhal, *6809 Assembly Language Programming*, Appendix C, PDF 553–555:
  the cycle counts, and `$7E` for `JMP` extended.

- John Kowalski, *GIME register reference*, `$FF91` and `$FF94`–`$FF95`:
  279.365 ns for each count, and the period on each GIME revision. This
  reference is outside the archive.

- Tim Lindner, "CoCo 3 GIME Timer Tests", his web log, 12 May 2021,
  <https://tlindner.macmess.org/?p=762>
  ([Wayback copy](http://web.archive.org/web/20260519163613/https://tlindner.macmess.org/?p=762)),
  read 15 November 2026. The report of one person, with a video of a real
  1986 GIME. In his TEST2, the timer with TINS set agrees with 279.365 ns
  for each count, not with 70 ns. No such report exists for the 1987 GIME.
  The [timer-clock conflict](../../guidance/techniques/sound.md#resolve-the-timer-clock-conflict)
  gives the details.
