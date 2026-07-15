"""FEMA National Risk Index — tract-level composite + per-hazard scores.

Primary path: the NRI census-tract ArcGIS feature service on
hazards.fema.gov/arcgis (same host that serves NFHL, verified reachable),
with the service name discovered at run time. Fallback: bulk CSV download
candidates (URL has churned post-RAPT; override with NRI_URL env).
"""
from __future__ import annotations

import io
import os
import re
import zipfile

import pandas as pd
import requests

from etl import db
from etl.build.rollup import rollup
from etl.config import load_city
from etl.fetch import UA, AllSourcesBlocked, download

ARCGIS_ROOT = "https://hazards.fema.gov/arcgis/rest/services"
LEGACY_URL = "https://hazards.fema.gov/nri/Content/StaticDocuments/DataDownload//NRI_Table_CensusTracts/NRI_Table_CensusTracts.zip"

COLUMN_METRICS = {
    "RISK_SCORE": "nri_risk_score",
    "HWAV_RISKS": "nri_heat_score",
    "WNTW_RISKS": "nri_winter_score",
    "TRND_RISKS": "nri_tornado_score",
}
PAGE = 1000


def _get(url: str, **params) -> dict:
    r = requests.get(url, params={"f": "json", **params}, headers={"User-Agent": UA}, timeout=120)
    r.raise_for_status()
    return r.json()


def discover_service() -> tuple[str, int] | None:
    """Find the NRI census-tract layer under the public ArcGIS folders."""
    try:
        root = _get(ARCGIS_ROOT)
        folders = [""] + root.get("folders", [])
        for folder in folders:
            listing = _get(f"{ARCGIS_ROOT}/{folder}" if folder else ARCGIS_ROOT)
            for svc in listing.get("services", []):
                name = svc["name"]
                if "nri" not in name.lower():
                    continue
                svc_url = f"{ARCGIS_ROOT.rsplit('/rest/services', 1)[0]}/rest/services/{name}/{svc['type']}"
                meta = _get(svc_url)
                for layer in meta.get("layers", []):
                    if re.search(r"tract", layer["name"], re.I):
                        print(f"  NRI service: {name} layer {layer['id']} ({layer['name']})")
                        return svc_url, layer["id"]
    except requests.RequestException as e:
        print(f"  ArcGIS discovery failed: {e.__class__.__name__}")
    return None


def fetch_via_arcgis(svc_url: str, layer_id: int, state_fips: str) -> pd.DataFrame:
    fields = ["TRACTFIPS", *COLUMN_METRICS]
    rows, offset = [], 0
    while True:
        data = _get(
            f"{svc_url}/{layer_id}/query",
            where=f"STATEFIPS = '{state_fips}'",
            outFields=",".join(fields),
            returnGeometry="false",
            resultOffset=offset,
            resultRecordCount=PAGE,
        )
        feats = data.get("features", [])
        rows += [f["attributes"] for f in feats]
        if len(feats) < PAGE:
            break
        offset += PAGE
    return pd.DataFrame(rows)


def fetch_via_csv(state_fips: str) -> pd.DataFrame:
    urls = [u for u in (os.environ.get("NRI_URL"), LEGACY_URL, LEGACY_URL.replace("//NRI", "/NRI")) if u]
    path, _ = download(urls[0], "nri_tracts", mirrors=urls[1:])
    with zipfile.ZipFile(path) as z:
        csv_name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(csv_name) as fobj:
            df = pd.read_csv(
                io.TextIOWrapper(fobj, "utf-8"),
                usecols=lambda c: c in {"TRACTFIPS", *COLUMN_METRICS},
                dtype={"TRACTFIPS": str},
            )
    return df[df["TRACTFIPS"].str.startswith(state_fips)]


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]
    state_fips = cfg["city"]["state_fips"]

    svc = discover_service()
    if svc:
        df = fetch_via_arcgis(svc[0], svc[1], state_fips)
        vintage = "arcgis_service"
    else:
        df = fetch_via_csv(state_fips)
        vintage = "bulk_csv"
    if df.empty:
        raise AllSourcesBlocked("NRI: no rows from ArcGIS service or CSV")
    print(f"  NRI rows for state {state_fips}: {len(df)} via {vintage}")

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "fema_nri", f"tracts_{vintage}")
        known = {g for (g,) in c.execute("select geoid from tracts").fetchall()}
        rows = []
        for r in df.itertuples():
            tract = str(r.TRACTFIPS).zfill(11)
            if tract not in known:
                continue
            for col, key in COLUMN_METRICS.items():
                v = getattr(r, col, None)
                if v is not None and pd.notna(v):
                    rows.append((tract, key, float(v), vid))
        n = db.upsert_rows(c, "tract_metrics", ["tract_geoid", "metric_key", "value", "dataset_version_id"],
                           rows, ["tract_geoid", "metric_key", "dataset_version_id"])
        rolled = rollup(c, city_id, list(COLUMN_METRICS.values()), vid, vid)
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"fema_nri: {n} tract metrics, {rolled} rollups")
    return 0
