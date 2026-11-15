# Play a tone from the main loop

This example plays a tone on the 6-bit DAC of the CoCo 1, 2 and 3. The main loop
writes each sample. After each block of 256 samples, the loop has one short
slot for frame work. The slot also changes the note.

The example does not do these things:

- read input
- use interrupts
- play music from a table
- use the single-bit sound output or ROM sound calls
- return to BASIC

A marker that moves along the screen is the context. It stands for the frame
work of a game.

## Choose a waveform and a note

The sample loop takes 41 cycles. At 894,886.25 Hz, that is 21,826 samples
each second. This is the slow CPU rate. The pitch is correct only at that
rate. On the CoCo 3, a write to `$FFD9` doubles the rate, and the tone goes
up by one octave.

A 16-bit phase adds the step on each sample. This formula gives
the tone:

```text
tone in Hz = 894,886.25 / 41 * step / 65,536
```

| Variant | Waveform | DAC values | Mask on the phase high byte | `LOW` step `$0800` | `HIGH` step `$1000` |
| --- | --- | --- | --- | --- | --- |
| (default) | Sawtooth | All 64 values | `$FC` | 682.1 Hz | 1,364.2 Hz |
| `square` | Square | 0 and 32 | `$80` | 682.1 Hz | 1,364.2 Hz |

- The sawtooth is the default because it uses all 64 values of the DAC.
- The square wave uses only phase bit 15, and half of the DAC range.
- Both masks cost the same cycles, so the pitch does not change.
- A larger step gives a higher note. Keep the step below `$8000`, which gives
  only two samples in each cycle of the wave.

The slot budget is the main choice. The work in the slot delays one sample.
This example allows 40 instructions between two DAC writes.
Its largest gap is 24 instructions.
More work in the slot makes the sound uneven and lowers the pitch.

Other ways to play sound:

- A timer interrupt writes the samples while the main loop draws. This
  needs CoCo 3 hardware. Read [timer sound](../timer-sound/README.md).
- A short effect can stop the game until it ends. Read
  [collect room](../collect-room/README.md).

## Play the tone

The example is the four `>>> EXAMPLE` parts of [main.asm](main.asm):

1. At `start`, mask the interrupts. Nothing must take CPU time between two
   samples. An enabled interrupt, such as the 60 Hz field-sync IRQ, adds a
   gap at a time that the loop cannot plan.

2. Make `$FF20` bits 7 to 2 outputs. Clear `$FF21` bit 2 to select the
   direction register. Set bits 7 to 2. Set `$FF21` bit 2 again. Keep bits 1
   and 0: bit 1 is the RS-232 output. Save their value in `low_bits`.

3. Select the DAC in the audio mux. Clear `$FF01` bit 3 (SEL 1) and `$FF03`
   bit 3 (SEL 2). Set `$FF23` bit 3 (SNDEN). Keep the other control bits.

4. At `tick`, add `step` to `phase`. Mask the high byte with `WAVE` and
   add `low_bits`. Write the result to `$FF20` at `sample`. The `divider`
   counts 256 samples.

   In the slot after each block, increment `blocks` and choose the next
   step. Each note lasts 16 blocks.

The `--- CONTEXT` blocks clear the screen and the state.
They show a 256×192 two-colour screen with the setup of
[first screen](../first-screen/README.md).
After each block, they move the marker one byte along row 96.
The check takes its snapshot at `frame_ready`.
[expected.py](expected.py) is only check context.

The example runs on three NTSC targets with a 6809 at the slow rate:

| Target | XRoar machine | RAM | Firmware |
| --- | --- | --- | --- |
| `coco1` | `cocous` | 32 KiB | Color BASIC 1.1 |
| `coco2` | `cocous`, CoCo 2 boards 26-3134/26-3136 | 64 KiB | Color BASIC 1.2 |
| `coco3` | `coco3`, GIME 1986 | 128 KiB | CoCo 3 ROM |

The program and the check model are the same on the three targets:

- The CoCo 2 boards and the CoCo 3 put the DAC and the audio mux in one IC.
  The register addresses and bits are the same as on the CoCo 1.
- The CoCo 3 manual gives the slow CPU rate as 0.89 MHz, a rounded value.
  The model uses 894,886.25 Hz. The 15 Hz pitch tolerance covers the
  difference.
- The context writes `$FFD8`, which selects the slow rate. At reset, the
  CoCo 3 ROM also clears all SAM registers, so BASIC starts at the slow rate.
- On the CoCo 3, the check reads the screen at offset `$10400` of the RAM
  snapshot. The `screen` setting of the `coco3` target in
  [coco.toml](coco.toml) gives this offset.

## Hear and check each variation

Start the commands in the starter folder. Close XRoar to stop the tone.

```sh
# Sawtooth, CoCo 1
uv run python scripts/coco.py run examples/sound-slots
# Square, CoCo 1
uv run python scripts/coco.py run examples/sound-slots --variant square
# Sawtooth, CoCo 2
uv run python scripts/coco.py run examples/sound-slots --target coco2
# Square, CoCo 2
uv run python scripts/coco.py run examples/sound-slots --target coco2 \
  --variant square
# Sawtooth, CoCo 3
uv run python scripts/coco.py run examples/sound-slots --target coco3
# Square, CoCo 3
uv run python scripts/coco.py run examples/sound-slots --target coco3 \
  --variant square
```

To check both variations on the three targets, use this command:

```sh
uv run python scripts/coco.py check examples/sound-slots
```

The check needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
`[capture] audio` in [coco.toml](coco.toml) records XRoar's mixer output at
each checkpoint.

The check compares these items with [expected.py](expected.py):

- Each of the first 16,384 DAC writes, from an instruction trace. The model
  calculates each value from the phase, the step and the waveform.
- The largest number of instructions between two DAC writes, against the
  budget of 40.
- The pitch of the mixer output at blocks 1, 16, 17, 32, 33, 63 and 64. The
  model calculates it from the loop's cycle count. The pitch must be within
  15 Hz. The check measures the pitch only after at least 100 ms of one note.
- All 6,144 screen bytes, for the context.

Three negative controls in `scripts/coco_spec.py` change a copy of the
example. Each copy passes the screen check and fails the full check:

| Change | Result |
| --- | --- |
| Clear SNDEN instead of setting it | Block 1: no tone |
| Write a constant `$80` to the DAC | Block 1: no tone |
| On CoCo 2, add a delay of 1,000 loops in the slot | The slot exceeds the budget |

The mixer output is XRoar's digital signal before the host audio driver. The
check does not prove the sound on a television or a physical CoCo.

The pitch check does not prove that the samples are evenly spaced. The
instruction count is not a cycle count.

## Sources

Read these pages before you change a register value. Use
[reference lookup](../../guidance/starter/references.md) to get them. The
[sound guide](../../guidance/techniques/sound.md) gives the source links.

- Tandy, *Color Computer Technical Reference Manual*:
  - PDF 13: `$FF01` bit 3 is SEL 1 and `$FF03` bit 3 is SEL 2.
  - PDF 14: `$FF20` bits 2 to 7 are the 6-bit DAC, and bit 1 is the RS-232
    output. `$FF21` bit 2 selects the direction register. `$FF23` bit 3
    enables six-bit sound.
  - PDF 26: the CPU clock is 14.31818 MHz divided by 16.
  - PDF 37: the 60 Hz field-sync interrupt.
  - PDF 38, Table 4: SNDEN 1 with SEL 1 and SEL 2 at 0 selects the DAC.
- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
  PDF 37–38: select inputs `00` choose the DAC, and SNDEN must be high.
- Tandy, *Color Computer 3 Service Manual*:
  - PDF 9: `$FF01` bit 3 is SEL 1 and `$FF03` bit 3 is SEL 2.
  - PDF 10: `$FF20` bits 2 to 7 are the 6-bit DAC, and bit 1 is the RS-232
    output. `$FF21` bit 2 selects the direction register. `$FF23` bit 3
    enables sound.
  - PDF 31: the CPU clock is 0.89 MHz or 1.78 MHz.
  - PDF 42–43: Sel B 0 and Sel A 0 select the DAC, and SNDEN must be high.
- Tepolt, *Assembly Language Programming for the CoCo3*:
  - PDF 56, step 14: the reset program clears all SAM registers.
  - PDF 58: BASIC's memory map, for the screen offset.
  - PDF 62: a write to `$FFD8` selects the slow CPU rate, and a write to
    `$FFD9` selects the fast rate.
- Leventhal, *6809 Assembly Language Programming*, Appendix C, PDF 553–555:
  the cycle count of each instruction in the sample loop.
