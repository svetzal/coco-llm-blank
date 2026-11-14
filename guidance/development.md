# Development practice

## Establish the contract

Record the CoCo model, RAM, CPU, video standard, clock, controls, and loader
before writing hardware-dependent code. Setup selects a starting target;
it does not establish that an application supports it. Keep unknowns explicit.
Do not silently enable a 6309, more RAM, or a faster clock to pass a test.

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
