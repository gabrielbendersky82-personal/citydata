"""Smoke test: schema applies, DB round-trips."""
from etl import db


def run(city: str, extra: list[str]) -> int:
    with db.conn() as c:
        db.apply_schema(c)
        vid = db.ensure_dataset_version(c, "smoke", "v0", "smoke test")
        db.finish_dataset_version(c, vid, 0)
        c.commit()
        n = c.execute("select count(*) from dataset_versions where source='smoke'").fetchone()[0]
    print(f"smoke ok: dataset_versions rows={n}")
    return 0
