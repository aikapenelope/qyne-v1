"""
QYNE v1 — Sentiment Analyzer Flow.

Batch-analyzes conversation sentiment using a lightweight model.
Updates conversations in Directus with sentiment scores.

Schedule: Daily or on-demand.
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def fetch_unscored_conversations(limit: int = 100) -> list[dict]:
    """Fetch conversations without sentiment analysis."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/conversations"
        f"?filter[sentiment][_null]=true&limit={limit}&sort=-date_created"
        f"&fields=id,raw_message,agent_response",
        headers=HEADERS,
        timeout=15,
    )
    items = resp.json().get("data", []) if resp.is_success else []
    logger.info(f"Found {len(items)} conversations without sentiment")
    return items


@task
def analyze_sentiment(text: str) -> str:
    """Simple keyword-based sentiment analysis. No LLM needed."""
    if not text:
        return "neutral"

    text_lower = text.lower()

    positive_words = [
        "gracias", "excelente", "perfecto", "genial", "bueno", "bien",
        "encanta", "feliz", "satisfecho", "recomiendo", "rapido", "facil",
        "thank", "great", "excellent", "perfect", "good", "love", "happy",
    ]
    negative_words = [
        "problema", "error", "malo", "terrible", "lento", "dificil",
        "queja", "molesto", "frustrado", "no funciona", "falla", "peor",
        "problem", "bad", "terrible", "slow", "difficult", "angry", "broken",
    ]

    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    if pos_count > neg_count:
        return "positive"
    elif neg_count > pos_count:
        return "negative"
    return "neutral"


@task(retries=2, retry_delay_seconds=5)
def update_sentiment(conversation_id: int, sentiment: str) -> bool:
    """Update conversation sentiment in Directus."""
    resp = httpx.patch(
        f"{DIRECTUS_URL}/items/conversations/{conversation_id}",
        json={"sentiment": sentiment},
        headers=HEADERS,
        timeout=10,
    )
    return resp.is_success


@flow(name="Sentiment Analyzer", log_prints=True)
def sentiment_analyzer(limit: int = 100) -> dict:
    """Analyze sentiment of unscored conversations."""
    conversations = fetch_unscored_conversations(limit)

    stats = {"processed": 0, "positive": 0, "neutral": 0, "negative": 0}
    for conv in conversations:
        text = (conv.get("raw_message") or "") + " " + (conv.get("agent_response") or "")
        sentiment = analyze_sentiment(text)
        update_sentiment(conv["id"], sentiment)
        stats["processed"] += 1
        stats[sentiment] += 1

    return stats


if __name__ == "__main__":
    sentiment_analyzer()
