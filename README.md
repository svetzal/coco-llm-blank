# Build something for the Color Computer

Make a game, animation, or experiment for the Tandy Color Computer with your
coding agent. This starter gives your agent project guidance, tools, and access
to original reference books. You bring the idea.

You do not need to know assembly language or prepare a development environment
before you start. Ask your agent to handle setup as part of building your project.
You can try the result on your current computer using XRoar, an emulator that
acts like a Color Computer. You do not need the original hardware. For now it
works on Macs with Apple silicon and on Ubuntu Linux 24.04; Windows and older
Intel Macs aren't supported yet.

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

## Building, and solving problems in a lab

Your agent works in one of two modes. The first line of each reply tells you
which, for example:

```text
BUILD · bouncing-lines
LAB · crackly-sound (from bouncing-lines)
```

**Building** is where you spend most of your time. You describe your game or
demo, and the agent makes it from the starter's guides and examples. Your
project stays in its own folder and grows as you ask for changes.

Sometimes a problem has no ready answer: the sound crackles, the graphics are
too slow, or a key press is missed. Then the agent can open a **lab**: a
separate session focused on that one problem. In a lab the agent:

1. writes down the question, such as "why does the sound crackle while the
   screen redraws?";
2. reads the original books and manuals, and tries small test programs until
   it finds an answer that works;
3. explains what it found in plain words;
4. adds the answer to the starter's guides or examples, so this and later
   projects can use it;
5. cleans up its test programs and returns to your project to apply the fix.

The agent may suggest a lab when it gets stuck, but it waits for you to agree.
You can also ask for one yourself:

> Open a lab: the sound crackles whenever the ball moves.

A lab can take longer than a normal change, because it tests ideas before
settling on one. You can stop it at any time:

> Close the lab and go back to building.

If you stop partway, your project notes record the open lab. Next time the
agent asks whether to continue it or carry on building. The improvements a lab
makes stay in your copy of the starter unless you choose to share them.

## What to expect today

This is a concept in development, the idea of having a repository like this
that guides an agent to help you in different ways at different times.

Building games and demos for the CoCo is in some ways an arcane art. In the
1980s and 1990s we had various magazines and books that helped explain the
hardware and capabilities, brought us games and various techniques for
building better games. But a lot of this knowledge is very hard to find,
or was never published, and there are still new things to discover as we use
these computers in a modern context.

The quality of the games or demos you produce is going to hinge on guides
already in this repository that are being built up over time, or on a lab
that you start to have the agent help you research your challenge. The agent
may find new books or blogs or articles on the Internet that may help find
a solution. Or the agent may just have to put its head down and try to solve
the problem itself.

Your attention to detail, your diligence in playability and user experience
will have far more impact on the quality of the game it produces than the agent
technology itself.

There will be problems you can't solve (I mean, it's a 40 year old computer),
there will be problems you might find a brand new solution to that nobody has
found before, there will be problems that someone else has published a solution
to, and there will be problems already solved by guides here in this repo.

Most importantly, have fun! And if you have trouble with it, drop me a line.
My goal is to enable, 40 years later, people to have the same sense of learning
and exploration that I and many others remember from our youth with these old
computers. There are fewer and fewer places to go to learn so deeply about
computing technology than these computers that inspired and drove our entire
personal computing field.

## Look inside when you are ready

The games and demos you build are written in 6809 assembly language, the
Color Computer's own machine language. Your agent writes it for you, and you
can read it in your project's `main.asm`. The starter also has some Python code
that automates the tedious technical steps: setting up tools, assembling your
program, launching the emulator and checking the results. You never need to
touch it.

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
