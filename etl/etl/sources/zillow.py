"""Zillow ZHVI (home values) + ZORI (rents) at ZIP level, apportioned to
tracts via the HUD ZIP↔tract crosswalk, then rolled up to neighborhoods.

Attribution: data © Zillow (zillow.com/research/data). Displayed/derived
analytics only — raw data is never redistributed or resold.
"""
from __future__ import annotations

import pandas as pd

from etl import db
from etl.build.rollup import rollup
from etl.config import load_city
from etl.fetch import download

ZHVI_ZIP_URL = "https://files.zillowstatic.com/research/public_csvs/zhvi/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
ZORI_ZIP_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondo_sm_sa_month.csv"
# HUD USPS crosswalk quarterly file (public download); quarter is bumped by the ETL calendar
HUD_XWALK_URL = "https://www.huduser.gov/portal/datasets/usps/ZIP_TRACT_032026.xlsx"


def load_hud_xwalk(c, state_fips: str) -> str:
    vintage = HUD_XWALK_URL.rsplit("_", 1)[-1].split(".")[0]
    path, _ = download(HUD_XWALK_URL, f"hud_zip_tract_{vintage}")
    df = pd.read_excel(path, dtype={"ZIP": str, "TRACT": str, "zip": str, "tract": str})
    df.columns = [col.lower() for col in df.columns]
    df = df[df["tract"].str.startswith(state_fips)]
    rows = [(r.zip, r.tract, float(r.res_ratio), vintage) for r in df.itertuples()]
    db.upsert_rows(c, "zip_tract_xwalk", ["zip", "tract_geoid", "res_ratio", "vintage"], rows,
                   ["zip", "tract_geoid", "vintage"])
    return vintage


def latest_value_by_zip(csv_path: str, city_name: str, state: str) -> dict[str, float]:
    df = pd.read_csv(csv_path, dtype={"RegionName": str})
    df = df[(df["State"] == state) & (df["City"] == city_name)]
    month_cols = [col for col in df.columns if col[:2] == "20" and "-" in col]
    month_cols.sort()
    out: dict[str, float] = {}
    for r in df.itertuples():
        row = df.loc[r.Index, month_cols].dropna()
        if len(row):
            out[getattr(r, "RegionName")] = float(row.iloc[-1])
    return out


def apportion_to_tracts(c, values_by_zip: dict[str, float], metric_key: str, vid: int, state_fips: str) -> int:
    """tract value = res_ratio-weighted mean of its ZIPs' values."""
    rows = c.execute(
        """
        select tract_geoid, zip, res_ratio from zip_tract_xwalk
        where vintage = (select max(vintage) from zip_tract_xwalk)
          and tract_geoid like %s
        """,
        (state_fips + "%",),
    ).fetchall()
    acc: dict[str, list[tuple[float, float]]] = {}
    for tract, zipc, ratio in rows:
        if zipc in values_by_zip:
            acc.setdefault(tract, []).append((values_by_zip[zipc], float(ratio)))
    out = [
        (tract, metric_key, sum(v * w for v, w in pairs) / sum(w for _, w in pairs), vid)
        for tract, pairs in acc.items()
        if sum(w for _, w in pairs) > 0
    ]
    return db.upsert_rows(c, "tract_metrics", ["tract_geoid", "metric_key", "value", "dataset_version_id"],
                          out, ["tract_geoid", "metric_key", "dataset_version_id"])


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]
    state = cfg["city"]["state"]
    state_fips = cfg["city"]["state_fips"]
    city_name = cfg["city"]["name"]

    with db.conn() as c:
        hud_vintage = load_hud_xwalk(c, state_fips)
        vid = db.ensure_dataset_version(c, "zillow", f"zip_{pd.Timestamp.utcnow():%Y%m}_hud{hud_vintage}")

        n = 0
        for url, key in ((ZHVI_ZIP_URL, "zhvi"), (ZORI_ZIP_URL, "zori")):
            path, _ = download(url, f"zillow_{key}_zip")
            vals = latest_value_by_zip(path, city_name, state)
            n += apportion_to_tracts(c, vals, key, vid, state_fips)
            print(f"  {key}: {len(vals)} ZIPs -> tract metrics")
        rolled = rollup(c, city_id, ["zhvi", "zori"], vid, vid)
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"zillow: {n} tract metrics, {rolled} neighborhood rollups")
    return 0
