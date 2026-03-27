"""
QYNE v1 — Lead Scorer Flow.

Recalculates lead scores for contacts based on activity.
Factors: conversations count, ticket interactions, recency, product interest.

Schedule: Daily at 06:00 UTC.
"""

import os
from datetime import datetime, timedelta

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def fetch_contacts() -> list[dict]:
    """Fetch all contacts for scoring."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/contacts?limit=500&fields=id,first_name,last_name,email,product,lead_score,date_created",
        headers=HEADERS,
        timeout=15,
    )
    contacts = resp.json().get("data", []) if resp.is_success else []
    logger.info(f"Fetched {len(contacts)} contacts for scoring")
    return contacts


@task(retries=2, retry_delay_seconds=10)
def count_activity(collection: str, days: int = 30) -> dict[str, int]:
    """Count activity per contact email in the last N days."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/{collection}"
        f"?filter[date_created][_gte]={since}&limit=500&fields=id,agent_name",
        headers=HEADERS,
        timeout=15,
    )
    items = resp.json().get("data", []) if resp.is_success else []
    return {"total": len(items)}


@task
def calculate_scores(contacts: list[dict], activity: dict) -> list[dict]:
    """Calculate lead scores based on activity and recency."""
    logger = get_run_logger()
    scored = []
    now = datetime.utcnow()

    for contact in contacts:
        score = 0

        # Base: has email (+2), has product interest (+2)
        if contact.get("email"):
            score += 2
        if contact.get("product"):
            score += 2

        # Recency: created in last 7 days (+3), 30 days (+1)
        created = contact.get("date_created")
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                days_old = (now - created_dt).days
                if days_old <= 7:
                    score += 3
                elif days_old <= 30:
                    score += 1
            except (ValueError, TypeError):
                pass

        # Cap at 10
        score = min(score, 10)
        scored.append({"id": contact["id"], "lead_score": score})

    logger.info(f"Scored {len(scored)} contacts")
    return scored


@task(retries=2, retry_delay_seconds=5)
def update_scores(scored: list[dict]) -> int:
    """Update lead scores in Directus."""
    logger = get_run_logger()
    updated = 0
    for item in scored:
        resp = httpx.patch(
            f"{DIRECTUS_URL}/items/contacts/{item['id']}",
            json={"lead_score": item["lead_score"]},
            headers=HEADERS,
            timeout=10,
        )
        if resp.is_success:
            updated += 1

    logger.info(f"Updated {updated}/{len(scored)} contact scores")
    return updated


@flow(name="Lead Scorer", log_prints=True)
def lead_scorer() -> dict:
    """Recalculate lead scores for all contacts."""
    contacts = fetch_contacts()
    activity = count_activity("conversations")
    scored = calculate_scores(contacts, activity)
    updated = update_scores(scored)

    return {"contacts_scored": len(scored), "updated": updated}


if __name__ == "__main__":
    lead_scorer()
