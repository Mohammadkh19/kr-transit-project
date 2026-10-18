r"""Cut a small sample out of the Guelph Transit GTFS feed and write it as SQL.

    py data\make_sample.py C:\Users\mhmdk\OneDrive\Desktop\gtfs-raw

Keeps 3 routes (1, 2, 99), then only the rows that belong to them:
routes -> trips -> stop_times -> stops, plus agency, calendar, calendar_dates.
Writes data/gtfs-sample.sql. Values are trimmed of spaces (the feed writes
times as " 6:00:00"); nothing else is changed.
"""
import csv
import sys
from pathlib import Path

ROUTES_TO_KEEP = {"1", "2", "99"}          # route_short_name values we keep
RAW = Path(sys.argv[1])                    # the folder with the unzipped feed
OUT = Path(__file__).resolve().parent / "gtfs-sample.sql"


def read(name):
    """One GTFS file as a list of dicts, every value trimmed."""
    with open(RAW / name, encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


# 1. follow the links from the routes we keep down to every row we need
routes = [r for r in read("routes.txt") if r["route_short_name"] in ROUTES_TO_KEEP]
route_ids = {r["route_id"] for r in routes}

trips = [t for t in read("trips.txt") if t["route_id"] in route_ids]
trip_ids = {t["trip_id"] for t in trips}
service_ids = {t["service_id"] for t in trips}

stop_times = [s for s in read("stop_times.txt") if s["trip_id"] in trip_ids]

# keep only the morning rush: trips whose first stop is between 07:00 and 08:59
start_hour = {}
for s in sorted(stop_times, key=lambda s: int(s["stop_sequence"])):
    start_hour.setdefault(s["trip_id"], int(s["departure_time"].split(":")[0]))
trips = [t for t in trips if start_hour.get(t["trip_id"]) in (7, 8)]
trip_ids = {t["trip_id"] for t in trips}
service_ids = {t["service_id"] for t in trips}
stop_times = [s for s in stop_times if s["trip_id"] in trip_ids]

stop_ids = {s["stop_id"] for s in stop_times}

stops = [s for s in read("stops.txt") if s["stop_id"] in stop_ids]
agency = read("agency.txt")
calendar = [c for c in read("calendar.txt") if c["service_id"] in service_ids]
calendar_dates = [c for c in read("calendar_dates.txt") if c["service_id"] in service_ids]

tables = {"agency": agency, "routes": routes, "trips": trips, "stops": stops,
          "stop_times": stop_times, "calendar": calendar, "calendar_dates": calendar_dates}


# 2. write each table as CREATE TABLE + INSERT lines (empty value -> NULL)
def sql_value(v):
    return "NULL" if v == "" else "'" + v.replace("'", "''") + "'"


lines = ["-- A sample of the Guelph Transit GTFS feed (service 2026-01-04 to 2026-05-02),",
         "-- routes " + ", ".join(sorted(ROUTES_TO_KEEP)) + ", made by data/make_sample.py.",
                 "-- routes " + ", ".join(sorted(ROUTES_TO_KEEP)) + ", trips starting 07:00-08:59, made by data/make_sample.py.", ""]
for name, rows in tables.items():
    if not rows:
        print(f"{name:15}      0 rows (skipped: nothing for our routes)")
        continue
    cols = list(rows[0].keys())
    lines.append(f"CREATE TABLE {name} ({', '.join(c + ' TEXT' for c in cols)});")
    for r in rows:
        lines.append(f"INSERT INTO {name} VALUES ({', '.join(sql_value(r[c]) for c in cols)});")
    lines.append("")
    print(f"{name:15} {len(rows):6} rows")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {OUT}")