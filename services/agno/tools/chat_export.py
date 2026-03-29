"""
QYNE v1 — Chat Export Tools.

Tools for saving chat conversations to Directus and optionally to LanceDB knowledge.
The agent calls these when the user says "guarda esta conversacion" or "ponlo en knowledge".

No extra tokens consumed — the conversation is already in memory.
"""

import os
from datetime import datetime

import httpx
from agno.tools.decorator import tool

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
_HEADERS = {
    "Authorization": f"Bearer {DIRECTUS_TOKEN}",
    "Content-Type": "application/json",
}


@tool()
def save_chat_to_directus(
    title: str,
    summary: str,
    full_conversation: str,
    tags: str = "",
) -> str:
    """Save the current conversation to Directus as a document in markdown format.

    Call this when the user says "guarda esta conversacion", "save this chat",
    or "exporta el chat". The conversation is saved as a markdown document
    in the documents collection.

    Args:
        title: A short title for the conversation (e.g., "Crawl de startups.rip")
        summary: A 2-3 sentence summary of what was discussed
        full_conversation: The full conversation formatted as markdown
        tags: Comma-separated tags (e.g., "scraping,startups,research")
    """
    if not DIRECTUS_TOKEN:
        return "Error: DIRECTUS_TOKEN not configured"

    # Format as markdown
    markdown = f"""# {title}

**Fecha**: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
**Tags**: {tags}

## Resumen
{summary}

## Conversacion completa
{full_conversation}
"""

    resp = httpx.post(
        f"{DIRECTUS_URL}/items/documents",
        json={
            "title": title[:500],
            "content": markdown[:50000],
            "source_file": f"chat-export-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "status": f"chat-export:{tags.split(',')[0] if tags else 'general'}",
        },
        headers=_HEADERS,
        timeout=10,
    )

    if resp.is_success:
        doc_id = resp.json()["data"]["id"]
        return f"Conversacion guardada en Directus (documents ID={doc_id}). Titulo: {title}"
    return f"Error guardando: {resp.status_code}"


@tool()
def save_chat_to_knowledge(
    title: str,
    content: str,
    tags: str = "",
) -> str:
    """Save conversation content to the knowledge base (LanceDB) for future agent retrieval.

    Call this when the user says "ponlo en knowledge", "indexalo",
    or "que los agentes puedan buscar esto".

    This generates embeddings and indexes the content so agents can find it
    when answering future questions.

    Args:
        title: Title for the knowledge entry
        content: The content to index (conversation summary or key findings)
        tags: Comma-separated tags for metadata
    """
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
            metadata={
                "title": title,
                "source": "chat-export",
                "tags": tags,
                "date": datetime.utcnow().isoformat(),
            },
        )
        return f"Contenido indexado en knowledge base. Titulo: {title}. Los agentes ahora pueden buscar esta informacion."
    except Exception as e:
        return f"Error indexando: {e}"
