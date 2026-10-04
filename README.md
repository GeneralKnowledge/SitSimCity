# SitSimCity

A tiny 2D top-down **audience simulator**: watch a seeded town of ~50 citizens live ordinary days.

Current scope: Milestones 1–5.5 — procedural town, commuting, mundane daily life (cafe/shop/pub/visits), persistent relationship memory with diminishing-return friendship (wide familiarity, scarce closeness, cooling/reactivation), and continuous follow mode.

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
- Inspect: close companions (with meet counts / peak / last seen) vs work acquaintances vs cooled bonds
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

The simulation can run without the renderer. That separation is intentional for later systems.
