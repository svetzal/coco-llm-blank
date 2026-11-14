"""Deliberately wrong, original controls. Never use these as game rules."""

from game_state_model import Journey, Planet, World, active_players, changed, try_send


def truncated_arrivals(world: World) -> tuple[int, ...]:
    """Source-inspired 15-slot arrival scan against a 25-slot allocation."""
    return tuple(
        i
        for i, j in enumerate(world.journeys[:15])
        if j is not None and j.arrival <= world.turn + 1
    )


def truncated_survivors(world: World) -> tuple[int, ...]:
    return active_players(changed(world, journeys=world.journeys[:15]))


def deduct_before_validation(world: World, count: int) -> tuple[World, str]:
    """Invented partial-mutation defect, NOT a reproduction of the BASIC listing."""
    origin = world.planets[0]
    planets = (
        Planet(owner=origin.owner, ships=origin.ships - count, production=origin.production),
    ) + world.planets[1:]
    damaged = changed(world, planets=planets)
    return try_send(damaged, 1, 0, 1, count, 1)


def overwrite_full_queue(world: World, journey: Journey) -> World:
    """Source-inspired full-queue fallback to slot 1 (Python slot 0)."""
    return changed(world, journeys=(journey,) + world.journeys[1:])
