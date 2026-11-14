"""Original host-side policies; no keyboard adapter or hardware timing model."""

from fractions import Fraction
from typing import NamedTuple


class Buttons(NamedTuple):
    left: bool = False
    right: bool = False
    fire: bool = False


def actions(previous: Buttons, held: Buttons) -> tuple[int, bool]:
    """Caller seeds previous with startup sample, then saves held every update."""
    return int(held.right) - int(held.left), held.fire and not previous.fire


Point = tuple[int, int]


def blocked(
    position: Point, probes: tuple[Point, ...], solid: frozenset[Point], size: Point
) -> bool:
    """Outside the half-open world is solid; artwork is deliberately absent."""
    x, y = position
    width, height = size
    return any(
        not (0 <= x + px < width and 0 <= y + py < height) or (x + px, y + py) in solid
        for px, py in probes
    )


def move_horizontal(
    position: Point,
    dx: int,
    probes: tuple[Point, ...],
    solid: frozenset[Point],
    size: Point,
    budget: int = 32,
) -> Point:
    """Stop at first rejection. Discard excess displacement, never teleport.

    Preconditions: valid starting placement, nonempty probes, integer grid.
    The finite budget bounds work; callers must request any later motion anew.
    """
    if budget < 0:
        raise ValueError("budget must be nonnegative")
    direction = 1 if dx > 0 else -1
    for _ in range(min(abs(dx), budget)):
        candidate = position[0] + direction, position[1]
        if blocked(candidate, probes, solid, size):
            break
        position = candidate
    return position


def endpoint_only(
    position: Point, dx: int, probes: tuple[Point, ...], solid: frozenset[Point], size: Point
) -> Point:
    """Deliberately naive failure control: no intermediate checks."""
    candidate = position[0] + dx, position[1]
    return position if blocked(candidate, probes, solid, size) else candidate


def swept_interval_contact(
    a: Fraction, da: Fraction, a_width: Fraction, b: Fraction, db: Fraction, b_width: Fraction
) -> bool:
    """Closed intervals, linear motion over one update, touching counts.

    Original restricted relative-motion example, not a 2-D collision engine.
    Widths are nonnegative. Exact rational arithmetic avoids rounding policy.
    """
    relative_start = a - b
    relative_end = relative_start + da - db
    return (
        min(relative_start, relative_end) <= b_width
        and max(relative_start, relative_end) >= -a_width
    )
