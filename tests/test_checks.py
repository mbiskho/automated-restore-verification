from datetime import datetime, timedelta, timezone

from restorecheck import checks, evidence
from restorecheck.config import TableExpect

NOW = datetime(2026, 11, 2, 3, 0, tzinfo=timezone.utc)


def test_rpo_and_rto():
    assert checks.backup_age(NOW - timedelta(hours=20), NOW, 26).passed
    assert not checks.backup_age(NOW - timedelta(hours=30), NOW, 26).passed
    assert checks.restore_time(30 * 60, 45).passed
    assert not checks.restore_time(50 * 60, 45).passed


def test_missing_table_fails_alone():
    [r] = checks.table("orders", TableExpect(min_rows=10), None, None, None, NOW)
    assert not r.passed and "missing" in r.detail


def test_shrink_and_freshness():
    exp = TableExpect(min_rows=100, max_shrink_pct=5, fresh_column="updated_at", max_age_hours=30)
    ok = checks.table("t", exp, 1000, 1010, NOW - timedelta(hours=2), NOW)
    assert all(r.passed for r in ok)
    bad = {r.check: r for r in checks.table("t", exp, 800, 1000, NOW - timedelta(hours=72), NOW)}
    assert not bad["shrink"].passed and not bad["freshness"].passed and bad["rows"].passed


def test_query_result():
    assert checks.query("q", 5, 1).passed
    assert not checks.query("q", None, 1).passed


def test_evidence_roundtrip(tmp_path):
    results = [checks.backup_age(NOW - timedelta(hours=1), NOW, 26), checks.restore_time(60, 45)]
    evidence.write(tmp_path, NOW, "prod-2026-11-02.dump", results, {"orders": 123})
    assert evidence.previous_row_counts(tmp_path) == {"orders": 123}
    assert "PASS" in evidence.history(tmp_path)
