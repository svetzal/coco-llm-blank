# Development practice

## Establish the contract

Record the CoCo model, RAM, CPU, video standard, clock, controls, and loader
before writing hardware-dependent code. Setup selects a starting target;
it does not establish that an application supports it. Keep unknowns explicit.
Do not silently enable a 6309, more RAM, or a faster clock to pass a test.

For a new CoCo 1 emulator demo with no RAM or video requirement, start with
32 KiB RAM, NTSC, a stock-clock 6809, and direct DECB binary auto-run in XRoar.
Record these as starter defaults in `local/PROJECT.md` and state them to the
owner; do not claim the owner confirmed them. An animation needs no controls
unless requested. These defaults let the first prototype proceed. Explicit
requirements and existing project notes take precedence; ask when a physical
machine's configuration or a conflicting requirement must be resolved.

## Graphics before code

Load [reference lookup](references.md) and consult the graphics programming book
before choosing a graphics mode, allocating its framebuffer, packing pixels,
or writing display registers. Do not start with remembered mode tables and use
the book only after the screen looks wrong.

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

## Learn from evidence

State a testable question before an experiment. Record the command, target,
result, and conclusion. Distinguish measured facts, sourced facts, proposals,
and uncertainty. Update current-state notes in place; Git keeps their history.

This guidance adapts general development practices from Stacey Vetzal's
`coco-llm` project. It does not carry that project's language-model goals,
game assumptions, private paths, or reference collection into this template.
