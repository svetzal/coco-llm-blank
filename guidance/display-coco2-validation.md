# Validate static CoCo 2 display output

Use this when an RG6 framebuffer check passes but you still need evidence for
pixel placement, selected mode, tile art or mask composition on a defined CoCo 2
profile. The [retained experiment](../experiments/display-coco2/README.md) captures
actual XRoar software-renderer output. It is an original adaptation of the
repository's examples, not a reproduction of a published game.

## Measured result and target

The asymmetric probe and eleven frozen example scenes matched all 6,144
framebuffer bytes and all 98,304 renderer samples each. Each case passed twice,
with identical capture hashes after 0.5 and 1.0 emulated seconds of settling.
Tile-room steps were 0, 5, 39 and 41. Masked-object scenes were 0, 2, 3, 8, 9,
10 and 11. The wrong-SAM probe retained matching RAM but differed in 3,040
renderer samples at both intervals. The unreachable `state` checkpoint produced
no RAM snapshot, although the renderer produced an image.

The target is **CoCo 2 NTSC, 32 KiB, normal-clock 6809, MC6847 non-T1**,
no cartridge, nonzero startup RAM and direct DECB auto-run. The task specified
this target. Shared project notes were not changed. XRoar 1.12.1 uses `cocous`
with explicit `-tv-type ntsc -vdg-type 6847 -machine-cpu 6809 -ram 32`.
`-c /dev/null` excludes user configuration. `bas12.rom` and `extbas11.rom` are
verified by the repository's checksum validator and passed as absolute paths.
Exact ROM, archive, input, assembler, private-build and artifact hashes are in
[baseline.json](../experiments/display-coco2/baseline.json).

This configuration is deliberately non-T1. In the examined XRoar 1.12.1
`src/xroar.c`, default machine definitions at lines 460–479 distinguish the
NTSC `cocous` architecture from `coco2bus`, which explicitly selects `6847t1`.
Choosing the latter would change the experiment's hardware contract. The ROM
version and explicit configuration define this emulator result; it does not
establish compatibility with every physical board sold as a CoCo 2.

## What a builder can do with this

1. Establish the display mode and independent expected picture before adding
   moving scenes. The asymmetric probe exercises both screen corners, bit and
   byte boundaries, row stride and unequal rectangle dimensions.
2. Freeze after a completed draw at a named program checkpoint. Use the symbol
   file emitted with that binary. Check the selected scene's state as well as
   pixels. The retained transformation adds a conditional self-loop at
   `frame_ready`; the example's drawing and hardware setup stay unchanged.
3. Compare actual renderer output with a separately expressed pixel model.
   The tile-room oracle walks a graph and uses text drawings. The masked-object
   oracle evaluates transparent and opaque ring geometry at pixel coordinates.
   Neither derives expectations from captured RAM or assembly art tables.
4. Require the wrong-mode control to retain correct RAM while producing a
   different picture. Require an unreachable program counter to produce no
   checkpoint. A file, process exit or plausible image alone proves too little.

The selected tile-room frames show the initial room, collection, and later
returns with the collectible still removed. Masked scenes exercise partial
overlap in both draw orders, an inverted background, removal and screen edges.
These do not exhaust all frame states or alignments. Full redraw remains the
examples' strategy. The experiment measures no drawing cost or performance
advantage over selective redraw.

The framebuffer occupies `$0400–$1BFF`. Code and data start at `$3000`; the
examples reserve `$7E00–$7EFF` for the stack. A freeze adds a few instructions
but no additional framebuffer. Keeping a complete screen costs 6,144 bytes,
derived as `256 / 8 * 192`. The room's state and display bytes remain distinct.

## Why this is renderer evidence

The imported original instrumentation modifies only the privately extracted
`src/null/ui_null.c`, with a pinned pristine hash and exact-match guards.
It attaches XRoar's RGBA8 software renderer and exports the buffer at draw time.
The emulator still fetches memory through its normal SAM/VDG path. Examined
XRoar 1.12.1 passages are `src/dragon/dragon.c:dragon_vdg_fs` and
`vdg_render_line` (lines 1447–1465), `src/vo.c:vo_set_renderer` and
`update_render_parameters` (102–143), and `src/vo.h:vo_vsync` (277–281).
These connect scanline generation, S-video palette rendering and drawing before
the renderer's frame reset. [Pinned upstream release][xroar]

The measured path is S-video, `-ccr none`, zoomed viewport, composite palette,
RGBA8 software buffer. PPM output is 512×192 RGB samples, two horizontal
samples per logical RG6 pixel. Its black/green values are `(0,31,0)` and
`(46,188,36)` in this build. The comparison rejects unexpected dimensions or
palette entries. PNGs are lossless conversions of those PPMs, not synthesized
RAM pictures. The asymmetric, tile-room-39 and masked-scene-9 PNGs were opened
and inspected during the measured run.

There is no exact VDG frame serial in the exported image. Stationary evidence
instead requires assembled `BRA`-to-self bytes at the reached checkpoint,
verified scene identity, the examples' interrupt-masked setup, and identical
complete renderer captures at two settling intervals. This removes scene
changes while the renderer catches up. It cannot demonstrate animation cadence,
tearing prevention or whether the unmodified running examples expose partial
redraws. Earlier CoCo 1 work found 0.08 seconds insufficient; this pass retains
the longer interval and independently compares a second one.

## Examined primary sources

The following passages were actually read for this pass. Hardware page images
were inspected where register tables and pixel encodings mattered. The metadata
and resource IDs resolve through the existing manifest, which was not edited.

- Tandy, [Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)][coco2],
  resource `coco2-service`, PDF/printed 31, section 4.4: IC8 is the MC6847,
  display information resides in DRAM, SAM supplies display addressing, and
  the mode inputs are controlled through a PIA. PDF/printed 32–33, section 4.5,
  explains the board's artifact circuitry. Those paragraphs were read as text;
  this experiment does not test their RF/artifact behavior.
- Tandy, [Color Computer Technical Reference Manual][technical], resource
  `coco1-technical`, PDF 14 (printed 7): `$FF22` mode fields and `$FF23`
  data-register selection. PDF 15 (printed 8): SAM display offset, mode, page
  and normal-rate strobes. PDF 31 (printed 24), mode-selection table: 256×192
  uses SAM `110` and PIA bits 7–4 set. This is the original CoCo register
  reference, cross-checked with the named CoCo 2 manual, not a claim about T1.
- Don Inman, Kurt Inman with Dymax, [Assembly Language Graphics for the TRS-80
  Color Computer][graphics], resource `assembly-graphics`, PDF 107 (printed 98):
  a byte specifies eight consecutive graphic elements, and color set zero maps
  zero to black and one to green. The page image's byte examples were inspected.

The probe, freeze transformations, two-interval stationary check and independent
models are our adaptations. None of the cited authors is credited with those
experiment procedures. Source archive availability is not a redistribution
license; no downloaded pages, ROMs or upstream source bodies are tracked here.

## Verification

The independent fresh-build scoped run passed all 13 tests with 94.16% combined
statement and branch coverage for the new experiment. Scoped Ruff lint and
format checks and Markdown lint passed. Imported display-capture helpers were
exercised through the real build and launches; this is not a full repository
suite result. The retained baseline identifies the successful test run.

## Failed attempts and remaining limits

The first private build completed, but the transformation guard refused
`frame_ready` because the candidate text also occurred in branch operands.
No emulator case ran in that attempt. The corrected transformation matches the
label on its own line. Failed artifacts remain under
`build/display-coco2/measured/`; the corrected standalone run is under
`build/display-coco2/corrected/`. The first test session had the already-loaded
old transformation and failed for the same reason. It is not a hardware failure
and was not removed from the research account.

The regression checks deliberately reject a correct-mode image presented as
the wrong-mode control, a wrong-mode image presented as a positive, corrupted
scene identity and stationary code, a damaged archive, and a reachable trap
presented as unreachable. These expected failures are part of acceptance.
Generated evidence and source stay in task-specific ignored directories.

PAL, MC6847T1, other RAM/ROM configurations, composite artifact decoding, RF,
GUI scaling, disk loading, input interaction, cadence, tearing and physical
hardware remain untested. Static sample equality is useful evidence for this
specific emulator path and nothing broader.

[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
[coco2]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf
[technical]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf
[graphics]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf
