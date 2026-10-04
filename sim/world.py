from __future__ import annotations

from dataclasses import dataclass, field

from sim.clock import Clock
from sim.generate.city import CityLayout, generate_city
from sim.generate.population import populate_city
from sim.rng import make_rng
from sim.systems.movement import advance_movement, begin_travel
from sim.systems.schedule import active_goal, assign_schedules
from sim.systems.social import process_colocations, record_arrival
from sim.types import (
    MINUTES_PER_DAY,
    Activity,
    Building,
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
            assign_schedules(self)
            self._travel_targets.clear()
        for person_id in sorted(self.people):
            self._step_person(self.people[person_id])
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


def create_world(seed: int = 42, citizen_count: int = 50) -> World:
    city_rng = make_rng(seed, "city")
    people_rng = make_rng(seed, "people")
    layout: CityLayout = generate_city(city_rng)
    people = populate_city(people_rng, layout, citizen_count=citizen_count)
    world = World(
        seed=seed,
        width=layout.width,
        height=layout.height,
        tiles=layout.tiles,
        buildings=layout.buildings,
        people=people,
    )
    for person in world.people.values():
        home = world.buildings[person.home_id]
        person.x = float(home.x)
        person.y = float(home.y)
        person.activity = Activity.SLEEP
    assign_schedules(world)
    return world
