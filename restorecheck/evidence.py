from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .checks import Result


def write(folder: Path, started: datetime, backup_name: str, results: list[Result], row_counts: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    stamp = started.strftime("%Y-%m-%dT%H%M%SZ")
    passed = all(r.passed for r in results)
    doc = {"run_at": started.isoformat(), "backup": backup_name, "passed": passed,
           "results": [r.to_dict() for r in results], "row_counts": row_counts}
    path = folder / f"{stamp}.json"
    path.write_text(json.dumps(doc, indent=2))
    lines = [f"# Restore verification {started:%Y-%m-%d %H:%M} UTC", "",
             f"**Result:** {'PASS' if passed else 'FAIL'} · backup `{backup_name}`", "",
             "| Check | Target | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {r.check} | {r.target} | {'✅' if r.passed else '❌'} | {r.detail} |" for r in results]
    (folder / f"{stamp}.md").write_text("\n".join(lines) + "\n")
    return path


def previous_row_counts(folder: Path) -> dict[str, int]:
    runs = sorted(folder.glob("*.json"))
    return json.loads(runs[-1].read_text()).get("row_counts", {}) if runs else {}


def history(folder: Path, limit: int = 30) -> str:
    rows = ["| Run | Backup | Result | RPO | RTO |", "|---|---|---|---|---|"]
    for p in sorted(folder.glob("*.json"))[-limit:]:
        d = json.loads(p.read_text())
        get = lambda check: next((r["detail"] for r in d["results"] if r["check"] == check), "-")  # noqa: E731
        rows.append(f"| {d['run_at'][:16]} | {d['backup']} | {'PASS' if d['passed'] else 'FAIL'} | {get('rpo')} | {get('rto')} |")
    return "\n".join(rows)
