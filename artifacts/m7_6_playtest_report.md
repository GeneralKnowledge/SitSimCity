# SitSimCity M7.6 Playtest Report — Live Follow

## A. What changed (UI only)

- **Compact follow card** while following (`F` / `O` / `I`) — Now / today / circumstances / short social; traits dump hidden
- **Soft work-colocation prose** — “Often at work together” instead of raw hundreds; `verbose_work=True` keeps diagnostics
- **`O` random citizen** — pick + follow, inhabit-first (timeline off)
- **Soft day-roll cue** — brief centered “— Day N —” when the calendar advances
- Slight zoom-in while following

## B. Deliberately not changed

M5.5 friendship math, M6 circumstance rates, schedules, visit mechanics, cadence caps.

## C. Agent-run follow analysis (no human at keyboard)

Protocol: `scripts/live_follow_analysis.py --protocol` — compact inhabit snapshots at ~⅓ / ⅔ / end of each sit, seeds 7 / 1 / 13, random + quiet, 30–60 days. Plus live pygame GUI verification (RecordScreen + computer use).

| seed | days | role | name | compact | inspect | close | cooled | durable |
| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 7 | 30 | random | Tess Jones | 14 | 26 | 4 | 0 | 0 |
| 7 | 30 | quiet* | Lara Green | 14 | 27 | 4 | 0 | 2 |
| 7 | 60 | random | Tess Jones | 12 | 19 | 0 | 5 | 4 |
| 7 | 60 | quiet* | Lara Green | 15 | 31 | 8 | 3 | 3 |
| 1 | 60 | random | Clara Reed | 15 | 29 | 5 | 1 | 4 |
| 1 | 60 | quiet | Leo Murphy | 10 | 16 | 0 | 0 | 8 |
| 13 | 60 | random | Ben Hill | 10 | 15 | 0 | 0 | 2 |
| 13 | 60 | quiet* | Bob Wright | 15 | 30 | 2 | 1 | 1 |

\* Quiet pick is at day 1 (zero close then); some later grow café circles — expected.

### Compact card checks (all runs)

- Traits dump: **absent** on compact, **present** on full inspect
- Raw `Work colocations:`: **absent** on both default surfaces
- Soft coworker prose appears when relevant (e.g. Bob Wright: Origin Work + “Often at work together”)

### Sketches (inhabit reading)

1. **Tess Jones (seed 7, 60d)** — Café circle forms then cools; illness/overwork/job churn enters the compact “Recent events” without spreadsheet noise. Readable arc in ~12 lines.
2. **Leo Murphy (seed 1, quiet)** — Job change, overwork, two illnesses; zero close friends. Compact card stays short; ordinary life preserved.
3. **Ben Hill (seed 13)** — One illness, café acquaintances, straight-home days. Calm.
4. **Bob Wright (seed 13)** — Work-origin bond with Kate Harris; later move Mill→Harbor. Soft work line, no raw colocation dump.

### Live GUI verification

Recorded session: `/opt/cursor/artifacts/m76-live-follow-ui.mp4`

| Feature | Result |
| --- | --- |
| `O` random → compact FOLLOW | Pass |
| Day cue on `D` / `Y` | Pass |
| `T` expand / collapse | Pass |
| Click inspect shows Traits | Pass |
| `F` returns compact card | Pass |
| `I` interesting follow | Pass |

Screenshots under `/opt/cursor/artifacts/screenshots/m76-*.webp`.

## D. Verdict: inhabit vs inspect

**Yes — leaning Yes for inhabit comfort; Yes for inspect still available.**

Sitting with someone via `O`/`F` now reads as watching a life (Now / Today / Close / Recent events) rather than opening a CRM. Expanding with `T`/`J` or clearing follow restores the fuller inspect surface. Work-colocation hundreds no longer compete with social meaning on the default card.

Remaining soft edges (not blockers):

- Quiet-at-start picks can become social later (selection timing, not UI)
- Compact Home/Work lines needed a wrap fix after first GUI pass (shipped)
- “Became close” clusters still appear in recent events up to cadence caps (M7.5 territory)

## E. Recommended next

Freeze M1–M7.6 as substrate. Prefer **game-facing polish / more human sits** over a new sim system. If one systems step later: place / neighbourhood loyalty (moves already create readable drift). Still **not romance**.

## Tests

**65 passed** (`pytest -q`) after M7.6 UI + live-follow tests.
