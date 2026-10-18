import csv
import json
from pathlib import Path

import numpy as np
import torch
from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
GTFS = Namespace("http://vocab.gtfs.org/terms#")
GEO = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")
MATCH_THRESHOLD = 0.8

g = Graph().parse(ROOT / "build" / "graph.nt", format="nt")
stops = sorted(g.subjects(RDF.type, GTFS.Stop), key=str)
index = {s: i for i, s in enumerate(stops)}

trips = {}
for st in g.subjects(RDF.type, GTFS.StopTime):
    trip = g.value(st, GTFS.trip)
    trips.setdefault(trip, []).append((int(g.value(st, GTFS.stopSequence)), g.value(st, GTFS.stop)))

n = len(stops)
trip_count = np.zeros(n)
routes_at = [set() for _ in range(n)]
starts_or_ends = np.zeros(n)
edges = set()
for trip, seq in trips.items():
    seq.sort()
    route = g.value(trip, GTFS.route)
    for _, s in seq:
        trip_count[index[s]] += 1
        routes_at[index[s]].add(route)
    starts_or_ends[index[seq[0][1]]] = 1
    starts_or_ends[index[seq[-1][1]]] = 1
    for (_, a), (_, b) in zip(seq, seq[1:]):
        if a != b:
            edges.add((index[a], index[b]))

lat = np.array([float(g.value(s, GEO.lat)) for s in stops])
lon = np.array([float(g.value(s, GEO.long)) for s in stops])
x = np.column_stack([np.log1p(trip_count), [len(r) for r in routes_at], starts_or_ends])

osm = {str(e["id"]): e.get("tags", {}) for e in
       json.loads((ROOT / "mapping" / "er" / "osm-bus-stops.json").read_text(encoding="utf-8"))["elements"]}
shelter = np.full(n, -1)
by_id = {str(s).rsplit("/", 1)[-1]: i for s, i in index.items()}
for row in csv.DictReader(open(ROOT / "mapping" / "er" / "matches.csv", encoding="utf-8")):
    if row["score"] and float(row["score"]) >= MATCH_THRESHOLD:
        tag = osm[row["osm_node"]].get("shelter")
        if tag in ("yes", "no"):
            shelter[by_id[row["gtfs_stop"]]] = 1 if tag == "yes" else 0

torch.save({
    "x": torch.tensor(x, dtype=torch.float),
    "feature_names": ["log trips", "routes", "first or last stop"],
    "lat": torch.tensor(lat), "lon": torch.tensor(lon),
    "edge_index": torch.tensor(sorted(edges), dtype=torch.long).T.contiguous(),
    "shelter": torch.tensor(shelter),
    "stop_iri": [str(s) for s in stops],
}, ROOT / "model" / "graph.pt")

labelled = shelter >= 0
print(f"read build/graph.nt: {len(g):,} triples")
print(f"nodes: {n} stops; edges: {len(edges)} 'next stop' links from {len(trips)} trips")
print(f"label: shelter known for {labelled.sum()} stops ({(shelter == 1).sum()} yes, {(shelter == 0).sum()} no), "
      f"from OpenStreetMap through mapping/er/matches.csv; not in the features")
print("written: model/graph.pt")