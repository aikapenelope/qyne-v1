"""
NEXUS Cerebro — Document ETL Flow (Prefect + Docling).

Deterministic document processing pipeline. NO AI involved in parsing.
Docling handles: PDF, DOCX, PPTX, XLSX, HTML, images, LaTeX, TXT.

Pipeline: Fetch from RustFS -> Parse with Docling -> Store in Directus -> Embed in pgvector.

Schedule: Triggered by n8n webhook when new files arrive, or on-demand.
"""

import os

import httpx
from prefect import flow, task
from prefect.logging import get_run_logger

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
AGNO_VECTOR_DB_URL = os.getenv("AGNO_VECTOR_DB_URL", "")


@task(retries=2, retry_delay_seconds=10)
def parse_document(file_path: str) -> dict:
    """Parse a document with Docling and return structured content."""
    from docling.document_converter import DocumentConverter
    from pathlib import Path

    logger = get_run_logger()
    logger.info(f"Parsing: {file_path}")

    converter = DocumentConverter()
    result = converter.convert(file_path)
    markdown = result.document.export_to_markdown()

    title = Path(file_path).stem.replace("-", " ").replace("_", " ").title()

    logger.info(f"Parsed {len(markdown)} chars from {file_path}")
    return {
        "title": title,
        "content": markdown,
        "source_file": Path(file_path).name,
    }


@task(retries=2, retry_delay_seconds=10)
def save_to_directus(doc: dict, collection: str = "documents") -> str:
    """Save parsed document to Directus via REST API."""
    if not DIRECTUS_TOKEN:
        return "skipped (no token)"

    logger = get_run_logger()
    headers = {
        "Authorization": f"Bearer {DIRECTUS_TOKEN}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(
        f"{DIRECTUS_URL}/items/{collection}",
        json={
            "title": doc["title"],
            "content": doc["content"][:50000],
            "source_file": doc["source_file"],
            "status": "indexed",
        },
        headers=headers,
        timeout=15,
    )

    if resp.is_success:
        logger.info(f"Saved to Directus: {doc['title']}")
        return "saved"
    else:
        logger.warning(f"Directus error {resp.status_code}: {resp.text[:200]}")
        return f"error ({resp.status_code})"


@task(retries=1)
def generate_embeddings(doc: dict) -> str:
    """Generate embeddings and store in pgvector for knowledge base search."""
    if not AGNO_VECTOR_DB_URL:
        return "skipped (no vector DB URL)"

    logger = get_run_logger()

    try:
        from agno.knowledge.knowledge import Knowledge
        from agno.knowledge.embedder.voyageai import VoyageAIEmbedder
        from agno.vectordb.pgvector import PgVector, SearchType

        embedder = VoyageAIEmbedder(id="voyage-3-lite", dimensions=512)
        vector_db = PgVector(
            table_name="nexus_knowledge",
            db_url=AGNO_VECTOR_DB_URL,
            search_type=SearchType.hybrid,
            embedder=embedder,
        )
        kb = Knowledge(vector_db=vector_db)
        kb.insert(
            content=doc["content"],
            metadata={"title": doc["title"], "source": doc["source_file"]},
        )
        logger.info(f"Embedded: {doc['title']}")
        return "indexed"
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return f"error ({e})"


@flow(name="Document ETL", log_prints=True)
def etl_documents(
    file_paths: list[str] | None = None,
    collection: str = "documents",
) -> dict:
    """Process documents: parse with Docling, store in Directus, embed in pgvector.

    Args:
        file_paths: List of local file paths to process.
        collection: Directus collection to store results.
    """
    if not file_paths:
        return {"processed": 0, "message": "No files provided"}

    results = []
    for path in file_paths:
        doc = parse_document(path)
        directus_status = save_to_directus(doc, collection)
        embed_status = generate_embeddings(doc)
        results.append({
            "file": path,
            "title": doc["title"],
            "chars": len(doc["content"]),
            "directus": directus_status,
            "embeddings": embed_status,
        })

    return {"processed": len(results), "results": results}


if __name__ == "__main__":
    etl_documents()
