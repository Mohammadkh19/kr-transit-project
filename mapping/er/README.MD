# Entity resolution: GTFS stops and OpenStreetMap stops

- `osm-bus-stops.json`: OpenStreetMap bus stops around Guelph, downloaded 2026-10-19 (ODbL, © OpenStreetMap contributors).
- `match_stops.py`: the matcher. It uses distance and name only, with blocking at 100 m.
- `matches.csv`: the best OSM stop for each of our 104 GTFS stops.
- `result.txt`: precision and recall.

Labels: OSM `ref` is the stop number on the sign, the same as the GTFS stop code. 82 of our stops have exactly one OSM stop with their code. The matcher never reads `ref`.

| Threshold | Matches | Right | Precision | Recall |
|---|---|---|---|---|
| 0.5 | 74 | 70 | 0.946 | 0.854 |
| 0.8 | 71 | 70 | 0.986 | 0.854 |

We use 0.8: fewer wrong matches, same recall.

Errors: 3 of the 4 wrong matches at 0.5 are the stop on the other side of the road (northbound vs southbound), because the true OSM stop has no name. The 4th is a GO Transit stop at the same corner. The 12 missed stops have no name in OSM.