# Sound while a game runs

Load this guide before combining sound, animation, and controls.
The main question is how often the CPU must service each task.
A music player with several voices does not necessarily leave time for a game.

## Choose the sound path

| Path | What the examined sources establish | Game-development consequence |
| --- | --- | --- |
| Stock six-bit DAC | CPU supplies samples; analog joystick conversion uses the same DAC and selection hardware. | Schedule joystick conversion deliberately. Do not call an analog reader during playback without checking its writes. |
| Stock one-bit output | Separate PIA output; its direction must be configured. | Simpler amplitude choices, but the CPU still supplies transitions. It is not an autonomous tone generator. |
| Cassette audio | An external signal can reach the television through the sound mux. | Animation with cassette music does not demonstrate software synthesis alongside gameplay. |
| Sound/Speech cartridge | Separate processor and generators, described in the Hot CoCo review. | Investigate as an explicit expansion target. Do not present its capabilities as stock CoCo hardware. |

These are distinct mechanisms. Name the mechanism before borrowing a technique.

## Hardware evidence by machine

### CoCo 1

Read Tandy's **Color Computer Technical Reference Manual**, resource
`coco1-technical`, PDF 13–14 and 37–38 (printed 6–7 and 30–31).
[Archive manual][coco1]. The register tables and sound-selection table were
checked as page images.

The DAC uses bits 2–7 at `$FF20`. The audio mux selects DAC sound when both
selection bits are zero and sound enable is set. These controls share the
joystick circuitry. Analog joystick conversion changes DAC values while
comparing them with the joystick voltage.

Fire buttons are different. They share keyboard input rows and are active low.
They do not need analog conversion. Keyboard column selection still matters:
read the keyboard discussion before combining keys and fire buttons.

The one-bit output is bit 1 at `$FF22`. The manual says to configure that pin
as an output and disable the mux sound path. Do not change the other bits
carelessly: the same port also controls video.

### CoCo 2

Read Tandy's **Color Computer 2 NTSC Service Manual**, models 26-3134 and
26-3136, resource `coco2-service`, PDF/printed 37.
[Archive manual][coco2]. The page image was examined.

This board integrates the six-bit DAC and multiplexing functions.
Its table connects joystick selection with DAC, cassette, cartridge, or no
sound. Integration into one chip does not remove the shared-resource problem.
This source covers the named NTSC models, not every CoCo 2 board revision.

The original experiment below has not been run as a CoCo 2 compatibility test.
Do not turn shared hardware descriptions into an untested support claim.

### CoCo 3

Read Tandy's **Color Computer 3 Service Manual**, resource `coco3-service`,
PDF/printed 10–11 and 42–43. [Archive manual][coco3]. These register tables,
DAC diagram, and mux discussion were examined as page images.

The familiar DAC and shared joystick/audio selection remain present.
CoCo 3 also has programmable interrupt facilities. Page 11 identifies timer
input selection and timer IRQ/FIRQ enables. This creates another scheduling
option, but it does not supply a complete audio driver.

The [timer experiment below](#coco-3-timer-experiment) now checks an original
FIRQ player on both emulated GIME revisions. Tepolt PDF 47–53 and 60 explain
interrupt handling and mapping. Physical-hardware timing remains unverified.

## What the magazines contribute

### Six software voices are not background music

William P. Nee's **Machine Language Made BASIC, Part XII: And the Music
Played On**, The Rainbow, June 1989, starts on printed 68 (PDF 72).
The continuation and listing occupy PDF 76–79. Resource `rainbow-1989-06`.
[Archive issue][sixvoices].

The article explains mixing waveform values, separate phase advances, and
note duration. PDF 77–78 show the player disabling interrupts and repeatedly
writing the mixed value to `$FF20`. The examined loop services the music,
not animation or controls. Its delay path is part of the playback timing.

Use this source to understand synthesis and why adding work changes timing.
Do not drop the player into a game and label it background audio.
The starter example uses an original, simpler oscillator; it does not copy
this player, its waveform table, or its musical score.

Docling converted PDF 77–78 with no sparse-page warnings. Its page-77 image
retains the listing. OCR still corrupts addresses and labels, so both original
page images were checked.
Even the printed source has inconsistencies: the prose's curve address differs
from the listing's copied table address. Reconcile prose, listing, and memory
layout before attempting a port. The original six-voice program was not built.

The searchable Rainbow index, PDF 65 and 72, lists this article without a
correction note. That limited check does not establish that no errata exist.

### Expansion sound is a separate research route

Gary W. Clemens's **Sounding Out Tandy's Sound/Speech Cartridge**, Hot CoCo,
June 1985, begins on printed 73 (PDF 75). PDF 75–76 describe its processor,
sound generators, buffers, and the reviewer's experience with game effects.
Resource `hotcoco-1985-06`. [Archive issue][hotcoco].

Those pages make the review useful for choosing an expansion target.
They do not establish a tested command interface or bounded background latency.
The review continues beyond the sampled pages. Consult the cartridge manual
before writing a driver. No cartridge is required by the starter example.
Docling converted PDF 75 with no sparse warning; its full-page image retains
the review columns.

### Useful leads that did not become implementation sources

- Barden's **Listening to Your CoCo with Assembly Language**, The Rainbow,
  March 1986, PDF 239–241: DAC and waveform introduction. Sampled, not a
  completed article review. The hardware manuals already establish the
  register facts needed here. [Archive issue][barden].
- Nee's **Let There Be Music**, The Rainbow, March 1989, PDF 30:
  ROM SOUND/PLAY entry points and an explicit warning that integrating notes
  with a display slows the tempo. Only the opening page was sampled.
  ROM-version compatibility remains unchecked. [Archive issue][notes].
- The archive's **Assembly music** directory: `country.asm` contains a
  software mixing loop and masks interrupts. The inspected loop has no input
  or animation service. Its credits are not license evidence. Published code
  and melodies remain local reference material. [Archive directory][assembly].

## Original experiment and evidence

[Sound slots](../examples/sound-slots/README.md) asks whether a small cooperative
loop can advance audio, graphics, and a button response together.
It is a CoCo 1 experiment, not a reproduced six-voice player.

The emulator checks compare every DAC value with an independent phase model.
They also check marker movement, background restoration, and scripted input
changes. Instruction traces expose the longer gaps during frame work.
The runner measures throughput over one emulated second separately.

This demonstrates progress of the three tasks and the cost of extra work.
It does not establish constant sample timing, good sound, physical controls,
or CoCo 2/3 compatibility. A production player needs a tighter timing design.

## CoCo 3 timer experiment

### Resolve the clock discrepancy first

Tandy's service manual, PDF 12, describes a 14 MHz timer clock.
Tepolt, PDF 50, likewise describes about 70 ns per decrement.
These values conflict with [John Kowalski's GIME reference][sock].
Kowalski gives 279.365 ns and documents a revision-dependent reload offset:
programmed value plus two for 1986, plus one for 1987.
His reference also distinguishes writing the low byte from starting the timer
with the high-byte write. Use this as an explicit correction, not an unnoticed
substitution for the cited book.

[XRoar 1.12.1 source][xroar-source], `src/tcc1014.c`, agrees with that later
reference: `schedule_timer` uses the revision offset and four master-clock ticks
per fast timer decrement. This establishes the emulator's intended behaviour.
It does not replace a measurement on a physical GIME.

### Compare audio and drawing under load

The [original timer experiment](../examples/timer-sound/README.md) uses a
510 reload value, a short FIRQ handler, and an unchanged foreground renderer.
It acknowledges `$FF93`, preserves the registers it uses, and leaves mapping fixed.
The cooperative build generates samples in the foreground instead.
Both builds run on a slow-clock NTSC CoCo 3 with 128 KiB and a 6809.

The heavy workload clears 6,144 bytes for every completed marker update.
The light workload changes only the marker bytes. Results on XRoar 1.12.1:

| Scheduler and GIME | Light: samples / redraws | Heavy: samples / redraws |
| --- | ---: | ---: |
| Cooperative, 1986 | 12,746 / 49 | 2,508 / 9 |
| Timer FIRQ, 1986 | 6,992 / 27 | 6,992 / 2 |
| Timer FIRQ, 1987 | 7,005 / 27 | 7,005 / 2 |

Each column records one emulated second starting at the first sample checkpoint.
These are counts, with start/end boundary uncertainty, not exact frequencies.
The timer counts match the revision-specific prediction using the corrected clock.

Compare the load change within each row. The cooperative loop has no fixed
sample-rate target, so the rows are not equal-rate audio benchmarks.
Timer audio retains its throughput under this drawing load, but the foreground
gets fewer redraws. Lowering the sample rate or reducing handler work could
release CPU time. Neither alternative has been measured here.

A deliberately unacknowledged FIRQ fails to complete a frame in the test.
Every successful run checks the DAC sequence and completed-frame memory.
Average throughput does not prove evenly spaced samples, audio quality, or
physical-hardware compatibility. No utilization percentage is claimed.

### Source coverage and conversion

Tepolt PDF 48–53 were converted with Docling: six pages, nine linked images,
no sparse-page warnings. The original page images were inspected for vectors,
acknowledgement, register saving, and interrupt initialization. Sparse flags do
not identify the clock discrepancy. It is a source conflict, not an OCR error.

Rick Adams's **GIME Power**, The Rainbow, March 1989, PDF 14, 18, and 24,
provides a period explanation of background tasks and the programmable timer.
Those pages were examined, including the title image on PDF 14.
It is useful motivation, not the implementation authority. Its PDF 24 task-bit
statement conflicts with the register table on PDF 18 and the hardware manual.
This sampled issue remains outside the manifest. [Archive issue][notes].

## Obtain selected pages

Use the project's existing target. Convert only the needed range:

```sh
uv run python scripts/setup.py --resource rainbow-1989-06 --pages 77:78
uv run python scripts/setup.py --resource coco1-technical --pages 37:38
uv run python scripts/setup.py --resource coco3-service --pages 42:43
uv run python scripts/setup.py --resource tepolt-coco3 --pages 48:53
```

Open the linked page PNG when a register or listing is unclear.
Keep downloaded issues, extracted text, and images in ignored `local/` storage.

[coco1]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[coco2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf
[coco3]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf
[sixvoices]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2008%20No.%2011%20-%20June%201989.pdf
[hotcoco]: https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20(OCR)/HotCoCo-1985-06.pdf
[barden]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2005%20No.%2008%20-%20March%201986.pdf
[notes]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2008%20No.%2008%20-%20March%201989.pdf
[assembly]: https://colorcomputerarchive.com/repo/Programming/Source/Assembly%20music/

[sock]: https://www.6809.org.uk/twilight/sock/gime.html
[xroar-source]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
