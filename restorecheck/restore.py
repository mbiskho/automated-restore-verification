from __future__ import annotations

import os
import subprocess
import time
import uuid
from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo


@contextmanager
def scratch_database(admin_dsn: str) -> Iterator[str]:
    """Create a uniquely named database and always drop it afterwards."""
    name = f"restorecheck_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{name}"')
    try:
        yield make_conninfo(admin_dsn, dbname=name)
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


def restore(dump_path: str, target_dsn: str, jobs: int) -> float:
    """pg_restore into target; returns elapsed seconds. Raises on failure."""
    params = conninfo_to_dict(target_dsn)
    start = time.monotonic()
    subprocess.run(
        ["pg_restore", "--no-owner", "--no-privileges", "--exit-on-error", f"--jobs={jobs}",
         "--dbname", target_dsn, dump_path],
        check=True, capture_output=True, text=True,
        env={**os.environ, "PGPASSWORD": str(params.get("password", ""))},
    )
    return time.monotonic() - start
