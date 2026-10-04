"""M7: timelines, origin metadata, ranking, diagnostics."""

from __future__ import annotations

from sim.systems.observe import (
    advance_days,
    citizen_timeline,
    format_rank_table,
    origin_summary_lines,
    rank_interesting_citizens,
    relationship_detail_lines,
    relationship_timeline,
    world_metrics,
    world_report_lines,
)
from sim.systems.social import get_relationship, process_colocations, social_summary_lines
from sim.types import (
    MINUTES_PER_DAY,
    SOCIAL_COOLDOWN_MINUTES,
    Activity,
    BondEvent,
    BuildingKind,
)
from sim.world import create_world


def _force_pair(world, a_id, b_id, activity, x, y) -> None:
    for pid in (a_id, b_id):
        p = world.people[pid]
        p.activity = activity
        p.x = float(x)
        p.y = float(y)
        p.path.clear()


def _advance_cooldown(world) -> None:
    world.clock.minute_of_day += SOCIAL_COOLDOWN_MINUTES
    while world.clock.minute_of_day >= MINUTES_PER_DAY:
        world.clock.minute_of_day -= MINUTES_PER_DAY
        world.clock.day += 1


def test_origin_set_on_first_meeting_not_inferred_from_counts() -> None:
    world = create_world(seed=7, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    cafe = next(b for b in world.buildings.values() if b.kind == BuildingKind.CAFE)
    work = world.buildings[world.people[a_id].work_id]
    # First meet socially at cafe.
    _force_pair(world, a_id, b_id, Activity.AT_CAFE, cafe.x, cafe.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    assert rel.origin_context == "cafe"
    assert any(e.kind == "first_met" for e in rel.bond_events)

    # Later many work meetings should not rewrite origin.
    for _ in range(8):
        _advance_cooldown(world)
        _force_pair(world, a_id, b_id, Activity.WORK, work.x, work.y)
        process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    assert rel.meetings_work > rel.meetings_cafe
    assert rel.origin_context == "cafe"
    lines = origin_summary_lines(world, rel, a_id)
    assert any(line.startswith("Origin: Café") or line.startswith("Origin: Cafe") for line in lines)
    joined = " ".join(lines).lower()
    assert "met through work" not in joined
    assert "later overlap: work" in joined or "also coworkers" in joined or "work" in joined


def test_work_origin_when_first_meeting_is_work() -> None:
    world = create_world(seed=5, citizen_count=40)
    by_work: dict[int, list[int]] = {}
    for p in world.people.values():
        by_work.setdefault(p.work_id, []).append(p.id)
    coworkers = next(ids for ids in by_work.values() if len(ids) >= 2)
    a_id, b_id = coworkers[0], coworkers[1]
    work = world.buildings[world.people[a_id].work_id]
    _force_pair(world, a_id, b_id, Activity.WORK, work.x, work.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    assert rel.origin_context == "work"
    lines = origin_summary_lines(world, rel, a_id)
    assert lines[0] == "Origin: Work"


def test_citizen_timeline_ordered_and_includes_baseline() -> None:
    world = create_world(seed=7, citizen_count=20)
    person = world.people[1]
    person.life_events.clear()
    from sim.systems.circumstances import record_life_event
    from sim.types import LifeEvent, LifeEventKind

    record_life_event(
        person, LifeEvent(LifeEventKind.BECAME_SICK, 5, "Fell ill (2 days)")
    )
    record_life_event(
        person, LifeEvent(LifeEventKind.RECOVERED, 7, "Recovered from illness")
    )
    entries = citizen_timeline(world, person.id, limit=20)
    days = [e.day for e in entries]
    assert days == sorted(days)
    assert any("Lives at" in e.text for e in entries)
    assert any("Works at" in e.text for e in entries)
    assert any("Fell ill" in e.text for e in entries)
    texts = [e.text for e in entries]
    assert texts.index(next(t for t in texts if "Fell ill" in t)) < texts.index(
        next(t for t in texts if "Recovered" in t)
    )


def test_relationship_timeline_uses_bond_events() -> None:
    world = create_world(seed=3, citizen_count=20)
    a_id, b_id = 1, 2
    rel = get_relationship(world, a_id, b_id)
    rel.bond_events = [
        BondEvent(4, "first_met", "First met at the cafe", "cafe"),
        BondEvent(12, "became_close", "Became close at the cafe", "cafe"),
        BondEvent(20, "cooling", "Friendship began cooling", None),
    ]
    rel.first_met_total_minutes = 4 * MINUTES_PER_DAY
    rel.last_met_total_minutes = 18 * MINUTES_PER_DAY
    rel.times_met = 6
    rel.friendship = 10
    rel.peak_friendship = 25
    entries = relationship_timeline(world, a_id, b_id, limit=20)
    kinds = [e.kind for e in entries]
    assert "first_met" in kinds
    assert "became_close" in kinds
    assert "cooling" in kinds
    detail = relationship_detail_lines(world, a_id, b_id)
    assert any(line.startswith("Bond:") for line in detail)
    assert any("Bond timeline:" in line for line in detail)


def test_rank_interesting_citizens_deterministic() -> None:
    world = create_world(seed=7, citizen_count=50)
    advance_days(world, 40)
    a = format_rank_table(world, limit=5)
    b = format_rank_table(world, limit=5)
    assert a == b
    ranked = rank_interesting_citizens(world, limit=5)
    assert len(ranked) == 5
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_world_report_deterministic_for_seed_state() -> None:
    def report(seed: int) -> list[str]:
        world = create_world(seed=seed, citizen_count=30)
        advance_days(world, 25)
        return world_report_lines(world)

    assert report(7) == report(7)
    assert report(7) != report(8)
    lines = report(7)
    assert lines[0].startswith("WORLD — DAY")
    assert any("Most eventful citizens" in line for line in lines)


def test_advance_days_helper() -> None:
    world = create_world(seed=2, citizen_count=20)
    start = world.clock.day
    advance_days(world, 3)
    assert world.clock.day == start + 3


def test_social_summary_uses_origin_not_work_majority() -> None:
    world = create_world(seed=11, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    shop = next(b for b in world.buildings.values() if b.kind == BuildingKind.SHOP)
    _force_pair(world, a_id, b_id, Activity.AT_SHOP, shop.x, shop.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    rel.friendship = 25
    rel.peak_friendship = 25
    rel.ever_close = True
    rel.last_met_total_minutes = world.total_minutes()
    rel.meetings_shop = 6
    rel.meetings_work = 20  # majority work, but origin shop
    assert rel.origin_context == "shop"
    summary = "\n".join(social_summary_lines(world, a_id))
    assert "Origin: Shop" in summary
    assert "Met through work" not in summary


def test_world_metrics_sanity_after_run() -> None:
    world = create_world(seed=7, citizen_count=50)
    advance_days(world, 30)
    m = world_metrics(world)
    assert m["population"] == 50
    assert m["eq100"] == 0
    assert m["close_edges"] >= 0
    assert m["avg_life_events"] > 0
