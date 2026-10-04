"""M5.5: diminishing friendship, scarce closeness, gradual reactivation."""

from __future__ import annotations

from sim.systems.social import (
    apply_relationship_staleness,
    get_relationship,
    process_colocations,
    social_summary_lines,
)
from sim.types import (
    CLOSE_FRIENDSHIP_MIN,
    FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS,
    FRIENDSHIP_DECAY_EVER_CLOSE_PER_DAY,
    FRIENDSHIP_DECAY_PER_DAY,
    MINUTES_PER_DAY,
    SOCIAL_COOLDOWN_MINUTES,
    Activity,
    BuildingKind,
)
from sim.world import create_world


def _force_pair_at(world, a_id, b_id, activity, x, y) -> None:
    a = world.people[a_id]
    b = world.people[b_id]
    a.activity = activity
    b.activity = activity
    a.x = x
    a.y = y
    b.x = x
    b.y = y
    a.path.clear()
    b.path.clear()


def _advance_cooldown(world) -> None:
    world.clock.minute_of_day += SOCIAL_COOLDOWN_MINUTES
    while world.clock.minute_of_day >= MINUTES_PER_DAY:
        world.clock.minute_of_day -= MINUTES_PER_DAY
        world.clock.day += 1


def _two_people(world) -> tuple[int, int]:
    ids = sorted(world.people)
    return ids[0], ids[1]


def _meet_n_times(world, a_id, b_id, activity, n, x, y) -> None:
    for _ in range(n):
        _force_pair_at(world, a_id, b_id, activity, x, y)
        process_colocations(world)
        _advance_cooldown(world)


def test_friendship_gains_diminish_with_strength() -> None:
    world = create_world(seed=3, citizen_count=30)
    a_id, b_id = _two_people(world)
    pub = next(b for b in world.buildings.values() if b.kind == BuildingKind.PUB)
    gains: list[int] = []
    prev = 0
    for _ in range(8):
        _force_pair_at(world, a_id, b_id, Activity.AT_PUB, float(pub.x), float(pub.y))
        process_colocations(world)
        rel = get_relationship(world, a_id, b_id)
        gains.append(rel.friendship - prev)
        prev = rel.friendship
        _advance_cooldown(world)
    # Early gains should be larger than later gains.
    assert gains[0] >= gains[-1]
    assert gains[0] >= 2
    assert sum(gains) < 8 * gains[0]  # not flat accumulation


def test_work_never_grants_friendship() -> None:
    world = create_world(seed=5, citizen_count=40)
    by_work: dict[int, list[int]] = {}
    for p in world.people.values():
        by_work.setdefault(p.work_id, []).append(p.id)
    coworkers = next(ids for ids in by_work.values() if len(ids) >= 2)
    a_id, b_id = coworkers[0], coworkers[1]
    work = world.buildings[world.people[a_id].work_id]
    _meet_n_times(world, a_id, b_id, Activity.WORK, 12, float(work.x), float(work.y))
    rel = get_relationship(world, a_id, b_id)
    assert rel.familiarity >= 20
    assert rel.friendship == 0


def test_amenity_reunion_does_not_snap_to_peak() -> None:
    world = create_world(seed=8, citizen_count=30)
    a_id, b_id = _two_people(world)
    pub = next(b for b in world.buildings.values() if b.kind == BuildingKind.PUB)
    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 15, float(pub.x), float(pub.y))
    rel = get_relationship(world, a_id, b_id)
    peak = rel.peak_friendship
    assert peak >= CLOSE_FRIENDSHIP_MIN
    rel.friendship = max(1, int(peak * 0.4))
    cooled = rel.friendship
    rel.last_met_total_minutes = world.total_minutes() - 5 * MINUTES_PER_DAY

    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 1, float(pub.x), float(pub.y))
    assert rel.friendship == cooled + 1
    assert rel.peak_friendship == peak
    assert rel.friendship < peak


def test_visit_reunion_rebuilds_faster_than_amenity_but_not_to_peak() -> None:
    world = create_world(seed=8, citizen_count=30)
    a_id, b_id = _two_people(world)
    home = world.buildings[world.people[b_id].home_id]
    pub = next(b for b in world.buildings.values() if b.kind == BuildingKind.PUB)
    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 15, float(pub.x), float(pub.y))
    rel = get_relationship(world, a_id, b_id)
    peak = rel.peak_friendship
    rel.friendship = max(1, int(peak * 0.4))
    cooled = rel.friendship
    rel.last_met_total_minutes = world.total_minutes() - 5 * MINUTES_PER_DAY

    _meet_n_times(world, a_id, b_id, Activity.VISITING, 1, float(home.x), float(home.y))
    assert cooled < rel.friendship <= cooled + 2
    assert rel.friendship < peak
    assert rel.peak_friendship == peak


def test_ever_close_decays_faster_after_longer_gap() -> None:
    world = create_world(seed=9, citizen_count=30)
    a_id, b_id = _two_people(world)
    rel = get_relationship(world, a_id, b_id)
    rel.times_met = 5
    rel.first_met_total_minutes = 0
    rel.peak_friendship = 40
    rel.friendship = 40
    rel.last_met_total_minutes = world.total_minutes() - FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS * MINUTES_PER_DAY
    apply_relationship_staleness(world)
    assert rel.friendship == 40 - FRIENDSHIP_DECAY_EVER_CLOSE_PER_DAY
    assert rel.peak_friendship == 40

    # Non-close relationships keep the slower decay.
    rel2 = get_relationship(world, a_id, sorted(world.people)[2])
    rel2.times_met = 2
    rel2.first_met_total_minutes = 0
    rel2.peak_friendship = 10
    rel2.friendship = 10
    rel2.last_met_total_minutes = world.total_minutes() - FRIENDSHIP_DECAY_EVER_CLOSE_AFTER_DAYS * MINUTES_PER_DAY
    apply_relationship_staleness(world)
    assert rel2.friendship == 10 - FRIENDSHIP_DECAY_PER_DAY


def test_inspector_shows_relationship_continuity() -> None:
    world = create_world(seed=1, citizen_count=50)
    world.step_minutes(12 * MINUTES_PER_DAY)
    # Find someone with a close companion if possible; else force one.
    from sim.systems.social import close_companions

    subject = None
    for person in world.people.values():
        if close_companions(world, person.id, limit=1):
            subject = person
            break
    if subject is None:
        a_id, b_id = _two_people(world)
        pub = next(b for b in world.buildings.values() if b.kind == BuildingKind.PUB)
        _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 20, float(pub.x), float(pub.y))
        subject = world.people[a_id]
    lines = social_summary_lines(world, subject.id)
    joined = "\n".join(lines)
    assert "Close with:" in joined or "At work knows:" in joined or "Often sees:" in joined
    if "Close with:" in joined:
        assert "Met " in joined
        assert "Friendship " in joined
        assert "peak " in joined
