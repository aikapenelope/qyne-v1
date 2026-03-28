"""
QYNE v1 — CSV Export Flow.

Exports any Directus collection to CSV file in RustFS.
Useful for external tools, spreadsheets, and data sharing.

Schedule: On-demand.
"""

import csv
import io
import os
from datetime import datetime

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
def fetch_all_items(collection: str, fields: str = "*", limit: int = 1000) -> list[dict]:
    """Fetch all items from a collection."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/{collection}?fields={fields}&limit={limit}&sort=-date_created",
        headers=HEADERS,
        timeout=30,
    )
    items = resp.json().get("data", []) if resp.is_success else []
    logger.info(f"Fetched {len(items)} items from {collection}")
    return items


@task
def items_to_csv(items: list[dict]) -> str:
    """Convert items to CSV string."""
    if not items:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=items[0].keys())
    writer.writeheader()
    for item in items:
        # Convert non-string values
        row = {}
        for k, v in item.items():
            if isinstance(v, (dict, list)):
                import json
                row[k] = json.dumps(v)
            else:
                row[k] = v
        writer.writerow(row)
    return output.getvalue()


@task(retries=2, retry_delay_seconds=10)
def upload_csv(csv_content: str, collection: str, bucket: str = "exports") -> str:
    """Upload CSV to RustFS."""
    logger = get_run_logger()
    if not RUSTFS_PASSWORD or not csv_content:
        return "skipped"

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{collection}_{timestamp}.csv"

    httpx.put(f"{RUSTFS_URL}/{bucket}", auth=(RUSTFS_USER, RUSTFS_PASSWORD), timeout=10)

    resp = httpx.put(
        f"{RUSTFS_URL}/{bucket}/{filename}",
        content=csv_content.encode("utf-8"),
        auth=(RUSTFS_USER, RUSTFS_PASSWORD),
        headers={"Content-Type": "text/csv"},
        timeout=30,
    )

    if resp.is_success:
        logger.info(f"Exported: {bucket}/{filename} ({len(csv_content)} bytes)")
        return f"{bucket}/{filename}"
    return f"error:{resp.status_code}"


@flow(name="CSV Export", log_prints=True)
def export_csv(
    collection: str = "contacts",
    fields: str = "*",
    bucket: str = "exports",
) -> dict:
    """Export a Directus collection to CSV in RustFS."""
    items = fetch_all_items(collection, fields)
    csv_content = items_to_csv(items)
    location = upload_csv(csv_content, collection, bucket)
    return {"collection": collection, "items": len(items), "location": location}


if __name__ == "__main__":
    export_csv()
