from __future__ import annotations

from sim.systems.social import (
    apply_relationship_staleness,
    close_companions,
    get_relationship,
    process_colocations,
    work_acquaintances,
)
from sim.types import (
    MINUTES_PER_DAY,
    SOCIAL_COOLDOWN_MINUTES,
    STALE_AFTER_DAYS,
    Activity,
    BuildingKind,
)
from sim.world import create_world


def _force_pair_at(
    world,
    a_id: int,
    b_id: int,
    activity: Activity,
    x: float,
    y: float,
) -> None:
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


def _meet_n_times(world, a_id: int, b_id: int, activity: Activity, n: int, x: float, y: float) -> None:
    for _ in range(n):
        _force_pair_at(world, a_id, b_id, activity, x, y)
        process_colocations(world)
        _advance_cooldown(world)


def test_amenity_meetings_accumulate_place_counts() -> None:
    world = create_world(seed=3, citizen_count=40)
    a_id, b_id = _two_people(world)
    pubs = [b for b in world.buildings.values() if b.kind == BuildingKind.PUB]
    assert pubs
    pub = pubs[0]
    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 4, float(pub.x), float(pub.y))
    rel = get_relationship(world, a_id, b_id)
    assert rel.times_met >= 4
    assert rel.meetings_pub >= 4
    assert rel.meetings_work == 0
    # Diminishing returns: early meetings still establish a real bond.
    assert rel.friendship >= 8
    assert rel.familiarity >= 8


def test_work_meetings_build_familiarity_not_strong_friendship() -> None:
    world = create_world(seed=5, citizen_count=40)
    # Pick two coworkers who are not both ultra-sociable (rare work friendship bump).
    by_work: dict[int, list[int]] = {}
    for p in world.people.values():
        by_work.setdefault(p.work_id, []).append(p.id)
    a_id = b_id = None
    for ids in by_work.values():
        if len(ids) < 2:
            continue
        for i, left in enumerate(ids):
            for right in ids[i + 1 :]:
                sa = world.people[left].tendencies.sociability
                sb = world.people[right].tendencies.sociability
                if sa < 85 or sb < 85:
                    a_id, b_id = left, right
                    break
            if a_id is not None:
                break
        if a_id is not None:
            break
    assert a_id is not None and b_id is not None
    work = world.buildings[world.people[a_id].work_id]
    _meet_n_times(world, a_id, b_id, Activity.WORK, 8, float(work.x), float(work.y))
    rel = get_relationship(world, a_id, b_id)
    assert rel.meetings_work >= 8
    assert rel.familiarity >= 16
    assert rel.friendship == 0  # ordinary work co-location builds familiarity only


def test_pub_friendship_grows_faster_than_work() -> None:
    world = create_world(seed=9, citizen_count=40)
    a_id, b_id = _two_people(world)
    pubs = [b for b in world.buildings.values() if b.kind == BuildingKind.PUB]
    work = next(b for b in world.buildings.values() if b.kind == BuildingKind.WORKPLACE)
    pub = pubs[0]

    _meet_n_times(world, a_id, b_id, Activity.WORK, 5, float(work.x), float(work.y))
    work_rel = get_relationship(world, a_id, b_id)

    world2 = create_world(seed=9, citizen_count=40)
    a2, b2 = _two_people(world2)
    _meet_n_times(world2, a2, b2, Activity.AT_PUB, 5, float(pub.x), float(pub.y))
    pub_rel = get_relationship(world2, a2, b2)

    assert pub_rel.friendship > work_rel.friendship
    assert pub_rel.meetings_pub == 5
    assert work_rel.meetings_work == 5


def test_visit_friendship_at_least_as_strong_as_pub() -> None:
    world = create_world(seed=11, citizen_count=40)
    a_id, b_id = _two_people(world)
    home = world.buildings[world.people[b_id].home_id]
    pubs = [b for b in world.buildings.values() if b.kind == BuildingKind.PUB]

    _meet_n_times(world, a_id, b_id, Activity.VISITING, 3, float(home.x), float(home.y))
    visit_friendship = get_relationship(world, a_id, b_id).friendship

    world2 = create_world(seed=11, citizen_count=40)
    a2, b2 = _two_people(world2)
    _meet_n_times(world2, a2, b2, Activity.AT_PUB, 3, float(pubs[0].x), float(pubs[0].y))
    pub_friendship = get_relationship(world2, a2, b2).friendship

    assert visit_friendship >= pub_friendship
    assert get_relationship(world, a_id, b_id).meetings_visit == 3


def test_first_and_last_met_timestamps() -> None:
    world = create_world(seed=12, citizen_count=30)
    a_id, b_id = _two_people(world)
    pubs = [b for b in world.buildings.values() if b.kind == BuildingKind.PUB]
    pub = pubs[0]
    start = world.total_minutes()
    _force_pair_at(world, a_id, b_id, Activity.AT_PUB, float(pub.x), float(pub.y))
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    assert rel.first_met_total_minutes == start
    assert rel.last_met_total_minutes == start

    _advance_cooldown(world)
    later = world.total_minutes()
    _force_pair_at(world, a_id, b_id, Activity.AT_PUB, float(pub.x), float(pub.y))
    process_colocations(world)
    rel = get_relationship(world, a_id, b_id)
    assert rel.first_met_total_minutes == start
    assert rel.last_met_total_minutes == later
    assert later > start


def test_staleness_decays_friendship_keeps_totals_and_peak() -> None:
    world = create_world(seed=13, citizen_count=30)
    a_id, b_id = _two_people(world)
    pubs = [b for b in world.buildings.values() if b.kind == BuildingKind.PUB]
    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 10, float(pubs[0].x), float(pubs[0].y))
    rel = get_relationship(world, a_id, b_id)
    peak = rel.peak_friendship
    times = rel.times_met
    pubs_met = rel.meetings_pub
    assert peak >= 20
    assert rel.friendship == peak

    # Pretend they last met long ago, then roll several days.
    rel.last_met_total_minutes = world.total_minutes() - (STALE_AFTER_DAYS + 3) * MINUTES_PER_DAY
    before = rel.friendship
    for _ in range(4):
        world.clock.day += 1
        apply_relationship_staleness(world)
    assert rel.friendship < before
    assert rel.peak_friendship == peak
    assert rel.times_met == times
    assert rel.meetings_pub == pubs_met


def test_renewed_meeting_reactivates_stale_friendship() -> None:
    world = create_world(seed=14, citizen_count=30)
    a_id, b_id = _two_people(world)
    pubs = [b for b in world.buildings.values() if b.kind == BuildingKind.PUB]
    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 12, float(pubs[0].x), float(pubs[0].y))
    rel = get_relationship(world, a_id, b_id)
    peak = rel.peak_friendship
    # Force a cooled state: peak remembered, current much lower, days apart.
    rel.friendship = max(1, peak // 3)
    rel.last_met_total_minutes = world.total_minutes() - 5 * MINUTES_PER_DAY
    stale_level = rel.friendship
    assert stale_level <= peak * 0.6

    _meet_n_times(world, a_id, b_id, Activity.AT_PUB, 1, float(pubs[0].x), float(pubs[0].y))
    assert rel.friendship > stale_level
    # Amenity reunion crawls — does not snap back to peak.
    assert rel.friendship <= stale_level + 2
    assert rel.friendship < peak
    assert rel.peak_friendship == peak


def test_many_work_acquaintances_few_close_friends() -> None:
    world = create_world(seed=7, citizen_count=50)
    # Several workdays of ordinary simulation.
    world.step_minutes(5 * MINUTES_PER_DAY)
    # Find someone with multiple coworkers.
    person = max(
        world.people.values(),
        key=lambda p: sum(1 for o in world.people.values() if o.work_id == p.work_id and o.id != p.id),
    )
    acquaintances = work_acquaintances(world, person.id, limit=10)
    close = close_companions(world, person.id, limit=10)
    assert len(acquaintances) >= 2
    # Close friends should be fewer than workplace acquaintances for a typical worker.
    assert len(close) <= len(acquaintances)


def test_relationship_snapshot_is_deterministic() -> None:
    a = create_world(seed=21, citizen_count=40)
    b = create_world(seed=21, citizen_count=40)
    a.step_minutes(3 * MINUTES_PER_DAY)
    b.step_minutes(3 * MINUTES_PER_DAY)

    def snap(world) -> set[tuple]:
        out = set()
        for key, rel in world.relationships.items():
            out.add(
                (
                    key,
                    rel.familiarity,
                    rel.friendship,
                    rel.peak_friendship,
                    rel.times_met,
                    rel.meetings_work,
                    rel.meetings_pub,
                    rel.meetings_cafe,
                    rel.meetings_shop,
                    rel.meetings_visit,
                    rel.meetings_other,
                    rel.first_met_total_minutes,
                    rel.last_met_total_minutes,
                )
            )
        return out

    assert snap(a) == snap(b)
