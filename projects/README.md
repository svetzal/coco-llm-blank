# Projects

Each project the owner builds is in its own folder here. The folder name is the
idea in a few lowercase words joined by hyphens, such as `bouncing-lines`.

A project folder holds:

- `README.md`: what the owner asked for and how to run it in plain language,
  then the project contract the agent works from.
- `main.asm`: the program.
- `coco.toml`: the machine, firmware, memory layout and checkpoint settings,
  plus any key scripts and screen or sound captures the checks use.
- `expected.py`: an independent model of what the program must produce: screen
  memory and state, and optionally the rendered picture and the sound.
- Key scripts (optional): text files of keys to hold at each keyboard scan,
  named by a variant in `coco.toml`.

To start a project, copy [`template/`](../template/README.md) to a new folder
here. Do not copy an example folder. Each example shows one practice. Use it as
a reference.

Build, run and check it with `uv run python scripts/coco.py <command> projects/<name>`.
[Development practice](../guidance/starter/development.md#reusable-launchers)
describes every setting and command. The starter keeps only this file here.
Your projects are yours.
