# SitSimCity M9 — Chronicle Polish

## Goal

Stored and displayed life text should read as a **small-town chronicle** (specific, slightly wry, person-centered) instead of audit logs and friendship metrics. Light inhabit UI polish so those words stay readable while sitting with someone.

Frozen: M5.5 friendship math, M6 circumstance rates, M8 shift/schedule structure. No romance, no new life systems.

## What changed

### Write-time phrase tables (`sim/systems/chronicle.py`)

- Seeded `pick_phrase(rng, key, **fmt)` + variant tables for life events, bond milestones, contact story notes, plan notes
- Circumstance / day-1 / social / schedule authors pull from tables (no day-count parentheticals in player strings)

### Display demotion

- Default social summary / origin / bond status: no `Friendship N`, `Social meetings:`, meeting tallies
- Soft work-colocation prose kept; `W` / `verbose_work` still has diagnostic counts
- Relative day phrasing (`today` / `yesterday` / `N days ago`) on recent timeline lines

### Inhabit UI

- Soft follow camera (`Camera.ease_toward`)
- Name label above followed citizen (+ close companions on-screen)
- `T` while following appends timeline under compact card (no Traits dump)
- Home map labels use street token (`Maple`), not house number
- Inhabit status bar: `Watching Tess · … · afternoon` + short keys
- `smart_truncate` at word boundaries on panel lines

## Before → after (sample voice)

| Before (log) | After (chronicle) |
| --- | --- |
| `Lives at 3 Mill Road` | `Took rooms at 3 Mill Road` |
| `Works at Mill Road Dispatch` | `Started work at Mill Road Dispatch` |
| `Fell ill (3 days)` | `Fell ill and kept to the house` |
| `Moved from A to B` | `Packed up at 3 Mill Road; keys now for 3 Pine Court` |
| `Left job at X` | `Left Pine Court Studio without another shift to go to` |
| `Overworked (N days)` | `The job ate the evenings` |
| `First met at the pub` | `Fell into conversation at the pub` |
| `Friendship 42 · peak 55` | *(hidden on inhabit; cooling / close prose kept)* |

## Seed 7 sit (Tess Nelson / Zoe Bell, day 31)

Headless dump: `python scripts/chronicle_playtest.py --seed 7`

**Tess Nelson** — moved day 10; lunch + pub on the plan; often sees Dan Parker at the shop; compact+T shows chronicle timeline without Traits / Friendship dumps.

**Zoe Bell** (quiet) — day-1 settle/job only; often sees Vera at the pub; Knows from work; compact+T stays lean.

Town-wide durable samples include illness, overwork easing, job trade, recovery — all in chronicle voice.

**CRM demotion:** PASS on default inhabit / social summary. Inspect still shows Traits.

## Tests

`pytest -q` → **79 passed** (includes `tests/test_chronicle.py`)

## Deliberately not done

- Retuning friendship, drip, decay, circumstance rates
- Surfacing raw `history` as a second log
- LLM text / romance / crime / economy
- Neighbourhood loyalty
