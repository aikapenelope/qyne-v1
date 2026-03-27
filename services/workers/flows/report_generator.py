"""
QYNE v1 — Report Generator Flow.

Generates weekly business reports from Directus data.
Aggregates contacts, tickets, conversations by product and time period.

Schedule: Weekly (Monday 8:00 UTC).
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
def count_items(collection: str, since: str) -> int:
    """Count items created since a given date."""
    url = (
        f"{DIRECTUS_URL}/items/{collection}"
        f"?aggregate[count]=id&filter[date_created][_gte]={since}"
    )
    resp = httpx.get(url, headers=HEADERS, timeout=10)
    if resp.is_success:
        data = resp.json().get("data", [])
        return data[0].get("count", {}).get("id", 0) if data else 0
    return 0


@task(retries=2, retry_delay_seconds=10)
def count_by_field(collection: str, field: str, since: str) -> dict[str, int]:
    """Count items grouped by a field value."""
    url = (
        f"{DIRECTUS_URL}/items/{collection}"
        f"?aggregate[count]=id&groupBy[]={field}&filter[date_created][_gte]={since}"
    )
    resp = httpx.get(url, headers=HEADERS, timeout=10)
    if resp.is_success:
        data = resp.json().get("data", [])
        return {row.get(field, "unknown"): row.get("count", {}).get("id", 0) for row in data}
    return {}


@task
def build_report(metrics: dict) -> str:
    """Build a markdown report from collected metrics."""
    logger = get_run_logger()
    lines = [
        f"# QYNE Weekly Report",
        f"**Period**: {metrics['since']} to {metrics['until']}",
        "",
        "## Summary",
        f"- New contacts: **{metrics['contacts']}**",
        f"- New tickets: **{metrics['tickets']}**",
        f"- Conversations: **{metrics['conversations']}**",
        f"- Payments: **{metrics['payments']}**",
        f"- Tasks created: **{metrics['tasks']}**",
        "",
        "## Tickets by Product",
    ]
    for product, count in metrics.get("tickets_by_product", {}).items():
        lines.append(f"- {product}: {count}")

    lines.extend(["", "## Tickets by Urgency"])
    for urgency, count in metrics.get("tickets_by_urgency", {}).items():
        lines.append(f"- {urgency}: {count}")

    report = "\n".join(lines)
    logger.info(f"Report generated: {len(report)} chars")
    return report


@task(retries=1)
def save_report(report: str, since: str) -> str:
    """Save report to Directus events collection."""
    resp = httpx.post(
        f"{DIRECTUS_URL}/items/events",
        json={"type": "weekly_report", "payload": {"report": report, "period": since}},
        headers=HEADERS,
        timeout=10,
    )
    return "saved" if resp.is_success else f"error:{resp.status_code}"


@flow(name="Weekly Report", log_prints=True)
def weekly_report(days_back: int = 7) -> dict:
    """Generate a weekly business report from Directus data."""
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    until = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")

    metrics = {
        "since": since,
        "until": until,
        "contacts": count_items("contacts", since),
        "tickets": count_items("tickets", since),
        "conversations": count_items("conversations", since),
        "payments": count_items("payments", since),
        "tasks": count_items("tasks", since),
        "tickets_by_product": count_by_field("tickets", "product", since),
        "tickets_by_urgency": count_by_field("tickets", "urgency", since),
    }

    report = build_report(metrics)
    status = save_report(report, since)

    return {"period_days": days_back, "report_length": len(report), "save_status": status}


if __name__ == "__main__":
    weekly_report()
