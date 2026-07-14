"""CDC PLACES tract-level health measures via Socrata (data.cdc.gov).

The dataset ID changes with each yearly release, so it is discovered at run
time through the Socrata catalog (override with PLACES_DATASET_ID env).
"""
from __future__ import annotations

import os

import requests

from etl import db
from etl.build.rollup import rollup
from etl.config import load_city
from etl.fetch import UA

CATALOG = "https://api.us.socrata.com/api/catalog/v1"
MEASURES = {
    "MHLTH": "poor_mental_health_pct",
    "CASTHMA": "asthma_pct",
    "LPA": "physical_inactivity_pct",
}
PAGE = 50_000


def discover_dataset_id() -> str:
    override = os.environ.get("PLACES_DATASET_ID")
    if override:
        return override
    r = requests.get(
        CATALOG,
        params={
            "domains": "data.cdc.gov",
            "search_context": "data.cdc.gov",
            "q": "PLACES Census Tract Data GIS Friendly Format",
            "only": "datasets",
            "limit": 10,
        },
        headers={"User-Agent": UA},
        timeout=60,
    )
    r.raise_for_status()
    results = r.json()["results"]
    candidates = [
        (res["resource"]["name"], res["resource"]["id"])
        for res in results
        if "census tract" in res["resource"]["name"].lower()
        and "gis friendly" in res["resource"]["name"].lower()
    ]
    if not candidates:
        raise RuntimeError("no PLACES tract dataset found in catalog")
    name, ds_id = sorted(candidates, reverse=True)[0]  # latest release sorts last by year in name
    print(f"  PLACES dataset: {name} ({ds_id})")
    return ds_id


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]
    county5 = cfg["city"]["county_fips"]

    ds_id = discover_dataset_id()
    base = f"https://data.cdc.gov/resource/{ds_id}.json"
    headers = {"User-Agent": UA}
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "cdc_places", f"tract_gis_{ds_id}")
        known = {g for (g,) in c.execute("select geoid from tracts").fetchall()}
        rows, offset = [], 0
        while True:
            r = requests.get(
                base,
                params={
                    "$where": f"countyfips = '{county5}'",
                    "$limit": PAGE,
                    "$offset": offset,
                },
                headers=headers,
                timeout=120,
            )
            r.raise_for_status()
            batch = r.json()
            if not batch:
                break
            for rec in batch:
                tract = str(rec.get("tractfips", "")).zfill(11)
                if tract not in known:
                    continue
                for code, key in MEASURES.items():
                    # GIS-friendly format: one column per measure, e.g. mhlth_crudeprev
                    v = rec.get(f"{code.lower()}_crudeprev")
                    if v not in (None, ""):
                        rows.append((tract, key, float(v), vid))
            offset += PAGE
            if len(batch) < PAGE:
                break
        n = db.upsert_rows(c, "tract_metrics", ["tract_geoid", "metric_key", "value", "dataset_version_id"],
                           rows, ["tract_geoid", "metric_key", "dataset_version_id"])
        rolled = rollup(c, city_id, list(MEASURES.values()), vid, vid)
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"cdc_places: {n} tract metrics, {rolled} rollups")
    return 0
