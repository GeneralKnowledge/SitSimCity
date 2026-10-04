# SitSimCity

A tiny 2D top-down **audience simulator**: watch a seeded town of ~50 citizens live ordinary days.

Current scope: Milestones 1–7.6 — procedural town, commuting, mundane daily life, M5.5 relationship memory, M6 circumstances/life changes, M7 observer polish, M7.5 cadence hygiene, and M7.6 live-follow comfort (compact follow card, soft work-colocation prose, random pick, day-roll cue).

Not included yet: romance, crime, murder, marriage, births, economy, quests.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
python main.py --seed 7
python main.py --seed 7 --citizens 50
```

### Controls

| Input | Action |
| --- | --- |
| Space | Pause / resume |
| `[` `]` or `1`–`7` | Simulation speed |
| Click citizen | Inspect |
| `F` | Toggle continuous follow on selected citizen |
| `O` | Pick a random citizen and follow (compact inhabit card) |
| Esc | Clear selection / stop follow |
| Middle/right drag | Pan (cancels follow) |
| Mouse wheel | Zoom |
| `N` | Generate next seed |
| `R` | Regenerate current seed |
| `D` | Advance 1 day (pauses; soft day-roll cue) |
| `Y` | Advance 5 days (pauses; soft day-roll cue) |
| `T` | Toggle life timeline in inspector (expands follow card) |
| `J` | Cycle focused bond (close / cooled) |
| `I` | Jump to next interesting citizen + follow |
| `W` | Toggle world diagnostic report |

The player is an observer only. There are no orders, objectives, or win conditions.

### What to watch for

- Morning commute rush
- Midday cafe/shop trips by some workers
- After-work pub visits, shopping, or visits to another home
- Different citizens developing different habits
- Inspect: close companions (with meet counts / peak / last seen) vs work acquaintances vs cooled bonds
- Circumstances: illness, job loss/change, overwork, moving home — and how they thin or shift meetings
- Life / bond timelines and accurate relationship origin (work vs amenity)
- Following one person through their day (`F` / `O`); compact inhabit card while following; day-step with `D` / `Y`

## Headless tests

```bash
pytest -q
```

## Playtest / observer diagnostics

```bash
python scripts/playtest_m7.py --mode all
python scripts/follow_playtest.py --protocol   # random + quiet follows
python scripts/playtest_m7.py --mode metrics
```

## Layout

```text
sim/          # pure simulation (no pygame)
  generate/   # city, population, tendencies
  systems/    # schedule, movement, social, circumstances, observe
app/          # pygame camera, render, UI loop
scripts/      # playtest / validation helpers
tests/        # headless simulation tests
main.py       # entry point
```

The simulation can run without the renderer. That separation is intentional for later systems.
