"""Roll tract-level metrics up to neighborhoods through the crosswalk.

Weight for tract t within neighborhood n = pop_weight(n,t) × tract population
(area in km² as proxy when population is unavailable in area-fallback mode).
Coverage = share of a neighborhood's total weight backed by tracts that have
a value — never silently zero-filled.
"""
from __future__ import annotations

import psycopg


def rollup(
    c: psycopg.Connection,
    city_id: int,
    metric_keys: list[str],
    source_version_id: int,
    target_version_id: int,
) -> int:
    cur = c.execute(
        """
        with w as (
          select x.neighborhood_id, x.tract_geoid,
                 x.pop_weight * coalesce(t.pop_2020::numeric, t.aland::numeric / 1e6, 1) as wt
          from tract_neighborhood_xwalk x
          join tracts t on t.geoid = x.tract_geoid
          join neighborhoods n on n.id = x.neighborhood_id and n.city_id = %(city)s
        ),
        agg as (
          select w.neighborhood_id, tm.metric_key,
                 sum(tm.value * w.wt) filter (where tm.value is not null)
                   / nullif(sum(w.wt) filter (where tm.value is not null), 0) as value,
                 coalesce(sum(w.wt) filter (where tm.value is not null)
                   / nullif(sum(w.wt), 0), 0) as coverage
          from w
          join tract_metrics tm on tm.tract_geoid = w.tract_geoid
           and tm.metric_key = any(%(keys)s)
           and tm.dataset_version_id = %(src_vid)s
          group by w.neighborhood_id, tm.metric_key
        )
        insert into neighborhood_metrics
          (neighborhood_id, metric_key, value, coverage, dataset_version_id)
        select neighborhood_id, metric_key, value, coverage, %(tgt_vid)s
        from agg
        on conflict (neighborhood_id, metric_key, dataset_version_id)
        do update set value = excluded.value, coverage = excluded.coverage
        """,
        {
            "city": city_id,
            "keys": metric_keys,
            "src_vid": source_version_id,
            "tgt_vid": target_version_id,
        },
    )
    return cur.rowcount
