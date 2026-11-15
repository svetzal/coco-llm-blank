# Turn queue on CoCo 3

This original example keeps the state of a small turn-based game.
A player sends ships from one planet to the other, and they land some turns
later.
The program rejects a bad command without a change to the world.
It lands each journey once and stops at a turn limit.

It is not a game.
It has no display, no input, no combat and no production.
A script runs 19 cases and records the world after each of 44 steps.
The [game-state guide](../../guidance/techniques/game-state.md) explains the
design.

Ask your agent to run these steps.
Commands start in the project folder:

```sh
sh scripts/bootstrap.sh coco3
uv run python scripts/coco.py check examples/turn-queue
```

Use `check`, not `run`.
The program shows nothing.
It writes only RAM.

## The rules

These rules are our choices for this example, not rules from a source.

- Player 1 owns both planets. Each planet holds 0 to 255 ships.
- The turn and the turn limit are 16-bit numbers. The turn never wraps.
- The phase is complete, commands or finished.
- Each routine sets a status: 0 for accepted, 1 for rejected, with no reason.

`send` needs all of these:

- the commands phase and player 1
- two different planets, 0 or 1
- 1 or more ships, and no more than the source has
- a delay of 1 or more turns, with an arrival turn not past the limit
- a free slot

`send` does every check before it writes.
A rejected `send` changes no world byte.
An accepted `send` takes the ships and fills the first free slot.

`begin_turn` needs the complete phase and a turn below the limit.
It adds 1 to the turn.
Then it lands each journey whose turn has come, in slot order.
The ships add to the destination, up to 255, and the slot becomes free.
Then the phase is commands.

`end_commands` needs the commands phase.
The phase becomes finished at the turn limit, or complete before it.

## World layout

The world is 17 bytes at `$4100`.
A 16-bit value has its high byte first, as `ADDD` reads it.
[Leventhal, PDF 537][leventhal-add]

| Offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 2 | Turn |
| 2 | 2 | Turn limit |
| 4 | 1 | Phase: 0 complete, 1 commands, 2 finished |
| 5 | 2 | Ships on planets 0 and 1 |
| 7 | 5 | Slot 0: used, destination, ships, arrival turn (2 bytes) |
| 12 | 5 | Slot 1, the same |

A free slot is five zero bytes.
A command is six bytes at `$4200`: player, source, destination, ships and a
16-bit delay.

The checks use unsigned arithmetic.
`ADDD` sets the carry when the sum does not fit in 16 bits.
[Leventhal, PDF 537][leventhal-add]

After a compare, `BHI` branches when carry and zero are both clear.
`BHS` branches when carry is clear.
[Leventhal, PDF 543][leventhal-branch]
Thus `send` rejects an arrival past 65535 or past the limit before any write.

## How the check works

[turns.txt](turns.txt) holds the cases.
Each step has its action and an outcome that we wrote by hand: the status, the
slots that landed and the whole world.
`prepare.py` writes only the starting worlds and the actions into the program.

[expected.py](expected.py) compares each 19-byte record in RAM with the
hand-written outcome.
It also requires the completion byte.
It requires 8 fill bytes (`$A5`) around the world, the scratch bytes, the
records and the stack.

The cases include these steps:

- Fill both slots. Reject a third send. Land one journey and reuse its slot.
- Land two journeys on one turn. Land an overdue journey in the last slot.
- Add ships up to 255. Send every ship.
- Reject each bad command, including a 16-bit overflow. Then send again.
- Reject each routine in the wrong phase. Stop at turn 65535 without a wrap.

The spec, [turn_queue_spec.py](turn_queue_spec.py), states the rules a second
time in Python.
It checks that every hand-written outcome obeys them.
It also checks the layout, and that the model rejects changed records and
guards.

Five integration tests in `scripts/coco_spec.py` assemble a broken program.
They run it on both targets.
Each must fail first at the named step:

| Define | Fault | First failed step |
| --- | --- | --- |
| `BAD_REJECT` | Takes the ships before the delay and slot checks | queue-lifecycle 3 |
| `BAD_FULL` | Uses slot 0 when no slot is free | queue-lifecycle 3 |
| `BAD_REPEAT` | Leaves a landed slot in use | queue-lifecycle 5 |
| `BAD_LAST` | Scans only slot 0 | queue-lifecycle 8 |
| `BAD_WRAP` | Omits the phase and limit checks | queue-lifecycle 12 |

## Limits

The check proves the RAM state at one checkpoint, after all cases.
It does not test a display, input, sound, speed or physical hardware.

IRQ and FIRQ stay masked for the whole run.
Each routine finishes before the next starts.
This does not make the routines safe when an interrupt handler reads the world
during an update.

The state routines write no hardware register.
Only the setup is for the CoCo 3.
A CoCo 1 or CoCo 2 program needs a different setup, and this example does not
test it.

## Target and memory

There are two targets: XRoar `coco3`, NTSC, a 6809 at the normal low rate,
GIME 1986, and the combined `coco3.rom`.
`coco3-128` has 128 KiB RAM and `coco3-512` has 512 KiB.

The program sets these registers before it runs the cases:

- A write to `$FFD8` selects the normal low CPU rate.
  [Tepolt, PDF 62][tepolt-62]
- `$FF91=$00` selects MMU task 0. [Tandy, PDF 11][service-11]
- `$FF90=$4E` sets native mode, the MMU on, no GIME interrupts, constant DRAM
  at `$FExx`, standard SCS and 32 KiB internal ROM. [Tandy, PDF 11][service-11]
- `$FFA0-$FFA7` get `$38-$3F`, a 64 KiB map in the top of 512 KiB RAM.
  [Tandy, PDF 16][service-16]

The RAM snapshot is physical RAM.
Thus `expected.py` reads its last 64 KiB at both sizes.

| Purpose | CPU address |
| --- | --- |
| Code and script | `$3000-$3FFF` |
| World | `$4100-$4110` |
| Command and scratch | `$4200-$420D` |
| Records, 44 x 19 bytes | `$5000-$5343` |
| Stack | `$7E00-$7EFF`, top `$7F00` |

[leventhal-add]: <https://colorcomputerarchive.com/repo/Documents/Books/6809%20Assembly%20Language%20Programming%20%28Lance%20Leventhal%29.pdf#page=537>
[leventhal-branch]: <https://colorcomputerarchive.com/repo/Documents/Books/6809%20Assembly%20Language%20Programming%20%28Lance%20Leventhal%29.pdf#page=543>
[service-11]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=11>
[service-16]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=16>
[tepolt-62]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=62>
