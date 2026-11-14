# Development practice

## Establish the contract

Record the CoCo model/revision, XRoar machine profile, RAM, CPU, video standard,
clock, controls, and loader in `local/PROJECT.md` before adapting an example,
assembling, or writing hardware-dependent code. Read the file back to verify
the write succeeded. Notes filled in after a run describe that run; they do not
replace this implementation contract.
Setup selects a starting target;
it does not establish that an application supports it. Keep unknowns explicit.
Do not silently enable a 6309, more RAM, or a faster clock to pass a test.

For a new CoCo 1 emulator demo with no RAM or video requirement, start with
32 KiB RAM, NTSC, a stock-clock 6809, and direct DECB binary auto-run in XRoar.
Record these as starter defaults in `local/PROJECT.md` and state them to the
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

### Keyboard input

For an input claim, deliver press, hold and release through the actual keyboard
adapter and observe the resulting game state. Use the
[keyboard experiment's injection boundary](../techniques/validation/keyboard-controls.md#actual-injection-boundary)
and [failure controls](../techniques/validation/keyboard-controls.md#reproduction-and-failure-controls)
as a starting method. It drives XRoar's keyboard API through its matrix, PIA
and the 6809 scanner. Adapt its keys and profile to the game; a passing example
does not validate a new scanner.

Writing logical key bits after the scanner returns tests gameplay logic only,
even if the scanner executed first. Keep that useful test separate from keyboard
delivery. Include a no-input or wrong-column control, and check release and
repress across the relevant blocked movement or restart transition. XRoar API
injection does not establish OS key delivery, window focus or physical keys;
claim those only after checking those paths.

### Sound

A sound-call counter proves invocation, not DAC output, duration or audibility.
For a waveform or duration claim, use actual DAC values and event timestamps,
following the [DAC timing method](../techniques/validation/audio-timing.md) or its retained
[CoCo 2 experiment](../../experiments/sound-coco2/README.md). State whether a duration
is measured or calculated and give its basis; a call count supplies neither.

For emulator audio output, adapt the
[mixer PCM capture method](../../experiments/audio-output/README.md), with an
independent expected signal and a muted or wrong-routing control. PCM captured
from XRoar is separate evidence from host playback, listening and physical
output. Keep those limits explicit when any of them is untested.

### Artwork and display

Derive expected pixels from independently specified art rows and scene positions,
not from art or font bytes read back from the same emulator RAM being checked.
Copying those bytes into an oracle can check placement while accepting corrupted
art. The [asset-loading experiment](../../experiments/asset-loading/README.md#what-the-target-checks-establish)
compares literal artwork and the full framebuffer, with complemented-picture
and swapped-assignment controls. Adapt that method to the intended artwork;
do not make captured output the new expected picture.

A PNG decoded from RAM is a framebuffer view, not an emulator renderer capture.
For a rendered-display claim, use the
[renderer method and wrong-mode control](../../experiments/display-validation/README.md#acceptance-and-negative-controls)
within its stated target scope. Static captures do not establish animation
cadence or tearing; for those tasks follow the
[animation guide](../techniques/animation.md). Host presentation and physical displays
remain separate checks.

## Reusable launchers

Parse arguments before setup, downloads, builds, or emulator calls. `--help`
must print usage and exit successfully without those side effects; reject
unknown arguments with a nonzero exit. Probe these paths with a recording
process substitute so a help check cannot accidentally open XRoar.

Before launch, call `roms.verify_installed` for every ROM required by the chosen
machine and loader, then pass its returned absolute paths to XRoar. Checking
only the BASIC ROM's existence misses a missing Extended BASIC ROM. Use the
existing provisioner for recovery and verify again before launch; stop on
validation failure. Test the partially installed case as well as missing and
corrupt firmware. Do not duplicate ROM validation in a shell wrapper.

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
