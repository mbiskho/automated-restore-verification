from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TableExpect:
    min_rows: int = 1
    max_shrink_pct: float | None = None
    fresh_column: str | None = None
    max_age_hours: float | None = None


@dataclass
class Config:
    source: str
    pattern: str
    max_backup_age_hours: float
    admin_dsn: str
    max_restore_minutes: float
    jobs: int
    tables: dict[str, TableExpect]
    queries: list[dict] = field(default_factory=list)
    evidence_dir: Path = Path("evidence")


def load(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    dsn_var = raw["restore"]["admin_dsn_env"]
    dsn = os.environ.get(dsn_var)
    if not dsn:
        raise SystemExit(f"set {dsn_var} to the scratch server's admin DSN")
    return Config(
        source=raw["backup"]["source"],
        pattern=raw["backup"].get("pattern", "*.dump"),
        max_backup_age_hours=float(raw["backup"]["max_backup_age_hours"]),
        admin_dsn=dsn,
        max_restore_minutes=float(raw["restore"]["max_restore_minutes"]),
        jobs=int(raw["restore"].get("jobs", 2)),
        tables={name: TableExpect(**(spec or {})) for name, spec in raw["expect"]["tables"].items()},
        queries=raw["expect"].get("queries", []),
        evidence_dir=Path(raw.get("evidence_dir", "evidence")),
    )
