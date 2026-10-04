from __future__ import annotations

import random
from typing import TYPE_CHECKING

from sim.rng import make_rng
from sim.systems.social import get_relationship, social_meeting_count
from sim.types import Activity, BuildingKind, Person, ScheduleEntry

if TYPE_CHECKING:
    from sim.world import World


def assign_schedules(world: World) -> None:
    """Rebuild each citizen's agenda for the current calendar day."""
    for person_id in sorted(world.people):
        person = world.people[person_id]
        rng = make_rng(world.seed, f"plan-d{world.clock.day}-p{person.id}")
        person.schedule = build_daily_schedule(world, person, rng)


def build_daily_schedule(
    world: World,
    person: Person,
    rng: random.Random,
) -> list[ScheduleEntry]:
    """Commute baseline plus a few tendency-weighted optional trips."""
    t = person.tendencies
    leave_home = 7 * 60 + 20 + person.wake_offset_minutes
    leave_work = 17 * 60 + (person.wake_offset_minutes % 25)
    notes: list[str] = []
    entries: list[ScheduleEntry] = [
        ScheduleEntry(0, Activity.SLEEP, person.home_id),
        ScheduleEntry(leave_home, Activity.WORK, person.work_id),
    ]

    if _roll_lunch(person, rng):
        lunch_start = 12 * 60 + rng.randint(0, 25)
        place_id, place_activity, place_name = _pick_errand_place(
            world, rng, prefer_cafe=t.cafe_affinity >= t.shop_affinity
        )
        duration = 25 + rng.randint(0, 25)
        back = min(lunch_start + duration, leave_work - 10)
        if back > lunch_start + 15:
            entries.append(ScheduleEntry(lunch_start, place_activity, place_id))
            entries.append(ScheduleEntry(back, Activity.WORK, person.work_id))
            notes.append(f"Lunch at {place_name}")

    evening = _decide_evening(world, person, rng)
    if evening is None:
        entries.append(ScheduleEntry(leave_work, Activity.SLEEP, person.home_id))
        notes.append("Straight home after work")
        _nudge_habit(person, "home")
    else:
        activity, target_id, duration, label, habit_key, visit_id = evening
        end = min(leave_work + duration, 22 * 60)
        entries.append(ScheduleEntry(leave_work, activity, target_id))
        entries.append(ScheduleEntry(end, Activity.SLEEP, person.home_id))
        notes.append(label)
        _nudge_habit(person, habit_key)
        if visit_id is not None:
            person.favorite_visit_id = visit_id

    person.plan_notes = notes
    entries.sort(key=lambda e: e.minute_of_day)
    return entries


def active_goal(person: Person, minute_of_day: int) -> ScheduleEntry | None:
    current: ScheduleEntry | None = None
    for entry in person.schedule:
        if entry.minute_of_day <= minute_of_day:
            current = entry
        else:
            break
    return current


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _roll_lunch(person: Person, rng: random.Random) -> bool:
    t = person.tendencies
    interest = max(t.cafe_affinity, t.shop_affinity)
    chance = (
        interest * 0.0045
        + (100 - t.routine_adherence) * 0.0025
        + (100 - t.homebody) * 0.0015
    )
    chance = _clamp01(chance)
    chance = max(0.04, min(0.70, chance))
    return rng.random() < chance


def _buildings_of_kind(world: World, kind: BuildingKind) -> list:
    return [b for b in world.buildings.values() if b.kind == kind]


def _pick_errand_place(
    world: World,
    rng: random.Random,
    prefer_cafe: bool,
) -> tuple[int, Activity, str]:
    cafes = _buildings_of_kind(world, BuildingKind.CAFE)
    shops = _buildings_of_kind(world, BuildingKind.SHOP)
    if prefer_cafe and cafes:
        b = rng.choice(cafes)
        return b.id, Activity.AT_CAFE, b.name
    if shops:
        b = rng.choice(shops)
        return b.id, Activity.AT_SHOP, b.name
    if cafes:
        b = rng.choice(cafes)
        return b.id, Activity.AT_CAFE, b.name
    # Fallback should not happen in generated towns.
    home = next(iter(world.buildings.values()))
    return home.id, Activity.WAIT, home.name


def _decide_evening(
    world: World,
    person: Person,
    rng: random.Random,
) -> tuple[Activity, int, int, str, str, int | None] | None:
    """Returns activity details plus habit key and optional visit target id."""
    t = person.tendencies
    home_w = 25 + t.homebody * 0.75 + t.routine_adherence * 0.35
    pub_w = t.pub_affinity * (1.0 - t.homebody / 220.0)
    shop_w = t.shop_affinity * 0.45
    cafe_w = t.cafe_affinity * 0.30
    visit_w = t.sociability * 0.60

    if t.homebody >= 80:
        pub_w *= 0.25
        visit_w *= 0.45
        shop_w *= 0.5
        cafe_w *= 0.5

    # Sticky habits: people tend to repeat yesterday's ordinary choice.
    habit_boost = 90.0
    if person.habit_evening == "home":
        home_w += habit_boost
    elif person.habit_evening == "pub":
        pub_w += habit_boost
    elif person.habit_evening == "shop":
        shop_w += habit_boost * 0.8
    elif person.habit_evening == "cafe":
        cafe_w += habit_boost * 0.8
    elif person.habit_evening == "visit":
        visit_w += habit_boost

    # Soft pull toward the pub if a close friend likes drinking there (capped).
    best_friend_pub_pull = 0.0
    for (a, b), rel in world.relationships.items():
        if rel.friendship < 18 or person.id not in (a, b):
            continue
        other = world.people[b if a == person.id else a]
        if other.tendencies.pub_affinity >= 60 or other.habit_evening == "pub":
            best_friend_pub_pull = max(
                best_friend_pub_pull, 10 + rel.friendship * 0.15
            )
    pub_w += best_friend_pub_pull

    choices: list[tuple[float, str]] = [
        (max(0.1, home_w), "home"),
        (max(0.0, pub_w), "pub"),
        (max(0.0, shop_w), "shop"),
        (max(0.0, cafe_w), "cafe"),
        (max(0.0, visit_w), "visit"),
    ]
    pick = _weighted_choice(rng, choices)
    duration = 50 + rng.randint(0, 55)

    if pick == "home":
        return None
    if pick == "pub":
        pubs = _buildings_of_kind(world, BuildingKind.PUB)
        if not pubs:
            return None
        b = rng.choice(pubs)
        return Activity.AT_PUB, b.id, duration + 15, f"Pub: {b.name}", "pub", None
    if pick == "shop":
        shops = _buildings_of_kind(world, BuildingKind.SHOP)
        if not shops:
            return None
        b = rng.choice(shops)
        return Activity.AT_SHOP, b.id, duration, f"Shop: {b.name}", "shop", None
    if pick == "cafe":
        cafes = _buildings_of_kind(world, BuildingKind.CAFE)
        if not cafes:
            return None
        b = rng.choice(cafes)
        return Activity.AT_CAFE, b.id, duration, f"Cafe: {b.name}", "cafe", None

    target = _pick_visit_target(world, person, rng)
    if target is None:
        return None
    home = world.buildings[target.home_id]
    visit_duration = 55 + rng.randint(0, 60)
    return (
        Activity.VISITING,
        home.id,
        visit_duration,
        f"Visit {target.name}",
        "visit",
        target.id,
    )


def _nudge_habit(person: Person, habit_key: str) -> None:
    person.habit_evening = habit_key


def _pick_visit_target(world: World, person: Person, rng: random.Random) -> Person | None:
    candidates = [p for p in world.people.values() if p.id != person.id]
    if not candidates:
        return None

    # Once someone has a favourite host, usually keep visiting them.
    if (
        person.favorite_visit_id is not None
        and person.favorite_visit_id in world.people
        and rng.random() < 0.8
    ):
        return world.people[person.favorite_visit_id]

    weights: list[float] = []
    for other in candidates:
        rel = get_relationship(world, person.id, other.id)
        # Genuine friendship + social meetings matter; work familiarity does not.
        weight = 1.0 + rel.friendship * 2.0 + social_meeting_count(rel) * 0.5
        if other.work_id == person.work_id:
            weight += 6.0  # mild acquaintance bias, not friendship
        if person.favorite_visit_id == other.id:
            weight += 40.0
        weight += other.tendencies.sociability * 0.05
        weight *= 1.0 - other.tendencies.homebody * 0.003
        weights.append(max(0.1, weight))

    return _weighted_pick(rng, candidates, weights)


def _weighted_choice(rng: random.Random, choices: list[tuple[float, str]]) -> str:
    total = sum(weight for weight, _ in choices)
    roll = rng.random() * total
    acc = 0.0
    for weight, label in choices:
        acc += weight
        if roll <= acc:
            return label
    return choices[-1][1]


def _weighted_pick(rng: random.Random, items: list, weights: list[float]):
    total = sum(weights)
    roll = rng.random() * total
    acc = 0.0
    for item, weight in zip(items, weights, strict=True):
        acc += weight
        if roll <= acc:
            return item
    return items[-1]
