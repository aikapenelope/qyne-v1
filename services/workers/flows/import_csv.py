"""
QYNE v1 — CSV Import Flow.

Imports CSV data from RustFS into any Directus collection.
Validates each row before inserting.

Schedule: On-demand.
"""

import csv
import io
import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
RUSTFS_URL = os.getenv("RUSTFS_URL", "http://rustfs:9000")
RUSTFS_USER = os.getenv("RUSTFS_USER", "qyne")
RUSTFS_PASSWORD = os.getenv("RUSTFS_PASSWORD", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def download_csv(bucket: str, filename: str) -> list[dict]:
    """Download and parse CSV from RustFS."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{RUSTFS_URL}/{bucket}/{filename}",
        auth=(RUSTFS_USER, RUSTFS_PASSWORD),
        timeout=30,
    )
    if not resp.is_success:
        logger.error(f"Failed to download {bucket}/{filename}: {resp.status_code}")
        return []

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    logger.info(f"Parsed {len(rows)} rows from {filename}")
    return rows


@task
def validate_row(row: dict, required_fields: list[str]) -> tuple[bool, dict]:
    """Validate a CSV row."""
    cleaned = {}
    for k, v in row.items():
        if v is not None and str(v).strip():
            cleaned[k] = str(v).strip()

    for field in required_fields:
        if field not in cleaned:
            return False, cleaned

    return True, cleaned


@task(retries=2, retry_delay_seconds=5)
def insert_row(collection: str, row: dict) -> bool:
    """Insert a row into Directus."""
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/{collection}",
        json=row,
        headers=HEADERS,
        timeout=10,
    )
    return resp.is_success


@flow(name="CSV Import", log_prints=True)
def import_csv(
    bucket: str = "exports",
    filename: str = "",
    collection: str = "contacts",
    required_fields: list[str] | None = None,
) -> dict:
    """Import CSV from RustFS into a Directus collection."""
    if not filename:
        return {"error": "filename is required"}

    required = required_fields or ["first_name"]
    rows = download_csv(bucket, filename)

    stats = {"total": len(rows), "valid": 0, "imported": 0, "skipped": 0}
    for row in rows:
        is_valid, cleaned = validate_row(row, required)
        if not is_valid:
            stats["skipped"] += 1
            continue
        stats["valid"] += 1

        if insert_row(collection, cleaned):
            stats["imported"] += 1
        else:
            stats["skipped"] += 1

    return stats


if __name__ == "__main__":
    import_csv()
