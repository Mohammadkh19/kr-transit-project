# Guelph Transit knowledge graph

Mohammad Khashab's project for Knowledge Representation (Lebanese University,
MSc). A knowledge graph of a Guelph Transit GTFS sample (routes 1, 2 and 99,
trips starting 07:00 to 08:59), with an ontology, SHACL shapes, an R2RML
mapping, entity resolution with OpenStreetMap, two graph models, and an access
layer that answers questions in English. The full write-up is in
`report/REPORT.md`.

The labs and slides are at
https://ahmabboud.github.io/course_knowledge_representation/.

## Run it

```sh
cp .env.example .env        # then put your Gemini key after GOOGLE_API_KEY=
docker compose up --build
```

On Windows, install Docker Desktop and use PowerShell:
`Copy-Item .env.example .env`, then the same `docker compose up --build`.

**Expect:** the pipeline prints five steps and `done` (on the Guelph sample:
17,319 triples, 0 Violation, 2,356 Warning, 147 VoID triples), then the access
layer serves on http://127.0.0.1:8000. Try
`http://127.0.0.1:8000/?question=How%20many%20trips%20run%20on%20Sunday%3F&dataset=https://ul.edu.lb/kr/guelph/`
(it answers) and
`http://127.0.0.1:8000/?question=How%20much%20does%20a%20bus%20ticket%20cost%3F&dataset=https://ul.edu.lb/kr/guelph/`
(it refuses: the graph has no fares).
The endpoint is at http://127.0.0.1:3030 (dataset `kr`).

Without internet, add `LLM_MODE=replay` to `.env`: the access layer then
answers the test questions from `access-layer/llm-cache.json`.

Without Docker, the pipeline also runs on its own (Python 3.12, from the
repository root): `pip install -r pipeline/requirements-pipeline.txt`, then
`pip install --no-deps morph-kgc==2.10.0`, then `python pipeline/run.py --no-load`.

## What goes where

| Folder | Layer | What is in it |
|---|---|---|
| `data/` | the source | `example.sql`, the Guelph sample, made by `make_sample.py`; the official GTFS validator report |
| `ontology/` | the ontology | `ontology.ttl` (reuses Linked GTFS, OWL 2 EL, version 1.0.1), the competency questions, the reasoner run |
| `shapes/` | the SHACL shapes | `shapes.ttl` (C1 to C11) and `triage.md` |
| `mapping/` | the R2RML mapping | `mapping.ttl`, and `er/`: matching our stops to OpenStreetMap |
| `pipeline/` | map, gate, describe, load | the five steps |
| `model/` | the graph models | shelter prediction and next-stop prediction, with baselines and results |
| `access-layer/` | questions in English | prompt rules, examples, the 16 test questions, the recorded answers |
| `report/` | the technical report | `REPORT.md`, the scores before and after, the red runs |
| `.github/workflows/` | the SHACL gate in CI | runs on every push |

## How the stack fits together

```text
data (Guelph sample) --> pipeline: map (mapping/) --> SHACL gate (shapes/ + ontology/)
                                                          |
                                      Violation: stop     |  pass
                                                          v
                                     VoID (build/void.ttl) + load --> Fuseki (kr)
                                                                          ^
                     a question in English --> access layer (Gemini) -----+
```

The endpoint is only ever loaded with data that passes the gate. Set the
latitude of one stop in `data/example.sql` to 200 and run the pipeline again:
it stops at step 3 and says why (`report/red-run.png`).

## Results

- Graph: 17,319 triples from 3 routes, 95 trips, 104 stops.
- Shapes: 0 Violation, 2,356 Warning (one-digit hours, C7).
- Entity resolution with OpenStreetMap: precision 0.986, recall 0.854 at
  threshold 0.8.
- Shelter prediction: no model beats the majority baseline (0.706 accuracy).
  Next-stop prediction: GraphSAGE MRR 0.184 against 0.159 for nearest stop,
  within the spread.
- Access layer: 0.889 on 16 test questions (0.806 before the fix).

## Licences

- Guelph Transit GTFS: Open Government Licence – City of Guelph v2.0.
- Linked GTFS vocabulary: CC BY 3.0.
- OpenStreetMap data: ODbL.