# Competency questions

The questions our system must answer. Every class we add to Linked GTFS
answers one of them (`tr:answersCQ` on the class). Checked against our
sample (data/gtfs-sample.sql).

| # | Competency question | Answered with |
|---|---|---|
| CQ1 | Which stops does route 99 serve, in order? | gtfs:Route, gtfs:Trip, gtfs:StopTime, gtfs:Stop, gtfs:stopSequence |
| CQ2 | Which stops are served by more than one route (places to change bus)? | SPARQL over gtfs:stop, gtfs:trip, gtfs:route (18 stops in the sample) |
| CQ3 | Which routes run on Sunday? | **tr:SundayService** (only route 99 in the sample) |
| CQ4 | Which trips are wheelchair accessible, and on which routes? | **tr:AccessibleTrip** (79 of 95 trips in the sample) |
| CQ5 | When does the first trip of each route leave on a Saturday? | gtfs:CalendarRule, gtfs:saturday, gtfs:departureTime |

## A question we could not answer

"Which stops are wheelchair accessible?" In our sample, wheelchair_boarding
is empty for 72 stops and 0 ("no information") for 32. No stop says yes or
no, so we answer accessibility for trips (CQ4) instead.

## Reuse decisions

We reuse Linked GTFS (http://vocab.gtfs.org/terms#, CC BY 3.0, Open
Transport contributors) by using its IRIs, but we do not owl:import its file:

1. `gtfs:route` has two ranges, gtfs:Route and gtfs:FareRule. In RDFS two
   ranges mean both, so every route of a trip would become a fare rule.
2. `gtfs:shortName` has two domains, gtfs:Trip and gtfs:Route, so every route
   with a short name would become a trip too.
3. `gtfs:wheelchairAccessible` has domains gtfs:Stop and gtfs:Station, so an
   accessible trip would become a stop and a station.
4. HermiT cannot load the file at all: `gtfs:arrivalTime` uses xsd:duration,
   which is not in the OWL 2 datatype map.

So `ontology.ttl` declares only the Linked GTFS terms we use, with the
domains and ranges that are true for our data.