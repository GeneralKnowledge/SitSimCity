from __future__ import annotations

from dataclasses import dataclass, field

from sim.clock import Clock
from sim.generate.city import CityLayout, generate_city
from sim.generate.population import populate_city
from sim.rng import make_rng
from sim.systems.circumstances import tick_circumstances
from sim.systems.lifecycle import tick_lifecycle
from sim.systems.movement import advance_movement, begin_travel
from sim.systems.schedule import active_goal, assign_schedules
from sim.systems.social import (
    apply_relationship_staleness,
    process_colocations,
    record_arrival,
)
from sim.systems.circumstances import record_life_event
from sim.types import (
    MINUTES_PER_DAY,
    Activity,
    Building,
    LifeEvent,
    LifeEventKind,
    Person,
    Relationship,
    TileKind,
)


@dataclass
class World:
    seed: int
    width: int
    height: int
    tiles: list[list[TileKind]]
    buildings: dict[int, Building]
    people: dict[int, Person]
    clock: Clock = field(default_factory=Clock)
    relationships: dict[tuple[int, int], Relationship] = field(default_factory=dict)
    # M10: town-level chronicle (deaths / arrivals) + stable id allocator.
    town_chronicle: list[LifeEvent] = field(default_factory=list)
    next_person_id: int = 1
    # Remember last pursued building so we do not repath every minute.
    _travel_targets: dict[int, int] = field(default_factory=dict)

    def total_minutes(self) -> int:
        return (self.clock.day - 1) * MINUTES_PER_DAY + self.clock.minute_of_day

    def is_walkable(self, x: int, y: int) -> bool:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return False
        return self.tiles[y][x] in (TileKind.ROAD, TileKind.BUILDING)

    def building_at(self, x: int, y: int) -> Building | None:
        for building in self.buildings.values():
            if building.x == x and building.y == y:
                return building
        return None

    def people_at_building(self, building_id: int) -> list[Person]:
        building = self.buildings[building_id]
        found: list[Person] = []
        for person in self.people.values():
            if person.activity == Activity.TRAVEL:
                continue
            if int(round(person.x)) == building.x and int(round(person.y)) == building.y:
                found.append(person)
        return found

    def step_minutes(self, minutes: int) -> None:
        for _ in range(minutes):
            self.step_once()

    def step_once(self) -> None:
        rolled = self.clock.advance_one_minute()
        if rolled:
            apply_relationship_staleness(self)
            tick_circumstances(self)
            tick_lifecycle(self)
            assign_schedules(self)
            self._travel_targets.clear()
        for person_id in sorted(self.people):
            person = self.people.get(person_id)
            if person is None:
                continue
            self._step_person(person)
        process_colocations(self)

    def _step_person(self, person: Person) -> None:
        goal = active_goal(person, self.clock.minute_of_day)
        if goal is None or goal.target_building_id is None:
            return

        target = self.buildings[goal.target_building_id]
        at_target = (
            int(round(person.x)) == target.x
            and int(round(person.y)) == target.y
            and not person.path
        )

        if at_target:
            previous = person.activity
            person.activity = goal.activity
            self._travel_targets.pop(person.id, None)
            if previous != goal.activity:
                record_arrival(person, goal.activity, target.name)
            return

        if self._travel_targets.get(person.id) != goal.target_building_id:
            begin_travel(person, (target.x, target.y), self.is_walkable)
            self._travel_targets[person.id] = goal.target_building_id

        arrived = advance_movement(person)
        if arrived:
            previous = person.activity
            person.activity = goal.activity
            self._travel_targets.pop(person.id, None)
            if previous != goal.activity:
                record_arrival(person, goal.activity, target.name)


def create_world(seed: int = 42, citizen_count: int = 80) -> World:
    city_rng = make_rng(seed, "city")
    people_rng = make_rng(seed, "people")
    layout: CityLayout = generate_city(city_rng)
    people = populate_city(people_rng, layout, citizen_count=citizen_count)
    next_id = max(people) + 1 if people else 1
    world = World(
        seed=seed,
        width=layout.width,
        height=layout.height,
        tiles=layout.tiles,
        buildings=layout.buildings,
        people=people,
        next_person_id=next_id,
    )
    for person in world.people.values():
        home = world.buildings[person.home_id]
        work = world.buildings[person.work_id]
        person.x = float(home.x)
        person.y = float(home.y)
        person.activity = Activity.SLEEP
        from sim.systems.chronicle import pick_phrase

        place_rng = make_rng(seed, f"chronicle-place-p{person.id}")
        record_life_event(
            person,
            LifeEvent(
                LifeEventKind.SETTLED_HOME,
                1,
                pick_phrase(place_rng, "settled_home", place=home.name),
            ),
        )
        record_life_event(
            person,
            LifeEvent(
                LifeEventKind.STARTED_JOB,
                1,
                pick_phrase(place_rng, "started_job", place=work.name),
            ),
        )
    assign_schedules(world)
    return world
