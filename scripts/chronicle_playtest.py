#!/usr/bin/env python3
"""M9: headless chronicle dump — sample life/bond/inhabit lines for seed 7."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.render import _compact_follow_lines, _person_inspector_lines
from sim.rng import make_rng
from sim.systems.observe import advance_days, citizen_timeline, timeline_lines
from sim.systems.social import close_companions, social_summary_lines, stale_companions
from sim.types import LifeEventKind
from sim.world import create_world

DURABLE = {
    LifeEventKind.BECAME_SICK,
    LifeEventKind.RECOVERED,
    LifeEventKind.BECAME_UNEMPLOYED,
    LifeEventKind.JOB_CHANGED,
    LifeEventKind.MOVED_HOME,
    LifeEventKind.BECAME_OVERWORKED,
    LifeEventKind.OVERWORK_ENDED,
}

CRM_MARKERS = (
    "Friendship ",
    "Social meetings:",
    "Social: ",
    "Work colocations:",
    "times ·",
    " · peak ",
)


def pick_named(world, needle: str) -> int | None:
    for pid, p in world.people.items():
        if needle.lower() in p.name.lower():
            return pid
    return None


def pick_quiet(world, exclude: int | None = None) -> int:
    scored = []
    for pid in sorted(world.people):
        if pid == exclude:
            continue
        close_n = len(close_companions(world, pid, limit=5))
        durable = sum(
            1 for e in world.people[pid].life_events if e.kind in DURABLE and e.day > 1
        )
        scored.append((close_n, durable, pid))
    scored.sort()
    return scored[0][2]


def crm_hits(text: str) -> list[str]:
    return [m for m in CRM_MARKERS if m in text]


def dump_person(world, person_id: int, label: str) -> dict:
    person = world.people[person_id]
    compact = _compact_follow_lines(world, person)
    compact_t = _compact_follow_lines(world, person, show_timeline=True)
    social = social_summary_lines(world, person_id)
    inspect = _person_inspector_lines(world, person, following=False)
    durable = [e for e in person.life_events if e.kind in DURABLE or e.day == 1]

    print(f"\n{'=' * 72}")
    print(f"{label}: {person.name} (id={person_id}) · day {world.clock.day}")
    print(f"{'=' * 72}")

    print("\n--- Day-1 / durable life details (sample) ---")
    for e in durable[:8]:
        print(f"  d{e.day} {e.kind.name}: {e.detail}")

    print("\n--- Social summary (default inhabit) ---")
    for line in social or ["(quiet)"]:
        print(f"  {line}")

    print("\n--- Compact follow ---")
    for line in compact:
        print(f"  {line}")

    print("\n--- Compact + T (timeline under card) ---")
    for line in compact_t:
        print(f"  {line}")

    joined_c = "\n".join(compact_t)
    joined_s = "\n".join(social)
    joined_i = "\n".join(inspect)
    hits_c = crm_hits(joined_c)
    hits_s = crm_hits(joined_s)
    print("\n--- CRM demotion checks ---")
    print(f"  compact+T CRM markers: {hits_c or 'none'}")
    print(f"  social summary CRM markers: {hits_s or 'none'}")
    print(f"  compact+T has Traits: {'Traits' in joined_c}")
    print(f"  inspect has Traits: {'Traits' in joined_i}")

    return {
        "name": person.name,
        "life_samples": [f"d{e.day} {e.kind.name}: {e.detail}" for e in durable[:8]],
        "social": social,
        "compact": compact,
        "compact_t": compact_t,
        "crm_compact": hits_c,
        "crm_social": hits_s,
        "traits_in_compact_t": "Traits" in joined_c,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--citizens", type=int, default=80)
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    world = create_world(seed=args.seed, citizen_count=args.citizens)
    advance_days(world, args.days)

    tess = pick_named(world, "Tess")
    if tess is None:
        rng = make_rng(args.seed, "chronicle-pick")
        tess = rng.choice(sorted(world.people))
    quiet = pick_quiet(world, exclude=tess)

    print(f"SitSimCity M9 chronicle dump · seed {args.seed} · day {world.clock.day}")
    results = [
        dump_person(world, tess, "Tess / named follow"),
        dump_person(world, quiet, "Quiet citizen"),
    ]

    # Town-wide sample of life-event voice
    print(f"\n{'=' * 72}")
    print("Town-wide durable event samples (first 12 found)")
    print(f"{'=' * 72}")
    n = 0
    for pid in sorted(world.people):
        for e in world.people[pid].life_events:
            if e.kind in DURABLE and e.day > 1:
                print(f"  {world.people[pid].name}: {e.detail}")
                n += 1
                if n >= 12:
                    break
        if n >= 12:
            break

    ok = all(
        not r["crm_compact"] and not r["crm_social"] and not r["traits_in_compact_t"]
        for r in results
    )
    print(f"\nVerdict: {'PASS — chronicle voice, CRM demoted' if ok else 'REVIEW needed'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
