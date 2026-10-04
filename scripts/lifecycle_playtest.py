#!/usr/bin/env python3
"""M10: headless death / replacement / couple story dump."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.systems.observe import advance_days, world_metrics, world_report_lines
from sim.types import LifeEventKind
from sim.world import create_world


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--citizens", type=int, default=80)
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args()

    world = create_world(seed=args.seed, citizen_count=args.citizens)
    # Nudge ages so a long sit produces a few exits without a plague.
    for p in world.people.values():
        if p.id % 4 == 0:
            p.age = min(68, p.age + 20)
    start_n = len(world.people)
    advance_days(world, args.days)
    m = world_metrics(world)

    print(f"SitSimCity M10 lifecycle · seed {args.seed} · day {world.clock.day}")
    print(f"Population start/end: {start_n} / {m['population']}")
    print(
        f"Deaths: {m['town_deaths']}  Arrivals: {m['town_arrivals']}  "
        f"Keeping company: {m['keeping_company_pairs']}"
    )
    print("\n--- Town chronicle ---")
    for e in world.town_chronicle:
        print(f"  Day {e.day}: [{e.kind.name}] {e.detail}")

    print("\n--- Grown-child arrivals ---")
    children = [p for p in world.people.values() if p.parent_ids]
    for p in children[:12]:
        parents = []
        for pid in p.parent_ids or ():
            if pid in world.people:
                parents.append(world.people[pid].name)
            else:
                parents.append(f"#{pid}")
        print(f"  {p.name} (age {p.age}) · child of {' & '.join(parents)}")
    if not children:
        print("  (none this run)")

    print("\n--- Friend-passed / title samples ---")
    n = 0
    for p in world.people.values():
        for e in p.life_events:
            if e.kind in {LifeEventKind.FRIEND_PASSED, LifeEventKind.TITLE_CHANGED, LifeEventKind.CHILD_SETTLED}:
                print(f"  {p.name}: {e.detail}")
                n += 1
                if n >= 14:
                    break
        if n >= 14:
            break

    print("\n--- W report (tail) ---")
    for line in world_report_lines(world)[:20]:
        print(line)

    ok = m["population"] == start_n and m["town_deaths"] == m["town_arrivals"]
    print(f"\nVerdict: {'PASS' if ok else 'REVIEW'} — pop stable, deaths matched by arrivals")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
