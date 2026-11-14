# Keep sound playing while the game works

Read this before combining sound, drawing, and controls. Start by deciding
which task supplies the next audio sample and what can delay that task.
A music routine that occupies the CPU does not automatically become background music.

## Identify the sound hardware

The stock six-bit DAC receives sample values from the CPU. On CoCo 1, its
bits occupy `$FF20` bits 2–7. Analog joystick conversion shares the DAC and
audio selection hardware. Reading an axis can therefore change the sound path.
Fire buttons are digital inputs and do not need that conversion.
[Tandy CoCo 1 technical manual, PDF 13–14 and 37–38][coco1]

The named CoCo 2 NTSC boards integrate the DAC and selection functions.
The shared joystick/audio problem remains. [Tandy CoCo 2 manual, PDF 37][coco2]
CoCo 3 retains shared DAC and selection hardware too.
[Tandy CoCo 3 manual, PDF 42–43][coco3dac]

Our recommendation is to inventory every routine that writes these ports
before combining input and audio. A tested fire-button reader is not evidence
that analog joystick reading can run without disturbing playback.

The one-bit output is another CPU-driven path. On CoCo 1 it uses `$FF22`
bit 1, with direction and mux setup. Other bits also control video.
Preserve those fields when changing the sound bit.
[Tandy CoCo 1 technical manual, PDF 14 and 38][coco1]

## Understand what a published player proves

William P. Nee's **"Machine Language Made BASIC, Part XII: And the Music
Played On," The Rainbow, June 1989**, explains waveform mixing and note duration.
Its player masks interrupts and repeatedly writes samples to the DAC.
The examined loop does not service game drawing or controls.
[Printed 68 / PDF 72, continuation PDF 76–79][nee]

This is useful synthesis research, but the original player was not built here.
Its prose and listing disagree about a curve address. Read the listing image
and reconcile the memory layout before adapting it. The starter's experiments
use an original, simpler oscillator. They copy neither its player nor its score.

## Choose short effects or continuous music

For an explosion or pickup sound, a small sample table is a useful starting
point. Barden separates the table bounds, repeat count, and delay between
samples. His envelope diagrams show how an effect can grow or fade.
The published routine plays the whole effect before returning. It does not
keep a game moving during playback. [Barden, PDF 248–251 and 255][barden]

Our recommendation is to decide whether that pause is acceptable before
choosing the player. For continuous movement, advance sound through a scheduler
such as the experiments below. Give original sound assets an explicit format:
Barden's ordinary 0–63 amplitude bytes need alignment for the DAC, while his
cassette ROM example already contains aligned bytes. Applying both conversions
would corrupt the values. [Barden, PDF 246 and 251][barden]

ROM SOUND and PLAY calls can be convenient for a BASIC-hosted prototype.
Nee's examples require particular workspace and register handling; his PLAY
example saves the BASIC text pointer and runs from BASIC. They do not establish
a portable standalone game interface. Verify the installed ROM and calling
context before using any address, and measure the pause caused by each call.
[Nee, March 1989, PDF 30–32][notes]

## Treat cartridge sound as an optional target

Clemens's complete review describes separate processing and generators in
Tandy's Sound/Speech cartridge. It is an expansion choice, not stock-machine
capability. [Hot CoCo, June 1985, printed 73–76 / PDF 75–78][cartridge]

The primary manual exposes a practical trap. Before sending each byte to
`$FF7E`, wait until status bit 7 is high. A byte sent while that bit is low is
lost. Bits 6 and 5 report speech and sound activity, but are temporarily invalid
after a command starts. An immediate "inactive" result is not evidence that
playback finished. [Tandy cartridge manual, PDF 10–11][speechmanual]

Our proposed game integration would preload effects and send commands in small
steps as the cartridge becomes ready. It must track command acceptance separately
from playback state. The manual gives no single startup delay for every command,
so measure this on the chosen target before promising uninterrupted gameplay.
Its timing also assumes the normal CoCo clock. No cartridge driver or latency
test exists in this starter. [Tandy cartridge manual, PDF 8 and 11][speechmanual]

## Try cooperative scheduling for small tasks

The original [sound-slots example](../../examples/sound-slots/README.md) interleaves
samples with marker movement and fire-button reads. Its target is CoCo 1,
NTSC, 32 KiB, and normal-clock 6809. It masks interrupts and avoids analog axes.

After the CoCo 1 setup, run from the repository root:

```sh
uv run python scripts/sound_slots.py check
uv run python scripts/sound_slots.py run
```

The XRoar checks compare sample values, screen memory, and scripted button
states with independent expectations. Ordinary sample gaps contain 11 traced
instructions. Frame work increases that to 30. Those are instruction counts,
not cycle counts or a measure of audible quality. A later
[DAC interval measurement](validation/audio-timing.md) observed
57–138 slow CPU cycles between writes in this example.

The practical consequence is that more foreground work can slow playback.
Use this example to expose that coupling before adding a whole game.
The input fixture does not prove physical joystick operation.
A separate CoCo 2 adaptation now supplies bounded evidence, described below.

## Bound foreground work on CoCo 2

The separate [CoCo 2 report](validation/sound-coco2.md) and
[reproduction guide](../../experiments/sound-coco2/README.md) adapt the original
sound-slots example without changing it. The target is explicit NTSC, 64 KiB,
normal-clock 6809, non-T1 MC6847, with verified BASIC 1.2/Extended BASIC 1.1.
The reviewed scoped run passes 19 tests with 98.13% Python statement/branch
coverage. Each of three cases passes seven checkpoints; every final run checks
16,384 samples, 16,383 modeled DAC intervals and all 6,144 framebuffer bytes.

Released-input gaps are 57–138 slow cycles; scripted-input gaps are 57–158.
Delayed foreground work preserves samples and state but adds exactly 80,003
slow cycles at each of 63 inter-block boundaries, reaching a maximum gap of
80,161 cycles. A regression shifts a boundary while preserving the total delay
and requires rejection. Correct state alone does not establish timely samples.

Scripted cases substitute logical input after the real PIA read. They do not
exercise OS events, a physical button or the keyboard experiment's matrix path.
Application updates are not video frames. These finite modeled intervals supply
no worst-case, listening, rendered-output, analog-voltage or hardware evidence.

## Use CoCo 3 timer interrupts when drawing delays samples

CoCo 3 provides a programmable timer and interrupt routing.
Tepolt explains IRQ/FIRQ handling, acknowledgement, and initialization on
PDF 47–53. FIRQ automatically saves less state than IRQ, so the handler must
preserve the other registers it changes. [Tepolt][interrupts]
Tandy describes the timer and enables on PDF 10–12.
[Tandy CoCo 3 manual][timer]

The original [timer-sound example](../../examples/timer-sound/README.md) compares
cooperative and timer scheduling on the same CoCo 3. It uses NTSC, 128 KiB,
a slow-clock 6809, and a fixed memory mapping.
Read that example's setup and memory contract before running it:

```sh
uv run python scripts/timer_sound.py check
uv run python scripts/timer_sound.py run
uv run python scripts/timer_sound.py run --heavy --revision 1987
```

Under a full-screen clear, both tested GIME revisions retain their predicted
timer-driven sample throughput. Completed redraws fall from 27 to 2 in the
measured second. Interrupt-driven sound consumes CPU time. It does not make
drawing free. The cooperative case loses audio throughput under the same load.
These are results from our experiment, not benchmarks published by Tepolt.

The checks cover every DAC value and the latest completed framebuffer.
A missing-acknowledgement build fails the expected progress check.
These checks establish bounded emulator behaviour. The later
[eleven-case timing experiment](validation/audio-timing.md)
measured individual DAC intervals: the tested timer cases ranged from 123 to
134 slow CPU cycles under light load and 123 to 133 under heavy load.
Stable average throughput therefore does not mean evenly spaced writes.
These finite windows are not worst-case bounds or evidence of sound quality,
physical GIME timing, or interrupt safety during bank changes. The linked
record provides controls and tracked fresh-clone reproduction instructions.

## Check the emulator's produced audio

The independently reviewed [audio-output validation](validation/audio-output.md)
and [reproduction procedure](../../experiments/audio-output/README.md) now cover
CoCo 1 sound-slots and its CoCo 2 adaptation. Published fixes add capture
completeness and build-provenance checks; the revised scoped suite passes
33 tests with 95.44% combined statement/branch coverage.

A private XRoar build captures signed PCM from the digital mixer's output
callback, before any host audio driver. Independent pitch and duration
expectations, muted-mux and constant-DAC controls, and whole-fragment-loss
checks test a boundary beyond DAC writes. The report distinguishes the earlier
captures from the rerun with verified provenance and completeness checks.
This does not test the CoCo 3 timer example, host playback, listening quality
or physical audio output. Use the report's exact configurations and controls
before extending that claim to another workload.

## Resolve the timer-clock conflict explicitly

Tandy PDF 12 and Tepolt PDF 50 describe a fast clock near 14 MHz.
John Kowalski's later **GIME register reference**, under `$FF91` and
`$FF94–$FF95`, gives about 3.58 MHz and revision-dependent reload offsets.
The experiment uses that later account. [Kowalski's reference][kowalski]

XRoar 1.12.1 models the later account in `src/tcc1014.c`, including
`schedule_timer` and `tcc1014_variant`. This corroborates the emulator
prediction, not physical hardware. [XRoar source release][xroar]
The [research record](research/sound.md#coco-3-timer-experiment)
records the disagreement and the tested revision settings.

Do not silently replace one cited clock with another. Record which account
your timing calculation uses and check it against the target.

## Apply the findings to a game

These are our next implementation steps, not a completed music engine:

1. Choose the target hardware and a sample-rate budget.
2. Measure the worst drawing workload with audio enabled.
3. Test press, hold, and release behaviour for each control path.
4. Check every handler's register preservation and acknowledgement.
5. Check handler accessibility before introducing banked assets.
6. Listen to the running result and inspect the display.

The sound experiments have no confirmed listening or display inspection.
The CoCo 1/2 PCM capture establishes modeled mixer output; successful execution
and correct memory alone do not establish even that audio boundary.
For banked memory, read [scrolling and memory](scrolling.md#keep-interrupt-code-reachable).
For complete measurements and source exclusions, read the
[sound research notes](research/sound.md).

## Sources and provenance

- Tandy, *Color Computer Technical Reference Manual*, PDF 13–14 and 37–38
  (printed 6–7 and 30–31). Resource `coco1-technical`. [Archive][coco1]
- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
  printed/PDF 37. Resource `coco2-service`. [Archive][coco2]
- Tandy, *Color Computer 3 Service Manual*, printed/PDF 10–12 and 42–43.
  Resource `coco3-service`. [Archive][timer]
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 47–53 and 60. Resource `tepolt-coco3`. [Archive][interrupts]
- William P. Nee, "Machine Language Made BASIC, Part XII: And the Music
  Played On." *The Rainbow*, June 1989, printed 68 / PDF 72; continuation
  PDF 76–79. Resource `rainbow-1989-06`. [Archive][nee]
- Gary W. Clemens, "Sounding Out Tandy's Sound/Speech Cartridge." *Hot CoCo*,
  June 1985, printed 73–76 / PDF 75–78; complete review examined.
  Resource `hotcoco-1985-06`. [Archive][cartridge]
- William Barden Jr., "Listening to Your CoCo with Assembly Language."
  *The Rainbow*, March 1986, printed 237–240, 244, 246, 248–249, 252–253;
  PDF 239–242, 246, 248, 250–251, 254–255. Complete article read. [Archive][barden]
- William P. Nee, "Machine Language Made BASIC, Part IX: Let There Be Music."
  *The Rainbow*, March 1989, printed/PDF 30–32. Complete article read. [Archive][notes]
- Tandy, *Color Computer Speech/Sound Cartridge*, archive copy,
  PDF/printed 8–11 and 15. Selected interface reading; no driver validation.
  [Archive][speechmanual]
- John Kowalski (SockMaster), *GIME register reference*, register sections
  `$FF91`, `$FF94–$FF95`. Supplemental author reference outside the archive.
  [Author reference mirror][kowalski]
- *XRoar 1.12.1 source release*, `src/tcc1014.c`.
  Supplemental emulator implementation, not a hardware specification. [Source][xroar]

The original examples, runners, and specifications contain the measurement
procedures. Their READMEs link those files and identify the tested configurations.
The earlier research inspired the questions. These examples are our work,
not reproductions of the magazine programs.

[coco1]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>

[coco2]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=37>

[coco3dac]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=42>

[timer]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=10>

[interrupts]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=47>

[nee]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2008%20No.%2011%20-%20June%201989.pdf#page=72>

[cartridge]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20(OCR)/HotCoCo-1985-06.pdf#page=75>

[kowalski]: https://www.6809.org.uk/twilight/sock/gime.html

[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz

[barden]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2005%20No.%2008%20-%20March%201986.pdf#page=248>

[notes]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2008%20No.%2008%20-%20March%201989.pdf#page=30>

[speechmanual]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Speech-Sound%20Cartridge%20(Tandy).pdf#page=10>
