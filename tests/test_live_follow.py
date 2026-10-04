"""M7.6: live-follow UI polish — compact card, soft work prose, random pick."""

from __future__ import annotations

from app.render import _compact_follow_lines, _person_inspector_lines
from sim.rng import make_rng
from sim.systems.observe import (
    advance_days,
    origin_summary_lines,
    relationship_detail_lines,
)
from sim.systems.social import get_relationship, process_colocations
from sim.types import Activity, BuildingKind
from sim.world import create_world


def test_origin_softens_work_colocations_by_default() -> None:
    world = create_world(seed=11, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    cafe = next(b for b in world.buildings.values() if b.kind == BuildingKind.CAFE)
    world.people[a_id].activity = Activity.AT_CAFE
    world.people[b_id].activity = Activity.AT_CAFE
    world.people[a_id].x = float(cafe.x)
    world.people[a_id].y = float(cafe.y)
    world.people[b_id].x = float(cafe.x)
    world.people[b_id].y = float(cafe.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    rel.meetings_work = 40
    # Same workplace → soft coworker wording.
    world.people[b_id].work_id = world.people[a_id].work_id

    soft = "\n".join(origin_summary_lines(world, rel, a_id))
    assert "Social meetings:" in soft
    assert "Often at work together" in soft
    assert "Work colocations:" not in soft
    assert "Currently coworkers" in soft

    verbose = "\n".join(origin_summary_lines(world, rel, a_id, verbose_work=True))
    assert "Work colocations: 40" in verbose
    assert "familiarity only" in verbose.lower() or "no friendship" in verbose.lower()


def test_origin_hides_zero_work_colocations() -> None:
    world = create_world(seed=3, citizen_count=20)
    a_id, b_id = sorted(world.people)[:2]
    shop = next(b for b in world.buildings.values() if b.kind == BuildingKind.SHOP)
    world.people[a_id].activity = Activity.AT_SHOP
    world.people[b_id].activity = Activity.AT_SHOP
    world.people[a_id].x = float(shop.x)
    world.people[a_id].y = float(shop.y)
    world.people[b_id].x = float(shop.x)
    world.people[b_id].y = float(shop.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    rel.meetings_work = 0
    joined = "\n".join(origin_summary_lines(world, rel, a_id))
    assert "Work colocations:" not in joined
    assert "Often at work together" not in joined


def test_compact_follow_hides_traits_and_raw_work_counts() -> None:
    world = create_world(seed=7, citizen_count=50)
    advance_days(world, 20)
    person = next(iter(world.people.values()))
    lines = _compact_follow_lines(world, person)
    joined = "\n".join(lines)
    assert "FOLLOWING" in joined
    assert "Now:" in joined
    assert "Shift ·" in joined
    assert "Traits" not in joined
    assert "Work colocations:" not in joined
    assert "Sit with them" in joined

    # Following without T/J uses compact card.
    follow_lines = _person_inspector_lines(world, person, following=True)
    assert "Traits" not in "\n".join(follow_lines)

    # Inspect (not following) keeps the fuller card.
    inspect_lines = _person_inspector_lines(world, person, following=False)
    assert "Traits" in "\n".join(inspect_lines)


def test_bond_detail_uses_soft_work_prose() -> None:
    world = create_world(seed=11, citizen_count=30)
    a_id, b_id = sorted(world.people)[:2]
    cafe = next(b for b in world.buildings.values() if b.kind == BuildingKind.CAFE)
    for pid in (a_id, b_id):
        p = world.people[pid]
        p.activity = Activity.AT_CAFE
        p.x = float(cafe.x)
        p.y = float(cafe.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    rel.meetings_work = 12
    world.people[b_id].work_id = world.people[a_id].work_id
    detail = "\n".join(relationship_detail_lines(world, a_id, b_id))
    assert "Social meetings:" in detail
    assert "Often at work together" in detail
    assert "Work colocations:" not in detail


def test_ui_random_pick_deterministic_per_nonce() -> None:
    world = create_world(seed=7, citizen_count=50)
    ids = sorted(world.people)

    def pick(nonce: int) -> int:
        rng = make_rng(world.seed, f"ui-random-follow-{nonce}")
        return rng.choice(ids)

    assert pick(1) == pick(1)
    assert pick(1) != pick(2) or len(ids) == 1
