# data/

`example.sql` is a sample of the Guelph Transit GTFS feed (service 4 Jan to
2 May 2026, City of Guelph, Open Government Licence - City of Guelph v2.0):
routes 1, 2 and 99, trips starting 07:00-08:59. 3 routes, 95 trips, 104 stops,
2356 stop times. `make_sample.py` makes it from the unzipped feed:

    py data\make_sample.py C:\path\to\gtfs-raw

`gtfs-validator-report.html` is the official GTFS validator's report on the
full feed (MobilityData, version 8.0.0).