"""Build the tract↔neighborhood crosswalk.

Preferred mode: block-population weighting (2020 blocks, centroid-in-polygon).
Fallback mode (no staging.blocks rows, e.g. egress-restricted dev): area
weighting, recorded as built_from='area_fallback' so a later Actions run with
real blocks upgrades it.

Also: assigns tracts.city_id, builds simplified display geometries and
population(-ish) centroids, and validates weight sums.
"""
from __future__ import annotations

from etl import db
from etl.config import load_city

SIMPLIFY_TOLERANCE_DEG = 0.0005  # ~50m; keeps 77-area GeoJSON well under 100KB gzipped


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        have_blocks = c.execute("select exists(select 1 from staging.blocks)").fetchone()[0]

        c.execute(
            """
            delete from tract_neighborhood_xwalk
            where neighborhood_id in (select id from neighborhoods where city_id = %s)
            """,
            (city_id,),
        )

        if have_blocks:
            c.execute(
                """
                with tract_pop as (
                  select tract_geoid, sum(pop) as pop from staging.blocks group by tract_geoid
                ),
                assigned as (
                  select n.id as nid, b.tract_geoid, sum(b.pop) as pop, count(*) as blocks
                  from staging.blocks b
                  join neighborhoods n on n.city_id = %s and ST_Contains(n.geom, b.centroid)
                  group by n.id, b.tract_geoid
                )
                insert into tract_neighborhood_xwalk
                  (neighborhood_id, tract_geoid, pop_weight, block_count, built_from)
                select a.nid, a.tract_geoid,
                       a.pop::numeric / nullif(tp.pop, 0),
                       a.blocks, '2020_blocks_p1'
                from assigned a join tract_pop tp using (tract_geoid)
                where tp.pop > 0 and a.pop > 0
                """,
                (city_id,),
            )
            mode = "2020_blocks_p1"
        else:
            c.execute(
                """
                insert into tract_neighborhood_xwalk
                  (neighborhood_id, tract_geoid, pop_weight, block_count, built_from)
                select n.id, t.geoid, share, null, 'area_fallback'
                from tracts t
                join neighborhoods n on n.city_id = %s and ST_Intersects(t.geom, n.geom)
                cross join lateral (
                  select ST_Area(ST_Intersection(t.geom, n.geom)::geography)
                       / nullif(ST_Area(t.geom::geography), 0) as share
                ) s
                where share > 0.02
                """,
                (city_id,),
            )
            # geometric overlap of simplified polygons can push a tract's sum
            # slightly over 1 — renormalize only those
            c.execute(
                """
                update tract_neighborhood_xwalk x set pop_weight = x.pop_weight / s.total
                from (
                  select tract_geoid, sum(pop_weight) as total
                  from tract_neighborhood_xwalk group by tract_geoid having sum(pop_weight) > 1
                ) s
                where x.tract_geoid = s.tract_geoid
                """
            )
            mode = "area_fallback"

        # tracts that carry weight belong to the city
        c.execute(
            """
            update tracts t set city_id = %s
            where t.geoid in (select tract_geoid from tract_neighborhood_xwalk
                              where neighborhood_id in (select id from neighborhoods where city_id = %s))
            """,
            (city_id, city_id),
        )

        # display geometry + centroid
        c.execute(
            """
            update neighborhoods
            set geom_display = ST_Multi(ST_SimplifyPreserveTopology(geom, %s))
            where city_id = %s
            """,
            (SIMPLIFY_TOLERANCE_DEG, city_id),
        )
        if have_blocks:
            c.execute(
                """
                update neighborhoods n set centroid_pop = w.pt
                from (
                  select n2.id, ST_SetSRID(ST_MakePoint(
                    sum(ST_X(b.centroid) * b.pop) / nullif(sum(b.pop), 0),
                    sum(ST_Y(b.centroid) * b.pop) / nullif(sum(b.pop), 0)), 4326) as pt
                  from neighborhoods n2
                  join staging.blocks b on ST_Contains(n2.geom, b.centroid)
                  where n2.city_id = %s
                  group by n2.id
                ) w where w.id = n.id
                """,
                (city_id,),
            )
        c.execute(
            """
            update neighborhoods set centroid_pop = ST_PointOnSurface(geom)
            where city_id = %s and centroid_pop is null
            """,
            (city_id,),
        )

        vid = db.ensure_dataset_version(c, "crosswalk", f"{city}_{mode}")

        # --- validation ---
        stats = c.execute(
            """
            select count(distinct neighborhood_id),
                   count(distinct tract_geoid),
                   count(*),
                   avg(sums.total), max(sums.total)
            from tract_neighborhood_xwalk x,
            lateral (select sum(pop_weight) as total from tract_neighborhood_xwalk x2
                     where x2.tract_geoid = x.tract_geoid) sums
            """
        ).fetchone()
        n_hoods, n_tracts, n_rows, avg_sum, max_sum = stats
        uncovered = c.execute(
            "select count(*) from neighborhoods where city_id = %s and id not in "
            "(select neighborhood_id from tract_neighborhood_xwalk)",
            (city_id,),
        ).fetchone()[0]
        db.finish_dataset_version(c, vid, n_rows)
        c.commit()

        print(
            f"crosswalk[{mode}]: {n_rows} pairs, {n_hoods} neighborhoods, {n_tracts} tracts; "
            f"tract weight sums avg={avg_sum:.3f} max={max_sum:.3f}; neighborhoods w/o tracts: {uncovered}"
        )
        assert uncovered == 0, "every neighborhood must map to at least one tract"
        assert float(max_sum) <= 1.001, "tract weights must not exceed 1"
    return 0
