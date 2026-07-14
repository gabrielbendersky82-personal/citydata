"""FEMA NFHL: share of each neighborhood inside a Special Flood Hazard Area.

Queries the NFHL ArcGIS REST flood-zone layer per neighborhood envelope and
intersects locally. Zones starting with A or V are SFHA (1%-annual-chance).
"""
from __future__ import annotations

import json

import requests
from shapely.geometry import shape
from shapely.ops import unary_union

from etl import db
from etl.config import load_city
from etl.fetch import UA

NFHL_LAYER = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"


def sfha_share(geom_geojson: dict) -> float | None:
    poly = shape(geom_geojson)
    minx, miny, maxx, maxy = poly.bounds
    r = requests.get(
        NFHL_LAYER,
        params={
            "geometry": json.dumps({"xmin": minx, "ymin": miny, "xmax": maxx, "ymax": maxy,
                                    "spatialReference": {"wkid": 4326}}),
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "outSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "where": "FLD_ZONE LIKE 'A%' OR FLD_ZONE LIKE 'V%'",
            "outFields": "FLD_ZONE",
            "returnGeometry": "true",
            "f": "geojson",
        },
        headers={"User-Agent": UA},
        timeout=120,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        return 0.0
    flood = unary_union([shape(f["geometry"]) for f in feats if f.get("geometry")])
    return poly.intersection(flood).area / poly.area * 100 if poly.area else None


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    city_id = cfg["city"]["id"]

    with db.conn() as c:
        vid = db.ensure_dataset_version(c, "nfhl", f"{city}_sfha")
        hoods = c.execute(
            "select id, ST_AsGeoJSON(geom) from neighborhoods where city_id = %s order by id",
            (city_id,),
        ).fetchall()
        rows = []
        for nid, gj in hoods:
            try:
                share = sfha_share(json.loads(gj))
            except requests.RequestException as e:
                print(f"WARN: NFHL query failed for neighborhood {nid}: {e}")
                share = None
            if share is not None:
                rows.append((nid, "flood_sfha_pct", share, 1.0, vid))
        n = db.upsert_rows(
            c, "neighborhood_metrics",
            ["neighborhood_id", "metric_key", "value", "coverage", "dataset_version_id"],
            rows, ["neighborhood_id", "metric_key", "dataset_version_id"],
        )
        db.finish_dataset_version(c, vid, n)
        c.commit()
        print(f"nfhl: {n}/{len(hoods)} neighborhoods with SFHA share")
    return 0
