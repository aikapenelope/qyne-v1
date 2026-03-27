"""
QYNE v1 — Database Backup Flow (Prefect).

Deterministic backup pipeline. NO AI involved.
Dumps PostgreSQL databases and uploads to RustFS (S3).

Schedule: Daily at 03:00 UTC.
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
RUSTFS_URL = os.getenv("RUSTFS_URL", "http://rustfs:9000")
RUSTFS_USER = os.getenv("RUSTFS_USER", "qyne")
RUSTFS_PASSWORD = os.getenv("RUSTFS_PASSWORD", "")
BACKUP_DIR = Path("/tmp/backups")


@task(retries=2, retry_delay_seconds=30)
def dump_database(db_name: str) -> str:
    """Dump a PostgreSQL database to a SQL file."""
    logger = get_run_logger()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{db_name}_{timestamp}.sql.gz"
    filepath = BACKUP_DIR / filename

    env = {**os.environ, "PGPASSWORD": POSTGRES_PASSWORD}
    cmd = (
        f"pg_dump -h {POSTGRES_HOST} -U {POSTGRES_USER} -d {db_name} "
        f"--no-owner --no-privileges | gzip > {filepath}"
    )

    result = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"pg_dump failed: {result.stderr}")

    size_mb = filepath.stat().st_size / (1024 * 1024)
    logger.info(f"Dumped {db_name}: {filename} ({size_mb:.1f} MB)")
    return str(filepath)


@task(retries=2, retry_delay_seconds=10)
def upload_to_rustfs(filepath: str, bucket: str = "backups") -> str:
    """Upload backup file to RustFS via S3 API."""
    logger = get_run_logger()

    if not RUSTFS_PASSWORD:
        logger.warning("RUSTFS_PASSWORD not set, skipping upload")
        return "skipped"

    filename = Path(filepath).name

    # Ensure bucket exists
    httpx.put(
        f"{RUSTFS_URL}/{bucket}",
        auth=(RUSTFS_USER, RUSTFS_PASSWORD),
        timeout=10,
    )

    # Upload file
    with open(filepath, "rb") as f:
        resp = httpx.put(
            f"{RUSTFS_URL}/{bucket}/{filename}",
            content=f.read(),
            auth=(RUSTFS_USER, RUSTFS_PASSWORD),
            timeout=60,
        )

    if resp.is_success:
        logger.info(f"Uploaded to RustFS: {bucket}/{filename}")
        return f"{bucket}/{filename}"
    else:
        raise RuntimeError(f"Upload failed: {resp.status_code}")


@task
def cleanup_local(filepath: str) -> None:
    """Remove local backup file after upload."""
    Path(filepath).unlink(missing_ok=True)


@flow(name="Database Backup", log_prints=True)
def database_backup(
    databases: list[str] | None = None,
    bucket: str = "backups",
) -> dict:
    """Backup PostgreSQL databases to RustFS.

    Args:
        databases: List of database names. Defaults to directus_db + prefect_db.
        bucket: RustFS bucket name.
    """
    if databases is None:
        databases = ["directus_db", "prefect_db"]

    results = []
    for db_name in databases:
        filepath = dump_database(db_name)
        location = upload_to_rustfs(filepath, bucket)
        cleanup_local(filepath)
        results.append({"database": db_name, "location": location})

    return {"backups": len(results), "results": results}


if __name__ == "__main__":
    database_backup()
