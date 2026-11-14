# Development practice

## Establish the contract

A project is a folder, `projects/<name>/`, holding `main.asm`, `coco.toml`,
`expected.py` and `README.md`. The README starts with what the owner asked for
and how to run it in plain language. Its contract section records the CoCo
model/revision, XRoar machine profile, RAM, CPU, video standard, clock,
controls, and loader. Write it before adapting an example, assembling, or
writing hardware-dependent code, and read it back to verify the write
succeeded. Keep `coco.toml` consistent with it. Notes filled in after a run describe that run; they do not
replace this implementation contract.
Setup selects a starting target;
it does not establish that an application supports it. Keep unknowns explicit.
Do not silently enable a 6309, more RAM, or a faster clock to pass a test.

For a new CoCo 1 emulator demo with no RAM or video requirement, start with
32 KiB RAM, NTSC, a stock-clock 6809, and direct DECB binary auto-run in XRoar.
Record these as starter defaults in the project contract and state them to the
owner; do not claim the owner confirmed them. An animation needs no controls
unless requested. These defaults let the first prototype proceed. Explicit
requirements and existing project notes take precedence; ask when a physical
machine's configuration or a conflicting requirement must be resolved.

These are CoCo 1 defaults, not CoCo 2 defaults. For each configuration choice,
distinguish an owner requirement, a documented default applicable to that model,
and an agent-selected prototype choice. Cite the applicable guidance for a
default; state agent-selected choices to the owner without attributing consent.

## Graphics before code

Load [reference lookup](references.md) and consult the graphics programming book
before choosing a graphics mode, allocating its framebuffer, packing pixels,
or writing display registers. Do not start with remembered mode tables and use
the book only after the screen looks wrong. Copying display setup from a
working example still requires reading its cited primary passages for the
selected target before reuse. Downloading or converting a page does not count
as reading it. Reuse facts already checked in this session.

Establish these facts from passages that apply to the selected hardware:

- The mode's name and meaning in its context. Distinguish BASIC mode numbers,
  hardware control-bit encodings, and names used by the author. Do not assume
  they are interchangeable or transfer a CoCo 3 description to a CoCo 1/2.
- Resolution, available colors, pixel encoding, pixels per byte, row stride,
  and framebuffer size. Show how the memory sizes follow from the layout.
- The relevant control registers, field values, display-memory selection,
  alignment requirements, and shared bits that setup must preserve.
- The palette or artifact-color behavior relevant to the selected video
  standard and display. Do not treat an emulator's appearance as a mode table.

Keep a short source note beside the implementation or in existing design notes:
what was verified, the book title and PDF page, and the values derived from it.
Inspect table and diagram PNGs for bit ordering and labels; OCR of a register
value or bit pattern is not sufficient when its interpretation is uncertain.
If the book does not cover the target, find a source that does before proceeding.
For a physical model or board revision, read the passage or schematic that
supports that revision's register behavior. A contents entry or shared chip
names do not establish compatibility. An emulator check supports the tested
profile, not every physical revision bearing the same CoCo model name.

Derive expected test bytes from the sourced layout, independently of the packing
code. Check boundary pixels, row transitions, and framebuffer limits. Then use
a small emulator display check to inspect the chosen mode and colors before
building the full graphics feature. Passing arithmetic tests cannot establish
that the hardware mode was selected correctly.

If the observed display contradicts the source, revisit the target, source
scope, and setup code together. Do not cycle through guessed register values
until something looks plausible, or change working behavior solely to match an
unverified summary.

## Build and verify

Keep deterministic computation separate from display, input, and disk I/O.
Use fixed test vectors and compare exact output bytes where appropriate.
Use LWTOOLS for assembly and XRoar for machine integration. CPU-only tests
cannot prove PIA, display, ROM, or disk behavior.

For Disk BASIC `LOADM`, assemble with `lwasm --6809 --format=decb`.
Emit symbols from the same build. Inspect the memory map for overlap among
BASIC workspace, display RAM, code, data, stack, and loader needs. Initialize
state before reading it, set DP explicitly when required, and preserve shared
PIA bits when changing peripheral state.

Keep evidence separate:

- CPU tests prove arithmetic and memory transformations.
- Emulator tests prove behavior under the declared machine configuration.
- Visual checks prove the displayed result and interaction were inspected.
- Physical-hardware checks establish behavior on the named real machine.

A process exiting is not proof of a successful boot. Check a meaningful
program state. Directly loading a binary is not proof that a disk image works;
test `LOADM` from the disk. Report minimum RAM and loading instructions with
any distributable artifact.

## Check the feature you claim

Choose checks for the requested feature and declared target. A first prototype
needs a small complete path through its behavior, not every experiment or every
CoCo model. Use the methods below when their boundary matters, adapting their
configuration and expectations to the project. Report an untested boundary
plainly instead of expanding a narrow pass into a playability claim.

Write expected outcomes from the contract, source facts and intended artwork
before inspecting the run's output. Use an alternate route or lifecycle where
it could reveal a bug, and a negative control that breaks the claimed behavior.
Do not repair a failed expectation by copying the observed result; resolve the
difference against the requirement first.

`scripts/coco.py check` keeps each kind of evidence apart: execution, memory,
keys pressed through the emulated keyboard, XRoar's rendered frame and XRoar's
mixer output. Keys, rendered frames and sound need the
[instrumented XRoar](toolchain.md#instrumented-xroar), which the tool builds
once on first use. Its report ends with `Visual: not inspected by a person`:
a capture is not a person looking at a window, a television or a physical CoCo.

### Keyboard input

For an input claim, deliver press, hold and release through the emulated
keyboard and observe the resulting game state. Declare `[keys]` in `coco.toml`
and a variant whose `keys` names a key script; `check` plays it through XRoar's
keyboard API, matrix, PIA and the program's own scanner. Each script line takes
effect at one hit of the `[keys]` label, normally the scanner's entry, so line
N is held during the Nth scan. The first word lists the held keys by the
letters `[keys]` declares, or `-` for none; later words are ignored, so the
script can carry the expected outcome of each step beside it. After the last
line every key is released. The
[Collect room journey](../../examples/collect-room/journey.txt) is an example.

Keep a build without keys as the no-input control, and add a wrong-key or
wrong-column control that must fail. Check release and repress across the
relevant blocked movement or restart transition. Writing logical key bits
after the scanner returns tests gameplay logic only, even if the scanner
executed first; keep that useful test separate from keyboard delivery. XRoar
API injection does not establish OS key delivery, window focus or physical
keys; claim those only after checking those paths. The
[keyboard experiment's report](../techniques/validation/keyboard-controls.md#actual-injection-boundary)
records how this injection boundary was first established.

### Sound

A sound-call counter proves invocation, not DAC output, duration or audibility.
For a waveform or duration claim, use actual DAC values and event timestamps,
following the [DAC timing method](../techniques/validation/audio-timing.md) or its retained
[CoCo 2 experiment](../../experiments/sound-coco2/README.md). State whether a duration
is measured or calculated and give its basis; a call count supplies neither.

For emulator audio output, add `--audio` to `check`, or set `audio = true` in
`[capture]`. Each checkpoint then saves XRoar's mixer output as a WAV: mono,
44,100 Hz, 16-bit, from the start of emulation (including ROM boot) to the
checkpoint. If `expected.py` defines `verify_sound(sound, frame)`, it receives
`sound.samples` (a NumPy int16 array) and `sound.rate`, raises `ValueError`
when the sound differs, and may return a summary for the results file. Derive
the expected pitch or level from the program's cycle counts and sources, not
from a capture. Add a muted or wrong-routing control that must fail.
[Sound slots](../../examples/sound-slots/README.md) checks its tone this way. The
[audio-output experiment](../../experiments/audio-output/README.md) first
established this capture.

The mixer output is the emulator's digital signal before any host audio driver.
It is separate evidence from host playback, listening and physical output;
keep those limits explicit when any of them is untested.

### Artwork and display

Derive expected pixels from independently specified art rows and scene positions,
not from art or font bytes read back from the same emulator RAM being checked.
Copying those bytes into an oracle can check placement while accepting corrupted
art. The [asset-loading experiment](../../experiments/asset-loading/README.md#what-the-target-checks-establish)
compares literal artwork and the full framebuffer, with complemented-picture
and swapped-assignment controls. Adapt that method to the intended artwork;
do not make captured output the new expected picture.

Screen memory cannot show a wrong display mode or bit order. For a
rendered-display claim, add `--video` to `check`, or set `video = true` in
`[capture]`, and define `expected_frame(frame)` in `expected.py`: the picture
as rows of RGB values. Each checkpoint saves a PNG of the first frame XRoar's
software renderer completes entirely after the checkpoint, and `check` compares
every sample. The program must keep the picture still for about two video
frames (1/30 s) after its checkpoint, or the capture shows later drawing.

The renderer uses S-video colours without cross-colour artifacts and shows
only the active area. For CoCo 1/2 graphics that is 512×192 samples, two per
pixel, with no 4:3 stretch. Its colours are XRoar's palette values, not
measurements of a monitor; [first-screen](../../examples/first-screen/expected.py)
records the two for its mode. Include a control the memory check cannot catch,
such as a wrong SAM mode or a reversed bit order, and open the PNG with an
image viewer too. The
[display-validation experiment](../../experiments/display-validation/README.md#acceptance-and-negative-controls)
first established this renderer method. Static captures do not establish
animation cadence or tearing; for those tasks follow the
[animation guide](../techniques/animation.md).
Host presentation and physical displays remain separate checks.

## Reusable launchers

Do not write or copy a launcher. A project is a folder that
`scripts/coco.py` builds, launches and checks:

```sh
uv run python scripts/coco.py --help
uv run python scripts/coco.py build projects/<name>
uv run python scripts/coco.py run projects/<name>
uv run python scripts/coco.py check projects/<name>
uv run python scripts/coco.py check projects/<name> --video --audio
uv run python scripts/coco.py snapshot projects/<name> --frame 3
uv run python scripts/coco.py snapshot projects/<name> --frame 3 --video \
  --keys keys.txt
```

Besides its `README.md`, the folder holds three files. Start by copying
[first-screen](../../examples/first-screen/README.md); its files show each
setting with a comment.

- `main.asm`: the program, assembled as a DECB binary with a symbol dump.
- `coco.toml`: the contract the tool runs. Each `[targets.<name>]` table names
  the XRoar machine, CPU, video standard, VDG, RAM and firmware files; the first
  is the default. `[memory]` requires labels at or below addresses. `[check]`
  names the checkpoint label reached once per completed frame, the frames to
  snapshot, a label that must never execute, and where the screen starts.
  Optional `[variants.<name>]` tables add assembler defines, a key script
  (`keys = "file"`), or both. `[keys]` names the label where each script line
  takes effect (`at`) and maps the script's letters to XRoar key names
  (`letters`). `[capture]` turns on `video` or `audio` for every check.
  `prepare` names a Python file whose `prepare(output)` writes include files
  first.
- `expected.py` (optional): the independent model. `expected_screen(frame)`
  returns the exact screen bytes and `verify_ram(ram, symbols, frame)` raises
  `ValueError` when the state differs. `expected_frame(frame)` returns the
  rendered picture and `verify_sound(sound, frame)` judges the mixer output;
  each is used only when that capture runs. With variants, every function
  also receives the variant name. Write the model from sourced facts and
  requirements, never from the assembled bytes or a captured snapshot.

`check` starts from nonzero RAM, snapshots each frame, requires that the
unreachable label leaves no snapshot, compares every screen byte, and then runs
the model. It reports execution, keys, memory, rendered display and sound
evidence separately, and never claims that a person looked; use the `run`
window for that. Without `expected.py` it only proves that the checkpoint was
reached. Captures that ran without a matching model function are reported as
not compared. PNGs, WAVs and the results file stay in `build/<name>/`. Record
the `coco.toml` machine choices in the project contract too.

The tool parses arguments before any build or launch: `--help` exits
successfully and unknown arguments exit nonzero. It verifies every firmware
file the target names before starting XRoar and ignores personal XRoar
configuration. If firmware fails, run the recovery command it prints. `run`
always opens the installed XRoar; only key scripts and captures use the
instrumented one.

For a model spec, name it after the folder (for example `my_demo_spec.py`) and
load the model with `load_expected(Path(__file__).parent)` from `coco`; several
folders cannot each have an `expected_spec.py` in one pytest run.

## Learn from evidence

State a testable question before an experiment. Record the command, target,
result, and conclusion. Distinguish measured facts, sourced facts, proposals,
and uncertainty. Update current-state notes in place; Git keeps their history.

This guidance adapts general development practices from Stacey Vetzal's
`coco-llm` project. It does not carry that project's language-model goals,
game assumptions, private paths, or reference collection into this template.

## Keep implementation tied to verified facts

A citation does not make a transcription correct. Compare each display-register
write with the cited row, including every SAM strobe and the distinction between
SAM fields and PIA fields. If a second source corrects a fact, update the code
and source note together. Do not retain the earlier transcription in a stub.

Allocate code, state, framebuffer, and stack as explicit address intervals.
A framebuffer ending at an address does not imply code must fit below its
start; check the remaining RAM above it too. Reserve state after the code or
in a separate region, rather than assigning addresses inside growing code.

Assemble the smallest complete increment before extending it. Do not leave
invented instructions, omitted endpoint updates, or a line-drawing stub as a
finished animation. For trailing lines, test both endpoint bounds and direction
changes, history wrap and tenth-line expiry, and intersections between old and
retained lines. If the build fails, report runtime behavior as untested.
