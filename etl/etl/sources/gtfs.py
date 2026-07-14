"""GTFS static: stop density + weekly departures per km² per neighborhood."""
from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict

from etl import db
from etl.config import load_city
from etl.fetch import download


def weekly_departures(z: zipfile.ZipFile) -> dict[str, int]:
    """Approximate weekly departures per stop from stop_times × calendar."""
    service_days: dict[str, int] = {}
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if "calendar.txt" in z.namelist():
        with z.open("calendar.txt") as f:
            for row in csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")):
                service_days[row["service_id"]] = sum(int(row.get(d, 0) or 0) for d in days)
    trip_service: dict[str, str] = {}
    with z.open("trips.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")):
            trip_service[row["trip_id"]] = row["service_id"]
    per_stop: dict[str, int] = defaultdict(int)
    with z.open("stop_times.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")):
            sid = trip_service.get(row["trip_id"])
            per_stop[row["stop_id"]] += service_days.get(sid, 5)  # default weekday-ish
    return per_stop


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "gtfs", f"{city}_static")
        total = 0
        for agency in cfg["gtfs"]["agencies"]:
            path, _ = download(agency["static_url"], f"gtfs_{agency['name']}")
            with zipfile.ZipFile(path) as z:
                deps = weekly_departures(z)
                rows = []
                with z.open("stops.txt") as f:
                    for row in csv.DictReader(io.TextIOWrapper(f, "utf-8-sig")):
                        lat, lon = row.get("stop_lat"), row.get("stop_lon")
                        if not lat or not lon:
                            continue
                        rows.append(
                            (
                                row["stop_id"],
                                agency["name"],
                                city_id,
                                f"SRID=4326;POINT({float(lon)} {float(lat)})",
                                deps.get(row["stop_id"], 0),
                            )
                        )
            total += db.upsert_rows(
                c, "staging.gtfs_stops",
                ["stop_id", "agency", "city_id", "geom", "weekly_departures"],
                rows, ["agency", "stop_id"],
            )

        c.execute(
            """
            with area as (
              select id, ST_Area(geom::geography) / 1e6 as km2 from neighborhoods where city_id = %(city)s
            ),
            stops as (
              select n.id as nid, count(*) as n_stops, sum(s.weekly_departures) as deps
              from neighborhoods n
              join staging.gtfs_stops s on s.city_id = n.city_id and ST_Contains(n.geom, s.geom)
              where n.city_id = %(city)s
              group by n.id
            )
            insert into neighborhood_metrics (neighborhood_id, metric_key, value, coverage, dataset_version_id)
            select a.id, m.key,
                   case m.key when 'stop_density' then coalesce(s.n_stops, 0) / nullif(a.km2, 0)
                              else coalesce(s.deps, 0) / nullif(a.km2, 0) end,
                   1.0, %(vid)s
            from area a
            cross join (values ('stop_density'), ('weekly_departures')) m(key)
            left join stops s on s.nid = a.id
            on conflict (neighborhood_id, metric_key, dataset_version_id)
            do update set value = excluded.value, coverage = excluded.coverage
            """,
            {"city": city_id, "vid": vid},
        )
        db.finish_dataset_version(c, vid, total)
        c.commit()
        print(f"gtfs: {total} stops, transit metrics published")
    return 0
