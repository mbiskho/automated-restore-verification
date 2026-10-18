from __future__ import annotations

import fnmatch
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Backup:
    name: str
    taken_at: datetime   # object/file modification time, UTC
    local_path: Path


def newest(source: str, pattern: str) -> Backup:
    if source.startswith("s3://"):
        import boto3

        bucket, _, prefix = source[5:].partition("/")
        s3 = boto3.client("s3")
        objs = [o for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
                for o in page.get("Contents", []) if fnmatch.fnmatch(o["Key"].rsplit("/", 1)[-1], pattern)]
        if not objs:
            raise FileNotFoundError(f"no backups matching {pattern} under {source}")
        latest = max(objs, key=lambda o: o["LastModified"])
        dest = Path(tempfile.mkdtemp()) / latest["Key"].rsplit("/", 1)[-1]
        s3.download_file(bucket, latest["Key"], str(dest))
        return Backup(latest["Key"], latest["LastModified"].astimezone(timezone.utc), dest)

    files = [p for p in Path(source).glob(pattern) if p.is_file()]
    if not files:
        raise FileNotFoundError(f"no backups matching {pattern} in {source}")
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return Backup(latest.name, datetime.fromtimestamp(latest.stat().st_mtime, timezone.utc), latest)
