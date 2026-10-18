# Constraint inventory and triage

The rules our data must follow, where we found each one, and why each is a
SHACL shape and not an OWL axiom. Checked on our sample on 2026-10-19:
0 Violation, 2356 Warning.

| # | Rule | Evidence | Severity | Why SHACL, not OWL | Result |
|---|---|---|---|---|---|
| C1 | A trip has exactly one route | GTFS spec | Violation | OWL would assume a missing route exists somewhere; we need an error | passes |
| C2 | A trip has exactly one service | GTFS spec | Violation | same as C1 | passes |
| C3-C5 | A stop time has one trip, one stop, one position | GTFS spec | Violation | counting what is present needs a closed world | passes |
| C6 | Times look like H:MM:SS | GTFS spec | Violation | OWL has no text patterns | passes |
| C7 | Times use two digits, HH:MM:SS | GTFS spec; Guelph writes 7:01:06 | Warning | OWL has no text patterns | 2356 warnings |
| C8 | Distance traveled goes up along a trip | official validator: 96 errors in the full feed | Violation | compares two values; OWL cannot compare numbers between things | passes |
| C9 | A stop has one name and a valid latitude and longitude | common sense | Violation | value ranges are checks on data, not new knowledge | passes |
| C10 | Every stop is used by a trip | official validator: 5 unused stops in the full feed | Warning | "no trip stops here" is about missing data, closed world | passes |
| C11 | A service runs on at least one day | full feed: service 7 runs on no day | Violation | "no day is true" is about missing data, closed world | passes |

The reverse case: "a trip with wheelchair access is an accessible trip" adds
knowledge, so it is an OWL axiom (tr:AccessibleTrip in ontology.ttl), not a shape.

## Triage of failures on our real data

- C7, 2356 warnings: data defect in the source (one-digit hours). Harmless for
  our questions, so we keep the data and report it as a Warning.
- C8, C10, C11: real defects in the full feed. Our sample does not contain them
  because we kept 3 routes and morning trips only.
- Stop wheelchair access: empty or 0 for every stop in our sample. We could not
  write a rule for it; reported in the technical report.

## The gate blocks bad data

Locally: stop 103 latitude set to 200. Result: 1 Violation (C9), pipeline
stopped with code 1, Fuseki not loaded (report/red-run.png).
In CI: see report/red-run-ci.png.