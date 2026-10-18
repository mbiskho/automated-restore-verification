"""Checks as pure functions: inputs are numbers already queried, output is a Result."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

from .config import TableExpect


@dataclass
class Result:
    check: str
    target: str
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def backup_age(taken_at: datetime, now: datetime, max_hours: float) -> Result:
    age = (now - taken_at).total_seconds() / 3600
    return Result("rpo", "backup age", age <= max_hours, f"{age:.1f}h old (limit {max_hours:g}h)")


def restore_time(seconds: float, max_minutes: float) -> Result:
    mins = seconds / 60
    return Result("rto", "restore duration", mins <= max_minutes, f"{mins:.1f} min (limit {max_minutes:g} min)")


def table(name: str, exp: TableExpect, rows: int | None, previous_rows: int | None,
          newest: datetime | None, now: datetime) -> list[Result]:
    if rows is None:
        return [Result("table", name, False, "table missing from restore")]
    out = [Result("rows", name, rows >= exp.min_rows, f"{rows:,} rows (min {exp.min_rows:,})")]
    if exp.max_shrink_pct is not None and previous_rows:
        shrink = (previous_rows - rows) / previous_rows * 100
        out.append(Result("shrink", name, shrink <= exp.max_shrink_pct,
                          f"{shrink:+.1f}% vs last run ({previous_rows:,} → {rows:,}; limit {exp.max_shrink_pct:g}%)"))
    if exp.fresh_column and exp.max_age_hours is not None:
        if newest is None:
            out.append(Result("freshness", name, False, f"no values in {exp.fresh_column}"))
        else:
            age = (now - newest).total_seconds() / 3600
            out.append(Result("freshness", name, age <= exp.max_age_hours,
                              f"newest {exp.fresh_column} is {age:.1f}h old (limit {exp.max_age_hours:g}h)"))
    return out


def query(name: str, value: float | None, min_value: float) -> Result:
    if value is None:
        return Result("query", name, False, "returned no rows")
    return Result("query", name, value >= min_value, f"returned {value:g} (min {min_value:g})")
