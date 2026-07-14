"""Local ETL database helpers: connection, dataset versioning, bulk upserts."""
from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Sequence

import psycopg
from psycopg import sql

LOCAL_DSN = os.environ.get("ETL_DATABASE_URL", "postgresql://etl:etl@localhost/citydata_etl")


@contextmanager
def conn() -> Iterator[psycopg.Connection]:
    with psycopg.connect(LOCAL_DSN) as c:
        yield c


def apply_schema(c: psycopg.Connection) -> None:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for path in (
        os.path.join(root, "supabase", "migrations", "0001_reference.sql"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_schema.sql"),
    ):
        with open(path) as f:
            c.execute(f.read())
    c.commit()


def ensure_dataset_version(
    c: psycopg.Connection, source: str, vintage_label: str, notes: str = ""
) -> int:
    """Get-or-create a dataset version; re-runs of the same vintage reuse the row."""
    row = c.execute(
        """
        insert into dataset_versions (source, vintage_label, notes)
        values (%s, %s, %s)
        on conflict (source, vintage_label)
        do update set retrieved_at = now(), notes = excluded.notes
        returning id
        """,
        (source, vintage_label, notes),
    ).fetchone()
    assert row is not None
    return int(row[0])


def finish_dataset_version(c: psycopg.Connection, version_id: int, row_count: int, payload_for_checksum: str = "") -> None:
    checksum = hashlib.sha256(payload_for_checksum.encode()).hexdigest()[:16] if payload_for_checksum else None
    c.execute(
        "update dataset_versions set row_count = %s, checksum = coalesce(%s, checksum) where id = %s",
        (row_count, checksum, version_id),
    )


def upsert_rows(
    c: psycopg.Connection,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    conflict_cols: Sequence[str],
    batch: int = 5000,
) -> int:
    """Idempotent batched upsert. Returns number of rows written."""
    cols = sql.SQL(", ").join(sql.Identifier(col) for col in columns)
    updates = sql.SQL(", ").join(
        sql.SQL("{} = excluded.{}").format(sql.Identifier(col), sql.Identifier(col))
        for col in columns
        if col not in conflict_cols
    )
    conflict = sql.SQL(", ").join(sql.Identifier(col) for col in conflict_cols)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
    stmt = sql.SQL(
        "insert into {} ({}) values ({}) on conflict ({}) do update set {}"
    ).format(sql.SQL(table), cols, placeholders, conflict, updates)

    n = 0
    buf: list[Sequence[Any]] = []
    with c.cursor() as cur:
        for r in rows:
            buf.append(r)
            if len(buf) >= batch:
                cur.executemany(stmt, buf)
                n += len(buf)
                buf = []
        if buf:
            cur.executemany(stmt, buf)
            n += len(buf)
    return n
