"""Walkability metrics computed from staged POIs.

800m ≈ a 10-minute walk from the neighborhood's population centroid.
Straight-line buffers, not network distance — labeled as such in the UI.
"""
from __future__ import annotations

from etl import db
from etl.config import load_city

ESSENTIALS = ("grocery", "pharmacy", "health")


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "walkability", f"{city}_pois_800m")
        c.execute(
            """
            with hood as (
              select id, centroid_pop, geom, ST_Area(geom::geography) / 1e6 as km2
              from neighborhoods where city_id = %(city)s
            ),
            m as (
              select h.id as nid,
                (select count(*) from staging.pois p
                  where p.city_id = %(city)s and p.category = any(%(essentials)s)
                    and ST_DWithin(h.centroid_pop::geography, p.geom::geography, 800)) as essentials,
                (select count(*) from staging.pois p
                  where p.city_id = %(city)s and p.category = 'food_drink'
                    and ST_DWithin(h.centroid_pop::geography, p.geom::geography, 800)) as food,
                (select count(*) from staging.pois p
                  where p.city_id = %(city)s and p.category = 'park'
                    and ST_DWithin(h.centroid_pop::geography, p.geom::geography, 1200)) as parks,
                (select count(*) from staging.pois p
                  where p.city_id = %(city)s and ST_Contains(h.geom, p.geom)) / nullif(h.km2, 0) as density
              from hood h
            )
            insert into neighborhood_metrics (neighborhood_id, metric_key, value, coverage, dataset_version_id)
            select nid, x.key, x.v, 1.0, %(vid)s
            from m, lateral (values
              ('essential_amenities_800m', m.essentials::numeric),
              ('food_venues_800m', m.food::numeric),
              ('park_access', m.parks::numeric),
              ('amenity_density', m.density)
            ) x(key, v)
            where x.v is not null
            on conflict (neighborhood_id, metric_key, dataset_version_id)
            do update set value = excluded.value, coverage = excluded.coverage
            """,
            {"city": city_id, "vid": vid, "essentials": list(ESSENTIALS)},
        )
        n = c.execute(
            "select count(*) from neighborhood_metrics where dataset_version_id = %s", (vid,)
        ).fetchone()[0]
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"walkability: {n} neighborhood metrics")
    return 0
