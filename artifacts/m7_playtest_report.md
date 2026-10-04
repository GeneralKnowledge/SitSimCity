# SitSimCity M7 Playtest Report

## A. Test results

- **Tests:** 52 passed (`pytest -q`)
- **Protocol:** `scripts/playtest_m7.py --mode all`
- **Artifacts:** `m7_playtest.txt`, `m7_metrics.json`

### Seed 7 quantitative

| Day | Close | Mean deg | Max deg | Zero-close | ≥20 | ≥50 | =100 | Reunions | Avg life events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 30 | 48 | 1.92 | 13 | 27 | 49 | 0 | 0 | 5 | 4.2 |
| 100 | 100 | 4.00 | 12 | 10 | 115 | 2 | 0 | 136 | 17.8 |
| 200 | 126 | 5.04 | 16 | 10 | 136 | 24 | 0 | 277 | 21.8 |

### Multi-seed 100d

| Seed | Close | Mean deg | Zero-close | =100 | Avg life | Reunions |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 69 | 2.76 | 11 | 0 | 15.0 | 94 |
| 7 | 100 | 4.00 | 10 | 0 | 17.8 | 136 |
| 13 | 37 | 1.48 | 22 | 0 | 12.8 | 70 |
| 42 | 47 | 1.88 | 18 | 0 | 13.0 | 72 |
| 100 | 86 | 3.44 | 11 | 0 | 14.3 | 63 |

No stuck expired circumstances. Move/job counts remain sparse (most citizens 0–1).

## B. Citizen stories (seed 7)

1. **Gina Brown** — Moved Pine Court → Westside; café clique with Eve/Xander/Lara; work-origin closeness with coworker Lara that socialises at pub/café.
2. **Eve Green** — Baker at Brick & Board; café-native friendships; illness interruption + reunion with Gina; by day 200 holds a durable work→pub bond with Vince (f=60).
3. **Nora Williams** — Work-origin pub friendship with Yvonne Cook; many cooled secondary bonds; socially dense without many job/move events.
4. **Yvonne Cook** — One move; work→pub closeness; at 200d still café/pub-active with Rosa/Nora Jones.
5. **Ben Taylor (quiet)** — Zero close friends at 100d; job change Northwind→Harbor; occasional amenity meetings only — uneventful life present.

## C. Relationship stories

| Pattern | Example | Arc |
| --- | --- | --- |
| Formation / amenity | Eve Green ↔ Gina Brown | Origin Café → close at pub → cool → reunite at café |
| Work→social | Lara Green ↔ Gina Brown | Origin Work → close at pub → frequent café |
| Cooling + job | Kate Adams ↔ Felix Morgan | Shop origin → close → illness → cool → job-change notes → partial reunions |
| Pub origin | Felix Morgan ↔ Vince Brown | First pub → close at shop → cool/reunite loop |
| Work origin + place drift | Nora Williams ↔ Yvonne Cook | First work → close at pub; still coworkers |
| Move pressure | Leo Moore ↔ Nora Williams | Café origin → move/job notes → cooling/reunion |

Origin labels now match first meeting context (not meeting-count majority).

## D. Problems discovered

### Confirmed bugs (fixed in M7)
- “Met through work” inferred from work-meeting majority → fixed via `origin_context`
- Duplicate “became close” lines in citizen timeline → fixed

### Questionable behaviour
- **Reunion volume** still high in life logs (100d≈136, 200d≈277 on seed 7); timelines of busy citizens read as reunion lists
- **Coworker `times_met` inflation** (hundreds–thousands) from work colocation; social meeting counts are the meaningful figure
- **≥50 friendships** grow by day 200 (0→24 on seed 7) while =100 stays 0 — slow long-run creep, not epidemic
- Eventful ranking was reunion-dominated before reweighting toward job/move/illness

### Balance concerns (recorded, not changed)
- Circumstances may thin early close edges vs M5.5; long runs re-densify via amenity habits
- Café/shop dominate social closeness; visits remain rare

### Merely interesting
- Uneventful citizens exist alongside dense café regulars
- Work-origin pairs often become close at amenities, not at work (work grants no friendship)

## E. Recommendation for M8

**Not romance yet.** Evidence points to **relationship memory hygiene + meeting semantics** before new drama systems:

1. Separate *work presence* from *social meetings* in observer totals / optional meeting caps
2. Further throttle reunion life-events (or ring-buffer by kind)
3. Only then consider a small new system — strongest candidate from playtest: **stronger place loyalty / neighbourhood social gravity** (moves already create readable drift; lean into that)

Romance would amplify noisy reunion/cooling loops before those loops are pleasant to read.
