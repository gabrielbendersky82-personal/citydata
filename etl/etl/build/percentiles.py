"""Compute within-city, direction-adjusted percentiles (100 = best) and
confidence badges over the latest vintage of every metric."""
from __future__ import annotations

from etl import db
from etl.config import load_city


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        cur = c.execute(
            """
            with latest as (
              select m.metric_key, max(m.dataset_version_id) as vid
              from neighborhood_metrics m
              join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %(city)s
              group by m.metric_key
            ),
            ranked as (
              select m.neighborhood_id, m.metric_key, m.dataset_version_id, m.coverage,
                     case when d.higher_is_better
                          then percent_rank() over (partition by m.metric_key order by m.value)
                          else percent_rank() over (partition by m.metric_key order by m.value desc)
                     end * 100 as pct
              from neighborhood_metrics m
              join latest l on l.metric_key = m.metric_key and l.vid = m.dataset_version_id
              join metric_definitions d on d.key = m.metric_key
              join neighborhoods n on n.id = m.neighborhood_id and n.city_id = %(city)s
              where m.value is not null
            )
            update neighborhood_metrics m
            set percentile = r.pct,
                confidence = case
                  when coalesce(m.coverage, 0) >= 0.9 then 'high'
                  when coalesce(m.coverage, 0) >= 0.6 then 'medium'
                  else 'low' end
            from ranked r
            where m.neighborhood_id = r.neighborhood_id
              and m.metric_key = r.metric_key
              and m.dataset_version_id = r.dataset_version_id
            """,
            {"city": city_id},
        )
        n = cur.rowcount
        c.commit()
        print(f"percentiles: {n} metric rows updated")
    return 0
