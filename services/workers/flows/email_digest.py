"""
QYNE v1 — Email Digest Flow.

Sends a daily summary of activity to the team via email or Directus events.
Summarizes: new contacts, open tickets, pending tasks, conversations.

Schedule: Daily at 08:00 UTC.
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
def get_recent_items(collection: str, since: str, limit: int = 10) -> list[dict]:
    """Get recent items from a collection."""
    url = (
        f"{DIRECTUS_URL}/items/{collection}"
        f"?limit={limit}&sort=-date_created&filter[date_created][_gte]={since}"
    )
    resp = httpx.get(url, headers=HEADERS, timeout=10)
    return resp.json().get("data", []) if resp.is_success else []


@task
def build_digest(data: dict) -> str:
    """Build a daily digest summary."""
    lines = [
        f"# QYNE Daily Digest — {data['date']}",
        "",
        f"## New Contacts ({len(data['contacts'])})",
    ]
    for c in data["contacts"][:5]:
        name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        lines.append(f"- {name or 'Sin nombre'} ({c.get('email', 'sin email')})")

    lines.extend(["", f"## Open Tickets ({len(data['tickets'])})"])
    for t in data["tickets"][:5]:
        lines.append(f"- [{t.get('urgency', '?')}] {t.get('product', '?')}: {t.get('summary', '')[:60]}")

    lines.extend(["", f"## Pending Tasks ({len(data['tasks'])})"])
    for t in data["tasks"][:5]:
        lines.append(f"- {t.get('title', 'Sin titulo')}")

    lines.extend(["", f"## Conversations ({len(data['conversations'])})"])
    for c in data["conversations"][:3]:
        lines.append(f"- [{c.get('channel', '?')}] {c.get('intent', 'general')}")

    return "\n".join(lines)


@task(retries=1)
def save_digest(digest: str) -> str:
    """Save digest to Directus events."""
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/events",
        json={"type": "daily_digest", "payload": {"digest": digest}},
        headers=HEADERS,
        timeout=10,
    )
    return "saved" if resp.is_success else f"error:{resp.status_code}"


@flow(name="Daily Digest", log_prints=True)
def daily_digest(hours_back: int = 24) -> dict:
    """Generate and save a daily activity digest."""
    since = (datetime.utcnow() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT00:00:00")

    data = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "contacts": get_recent_items("contacts", since),
        "tickets": get_recent_items("tickets", since),
        "tasks": get_recent_items("tasks", since),
        "conversations": get_recent_items("conversations", since),
    }

    digest = build_digest(data)
    status = save_digest(digest)

    return {"digest_length": len(digest), "save_status": status}


if __name__ == "__main__":
    daily_digest()
