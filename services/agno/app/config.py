"""
QYNE v1 — Shared configuration.

Identical to the original nexus.py storage/knowledge/model setup,
adapted for Docker (data stored in /app/data/ volume).
"""

import os
from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.knowledge.embedder.voyageai import VoyageAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.vectordb.lancedb import LanceDb, SearchType

# ---------------------------------------------------------------------------
# Storage (SQLite + LanceDB, same as original nexus.py)
# ---------------------------------------------------------------------------
# In Docker: /app/data/ is a persistent volume.
# Locally: defaults to current directory (same as nexus.py).

DATA_DIR = Path(os.getenv("QYNE_DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

db = SqliteDb(db_file=str(DATA_DIR / "nexus.db"))

# ---------------------------------------------------------------------------
# Knowledge Base (LanceDB local + Voyage AI embeddings)
# ---------------------------------------------------------------------------
# LanceDB stores vectors locally (like SQLite). Voyage AI generates embeddings
# via API. Drop files into knowledge/ and restart.

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"
KNOWLEDGE_DIR.mkdir(exist_ok=True)

embedder = VoyageAIEmbedder(
    id="voyage-3-lite",
    dimensions=512,
)

vector_db = LanceDb(
    uri=str(DATA_DIR / "lancedb"),
    table_name="nexus_knowledge",
    search_type=SearchType.hybrid,
    embedder=embedder,
)

knowledge_base = Knowledge(
    name="NEXUS Knowledge",
    description="Internal documents, research, and reference material",
    vector_db=vector_db,
    contents_db=db,
)

# Learnings vector DB (separate table for what the agents learn over time).
learnings_db = LanceDb(
    uri=str(DATA_DIR / "lancedb"),
    table_name="nexus_learnings",
    search_type=SearchType.hybrid,
    embedder=embedder,
)

learnings_knowledge = Knowledge(
    name="NEXUS Learnings",
    description="Accumulated agent learnings, patterns, and corrections",
    vector_db=learnings_db,
    contents_db=db,
)

# Index all supported files in the knowledge/ folder on startup.
for file_path in sorted(KNOWLEDGE_DIR.iterdir()):
    if file_path.suffix.lower() in {".pdf", ".txt", ".md", ".csv", ".json"}:
        knowledge_base.insert(path=file_path, skip_if_exists=True)

# ---------------------------------------------------------------------------
# Model Configuration (same as original nexus.py)
# ---------------------------------------------------------------------------

_openrouter_kwargs = {
    "api_key": os.getenv("OPENROUTER_API_KEY"),
    "base_url": "https://openrouter.ai/api/v1",
}

_minimax_role_map = {
    "system": "system",
    "user": "user",
    "assistant": "assistant",
    "tool": "tool",
    "model": "assistant",
}

_minimax_kwargs = {
    "api_key": os.getenv("MINIMAX_API_KEY"),
    "base_url": "https://api.minimax.io/v1",
    "role_map": _minimax_role_map,
    "supports_native_structured_outputs": False,
    "supports_json_schema_outputs": False,
}

TOOL_MODEL = OpenAIChat(id="MiniMax-M2.7", **_minimax_kwargs)
FAST_MODEL = OpenAIChat(id="MiniMax-M2.7", **_minimax_kwargs)
REASONING_MODEL = OpenAIChat(id="openai/gpt-5-mini", **_openrouter_kwargs)
FOLLOWUP_MODEL = OpenAIChat(id="openai/gpt-5-nano", **_openrouter_kwargs)
LEARNING_MODEL = OpenAIChat(id="openai/gpt-4o-mini", **_openrouter_kwargs)
GROQ_FAST_MODEL = Groq(id="llama-3.1-8b-instant")
GROQ_ROUTING_MODEL = Groq(id="openai/gpt-oss-20b")

# ---------------------------------------------------------------------------
# Directus connection
# ---------------------------------------------------------------------------

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")

# ---------------------------------------------------------------------------
# Skills directory
# ---------------------------------------------------------------------------

SKILLS_DIR = Path(__file__).parent.parent / "skills"
