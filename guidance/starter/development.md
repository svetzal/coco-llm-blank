# Development practice

## Establish the contract

A project is a folder, `projects/<name>/`. The folder holds `main.asm`,
`coco.toml`, `expected.py` and `README.md`.

The README starts with what the owner asked for and how to run it in plain
language. Its contract section records these items:

- The CoCo model/revision
- The XRoar machine profile
- RAM
- CPU
- Video standard
- Clock
- Firmware
- Controls
- Loader

Write the contract section before you adapt an example, assemble, or write
hardware-dependent code. Read it back to make sure that the write succeeded.
Keep `coco.toml` consistent with it.

Notes filled in after a run describe that run. They do not replace this
implementation contract.

Setup selects a starting target. Setup does not establish that an application
supports that target. Keep unknowns explicit.
Do not silently enable a 6309, more RAM, or a faster clock to pass a test.

The starter has four standard targets: `coco1`, `coco2`, `coco2b` and
`coco3`. The [standard targets](toolchain.md#standard-targets) section gives
the machine and firmware of each target. It also gives the `[targets.<name>]`
table to copy into `coco.toml`.

For a new emulator demo on the CoCo 1 with no RAM or video requirement, start
with these defaults:

- The `coco1` target table
- 32 KiB RAM
- NTSC
- A stock-clock 6809
- Color BASIC 1.1 and Extended Color BASIC 1.1
- Direct auto-run of a DECB binary in XRoar

Record these as starter defaults in the project contract. State them to the
owner. Do not claim that the owner confirmed them.

An animation needs no controls unless requested. These defaults let the first
prototype proceed.

Explicit requirements and existing project notes take precedence.
Ask when you must resolve the configuration of a physical machine or a
conflicting requirement.

These are CoCo 1 defaults. For another model, use the table of its standard
target. For each configuration choice, identify which of these it is:

- An owner requirement
- A documented default for that model
- An agent-selected prototype choice

Cite the applicable guidance for a default. State agent-selected choices to the
owner without attributing consent.

## Graphics before code

Do these two actions before you choose a graphics mode, allocate its
framebuffer, pack pixels, or write display registers:

- Load [reference lookup](references.md).
- Consult the graphics programming book.

Do not start with remembered mode tables. Do not wait until the screen looks
wrong to use the book.

If you copy display setup from a working example, still read its cited primary
passages for the selected target before reuse.
Downloading or converting a page does not count as reading it.
Reuse facts already checked in this session.

For CoCo 1/2, the [graphics guide](../techniques/graphics.md) gives the VDG
mode table, colour sets and pixel order with citations. To turn an image into
screen or sprite bytes, use `scripts/graphics.py` (run it with `--help`).

Establish these facts from passages that apply to the selected hardware:

- The mode's name and meaning in its context. Distinguish BASIC mode numbers,
  hardware control-bit encodings, and names used by the author.
  Do not assume that they are interchangeable.
  Do not transfer a CoCo 3 description to a CoCo 1/2.

- Resolution, available colors, pixel encoding, pixels per byte, row stride,
  and framebuffer size. Show how the memory sizes follow from the layout.

- The relevant control registers, field values, display-memory selection,
  alignment requirements, and shared bits that setup must preserve.

- The palette or artifact-color behavior relevant to the selected video
  standard and display. Do not treat an emulator's appearance as a mode table.

Keep a short source note beside the implementation or in existing design notes.
In the note, give what you checked, the book title and PDF page, and the values
derived from it.

Inspect table and diagram PNGs for bit ordering and labels. OCR of a register
value or bit pattern is not enough when its interpretation is uncertain.
If the book does not cover the target, find a source that does before you
continue.

For a physical model or board revision, read the passage or schematic that
supports that revision's register behavior.
A contents entry or shared chip names do not establish compatibility.
An emulator check supports the tested profile, not every physical revision that
has the same CoCo model name.

Derive expected test bytes from the sourced layout, independently of the packing
code. Check boundary pixels, row transitions, and framebuffer limits.

Then use a small display check in the emulator to inspect the chosen mode and
colors. Do this before you build the full graphics feature.
Passing arithmetic tests cannot establish that the hardware mode was selected
correctly.

If the observed display contradicts the source, revisit the target, source
scope, and setup code together.
Do not cycle through guessed register values until something looks plausible.
Do not change working behavior solely to match an unverified summary.

## Build and check

Keep deterministic computation separate from display, input, and disk I/O.
Use fixed test vectors and compare exact output bytes where appropriate.
Use LWTOOLS for assembly and XRoar for machine integration. CPU-only tests
cannot prove PIA, display, ROM, or disk behavior.

For Disk BASIC `LOADM`, assemble with `lwasm --6809 --format=decb`.
Emit symbols from the same build. Inspect the memory map for overlap among
these areas:

- BASIC workspace
- Display RAM
- Code
- Data
- Stack
- Loader needs

Initialize state before you read it. Set DP explicitly when required.
Preserve shared PIA bits when you change peripheral state.

Keep evidence separate:

- CPU tests prove arithmetic and memory transformations.
- Emulator tests prove behavior under the declared machine configuration.
- Visual checks prove that the displayed result and interaction were inspected.
- Physical-hardware checks establish behavior on the named real machine.

The exit of a process is not proof of a successful boot. Check a meaningful
program state.

A direct load of a binary is not proof that a disk image works.
Test `LOADM` from the disk.
Report minimum RAM and loading instructions with any distributable artifact.

## Check the feature you claim

Choose checks for the requested feature and declared target. A first prototype
needs a small complete path through its behavior, not every experiment or every
CoCo model.

Use the methods below when their boundary matters. Adapt their configuration
and expectations to the project. Report an untested boundary plainly.
Do not expand a narrow pass into a playability claim.

Before you inspect the run's output, write expected outcomes from the contract,
source facts and intended artwork.
Use an alternate route or lifecycle where it could reveal a bug.
Use a negative control that breaks the claimed behavior.

Do not repair a failed expectation by copying the observed result.
Resolve the difference against the requirement first.

`scripts/coco.py check` keeps each kind of evidence apart:

- Execution
- Memory
- Keys pressed through the emulated keyboard
- XRoar's rendered frame
- XRoar's mixer output

Keys, rendered frames and sound need the
[instrumented XRoar](toolchain.md#instrumented-xroar).
The tool builds it once on first use.

Its report ends with `Visual: not inspected by a person`.
A capture is not a person looking at a window, a television or a physical CoCo.

### Keyboard input

For an input claim, deliver press, hold and release through the emulated
keyboard. Then examine the resulting game state.

Declare `[keys]` in `coco.toml`. Also declare a variant whose `keys` names a
key script. `check` plays it through XRoar's keyboard API, matrix, PIA and the
program's own scanner.

Each script line takes effect at one hit of the `[keys]` label. This label is
normally the scanner's entry, so line N is held during the Nth scan.

The first word lists the held keys by the letters `[keys]` declares, or `-` for
none. The tool ignores later words, so the script can carry the expected
outcome of each step beside it.

After the last line, the tool releases every key. The
[Collect room journey](../../examples/collect-room/journey.txt) is an example.

Keep a build without keys as the no-input control. Add a wrong-key or
wrong-column control that must fail.
Check release and repress across the relevant blocked movement or restart
transition.

A test that writes logical key bits after the scanner returns tests gameplay
logic only. This is true even if the scanner ran first.
Keep that useful test separate from keyboard delivery.

XRoar API injection does not establish OS key delivery, window focus or physical
keys. Claim those only after you check those paths. The
[keyboard-controls example](../../examples/keyboard-controls/README.md) shows
the method with four broken scanners that must fail.

### Sound

A sound-call counter proves invocation, not DAC output, duration or audibility.
For a waveform claim, check the actual DAC values or the mixer output.

State whether a duration is measured or calculated. Give its basis.
A call count supplies neither.

For emulator audio output, add `--audio` to `check`, or set `audio = true` in
`[capture]`. Each checkpoint then saves XRoar's mixer output as a WAV.
The WAV is mono, 44,100 Hz and 16-bit. It runs from the start of emulation
(including ROM boot) to the checkpoint.

If `expected.py` defines `verify_sound(sound, frame)`, that function receives
`sound.samples` (a NumPy int16 array) and `sound.rate`.
The function raises `ValueError` when the sound differs.
It may return a summary for the results file.

Derive the expected pitch or level from the program's cycle counts and sources,
not from a capture. Add a muted or wrong-routing control that must fail.

[Sound slots](../../examples/sound-slots/README.md) checks its tone this way.
[Timer sound](../../examples/timer-sound/README.md) also checks that the tone
does not pause, and that a costly redraw stops cooperative sound.

The mixer output is the emulator's digital signal before any host audio driver.
It is separate evidence from host playback, listening and physical output.
Keep those limits explicit when any of them is untested.

### Artwork and display

Derive expected pixels from independently specified art rows and scene
positions. Do not derive them from art or font bytes read back from the same
emulator RAM that you check.
Copying those bytes into an oracle can check placement while accepting corrupted
art.

[Tile room](../../examples/tile-room/README.md) converts its pictures from a
drawing but keeps text drawings in `expected.py`. Its check compares the full
framebuffer and the rendered frame, and a changed pixel in the drawing must
fail. Adapt that method to the intended artwork. Do not make captured output
the new expected picture.

Screen memory cannot show a wrong display mode or bit order. For a
rendered-display claim, add `--video` to `check`, or set `video = true` in
`[capture]`. Also define `expected_frame(frame)` in `expected.py`.
It is the picture as rows of RGB values.

Each checkpoint saves a PNG of the first frame that XRoar's software renderer
completes entirely after the checkpoint. `check` compares every sample.
The program must keep the picture still for about two video frames (1/30 s)
after its checkpoint, or the capture shows later drawing.

The renderer uses S-video colours without cross-colour artifacts and shows
only the active area. For CoCo 1/2 graphics that is 512×192 samples, two per
pixel, with no 4:3 stretch.

Its colours are XRoar's palette values, not measurements of a monitor.
[first-screen](../../examples/first-screen/expected.py)
records the values for colour set 0.

Include a control that the memory check cannot catch, such as a wrong SAM mode
or a reversed bit order. Also open the PNG with an image viewer. The
[display test](../techniques/colour.md#make-a-display-test-before-making-the-art)
lists the controls that the examples already run.

Static captures do not establish animation cadence or tearing.
For those tasks, obey the [animation guide](../techniques/animation.md).
Host presentation and physical displays remain separate checks.

### Test-harness controls for dynamic games

A game with moving opponents, random events or levels changes with each rule
you adjust. Do not write a key script that plays the game as a person would.
Do not model the whole game so that a script can follow it. That work takes much time and
many tokens, and a small change to a rule breaks it.

Build test-harness controls into the program instead. Each control removes one
dynamic part, so a short key script can reach one game element and check it.
Examples of controls:

- The player does not lose a life when an opponent hits it.
- The opponents do not move, or they move on a fixed path.
- The random-number generator starts from a fixed seed.
- The game starts at level N, or with a fixed arena layout.
- There is only one opponent, at a fixed position.
- A collision sets a flag but does not end the game.

Obey these rules for controls:

1. Select each control with an assembler define, for example
   `ifdef NO_DEATH`. Declare a `coco.toml` variant for each set of controls
   that a check uses. The main build has no controls.
2. Put a comment on each control that says it is only for the check.
3. Use one set of controls to check one element. Write a short script, and in
   `expected.py` model only that element.
4. Keep at least one check of the main build without controls. For example,
   check the first frames of play and the no-input control. Then the checks
   show that no control is active in the game that the owner plays.
5. A pass with a control does not prove the behavior that the control removes.
   Check that behavior with its own short script. For example, let one
   opponent hit a player that does not move.
6. List the controls and the checks that use them in the project's README.

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

Besides its `README.md`, the folder holds three files. Start with a copy of
[`template/`](../../template/README.md). It prints a message with the Color
BASIC ROM and returns to BASIC. Add `expected.py` with the first feature that
you can check.

Do not copy an example folder as the base of a project. Each example shows one
practice.

- `main.asm`: the program, assembled as a DECB binary with a symbol dump.

- `coco.toml`: the contract the tool runs.

  - Each `[targets.<name>]` table names the XRoar machine, CPU, video standard,
    VDG, RAM and firmware files. The first table is the default.

  - `[memory]` requires labels at or below addresses.

  - `[check]` names the checkpoint label reached once per completed frame and
    the frames to snapshot. It also names a label that must never run, and
    where the screen starts.

  - The snapshot holds the physical RAM of the target. On a target that maps
    its memory, such as the CoCo 3, the screen can be at a different offset.
    Set `screen` in that `[targets.<name>]` table to replace `[check].screen`
    for that target only.

  - Optional `[variants.<name>]` tables add assembler defines, a key script
    (`keys = "file"`), or both.

  - A variant can also name the targets that it applies to, for example
    `targets = ["coco3-128", "coco3-512"]`. Each name must be a
    `[targets.<name>]` table. Without `targets`, the variant applies to every
    target. `targets` alone does not make a variant.

  - `[keys]` names the label where each script line takes effect (`at`). It
    also maps the script's letters to XRoar key names (`letters`).

  - `[capture]` turns on `video` or `audio` for every check.

  - `prepare` names a Python file whose `prepare(output)` writes include files
    first.

- `expected.py` (optional): the independent model.
  - `expected_screen(frame)` returns the exact screen bytes.
  - `verify_ram(ram, symbols, frame)` raises `ValueError` when the state
    differs. `ram` is the physical snapshot of the target. Use the `target`
    keyword to find the addresses on each target.
  - `expected_frame(frame)` returns the rendered picture.
  - `verify_sound(sound, frame)` judges the mixer output.
  - The tool uses each of those two functions only when that capture runs.
  - With variants, every function also receives the variant name as its last
    argument.
  - A function that declares a `target` parameter also receives `target=`,
    the target name. An example is `expected_frame(frame, variant, target)`.
    Use it when the picture or the memory layout differs between machines.
  - Write the model from sourced facts and requirements, never from the
    assembled bytes or a captured snapshot.

`check` builds the main program for every target, or only for `--target`.
It builds a variant only for the targets that the variant applies to. The
results file and the report name the builds that ran on that target. They
also name each variant that applies only to other targets.

`run`, `build` and `snapshot` with `--variant` use the first target of the
variant. If `--target` names a target that the variant does not apply to, the
tool stops before it builds.

For each build, `check` does these actions:

- It starts from nonzero RAM.
- It snapshots each frame.
- It requires that the unreachable label leaves no snapshot.
- It compares every screen byte.
- Then it runs the model.

It reports execution, keys, memory, rendered display and sound evidence
separately. It never claims that a person looked. Use the `run` window for
that.

Without `expected.py` it only proves that the program reached the checkpoint.
It reports captures that ran without a matching model function as not compared.

PNGs, WAVs and the results file stay in `build/<name>/`. Also record the
machine choices from `coco.toml` in the project contract.

The tool parses arguments before any build or launch. `--help` exits
successfully and unknown arguments exit nonzero.

It checks every firmware file that the target names before it starts XRoar.
It ignores personal XRoar configuration.
If firmware fails, run the recovery command that the tool prints.

`run` always opens the installed XRoar. Only key scripts and captures use the
instrumented one.

`expected.py` and `coco.py check` are the test of a project. Do not write a
spec that tests `expected.py` or `coco.py`. If the check could pass a wrong
result, break the program once in a copy and see the check fail.

## Learn from evidence

State a testable question before an experiment. Record the command, target,
result, and conclusion.
Distinguish measured facts, sourced facts, proposals, and uncertainty.
Update current-state notes in place. Git keeps their history.

This guidance adapts general development practices from Stacey Vetzal's
`coco-llm` project. It does not carry that project's language-model goals,
game assumptions, private paths, or reference collection into this template.

## Keep implementation tied to verified facts

A citation does not make a transcription correct. Compare each display-register
write with the cited row. Include every SAM strobe and the distinction between
SAM fields and PIA fields.

If a second source corrects a fact, update the code and source note together.
Do not retain the earlier transcription in a stub.

Allocate code, state, framebuffer, and stack as explicit address intervals.
A framebuffer that ends at an address does not imply that code must fit below
its start. Check the remaining RAM above it too.

Reserve state after the code or in a separate region. Do not assign addresses
inside growing code.

Assemble the smallest complete increment before you extend it.
Do not leave invented instructions, omitted endpoint updates, or a line-drawing
stub as a finished animation.
If the build fails, report runtime behavior as untested.

For trailing lines, test these cases:

- Both endpoint bounds and direction changes
- History wrap and tenth-line expiry
- Intersections between old and retained lines
