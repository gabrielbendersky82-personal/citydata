"""Export serving tables as idempotent SQL files for Supabase.

The sandbox can't open TCP to Supabase and project provisioning is
interactive, so the ETL emits plain SQL under etl/out/supabase/ — applied
later via the Supabase MCP (execute_sql) or psql. Explicit ids are preserved
so cross-table FKs survive; sequences are bumped afterwards.
"""
from __future__ import annotations

import os

from etl import db

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "out", "supabase")

# table -> (columns, conflict key, geometry columns, where)
EXPORTS: dict[str, tuple[list[str], list[str], list[str], str]] = {
    "cities": (["id", "slug", "name", "state", "place_geoid", "status"], ["id"], [], ""),
    "dataset_versions": (["id", "source", "vintage_label", "retrieved_at", "row_count", "checksum", "notes"], ["source", "vintage_label"], [], ""),
    "metric_definitions": (["key", "label", "description", "units", "criterion", "higher_is_better", "default_intra_weight", "source", "source_attribution", "methodology_url"], ["key"], [], ""),
    "tracts": (["geoid", "city_id", "geom", "aland", "awater", "pop_2020"], ["geoid"], ["geom"], "where city_id is not null"),
    "neighborhoods": (["id", "city_id", "slug", "name", "geom", "geom_display", "centroid_pop", "boundary_source", "source_ref", "is_fallback_tract"], ["city_id", "slug"], ["geom", "geom_display", "centroid_pop"], ""),
    "tract_neighborhood_xwalk": (["neighborhood_id", "tract_geoid", "pop_weight", "block_count", "built_from"], ["neighborhood_id", "tract_geoid"], [], ""),
    "zip_tract_xwalk": (["zip", "tract_geoid", "res_ratio", "vintage"], ["zip", "tract_geoid", "vintage"], [], ""),
    "tract_metrics": (["tract_geoid", "metric_key", "value", "moe", "dataset_version_id"], ["tract_geoid", "metric_key", "dataset_version_id"], [], ""),
    "neighborhood_metrics": (["neighborhood_id", "metric_key", "value", "percentile", "coverage", "confidence", "dataset_version_id"], ["neighborhood_id", "metric_key", "dataset_version_id"], [], ""),
    "city_bundles": (["city_id", "built_at", "version_set", "bundle", "is_current"], ["city_id", "built_at"], [], "where is_current"),
}

BATCH = 500


def sql_literal(v, is_geom: bool) -> str:
    if v is None:
        return "null"
    if is_geom:
        return f"'{v}'::geometry"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v).replace("'", "''")
    return f"'{s}'"


def run(city: str, extra: list[str]) -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    with db.conn() as c:
        for i, (table, (cols, conflict, geoms, where)) in enumerate(EXPORTS.items()):
            select_cols = ", ".join(f"ST_AsEWKT({col})" if col in geoms else col for col in cols)
            rows = c.execute(f"select {select_cols} from {table} {where}").fetchall()
            path = os.path.join(OUT_DIR, f"{i:02d}_{table}.sql")
            update_cols = [col for col in cols if col not in conflict]
            with open(path, "w") as f:
                f.write(f"-- {table}: {len(rows)} rows (generated; idempotent)\n")
                for start in range(0, len(rows), BATCH):
                    chunk = rows[start:start + BATCH]
                    values = ",\n".join(
                        "(" + ", ".join(sql_literal(v, cols[j] in geoms) for j, v in enumerate(r)) + ")"
                        for r in chunk
                    )
                    updates = ", ".join(f"{col} = excluded.{col}" for col in update_cols)
                    f.write(
                        f"insert into {table} ({', '.join(cols)}) values\n{values}\n"
                        f"on conflict ({', '.join(conflict)}) do update set {updates};\n"
                    )
                if table in ("dataset_versions", "neighborhoods"):
                    seq = "dataset_versions_id_seq" if table == "dataset_versions" else "neighborhoods_id_seq"
                    f.write(f"select setval('{seq}', (select coalesce(max(id), 1) from {table}));\n")
            print(f"  {table}: {len(rows)} rows -> {path} ({os.path.getsize(path) // 1024} KB)")
    print("export complete")
    return 0
