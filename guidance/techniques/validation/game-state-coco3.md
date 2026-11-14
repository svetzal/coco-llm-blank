# CoCo 3 bounded game-state validation

Use this note when extending the host-only game-state work into 6809 code.
The [experiment contract and commands](../../../experiments/game-state-coco3/README.md)
define the deliberately small subset. The implementation has two friendly
planets, two journey slots, atomic send rejection, scheduled arrivals, and a
16-bit turn limit. It does not port the complete 60-case host model.

## Sources directly examined

These facts were checked before writing the assembly. They establish instruction
and emulator behavior, not the correctness of our game rules.

- Tandy, [Color Computer 3 Service Manual, PDF page 16][service], inspected as
  a full-page image as well as text. The table maps task-0 registers
  `$FFA0` through `$FFA7` to the eight CPU address segments. Values `$38`
  through `$3F` select the top 64 KiB of 512 KiB RAM. The prose requires the
  compatibility bit clear and MMU enable set. That page does not establish
  the 128 KiB aliasing behavior by itself.
- Motorola, [MC6809-MC6809E Programming Manual, sections 1.8–1.10][motorola]:
  D combines A and B with A most significant; IRQ and FIRQ masks are bits 4
  and 6. [Appendix A][instructions], ADD (16-bit), BCS, BHI/BHS, ORCC and
  PSHS/PULS entries: ADDD reports carry; unsigned comparisons use carry/zero;
  ORCC can set interrupt masks; stack operations save and restore registers.
  This pass read the HTML transcription of Motorola's manual, not its PDF.
- Ciaran Anscomb, [XRoar 1.12.1 source release][xroar-source], locally examined
  `src/tcc1014/tcc1014.c`, `tcc1014_mem_cycle`, `tcc1014_write_register`, and
  `update_from_sam_register`. They specify task selection, MMU enable at bit 6,
  address translation, and R1 slow/fast CPU rates. The SAM write decoding at
  `$FFD8` clears R1; slow cycles use 16 master ticks.
- The same release's `src/coco3.c`, machine initialization and
  `coco3_dump_ram`, plus `src/ram.c`, `recalculate_bank_size`, and
  `src/ram.h`, `ram_a8`: the 128 KiB profile has 17 RAM address bits, the
  512 KiB profile has 19, and raw dumps emit physical RAM. These explain our
  use of the dump's final 64 KiB for executive pages in both configurations.
- The installed XRoar 1.12.1 manual, machine configuration, debugging and
  file-type sections, also available in the [project manual][xroar-manual]:
  CPU and ROM selection, trap actions, timeout behavior and `.ram` dumps.
  A timeout is itself a trap, so our checkpoint actions follow their PC trap.

The existing [host model](../../../experiments/game-state/game_state_model.py),
`try_send`, `begin_turn` and `land`, supplies the rules being adapted.
Its historical Undercolor sources are documented in the
[host validation note](game-state.md); this pass did not re-examine
those magazine pages and does not claim to validate their listings.

## Original adaptation and ABI

The source in [main.asm](../../../experiments/game-state-coco3/main.asm) is original.
It initializes DP and S, masks IRQ/FIRQ, selects the slow MPU rate, writes the
executive map, sets task 0, and enables native MMU mode with `$FF90=$4E`.
This value is our configuration derived from the examined register definitions.
It is not a general-purpose game's interrupt or display setup.

The functions `send`, `begin_turn`, and `end_commands` use a fixed world and
command area. A caller must supply a coherent initial world within the subset.
Registers A, B, X, Y and condition codes are scratch; U is preserved for the
evidence cursor. Every routine returns through S. Status is 0 for acceptance
and 1 for rejection; rejection reasons are intentionally not distinguished.

| World offset | Bytes | Meaning |
| --- | --- | --- |
| 0 | 2 | Current turn, big endian |
| 2 | 2 | Turn limit, big endian |
| 4 | 1 | Phase: 0 complete, 1 commands, 2 finished |
| 5 | 2 | Ships on planets 0 and 1 |
| 7 | 5 | Queue slot 0 |
| 12 | 5 | Queue slot 1 |

A queue slot contains active, destination, ship count, arrival high byte,
arrival low byte. Empty slots contain five zero bytes. Ownership is always
player 1, so no redundant owner field is stored. A command contains player,
source, destination, ship count and a two-byte positive delay.

Sending checks the entire command and queue capacity before any world store.
Arrival addition rejects carry and values beyond the limit. Starting a turn
increments the turn, resolves due or overdue slots in order, saturates friendly
reinforcement at 255, then clears each retired record. Phase guards prevent
starting the same turn twice. Ending commands only changes phase; it does not
implement production or victory.

IRQ/FIRQ are masked for the entire fixture. No NMI source, rendering or input
callback observes the intermediate stores. The evidence supports rejection
atomicity at routine boundaries, not an interrupt-safe transaction library.

## Memory budget and guards

All addresses below are CPU addresses. The program installs executive pages
`$38–$3F`; the measured dump offset is physical RAM size minus 65536 plus the
CPU address. Both selected capacities pass the same byte checks.

| Allocation | Address interval | Size or bound |
| --- | --- | --- |
| Code, driver, literals | `$3000–$3896` | 2199 bytes, correct build |
| World | `$4100–$4110` | 17 bytes |
| Command, scratch, status and completion marker | `$4200–$420B` | 12 bytes |
| Captured operation records | `$5000–$5343` | 44 records × 19 = 836 bytes |
| Reserved stack | `$7E00–$7EFF` | 256 bytes, S starts at `$7F00` |

Assembly rejects code growth beyond `$4000` or an evidence area of 4096 bytes.
The largest faulty build ends at `$389A` exclusive. No allocated region
intersects the low BASIC workspace, text display RAM, or ROM space. The driver
takes over execution and does not return to BASIC; no disk loader is tested.

XRoar starts with nonzero RAM (`-ram-init set`). The program fills
`$4000–$5FFF` with `$A5`, then writes each initial world's complete 17 bytes.
The checker verifies guards at `$40FF`, `$4111`, `$41FF`, `$420C`, `$4FFF`,
`$5344`, `$7DFF` and `$7F00`, plus completion marker `$420B=$5A`.
Each evidence record contains the entire world, status and resolved-slot mask.
The caller clears that diagnostic mask before each operation; it is not part
of world state. RAM guards detect these tested boundary writes, not every
possible stray write elsewhere in memory.

## Independent expectations and faulty controls

[vectors.py](../../../experiments/game-state-coco3/vectors.py) retains 19 cases and
44 literal expected checkpoints. The host oracle independently executes
`try_send` and `begin_turn`; it is only one check. A small explicit phase-close
adapter excludes host production and victory. It does not invoke
`finish_commands` and then pretend the resulting game has been ported.

The lifecycle starts with 20 and 5 ships. Sending 3 and 4 leaves 13 and 5;
a full-queue rejection leaves every byte unchanged. The first arrival produces
13 and 8. Sending 2 back reuses the freed slot; the next turn produces 15 and
10 and retires both records. A further turn preserves 15 and 10. These values
are written as expected checkpoints, not calculated by the assembly generator.

Other cases reject invalid planet indices, wrong player, same source and
destination, zero/excess ships, zero delay, after-limit arrivals, arithmetic
overflow and invalid phases. They cover sending every ship, overdue final-slot
arrival, saturation, arrival exactly at 65535, refusal to wrap the turn, and
ending at the configured limit.

Five compile-time faulty controls execute under both capacities:

| Control | Deliberate defect | Required counterexample |
| --- | --- | --- |
| `BAD_REJECT` | Deduct before validation | Wrong-player rejection mutates |
| `BAD_FULL` | Reuse slot 0 when full | Third send overwrites |
| `BAD_LAST` | Scan only the first slot | Overdue final-slot arrival is missed |
| `BAD_REPEAT` | Keep resolved records active | Arrivals repeat |
| `BAD_WRAP` | Omit begin-phase and limit checks | Final turn wraps |

These are original test mutations, not claims about historical source defects.
A control must fail its named literal checkpoint; arbitrary process failure
cannot count as detection. All runs must still reach the completion marker,
retain the guards and avoid the unreachable program label.

## Measured result and limitations

On macOS with Python 3.13.12, LWTOOLS 4.25 and XRoar 1.12.1, the correct build
matched all 44 checkpoints on both 128 and 512 KiB configurations. Each of the
five faulty builds was detected on both configurations. The scoped suite passed
35 specifications with 97.13% combined statement/branch coverage of the Python
runner and vectors. That percentage is not assembly coverage. Scoped Ruff
and Markdown fix/check passed.

The first negative trap used `$4100`, the world address. It fired during ROM
boot before initialization, although the final state capture passed. The final
runner uses an unreachable label in its own binary instead. A separate test
points that trap at the entry label and proves that the checker rejects it.
Additional tests reject damaged guards, a missing completion marker, truncated
captures, altered literal expectations, undetected controls, and missing,
short or corrupt ROMs. Help and invalid-option tests run with unavailable
native-tool paths and produce no build output.

Generated evidence is ignored under `build/game-state-coco3/`: binaries,
symbols, generated driver includes, RAM captures, logs, coverage and
`results.json`. The report records exact commands, executable versions and
hashes, ROM hash, source hashes, binary hashes, code bounds and mismatches.
Tests use unique subdirectories so concurrent runs do not share captures.

This is assembly and headless emulator state evidence only. There is no
framebuffer, rendered display, audio, keyboard, disk-loading, performance or
physical-hardware evidence. It establishes neither PAL/GIME 1987 support nor
other CoCo models. IRQ/NMI integration, combat, production, ownership changes,
victory and a full game loop remain outside this subset.

The parent should link this note from the shared technique index and current
validation tracker if it accepts the experiment. Those shared files and the
production scripts were deliberately left unchanged.

[service]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=16>
[motorola]: https://www.maddes.net/m6809pm/sections.htm
[instructions]: https://www.maddes.net/m6809pm/appendix_a.htm
[xroar-source]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
[xroar-manual]: https://www.6809.org.uk/xroar/doc/xroar.shtml

Publication review added a valid send after each of nine rejected commands,
without resetting the world. Both capacities pass these recovery checkpoints.
Failed checks retain a traceback and the report entries appended before failure.
A regression injects a mismatch after a real capture and verifies its retained
commands, hashes and mismatches. Capture or assessment failures before appending
a run do not retain that run in structured results; available logs remain.
