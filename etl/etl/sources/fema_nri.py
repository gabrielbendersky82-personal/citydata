"""FEMA National Risk Index — tract-level composite + per-hazard scores.

Bulk CSV download (post-RAPT location may move; override with NRI_URL env).
"""
from __future__ import annotations

import io
import os
import zipfile

import pandas as pd

from etl import db
from etl.build.rollup import rollup
from etl.config import load_city
from etl.fetch import download

NRI_URL = os.environ.get(
    "NRI_URL",
    "https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload//NRI_Table_CensusTracts/NRI_Table_CensusTracts.zip",
)

COLUMN_METRICS = {
    "RISK_SCORE": "nri_risk_score",
    "HWAV_RISKS": "nri_heat_score",
    "WNTW_RISKS": "nri_winter_score",
    "TRND_RISKS": "nri_tornado_score",
}


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]
    state_fips = cfg["city"]["state_fips"]

    path, _ = download(NRI_URL, "nri_tracts")
    with zipfile.ZipFile(path) as z:
        csv_name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(csv_name) as f:
            df = pd.read_csv(
                io.TextIOWrapper(f, "utf-8"),
                usecols=lambda c: c in {"TRACTFIPS", *COLUMN_METRICS},
                dtype={"TRACTFIPS": str},
            )
    df = df[df["TRACTFIPS"].str.startswith(state_fips)]

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "fema_nri", "nri_tracts_latest")
        known = {g for (g,) in c.execute("select geoid from tracts").fetchall()}
        rows = []
        for r in df.itertuples():
            tract = r.TRACTFIPS.zfill(11)
            if tract not in known:
                continue
            for col, key in COLUMN_METRICS.items():
                v = getattr(r, col, None)
                if pd.notna(v):
                    rows.append((tract, key, float(v), vid))
        n = db.upsert_rows(c, "tract_metrics", ["tract_geoid", "metric_key", "value", "dataset_version_id"],
                           rows, ["tract_geoid", "metric_key", "dataset_version_id"])
        rolled = rollup(c, city_id, list(COLUMN_METRICS.values()), vid, vid)
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"fema_nri: {n} tract metrics, {rolled} rollups")
    return 0
