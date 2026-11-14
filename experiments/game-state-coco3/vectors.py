"""Literal checkpoints and a separately executed existing host oracle."""

import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/game-state"))
from game_state_model import Journey, Phase, Planet, World, begin_turn, changed, try_send


class State(BaseModel):
    model_config = ConfigDict(frozen=True)
    turn: int = 1
    limit: int = 4
    phase: int = 1
    ships: tuple[int, int] = (20, 5)
    queue: tuple[tuple[int, int, int] | None, tuple[int, int, int] | None] = (None, None)

    def raw(self) -> bytes:
        header = self.turn.to_bytes(2, "big") + self.limit.to_bytes(2, "big")
        slots = b"".join(
            bytes([1, q[0], q[1]]) + q[2].to_bytes(2, "big") if q else bytes(5) for q in self.queue
        )
        return header + bytes([self.phase, *self.ships]) + slots


class Step(BaseModel):
    action: str
    command: tuple[int, int, int, int, int] = (1, 0, 1, 3, 1)
    expected: State
    status: int = 0
    resolved: int = 0


class Case(BaseModel):
    name: str
    initial: State
    steps: tuple[Step, ...]


def fixtures() -> list[Case]:
    empty = State()
    queued = State(ships=(13, 5), queue=((1, 3, 2), (1, 4, 3)))
    cases = [
        Case(
            name="queue-lifecycle",
            initial=empty,
            steps=(
                Step(action="send", expected=State(ships=(17, 5), queue=((1, 3, 2), None))),
                Step(action="send", command=(1, 0, 1, 4, 2), expected=queued),
                Step(action="send", expected=queued, status=1),
                Step(action="end_commands", expected=queued.model_copy(update={"phase": 0})),
                Step(
                    action="begin_turn",
                    expected=State(turn=2, ships=(13, 8), queue=(None, (1, 4, 3))),
                    resolved=1,
                ),
                Step(
                    action="send",
                    command=(1, 1, 0, 2, 1),
                    expected=State(turn=2, ships=(13, 6), queue=((0, 2, 3), (1, 4, 3))),
                ),
                Step(
                    action="end_commands",
                    expected=State(turn=2, phase=0, ships=(13, 6), queue=((0, 2, 3), (1, 4, 3))),
                ),
                Step(action="begin_turn", expected=State(turn=3, ships=(15, 10)), resolved=3),
                Step(action="end_commands", expected=State(turn=3, phase=0, ships=(15, 10))),
                Step(action="begin_turn", expected=State(turn=4, ships=(15, 10))),
                Step(action="end_commands", expected=State(turn=4, phase=2, ships=(15, 10))),
                Step(
                    action="begin_turn", expected=State(turn=4, phase=2, ships=(15, 10)), status=1
                ),
            ),
        ),
        Case(
            name="overdue-saturation-last-slot",
            initial=State(turn=2, phase=0, ships=(250, 5), queue=(None, (0, 10, 1))),
            steps=(Step(action="begin_turn", expected=State(turn=3, ships=(255, 5)), resolved=2),),
        ),
        Case(
            name="maximum-turn",
            initial=State(turn=65534, limit=65535),
            steps=(
                Step(
                    action="send",
                    expected=State(
                        turn=65534, limit=65535, ships=(17, 5), queue=((1, 3, 65535), None)
                    ),
                ),
                Step(
                    action="end_commands",
                    expected=State(
                        turn=65534, limit=65535, phase=0, ships=(17, 5), queue=((1, 3, 65535), None)
                    ),
                ),
                Step(
                    action="begin_turn",
                    expected=State(turn=65535, limit=65535, ships=(17, 8)),
                    resolved=1,
                ),
                Step(
                    action="send", expected=State(turn=65535, limit=65535, ships=(17, 8)), status=1
                ),
                Step(
                    action="end_commands",
                    expected=State(turn=65535, limit=65535, phase=2, ships=(17, 8)),
                ),
                Step(
                    action="begin_turn",
                    expected=State(turn=65535, limit=65535, phase=2, ships=(17, 8)),
                    status=1,
                ),
            ),
        ),
        Case(
            name="send-all",
            initial=empty,
            steps=(
                Step(
                    action="send",
                    command=(1, 0, 1, 20, 3),
                    expected=State(ships=(0, 5), queue=((1, 20, 4), None)),
                ),
            ),
        ),
    ]
    invalid = {
        "wrong-player": (2, 0, 1, 3, 1),
        "source-range": (1, 2, 1, 3, 1),
        "destination-range": (1, 0, 255, 3, 1),
        "same-planet": (1, 0, 0, 3, 1),
        "zero-count": (1, 0, 1, 0, 1),
        "too-many": (1, 0, 1, 21, 1),
        "zero-delay": (1, 0, 1, 3, 0),
        "after-limit": (1, 0, 1, 3, 4),
        "addition-overflow": (1, 0, 1, 3, 65535),
    }
    cases += [
        Case(
            name=name,
            initial=empty,
            steps=(
                Step(action="send", command=cmd, expected=empty, status=1),
                Step(
                    action="send",
                    command=(1, 0, 1, 3, 1),
                    expected=State(ships=(17, 5), queue=((1, 3, 2), None)),
                ),
            ),
        )
        for name, cmd in invalid.items()
    ]
    for name, action, state in (
        ("send-complete", "send", State(phase=0)),
        ("send-finished", "send", State(phase=2)),
        ("begin-commands", "begin_turn", empty),
        ("end-complete", "end_commands", State(phase=0)),
        ("end-finished", "end_commands", State(phase=2)),
        ("limit-complete", "begin_turn", State(turn=4, phase=0)),
    ):
        cases.append(
            Case(name=name, initial=state, steps=(Step(action=action, expected=state, status=1),))
        )
    return cases


def to_host(state: State) -> World:
    phase = (Phase.COMPLETE, Phase.COMMANDS, Phase.FINISHED)[state.phase]
    return World(
        turn=state.turn,
        turn_limit=state.limit,
        phase=phase,
        pending_players=(1,) if state.phase == 1 else (),
        planets=tuple(Planet(owner=1, ships=s) for s in state.ships),
        journeys=tuple(
            Journey(owner=1, destination=q[0], ships=q[1], arrival=q[2]) if q else None
            for q in state.queue
        ),
    )


def host_step(world: World, step: Step) -> tuple[World, int, int]:
    if step.action == "send":
        result, status = try_send(world, *step.command)
        return result, int(status != "accepted"), 0
    if step.action == "begin_turn":
        try:
            result, slots = begin_turn(world)
        except ValueError:
            return world, 1, 0
        return result, 0, sum(1 << i for i in slots)
    # Deliberate adapter: phase close only. Host victory/production are excluded.
    if world.phase != Phase.COMMANDS:
        return world, 1, 0
    phase = Phase.FINISHED if world.turn == world.turn_limit else Phase.COMPLETE
    return changed(world, phase=phase, pending_players=()), 0, 0


def require_host_agreement(cases: list[Case]) -> None:
    for case in cases:
        world = to_host(case.initial)
        for step in case.steps:
            world, status, resolved = host_step(world, step)
            assert (world, status, resolved) == (
                to_host(step.expected),
                step.status,
                step.resolved,
            ), case.name
