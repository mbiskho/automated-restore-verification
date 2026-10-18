# Automated Restore Verification

A backup you've never restored is a hope, not a backup. This job restores the latest Postgres backup into a throwaway database every night, checks the data is really there, and writes evidence: how old the backup was (RPO) and how long the restore took (RTO). Auditors and incident commanders can both read it.

```
latest backup (S3 or local) ──► restore into scratch DB ──► checks ──► evidence/2026-11-02.json + .md
                                     (timed: RTO)            │            backup age (RPO), pass/fail
                                                             └─► non-zero exit → alert
```

## Checks

| Check | Fails when |
|---|---|
| Backup age | newest backup older than `max_backup_age_hours` (RPO breach) |
| Restore time | restore takes longer than `max_restore_minutes` (RTO breach) |
| Tables present | an expected table is missing |
| Row counts | a table has fewer rows than `min_rows`, or dropped more than `max_shrink_pct` vs the last run |
| Freshness | the newest row in a table is older than expected (backup taken from a stale replica) |
| Queries | an application smoke query returns nothing or errors |

## Usage

```bash
pip install -e ".[dev]"
restorecheck run --config config.example.yaml      # restore + checks + evidence; exit 1 on any failure
restorecheck report evidence/                      # last 30 runs as a Markdown table
```

Run it nightly from cron or a Kubernetes CronJob. The scratch database is dropped at the end of every run, pass or fail.

## Layout

```
restorecheck/config.py    load + validate the YAML config
restorecheck/backup.py    find the newest backup (S3 prefix or folder), download it
restorecheck/restore.py   create scratch DB, pg_restore, drop afterwards (timed)
restorecheck/checks.py    checks as pure functions over query results
restorecheck/evidence.py  JSON + Markdown evidence, history table
restorecheck/cli.py       run / report
tests/                    check and evidence logic
```
