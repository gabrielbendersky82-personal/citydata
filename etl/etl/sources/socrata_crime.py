"""Crime ingestion from a city Socrata portal (config-driven adapter).

Pulls point incidents for the rolling window, stores them in staging, then
aggregates directly into neighborhood polygons as per-1k-residents/yr rates.
Requires neighborhood populations (i.e. a block-weighted crosswalk) — refuses
to publish misleading rates without them.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import requests

from etl import db
from etl.config import load_city
from etl.fetch import UA

PAGE = 50_000


def category_lookup(cmap: dict[str, list[str]]) -> dict[str, str]:
    return {v.upper(): bucket for bucket, values in cmap.items() for v in values}


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    crime = cfg["crime"]
    city_id = cfg["city"]["id"]
    fields = crime["fields"]
    lookup = category_lookup(crime["category_map"])
    window_years = int(crime.get("window_years", 3))
    since = (datetime.now(timezone.utc) - timedelta(days=365 * window_years)).strftime(
        "%Y-%m-%dT00:00:00"
    )

    headers = {"User-Agent": UA}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token

    base = f"https://{crime['portal']}/resource/{crime['dataset_id']}.json"
    select = ",".join([fields["row_id"], fields["timestamp"], fields["lat"], fields["lon"], fields["category"]])

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "socrata_crime", f"{city}_{since[:10]}_w{window_years}y")
        offset, total, unmapped = 0, 0, set()
        while True:
            params = {
                "$select": select,
                "$where": f"{fields['timestamp']} >= '{since}'",
                "$order": fields["row_id"],
                "$limit": PAGE,
                "$offset": offset,
            }
            r = requests.get(base, params=params, headers=headers, timeout=180)
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            rows = []
            for rec in batch:
                lat, lon = rec.get(fields["lat"]), rec.get(fields["lon"])
                if not lat or not lon:
                    continue
                src_cat = str(rec.get(fields["category"], "")).upper()
                bucket = lookup.get(src_cat)
                if bucket is None:
                    unmapped.add(src_cat)
                    bucket = "qol"
                rows.append(
                    (
                        city_id,
                        str(rec[fields["row_id"]]),
                        rec[fields["timestamp"]],
                        bucket,
                        src_cat,
                        f"SRID=4326;POINT({float(lon)} {float(lat)})",
                        vid,
                    )
                )
            total += db.upsert_rows(
                c,
                "staging.crime_incidents",
                ["city_id", "source_row_id", "occurred_at", "category", "source_category", "geom", "dataset_version_id"],
                rows,
                ["city_id", "source_row_id"],
            )
            c.commit()
            print(f"  crime page offset={offset} -> total {total}")
            offset += PAGE
            if len(batch) < PAGE:
                break
        if unmapped:
            print(f"WARN: unmapped categories bucketed as qol: {sorted(unmapped)[:20]}")

        # assign neighborhoods spatially
        c.execute(
            """
            update staging.crime_incidents i set neighborhood_id = n.id
            from neighborhoods n
            where i.city_id = %s and n.city_id = %s and i.neighborhood_id is null
              and i.geom is not null and ST_Contains(n.geom, i.geom)
            """,
            (city_id, city_id),
        )

        # per-capita rates need real populations
        no_pop = c.execute(
            """
            select count(*) from neighborhoods n where n.city_id = %s and not exists (
              select 1 from tract_neighborhood_xwalk x join tracts t on t.geoid = x.tract_geoid
              where x.neighborhood_id = n.id and t.pop_2020 is not null)
            """,
            (city_id,),
        ).fetchone()[0]
        if no_pop:
            print(f"ERROR: {no_pop} neighborhoods lack population (crosswalk fallback mode); "
                  "not publishing per-capita rates. Re-run after block-weighted crosswalk.")
            return 1

        c.execute(
            """
            with pop as (
              select x.neighborhood_id, sum(x.pop_weight * t.pop_2020) as pop
              from tract_neighborhood_xwalk x join tracts t on t.geoid = x.tract_geoid
              group by x.neighborhood_id
            ),
            counts as (
              select neighborhood_id,
                     category || '_crime_rate' as metric_key,
                     count(*)::numeric as n
              from staging.crime_incidents
              where city_id = %(city)s and neighborhood_id is not null
              group by neighborhood_id, category
            )
            insert into neighborhood_metrics (neighborhood_id, metric_key, value, coverage, dataset_version_id)
            select p.neighborhood_id,
                   mk.metric_key,
                   coalesce(cn.n, 0) / %(years)s / nullif(p.pop, 0) * 1000,
                   1.0, %(vid)s
            from pop p
            cross join (values ('violent_crime_rate'), ('property_crime_rate'), ('qol_crime_rate')) mk(metric_key)
            left join counts cn on cn.neighborhood_id = p.neighborhood_id and cn.metric_key = mk.metric_key
            where p.pop > 0
            on conflict (neighborhood_id, metric_key, dataset_version_id)
            do update set value = excluded.value, coverage = excluded.coverage
            """,
            {"city": city_id, "years": window_years, "vid": vid},
        )
        db.finish_dataset_version(c, vid, total)
        c.commit()
        print(f"crime: {total} incidents ingested, rates published")
    return 0
