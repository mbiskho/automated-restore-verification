from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from . import checks, evidence
from .backup import newest
from .config import load
from .restore import restore, scratch_database


def run(config_path: str) -> int:
    cfg = load(config_path)
    started = datetime.now(timezone.utc)
    backup = newest(cfg.source, cfg.pattern)
    results = [checks.backup_age(backup.taken_at, started, cfg.max_backup_age_hours)]
    previous = evidence.previous_row_counts(cfg.evidence_dir)
    counts: dict[str, int] = {}

    with scratch_database(cfg.admin_dsn) as dsn:
        try:
            seconds = restore(str(backup.local_path), dsn, cfg.jobs)
            results.append(checks.restore_time(seconds, cfg.max_restore_minutes))
        except Exception as e:  # a failed restore is a result, not a crash
            results.append(checks.Result("restore", backup.name, False, f"pg_restore failed: {str(e)[:300]}"))
        else:
            with psycopg.connect(dsn) as conn:
                existing = {r[0] for r in conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")}
                now = datetime.now(timezone.utc)
                for name, exp in cfg.tables.items():
                    rows = newest_value = None
                    if name in existing:
                        rows = conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
                        counts[name] = rows
                        if exp.fresh_column:
                            newest_value = conn.execute(f'SELECT max("{exp.fresh_column}") FROM "{name}"').fetchone()[0]
                    results += checks.table(name, exp, rows, previous.get(name), newest_value, now)
                for q in cfg.queries:
                    try:
                        row = conn.execute(q["sql"]).fetchone()
                        value = None if row is None or row[0] is None else float(row[0])
                    except psycopg.Error as e:
                        conn.rollback()
                        results.append(checks.Result("query", q["name"], False, f"error: {e}"))
                        continue
                    results.append(checks.query(q["name"], value, q.get("min_value", 1)))

    path = evidence.write(cfg.evidence_dir, started, backup.name, results, counts)
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.check:<9} {r.target:<28} {r.detail}")
    print(f"evidence: {path}")
    return 0 if all(r.passed for r in results) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="restorecheck")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run").add_argument("--config", required=True)
    sub.add_parser("report").add_argument("folder", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return run(a.config)
    print(evidence.history(a.folder))
    return 0


if __name__ == "__main__":
    sys.exit(main())
