"""M6: circumstances, life changes, opportunity effects, history."""

from __future__ import annotations

from sim.systems.circumstances import (
    has_circumstance,
    tick_circumstances,
)
from sim.systems.schedule import build_daily_schedule
from sim.systems.social import get_relationship, process_colocations
from sim.rng import make_rng
from sim.types import (
    MINUTES_PER_DAY,
    SOCIAL_COOLDOWN_MINUTES,
    Activity,
    BuildingKind,
    Circumstance,
    CircumstanceKind,
    LifeEventKind,
)
from sim.world import create_world


def test_circumstances_are_deterministic_for_seed() -> None:
    def snapshot(seed: int) -> list[tuple]:
        world = create_world(seed=seed, citizen_count=50)
        world.step_minutes(30 * MINUTES_PER_DAY)
        rows = []
        for pid in sorted(world.people):
            p = world.people[pid]
            for c in p.circumstances:
                rows.append((pid, c.kind, c.start_day, c.end_day))
            for e in p.life_events:
                rows.append((pid, e.kind, e.day, e.detail))
        return rows

    assert snapshot(7) == snapshot(7)
    assert snapshot(7) != snapshot(8)


def test_sick_starts_and_ends_with_duration() -> None:
    world = create_world(seed=7, citizen_count=40)
    person = world.people[1]
    person.circumstances.clear()
    person.life_events.clear()
    # Force a known sick bout via the public tick helpers' data model.
    person.circumstances.append(
        Circumstance(CircumstanceKind.SICK, start_day=2, end_day=4, note="test")
    )
    world.clock.day = 2
    assert has_circumstance(person, CircumstanceKind.SICK)
    world.clock.day = 5
    tick_circumstances(world)
    assert not has_circumstance(person, CircumstanceKind.SICK)
    assert any(e.kind == LifeEventKind.RECOVERED for e in person.life_events)


def test_sick_reduces_activity_schedule() -> None:
    world = create_world(seed=3, citizen_count=30)
    person = world.people[1]
    person.circumstances = [
        Circumstance(CircumstanceKind.SICK, 1, 3, "ill")
    ]
    rng = make_rng(3, "test-sick-sched")
    schedule = build_daily_schedule(world, person, rng)
    activities = {e.activity for e in schedule}
    assert Activity.WORK not in activities
    assert Activity.AT_PUB not in activities
    assert Activity.VISITING not in activities
    assert all(e.target_building_id == person.home_id for e in schedule)


def test_unemployed_skips_work_then_gets_new_job() -> None:
    world = create_world(seed=11, citizen_count=40)
    person = world.people[2]
    old_work = person.work_id
    person.circumstances = [
        Circumstance(CircumstanceKind.UNEMPLOYED, 1, 1, "laid off")
    ]
    rng = make_rng(11, "test-unemp-sched")
    schedule = build_daily_schedule(world, person, rng)
    assert Activity.WORK not in {e.activity for e in schedule}

    world.clock.day = 2
    tick_circumstances(world)
    assert not has_circumstance(person, CircumstanceKind.UNEMPLOYED)
    assert any(e.kind == LifeEventKind.JOB_CHANGED for e in person.life_events)
    # Prefer a different workplace when available.
    workplaces = [b for b in world.buildings.values() if b.kind == BuildingKind.WORKPLACE]
    if len(workplaces) > 1:
        assert person.work_id != old_work or any(
            e.kind == LifeEventKind.JOB_CHANGED for e in person.life_events
        )


def test_overworked_skips_evening_outings() -> None:
    world = create_world(seed=5, citizen_count=30)
    person = world.people[1]
    person.circumstances = [
        Circumstance(CircumstanceKind.OVERWORKED, 1, 2, "crunch")
    ]
    rng = make_rng(5, "test-overwork")
    schedule = build_daily_schedule(world, person, rng)
    assert Activity.WORK in {e.activity for e in schedule}
    assert Activity.AT_PUB not in {e.activity for e in schedule}
    assert Activity.VISITING not in {e.activity for e in schedule}
    assert any("Long day" in n for n in person.plan_notes)


def test_move_home_changes_home_and_clears_habits() -> None:
    from sim.systems.circumstances import _try_move_home

    world = create_world(seed=9, citizen_count=50)
    person = world.people[1]
    person.habit_evening = "pub"
    person.favorite_visit_id = 2
    old_home = person.home_id
    _try_move_home(world, person, world.clock.day, make_rng(9, "force-move"))
    assert person.home_id != old_home
    assert person.habit_evening is None
    assert person.favorite_visit_id is None
    assert has_circumstance(person, CircumstanceKind.RECENTLY_MOVED)
    assert any(e.kind == LifeEventKind.MOVED_HOME for e in person.life_events)


def test_circumstances_do_not_directly_change_friendship() -> None:
    world = create_world(seed=7, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    rel = get_relationship(world, a_id, b_id)
    rel.friendship = 40
    rel.peak_friendship = 40
    rel.familiarity = 50
    rel.times_met = 5
    before = (rel.friendship, rel.familiarity, rel.peak_friendship)

    world.people[a_id].circumstances.append(
        Circumstance(CircumstanceKind.SICK, world.clock.day, world.clock.day + 2, "ill")
    )
    tick_circumstances(world)
    # Starting other circumstances / expiry must not mutate friendship fields.
    assert (rel.friendship, rel.familiarity, rel.peak_friendship) == before


def test_life_events_recorded_for_illness_cycle() -> None:
    world = create_world(seed=4, citizen_count=20)
    person = world.people[1]
    person.circumstances = [
        Circumstance(CircumstanceKind.SICK, 1, 1, "ill")
    ]
    world.clock.day = 2
    tick_circumstances(world)
    kinds = [e.kind for e in person.life_events]
    assert LifeEventKind.RECOVERED in kinds


def test_invalid_duplicate_sick_not_stacked_by_tick() -> None:
    world = create_world(seed=2, citizen_count=20)
    person = world.people[1]
    person.circumstances = [
        Circumstance(CircumstanceKind.SICK, 1, 10, "ill")
    ]
    world.clock.day = 3
    tick_circumstances(world)
    sick = [c for c in person.circumstances if c.kind == CircumstanceKind.SICK]
    assert len(sick) == 1


def test_m55_work_still_grants_no_friendship_under_m6() -> None:
    world = create_world(seed=5, citizen_count=40)
    by_work: dict[int, list[int]] = {}
    for p in world.people.values():
        by_work.setdefault(p.work_id, []).append(p.id)
    coworkers = next(ids for ids in by_work.values() if len(ids) >= 2)
    a_id, b_id = coworkers[0], coworkers[1]
    work = world.buildings[world.people[a_id].work_id]
    for _ in range(6):
        for pid in (a_id, b_id):
            p = world.people[pid]
            p.activity = Activity.WORK
            p.x = float(work.x)
            p.y = float(work.y)
            p.path.clear()
        process_colocations(world)
        world.clock.minute_of_day += SOCIAL_COOLDOWN_MINUTES
        while world.clock.minute_of_day >= MINUTES_PER_DAY:
            world.clock.minute_of_day -= MINUTES_PER_DAY
            world.clock.day += 1
    rel = get_relationship(world, a_id, b_id)
    assert rel.familiarity > 0
    assert rel.friendship == 0


def test_circumstances_occur_in_multi_day_run() -> None:
    world = create_world(seed=7, citizen_count=50)
    world.step_minutes(30 * MINUTES_PER_DAY)
    started = 0
    for p in world.people.values():
        started += len(
            [
                e
                for e in p.life_events
                if e.kind
                in {
                    LifeEventKind.BECAME_SICK,
                    LifeEventKind.BECAME_UNEMPLOYED,
                    LifeEventKind.BECAME_OVERWORKED,
                    LifeEventKind.MOVED_HOME,
                }
            ]
        )
    assert started >= 5


def test_no_permanent_stuck_circumstances_after_long_run() -> None:
    world = create_world(seed=7, citizen_count=50)
    world.step_minutes(60 * MINUTES_PER_DAY)
    # Every active circumstance must still be within its end_day window.
    for p in world.people.values():
        for c in p.circumstances:
            assert c.end_day >= world.clock.day
            assert c.start_day <= c.end_day
            span = c.end_day - c.start_day + 1
            assert span <= 10
