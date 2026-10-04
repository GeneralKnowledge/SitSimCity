# SitSimCity M10 — Death & Soft Continuity

## Goal

Add **story-sized** exits and refills: death, lite friend notes, meaningless title bumps, and adult “grown child” replacements from close pairs. Romance stays surface-level (`keeping company`) so it can flavor those children — not a dating sim.

Frozen: M5.5 friendship math, M6 circumstance rates, M8 shifts, M9 chronicle voice (extended only).

## What landed

| Beat | Behavior |
| --- | --- |
| Death | Age-weighted, seeded, **≤1/day**; town chronicle line |
| Friends | Soft `FRIEND_PASSED` life event + bond story note |
| Title | Optional coworker gets `Senior`/`Lead`/`Head`/`Chief` prefix — inspect only |
| Replacement | New adult fills the slot; population stays constant |
| Grown child | Often framed as child of a mutual close pair (adult 22–40); parents get `CHILD_SETTLED` |
| Romance flavor | Occasional `keeping company` bond note on mutual close pairs |

## Seed 7 sit (90d, light age nudge)

`python scripts/lifecycle_playtest.py --seed 7 --days 90`

- Population **80 → 80**
- **11** deaths / **11** arrivals
- Grown children e.g. Wendy/Nina/Frank of Lara & Vera; Dan of Tess & Piper
- Friend notes + title bumps appear in inspect timelines
- `W` report shows town chronicle + keeping-company count

## Tests

`pytest -q` → **85 passed** (includes `tests/test_lifecycle.py`)

## Deliberately not done

- Grief meters, funerals, wills, inheritance
- Juvenile children / aging pipeline
- Marriage, housing merge, jealousy, fertility systems
- Crime / murder
