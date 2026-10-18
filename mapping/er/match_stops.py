import csv
import difflib
import json
import math
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BLOCK_METRES = 100
THRESHOLDS = (0.5, 0.8)


def metres(a, b):
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def clean(name):
    name = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    return " ".join(w for w in name.split() if w != "platform")


def score(gtfs, osm):
    d = metres((gtfs["lat"], gtfs["lon"]), (osm["lat"], osm["lon"]))
    near = max(0.0, 1 - d / BLOCK_METRES)
    same_name = difflib.SequenceMatcher(None, clean(gtfs["name"]), clean(osm["name"])).ratio() if osm["name"] else 0.0
    return 0.5 * near + 0.5 * same_name, d


con = sqlite3.connect(":memory:")
con.executescript((ROOT / "data" / "example.sql").read_text(encoding="utf-8"))
gtfs = [{"id": i, "code": c, "name": n, "lat": float(la), "lon": float(lo)}
        for i, c, n, la, lo in con.execute("SELECT stop_id, stop_code, stop_name, stop_lat, stop_lon FROM stops")]
osm = [{"id": e["id"], "name": e.get("tags", {}).get("name"), "ref": e.get("tags", {}).get("ref"),
        "lat": e["lat"], "lon": e["lon"]}
       for e in json.loads((HERE / "osm-bus-stops.json").read_text(encoding="utf-8"))["elements"]]

by_ref = {}
for o in osm:
    if o["ref"]:
        by_ref.setdefault(o["ref"], []).append(o["id"])
truth = {g["id"]: by_ref[g["code"]][0] for g in gtfs if len(by_ref.get(g["code"], [])) == 1}

best = {}
pairs = 0
for g in gtfs:
    for o in osm:
        s, d = score(g, o)
        if d < BLOCK_METRES:
            pairs += 1
            if g["id"] not in best or s > best[g["id"]][0]:
                best[g["id"]] = (s, o, d)

with open(HERE / "matches.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["gtfs_stop", "gtfs_name", "osm_node", "osm_name", "metres", "score", "true_osm_node"])
    for g in gtfs:
        s, o, d = best.get(g["id"], (0, {"id": "", "name": ""}, ""))
        w.writerow([g["id"], g["name"], o["id"], o["name"], round(d) if d != "" else "", round(s, 3), truth.get(g["id"], "")])

lines = [f"{len(gtfs)} GTFS stops, {len(osm)} OSM stops: {len(gtfs) * len(osm):,} possible pairs, "
         f"{pairs} within {BLOCK_METRES} m",
         f"labelled (OSM ref = GTFS stop code, on exactly one OSM stop): {len(truth)} GTFS stops"]
for th in THRESHOLDS:
    found = {gid: o["id"] for gid, (s, o, d) in best.items() if s >= th and gid in truth}
    right = sum(1 for gid, oid in found.items() if truth[gid] == oid)
    precision = right / max(len(found), 1)
    recall = right / len(truth)
    lines.append(f"threshold {th}: {len(found)} matches, {right} right. "
                 f"precision {precision:.3f}, recall {recall:.3f}")
    for gid, oid in found.items():
        if truth[gid] != oid:
            g = next(x for x in gtfs if x["id"] == gid)
            lines.append(f"  wrong match  GTFS {gid} {g['name']!r} -> OSM {oid} (truth: OSM {truth[gid]})")
text = "\n".join(lines)
print(text)
(HERE / "result.txt").write_text(text + "\n", encoding="utf-8")