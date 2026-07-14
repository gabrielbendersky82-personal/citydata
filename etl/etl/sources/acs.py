"""Census ACS 5-year tract metrics (income, housing, education, employment).

Requires CENSUS_API_KEY (free; api.census.gov signup) — mandatory since 2026.
Skips gracefully with a warning if absent so the rest of the pipeline runs.
"""
from __future__ import annotations

import os

import requests

from etl import db
from etl.build.rollup import rollup
from etl.config import load_city
from etl.fetch import UA

ACS_YEAR = os.environ.get("ACS_YEAR", "2023")
BASE = "https://api.census.gov/data/{year}/acs/acs5"

# metric -> (numerator vars, denominator vars or None for direct value, scale)
DIRECT = {
    "median_hh_income": "B19013_001E",
    "median_home_value": "B25077_001E",
    "median_gross_rent": "B25064_001E",
}
RATIOS = {
    # rent burden: 30%+ of income on rent (B25070 buckets 7-10 / total reporting)
    "rent_burden_pct": (["B25070_007E", "B25070_008E", "B25070_009E", "B25070_010E"], "B25070_001E"),
    "poverty_rate": (["B17001_002E"], "B17001_001E"),
    "bachelors_plus_pct": (["B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E"], "B15003_001E"),
    "unemployment_rate": (["B23025_005E"], "B23025_003E"),
}
# mean commute: aggregate minutes / workers who commute
COMMUTE = ("B08013_001E", "B08012_001E")

ALL_KEYS = [*DIRECT, *RATIOS, "mean_commute_min"]


def run(city: str, extra: list[str]) -> int:
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("WARN: CENSUS_API_KEY not set — skipping ACS ingestion (metrics will be coverage-flagged)")
        return 0

    cfg = load_city(city)
    city_id = cfg["city"]["id"]
    state, county = cfg["city"]["state_fips"], cfg["city"]["county_fips"][2:]

    variables = list(DIRECT.values()) + [v for nums, den in RATIOS.values() for v in [*nums, den]] + list(COMMUTE)
    moe_vars = [v[:-1] + "M" for v in DIRECT.values()]
    r = requests.get(
        BASE.format(year=ACS_YEAR),
        params={
            "get": ",".join(dict.fromkeys(variables + moe_vars)),
            "for": "tract:*",
            "in": f"state:{state} county:{county}",
            "key": key,
        },
        headers={"User-Agent": UA},
        timeout=180,
    )
    r.raise_for_status()
    header, *data = r.json()
    idx = {name: i for i, name in enumerate(header)}

    def val(row, var):
        v = row[idx[var]]
        if v is None:
            return None
        f = float(v)
        return None if f < -111111111 else f  # census sentinel for suppressed

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "acs", f"acs5_{ACS_YEAR}")
        known = {g for (g,) in c.execute("select geoid from tracts").fetchall()}
        rows = []
        for row in data:
            tract = row[idx["state"]] + row[idx["county"]] + row[idx["tract"]]
            if tract not in known:
                continue
            for m_key, var in DIRECT.items():
                v = val(row, var)
                if v is not None:
                    moe = val(row, var[:-1] + "M")
                    rows.append((tract, m_key, v, moe, vid))
            for m_key, (nums, den) in RATIOS.items():
                d = val(row, den)
                ns = [val(row, n) for n in nums]
                if d and all(n is not None for n in ns):
                    rows.append((tract, m_key, sum(ns) / d * 100, None, vid))
            agg_min, workers = val(row, COMMUTE[0]), val(row, COMMUTE[1])
            if agg_min is not None and workers:
                rows.append((tract, "mean_commute_min", agg_min / workers, None, vid))
        n = db.upsert_rows(c, "tract_metrics",
                           ["tract_geoid", "metric_key", "value", "moe", "dataset_version_id"],
                           rows, ["tract_geoid", "metric_key", "dataset_version_id"])
        rolled = rollup(c, city_id, ALL_KEYS, vid, vid)
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"acs: {n} tract metrics, {rolled} rollups")
    return 0
