# SitSimCity M8 — Town Pulse

## What changed

- Default town: **80** citizens, **32** homes, **10** workplaces, **2** cafe/shop/pub each
- `Person.shift`: **day** (~75%) / **evening** (~25%)
- Day: leave ~7:15–8:15, leave work ~16:45–17:40; lunch + minority micro-errands
- Evening: leave ~13:30–14:30, leave work ~21:30–22:15; pre-work amenity outings mid-morning
- Unemployed daytime outing chance 0.35 → 0.45
- Inspector shows `Shift · day|evening`
- **No** M5.5 friendship / M6 circumstance retunes

## Pulse check (seeds 7 / 1 / 13)

| Time | Pattern |
| --- | --- |
| ~08:00 | Morning rush — heavy TRAVEL among day shift |
| ~10:30 | Quieter: day@work ~57, street/amenity ~7–11 |
| ~12:30 | Lunch band — cafe/shop/travel rise |
| ~17:15 | Evening rush — day leavers + evening@work |
| ~23:00 | Nearly all SLEEP |

## Tests

`pytest -q` → **70 passed**
