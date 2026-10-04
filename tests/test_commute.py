from __future__ import annotations

from collections import Counter

from sim.types import Activity, BuildingKind
from sim.world import create_world


def test_world_has_expected_town_shape() -> None:
    world = create_world(seed=42, citizen_count=50)
    kinds = Counter(b.kind for b in world.buildings.values())
    assert kinds[BuildingKind.HOME] == 20
    assert kinds[BuildingKind.WORKPLACE] >= 4
    assert kinds[BuildingKind.PUB] == 1
    assert kinds[BuildingKind.SHOP] == 1
    assert kinds[BuildingKind.CAFE] == 1
    assert kinds[BuildingKind.POLICE] == 1
    assert kinds[BuildingKind.HOSPITAL] == 1
    assert len(world.people) == 50


def test_morning_commute_moves_people_to_work() -> None:
    world = create_world(seed=7, citizen_count=50)
    # Start of day: everyone home asleep.
    assert world.clock.minute_of_day == 6 * 60
    asleep = sum(1 for p in world.people.values() if p.activity == Activity.SLEEP)
    assert asleep == 50

    # Advance through the morning rush into mid-morning.
    world.step_minutes(3 * 60)  # 06:00 -> 09:00
    assert world.clock.hour == 9

    at_work = 0
    traveling = 0
    for person in world.people.values():
        work = world.buildings[person.work_id]
        if person.activity == Activity.WORK:
            assert int(round(person.x)) == work.x
            assert int(round(person.y)) == work.y
            at_work += 1
        elif person.activity == Activity.TRAVEL:
            traveling += 1

    # Almost everyone should have arrived; a few long paths may still be walking.
    assert at_work + traveling == 50
    assert at_work >= 40


def test_evening_return_home() -> None:
    world = create_world(seed=7, citizen_count=50)
    world.step_minutes(14 * 60)  # 06:00 -> 20:00
    assert world.clock.hour == 20

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
    assert home_or_heading >= 45


def test_same_seed_is_deterministic() -> None:
    a = create_world(seed=99, citizen_count=50)
    b = create_world(seed=99, citizen_count=50)
    a.step_minutes(8 * 60)
    b.step_minutes(8 * 60)

    assert [(p.name, p.home_id, p.work_id) for p in a.people.values()] == [
        (p.name, p.home_id, p.work_id) for p in b.people.values()
    ]
    assert [(round(p.x, 3), round(p.y, 3), p.activity) for p in a.people.values()] == [
        (round(p.x, 3), round(p.y, 3), p.activity) for p in b.people.values()
    ]


def test_different_seeds_differ() -> None:
    a = create_world(seed=1, citizen_count=50)
    b = create_world(seed=2, citizen_count=50)
    names_a = [p.name for p in a.people.values()]
    names_b = [p.name for p in b.people.values()]
    assert names_a != names_b or list(a.buildings) != list(b.buildings)


def test_clock_speed_only_changes_tick_count() -> None:
    world = create_world(seed=3, citizen_count=20)
    world.clock.paused = False
    world.clock.speed = 1.0
    steps = world.clock.consume_real_time(1.0)
    assert steps == 10
    world.clock.speed = 10.0
    steps = world.clock.consume_real_time(1.0)
    assert steps == 100
