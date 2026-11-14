# Build something for the Color Computer

Make a game, animation, or experiment for the Tandy Color Computer with your
coding agent. This starter gives your agent project guidance, tools, and access
to original reference books. You bring the idea.

You do not need to know assembly language or prepare a development environment
before you start. Ask your agent to handle setup as part of building your project.
You can try the result on your current computer using XRoar, an emulator that
acts like a Color Computer. You do not need the original hardware.

## Start with your agent

Open Claude Code, Codex, OpenCode, or another coding agent that can work with
files and run programs on your computer. A chat window without those abilities
cannot do the setup for you.

Copy this prompt into your agent. Replace the last line with your own idea,
or keep it for a first project:

```text
Start a new project from https://github.com/svetzal/coco-llm-blank.
Read its AGENTS.md and handle setup for me. I'm a beginner.

Build a CoCo 1 animation with bouncing lines and a ten-line trail.
```

The repository address is enough for your agent to find the starter. You do not
need to download this repository yourself or type its setup commands.
Your agent may ask where to put your project or request permission to install tools.

Already have this starter open in your agent? Ask it to use the current folder
instead of making another copy.

## Describe what you want to make

Start with what you want to see or do. For example:

- "Make a game where I move a paddle to keep a ball on the screen."
- "Draw a colourful pattern that changes when I press a key."
- "Help me learn how to draw a sprite, one small step at a time."

Name your Color Computer model if you know it. The starter supports selecting
CoCo 1, 2, or 3. Its initial reference collection mainly covers CoCo 1 and 2.
Your agent may need more references for a CoCo 3 project.

If you are unsure, ask for a CoCo 1 project in the emulator. The agent has
starting defaults for that choice. Tell it if you want to use a real machine.
Its memory and equipment affect what the project can run.

## What happens next

Your agent checks the tools and downloads the references and firmware needed
for your machine. The first setup can take a while; later work reuses downloads.
Your agent names your project and keeps it in its own folder, such as
`projects/bouncing-lines`. That folder's README says what you asked for and how
to run it. Ask for a small working result before adding more features, then
describe what you want to change. Keep working in the same starter folder so
your agent can reuse your projects and the references.

## What to expect today

This is an early starter, not a finished game or a guarantee that an agent will
get every program right. The guidance asks agents to check original sources and
test their work. Scanned books can still contain conversion errors.

Apple Silicon Macs and Ubuntu 24.04 have automated checks. The Ubuntu tool
installation and emulator memory check also pass in a clean container.
macOS support means Apple Silicon; Intel Macs are outside scope.
Windows setup is not covered yet.

Your agent can handle setup commands when its permissions allow them. Some
installs need your approval or a password that only you can enter.
The setup entry point installs assembly and emulator tools on macOS and
Ubuntu 24.04. Other Linux distributions still need agent-led installation.
You do not need to prepare those tools before giving your agent the prompt.

Projects currently use 6809 assembly, the Color Computer's machine-level
programming language. Your agent writes that code for you. C development is
not included yet.

## Look inside when you are ready

You can start without reading these pages. Choose one when you need it:

- [Play collect-room](examples/collect-room/README.md), a complete small game
  for the documented CoCo 1 and CoCo 2B emulator configurations.
- [Examples](examples/README.md) for smaller programs to build and study.
- [Agent guidance](guidance/README.md): how your agent uses this starter, and the
  game and demo techniques it draws on.
- [Experiments](experiments/README.md) for reproducing individual measurements.
- [Agent instructions](AGENTS.md) for starting work; [PLAN.md](PLAN.md) for
  outstanding work.

## Books, firmware, and licensing

The starter downloads reference books and firmware from the
[Color Computer Archive](https://colorcomputerarchive.com/). It keeps those files
on your computer, outside the files Git tracks. The repository does not include
copies of the books or firmware.

The starter's code and original guidance use the [MIT license](LICENSE).
That license does not cover downloaded books, firmware, or converted pages.
Those materials retain their own copyright and licensing.
