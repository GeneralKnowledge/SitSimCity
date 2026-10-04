# SitSimCity M7.5 Playtest Report

## A. What changed (hygiene only)

- REUNITED no longer written to `Person.life_events` (stays on bond events)
- BECAME_CLOSE life-events throttled (gap 5 days)
- Citizen timeline caps: ≤3 became_close, ≤1 reunited, ≤4 first_met; durable events preferred
- Bond/inspector show **Social meetings** vs **Work colocations (familiarity only)**
- Day-1 `SETTLED_HOME` / `STARTED_JOB` persisted as life events
- `scripts/follow_playtest.py --protocol` for random + quiet follows

## B. Deliberately not changed

M5.5 friendship math, M6 circumstance rates/effects, schedules, visit mechanics.

## C. Follow playtest results

| seed | days | role | name | close | cooled | tl_close | tl_reunited | jobs | ill |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | 30 | random | Tess Jones | 4 | 0 | 3 | 1 | 0 | 0 |
| 7 | 30 | quiet | Hugo Adams | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 | 100 | random | Tess Jones | 1 | 5 | 3 | 1 | 1 | 1 |
| 7 | 100 | quiet | Eve Wright | 0 | 0 | 0 | 0 | 0 | 2 |
| 1 | 100 | random | Clara Reed | 1 | 5 | 3 | 1 | 1 | 1 |
| 1 | 100 | quiet | Elena Harris | 0 | 0 | 0 | 0 | 0 | 1 |
| 13 | 100 | random | Ben Hill | 2 | 0 | 2 | 0 | 0 | 2 |
| 13 | 100 | quiet | Alice Cook | 0 | 5 | 3 | 1 | 0 | 2 |
| 42 | 100 | random | Rosa Cooper | 8 | 5 | 3 | 1 | 0 | 1 |
| 42 | 100 | quiet | Nora Wright | 0 | 0 | 0 | 0 | 0 | 3 |
| 100 | 100 | random | Gina Hill | 4 | 2 | 3 | 1 | 1 | 2 |

Cadence caps held in every run (`tl_close ≤ 3`, `tl_reunited ≤ 1`).

### Sketches

1. **Tess Jones (seed 7)** — Mechanic → illness/overwork → Town Ledger → Harbor Logistics courier → unemployed; one café friend (Yvonne) remains; earlier café circle cooled. Readable arc.
2. **Hugo Adams (seed 7, quiet, 30d)** — Clerk; lunch/shop meetings; zero close friends. Ordinary.
3. **Eve Wright (seed 7, quiet, 100d)** — Two illnesses, brief overwork, shop/pub acquaintances, zero close. Boring life preserved.
4. **Clara Reed (seed 1)** — Job change + illness; one close, several cooled.
5. **Ben Hill (seed 13)** — Two illnesses; two close; no job change; calmer social life.
6. **Nora Wright (seed 42, quiet)** — Three illnesses; zero close; still functioning.

## D. Verdict: person vs database row

**Partially → leaning Yes for durable arcs; Yes for quiet lives.**

After hygiene, Tess’s 100-day timeline is dominated by illness, overwork, and job changes rather than reunion spam. Quiet citizens read as people who simply work and occasionally go out. Remaining spreadsheet feel is mostly “became close” clustering near the cap and large work-colocation numbers next to small social counts (now clearly labelled).

## E. Remaining sharp edges

- Work colocations still accumulate to hundreds (display-only; math unchanged)
- “Became close” still can appear in a short window up to the cap of 3
- Some quiet citizens with cooled bonds (Alice Cook) blur “quiet” vs “formerly social”
- Job churn still can feel busy for a few citizens (Tess left two jobs by day 96)

## F. Recommended next milestone

Still **not romance**. Options, evidence-based:

1. **Freeze + more human playtests** in the live UI (`D`/`Y`/`T`/`F`) before any systems work
2. If one small systems step: **place / neighbourhood loyalty** (moves already create readable drift)
3. Optional tiny hygiene: hide work colocations until >0 and ≠ coworker, or show “often at work together” instead of raw counts

## Tests

**60 passed** (`pytest -q`)
