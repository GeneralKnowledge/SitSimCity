"""M7.5: timeline cadence, work/social clarity, follow picks."""

from __future__ import annotations

from sim.rng import make_rng
from sim.systems.circumstances import record_life_event
from sim.systems.observe import (
    advance_days,
    citizen_timeline,
    origin_summary_lines,
    relationship_detail_lines,
)
from sim.systems.social import get_relationship, process_colocations
from sim.types import (
    BECAME_CLOSE_LIFE_EVENT_GAP_DAYS,
    MINUTES_PER_DAY,
    SOCIAL_COOLDOWN_MINUTES,
    TIMELINE_MAX_BECAME_CLOSE,
    TIMELINE_MAX_REUNITED,
    Activity,
    BuildingKind,
    LifeEvent,
    LifeEventKind,
)
from sim.world import create_world


def test_day1_placement_persisted_as_life_events() -> None:
    world = create_world(seed=7, citizen_count=20)
    person = world.people[1]
    kinds = {e.kind for e in person.life_events}
    assert LifeEventKind.SETTLED_HOME in kinds
    assert LifeEventKind.STARTED_JOB in kinds
    entries = citizen_timeline(world, person.id, limit=20)
    assert any("Lives at" in e.text for e in entries)
    assert any("Works at" in e.text for e in entries)


def test_reunited_not_written_to_life_events() -> None:
    world = create_world(seed=3, citizen_count=20)
    person = world.people[1]
    before = len(person.life_events)
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.REUNITED,
            day=10,
            detail="Reunited with Someone",
            related_person_id=2,
        ),
    )
    assert len(person.life_events) == before
    assert not any(e.kind == LifeEventKind.REUNITED for e in person.life_events)


def test_became_close_life_event_throttled() -> None:
    world = create_world(seed=4, citizen_count=20)
    person = world.people[1]
    record_life_event(
        person,
        LifeEvent(LifeEventKind.BECAME_CLOSE, 10, "Became close with A", 2),
    )
    record_life_event(
        person,
        LifeEvent(LifeEventKind.BECAME_CLOSE, 10 + BECAME_CLOSE_LIFE_EVENT_GAP_DAYS - 1, "Became close with B", 3),
    )
    closes = [e for e in person.life_events if e.kind == LifeEventKind.BECAME_CLOSE]
    assert len(closes) == 1
    record_life_event(
        person,
        LifeEvent(
            LifeEventKind.BECAME_CLOSE,
            10 + BECAME_CLOSE_LIFE_EVENT_GAP_DAYS,
            "Became close with C",
            4,
        ),
    )
    closes = [e for e in person.life_events if e.kind == LifeEventKind.BECAME_CLOSE]
    assert len(closes) == 2


def test_timeline_caps_became_close_and_reunited() -> None:
    from sim.systems.social import append_bond_event
    from sim.types import BondEvent

    world = create_world(seed=5, citizen_count=20)
    a_id, b_id = 1, 2
    # Fabricate many bond milestones
    for other_id in range(2, 12):
        rel = get_relationship(world, a_id, other_id)
        append_bond_event(
            rel,
            BondEvent(20 + other_id, "became_close", "Became close at the cafe", "cafe"),
        )
        append_bond_event(
            rel,
            BondEvent(40 + other_id, "reunited", "Reunited at the cafe", "cafe"),
        )
    entries = citizen_timeline(world, a_id, limit=40)
    assert sum(1 for e in entries if e.kind == "became_close") <= TIMELINE_MAX_BECAME_CLOSE
    assert sum(1 for e in entries if e.kind == "reunited") <= TIMELINE_MAX_REUNITED


def test_work_vs_social_meeting_clarity() -> None:
    world = create_world(seed=11, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    cafe = next(b for b in world.buildings.values() if b.kind == BuildingKind.CAFE)
    work = world.buildings[world.people[a_id].work_id]
    world.people[a_id].activity = Activity.AT_CAFE
    world.people[b_id].activity = Activity.AT_CAFE
    world.people[a_id].x = float(cafe.x)
    world.people[a_id].y = float(cafe.y)
    world.people[b_id].x = float(cafe.x)
    world.people[b_id].y = float(cafe.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    # Force some work colocations for display
    rel.meetings_work = 12
    # Soft default: no raw work-colocation dump in the inhabit inspector.
    lines = origin_summary_lines(world, rel, a_id)
    joined = "\n".join(lines)
    assert "Origin: Café" in joined or "Origin: Cafe" in joined
    assert "Social meetings:" in joined
    assert "Work colocations:" not in joined
    detail = "\n".join(relationship_detail_lines(world, a_id, b_id))
    assert "Social meetings:" in detail
    assert "Work colocations:" not in detail
    # Diagnostic path still exposes raw counts when asked.
    verbose = "\n".join(origin_summary_lines(world, rel, a_id, verbose_work=True))
    assert "Work colocations:" in verbose
    assert "familiarity only" in verbose.lower() or "no friendship" in verbose.lower()


def test_follow_pick_deterministic() -> None:
    def pick(seed: int) -> int:
        world = create_world(seed=seed, citizen_count=50)
        rng = make_rng(seed, "follow-playtest-pick")
        return rng.choice(sorted(world.people))

    assert pick(7) == pick(7)
    assert pick(7) != pick(1)


def test_origin_still_first_meeting_context() -> None:
    world = create_world(seed=7, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    shop = next(b for b in world.buildings.values() if b.kind == BuildingKind.SHOP)
    for pid in (a_id, b_id):
        p = world.people[pid]
        p.activity = Activity.AT_SHOP
        p.x = float(shop.x)
        p.y = float(shop.y)
        p.path.clear()
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    assert rel.origin_context == "shop"
    # Many work meetings later must not rewrite origin.
    rel.meetings_work = 50
    lines = "\n".join(origin_summary_lines(world, rel, a_id))
    assert "Origin: Shop" in lines
    assert "Met through work" not in lines


def test_m55_work_still_grants_no_friendship() -> None:
    world = create_world(seed=5, citizen_count=40)
    by_work: dict[int, list[int]] = {}
    for p in world.people.values():
        by_work.setdefault(p.work_id, []).append(p.id)
    coworkers = next(ids for ids in by_work.values() if len(ids) >= 2)
    a_id, b_id = coworkers[0], coworkers[1]
    work = world.buildings[world.people[a_id].work_id]
    for _ in range(5):
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
