"""
NEXUS Cerebro — Docling Document Processing Tool.

Gives AI agents the ability to parse documents on-demand.
Supports PDF, DOCX, PPTX, XLSX, HTML, images, and more.
Extracts structured text (Markdown) ready for knowledge base ingestion.

Usage: A user uploads a PDF via WhatsApp or CopilotKit, the agent
processes it with Docling and can answer questions about its content.
"""

import os
import tempfile
from pathlib import Path

import httpx

from agno.tools.decorator import tool

from app.config import DIRECTUS_URL, DIRECTUS_TOKEN, db, knowledge_base, embedder

_HEADERS = {
    "Authorization": f"Bearer {DIRECTUS_TOKEN}",
    "Content-Type": "application/json",
}


@tool()
def parse_document(file_path: str) -> str:
    """Parse a document file and return its content as Markdown.

    Supports: PDF, DOCX, PPTX, XLSX, HTML, images (PNG, JPEG, TIFF), LaTeX, TXT.
    Uses Docling for advanced PDF understanding (tables, formulas, layout).

    Args:
        file_path: Local path to the document file.

    Returns:
        Markdown text extracted from the document (truncated to 8000 chars).
    """
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)
        markdown = result.document.export_to_markdown()
        return markdown[:8000]
    except ImportError:
        return "ERROR: docling is not installed. Install with: pip install docling"
    except Exception as e:
        return f"ERROR parsing document: {e}"


@tool()
def parse_document_from_url(url: str) -> str:
    """Parse a document from a URL and return its content as Markdown.

    Works with direct file URLs (PDF, DOCX, etc.) and web pages (HTML).

    Args:
        url: URL of the document to parse.

    Returns:
        Markdown text extracted from the document (truncated to 8000 chars).
    """
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(url)
        markdown = result.document.export_to_markdown()
        return markdown[:8000]
    except ImportError:
        return "ERROR: docling is not installed. Install with: pip install docling"
    except Exception as e:
        return f"ERROR parsing document from URL: {e}"


@tool()
def parse_and_index_document(
    file_path: str,
    collection: str = "documents",
    title: str = "",
) -> str:
    """Parse a document, save its content to Directus, and index it in the knowledge base.

    This is the full pipeline: parse -> store in Directus -> generate embeddings -> pgvector.
    Use this when a document should become part of the permanent knowledge base.

    Args:
        file_path: Local path to the document file.
        collection: Directus collection to store the parsed content.
        title: Optional title for the document. Auto-detected from filename if empty.
    """
    # Step 1: Parse with Docling
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(file_path)
        markdown = result.document.export_to_markdown()
    except ImportError:
        return "ERROR: docling is not installed. Install with: pip install docling"
    except Exception as e:
        return f"ERROR parsing document: {e}"

    if not title:
        title = Path(file_path).stem.replace("-", " ").replace("_", " ").title()

    # Step 2: Save to Directus
    if DIRECTUS_TOKEN:
        try:
            resp = httpx.post(
                f"{DIRECTUS_URL}/items/{collection}",
                json={
                    "title": title,
                    "content": markdown[:50000],
                    "source_file": Path(file_path).name,
                    "status": "indexed",
                },
                headers=_HEADERS,
                timeout=15,
            )
            directus_status = "saved" if resp.is_success else f"error ({resp.status_code})"
        except Exception as e:
            directus_status = f"error ({e})"
    else:
        directus_status = "skipped (no token)"

    # Step 3: Index in knowledge base (pgvector)
    try:
        knowledge_base.insert(content=markdown, metadata={"title": title, "source": file_path})
        kb_status = "indexed"
    except Exception as e:
        kb_status = f"error ({e})"

    return (
        f"DOCUMENT_PROCESSED: {title}\n"
        f"- Parsed: {len(markdown)} chars extracted\n"
        f"- Directus: {directus_status}\n"
        f"- Knowledge base: {kb_status}"
    )
