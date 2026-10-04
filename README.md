# SitSimCity

A tiny 2D top-down **audience simulator**: watch a seeded town of ~50 citizens commute through ordinary days.

Milestones 1–3 only: procedural town, population, visible commuting, clock controls, click-to-inspect. No romance, crime, or other drama systems yet.

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
| `F` | Focus camera on selected citizen |
| Middle/right drag | Pan |
| Mouse wheel | Zoom |
| `N` | Generate next seed |
| `R` | Regenerate current seed |
| Esc | Clear selection |

The player is an observer only. There are no orders, objectives, or win conditions.

## Headless tests

```bash
pytest -q
```

Tests cover town shape, morning/evening commute, and seed determinism without opening a window.

## Layout

```text
sim/          # pure simulation (no pygame)
  generate/   # city + population
  systems/    # schedule + movement
app/          # pygame camera, render, UI loop
tests/        # headless simulation tests
main.py       # entry point
```

The simulation can run without the renderer. That separation is intentional for later systems.
