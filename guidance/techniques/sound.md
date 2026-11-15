# Keep sound playing while the game works

Read this before you combine sound, drawing, and controls. First, decide which
task supplies the next audio sample and what can delay that task. A music
routine that occupies the CPU does not automatically become background music.

## Identify the sound hardware

The stock six-bit DAC receives sample values from the CPU. On CoCo 1, it uses
`$FF20` bits 2–7. The audio mux selects the DAC when both selection bits are
zero and sound enable is set. Analog joystick conversion shares the DAC and the
mux, so reading an axis can change the sound path. Fire buttons are digital
inputs on the keyboard rows and need no conversion.
[CoCo 1 manual, PDF 13–14 and 37–38][coco1]

The named CoCo 2 NTSC boards combine the DAC and the mux in one IC. Selection
`00` chooses the DAC. [CoCo 2 manual, PDF 37–38][coco2] CoCo 3 keeps the shared
hardware too. [CoCo 3 manual, PDF 42–43][coco3dac]

The one-bit output on CoCo 1 is `$FF22` bit 1, with direction and mux setup.
Other bits of that port control video, so keep them when you change the sound
bit. [CoCo 1 manual, PDF 14 and 38][coco1] Cassette audio through the mux is
not CPU synthesis during gameplay.

Our recommendation: list every routine that writes these ports before you
combine input and audio. A tested fire button does not prove a safe axis read.

## Choose short effects or continuous music

**Published explanation.** William P. Nee's six-voice player mixes waveform
values and controls note duration. It masks interrupts and writes samples to
the DAC in a loop that does not service drawing or controls.
[Nee, June 1989, printed 68 / PDF 72, continuation PDF 76–79][nee]
Its prose and listing disagree about a curve address. Reconcile the memory
layout from the listing image before you adapt it. We did not build it.

For an explosion or pickup sound, a small sample table is a good start. Barden
separates the table bounds, repeat count, and delay between samples. His routine
plays the whole effect before it returns, so the game stops during playback.
His ordinary 0–63 amplitudes need a shift for the DAC, but his cassette ROM
samples are already aligned. Give each sound asset an explicit format. His prose
names `BNE` at the end of the table loop, but the listing uses `BLS`.
[Barden, PDF 246 and 248–251][barden]

The [collect-room example](../../examples/collect-room/README.md) plays its
effects in the same blocking way: 32 alternating DAC writes, then a return to
the game. Its check finds every effect in XRoar's mixer output and tests its
pitch band. The game cannot read keys during an effect.

ROM SOUND and PLAY calls can help a BASIC-hosted prototype. Nee's PLAY example
saves the BASIC text pointer and runs from BASIC. His prose and listing give
different note-table addresses, so use labels. These calls are not a portable
interface for a standalone game. Measure the pause that each call causes.
[Nee, March 1989, PDF 30–32][notes]

## Treat cartridge sound as an optional target

Clemens's review describes separate processing and generators in Tandy's
Sound/Speech cartridge. It is an expansion, not stock-machine capability.
[Hot CoCo, June 1985, printed 73–76 / PDF 75–78][cartridge]

The manual shows a practical trap. Before you send each byte to `$FF7E`, wait
until status bit 7 is high. The cartridge loses a byte sent while that bit is
low. Bits 6 and 5 report speech and sound activity, but are not valid
immediately after a command starts. Inside a sound event, `$FF` is data, not
an end mark.
[Cartridge manual, PDF 10–11 and 15][speechmanual]

Our proposal: load effects during setup, then send one byte each time the
cartridge accepts one. Track acceptance separately from playback. The timing
assumes the normal CoCo clock. [Cartridge manual, PDF 8][speechmanual] This
starter has no cartridge driver or latency test.

## Schedule samples cooperatively

The [sound-slots example](../../examples/sound-slots/README.md) interleaves
samples with marker movement and fire-button reads. It runs on CoCo 1 and on a
non-T1 CoCo 2 (26-3134/26-3136, 64 KiB), both NTSC and normal-clock. It masks
interrupts and avoids analog axes.

```sh
uv run python scripts/coco.py check examples/sound-slots
```

**Measured result.** On both targets, the check compares every DAC value,
screen byte and scripted button state with an independent model. The mixer
output has the tone that 57 cycles per sample predicts. The frame work takes
up to 30 instructions between two DAC writes, against a budget of 40.
Scripted input substitutes a value after the real PIA read. It is not evidence
of a physical button.

The budget is the lesson. A delay loop after each sample block keeps every
sample and every screen byte correct, but fails the budget. Correct memory does
not prove timely samples. More foreground work slows playback. Measure it again
each time the workload grows.

## Use CoCo 3 timer interrupts when drawing delays samples

CoCo 3 has a programmable timer. [CoCo 3 manual, PDF 10–12][timer] Tepolt
explains FIRQ handling, acknowledgement, and initialization. FIRQ saves less
state than IRQ, so the handler must keep the registers that it changes.
[Tepolt, PDF 47–53][interrupts]

The [timer-sound example](../../examples/timer-sound/README.md) compares
cooperative and timer scheduling on one CoCo 3: NTSC, 128 KiB, slow-clock 6809,
fixed mapping, both GIME revisions. It does not test interrupts during bank
changes. For banked memory, read
[scrolling and memory](scrolling.md#keep-interrupt-code-reachable).

```sh
uv run python scripts/coco.py check examples/timer-sound
```

**Measured result.** The heavy build clears all 6,144 screen bytes before each
redraw, 79,872 cycles. [Leventhal, PDF 552–555][leventhal] The cooperative build
stops its tone for all of that clear: 89.4 ms on the pinned XRoar. The timer
builds keep a 218.5 Hz tone with no pause longer than 0.16 ms.

Interrupt-driven sound uses CPU time. It does not make drawing free: the clear
still takes the same cycles, and fewer redraws complete. Two failure controls
pass the memory check:

- Masking FIRQ during the clear stops the tone, and the sound check fails.
- A handler that does not acknowledge `$FF93` never completes a redraw.

## Resolve the timer-clock conflict

Tandy PDF 12 and Tepolt PDF 50 describe a timer clock near 14 MHz. John
Kowalski's later GIME reference, under `$FF91` and `$FF94–$FF95`, gives
279.365 ns per count. It adds 2 to the reload value on the 1986 GIME and 1 on
the 1987 GIME. The examples use that later account. [Kowalski][kowalski]

The pinned XRoar models the later account in `src/tcc1014/tcc1014.c`
(`schedule_timer`, `timer_offset`), and the measured tone agrees. This supports
the emulator, not a physical GIME. Record which account your timing uses.

## Measurements the examples do not rerun

A private XRoar 1.12.1 build logged the emulated time of each DAC write. The
gaps, in slow-clock cycles, were:

- Sound-slots: 57–138 on CoCo 1 and on the 64 KiB non-T1 CoCo 2, and 57–158
  with the input fixture.
- Timer-sound: cooperative 70–125 (light) and 70–80,002 (heavy). Timer 123–134
  (light) and 123–133 (heavy) on both revisions, with a mean of 128.0 (1986) and
  127.75 (1987), the predicted timer periods.

A stable average rate is therefore not evenly spaced writes. As controls, a
`NOP` added two cycles, and masking FIRQ during the clear gave an 80,002-cycle
gap. On CoCo 2, a 10,000-iteration delay added exactly 80,003 cycles at each
of 63 block boundaries. These are finite windows, not worst-case bounds.

The same build counted progress in one emulated second. Sound-slots completed
60 redraws. On timer-sound, the cooperative build fell from 12,746 to 2,508
samples under the heavy load. The timer build kept 6,992 (1986) or 7,005 (1987)
samples, but its redraws fell from 27 to 2. The counts are uncertain by a small
amount at the edges of the window.

A private XRoar 1.12.1 build recorded every rendered frame and all mixer output
of collect-room for the first 43 lines of its journey. It ran on CoCo 1 and
CoCo 2 (NTSC, 32 KiB, non-T1). Each run gave 447 continuous frames and 328,704
samples. All 229 frames between a checkpoint and the next key sample showed
the complete scene.

The five effects peaked at 978 Hz (start), 1,739 Hz (pickup) and 680 Hz (win),
with 16 high runs each. The title was silent. The first checkpoint came 2.15 s
after audio start, and the next 42 scans took 5.27 s.

Frames during a redraw were not compared, so this is no tear-free claim. The
example check compares only one frame after each checkpoint.

## Apply the findings to a game

These are our next steps, not a completed music engine:

1. Choose the target hardware and a sample-rate budget.
2. Measure the worst drawing workload with audio enabled.
3. Test press, hold, and release for each control path.
4. Check that each handler keeps its registers and acknowledges its request.
5. Check that handlers stay mapped before you add banked assets.
6. Listen to the running result. Look at the display.

The mixer WAV is XRoar's digital output before any host audio driver. Nobody
has listened to these examples, and no physical CoCo result exists.

## Sources

- Tandy: *Color Computer Technical Reference Manual* (`coco1-technical`),
  *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)* (`coco2-service`),
  *Color Computer 3 Service Manual* (`coco3-service`) and *Color Computer
  Speech/Sound Cartridge* (`speech-sound-manual`). The text above gives the pages.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 47–53 (`tepolt-coco3`). Lance A. Leventhal, *6809 Assembly Language
  Programming*, Appendices B and C, PDF 552–555 (`6809-programming`).
- *The Rainbow*: Nee, "Machine Language Made BASIC, Part XII: And the Music
  Played On", June 1989 (`rainbow-1989-06`). Nee, "Part IX: Let There Be
  Music", March 1989 (`rainbow-1989-03`). Barden, "Listening to Your CoCo with
  Assembly Language", March 1986, PDF 239–242, 246, 248, 250–251, 254–255
  (`rainbow-1986-03`).
- Gary W. Clemens, "Sounding Out Tandy's Sound/Speech Cartridge", *Hot CoCo*,
  June 1985 (`hotcoco-1985-06`).
- John Kowalski (SockMaster), *GIME register reference*, an author reference
  outside the archive.

The examples are our original work. They do not reproduce the magazine programs.

[coco1]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[coco2]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=37>
[coco3dac]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=42>
[timer]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=10>
[interrupts]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=47>
[leventhal]: <https://colorcomputerarchive.com/repo/Documents/Books/6809%20Assembly%20Language%20Programming%20%28Lance%20Leventhal%29.pdf#page=552>
[nee]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2008%20No.%2011%20-%20June%201989.pdf#page=72>
[notes]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2008%20No.%2008%20-%20March%201989.pdf#page=30>
[barden]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2005%20No.%2008%20-%20March%201986.pdf#page=248>
[cartridge]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20(OCR)/HotCoCo-1985-06.pdf#page=75>
[speechmanual]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Speech-Sound%20Cartridge%20(Tandy).pdf#page=10>
[kowalski]: https://www.6809.org.uk/twilight/sock/gime.html
