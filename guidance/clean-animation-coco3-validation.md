# Native CoCo 3 hidden-buffer publication

This is an original bounded bitmap animation and a reproducible software-renderer
experiment. Its result concerns XRoar 1.12.1's GIME 1986 model. No physical
safe-switch timing claim follows from it. The independent
[publication source review](frame-publication-research.md) identifies the
manufacturer-document gaps; this note preserves those gaps.

## Sources checked before implementation

All page numbers are one-based PDF pages. Register tables and packing diagrams
were read as full-page images, not accepted from OCR alone. The existing local
PDFs were read without changing the shared reference collection.

<!-- markdownlint-disable MD013 -->

| Source | PDF pages | Facts used |
| --- | --- | --- |
| Tandy, *Color Computer 3 Service Manual* | 11–13, 18 | Native/MMU enables, VBORD enable, bitmap mode, 192 rows, 256-pixel two-colour encoding, display-offset bits. |
| Same | 14–17 | Horizontal offset, 8 KiB MMU pages and task mapping, RGB palette bits. |
| Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987) | 28–29 | CPU MMU mapping is distinct from video physical addressing; 128 KiB ignores upper address bits. |
| Same | 30–34, 38–40 | Physical video fetches, eight-byte base alignment, row-major pixels, bit 7 is leftmost, palette entries 0/1 for one-bit pixels. |
| Same | 49–53 | GIME IRQ enable/status and read-to-clear description; VBORD at the bottom border; separate PIA sources. |
| Same | 62 | Writing `$FFD8` selects normal low CPU speed. |

<!-- markdownlint-enable MD013 -->

[Tandy PDF][service] SHA-256:
`5c4c82d1b825daacf861be097d93d0a0eff78fbdf394234d4adb06df0cfd3c29`.
[Tepolt PDF][tepolt] SHA-256:
`070e4ac0ad8e59fc1a19b73966c7b55658456cc7ab59af2e3f559ad4791ea3ff`.

Tepolt page 50 explicitly describes reading `$FF92` as releasing a pending
GIME IRQ and identifying its source. That is additional published evidence
beyond the manufacturer pages examined in the independent review. It does not
supply an exact video-base latch instant or a safe write budget. PIA FS and GIME
VBORD are distinct; this implementation never polls or acknowledges PIA FS.

The service manual page 14 says horizontal virtual width is 128 bytes, while
Tepolt page 34 and the examined emulator say 256. This experiment sets horizontal
virtual enable and offset to zero, so it does not resolve or depend on that
conflict. Likewise, only LPR=0 is used; differing descriptions of other LPR
encodings do not establish their support here.

## Original allocation and scene

The target is CoCo 3 with 128 and 512 KiB, normal MC6809 clock, NTSC,
GIME 1986, RGB software output, no cartridge, nonzero startup RAM, and direct
DECB binary loading. These are selected experiment configurations, not measured
physical board revisions. The runner isolates XRoar configuration with
`-c /dev/null`, verifies ROM bytes, and supplies an absolute combined ROM path.

The mode is derived from the source tables: `$FF90=$6E` enables native video,
MMU and GIME IRQ generation with internal ROM mapping; `$FF91=0` selects task 0.
CPU IRQ/FIRQ remain masked. `$FF92=$08` selects VBORD, `$FF93=0` disables GIME
FIRQ sources. `$FF98=$80`, `$FF99=$08` select 256×192, one bit per pixel,
one scanline per row. `$FF9C` and `$FF9F` are zero. Palette entries 0/1 are
`$00/$3F`; border colour is zero. Thus row stride is 256/8 = 32 bytes and each
frame occupies 32×192 = 6,144 bytes.

<!-- markdownlint-disable MD013 -->

| Allocation | CPU address | Physical address |
| --- | --- | --- |
| Code and initialized state | `$3000` through emitted `code_end` exclusive, checked below `$4000` | Executive page `$39`; aliases on 128 KiB as Tepolt describes. |
| Buffer A | `$4100–$58FF` | `$04100–$058FF` via MMU page 2. |
| Buffer B | `$6100–$78FF` | `$06100–$078FF` via MMU page 3. |
| Reserved stack | `$7E00–$7EFF`, S initially `$7F00` | Same low physical addresses via page 3. |

<!-- markdownlint-enable MD013 -->

Task 0 starts with executive pages `$38–$3F`; entries `$FFA2/$FFA3` become
2/3. Display addressing bypasses that CPU map. From Tandy page 13,
`base = (FF9D << 11) | (FF9E << 3)`. Buffer A uses `$08,$20`; B uses `$0C,$20`.
Only the high byte changes during publication. This deliberate allocation
avoids a two-byte transition; it cannot establish two-byte atomicity.

Guards at `$40FF`, `$5900`, `$60FF`, `$7900`, `$7DFF` and `$7F00` start as
`$A5`. Each publication snapshot checks them, both complete buffers, and the
final snapshot adds the `$5A` completion marker. These are boundary guards,
not proof against every possible write elsewhere in RAM. The experiment
assumes exclusive machine ownership and does not return to BASIC.

The original scene has a one-pixel white outline, a black interior, and an
8×8 white square at y=80 and x=32, 48, 64, 80, 96. Assembly clears and draws
bytes; the independent oracle creates pixel-coordinate geometry and packs it.
Literal tests independently check the outline, first square row and row after
the square. The oracle is never used to generate assembly assets.

## Publication and measured boundary

The program constructs scene 0, then alternates four redraws into the other
buffer. Before each normal publication it reads `$FF92` to discard a pending
status, polls until a fresh bit 3, and writes `$FF9D`. It waits for two further
VBORD events before beginning the next redraw. This conservative reuse wait
is checked against emulator adoption; it is not a sourced silicon guarantee.

The private [XRoar release][xroar] archive is pinned to SHA-256
`ba525225fbd732c4dbf2cbb571dc9d2810fd9dcedf0482133cf637e2eef61f88`.
The pristine `src/tcc1014/tcc1014.c` hash is
`fc6d038e022908cc4cf939a5a41ffdf7802bfeb9ae6f8f055cc64649f458c102`.

Static source inspection establishes these model facts:

- `tcc1014.c`, register writes `$0D/$0E`, update Y independently.
- `do_vb_irq` copies Y into B after sync count 7 and raises VBORD at the
  end of active display. These are different events.
- `fetch_byte_vram` calls the machine's video-memory fetch using B plus Xoff;
  `coco3.c:fetch_vram` reads physical RAM.
- `coco3.c:gime_fs` calls `vo_vsync` on FS rise. The null-UI capture receives
  the completed software-renderer buffer through its draw callback.
- This NTSC GIME model has 263 lines of 912 event ticks. The expected renderer
  interval is therefore 239,856 ticks, not the MC6847 cadence constant.
- `tcc1014.c` selects 16 ticks per CPU cycle when R1 is clear, 8 when set.
  Every recorded publication/latch/fetch after initialization must have R1=0.

Original instrumentation records high-byte writes, model latches, VBORD events
and the first fetch of every row. Normal writes must be outside active display,
within 912 ticks after the previous VBORD, followed by adoption at the next
model latch and exactly 192 row fetches spaced by 32 bytes. The report records
write-to-latch margins. The host trace performs no writes to emulated state.

RGB expectations include the renderer's explicitly selected brightness and
contrast of 52. XRoar `coco3.c` maps RGB levels 0/3 to 0/0.920;
`vo_render.c:update_rgb_palette` applies scale 1.04 and offset 0.04;
`colourspace.c` uses the NTSC transfer function. Quantization yields 2 and 253
for black and white. This is an emulator RGB mapping, not a physical monitor
measurement. Each logical pixel has two horizontal software samples, and the
complete expected RGB image includes both samples and all three channels.

Every captured image from the first exact scene 0 to the end of the bounded
run is compared against all five complete scenes. Startup before that match is
excluded explicitly. All five scenes must appear. Timestamps must be consecutive
at the model interval, and repeats compare every timestamp and RGB hash.
Correct final RAM alone cannot pass.

## Controls and limits

`WRONG_BASE` adds one to the high offset byte at publication, selecting 2 KiB
past the intended buffer. Both intended RAM images still pass. GIME's actual
adoption and fetches must follow the incorrect base, and complete-scene renderer
checks must detect it.

`UNSAFE` publishes before clearing/drawing and waits two fields to make the
premature reuse observable. Complete checkpoint RAM still passes. In addition
to incomplete images, the analyzer requires a frame whose every row matches
either one complete scene or a cleared black row, with retained and cleared
rows both present, inside the measured window. A candidate scene number labels
matching row values, not a unique prior scene: all five scenes share the outline,
and the first unsafe destination has not yet held a completed scene. This proves
a partially cleared image, not the ancestry of each retained byte. Only this
exact mixture is called partial erasure; arbitrary mismatches remain unclassified.

The tests reject a frozen stream of complete scenes, skipped/truncated captures,
wrong viewport/sequence, a changed pixel channel, corrupted RAM and guards,
changed clock/phase/fetch evidence, and source drift. An uninstrumented emulator
must be rejected even when it produces correct RAM. Audio, physical hardware,
host GUI smoothness, composite/RF, PAL, GIME 1987, disk loading and a sustained
game workload are outside the evidence.

The exact hardware gap remains the adoption instant of `$FF9D/$FF9E`, any
setup/hold deadline or safe software latency budget relative to VBORD/PIA FS,
and multi-byte atomicity. No examined primary page establishes those contracts.
This experiment does not sweep hardware phases or prove a silicon-safe reuse
point. Its single-byte switch and observed model margin must not be described
as portable CoCo 3 tear-free publication.

## Reproduction and results

[Tracked reproduction and checks](../experiments/clean-animation-coco3/README.md)
retain the original assembly, independent oracle and private instrumentation.
No existing script was changed.

Initial attempts are retained under ignored `build/clean-animation-coco3/`.
The first private build misplaced a trace helper inside an upstream debug-only
conditional and failed compilation. The second passed final RAM but failed
renderer validation because fast host execution skipped fields and the initial
RGB oracle assumed full 0/255 levels. The corrected runner sets rate limiting
and explicit renderer brightness/contrast, with source-derived RGB endpoints.
Another attempt found that multiple count-limited traps at one PC did not
produce the fourth snapshot; distinct original publication labels now make
all four checkpoints unambiguous. None of these failed attempts is accepted
as a passing renderer result.

The first accepted fresh-build suite passed 22 specifications in 139.03 seconds
with 93.42% combined statement/branch coverage of the runner and oracle.
Three further firmware-boundary checks reject missing, short and corrupt ROMs
before a private build or launch. The initial combined suite passed all 25
specifications in 121.97 seconds,
with 93.42% combined statement/branch coverage. This is Python coverage, not
assembly instruction coverage.

For both capacities, the normal run contains 42 consecutive complete images,
all five scene states, and zero incomplete images. Its first-to-last span is
9,834,096 event ticks (41 intervals of 239,856). The four model write-to-latch
margins are 31,223, 31,351, 31,287 and 31,255 ticks. Every adoption is followed
by 192 row fetches from the selected physical base. Normal code ends at `$313F`
exclusive (319 bytes including state); the largest faulty build ends at `$3142`.

The wrong-base control has 34 incomplete images in 42 captured images after
scene 0. The unsafe control has 26 incomplete images in 46, including four
specific partial-erasure witnesses. All six runs pass the RAM scenes, guards
and completion marker. The repeated 128 KiB normal run matches every measured
frame timestamp, RGB hash and timing proof. The uninstrumented installed
emulator reaches valid final RAM but is rejected for missing renderer evidence.

These measurements are identical between the two tested capacities. They are
bounded early-animation evidence; no sustained performance or physical claim
is inferred. Ruff check/format and Markdown fix/check are scoped to the assigned
paths. The full starter test suite was not run.

## Independent review corrections

The retained normal captures passed independent reanalysis. Review also found
that acceptance allowed a truncated window or reordered complete scenes. Normal
acceptance now requires all 42 frames and transitions through scenes 0–4 in
order. Separate controls reject a six-frame tail loss and reordered scenes.
Runtime provenance now records Python and NumPy versions and the hashes of
`uv.lock` and `pyproject.toml`.

The revised suite passed 28 tests in 140.28 seconds, with 93.51% combined
statement/branch coverage. Missing, short and corrupt firmware still leave a
failed report before private build or launch. This remains emulator evidence;
the physical timing limitations above are unchanged.

[service]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf
[tepolt]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf
[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz

The final fresh-build report is ignored at
`build/clean-animation-coco3/spec-b1886286ead4/results.json`.
Its private executable SHA-256 is
`c5f439a84c56a603e6b1d7c88e5d48c9201ebaaca87bf091e34e1c0cf3be3702`.
The test log is `build/clean-animation-coco3/scoped-tests-final.log`.
No branch, commit, push, shared-script edit or GUI launch was performed.
