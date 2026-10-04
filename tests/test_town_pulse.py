"""M8: denser town, day/evening shifts, quieter-but-not-empty mid-day."""

from __future__ import annotations

from collections import Counter

from sim.types import Activity
from sim.world import create_world

STREET_OR_AMENITY = {
    Activity.TRAVEL,
    Activity.AT_CAFE,
    Activity.AT_SHOP,
    Activity.AT_PUB,
    Activity.VISITING,
}


def test_default_world_is_denser() -> None:
    world = create_world(seed=42)
    assert len(world.people) == 80
    kinds = Counter(b.kind.name for b in world.buildings.values())
    assert kinds["HOME"] == 32
    assert kinds["WORKPLACE"] == 10
    assert kinds["CAFE"] == 2
    assert kinds["SHOP"] == 2
    assert kinds["PUB"] == 2


def test_shift_mix_about_three_quarters_day() -> None:
    world = create_world(seed=7, citizen_count=80)
    shifts = Counter(p.shift for p in world.people.values())
    assert set(shifts) <= {"day", "evening"}
    assert shifts["day"] + shifts["evening"] == 80
    # Roughly 75/25 — allow seed variance.
    assert 55 <= shifts["day"] <= 70
    assert 10 <= shifts["evening"] <= 25


def test_mid_morning_has_sparse_street_life() -> None:
    world = create_world(seed=7, citizen_count=80)
    # 06:00 -> 10:30 — after morning rush, before lunch peak.
    world.step_minutes(4 * 60 + 30)
    assert world.clock.hour == 10

    day_at_work = sum(
        1
        for p in world.people.values()
        if p.shift == "day" and p.activity == Activity.WORK
    )
    out_and_about = sum(1 for p in world.people.values() if p.activity in STREET_OR_AMENITY)
    evening_awake = sum(
        1
        for p in world.people.values()
        if p.shift == "evening" and p.activity != Activity.SLEEP
    )

    # Day shift mostly settled at work — quieter than rush.
    assert day_at_work >= 40
    # But streets/amenities are not empty (errands, evening pre-work, travel).
    assert out_and_about >= 3
    assert evening_awake >= 5
    # Mid-day presence stays well below a full-town rush.
    assert out_and_about < 35


def test_evening_rush_has_day_leavers_and_evening_arrivers() -> None:
    world = create_world(seed=13, citizen_count=80)
    # 06:00 -> 17:15 — day shift leaving / evening shift arriving.
    world.step_minutes(11 * 60 + 15)
    assert world.clock.hour == 17

    day_leavingish = sum(
        1
        for p in world.people.values()
        if p.shift == "day"
        and p.activity
        in {
            Activity.TRAVEL,
            Activity.AT_CAFE,
            Activity.AT_SHOP,
            Activity.AT_PUB,
            Activity.VISITING,
            Activity.SLEEP,
            Activity.AT_HOME,
        }
    )
    evening_working = sum(
        1
        for p in world.people.values()
        if p.shift == "evening" and p.activity in (Activity.WORK, Activity.TRAVEL)
    )
    assert day_leavingish >= 20
    assert evening_working >= 8


def test_shift_assignment_deterministic() -> None:
    a = create_world(seed=21, citizen_count=80)
    b = create_world(seed=21, citizen_count=80)
    assert [(p.id, p.shift, p.wake_offset_minutes) for p in a.people.values()] == [
        (p.id, p.shift, p.wake_offset_minutes) for p in b.people.values()
    ]


def test_evening_shift_plan_notes_mark_shift() -> None:
    world = create_world(seed=7, citizen_count=80)
    evening = [p for p in world.people.values() if p.shift == "evening"]
    assert evening
    assert any(
        "evening shift" in " ".join(p.plan_notes).lower() for p in evening
    )
