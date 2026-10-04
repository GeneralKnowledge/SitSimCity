from __future__ import annotations

from collections import Counter

from sim.types import Activity, BuildingKind
from sim.world import create_world


def test_world_has_expected_town_shape() -> None:
    world = create_world(seed=42, citizen_count=80)
    kinds = Counter(b.kind for b in world.buildings.values())
    assert kinds[BuildingKind.HOME] == 32
    assert kinds[BuildingKind.WORKPLACE] == 10
    assert kinds[BuildingKind.PUB] == 2
    assert kinds[BuildingKind.SHOP] == 2
    assert kinds[BuildingKind.CAFE] == 2
    assert kinds[BuildingKind.POLICE] == 1
    assert kinds[BuildingKind.HOSPITAL] == 1
    assert len(world.people) == 80


def test_morning_commute_moves_day_shift_to_work() -> None:
    world = create_world(seed=7, citizen_count=80)
    assert world.clock.minute_of_day == 6 * 60
    asleep = sum(1 for p in world.people.values() if p.activity == Activity.SLEEP)
    assert asleep == 80

    day_ids = {p.id for p in world.people.values() if p.shift == "day"}
    assert len(day_ids) >= 50

    # Through morning rush into mid-morning (day shift should be at work).
    world.step_minutes(3 * 60 + 30)  # 06:00 -> 09:30
    assert world.clock.hour == 9

    at_work = 0
    traveling = 0
    day_at_work_or_travel = 0
    for person in world.people.values():
        work = world.buildings[person.work_id]
        if person.activity == Activity.WORK:
            assert int(round(person.x)) == work.x
            assert int(round(person.y)) == work.y
            at_work += 1
            if person.id in day_ids:
                day_at_work_or_travel += 1
        elif person.activity == Activity.TRAVEL:
            traveling += 1
            if person.id in day_ids:
                day_at_work_or_travel += 1

    # Day-shift majority should have arrived or still be finishing the walk.
    assert day_at_work_or_travel >= int(len(day_ids) * 0.85)
    assert at_work >= 40


def test_evening_return_home() -> None:
    world = create_world(seed=7, citizen_count=80)
    # After optional outings end, nearly everyone should be home asleep.
    world.step_minutes(17 * 60)  # 06:00 -> 23:00
    assert world.clock.hour == 23

    home_or_heading = 0
    for person in world.people.values():
        home = world.buildings[person.home_id]
        at_home = (
            int(round(person.x)) == home.x
            and int(round(person.y)) == home.y
            and person.activity in (Activity.SLEEP, Activity.AT_HOME)
        )
        heading_home = (
            person.activity == Activity.TRAVEL
            and person.path
            and person.path[-1] == (home.x, home.y)
        )
        if at_home or heading_home:
            home_or_heading += 1
    assert home_or_heading >= 70


def test_same_seed_is_deterministic() -> None:
    a = create_world(seed=99, citizen_count=80)
    b = create_world(seed=99, citizen_count=80)
    a.step_minutes(8 * 60)
    b.step_minutes(8 * 60)

    assert [(p.name, p.home_id, p.work_id, p.shift) for p in a.people.values()] == [
        (p.name, p.home_id, p.work_id, p.shift) for p in b.people.values()
    ]
    assert [(p.x, p.y, p.activity) for p in a.people.values()] == [
        (p.x, p.y, p.activity) for p in b.people.values()
    ]


def test_different_seeds_differ() -> None:
    a = create_world(seed=1, citizen_count=80)
    b = create_world(seed=2, citizen_count=80)
    assert [p.name for p in a.people.values()] != [p.name for p in b.people.values()]
