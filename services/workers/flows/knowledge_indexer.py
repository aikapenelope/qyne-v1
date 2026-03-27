"""
QYNE v1 — Knowledge Indexer Flow.

Re-indexes the knowledge base with new documents from Directus.
Fetches documents with status='pending', generates embeddings, updates status.

Schedule: On-demand (triggered by n8n when new documents arrive).
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {DIRECTUS_TOKEN}", "Content-Type": "application/json"}


@task(retries=2, retry_delay_seconds=10)
def fetch_pending_documents() -> list[dict]:
    """Fetch documents with status='pending' from Directus."""
    logger = get_run_logger()
    resp = httpx.get(
        f"{DIRECTUS_URL}/items/documents?filter[status][_eq]=pending&limit=50",
        headers=HEADERS,
        timeout=10,
    )
    docs = resp.json().get("data", []) if resp.is_success else []
    logger.info(f"Found {len(docs)} pending documents")
    return docs


@task(retries=1)
def index_document(doc: dict) -> str:
    """Generate embeddings for a document and store in LanceDB."""
    logger = get_run_logger()
    content = doc.get("content", "")
    title = doc.get("title", "unknown")

    if not content or len(content) < 50:
        logger.warning(f"Skipping {title}: content too short ({len(content)} chars)")
        return "skipped"

    try:
        from agno.knowledge.knowledge import Knowledge
        from agno.knowledge.embedder.voyageai import VoyageAIEmbedder
        from agno.vectordb.lancedb import LanceDb, SearchType

        embedder = VoyageAIEmbedder(id="voyage-3-lite", dimensions=512)
        vector_db = LanceDb(
            uri="/app/data/lancedb",
            table_name="nexus_knowledge",
            search_type=SearchType.hybrid,
            embedder=embedder,
        )
        kb = Knowledge(vector_db=vector_db)
        kb.insert(
            content=content,
            metadata={"title": title, "source": doc.get("source_file", "directus")},
        )
        logger.info(f"Indexed: {title} ({len(content)} chars)")
        return "indexed"
    except Exception as e:
        logger.error(f"Indexing error for {title}: {e}")
        return f"error:{e}"


@task(retries=2, retry_delay_seconds=5)
def update_document_status(doc_id: int, status: str) -> None:
    """Update document status in Directus after indexing."""
    httpx.patch(
        f"{DIRECTUS_URL}/items/documents/{doc_id}",
        json={"status": status},
        headers=HEADERS,
        timeout=10,
    )


@flow(name="Knowledge Indexer", log_prints=True)
def knowledge_indexer() -> dict:
    """Index pending documents from Directus into LanceDB knowledge base."""
    docs = fetch_pending_documents()

    results = {"indexed": 0, "skipped": 0, "errors": 0}
    for doc in docs:
        status = index_document(doc)
        if status == "indexed":
            update_document_status(doc["id"], "indexed")
            results["indexed"] += 1
        elif status == "skipped":
            results["skipped"] += 1
        else:
            update_document_status(doc["id"], "error")
            results["errors"] += 1

    return results


if __name__ == "__main__":
    knowledge_indexer()
