"""
QYNE v1 — Data Enricher Flow.

Adds computed fields to existing Directus items.
Runs retroactively on items that were stored before enrichment logic existed.

Schedule: On-demand or daily.
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def fetch_items_to_enrich(collection: str, filter_query: str = "", limit: int = 100) -> list[dict]:
    """Fetch items that need enrichment."""
    logger = get_run_logger()
    url = f"{DIRECTUS_URL}/items/{collection}?limit={limit}&sort=-date_created"
    if filter_query:
        url += f"&{filter_query}"
    resp = httpx.get(url, headers=HEADERS, timeout=15)
    items = resp.json().get("data", []) if resp.is_success else []
    logger.info(f"Fetched {len(items)} items from {collection} for enrichment")
    return items


@task
def enrich_contact(contact: dict) -> dict | None:
    """Enrich a contact with computed fields."""
    updates = {}

    # Auto-categorize by email domain
    email = contact.get("email", "")
    if email:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if domain in ("gmail.com", "hotmail.com", "yahoo.com", "outlook.com"):
            updates["notes"] = (contact.get("notes") or "") + " [personal-email]"
        elif domain:
            updates["notes"] = (contact.get("notes") or "") + f" [business:{domain}]"

    # Auto lead score boost if has company
    if contact.get("company") and (contact.get("lead_score") or 0) < 3:
        updates["lead_score"] = max(contact.get("lead_score") or 0, 3)

    return updates if updates else None


@task(retries=2, retry_delay_seconds=5)
def update_item(collection: str, item_id: int, updates: dict) -> bool:
    """Update an item in Directus."""
    resp = httpx.patch(
        f"{DIRECTUS_URL}/items/{collection}/{item_id}",
        json=updates,
        headers=HEADERS,
        timeout=10,
    )
    return resp.is_success


@flow(name="Data Enricher", log_prints=True)
def data_enricher(
    collection: str = "contacts",
    filter_query: str = "",
    limit: int = 100,
) -> dict:
    """Enrich existing items with computed fields."""
    items = fetch_items_to_enrich(collection, filter_query, limit)

    stats = {"processed": 0, "enriched": 0, "skipped": 0}
    for item in items:
        if collection == "contacts":
            updates = enrich_contact(item)
        else:
            updates = None

        if updates:
            success = update_item(collection, item["id"], updates)
            if success:
                stats["enriched"] += 1
            else:
                stats["skipped"] += 1
        else:
            stats["skipped"] += 1
        stats["processed"] += 1

    return stats


if __name__ == "__main__":
    data_enricher()
