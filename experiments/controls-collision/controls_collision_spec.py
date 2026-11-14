"""Literal fixtures specify policies independently of drawing and collision code."""

from fractions import Fraction as F

import pytest
from controls_collision import (
    Buttons,
    actions,
    blocked,
    endpoint_only,
    move_horizontal,
    swept_interval_contact,
)

POINT = ((0, 0),)
WORLD = (12, 6)


class DescribeSampledControls:
    def should_hold_move_fire_once_release_and_press_again(self):
        previous = Buttons()
        samples = [
            Buttons(right=True, fire=True),
            Buttons(right=True, fire=True),
            Buttons(),
            Buttons(left=True, fire=True),
            Buttons(),
        ]
        observed = []
        x = 4
        for held in samples:
            dx, shot = actions(previous, held)
            x += dx
            observed.append((x, shot))
            previous = held

        assert observed == [(5, True), (6, False), (6, False), (5, True), (5, False)]
        # Naive held-fire control fires three times, violating two literal events.
        assert sum(sample.fire for sample in samples) == 3
        assert sum(shot for _, shot in observed) == 2

    def should_record_press_hold_release_while_blocked_then_move_away(self):
        samples = [
            Buttons(right=True, fire=True),
            Buttons(right=True, fire=True),
            Buttons(right=True),
            Buttons(right=True, fire=True),
            Buttons(left=True, fire=True),
            Buttons(left=True),
        ]
        solid = frozenset({(5, 2)})
        observed = []
        previous = Buttons()
        position = (4, 2)
        naive_previous = Buttons()
        naive_shots = []
        for held in samples:
            dx, shot = actions(previous, held)
            next_position = move_horizontal(position, dx, POINT, solid, WORLD)
            observed.append((next_position, shot))
            naive_shots.append(actions(naive_previous, held)[1])
            if next_position != position:
                naive_previous = held
            previous = held
            position = next_position

        assert observed == [
            ((4, 2), True),
            ((4, 2), False),
            ((4, 2), False),
            ((4, 2), True),
            ((3, 2), False),
            ((2, 2), False),
        ]
        assert naive_shots == [True, True, False, True, True, False]
        assert solid == frozenset({(5, 2)})

    @pytest.mark.parametrize(
        "previous,held,expected",
        [
            (Buttons(), Buttons(True, False, True), (-1, True)),
            (Buttons(), Buttons(False, True, True), (1, True)),
            (Buttons(), Buttons(True, True, True), (0, True)),
            (Buttons(fire=True), Buttons(True, True, True), (0, False)),
        ],
    )
    def should_resolve_simultaneous_inputs(self, previous, held, expected):
        assert actions(previous, held) == expected
        # Early return on direction loses fire and gives opposing keys priority.
        naive = (-1, False) if held.left else (1, False)
        assert naive != expected

    def should_suppress_startup_hold_until_release_and_new_press(self):
        previous = Buttons(right=True, fire=True)
        observed = []
        for held in [previous, Buttons(), Buttons(fire=True), Buttons(fire=True)]:
            observed.append(actions(previous, held))
            previous = held

        assert observed == [(1, False), (0, False), (0, True), (0, False)]
        assert actions(Buttons(), Buttons(fire=True)) == (0, True)  # Naive startup.

    def should_expose_between_sample_press_limit(self):
        # Physical press/release between two idle samples leaves identical data.
        assert actions(Buttons(), Buttons()) == (0, False)


class DescribeGridMovement:
    def should_approach_wall_reject_preserve_state_and_return(self):
        solid = frozenset({(5, 2)})
        state = {"position": (1, 2), "score": 7, "lives": 3}
        state["position"] = move_horizontal(state["position"], 7, POINT, solid, WORLD)
        assert state == {"position": (4, 2), "score": 7, "lives": 3}
        before = state.copy()

        state["position"] = move_horizontal(state["position"], 1, POINT, solid, WORLD)
        assert state == before
        assert solid == frozenset({(5, 2)})
        state["position"] = move_horizontal(state["position"], -3, POINT, solid, WORLD)
        assert state == {"position": (1, 2), "score": 7, "lives": 3}

    def should_catch_thin_wall_that_endpoint_control_skips_in_both_directions(self):
        solid = frozenset({(5, 2)})
        assert endpoint_only((1, 2), 7, POINT, solid, WORLD) == (8, 2)
        assert move_horizontal((1, 2), 7, POINT, solid, WORLD) == (4, 2)
        assert endpoint_only((8, 2), -7, POINT, solid, WORLD) == (1, 2)
        assert move_horizontal((8, 2), -7, POINT, solid, WORLD) == (6, 2)
        assert endpoint_only((4, 2), 1, POINT, solid, WORLD) == (4, 2)

    def should_retain_sparse_probe_blindspot_and_detect_with_full_shape(self):
        sparse = ((0, 0), (0, 2))
        full = ((0, 0), (0, 1), (0, 2))
        solid = frozenset({(4, 2)})

        assert move_horizontal((1, 1), 6, sparse, solid, WORLD) == (7, 1)
        assert move_horizontal((1, 1), 6, full, solid, WORLD) == (3, 1)

    def should_ignore_decoration_but_observe_scenery_edit_and_return(self):
        solid = frozenset({(5, 2)})
        art = {(5, 2): "wall", (3, 2): "flower"}
        before = move_horizontal((1, 2), 7, POINT, solid, WORLD)
        art[(5, 2)] = "background"
        art[(3, 2)] = "wall"

        assert move_horizontal((1, 2), 7, POINT, solid, WORLD) == before == (4, 2)
        art_based = frozenset(p for p, colour in art.items() if colour == "wall")
        assert move_horizontal((1, 2), 7, POINT, art_based, WORLD) == (2, 2)
        # Explicit world edit updates both representations; decoration stays.
        solid = frozenset()
        art[(5, 2)] = "background"
        assert (5, 2) not in solid and art[(5, 2)] == "background"
        assert move_horizontal((4, 2), 4, POINT, solid, WORLD) == (8, 2)
        assert move_horizontal((8, 2), -7, POINT, solid, WORLD) == (1, 2)

    @pytest.mark.parametrize(
        "position,dx,expected",
        [
            ((1, 2), -5, (0, 2)),
            ((10, 2), 5, (11, 2)),
            ((1, 2), 0, (1, 2)),
            ((1, 2), 3, (4, 2)),
        ],
    )
    def should_enforce_world_edges_and_accept_clear_or_zero_motion(self, position, dx, expected):
        assert move_horizontal(position, dx, POINT, frozenset(), WORLD) == expected

    def should_bound_work_without_jumping_then_allow_later_request(self):
        solid = frozenset({(5, 2)})
        first = move_horizontal((1, 2), 7, POINT, solid, WORLD, budget=2)
        assert first == (3, 2)
        assert move_horizontal(first, 5, POINT, solid, WORLD, budget=2) == (4, 2)
        assert move_horizontal(first, 5, POINT, solid, WORLD, budget=0) == (3, 2)
        with pytest.raises(ValueError, match="budget"):
            move_horizontal(first, 1, POINT, solid, WORLD, budget=-1)

    def should_expose_diagonal_endpoint_corner_failure_without_claiming_a_diagonal_solver(self):
        solid = frozenset({(2, 1), (1, 2)})
        assert not blocked((2, 2), POINT, solid, WORLD)
        # A policy requiring both orthogonal neighbours clear rejects this corner.
        assert blocked((2, 1), POINT, solid, WORLD)
        assert blocked((1, 2), POINT, solid, WORLD)
        assert blocked((1, -1), POINT, solid, WORLD)
        assert blocked((1, 6), POINT, solid, WORLD)


class DescribeRestrictedSweptContact:
    @pytest.mark.parametrize(
        "a,da,aw,b,db,bw,expected",
        [
            (0, 4, 1, 4, -4, 1, True),  # Objects swap sides; endpoints miss.
            (0, 2, 1, 4, 0, 1, False),  # Separated through entire update.
            (0, 3, 1, 4, 0, 1, True),  # Touch exactly at end.
            (0, -1, 1, 1, 1, 1, True),  # Touch at start, then separate.
            (0, 4, 1, 2, 4, 1, False),  # Equal velocities, disjoint.
            (0, 0, 2, 1, 0, 1, True),  # Initial overlap, stationary.
        ],
    )
    def should_use_relative_linear_motion_and_closed_contact(self, a, da, aw, b, db, bw, expected):
        assert swept_interval_contact(F(a), F(da), F(aw), F(b), F(db), F(bw)) is expected

    def should_expose_finite_samples_missing_fractional_obstacle(self):
        # Point passes a thin interval [2/5, 3/5]; samples only at x=0 and x=1.
        assert not any(F(2, 5) <= sample <= F(3, 5) for sample in (F(0), F(1)))
        assert swept_interval_contact(F(0), F(1), F(0), F(2, 5), F(0), F(1, 5))

    def should_expose_endpoint_only_and_old_position_object_controls(self):
        # Unit-width A travels 0->4; B travels 4->0. Both endpoint pairs disjoint.
        def overlap(a, b):
            return a <= b + 1 and b <= a + 1

        assert not overlap(0, 4)
        assert not overlap(4, 0)
        assert swept_interval_contact(F(0), F(4), F(1), F(4), F(-4), F(1))
        # Same velocity: A's new interval [4,5] overlaps B's OLD [4,5],
        # but actual intervals stay separated while B moves to [8,9].
        assert overlap(4, 4)
        assert not swept_interval_contact(F(0), F(4), F(1), F(4), F(4), F(1))
