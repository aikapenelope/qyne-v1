"""QYNE v1 — Agno config. SQLite + LanceDB (embedded, no PostgreSQL)."""

import os
from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.knowledge.chunking.fixed_size_chunking import FixedSizeChunking
from agno.knowledge.embedder.voyageai import VoyageAIEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reranker import InfinityReranker
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from agno.vectordb.lancedb import LanceDb, SearchType

DATA_DIR = Path(os.getenv("AGNO_DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

db = SqliteDb(db_file=str(DATA_DIR / "nexus.db"))

embedder = VoyageAIEmbedder(id="voyage-3-lite", dimensions=512)

reranker = InfinityReranker(
    model="BAAI/bge-reranker-base",
    host=os.getenv("RERANKER_HOST", "reranker"),
    port=int(os.getenv("RERANKER_PORT", "7997")),
    top_n=5,
)

chunking = FixedSizeChunking(chunk_size=2000, overlap=200)

_lancedb_uri = str(DATA_DIR / "lancedb")

_vdb_kwargs = {"uri": _lancedb_uri, "search_type": SearchType.hybrid, "embedder": embedder, "reranker": reranker}

knowledge_base = Knowledge(name="qyne-general", vector_db=LanceDb(table_name="knowledge", **_vdb_kwargs), contents_db=db, isolate_vector_search=True)
whabi_knowledge = Knowledge(name="qyne-whabi", vector_db=LanceDb(table_name="knowledge", **_vdb_kwargs), contents_db=db, isolate_vector_search=True)
docflow_knowledge = Knowledge(name="qyne-docflow", vector_db=LanceDb(table_name="knowledge", **_vdb_kwargs), contents_db=db, isolate_vector_search=True)
aurora_knowledge = Knowledge(name="qyne-aurora", vector_db=LanceDb(table_name="knowledge", **_vdb_kwargs), contents_db=db, isolate_vector_search=True)
learnings_knowledge = Knowledge(name="qyne-learnings", vector_db=LanceDb(table_name="learnings", **_vdb_kwargs), contents_db=db, isolate_vector_search=True)

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"

def load_initial_knowledge() -> None:
    if not KNOWLEDGE_DIR.exists():
        return
    knowledge_base.insert(path=str(KNOWLEDGE_DIR), skip_if_exists=True)

# Models
_openrouter = {"api_key": os.getenv("OPENROUTER_API_KEY"), "base_url": "https://openrouter.ai/api/v1"}
_minimax_role = {"system": "system", "user": "user", "assistant": "assistant", "tool": "tool", "model": "assistant"}
_minimax = {"api_key": os.getenv("MINIMAX_API_KEY"), "base_url": "https://api.minimax.io/v1", "role_map": _minimax_role, "supports_native_structured_outputs": False, "supports_json_schema_outputs": False}

TOOL_MODEL = OpenAIChat(id="MiniMax-M2.7", **_minimax)
FAST_MODEL = OpenAIChat(id="MiniMax-M2.7", **_minimax)
REASONING_MODEL = OpenAIChat(id="openai/gpt-5-mini", **_openrouter)
FOLLOWUP_MODEL = OpenAIChat(id="openai/gpt-5-nano", **_openrouter)
LEARNING_MODEL = OpenAIChat(id="openai/gpt-4o-mini", **_openrouter)
GROQ_FAST_MODEL = Groq(id="llama-3.1-8b-instant")

DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://directus:8055")
DIRECTUS_TOKEN = os.getenv("DIRECTUS_TOKEN", "")
