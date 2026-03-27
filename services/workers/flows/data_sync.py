"""
QYNE v1 — Data Sync Flow.

Syncs data between Directus collections or external APIs.
Use case: sync contacts from external CRM, update lead scores from analytics.

Schedule: Every hour.
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=15)
def fetch_directus_items(collection: str, filters: str = "") -> list[dict]:
    """Fetch items from a Directus collection."""
    logger = get_run_logger()
    url = f"{DIRECTUS_URL}/items/{collection}?limit=100&sort=-date_created"
    if filters:
        url += f"&{filters}"
    resp = httpx.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    items = resp.json().get("data", [])
    logger.info(f"Fetched {len(items)} items from {collection}")
    return items


@task(retries=2, retry_delay_seconds=10)
def upsert_directus_item(collection: str, item: dict) -> str:
    """Create or update an item in Directus."""
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/{collection}",
        json=item,
        headers=HEADERS,
        timeout=10,
    )
    if resp.is_success:
        return f"saved:{resp.json()['data']['id']}"
    return f"error:{resp.status_code}"


@task
def transform_for_sync(items: list[dict], field_map: dict[str, str]) -> list[dict]:
    """Map fields from source format to target format."""
    logger = get_run_logger()
    transformed = []
    for item in items:
        mapped = {}
        for src, dst in field_map.items():
            if src in item and item[src] is not None:
                mapped[dst] = item[src]
        if mapped:
            transformed.append(mapped)
    logger.info(f"Transformed {len(transformed)} items")
    return transformed


@flow(name="Data Sync", log_prints=True)
def data_sync(
    source_collection: str = "contacts",
    target_collection: str = "contacts",
    field_map: dict[str, str] | None = None,
    filters: str = "",
) -> dict:
    """Sync data between Directus collections or transform and reload.

    Args:
        source_collection: Collection to read from.
        target_collection: Collection to write to.
        field_map: Mapping of source fields to target fields.
        filters: Directus filter query string.
    """
    if field_map is None:
        field_map = {"first_name": "first_name", "last_name": "last_name", "email": "email"}

    items = fetch_directus_items(source_collection, filters)
    transformed = transform_for_sync(items, field_map)

    saved = 0
    for item in transformed:
        result = upsert_directus_item(target_collection, item)
        if result.startswith("saved"):
            saved += 1

    return {"source": source_collection, "fetched": len(items), "saved": saved}


if __name__ == "__main__":
    data_sync()
