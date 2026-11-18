# Build something for the Colour Computer

Make a game, animation, or experiment for the Tandy Colour Computer with your
coding agent. This starter gives your agent project guidance, tools, and access
to original reference books. You bring the idea.

You do not need to know assembly language or prepare a development environment
before you start. Ask your agent to handle setup as part of building your
project.

You can try the result on your current computer using XRoar, an emulator that
acts like a Colour Computer. You do not need the original hardware.

The starter supports Macs with Apple silicon and PCs running Ubuntu 24.04.
Automated checks run on both platforms. A full first-time setup on a freshly
installed desktop still needs testing on each platform. Windows and Intel Macs
are outside the supported platforms. See [supported hosts](guidance/starter/toolchain.md#supported-hosts).

## Start with your agent

Open Claude Code, Codex, OpenCode, or another coding agent that can work with
files and run programs on your computer. A chat window without those abilities
cannot do the setup for you.

Copy this prompt into your agent. Replace the last line with your own idea,
or keep it for a first project:

```text
Start a new project from https://github.com/svetzal/retro-explorer-coco.
Read its AGENTS.md and handle setup for me. I'm a beginner.

Build a CoCo 1 animation with bouncing lines and a ten-line trail.
```

The repository address is enough for your agent to find the starter. You do not
need to download this repository yourself or type its setup commands.
Your agent may ask where to put your project, or ask for permission to install
tools.

If this starter is already open in your agent, ask it to use the current
folder. Ask it not to make another copy.

## Describe what you want to make

Start with what you want to see or do. For example:

- "Make a game where I move a paddle to keep a ball on the screen."
- "Draw a colourful pattern that changes when I press a key."
- "Help me learn how to draw a sprite, one small step at a time."

Name your Colour Computer model if you know it. The starter lets you select
a CoCo 1, CoCo 2, CoCo 2B or CoCo 3. A CoCo 2B has a different video chip,
the MC6847T1. Its initial reference collection mainly covers CoCo 1 and 2.
Your agent may need more references for a CoCo 3 project.

If you are unsure, ask for a CoCo 1 project in the emulator. The agent has
starting defaults for that choice. Tell it if you want to use a real machine.
The memory and equipment of that machine affect what the project can run.

## What happens next

Your agent checks the tools. It downloads the references and firmware that
your machine needs. The first setup can take a while. Later work reuses the
downloads.

Your agent names your project and keeps it in its own folder, such as
`projects/bouncing-lines`. The README in that folder says what you asked for
and how to run it.

Ask for a small working result before you add more features. Then describe
what you want to change. Keep working in the same starter folder so your agent
can reuse your projects and the references.

## Building, and solving problems in a lab

Your agent usually works in one of two modes. The first line of each reply tells you
which mode, for example:

```text
BUILD · bouncing-lines
LAB · crackly-sound (from bouncing-lines)
```

**Building** is where you spend most of your time. You describe your game or
demo, and the agent makes it from the starter's guides and examples. Your
project stays in its own folder and grows as you ask for changes.

Sometimes a problem has no ready answer. For example, the sound crackles, the
graphics are too slow, or a key press is missed. Then the agent can open a
**lab**. A lab is a separate session that focuses on that one problem. In a lab
the agent does these steps:

1. It writes down the question, such as "why does the sound crackle while the
   screen redraws?"
2. It reads the original books and manuals. It tries small test programs until
   it finds an answer that works.
3. It explains what it found in plain words.
4. It adds the answer to the starter's guides or examples, so this project and
   later projects can use it.
5. It cleans up its test programs. Then it returns to your project to apply
   the fix.

The agent may suggest a lab when it gets stuck, but it waits for you to agree.
You can also ask for one yourself:

> Open a lab: the sound crackles whenever the ball moves.

A lab can take longer than a normal change, because it tests ideas before it
settles on one. You can stop it at any time:

> Close the lab and go back to building.

If you stop partway, your project notes record the open lab. Next time, the
agent asks whether to continue the lab or to continue building. The
improvements a lab makes stay in your copy of the starter unless you choose to
share them.

A third mode, **SYSTEM**, changes the starter itself: its tools and its
guides. It is for people who maintain the starter. The agent starts it only
when you ask for SYSTEM mode by name.

## What to expect today

This is a concept in development. The idea is a repository like this, one
that guides an agent to help you in different ways at different times.

Building games and demos for the CoCo is in some ways an arcane art. In the
1980s and 1990s we had various magazines and books that helped explain the
hardware and capabilities. They brought us games and various techniques for
building better games. But a lot of this knowledge is very hard to find,
or was never published. And there are still new things to discover as we use
these computers in a modern context.

The quality of the games or demos you produce is going to hinge on two
things. One is the guides already in this repository, which are being built up
over time. The other is a lab that you start, to have the agent help you
research your challenge. The agent
may find new books or blogs or articles on the Internet that may help find
a solution. Or the agent may just have to put its head down and try to solve
the problem itself.

Your attention to detail matters, and so does your diligence in playability
and user experience. They will have far more impact on the quality of the game
than the agent technology itself.

There will be problems you can't solve. (I mean, it's a 40 year old computer,
you won't be building Call of Duty or First Light.) There will be problems you
might find a brand new solution to that nobody has found before. There will be
problems that someone else has published a solution to. And there will be
problems already solved by guides here in this repo.

Most importantly, have fun! And if you have trouble with it, drop me a line.
My goal is to enable people, 40 years later, to have the same sense of learning
and exploration. I and many others remember it from our youth with these old
computers. There are fewer and fewer places to go to learn so deeply about
computing technology. These computers inspired and drove our entire personal
computing field.

## Play Arena Blaster

Arena Blaster is an original arena shooter for the CoCo 1. An owner built it with a coding
agent, one small increment at a time. It is in
[`projects/arena-blaster`](projects/arena-blaster/README.md). Its README
records each request and how the agent tested it.

To play it, open a terminal in the starter folder. Prepare the tools and
the CoCo 1 firmware once:

```sh
sh scripts/bootstrap.sh coco1
```

Start the game from the starter folder. The first line lets this terminal find
a copy of `uv` in your home folder.

```sh
export PATH="$PATH:$HOME/.local/bin"
uv run python scripts/coco.py run projects/arena-blaster
```

To run it from a Disk BASIC disk, use this command:

```sh
uv run python scripts/coco.py disk projects/arena-blaster --run
```

Use W, A, S and D to move. Use O, K, L and the semicolon key to shoot up, left,
down and right. Hold two keys to move or shoot on a diagonal. If you do
not touch a key on the title screen for 10 seconds, a demo shows the
enemies, the gifts and the jinxes. Close the XRoar window to stop.

## Look inside when you are ready

The games and demos you build are in 6809 assembly language, the Color
Computer's own machine language. Your agent writes it for you, and you can
read it in your project's `main.asm`.

The starter also has some Python code that automates the tedious technical
steps:

- setting up tools
- assembling your program
- launching the emulator
- checking the results

You never need to touch that code.

You can start without reading these pages. Choose one when you need it:

- [Play collect-room](examples/collect-room/README.md), a complete small game
  for the documented emulator configurations of CoCo 1 and CoCo 2B.
- [Projects](projects/README.md) for the games you can play in this copy.
- [Examples](examples/README.md) for smaller programs to build and study.
- [Agent guidance](guidance/README.md): how your agent uses this starter, and the
  game and demo techniques it uses.
- [Agent instructions](AGENTS.md) for starting work.
- [PLAN.md](PLAN.md) for outstanding work.

## Books, firmware, and licensing

The starter downloads reference books and firmware from the
[Color Computer Archive](https://colorcomputerarchive.com/). It keeps those files
on your computer, outside the files Git tracks. The repository does not include
copies of the books or firmware.

The starter's code and original guidance use the [MIT license](LICENSE).
That license does not cover downloaded books, firmware, or converted pages.
Those materials retain their own copyright and licensing.
