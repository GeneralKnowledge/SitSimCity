# SitSimCity

A tiny 2D top-down **audience simulator**: watch a seeded town of ~80 citizens live ordinary days.

Current scope: Milestones 1–9 — procedural town, commuting, mundane daily life, M5.5 relationship memory, M6 circumstances/life changes, M7 observer polish, M7.5 cadence hygiene, M7.6 live-follow comfort, M8 town pulse (denser buildings/NPCs, day/evening shifts), and M9 chronicle polish (DF-flavored life/bond prose, demoted CRM metrics, soft inhabit UI).

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
python main.py --seed 7 --citizens 80
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

- Morning rush (day shift) and evening rush (day leavers + evening arrivals)
- Quieter mid-day streets that are not empty — lunch, micro-errands, evening-shift pre-work outings
- Day vs evening shifts on the inspector (`Shift · day` / `evening`)
- After-work pub visits, shopping, or visits to another home (day shift)
- Different citizens developing different habits
- Inspect: close companions and cooled bonds in chronicle prose (not friendship scores); work acquaintances
- Circumstances: illness, job loss/change, overwork, moving home — written as small-town notes
- Life / bond timelines with relative days for recent events; accurate origin (work vs amenity)
- Following one person (`F` / `O`): soft camera, name tag, inhabit status bar; `T` expands timeline under the compact card

## Headless tests

```bash
pytest -q
```

## Playtest / observer diagnostics

```bash
python scripts/playtest_m7.py --mode all
python scripts/follow_playtest.py --protocol   # random + quiet follows
python scripts/live_follow_analysis.py --protocol  # M7.6 compact inhabit snapshots
python scripts/town_pulse_playtest.py              # M8 density / shifts / mid-day pulse
python scripts/chronicle_playtest.py --seed 7      # M9 chronicle voice / CRM demotion
python scripts/playtest_m7.py --mode metrics
```

## Layout

```text
sim/          # pure simulation (no pygame)
  generate/   # city, population, tendencies
  systems/    # schedule, movement, social, circumstances, observe, chronicle
app/          # pygame camera, render, UI loop
scripts/      # playtest / validation helpers
tests/        # headless simulation tests
main.py       # entry point
```

The simulation can run without the renderer. That separation is intentional for later systems.
