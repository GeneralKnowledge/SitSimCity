from __future__ import annotations

from collections import Counter

from sim.types import Activity, BuildingKind
from sim.world import create_world


OPTIONAL = {
    Activity.AT_CAFE,
    Activity.AT_SHOP,
    Activity.AT_PUB,
    Activity.VISITING,
}


def test_citizens_have_tendencies() -> None:
    world = create_world(seed=42, citizen_count=50)
    for person in world.people.values():
        t = person.tendencies
        for value in (
            t.sociability,
            t.homebody,
            t.cafe_affinity,
            t.shop_affinity,
            t.pub_affinity,
            t.routine_adherence,
        ):
            assert 0 <= value <= 100
        assert person.plan_notes  # every citizen gets at least a home/evening note


def test_optional_activities_occur_during_day() -> None:
    world = create_world(seed=42, citizen_count=50)
    seen: set[Activity] = set()
    # Sample through a full waking day.
    for _ in range(16 * 60):
        world.step_once()
        for person in world.people.values():
            if person.activity in OPTIONAL:
                seen.add(person.activity)
    assert Activity.AT_CAFE in seen or Activity.AT_SHOP in seen
    assert Activity.AT_PUB in seen
    assert Activity.VISITING in seen


def test_people_use_amenity_buildings() -> None:
    world = create_world(seed=11, citizen_count=50)
    amenity_ids = {
        b.id
        for b in world.buildings.values()
        if b.kind in (BuildingKind.PUB, BuildingKind.SHOP, BuildingKind.CAFE)
    }
    visited = 0
    for _ in range(18 * 60):
        world.step_once()
        for person in world.people.values():
            if person.activity in OPTIONAL and person.activity != Activity.VISITING:
                b = world.building_at(int(round(person.x)), int(round(person.y)))
                if b and b.id in amenity_ids and not person.path:
                    visited += 1
    assert visited > 0


def test_tendencies_create_different_patterns() -> None:
    world = create_world(seed=42, citizen_count=50)
    # Run two days and count optional destination kinds per person via plan notes.
    pub_lovers = 0
    homebodies = 0
    for person in world.people.values():
        notes = " ".join(person.plan_notes).lower()
        if "pub" in notes:
            pub_lovers += 1
        if "straight home" in notes:
            homebodies += 1
    assert pub_lovers >= 1
    assert homebodies >= 1
    assert pub_lovers != len(world.people)


def test_colocated_workers_gain_familiarity() -> None:
    world = create_world(seed=7, citizen_count=50)
    world.step_minutes(4 * 60)  # into mid-morning work
    assert sum(1 for p in world.people.values() if p.activity == Activity.WORK) >= 40
    world.step_minutes(3 * 60)  # several social cooldown windows at work
    assert world.relationships
    work_rels = [rel for rel in world.relationships.values() if rel.meetings_work > 0]
    assert work_rels
    strongest_familiarity = max(rel.familiarity for rel in work_rels)
    assert strongest_familiarity >= 2
    # Workplace presence alone should not mint close friends.
    assert max(rel.friendship for rel in work_rels) < 20
    met = sum(rel.times_met for rel in world.relationships.values())
    assert met >= 1


def test_daily_life_is_deterministic() -> None:
    a = create_world(seed=21, citizen_count=40)
    b = create_world(seed=21, citizen_count=40)
    a.step_minutes(12 * 60)
    b.step_minutes(12 * 60)
    assert [(p.activity, round(p.x, 3), round(p.y, 3), p.plan_notes) for p in a.people.values()] == [
        (p.activity, round(p.x, 3), round(p.y, 3), p.plan_notes) for p in b.people.values()
    ]
    assert {
        (k, v.familiarity, v.friendship, v.times_met, v.meetings_work, v.meetings_pub)
        for k, v in a.relationships.items()
    } == {
        (k, v.familiarity, v.friendship, v.times_met, v.meetings_work, v.meetings_pub)
        for k, v in b.relationships.items()
    }


def test_evening_outings_finish_by_late_night() -> None:
    world = create_world(seed=7, citizen_count=50)
    world.step_minutes(17 * 60)  # 06:00 -> 23:00
    assert world.clock.hour == 23
    counts = Counter(p.activity for p in world.people.values())
    assert counts[Activity.SLEEP] >= 45
    assert counts.get(Activity.AT_PUB, 0) + counts.get(Activity.VISITING, 0) <= 5


def test_evening_habits_become_sticky() -> None:
    world = create_world(seed=8, citizen_count=50)
    world.step_minutes(8 * 1440)
    habitual = [
        p
        for p in world.people.values()
        if p.habit_evening in {"pub", "visit", "home", "cafe", "shop"}
    ]
    assert len(habitual) >= 40
    # Someone who likes the pub should often lock onto that habit.
    pub_habits = [p for p in world.people.values() if p.habit_evening == "pub"]
    assert pub_habits


def test_repeat_visits_can_stick_to_one_host() -> None:
    world = create_world(seed=26, citizen_count=50)
    visit_days = Counter()
    for _ in range(10):
        for person in world.people.values():
            for note in person.plan_notes:
                if note.startswith("Visit "):
                    visit_days[(person.id, note)] += 1
        world.step_minutes(1440)
    assert max(visit_days.values(), default=0) >= 3


def test_amenity_meetings_write_history() -> None:
    world = create_world(seed=8, citizen_count=50)
    world.step_minutes(6 * 1440)
    with_history = [p for p in world.people.values() if p.history]
    assert with_history
    assert any(
        "pub" in line.lower() or "cafe" in line.lower() or "Visited" in line or "Saw " in line
        for p in with_history
        for line in p.history
    )
