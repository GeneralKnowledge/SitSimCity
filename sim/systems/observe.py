"""M7 observer helpers: timelines, ranking, diagnostics. No friendship retunes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sim.types import (
    ACQUAINTANCE_FAMILIARITY_MIN,
    ACQUAINTANCE_FRIENDSHIP_MAX,
    CLOSE_FRIENDSHIP_MIN,
    MINUTES_PER_DAY,
    LifeEventKind,
    Relationship,
)

if TYPE_CHECKING:
    from sim.world import World


_CONTEXT_LABEL = {
    "work": "Work",
    "pub": "Pub",
    "cafe": "Café",
    "shop": "Shop",
    "visit": "Visits",
    "other": "Town",
}


@dataclass(frozen=True)
class TimelineEntry:
    day: int
    text: str
    kind: str = "event"


@dataclass(frozen=True)
class CitizenRank:
    person_id: int
    score: int
    life_events: int
    close: int
    cooled: int
    reunions: int
    job_changes: int
    moves: int
    illnesses: int


def advance_days(world: World, days: int) -> None:
    """Advance the simulation by whole calendar days (deterministic)."""
    if days <= 0:
        return
    world.step_minutes(days * MINUTES_PER_DAY)


def minutes_to_day(total_minutes: int) -> int:
    if total_minutes < 0:
        return 0
    return total_minutes // MINUTES_PER_DAY + 1


def context_label(context: str | None) -> str:
    if not context:
        return "Unknown"
    return _CONTEXT_LABEL.get(context, context.title())


def are_coworkers(world: World, a_id: int, b_id: int) -> bool:
    return world.people[a_id].work_id == world.people[b_id].work_id


def origin_summary_lines(
    world: World, rel: Relationship, viewer_id: int
) -> list[str]:
    """Accurate origin wording — never infer from meeting-count majority."""
    from sim.systems.social import dominant_meeting_place, social_meeting_count

    lines: list[str] = []
    origin = rel.origin_context
    lines.append(f"Origin: {context_label(origin)}")

    place = dominant_meeting_place(rel)
    social = social_meeting_count(rel)
    if place:
        place_label = "Visits" if place == "visits" else place.title()
        if origin and place != origin and not (
            place == "visits" and origin == "visit"
        ):
            lines.append(f"Frequent place: {place_label} ({social} social meetings)")
        elif social > 0:
            lines.append(f"Frequent place: {place_label} ({social})")

    other_id = rel.b_id if rel.a_id == viewer_id else rel.a_id
    if are_coworkers(world, viewer_id, other_id):
        if origin == "work":
            lines.append("Coworkers")
        else:
            lines.append(f"Also coworkers (work meetings: {rel.meetings_work})")
    elif rel.meetings_work > 0 and origin != "work":
        lines.append(f"Later overlap: work ({rel.meetings_work} meetings)")

    return lines


def citizen_timeline(world: World, person_id: int, limit: int = 24) -> list[TimelineEntry]:
    """Chronological life timeline from recorded facts + initial placement."""
    person = world.people[person_id]
    home = world.buildings[person.home_id]
    work = world.buildings[person.work_id]
    entries: list[TimelineEntry] = [
        TimelineEntry(1, f"Lives at {home.name}", "home"),
        TimelineEntry(1, f"Works at {work.name}", "work"),
    ]
    for event in person.life_events:
        entries.append(TimelineEntry(event.day, event.detail, event.kind.name.lower()))

    # Include first meetings / became-close from bond events involving this person.
    for (a, b), rel in world.relationships.items():
        if person_id not in (a, b):
            continue
        other_id = b if a == person_id else a
        other = world.people[other_id]
        for be in rel.bond_events:
            if be.kind == "first_met":
                entries.append(
                    TimelineEntry(
                        be.day,
                        f"Met {other.name} {be.detail.replace('First met ', '')}",
                        "first_met",
                    )
                )
            elif be.kind == "became_close":
                entries.append(
                    TimelineEntry(
                        be.day,
                        f"Friendship with {other.name} became close",
                        "became_close",
                    )
                )
            elif be.kind == "reunited":
                entries.append(
                    TimelineEntry(
                        be.day,
                        f"Reunited with {other.name}",
                        "reunited",
                    )
                )

    entries.sort(key=lambda e: (e.day, e.text))
    # Deduplicate identical day+text
    deduped: list[TimelineEntry] = []
    seen: set[tuple[int, str]] = set()
    for entry in entries:
        key = (entry.day, entry.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    if limit > 0:
        return deduped[-limit:]
    return deduped


def relationship_timeline(
    world: World, a_id: int, b_id: int, limit: int = 20
) -> list[TimelineEntry]:
    from sim.systems.social import days_since_met, get_relationship, social_meeting_count

    rel = get_relationship(world, a_id, b_id)
    entries: list[TimelineEntry] = []
    for be in rel.bond_events:
        entries.append(TimelineEntry(be.day, be.detail, be.kind))

    # Status snapshot lines (not invented history).
    if rel.first_met_total_minutes >= 0:
        last_day = minutes_to_day(rel.last_met_total_minutes)
        entries.append(
            TimelineEntry(
                last_day,
                (
                    f"Last seen day {last_day} · friendship {rel.friendship} "
                    f"(peak {rel.peak_friendship}) · meetings {rel.times_met} "
                    f"({social_meeting_count(rel)} social)"
                ),
                "status",
            )
        )
        gap = days_since_met(world, rel)
        if gap >= 3 and rel.peak_friendship >= CLOSE_FRIENDSHIP_MIN:
            entries.append(
                TimelineEntry(
                    world.clock.day,
                    f"{gap} days since last meeting",
                    "gap",
                )
            )

    entries.sort(key=lambda e: (e.day, e.kind, e.text))
    deduped: list[TimelineEntry] = []
    seen: set[tuple[int, str]] = set()
    for entry in entries:
        key = (entry.day, entry.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    if limit > 0:
        return deduped[-limit:]
    return deduped


def timeline_lines(entries: list[TimelineEntry], heading: str = "Timeline:") -> list[str]:
    if not entries:
        return []
    lines = [heading]
    for entry in entries:
        lines.append(f"  Day {entry.day}: {entry.text}")
    return lines


def relationship_detail_lines(
    world: World, viewer_id: int, other_id: int
) -> list[str]:
    from sim.systems.social import days_since_met, get_relationship, social_meeting_count

    rel = get_relationship(world, viewer_id, other_id)
    other = world.people[other_id]
    lines = [
        f"Bond: {other.name}",
        f"Friendship {rel.friendship} · peak {rel.peak_friendship}",
        f"Meetings {rel.times_met} ({social_meeting_count(rel)} social)",
    ]
    last = days_since_met(world, rel)
    if last >= 10_000:
        lines.append("Last seen: never")
    elif last == 0:
        lines.append("Last seen: today")
    else:
        lines.append(f"Last seen: {last} day{'s' if last != 1 else ''} ago")
    lines.extend(origin_summary_lines(world, rel, viewer_id))
    lines.extend(
        timeline_lines(
            relationship_timeline(world, viewer_id, other_id, limit=12),
            heading="Bond timeline:",
        )
    )
    return lines


def rank_interesting_citizens(world: World, limit: int = 10) -> list[CitizenRank]:
    from sim.systems.social import close_companions, stale_companions

    ranked: list[CitizenRank] = []
    for person in world.people.values():
        life = person.life_events
        job_changes = sum(1 for e in life if e.kind == LifeEventKind.JOB_CHANGED)
        moves = sum(1 for e in life if e.kind == LifeEventKind.MOVED_HOME)
        illnesses = sum(1 for e in life if e.kind == LifeEventKind.BECAME_SICK)
        reunions = sum(1 for e in life if e.kind == LifeEventKind.REUNITED)
        close = len(close_companions(world, person.id, limit=20))
        cooled = len(stale_companions(world, person.id, limit=20))
        n_rel = sum(
            1
            for (a, b), rel in world.relationships.items()
            if person.id in (a, b) and rel.times_met > 0
        )
        score = (
            len(life) * 3
            + close * 4
            + cooled * 3
            + reunions * 2
            + job_changes * 5
            + moves * 5
            + illnesses * 3
            + min(n_rel, 12)
        )
        ranked.append(
            CitizenRank(
                person_id=person.id,
                score=score,
                life_events=len(life),
                close=close,
                cooled=cooled,
                reunions=reunions,
                job_changes=job_changes,
                moves=moves,
                illnesses=illnesses,
            )
        )
    ranked.sort(key=lambda r: (-r.score, r.person_id))
    return ranked[:limit]


def interesting_relationship_pairs(
    world: World, limit: int = 8
) -> list[tuple[int, int, int]]:
    """Return (score, a_id, b_id) for bonds with rich arcs."""
    scored: list[tuple[int, int, int]] = []
    for (a, b), rel in world.relationships.items():
        if rel.times_met <= 0:
            continue
        score = (
            len(rel.bond_events) * 3
            + rel.peak_friendship
            + (10 if rel.ever_close else 0)
            + (8 if rel.last_reunion_day >= 0 else 0)
            + len(rel.story_notes) * 4
            + (5 if rel.cooling_noted else 0)
        )
        if score < 15:
            continue
        scored.append((score, a, b))
    scored.sort(reverse=True)
    return scored[:limit]


def world_metrics(world: World) -> dict:
    from sim.systems.social import (
        close_companions,
        social_meeting_count,
        stale_companions,
    )

    close_keys: set[tuple[int, int]] = set()
    acquaintance = 0
    ever_close = 0
    reunions = 0
    ge20 = ge50 = eq100 = 0
    meetings = 0
    for (a, b), rel in world.relationships.items():
        meetings += rel.times_met
        if rel.ever_close:
            ever_close += 1
        if rel.last_reunion_day >= 0:
            reunions += 1
        if rel.friendship >= 100:
            eq100 += 1
        if rel.friendship >= 50:
            ge50 += 1
        if rel.friendship >= CLOSE_FRIENDSHIP_MIN:
            ge20 += 1
        if (
            rel.familiarity >= ACQUAINTANCE_FAMILIARITY_MIN
            and rel.friendship <= ACQUAINTANCE_FRIENDSHIP_MAX
        ):
            acquaintance += 1

    for pid in world.people:
        for oid, rel, _ in close_companions(world, pid, limit=30):
            close_keys.add((min(pid, oid), max(pid, oid)))

    degrees = []
    zero_close = 0
    for pid in world.people:
        n = len(close_companions(world, pid, limit=30))
        degrees.append(n)
        if n == 0:
            zero_close += 1

    cooled = sum(len(stale_companions(world, pid, limit=30)) for pid in world.people)

    circ = Counter()
    life = Counter()
    for p in world.people.values():
        for c in p.circumstances:
            circ[c.kind.name] += 1
        for e in p.life_events:
            life[e.kind.name] += 1

    n = len(world.people)
    mean_deg = sum(degrees) / n if n else 0.0
    return {
        "day": world.clock.day,
        "population": n,
        "close_edges": len(close_keys),
        "mean_degree": mean_deg,
        "max_degree": max(degrees) if degrees else 0,
        "zero_close": zero_close,
        "acquaintance_edges": acquaintance,
        "ever_close_bonds": ever_close,
        "reunions": reunions,
        "ge20": ge20,
        "ge50": ge50,
        "eq100": eq100,
        "relationships": len(world.relationships),
        "meetings_total": meetings,
        "cooled_listings": cooled,
        "active_circumstances": dict(circ),
        "life_events": dict(life),
        "avg_life_events": (
            sum(len(p.life_events) for p in world.people.values()) / n if n else 0.0
        ),
    }


def world_report_lines(world: World) -> list[str]:
    m = world_metrics(world)
    lines = [
        f"WORLD — DAY {m['day']}",
        f"Population: {m['population']}",
        "Relationships",
        f"  Close: {m['close_edges']}",
        f"  Acquaintance: {m['acquaintance_edges']}",
        f"  Ever-close: {m['ever_close_bonds']}",
        f"  Reunions: {m['reunions']}",
        f"  Mean/max degree: {m['mean_degree']:.2f} / {m['max_degree']}",
        f"  Zero-close: {m['zero_close']}  ≥20:{m['ge20']}  ≥50:{m['ge50']}  =100:{m['eq100']}",
        "Circumstances (active)",
    ]
    active = m["active_circumstances"]
    if active:
        for kind, count in sorted(active.items()):
            lines.append(f"  {kind}: {count}")
    else:
        lines.append("  (none)")
    lines.append("Most eventful citizens")
    for rank in rank_interesting_citizens(world, limit=5):
        p = world.people[rank.person_id]
        bits = []
        if rank.job_changes:
            bits.append(f"{rank.job_changes} job")
        if rank.moves:
            bits.append(f"{rank.moves} move")
        if rank.illnesses:
            bits.append(f"{rank.illnesses} ill")
        if rank.close:
            bits.append(f"{rank.close} close")
        if rank.cooled:
            bits.append(f"{rank.cooled} cooled")
        extra = ", ".join(bits) if bits else "quiet"
        lines.append(f"  {p.name} — {rank.life_events} events ({extra})")
    lines.append("Most interesting relationships")
    for score, a, b in interesting_relationship_pairs(world, limit=5):
        lines.append(
            f"  {world.people[a].name} ↔ {world.people[b].name} (score {score})"
        )
    return lines


def format_rank_table(world: World, limit: int = 8) -> list[str]:
    lines = ["Most eventful citizens"]
    for i, rank in enumerate(rank_interesting_citizens(world, limit=limit), start=1):
        p = world.people[rank.person_id]
        lines.append(
            f"{i}. {p.name}  score={rank.score}  events={rank.life_events}  "
            f"close={rank.close}  cooled={rank.cooled}  "
            f"jobs={rank.job_changes}  moves={rank.moves}  ill={rank.illnesses}"
        )
    return lines
