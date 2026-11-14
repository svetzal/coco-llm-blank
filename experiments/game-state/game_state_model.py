"""Original host-only rules, not a port of either Undercolor listing."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)


class Planet(Record):
    owner: int = Field(ge=0, le=6)
    ships: int = Field(ge=0, le=255)
    production: int = Field(default=0, ge=0, le=255)


class Journey(Record):
    owner: int = Field(ge=1, le=6)
    destination: int = Field(ge=0, le=25)
    ships: int = Field(ge=1, le=255)
    arrival: int = Field(ge=1, le=65535)


class Phase(StrEnum):
    COMPLETE = "turn_complete"
    COMMANDS = "commands"
    FINISHED = "finished"


class World(Record):
    planets: tuple[Planet, ...] = Field(min_length=2, max_length=26)
    journeys: tuple[Journey | None, ...] = Field(min_length=1, max_length=25)
    players: tuple[int, ...] = (1, 2)
    turn: int = Field(default=0, ge=0, le=65535)
    turn_limit: int = Field(default=100, ge=1, le=65535)
    phase: Phase = Phase.COMPLETE
    pending_players: tuple[int, ...] = ()

    @model_validator(mode="after")
    def coherent(self) -> "World":
        if not self.players or len(set(self.players)) != len(self.players):
            raise ValueError("players must be nonempty and unique")
        if any(p < 1 or p > 6 for p in self.players) or self.turn > self.turn_limit:
            raise ValueError("invalid players or turn")
        if any(p.owner and p.owner not in self.players for p in self.planets):
            raise ValueError("unknown planet owner")
        if any(
            j and (j.owner not in self.players or j.destination >= len(self.planets))
            for j in self.journeys
        ):
            raise ValueError("invalid journey reference")
        if any(j and j.arrival > self.turn_limit for j in self.journeys):
            raise ValueError("journey arrives after turn limit")
        if bool(self.pending_players) != (self.phase == Phase.COMMANDS):
            raise ValueError("commands need pending players")
        expected = tuple(p for p in self.players if p in self.pending_players)
        if self.pending_players != expected:
            raise ValueError("pending players must follow declared order")
        return self


def changed(world: World, **fields: object) -> World:
    """Build and validate a whole replacement before exposing it to a caller."""
    return World.model_validate(world.model_dump() | fields)


def active_players(world: World) -> tuple[int, ...]:
    owners = {p.owner for p in world.planets}
    owners.update(j.owner for j in world.journeys if j is not None)
    return tuple(p for p in world.players if p in owners)


def send_error(
    world: World, player: int, source: int, destination: int, count: int, delay: int
) -> str | None:
    if world.phase != Phase.COMMANDS or world.pending_players[0] != player:
        return "wrong_phase"
    if source == destination or not (
        0 <= source < len(world.planets) and 0 <= destination < len(world.planets)
    ):
        return "invalid_planets"
    planet = world.planets[source]
    if planet.owner != player:
        return "not_owner"
    if count <= 0 or count > planet.ships:
        return "invalid_count"
    if delay < 1 or world.turn + delay > world.turn_limit:
        return "invalid_time"
    if None not in world.journeys:
        return "queue_full"
    return None


def try_send(
    world: World, player: int, source: int, destination: int, count: int, delay: int
) -> tuple[World, str]:
    error = send_error(world, player, source, destination, count, delay)
    if error:
        return world, error
    planets = list(world.planets)
    origin = planets[source]
    planets[source] = Planet(
        owner=origin.owner, ships=origin.ships - count, production=origin.production
    )
    journeys = list(world.journeys)
    journeys[journeys.index(None)] = Journey(
        owner=player, destination=destination, ships=count, arrival=world.turn + delay
    )
    return changed(world, planets=tuple(planets), journeys=tuple(journeys)), "accepted"


def land(planet: Planet, journey: Journey) -> Planet:
    """Friendly addition; enemies subtract; defender retains ownership on ties."""
    if planet.owner == journey.owner:
        owner, ships = planet.owner, planet.ships + journey.ships
    elif journey.ships > planet.ships:
        owner, ships = journey.owner, journey.ships - planet.ships
    else:
        owner, ships = planet.owner, planet.ships - journey.ships
    return Planet(owner=owner, ships=min(255, ships), production=planet.production)


def begin_turn(world: World) -> tuple[World, tuple[int, ...]]:
    if world.phase != Phase.COMPLETE or world.turn >= world.turn_limit:
        raise ValueError("turn cannot start")
    turn = world.turn + 1
    planets, journeys = list(world.planets), list(world.journeys)
    resolved = []
    for slot, journey in enumerate(journeys):
        if journey is not None and journey.arrival <= turn:
            planets[journey.destination] = land(planets[journey.destination], journey)
            journeys[slot] = None
            resolved.append(slot)
    arrivals_done = changed(world, turn=turn, planets=tuple(planets), journeys=tuple(journeys))
    players = active_players(arrivals_done)
    # With no surviving player there is nobody to collect commands from.
    if not players:
        return changed(arrivals_done, phase=Phase.FINISHED), tuple(resolved)
    return changed(arrivals_done, phase=Phase.COMMANDS, pending_players=players), tuple(resolved)


def finish_commands(world: World, player: int) -> World:
    if world.phase != Phase.COMMANDS or world.pending_players[0] != player:
        raise ValueError("not this player's command phase")
    pending = world.pending_players[1:]
    if pending:
        return changed(world, pending_players=pending)
    planets = tuple(
        Planet(
            owner=p.owner,
            ships=min(255, p.ships + p.production) if p.owner else p.ships,
            production=p.production,
        )
        for p in world.planets
    )
    phase = (
        Phase.FINISHED
        if world.turn == world.turn_limit or len(active_players(world)) <= 1
        else Phase.COMPLETE
    )
    return changed(world, planets=planets, pending_players=(), phase=phase)


class Menu(Record):
    columns: tuple[tuple[str, ...], ...] = (("send", "cancel"), ("end",))
    column: int = Field(default=0, ge=0)
    item: int | None = None
    dwell: int = Field(default=3, ge=1, le=255)
    remaining: int = Field(default=3, ge=1, le=255)

    @model_validator(mode="after")
    def coherent(self) -> "Menu":
        if not self.columns or any(not c for c in self.columns):
            raise ValueError("menu must contain nonempty columns")
        if self.column >= len(self.columns) or self.remaining > self.dwell:
            raise ValueError("invalid column or dwell")
        if self.item is not None and not 0 <= self.item < len(self.columns[self.column]):
            raise ValueError("invalid item")
        return self


def menu_step(menu: Menu, *, select: bool = False, tick: bool = False) -> tuple[Menu, str | None]:
    """One accepted SELECT or one logical tick. SELECT wins a coincident expiry."""
    fields = menu.model_dump()
    command = None
    if select:
        if menu.item is None:
            fields["item"] = 0
        else:
            command = menu.columns[menu.column][menu.item]
            fields.update(column=0, item=None)
        fields["remaining"] = menu.dwell
    elif tick and menu.remaining > 1:
        fields["remaining"] -= 1
    elif tick:
        fields["remaining"] = menu.dwell
        if menu.item is None:
            fields["column"] = (menu.column + 1) % len(menu.columns)
        elif menu.item + 1 < len(menu.columns[menu.column]):
            fields["item"] += 1
        else:
            fields.update(column=0, item=None)
    return Menu.model_validate(fields), command


def set_dwell(menu: Menu, ticks: int) -> Menu:
    return Menu.model_validate(menu.model_dump() | {"dwell": ticks, "remaining": ticks})


def present(world: World, menu: Menu) -> str:
    """Read-only text projection. No clock, command dispatch or hardware I/O."""
    return f"turn={world.turn} phase={world.phase} column={menu.column} item={menu.item}"
