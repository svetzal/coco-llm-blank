# Projects

Each project the owner builds lives in its own folder here, named after the
idea in a few lowercase words joined by hyphens, such as `bouncing-lines`.

A project folder holds:

- `README.md`: what the owner asked for and how to run it in plain language,
  then the project contract the agent works from.
- `main.asm`: the program.
- `coco.toml`: the machine, firmware, memory layout and checkpoint settings.
- `expected.py`: an independent model of what the program must produce.

Start a project by copying [first-screen](../examples/first-screen/README.md).
Build, run and check it with `uv run python scripts/coco.py <command> projects/<name>`.
The starter keeps only this file here; your projects are yours.
