# Rules for examples

Read this file before you write, change or review anything in `examples/`.
These rules come from the owner. They apply to every example.

[First-screen](first-screen/README.md) is the reference: it obeys all of them.
Some older examples do not obey them yet. [PLAN.md](../PLAN.md) records that
work.

## One example shows one practice

An example shows one practice that an agent will use in a real project, for
example how to set up a graphics screen. It stops when that practice is shown.

- Name the practice in the first lines of the README. Say what the example
  does not do.
- Do not add a game loop, input, sound or timing to an example about another
  practice. Each of those is its own example.
- Show the variations of the practice, not only one case. First-screen sets up
  all eight graphics modes, one variant in `coco.toml` for each mode.
- Select a default that suits most games. Do not select the most familiar or
  the first case. First-screen uses CG6, a four-colour mode, not RG6.
- Give the agent what it needs to choose. Put a table of the options and their
  characteristics in the README: size, colours, memory, register values and
  the names a reader can know them by, such as `PMODE` numbers.

## An example is not a smoke test or a template

- Do not use an example to check boot, firmware, tools or the emulator. Do not
  write that it does. Those checks belong in `scripts/` and its tests, and in
  the [toolchain guide](../guidance/starter/toolchain.md).
- Do not add a value or a function that only proves that the program ran, such
  as a ready marker in RAM or a `verify_ram` that tests it. The check compares
  the full result.
- Do not put claims about host platforms or past runs in an example README.
- Do not write an example as the base of a project. Agents copy
  [`template/`](../template/README.md), not an example. An agent reads an
  example and copies the steps it needs.

## Add only what the practice needs

- Do not add setup because it sounds reasonable. Each line of code, each
  firmware file and each setting must have a specific reason. If you cannot
  give the reason, remove it.
- Keep the machine state that BASIC sets. Do not mask interrupts, move the
  stack, set the CPU clock or set the direct page unless the practice needs it.
- If a line exists only for the check, put a comment on it that says so. Then
  an agent knows to remove it from a real project. The `ready` loop in
  first-screen is an example.
- Do not load firmware that the example does not use. The starter does not
  load Extended Color BASIC on the CoCo 1 or CoCo 2.

## Test with the oracle, not with specs

- `expected.py` is the test of an example. Write it from the sourced facts and
  the requirements, never from the assembly or a snapshot.
- `scripts/coco.py check` compares the result with `expected.py`. Use
  `--video` when the practice changes what the screen shows.
- Do not add a `*_spec.py` that tests `expected.py` or `scripts/coco.py`.
- If the check could pass a wrong result, add a negative control to
  `scripts/coco_spec.py`. The wrong-SAM-mode control is an example. Run each
  new control once and see it fail before you rely on it.

## Use sources, then measure

- Read the cited pages before you write hardware-dependent code. Obey
  [reference lookup](../guidance/starter/references.md). Model memory is not
  evidence.
- Cite the book title and the PDF page in `main.asm` and in the README, beside
  each fact.
- Read a table as an image when the conversion is not clear.
- When two sources disagree, let the check settle it in the emulator. Then
  write the result and its limits. First-screen did this for the size of RG2.
- State what the check proves and what it does not prove. An emulator check is
  not a television or a physical CoCo.

## Write the README for an agent that will build

Write it with the
[simplified-technical-english](../.agents/skills/simplified-technical-english/SKILL.md)
skill and run its checker. Use these sections, in this order:

1. The practice, and what the example does not do.
2. How to choose: the table of options.
3. The steps, one for each block of code.
4. How to see each variation and how to check it, in a few lines.
5. The sources, with PDF pages.
