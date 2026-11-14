"""Hand-calculated outcomes for the original bounded rules in README.md."""

import pytest
from game_state_controls import (
    deduct_before_validation,
    overwrite_full_queue,
    truncated_arrivals,
    truncated_survivors,
)
from game_state_model import (
    Journey,
    Menu,
    Phase,
    Planet,
    World,
    active_players,
    begin_turn,
    changed,
    finish_commands,
    land,
    menu_step,
    present,
    set_dwell,
    try_send,
)
from pydantic import ValidationError


def command_world(**fields: object) -> World:
    defaults = {
        "planets": (Planet(owner=1, ships=20), Planet(owner=2, ships=10)),
        "journeys": (None, None),
        "turn": 1,
        "phase": Phase.COMMANDS,
        "pending_players": (1, 2),
    }
    return World.model_validate(defaults | fields)


def end_turn(world: World) -> World:
    for player in world.pending_players:
        world = finish_commands(world, player)
    return world


class DescribeAtomicCommands:
    @pytest.mark.parametrize(
        "args,error",
        [
            ((2, 0, 1, 2, 1), "wrong_phase"),
            ((1, 0, 0, 2, 1), "invalid_planets"),
            ((1, -1, 1, 2, 1), "invalid_planets"),
            ((1, 0, 2, 2, 1), "invalid_planets"),
            ((1, 2, 0, 2, 1), "invalid_planets"),
            ((1, 0, -1, 2, 1), "invalid_planets"),
            ((1, 1, 0, 2, 1), "not_owner"),
            ((1, 0, 1, 0, 1), "invalid_count"),
            ((1, 0, 1, -1, 1), "invalid_count"),
            ((1, 0, 1, 21, 1), "invalid_count"),
            ((1, 0, 1, 256, 1), "invalid_count"),
            ((1, 0, 1, 2, 0), "invalid_time"),
            ((1, 0, 1, 2, -1), "invalid_time"),
            ((1, 0, 1, 2, 100), "invalid_time"),
        ],
    )
    def should_reject_without_any_world_change(self, args, error):
        world = command_world()
        before = world.model_dump_json()

        after, result = try_send(world, *args)

        assert result == error
        assert after.model_dump_json() == before
        assert world.model_dump_json() == before

    def should_publish_the_complete_command_and_leave_old_snapshot_unchanged(self):
        world = command_world()

        after, result = try_send(world, 1, 0, 1, 7, 3)

        assert result == "accepted"
        assert world.planets[0].ships == 20
        assert world.journeys == (None, None)
        assert after.planets[0].ships == 13
        assert after.journeys == (Journey(owner=1, destination=1, ships=7, arrival=4), None)

    def should_reject_full_queue_then_resolve_and_reuse_last_slot(self):
        future = Journey(owner=1, destination=0, ships=1, arrival=9)
        last = Journey(owner=2, destination=1, ships=3, arrival=2)
        world = command_world(journeys=(future,) * 24 + (last,))
        before = world.model_dump_json()

        rejected, result = try_send(world, 1, 0, 1, 2, 1)
        next_world, resolved = begin_turn(end_turn(rejected))
        reused, accepted = try_send(next_world, 1, 0, 1, 2, 1)

        assert result == "queue_full"
        assert rejected.model_dump_json() == before
        assert resolved == (24,)
        assert next_world.planets[1].ships == 13
        assert reused.journeys[:24] == (future,) * 24
        assert reused.journeys[24] == Journey(owner=1, destination=1, ships=2, arrival=3)
        assert reused.planets[0].ships == 18
        assert accepted == "accepted"

    def should_keep_draft_cancellation_outside_world_state(self):
        world = command_world()
        before = world.model_dump_json()
        # A draft is caller-owned; neither editing nor cancelling dispatches a send.
        draft = {"source": 0, "count": 7}
        draft.clear()

        assert world.model_dump_json() == before
        assert draft == {}


class DescribeTurnRules:
    def should_resolve_in_slot_order_and_apply_capture_production_once(self):
        # Neutral defence 5; player 1 sends 8 -> 3; player 2 sends 4 -> 1.
        # Reversing these events would leave player 1 with 7, so order matters.
        planets = (
            Planet(owner=1, ships=20),
            Planet(owner=2, ships=20),
            Planet(owner=0, ships=5, production=2),
        )
        world = World(
            planets=planets,
            journeys=(
                Journey(owner=1, destination=2, ships=8, arrival=1),
                Journey(owner=2, destination=2, ships=4, arrival=1),
            ),
        )

        arrived, resolved = begin_turn(world)
        produced = end_turn(arrived)
        next_world, repeated = begin_turn(produced)

        assert resolved == (0, 1)
        assert arrived.planets[2] == Planet(owner=2, ships=1, production=2)
        assert arrived.pending_players == (1, 2)
        assert produced.planets[2] == Planet(owner=2, ships=3, production=2)
        assert produced.phase == Phase.COMPLETE
        assert repeated == ()
        assert next_world.journeys == (None, None)
        assert next_world.planets[2].ships == 3

    def should_resolve_overdue_events_once_and_leave_future_events(self):
        world = World(
            planets=(Planet(owner=1, ships=10), Planet(owner=2, ships=10)),
            journeys=(
                Journey(owner=1, destination=0, ships=3, arrival=1),
                Journey(owner=2, destination=1, ships=4, arrival=4),
            ),
            turn=2,
        )

        arrived, resolved = begin_turn(world)
        later, later_slots = begin_turn(end_turn(arrived))
        again, again_slots = begin_turn(end_turn(later))

        assert resolved == (0,)
        assert arrived.planets[0].ships == 13
        assert later_slots == (1,)
        assert later.planets[1].ships == 14
        assert again_slots == ()
        assert tuple(p.ships for p in again.planets) == (13, 14)

    def should_keep_last_slot_fleet_only_player_alive_until_arrival(self):
        world = World(
            planets=(Planet(owner=1, ships=10), Planet(owner=0, ships=1)),
            journeys=(None,) * 24 + (Journey(owner=2, destination=1, ships=4, arrival=2),),
        )

        first, _ = begin_turn(world)
        complete = end_turn(first)
        second, resolved = begin_turn(complete)

        assert active_players(first) == (1, 2)
        assert first.pending_players == (1, 2)
        assert complete.phase == Phase.COMPLETE
        assert resolved == (24,)
        assert second.planets[1] == Planet(owner=2, ships=3)
        assert active_players(second) == (1, 2)

    def should_finish_after_last_fleet_is_lost_and_production_has_run(self):
        world = World(
            planets=(Planet(owner=1, ships=10, production=2), Planet(owner=0, ships=5)),
            journeys=(Journey(owner=2, destination=0, ships=3, arrival=1),),
        )

        arrived, _ = begin_turn(world)
        final = end_turn(arrived)

        assert arrived.pending_players == (1,)
        assert arrived.planets[0].ships == 7
        assert final.planets[0].ships == 9
        assert final.phase == Phase.FINISHED
        with pytest.raises(ValueError, match="turn cannot start"):
            begin_turn(final)

    def should_enforce_declared_player_order_and_pending_phase(self):
        world = command_world(players=(2, 1), pending_players=(2, 1))

        with pytest.raises(ValueError, match="not this player's"):
            finish_commands(world, 1)
        with pytest.raises(ValueError, match="turn cannot start"):
            begin_turn(world)
        next_player = finish_commands(world, 2)

        assert next_player.pending_players == (1,)
        assert next_player.planets == world.planets
        complete = finish_commands(next_player, 1)
        with pytest.raises(ValueError, match="not this player's"):
            finish_commands(complete, 1)
        assert try_send(complete, 1, 0, 1, 1, 1) == (complete, "wrong_phase")

    def should_bound_turn_arithmetic_and_finish_after_final_production(self):
        world = command_world(
            turn=65534,
            turn_limit=65535,
            planets=(Planet(owner=1, ships=20, production=1), Planet(owner=2, ships=10)),
        )

        sent, result = try_send(world, 1, 0, 1, 2, 1)
        rejected, error = try_send(world, 1, 0, 1, 2, 2)
        final_turn, resolved = begin_turn(end_turn(sent))
        final = end_turn(final_turn)

        assert result == "accepted"
        assert rejected == world and error == "invalid_time"
        assert resolved == (0,)
        assert final.turn == 65535 and final.phase == Phase.FINISHED
        assert final.planets[0].ships == 20  # 20 - 2 + 1 + 1
        assert try_send(final_turn, 1, 0, 1, 1, 1) == (final_turn, "invalid_time")
        with pytest.raises(ValueError):
            begin_turn(final)
        with pytest.raises(ValueError):
            begin_turn(changed(final, phase=Phase.COMPLETE))

    def should_cap_production_and_leave_neutral_planets_unchanged(self):
        world = command_world(
            planets=(
                Planet(owner=1, ships=254, production=3),
                Planet(owner=0, ships=10, production=4),
            )
        )
        assert tuple(p.ships for p in end_turn(world).planets) == (255, 10)

    @pytest.mark.parametrize(
        "owner,ships,expected",
        [
            (1, 254, Planet(owner=1, ships=255)),
            (2, 4, Planet(owner=2, ships=0)),
            (2, 7, Planet(owner=2, ships=3)),
            (0, 2, Planet(owner=1, ships=2)),
        ],
    )
    def should_apply_explicit_battle_and_reinforcement_rules(self, owner, ships, expected):
        assert (
            land(
                Planet(owner=owner, ships=ships),
                Journey(owner=1, destination=0, ships=4, arrival=1),
            )
            == expected
        )

    def should_finish_an_empty_world_without_a_command_phase(self):
        world = World(planets=(Planet(owner=0, ships=0),) * 2, journeys=(None,))
        after, resolved = begin_turn(world)
        assert after.phase == Phase.FINISHED and after.pending_players == ()
        assert resolved == ()


class DescribeMenuBoundary:
    def should_consume_one_select_and_prioritize_it_over_expiry(self):
        menu = Menu(remaining=1)

        items, command = menu_step(menu, select=True, tick=True)
        held, held_command = menu_step(items, tick=True)  # Adapter emits no new SELECT.
        selected, accepted = menu_step(held, select=True)

        assert (items.column, items.item, items.remaining, command) == (0, 0, 3, None)
        assert (held.item, held.remaining, held_command) == (0, 2, None)
        assert accepted == "send"
        assert (selected.column, selected.item, selected.remaining) == (0, None, 3)

    def should_scan_columns_wrap_and_return_after_last_item_timeout(self):
        menu = Menu(dwell=1, remaining=1)
        menu, _ = menu_step(menu, tick=True)
        assert menu.column == 1
        menu, _ = menu_step(menu, tick=True)
        assert menu.column == 0
        menu, _ = menu_step(menu, select=True)
        menu, _ = menu_step(menu, tick=True)
        assert menu.item == 1
        menu, command = menu_step(menu, tick=True)
        assert (menu.column, menu.item, command) == (0, None, None)

    def should_select_last_item_once_and_return_to_first_column(self):
        menu = Menu(column=1, item=0)
        menu, command = menu_step(menu, select=True)
        assert command == "end"
        assert (menu.column, menu.item) == (0, None)
        assert menu_step(menu) == (menu, None)

    def should_preserve_world_and_draft_during_redraw_ticks_speed_change_and_cancel(self):
        world = command_world()
        before = world.model_dump_json()
        draft = {"source": 0, "count": 3}
        menu = Menu(item=0)

        faster = set_dwell(menu, 1)
        assert faster.item == 0 and faster.remaining == 1
        assert draft == {"source": 0, "count": 3}
        for _ in range(100):
            text = present(world, faster)
            faster, command = menu_step(faster, tick=True)
            assert command is None
        draft.clear()

        assert text.startswith("turn=1 phase=commands")
        assert world.model_dump_json() == before


class DescribeValidation:
    @pytest.mark.parametrize(
        "fields",
        [
            {"players": ()},
            {"players": (1, 1)},
            {"players": (0, 1)},
            {"turn": 101},
            {"players": (1,)},
            {"pending_players": (2, 1)},
            {"phase": Phase.COMPLETE},
            {"journeys": ()},
            {"journeys": (None,) * 26},
            {"journeys": (Journey(owner=3, destination=0, ships=1, arrival=1),)},
            {"journeys": (Journey(owner=1, destination=25, ships=1, arrival=1),)},
        ],
    )
    def should_reject_incoherent_worlds(self, fields):
        with pytest.raises(ValidationError):
            command_world(**fields)

    @pytest.mark.parametrize(
        "fields",
        [
            {"columns": ()},
            {"columns": ((),)},
            {"column": 2},
            {"remaining": 4},
            {"item": -1},
            {"item": 2},
            {"dwell": 0},
        ],
    )
    def should_reject_invalid_menu_states(self, fields):
        with pytest.raises(ValidationError):
            Menu(**fields)

    def should_reject_invalid_dwell_without_changing_menu(self):
        menu = Menu()
        with pytest.raises(ValidationError):
            set_dwell(menu, 0)
        assert menu.remaining == 3


class DescribeNegativeControls:
    def should_detect_source_inspired_capacity_mismatch_for_arrival_and_survival(self):
        world = World(
            planets=(Planet(owner=1, ships=10), Planet(owner=0, ships=0)),
            journeys=(None,) * 24 + (Journey(owner=2, destination=1, ships=3, arrival=1),),
        )

        _, actual_slots = begin_turn(world)

        assert actual_slots == (24,)
        assert active_players(world) == (1, 2)
        assert truncated_arrivals(world) == ()  # Fails the literal (24,) oracle.
        assert truncated_survivors(world) == (1,)  # Fails the literal (1, 2) oracle.

    def should_detect_partial_mutation_on_rejected_full_queue(self):
        event = Journey(owner=2, destination=0, ships=1, arrival=3)
        world = command_world(journeys=(event,) * 25)
        before = world.model_dump_json()

        correct, correct_status = try_send(world, 1, 0, 1, 2, 1)
        broken, broken_status = deduct_before_validation(world, 2)

        assert correct_status == broken_status == "queue_full"
        assert correct.model_dump_json() == before
        assert broken.model_dump_json() != before
        assert correct.planets[0].ships == 20
        assert broken.planets[0].ships == 18
        assert broken.journeys == world.journeys

    def should_detect_full_queue_overwrite_without_losing_the_failed_control(self):
        original = Journey(owner=2, destination=0, ships=1, arrival=3)
        replacement = Journey(owner=1, destination=1, ships=2, arrival=2)
        world = command_world(journeys=(original,) * 25)

        broken = overwrite_full_queue(world, replacement)

        assert broken.journeys != world.journeys
        assert broken.journeys[0] == replacement
        assert world.journeys[0] == original


class DescribeCapacitySweep:
    @pytest.mark.parametrize("capacity", [1, 15, 16, 25])
    def should_deliver_every_accepted_event_once_at_each_boundary(self, capacity):
        world = command_world(
            journeys=(None,) * capacity,
            planets=(
                Planet(owner=1, ships=100),
                Planet(owner=1, ships=0),
                Planet(owner=2, ships=10),
            ),
        )
        for _ in range(capacity):
            world, status = try_send(world, 1, 0, 1, 1, 1)
            assert status == "accepted"
        rejected, status = try_send(world, 1, 0, 1, 1, 1)
        assert rejected == world and status == "queue_full"

        arrived, slots = begin_turn(end_turn(world))
        again, second_slots = begin_turn(end_turn(arrived))

        assert slots == tuple(range(capacity))
        assert arrived.planets[0].ships == 100 - capacity
        assert arrived.planets[1].ships == capacity
        assert arrived.journeys == (None,) * capacity
        assert second_slots == ()
        assert again.planets == arrived.planets


class DescribeWorldJourneyBounds:
    def should_reject_unreachable_arrival_but_resolve_arrival_at_limit(self):
        fields = {
            "planets": (Planet(owner=1, ships=5), Planet(owner=0, ships=0)),
            "turn": 1,
            "turn_limit": 2,
        }
        with pytest.raises(ValidationError, match="journey arrives after turn limit"):
            World(**fields, journeys=(Journey(owner=2, destination=1, ships=3, arrival=3),))
        world = World(**fields, journeys=(Journey(owner=2, destination=1, ships=3, arrival=2),))
        advanced, resolved = begin_turn(world)
        assert resolved == (0,)
        assert advanced.journeys == (None,)
        assert advanced.planets[1] == Planet(owner=2, ships=3)
