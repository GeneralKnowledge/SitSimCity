# SitSimCity

A tiny 2D top-down **audience simulator**: watch a seeded town of ~50 citizens live ordinary days.

Current scope: Milestones 1–4 — procedural town, commuting, mundane daily variations (cafe/shop/pub/visits), minimal co-location friendship, and continuous follow mode.

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
| Esc | Clear selection / stop follow |
| Middle/right drag | Pan (cancels follow) |
| Mouse wheel | Zoom |
| `N` | Generate next seed |
| `R` | Regenerate current seed |

The player is an observer only. There are no orders, objectives, or win conditions.

### What to watch for

- Morning commute rush
- Midday cafe/shop trips by some workers
- After-work pub visits, shopping, or visits to another home
- Different citizens developing different habits
- Friendship numbers rising among people who keep meeting
- Following one person through their day (`F`)

## Headless tests

```bash
pytest -q
```

## Layout

```text
sim/          # pure simulation (no pygame)
  generate/   # city, population, tendencies
  systems/    # schedule, movement, social
app/          # pygame camera, render, UI loop
tests/        # headless simulation tests
main.py       # entry point
```
