"""M10: lite death, adult replacements, soft couple / grown-child story beats."""

from __future__ import annotations

from sim.generate.names import bump_occupation_title
from sim.systems.lifecycle import (
    _apply_death,
    _ensure_couple_note,
    mutual_close_pairs,
    tick_lifecycle,
)
from sim.systems.observe import advance_days, world_metrics
from sim.systems.social import get_relationship, process_colocations
from sim.types import Activity, BuildingKind, LifeEventKind
from sim.world import create_world


def test_title_bump_is_meaningless_prefix() -> None:
    from sim.rng import make_rng

    rng = make_rng(7, "title")
    assert bump_occupation_title("Clerk", rng).startswith(
        ("Senior ", "Lead ", "Head ", "Chief ")
    )
    assert bump_occupation_title("Senior Clerk", rng) == "Senior Clerk"


def test_death_replaces_and_keeps_population() -> None:
    world = create_world(seed=7, citizen_count=40)
    start_n = len(world.people)
    # Age someone up so death is plausible, then force an exit.
    victim = world.people[1]
    victim.age = 62
    home_id = victim.home_id
    _apply_death(world, 1, day=5)
    assert 1 not in world.people
    assert len(world.people) == start_n
    assert any(e.kind == LifeEventKind.DIED for e in world.town_chronicle)
    assert any(e.kind == LifeEventKind.ARRIVED for e in world.town_chronicle)
    # Replacement took the vacated home (or another home — we pass home_id).
    assert any(p.home_id == home_id for p in world.people.values())


def test_friends_get_passed_notes() -> None:
    world = create_world(seed=11, citizen_count=30)
    a_id, b_id = 1, 2
    cafe = next(b for b in world.buildings.values() if b.kind == BuildingKind.CAFE)
    for pid in (a_id, b_id):
        p = world.people[pid]
        p.activity = Activity.AT_CAFE
        p.x = float(cafe.x)
        p.y = float(cafe.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    rel.friendship = 40
    rel.peak_friendship = 40
    rel.ever_close = True
    rel.last_met_total_minutes = world.total_minutes()

    _apply_death(world, a_id, day=8)
    friend = world.people[b_id]
    assert any(e.kind == LifeEventKind.FRIEND_PASSED for e in friend.life_events)


def test_child_replacement_links_close_pair() -> None:
    world = create_world(seed=3, citizen_count=30)
    # Manufacture a mutual close older pair.
    a_id, b_id = 1, 2
    for pid in (a_id, b_id):
        world.people[pid].age = 52
    cafe = next(b for b in world.buildings.values() if b.kind == BuildingKind.CAFE)
    for pid in (a_id, b_id):
        p = world.people[pid]
        p.activity = Activity.AT_CAFE
        p.x = float(cafe.x)
        p.y = float(cafe.y)
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    rel.friendship = 50
    rel.peak_friendship = 50
    rel.ever_close = True
    rel.last_met_total_minutes = world.total_minutes()
    assert mutual_close_pairs(world)

    import sim.systems.lifecycle as life

    victim_id = 3
    home_id = world.people[victim_id].home_id
    work_id = world.people[victim_id].work_id
    original = life.CHILD_REPLACEMENT_CHANCE
    life.CHILD_REPLACEMENT_CHANCE = 1.0
    try:
        child = life._spawn_replacement(
            world, day=9, home_id=home_id, preferred_work_id=work_id
        )
    finally:
        life.CHILD_REPLACEMENT_CHANCE = original

    assert child.parent_ids is not None
    assert set(child.parent_ids) == {a_id, b_id}
    assert any(e.kind == LifeEventKind.ARRIVED for e in child.life_events)
    for pid in child.parent_ids:
        assert any(
            e.kind == LifeEventKind.CHILD_SETTLED for e in world.people[pid].life_events
        )
    assert "keeping_company" in {
        be.kind for be in get_relationship(world, *child.parent_ids).bond_events
    }
    # Adult, not a juvenile subsystem.
    assert child.age >= 22


def test_lifecycle_tick_deterministic_and_sparse() -> None:
    def run(seed: int) -> tuple[int, tuple]:
        world = create_world(seed=seed, citizen_count=50)
        # Age the town so exits can fire over a long run.
        for p in world.people.values():
            if p.id % 3 == 0:
                p.age = 60
        advance_days(world, 80)
        deaths = sum(1 for e in world.town_chronicle if e.kind == LifeEventKind.DIED)
        snap = tuple(
            (e.day, e.kind.name, e.detail) for e in world.town_chronicle if e.kind == LifeEventKind.DIED
        )
        return deaths, snap

    d1, s1 = run(7)
    d2, s2 = run(7)
    assert s1 == s2
    assert d1 == d2
    # Story-sparse: not a plague.
    assert d1 <= 12
    m = world_metrics(create_world(seed=7, citizen_count=40))
    assert m["population"] == 40


def test_population_stable_after_forced_deaths() -> None:
    world = create_world(seed=13, citizen_count=40)
    n = len(world.people)
    for day in range(2, 8):
        # Always kill the lowest living id.
        victim = min(world.people)
        world.people[victim].age = 70
        _apply_death(world, victim, day=day)
        assert len(world.people) == n
    assert len([e for e in world.town_chronicle if e.kind == LifeEventKind.DIED]) == 6
