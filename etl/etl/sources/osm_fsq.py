"""POIs from Overture Maps places (CDLA-Permissive-2.0; includes Foursquare
OS Places + OSM-derived data). Read straight off the public S3 bucket as
GeoParquet with bbox predicate pushdown — no bulk download.

Attribution: © Overture Maps Foundation; includes Foursquare OS Places and
© OpenStreetMap contributors data.
"""
from __future__ import annotations

import re

import pyarrow.dataset as ds
import requests

from etl import db
from etl.config import load_city

BASE = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"

# normalized bucket -> regex on Overture categories.primary
CATEGORY_PATTERNS = {
    "grocery": r"grocery|supermarket|farmers_market|food_store",
    "food_drink": r"^(restaurant|cafe|coffee|bar|pub|bakery|brewery|fast_food|dessert|tea_)|_restaurant$",
    "pharmacy": r"pharmacy|drugstore",
    "health": r"hospital|clinic|doctor|dentist|urgent_care|health_center",
    "fitness": r"gym|fitness|yoga|sports_club|recreation_center",
    "park": r"^park$|state_park|city_park|playground|garden|dog_park|nature_reserve",
    "culture": r"museum|library|theater|theatre|art_gallery|cinema|music_venue",
    "retail": r"clothing|shopping|bookstore|hardware|electronics|department_store|convenience",
    "education": r"^school$|elementary_school|middle_school|high_school|preschool|child_care",
}


def latest_release() -> str:
    t = requests.get(f"{BASE}/?list-type=2&prefix=release/&delimiter=/", timeout=30).text
    return sorted(re.findall(r"<Prefix>release/([^<]+)/</Prefix>", t))[-1]


def place_files(release: str) -> list[str]:
    keys, token = [], None
    while True:
        url = f"{BASE}/?list-type=2&prefix=release/{release}/theme=places/type=place/"
        if token:
            url += f"&continuation-token={requests.utils.quote(token)}"
        t = requests.get(url, timeout=30).text
        keys += re.findall(r"<Key>([^<]+\.parquet)</Key>", t)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", t)
        if not m:
            return [f"{BASE}/{k}" for k in keys]
        token = m.group(1)


def bucket_of(cat: str | None) -> str | None:
    if not cat:
        return None
    for bucket, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, cat):
            return bucket
    return None


def run(city: str, extra: list[str]) -> int:
    import fsspec

    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        bbox = c.execute(
            """select ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) from
               (select ST_Extent(geom)::geometry as e from neighborhoods where city_id = %s) s""",
            (city_id,),
        ).fetchone()
        xmin, ymin, xmax, ymax = (float(v) for v in bbox)

        release = latest_release()
        files = place_files(release)
        print(f"  overture {release}: {len(files)} place files, bbox=({xmin:.2f},{ymin:.2f},{xmax:.2f},{ymax:.2f})")
        vid = db.ensure_dataset_version(c, "overture_places", release)

        fs = fsspec.filesystem("https")
        f = ds.field
        expr = (
            (f(("bbox", "xmin")) > xmin) & (f(("bbox", "xmax")) < xmax)
            & (f(("bbox", "ymin")) > ymin) & (f(("bbox", "ymax")) < ymax)
        )
        total, failed_files = 0, 0
        for i, url in enumerate(files):
            tbl = None
            for attempt in range(3):  # S3-over-HTTP reads flake occasionally
                try:
                    d = ds.dataset(url, filesystem=fs, format="parquet")
                    tbl = d.to_table(
                        columns={
                            "id": f("id"),
                            "cat": f(("categories", "primary")),
                            "name": f(("names", "primary")),
                            "lon": f(("bbox", "xmin")),
                            "lat": f(("bbox", "ymin")),
                        },
                        filter=expr,
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"WARN: file {i + 1}/{len(files)} failed after retries ({e.__class__.__name__}); continuing")
                        failed_files += 1
                    else:
                        import time

                        time.sleep(3 * (attempt + 1))
            if tbl is None:
                continue
            if not tbl.num_rows:
                continue
            rows = []
            for rec in tbl.to_pylist():
                bucket = bucket_of(rec["cat"])
                if bucket is None:
                    continue
                rows.append(
                    (
                        f"ovt:{rec['id']}",
                        "overture",
                        bucket,
                        rec["cat"],
                        rec["name"],
                        city_id,
                        f"SRID=4326;POINT({rec['lon']} {rec['lat']})",
                    )
                )
            total += db.upsert_rows(
                c, "staging.pois",
                ["id", "source", "category", "source_category", "name", "city_id", "geom"],
                rows, ["id"],
            )
            c.commit()
            print(f"  file {i + 1}/{len(files)}: +{len(rows)} (total {total})")
        db.finish_dataset_version(c, vid, total)
        c.commit()
        print(f"overture places: {total} POIs in city bbox ({failed_files} files skipped)")
        if total == 0:
            raise RuntimeError("no POIs ingested — refusing to publish empty walkability")
    return 0
