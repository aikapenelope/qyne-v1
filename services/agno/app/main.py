"""
QYNE v1 — AgentOS Entry Point.

Same pattern as original nexus.py but modular.
SQLite + LanceDB for storage. Docling via knowledge reader (official Agno v2.5.10).
"""

import os

from agno.os import AgentOS

try:
    from agno.os.interfaces.agui import AGUI
    _agui_available = True
except ImportError:
    _agui_available = False

from agno.os.interfaces.whatsapp.whatsapp import Whatsapp

from app.config import db, knowledge_base

from agents.research import research_agent
from agents.knowledge import knowledge_agent
from agents.support import support_agent

# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------

interfaces: list = []

if _agui_available:
    interfaces.append(AGUI())

if os.getenv("WHATSAPP_ACCESS_TOKEN"):
    interfaces.append(Whatsapp(agent=support_agent))

# ---------------------------------------------------------------------------
# AgentOS
# ---------------------------------------------------------------------------

agent_os = AgentOS(
    id="qyne",
    description="QYNE v1 — Enterprise AI Workspace",
    agents=[
        research_agent,
        knowledge_agent,
        support_agent,
    ],
    teams=[],
    workflows=[],
    knowledge=[knowledge_base],
    interfaces=interfaces or None,
    db=db,
    tracing=True,
    scheduler=True,
    scheduler_poll_interval=30,
)

app = agent_os.get_app()
