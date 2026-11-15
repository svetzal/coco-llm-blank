# Keep turn state in a journey queue

This example keeps the state of a turn-based game in RAM. A player sends ships
from one planet to the other, and they land some turns later. Three rules
protect the state:

- A command changes the world only after every check passes. A rejected
  command changes no world byte.
- A turn lands each due journey once, in slot order, and frees its slot.
- A phase byte and a turn limit decide which routine can run. The turn does
  not wrap.

The example does not show a display, input, sound, combat, production or more
than one player. It does not make the state safe from an interrupt handler
that reads the world during an update.

The [game-state guide](../../guidance/techniques/game-state.md) explains the
design and the published listings that it comes from.

## Choose the queue design

The example uses the first option in each row. These are our design choices,
not rules from a source.

| Choice | This example | Other option | Cost of the other option |
| --- | --- | --- | --- |
| Capacity | 2 slots | `N` slots | 5 bytes for each slot. The send and turn scans pass `N` slots. |
| Slot record | Used, destination, ships, arrival turn | Add an owner or a departure turn | 1 or 2 bytes for each slot |
| Time | 16-bit turn and turn limit | 8-bit turn | Fewer bytes, but a limit of 255 turns |
| Same-turn order | Slot order | A sequence number in each slot | 1 or 2 bytes for each slot |
| Full queue | Reject the command | None that keeps the world correct | — |
| Landing above 255 ships | Keep 255 | Reject a send that can go above 255 | One more check in `send` |

- Use one capacity for the free-slot search and the landing scan. The
  [game-state guide](../../guidance/techniques/game-state.md#make-the-phase-order-part-of-the-rules)
  shows a published listing that scans fewer slots than it fills.
- Store the arrival turn, not each position on the route. This suits delayed
  orders, not arcade movement.
- On one turn, slot 0 lands before slot 1, even when slot 0 holds the newer
  journey. Use a sequence number if the order of landings matters, for
  example for battles.

## Check, commit and land

The example is the four `>>> EXAMPLE` parts of [main.asm](main.asm):

1. At `world`, the layout: 17 bytes at `$4100`. A 16-bit value has its high
   byte first, as `ADDD` and `CMPD` read it. (Leventhal, PDF 537)

   | Offset | Bytes | Meaning |
   | --- | --- | --- |
   | 0 | 2 | Turn |
   | 2 | 2 | Turn limit |
   | 4 | 1 | Phase: 0 complete, 1 commands, 2 finished |
   | 5 | 2 | Ships on planets 0 and 1, 0 to 255 each |
   | 7 | 5 | Slot 0: used, destination, ships, arrival turn (2 bytes) |
   | 12 | 5 | Slot 1, the same |

   A free slot is five zero bytes.

2. At `send`, check the command, then commit it. A command is six bytes at
   `$4200`: player, source, destination, ships and a 16-bit delay. `send`
   accepts the command only when all of these are true:

   - The phase is commands and the player is 1.
   - The source and destination are 0 or 1, and they are different.
   - The ships are 1 or more and no more than the source has.
   - The delay is 1 or more, and the arrival turn is not past the limit.
   - A slot is free.

   The commit, at `commit`, takes the ships and fills the first free slot. No
   instruction before `commit` writes a world byte.

   The arrival check uses unsigned arithmetic:

   - `ADDD` sets C when the sum does not fit in 16 bits. Then `LBCS` rejects
     the command. (Leventhal, PDF 537)
   - `BHI` branches when C and Z are both 0. Thus `LBHI` after `CMPD` rejects
     an arrival past the limit. (Leventhal, PDF 543)

3. At `begin_turn`, start the next turn. It needs the complete phase and a
   turn below the limit. It adds 1 to the turn and lands each journey whose
   arrival turn is this turn or earlier, in slot order.

   The ships add to the destination, up to 255. The slot becomes free, so the
   journey cannot land again. Then the phase is commands.

4. At `end_commands`, close the commands phase. The phase becomes finished
   at the turn limit, or complete before it.

Each routine sets `status` to 0 when it accepts and 1 when it rejects. It does
not give a reason.

The `--- CONTEXT` parts are not part of the practice:

- A runner reads a script that [prepare.py](prepare.py) writes from
  [turns.txt](turns.txt) into the build.
- For each case, the runner loads a start world.
- For each step, it calls a routine and appends a 19-byte record at `$5000`.
  The record holds the world, the status and a mask of the slots that landed.

The program keeps the machine state that BASIC sets: the interrupts, the
stack, the direct page, the CPU rate and the memory map. No routine writes a
hardware register.

The `script` label is data. The check fails if the CPU runs it.

The `BAD_*` defines are faults for the negative controls in
`scripts/coco_spec.py`. Remove them in a project.

## See and check the state

The program shows nothing on the screen. It writes only RAM. Open a terminal
in the starter folder. Copy this line to save the RAM after the last case and
print the path of the file:

```sh
uv run python scripts/coco.py snapshot examples/turn-queue   # default design
```

To check the state, paste this line:

```sh
uv run python scripts/coco.py check examples/turn-queue
```

The file [turns.txt](turns.txt) holds 19 cases with 44 steps. Each step has
an action and an outcome that we wrote by hand from the rules above. The
outcome is the status, the slots that landed and the full world.

[expected.py](expected.py) compares each record in RAM with that outcome. It
does not read the assembly.

The cases include these steps:

- Fill both slots. Reject a third send. Land one journey and use its slot
  again.
- Land two journeys on one turn. Land an overdue journey in the last slot.
- Add ships up to 255. Send every ship.
- Reject each bad command, including a 16-bit overflow. Then send again.
- Reject each routine in the wrong phase. Stop at turn 65535 without a wrap.

Five negative controls in `scripts/coco_spec.py` assemble a faulty program.
Each must fail first at the named step:

| Define | Fault | First failed step |
| --- | --- | --- |
| `BAD_REJECT` | Takes the ships before the delay and slot checks | queue-lifecycle 3 |
| `BAD_FULL` | Uses slot 0 when no slot is free | queue-lifecycle 3 |
| `BAD_REPEAT` | Does not free a landed slot | queue-lifecycle 5 |
| `BAD_LAST` | Scans only slot 0 | queue-lifecycle 8 |
| `BAD_WRAP` | Does not check the phase and the limit | queue-lifecycle 12 |

The check reads the records in the top 64 KiB of the 128 KiB snapshot. At
reset, BASIC maps the CPU addresses `$0000-$FFFF` to physical pages `$38-$3F`
(Tepolt, PDF 56 and 57, Fig. 7-2 on PDF 58).

The check uses the CoCo 3 target in [coco.toml](coco.toml): NTSC, 128 KiB,
GIME 1986 and the CoCo 3 ROM. The routines use no CoCo 3 feature.

The check proves the RAM state at one checkpoint, after all cases. It does not
prove these items:

- That no routine writes a byte outside the world and the records.
- A display, input or speed.
- An interrupt handler that reads the world during an update.
- The CoCo 1, the CoCo 2 or a physical CoCo.

## Sources

Read these pages before you change the 16-bit checks or the memory map.
Use [reference lookup](../../guidance/starter/references.md) to get them.

- Leventhal, *6809 Assembly Language Programming*, PDF 537: `ADDD` and `CMPD`
  take a 16-bit value with its high byte at the lower address. `ADDD` sets C.

- The same book, PDF 543: `BHI` branches when C and Z are both 0, and `BHS`
  branches when C is 0.

- Tepolt, *Assembly Language Programming for the CoCo3*, PDF 55–58: the reset
  initialization loads the executive map `$38-$3F`. Fig. 7-2 shows these pages
  at the top of 128 KiB and 512 KiB.

The game rules, the slot format and the cases are our own design. The
[game-state guide](../../guidance/techniques/game-state.md) cites the
magazine listings that the design adapts.
