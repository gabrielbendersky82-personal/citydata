"""Geo spine: city row, TIGER/CB tracts, 2020 blocks (with population),
official neighborhood polygons. Everything lands in local PostGIS.

Blocks are optional: in egress-restricted dev environments the TABBLOCK20
download fails, and the crosswalk builder falls back to area weighting.
The GitHub Actions run (full egress) rebuilds with true block weighting.
"""
from __future__ import annotations

import re

import geopandas as gpd

from etl import db
from etl.config import load_city
from etl.fetch import AllSourcesBlocked, download

TABBLOCK_URL = "https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_{state}_tabblock20.zip"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def to_multi_wkt(geom) -> str:
    from shapely.geometry import MultiPolygon, Polygon

    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    return geom.wkt


def load_tracts(c, cfg) -> int:
    t_cfg = cfg["tracts"]
    county = cfg["city"]["county_fips"]
    path, used = download(
        t_cfg["official_url"],
        f"tracts_{cfg['city']['state_fips']}",
        mirrors=t_cfg.get("dev_mirrors"),
    )
    tracts = gpd.read_file(path)
    # CB shapefiles and their GeoJSON mirrors share the GEOID/COUNTYFP/ALAND columns.
    tracts = tracts[tracts["COUNTYFP"] == county[2:]]
    if tracts.crs is None:
        tracts = tracts.set_crs(4326)
    tracts = tracts.to_crs(4326)
    rows = [
        (
            str(r.GEOID),
            f"SRID=4326;{to_multi_wkt(r.geometry)}",
            int(getattr(r, "ALAND", 0) or 0),
            int(getattr(r, "AWATER", 0) or 0),
        )
        for r in tracts.itertuples()
    ]
    return db.upsert_rows(c, "tracts", ["geoid", "geom", "aland", "awater"], rows, ["geoid"])


def load_blocks(c, cfg) -> int:
    state = cfg["city"]["state_fips"]
    county = cfg["city"]["county_fips"]
    path, _ = download(TABBLOCK_URL.format(state=state), f"tl_2020_{state}_tabblock20.zip")
    import pyogrio

    blocks = pyogrio.read_dataframe(
        path,
        columns=["GEOID20", "COUNTYFP20", "POP20", "INTPTLAT20", "INTPTLON20"],
        where=f"COUNTYFP20 = '{county[2:]}'",
        read_geometry=False,
    )
    rows = [
        (
            r.GEOID20,
            r.GEOID20[:11],
            int(r.POP20),
            f"SRID=4326;POINT({float(r.INTPTLON20)} {float(r.INTPTLAT20)})",
        )
        for r in blocks.itertuples()
    ]
    n = db.upsert_rows(
        c, "staging.blocks", ["geoid", "tract_geoid", "pop", "centroid"], rows, ["geoid"]
    )
    c.execute(
        """
        update tracts t set pop_2020 = b.pop
        from (select tract_geoid, sum(pop) as pop from staging.blocks group by tract_geoid) b
        where b.tract_geoid = t.geoid
        """
    )
    return n


def load_neighborhoods(c, cfg) -> int:
    n_cfg = cfg["neighborhoods"]
    city_id = cfg["city"]["id"]
    path, used = download(
        n_cfg["url"],
        f"{cfg['city']['slug']}_neighborhoods.geojson",
        mirrors=n_cfg.get("dev_mirrors"),
    )
    hoods = gpd.read_file(path)
    if hoods.crs is None:
        hoods = hoods.set_crs(4326)
    hoods = hoods.to_crs(4326)
    name_field = n_cfg["name_field"]
    if name_field not in hoods.columns:
        # mirrors sometimes use different casing
        matches = [col for col in hoods.columns if col.lower() == name_field.lower()]
        if not matches:
            raise KeyError(f"name field {name_field!r} not in {list(hoods.columns)}")
        name_field = matches[0]
    rows = [
        (
            city_id,
            slugify(str(row[name_field])),
            str(row[name_field]).title(),
            f"SRID=4326;{to_multi_wkt(row.geometry)}",
            n_cfg["source"],
            used,
        )
        for _, row in hoods.iterrows()
    ]
    return db.upsert_rows(
        c,
        "neighborhoods",
        ["city_id", "slug", "name", "geom", "boundary_source", "source_ref"],
        rows,
        ["city_id", "slug"],
    )


def run(city: str, extra: list[str]) -> int:
    cfg = load_city(city)
    c_cfg = cfg["city"]

    with db.conn() as c:
        db.apply_schema(c)
        vid = db.ensure_dataset_version(c, "geo_spine", f"{city}_tiger_blocks2020")

        c.execute(
            """
            insert into cities (id, slug, name, state, place_geoid, status)
            values (%s, %s, %s, %s, %s, 'staging')
            on conflict (id) do update set slug = excluded.slug, name = excluded.name,
              state = excluded.state, place_geoid = excluded.place_geoid
            """,
            (c_cfg["id"], c_cfg["slug"], c_cfg["name"], c_cfg["state"], c_cfg["place_geoid"]),
        )

        n_tracts = load_tracts(c, cfg)
        print(f"tracts upserted: {n_tracts}")

        try:
            n_blocks = load_blocks(c, cfg)
            print(f"blocks upserted: {n_blocks}")
        except AllSourcesBlocked as e:
            print(f"WARN: blocks unavailable ({e}); crosswalk will use area fallback")

        n_hoods = load_neighborhoods(c, cfg)
        print(f"neighborhoods upserted: {n_hoods}")

        db.finish_dataset_version(c, vid, n_tracts + n_hoods)
        c.commit()
    return 0
