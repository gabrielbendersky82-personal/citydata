"""Assemble the city bundle: everything the frontend needs to rank and
explain, in one JSON document.

Written to apps/web/public/bundles/<city>.json (static serving path — the app
works even with no database behind it) and into the local city_bundles table
(which the Supabase loader exports).
"""
from __future__ import annotations

import json
import os

from etl import db
from etl.config import load_city

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "apps", "web", "public", "bundles",
)


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        metrics_meta = {
            k: {
                "label": label, "units": units, "criterion": crit,
                "higherIsBetter": hib, "intraWeight": float(w),
                "source": src, "attribution": attr,
            }
            for k, label, units, crit, hib, w, src, attr in c.execute(
                """select key, label, units, criterion, higher_is_better,
                          default_intra_weight, source, source_attribution
                   from metric_definitions order by key"""
            ).fetchall()
        }

        version_set = {
            src: {"vintage": vintage, "retrievedAt": str(ts)}
            for src, vintage, ts in c.execute(
                """select distinct on (dv.source) dv.source, dv.vintage_label, dv.retrieved_at
                   from dataset_versions dv
                   join neighborhood_metrics m on m.dataset_version_id = dv.id
                   join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %s
                   order by dv.source, dv.retrieved_at desc""",
                (city_id,),
            ).fetchall()
        }

        # latest vintage per metric
        rows = c.execute(
            """
            with latest as (
              select m.metric_key, max(m.dataset_version_id) as vid
              from neighborhood_metrics m
              join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %(city)s
              group by m.metric_key
            )
            select m.neighborhood_id, m.metric_key, m.value, m.percentile, m.coverage, m.confidence
            from neighborhood_metrics m
            join latest l on l.metric_key = m.metric_key and l.vid = m.dataset_version_id
            join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %(city)s
            """,
            {"city": city_id},
        ).fetchall()

        medians = {
            key: float(med) if med is not None else None
            for key, med in c.execute(
                """
                with latest as (
                  select m.metric_key, max(m.dataset_version_id) as vid
                  from neighborhood_metrics m
                  join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %(city)s
                  group by m.metric_key
                )
                select m.metric_key, percentile_cont(0.5) within group (order by m.value)
                from neighborhood_metrics m
                join latest l on l.metric_key = m.metric_key and l.vid = m.dataset_version_id
                join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %(city)s
                where m.value is not null
                group by m.metric_key
                """,
                {"city": city_id},
            ).fetchall()
        }

        per_hood: dict[int, dict] = {}
        for nid, key, value, pct, cov, conf in rows:
            per_hood.setdefault(nid, {})[key] = {
                "value": float(value) if value is not None else None,
                "pct": float(pct) if pct is not None else None,
                "coverage": float(cov) if cov is not None else None,
                "confidence": conf,
            }

        hoods = c.execute(
            """select id, slug, name, boundary_source,
                      ST_X(centroid_pop), ST_Y(centroid_pop), ST_AsGeoJSON(geom_display, 5),
                      (select round(sum(x.pop_weight * t.pop_2020))::int
                       from tract_neighborhood_xwalk x join tracts t on t.geoid = x.tract_geoid
                       where x.neighborhood_id = neighborhoods.id and t.pop_2020 is not null)
               from neighborhoods where city_id = %s order by name""",
            (city_id,),
        ).fetchall()

        features, hood_list = [], []
        for nid, slug, name, bsrc, lon, lat, gj, pop in hoods:
            hood_list.append({
                "id": nid, "slug": slug, "name": name,
                "centroid": [round(lon, 5), round(lat, 5)],
                "population": pop,
                "boundarySource": bsrc,
                "metrics": per_hood.get(nid, {}),
            })
            features.append({
                "type": "Feature",
                "id": nid,
                "properties": {"slug": slug, "name": name},
                "geometry": json.loads(gj),
            })

        bundle = {
            "city": {"id": city_id, "slug": cfg["city"]["slug"], "name": cfg["city"]["name"],
                     "state": cfg["city"]["state"]},
            "versionSet": version_set,
            "metricsMeta": metrics_meta,
            "cityMedians": medians,
            "neighborhoods": hood_list,
            "geojson": {"type": "FeatureCollection", "features": features},
        }

        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{cfg['city']['slug']}.json")
        with open(out_path, "w") as f:
            json.dump(bundle, f, separators=(",", ":"))
        size_kb = os.path.getsize(out_path) // 1024

        c.execute(
            "update city_bundles set is_current = false where city_id = %s", (city_id,)
        )
        c.execute(
            """insert into city_bundles (city_id, version_set, bundle, is_current)
               values (%s, %s, %s, true)""",
            (city_id, json.dumps(version_set), json.dumps(bundle)),
        )
        c.commit()

        n_metrics = sum(len(h["metrics"]) for h in hood_list)
        print(f"bundle: {len(hood_list)} neighborhoods, {n_metrics} metric values, {size_kb} KB -> {out_path}")
    return 0
