"""Run the HermiT reasoner on our ontology and save what it found.

    python ontology/run_reasoner.py

Run from the repository root, in the course's demos/.venv (it has rdflib and
owlready2) with Java installed. It loads ontology/ontology.ttl together with
ontology/reasoner-check.ttl (a few real things from our sample), runs
HermiT, prints the impossible classes (there should be none) and what the
reasoner inferred, and writes the same to ontology/reasoner-run.txt with
the date.
"""
import datetime
import tempfile
from pathlib import Path

import owlready2
from rdflib import Graph

HERE = Path(__file__).resolve().parent
FILES = [HERE / "ontology.ttl", HERE / "reasoner-check.ttl"]

# 1. merge the two files and give them to owlready2 (it reads N-Triples)
g = Graph()
for f in FILES:
    g.parse(f)
tmp = Path(tempfile.mkdtemp()) / "merged.nt"
g.serialize(tmp, format="nt", encoding="utf-8")
world = owlready2.World()
with open(tmp, "rb") as f:
    onto = world.get_ontology("https://ul.edu.lb/kr/transit").load(fileobj=f, format="ntriples")

# 2. run HermiT
with onto:
    owlready2.sync_reasoner_hermit(world, infer_property_values=False, debug=0)

# 3. report
impossible = [c.name for c in world.inconsistent_classes()]
lines = [f"Reasoner run, {datetime.date.today()}: HermiT (owlready2 {owlready2.VERSION}) on "
         + " + ".join(f.name for f in FILES),
         f"Triples loaded: {len(g)}",
         "Impossible classes (equivalent to owl:Nothing): " + (", ".join(impossible) or "none"),
         "Inferred types of the check individuals:"]
for ind in sorted(world.individuals(), key=lambda i: i.iri):
    if "/kr/id/" in ind.iri:
        types = sorted(c.name for c in ind.is_a if hasattr(c, "name"))
        lines.append(f"  {ind.iri.rsplit('/', 1)[-1]}: {', '.join(types)}")
text = "\n".join(lines)
print(text)
(HERE / "reasoner-run.txt").write_text(text + "\n", encoding="utf-8")