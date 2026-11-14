# Sound while a game runs

Start with [Schedule sound](../sound.md) for practical guidance.
Read these research notes for detailed evidence, source conflicts, and exclusions.
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

### Short effects from sample tables

William Barden Jr.'s **Listening to Your CoCo with Assembly Language**, The
Rainbow, March 1986, occupies printed 237–240, 244, 246, 248–249, and 252–253
(PDF 239–242, 246, 248, 250–251, and 254–255). The complete article, diagrams,
assembly listing, and BASIC loader were read, including the separated
continuations. [Archive issue][barden].

The reusable idea is an effect descriptor: sample start, sample end, repeat
count, and delay count. The table supplies amplitude; spacing and repetition
control playback. The diagrams connect sample shapes to envelopes, including
rising and falling effects. This helps design original game sounds without
embedding the magazine's table or loader in the repository.

The listing on PDF 251 is a blocking subroutine. It plays every requested
repeat before returning to BASIC; the inner loop contains no game service.
Its ordinary samples are 0–63 and are shifted left twice. Barden explicitly
removes those shifts when using the already aligned cassette ROM samples.
A raw DAC byte and an unshifted amplitude are different asset formats.

Two source cautions matter. The PDF 251 prose names a BNE at the table-loop
end, while the printed listing uses BLS. Derive bounds from the assembled
instructions before adapting it. The routing setup is described as lasting
for the program, but that assumes no later routine changes the shared mux.
Neither the sample ROM addresses nor the program have been tested here
against particular ROM revisions. No timing or audio-quality result is claimed.

### ROM calls need an interpreter contract

William P. Nee's **Machine Language Made BASIC, Part IX: Let There Be Music**,
The Rainbow, March 1989, printed/PDF 30–32, was read completely, including
all three routine listings and the assembled listing. [Archive issue][notes].

Nee presents SOUND calls and PLAY strings from assembly. His warning that
adding display work slows the tempo is consistent with a sequence of blocking
calls, not a background scheduler. The PLAY example saves and restores the
BASIC text pointer and must run from BASIC rather than ZBUG. The SOUND
example identifies clobbered registers. These are calling-context requirements,
not merely addresses to paste into a standalone game.

The PDF 32 prose gives note-table addresses `$301D` and `$3056`; the printed
assembled listing places NTAB1 at `$3019` and NTAB2 at `$3058`. This is a
source discrepancy, not an OCR correction. Use labels and inspect the actual
assembly. The article's entry points and workspaces have not been matched to
specific BASIC/Extended BASIC ROM revisions, and its tunes were not reproduced.

The searchable Rainbow index entries on PDF 34 and 135 (Barden), and 65, 72,
75, and 90 (Nee), contain no correction note. This limited index check is not
an exhaustive search of later issues or proof that no errata exist.

### Expansion sound needs a byte handshake

Gary W. Clemens's **Sounding Out Tandy's Sound/Speech Cartridge**, Hot CoCo,
June 1985, occupies printed 73–76 / PDF 75–78. The whole review was read,
including its final paragraph on PDF 78. Resource `hotcoco-1985-06`.
[Archive issue][hotcoco]. It describes separate processing, generators, stored
effects, and the difficulty of programming the command bytes. Its judgement
about sound quality is the reviewer's experience, not a starter measurement.

Tandy's **Color Computer Speech/Sound Cartridge** manual supplies the useful
interface detail. The archive copy has 54 PDF pages and typeset text; page
numbers below refer to that copy. It differs in extent from the 56-page manual
mentioned by Clemens. PDF/printed 8–11 were read for background and the complete
status-byte discussion; PDF 15 was read for sound-event framing. The key status
pages and event table were also checked as images. This is selected manual
coverage, not a complete driver or command-reference audit. [Manual][speechmanual].

- `$FF7E` is the data-write/status-read address. Bit 7 is active-low BUSY.
  Check it before each byte; writing while it is low loses data (PDF 10).
- Bits 6 and 5 report speech and sound activity respectively, also active low.
  They are not valid immediately after an execution command. Processing time
  varies with the command, so immediate inactivity cannot prove completion
  (PDF 10–11).
- Sound-event groups have different lengths. `$FF` terminates a sequence only
  where a new event may begin; inside an event it is data (PDF 15).
- The manual's pitch and duration assume the normal .89 MHz CoCo clock and
  the cartridge's doubled clock (PDF 8). Faster host operation needs a separate
  timing check.

For a game, our proposed design is to load effects during setup, then advance
a command sender only when the cartridge accepts another byte. Keep command
acceptance separate from playback start and completion. That design still needs
measured startup delays, error recovery, and target-specific tests. No cartridge
driver, latency bound, Multi-Pak compatibility test, or physical listening test
has been completed. The stock starter remains independent of this expansion.

### Excluded implementation material

The archive's **Assembly music** directory contains `country.asm`, whose
inspected software-mixing loop masks interrupts and contains no input or
animation service. Its credits are not license evidence. Published code and
melodies remain local reference material. [Archive directory][assembly].

Source PDFs, extracted passages, rendered pages, and URL/SHA-256 provenance
for this follow-up remain under ignored `local/research/sound-followup/`.
No magazine listings, sample tables, or scores were added to tracked files.

## Original experiment and evidence

[Sound slots](../../../examples/sound-slots/README.md) asks whether a small cooperative
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

The [original timer experiment](../../../examples/timer-sound/README.md) uses a
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

[speechmanual]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Speech-Sound%20Cartridge%20(Tandy).pdf#page=8>
